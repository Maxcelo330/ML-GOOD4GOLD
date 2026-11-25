"""
Paso 4 (tarea T-003 simplificada, SIN radar) - Compuesto Sentinel-2 de epoca seca 2026,
indices espectrales y pendiente del terreno, todo en la MISMA grilla de 20 m.

Que hace, en orden:
  1. Busca en el catalogo STAC de Microsoft Planetary Computer (gratis, sin credenciales)
     varias escenas Sentinel-2 L2A de mayo a septiembre de 2026 por cada "tile" que cubre la
     zona, con pocas nubes y de ORBITAS distintas (asi se tapan los huecos que deja una sola
     pasada del satelite).
  2. Baja a una carpeta temporal solo la parte de cada escena que cae dentro de la zona,
     ya reducida a 20 m (los archivos son COG: se leen por partes).
  3. Por cada pixel toma la MEDIANA de las observaciones validas (sin nubes, sin sombra de
     nube, sin cirrus, sin nieve, sin saturar). La mediana "ignora" lo raro: si una fecha
     tiene nube en ese pixel, las otras fechas mandan.
  4. Calcula NDVI, NDWI y BSI sobre los compuestos medianos.
  5. Calcula la pendiente (grados) con el modelo de elevacion Copernicus GLO-30.
  6. Guarda GeoTIFF, miniaturas PNG y metadata.json.

Nota tecnica importante: en este equipo rasterio.merge, rasterio.windows.from_bounds y
rasterio.transform.rowcol cierran Python sin avisar (error 0xc06d007f). Por eso las ventanas
se calculan a mano con aritmetica simple (igual que en paso3_previa_sentinel.py) y el DEM se
remuestrea con scipy en vez de rasterio.warp.reproject.

Como correrlo (entorno g4g-ml), desde la raiz del repo:
  python -I -u 05_CODIGO\\paso4_compuesto_indices.py
Opciones:
  --conservar-cache   no borra la carpeta temporal con las escenas bajadas
  --solo-seleccion    solo muestra que escenas elegiria y termina (no descarga nada)
"""
import argparse
import datetime
import json
import platform
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import geopandas as gpd
import numpy as np
import planetary_computer
import pyproj
import pystac_client
import rasterio
import scipy
from PIL import Image
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.windows import Window
from scipy.ndimage import map_coordinates
from shapely.geometry import shape

try:
    import psutil
except ImportError:  # solo sirve para medir cuanto se bajo; no es obligatorio
    psutil = None

# ------------------------------------------------------------------ parametros
RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "04_DATOS" / "imagenes" / "compuesto"
CACHE = SALIDA / "_cache_escenas"           # carpeta temporal (se borra al final)
MINIATURAS = SALIDA / "miniaturas"

PERIODO = "2026-05-01/2026-09-30"           # epoca seca
MAX_NUBES = 30                              # % maximo de nubes de la escena completa
ESCENAS_INICIO = 6                          # escenas por tile al comenzar
ESCENAS_MAX = 12                            # tope de escenas por tile
PASO_EXTRA = 2                              # cuantas escenas se agregan por tile si quedan huecos
UMBRAL_HUECOS_PCT = 0.5                     # si queda mas de esto sin datos, se agregan escenas
RES = 20.0                                  # resolucion de salida (metros)
NODATA = -9999.0
FILAS_TIRA = 512                            # filas que se procesan juntas (controla la memoria)

BANDAS = ["B02", "B03", "B04", "B08", "B11", "B12"]
# Valores de la mascara SCL que se DESCARTAN: 0 sin datos, 1 saturado, 3 sombra de nube,
# 8 nube probabilidad media, 9 nube probabilidad alta, 10 cirrus, 11 nieve/hielo
SCL_INVALIDOS = [0, 1, 3, 8, 9, 10, 11]

FORMULAS = {
    "NDVI": "(B08 - B04) / (B08 + B04)",
    "NDWI": "(B03 - B08) / (B03 + B08)",
    "BSI": "((B11 + B04) - (B08 + B02)) / ((B11 + B04) + (B08 + B02))",
}

URL_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


def bytes_red():
    """Bytes recibidos por la red hasta ahora (para estimar cuanto se descargo)."""
    return psutil.net_io_counters().bytes_recv if psutil else 0


# ------------------------------------------------------------------ 0. la grilla
# Zona piloto en UTM 19S (metros). Los bordes se ajustan a multiplos de 20 m para que la
# grilla calce exacto con los pixeles Sentinel-2 (los tiles empiezan en multiplos de 10/20 m).
aoi_gdf = gpd.read_file(RAIZ / "04_DATOS" / "zona_piloto.gpkg", layer="aoi_utm19s")
aoi_wgs = gpd.read_file(RAIZ / "04_DATOS" / "zona_piloto.gpkg", layer="aoi_wgs84")
xmin, ymin, xmax, ymax = aoi_gdf.total_bounds
X0 = float(np.floor(xmin / RES) * RES)
X1 = float(np.ceil(xmax / RES) * RES)
Y0 = float(np.floor(ymin / RES) * RES)
Y1 = float(np.ceil(ymax / RES) * RES)
ANCHO = int(round((X1 - X0) / RES))
ALTO = int(round((Y1 - Y0) / RES))
TRANSFORM = from_origin(X0, Y1, RES, RES)    # esquina superior izquierda (X0, Y1), pixel RES x RES
CRS = "EPSG:32719"


# ------------------------------------------------------------------ 1. escenas
def buscar_escenas():
    """Devuelve {tile: [escenas ordenadas de menos a mas nubes]} (escenas ya firmadas)."""
    catalogo = pystac_client.Client.open(URL_STAC, modifier=planetary_computer.sign_inplace)
    items = list(catalogo.search(
        collections=["sentinel-2-l2a"], bbox=list(aoi_wgs.total_bounds), datetime=PERIODO,
        query={"eo:cloud_cover": {"lt": MAX_NUBES}}).items())
    por_tile = {}
    for it in items:
        por_tile.setdefault(it.properties["s2:mgrs_tile"], []).append(it)
    for tile in por_tile:
        por_tile[tile].sort(key=lambda e: e.properties["eo:cloud_cover"])
    return por_tile


def fraccion_zona_cubierta(item):
    """Fraccion de la zona piloto que cae dentro del contorno de datos de la escena.
    Sirve para no gastar escenas en pasadas que casi no tocan la zona."""
    contorno = gpd.GeoSeries([shape(item.geometry)], crs=4326).to_crs(CRS).iloc[0]
    return contorno.intersection(aoi_gdf.geometry.union_all()).area / aoi_gdf.geometry.union_all().area


def elegir(por_tile, n_por_tile, extra_tiles=None):
    """Elige hasta n_por_tile escenas por tile, mezclando ORBITAS distintas.

    Regla: primero la mejor escena (menos nubes) de cada orbita relativa que realmente cubre
    la zona, y luego se completa con las escenas de menos nubes. Dos orbitas distintas
    ven franjas distintas del terreno, y por eso se tapan los huecos de borde.
    extra_tiles: {tile: n} para pedir mas escenas solo en algunos tiles.
    """
    elegidas = {}
    for tile, lista in por_tile.items():
        n = (extra_tiles or {}).get(tile, n_por_tile)
        util = [e for e in lista if fraccion_zona_cubierta(e) > 0.005]
        orbitas = sorted({e.properties["sat:relative_orbit"] for e in util})
        sel = []
        # Se garantizan hasta 3 escenas de cada orbita (las de menos nubes)
        for orb in orbitas:
            sel += [e for e in util if e.properties["sat:relative_orbit"] == orb][:max(1, min(3, n // len(orbitas)))]
        for e in util:  # completar con las demas, de menos a mas nubes
            if len(sel) >= n:
                break
            if e not in sel:
                sel.append(e)
        elegidas[tile] = sorted(sel[:n], key=lambda e: e.datetime)
    return elegidas


# ------------------------------------------------------------------ 2. descarga a la cache
def ventana_en_grilla(src):
    """Rectangulo de la grilla de salida que cubre esta escena (calculo a mano, sin rasterio.windows.from_bounds).
    Devuelve (col_dst, fila_dst, ancho, alto) en pixeles de 20 m, o None si no se tocan."""
    ix0 = max(X0, src.bounds.left)
    ix1 = min(X1, src.bounds.right)
    iy0 = max(Y0, src.bounds.bottom)
    iy1 = min(Y1, src.bounds.top)
    if ix0 >= ix1 or iy0 >= iy1:
        return None
    # Alinear a multiplos de RES contando desde la esquina de la grilla
    c0 = int(np.ceil((ix0 - X0) / RES))
    c1 = int(np.floor((ix1 - X0) / RES))
    f0 = int(np.ceil((Y1 - iy1) / RES))
    f1 = int(np.floor((Y1 - iy0) / RES))
    if c1 <= c0 or f1 <= f0:
        return None
    return c0, f0, c1 - c0, f1 - f0


def leer_banda(href, rect, remuestreo):
    """Lee la parte de una banda que cae en 'rect' (de la grilla de salida), ya a 20 m."""
    c0, f0, w, h = rect
    x_izq = X0 + c0 * RES
    y_sup = Y1 - f0 * RES
    with rasterio.open(href) as src:
        t = src.transform  # t.a = tamano de pixel de la banda (10 o 20 m), t.c / t.f = esquina sup. izq.
        ventana = Window(round((x_izq - t.c) / t.a), round((t.f - y_sup) / -t.e),
                         round(w * RES / t.a), round(h * RES / -t.e))
        # Si la banda es de 10 m, out_shape la reduce a 20 m promediando 2x2 pixeles
        return src.read(1, window=ventana, out_shape=(h, w), resampling=remuestreo)


def bajar_escena(item):
    """Guarda en CACHE/<id>/ las 6 bandas (uint16) y la SCL (uint8) de la parte que cae en la zona."""
    carpeta = CACHE / item.id
    marca = carpeta / "listo.json"
    if marca.exists():
        return json.loads(marca.read_text())
    carpeta.mkdir(parents=True, exist_ok=True)
    item = planetary_computer.sign(item)  # renueva la firma del enlace (caduca con el tiempo)
    with rasterio.open(item.assets["B04"].href) as src:
        rect = ventana_en_grilla(src)
        # Los tiles deben arrancar en multiplos de 20 m para calzar con la grilla
        assert abs((src.transform.c - X0) / RES - round((src.transform.c - X0) / RES)) < 1e-6, "tile desalineado"
    if rect is None:
        info = {"rect": None}
        marca.write_text(json.dumps(info))
        return info

    def tarea(nombre):
        remuestreo = Resampling.nearest if nombre == "SCL" else Resampling.average
        for intento in range(4):
            try:
                a = leer_banda(item.assets[nombre].href, rect, remuestreo)
                np.save(carpeta / f"{nombre}.npy", a.astype("uint8" if nombre == "SCL" else "uint16"))
                return nombre
            except Exception as err:  # error de red: reintentar
                print(f"    reintento {intento + 1} de {nombre}: {err}", flush=True)
                time.sleep(3)
        raise RuntimeError(f"no se pudo leer {nombre} de {item.id}")

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(tarea, BANDAS + ["SCL"]))
    info = {"rect": rect}
    marca.write_text(json.dumps(info))
    return info


def datos_escena(item):
    """Resumen de una escena para el metadata.json, incluyendo el offset de reflectancia."""
    base = item.properties.get("s2:processing_baseline", "")
    offset = 1000 if float(base) >= 4.0 else 0  # baseline >= 04.00 => DN lleva -1000 de offset
    return {
        "id": item.id, "tile": item.properties["s2:mgrs_tile"], "fecha": str(item.datetime.date()),
        "nubes_pct": round(item.properties["eo:cloud_cover"], 1),
        "orbita_relativa": item.properties.get("sat:relative_orbit"),
        "baseline": base, "offset_dn": offset,
        "pct_sin_datos_en_tile": round(item.properties.get("s2:nodata_pixel_percentage", 0), 1),
    }


# ------------------------------------------------------------------ 3. mediana por tiras
def mediana_pila(pila):
    """Mediana por pixel ignorando NaN (equivale a np.nanmedian pero mucho mas rapida).

    Se ordenan las observaciones de cada pixel (los NaN quedan al final), se cuenta cuantas
    son validas (n) y se toma el valor del medio (o el promedio de los dos del medio).
    Devuelve (mediana, n). Donde n = 0 la mediana es NaN.
    """
    pila = np.sort(pila, axis=0)
    n = np.sum(~np.isnan(pila), axis=0).astype("int16")
    nmax = pila.shape[0]
    bajo = np.clip((n - 1) // 2, 0, nmax - 1)[None]
    alto = np.clip(n // 2, 0, nmax - 1)[None]
    v1 = np.take_along_axis(pila, bajo, axis=0)[0]
    v2 = np.take_along_axis(pila, alto, axis=0)[0]
    med = (v1 + v2) / 2
    med[n == 0] = np.nan
    return med.astype("float32"), n


def cargar_cache(escenas):
    """Abre (sin cargar en RAM, con memmap) los arrays de cada escena. Lista de dicts."""
    lista = []
    for it in escenas:
        info = json.loads((CACHE / it.id / "listo.json").read_text())
        if info["rect"] is None:
            continue
        d = {"item": it, "rect": info["rect"], "offset": datos_escena(it)["offset_dn"]}
        for nombre in BANDAS + ["SCL"]:
            d[nombre] = np.load(CACHE / it.id / f"{nombre}.npy", mmap_mode="r")
        lista.append(d)
    return lista


def tira_de_escena(d, nombre, f0, f1):
    """Recorta de una escena la franja de filas [f0, f1) de la grilla. Devuelve (col0, array) o None."""
    c0, r0, w, h = d["rect"]
    a, b = max(f0, r0), min(f1, r0 + h)
    if a >= b:
        return None
    return c0, w, a - f0, d[nombre][a - r0:b - r0]


def contar_observaciones(lista):
    """Cuenta por pixel cuantas observaciones validas hay (solo con la mascara SCL; rapido)."""
    n = np.zeros((ALTO, ANCHO), dtype="uint8")
    for d in lista:
        c0, r0, w, h = d["rect"]
        valido = ~np.isin(np.asarray(d["SCL"]), SCL_INVALIDOS)
        n[r0:r0 + h, c0:c0 + w] += valido
    return n


def construir_compuesto(lista, ruta_bandas, ruta_n, mascara_aoi):
    """Recorre la zona por tiras de filas y escribe bandas medianas, n_observaciones e indices."""
    perfil = dict(driver="GTiff", height=ALTO, width=ANCHO, crs=CRS, transform=TRANSFORM,
                  compress="deflate", tiled=True, blockxsize=256, blockysize=256, predictor=3)
    perfil_1 = dict(perfil, count=1, dtype="float32", nodata=NODATA)
    salidas = {
        "bandas": rasterio.open(ruta_bandas, "w", **dict(perfil_1, count=len(BANDAS))),
        "ndvi": rasterio.open(SALIDA / "ndvi_2026.tif", "w", **perfil_1),
        "ndwi": rasterio.open(SALIDA / "ndwi_2026.tif", "w", **perfil_1),
        "bsi": rasterio.open(SALIDA / "bsi_2026.tif", "w", **perfil_1),
        "n": rasterio.open(ruta_n, "w", **dict(perfil, count=1, dtype="uint8", nodata=0, predictor=2)),
    }
    for i, b in enumerate(BANDAS, 1):
        salidas["bandas"].set_band_description(i, b)
    salidas["ndvi"].set_band_description(1, "NDVI " + FORMULAS["NDVI"])
    salidas["ndwi"].set_band_description(1, "NDWI " + FORMULAS["NDWI"])
    salidas["bsi"].set_band_description(1, "BSI " + FORMULAS["BSI"])
    salidas["n"].set_band_description(1, "observaciones validas por pixel")

    estad = {"sin_datos_aoi": 0, "n_aoi": 0}
    for f0 in range(0, ALTO, FILAS_TIRA):
        f1 = min(ALTO, f0 + FILAS_TIRA)
        h = f1 - f0
        ventana = Window(0, f0, ANCHO, h)
        # (a) mascara de validez de cada escena en esta tira (a partir de la SCL)
        activas = []
        for d in lista:
            t = tira_de_escena(d, "SCL", f0, f1)
            if t is None:
                continue
            c0, w, fa, scl = t
            valido = ~np.isin(np.asarray(scl), SCL_INVALIDOS)
            activas.append((d, valido))
        # (b) mediana de cada banda
        medianas = {}
        n_obs = None
        for b in BANDAS:
            pila = np.full((max(1, len(activas)), h, ANCHO), np.nan, dtype="float32")
            for k, (d, valido) in enumerate(activas):
                c0, w, fa, dn = tira_de_escena(d, b, f0, f1)
                dn = np.asarray(dn).astype("float32")
                # reflectancia = (DN - offset) / 10000; DN = 0 es "sin datos" de la imagen
                refl = (dn - d["offset"]) / 10000.0
                refl = np.clip(refl, 0.0, 1.5)           # recorte a [0, 1.5] antes de los indices
                refl[(dn == 0) | ~valido] = np.nan        # fuera lo invalido
                pila[k, fa:fa + dn.shape[0], c0:c0 + w] = refl
            medianas[b], n = mediana_pila(pila)
            n_obs = n if n_obs is None else np.minimum(n_obs, n)  # observaciones usables en TODAS las bandas
            del pila
        # (c) pixeles sin datos en alguna banda -> sin datos en todas
        sin = np.zeros((h, ANCHO), dtype=bool)
        for b in BANDAS:
            sin |= np.isnan(medianas[b])
        n_obs[sin] = 0
        # (d) indices sobre las medianas
        B2, B3, B4, B8, B11 = (medianas[x] for x in ("B02", "B03", "B04", "B08", "B11"))
        with np.errstate(divide="ignore", invalid="ignore"):
            ndvi = (B8 - B4) / (B8 + B4)
            ndwi = (B3 - B8) / (B3 + B8)
            bsi = ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))
        # (e) escribir
        for i, b in enumerate(BANDAS, 1):
            a = np.where(sin, NODATA, medianas[b]).astype("float32")
            salidas["bandas"].write(a, i, window=ventana)
        for clave, idx in (("ndvi", ndvi), ("ndwi", ndwi), ("bsi", bsi)):
            a = np.where(sin | ~np.isfinite(idx), NODATA, idx).astype("float32")
            salidas[clave].write(a, 1, window=ventana)
        salidas["n"].write(n_obs.astype("uint8"), 1, window=ventana)
        m = mascara_aoi[f0:f1]
        estad["n_aoi"] += int(m.sum())
        estad["sin_datos_aoi"] += int((sin & m).sum())
        print(f"  tira filas {f0}-{f1} de {ALTO} lista", flush=True)
    for s in salidas.values():
        s.close()
    return estad


# ------------------------------------------------------------------ 4. pendiente (DEM)
def pendiente_grados(ruta_salida):
    """Pendiente en grados en la grilla de 20 m a partir del DEM Copernicus GLO-30.

    1) Se bajan los cuadros de 1 grado del DEM que cubren la zona (estan en EPSG:4326).
    2) Para cada pixel de la grilla de 20 m (con 1 pixel extra de margen) se calcula su
       longitud/latitud y se interpola la altura del DEM (map_coordinates, interpolacion lineal).
    3) La pendiente sale del gradiente de alturas: tan(pendiente) = sqrt((dz/dx)^2 + (dz/dy)^2),
       donde dx y dy se miden en METROS (pixel de 20 m). El margen extra evita el efecto de borde.
    """
    catalogo = pystac_client.Client.open(URL_STAC, modifier=planetary_computer.sign_inplace)
    items = list(catalogo.search(collections=["cop-dem-glo-30"], bbox=list(aoi_wgs.total_bounds)).items())
    print(f"  cuadros DEM encontrados: {len(items)}", flush=True)
    # Armar un mosaico del DEM (los cuadros son de 1 x 1 grado y vienen alineados a grados enteros)
    trozos = []
    for it in items:
        with rasterio.open(it.assets["data"].href) as src:
            trozos.append((src.transform, src.read(1).astype("float32"), src.nodata))
    lon_min = min(t[0].c for t in trozos)
    lat_max = max(t[0].f for t in trozos)
    lon_max = max(t[0].c + t[0].a * t[1].shape[1] for t in trozos)
    lat_min = min(t[0].f + t[0].e * t[1].shape[0] for t in trozos)
    pix = trozos[0][0].a  # tamano de pixel en grados
    dem = np.full((int(round((lat_max - lat_min) / pix)), int(round((lon_max - lon_min) / pix))), np.nan, "float32")
    for t, a, nd in trozos:
        c = int(round((t.c - lon_min) / pix))
        f = int(round((lat_max - t.f) / pix))
        if nd is not None:
            a = np.where(a == nd, np.nan, a)
        dem[f:f + a.shape[0], c:c + a.shape[1]] = a
    print(f"  mosaico DEM: {dem.shape[1]} x {dem.shape[0]} px", flush=True)

    # Grilla de 20 m con 1 pixel de margen por lado
    alto, ancho = ALTO + 2, ANCHO + 2
    transf = pyproj.Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
    xs = X0 - RES / 2 + RES * np.arange(ancho)       # centros de pixel (con margen)
    z = np.empty((alto, ancho), dtype="float32")
    for r0 in range(0, alto, 400):
        r1 = min(alto, r0 + 400)
        ys = Y1 + RES / 2 - RES * np.arange(r0, r1)
        gx, gy = np.meshgrid(xs, ys)
        lon, lat = transf.transform(gx, gy)
        # coordenadas fraccionarias dentro del mosaico DEM (el centro del pixel 0 esta en 0.5)
        col = (lon - lon_min) / pix - 0.5
        fil = (lat_max - lat) / pix - 0.5
        z[r0:r1] = map_coordinates(dem, [fil, col], order=1, mode="nearest")
    # Gradiente con numpy: filas crecen hacia el sur, por eso dz/dy_norte = -dz/dfila
    dz_dfila, dz_dcol = np.gradient(z, RES, RES)
    pend = np.degrees(np.arctan(np.hypot(dz_dfila, dz_dcol)))
    pend = pend[1:-1, 1:-1].astype("float32")          # quitar el margen
    pend[~np.isfinite(pend)] = NODATA
    perfil = dict(driver="GTiff", height=ALTO, width=ANCHO, count=1, dtype="float32", crs=CRS,
                  transform=TRANSFORM, compress="deflate", tiled=True, blockxsize=256,
                  blockysize=256, predictor=3, nodata=NODATA)
    with rasterio.open(ruta_salida, "w", **perfil) as dst:
        dst.write(pend, 1)
        dst.set_band_description(1, "pendiente en grados (DEM Copernicus GLO-30)")
    return {"cuadros_dem": [i.id for i in items], "dem_min_m": float(np.nanmin(z)), "dem_max_m": float(np.nanmax(z)),
            "pendiente_media_grados": float(pend[pend != NODATA].mean()),
            "pendiente_max_grados": float(pend.max())}


# ------------------------------------------------------------------ 5. miniaturas
def reducir(a, factor):
    """Reduce un array 2D (o 3D con bandas primero) promediando bloques; ignora NaN."""
    h = (a.shape[-2] // factor) * factor
    w = (a.shape[-1] // factor) * factor
    a = a[..., :h, :w]
    nuevo = a.reshape(*a.shape[:-2], h // factor, factor, w // factor, factor)
    with np.errstate(all="ignore"):
        return np.nanmean(nuevo, axis=(-3, -1))


def miniaturas(ruta_bandas):
    import matplotlib
    MINIATURAS.mkdir(parents=True, exist_ok=True)
    factor = int(np.ceil(max(ANCHO, ALTO) / 1400))
    # Color natural: B04 (rojo), B03 (verde), B02 (azul) = bandas 3, 2, 1 del archivo
    with rasterio.open(ruta_bandas) as src:
        rgb = np.stack([src.read(i).astype("float32") for i in (3, 2, 1)])
    rgb[rgb == NODATA] = np.nan
    peq = reducir(rgb, factor)
    valido = np.isfinite(peq).all(axis=0)
    # Estiramiento 2-98 %: los valores bajo el percentil 2 van a negro y sobre el 98 a blanco
    lo, hi = np.percentile(peq[:, valido], [2, 98])
    img = np.clip((peq - lo) / (hi - lo), 0, 1)
    img = (np.nan_to_num(img) * 255).astype("uint8").transpose(1, 2, 0)
    img[~valido] = (255, 0, 255)  # magenta = sin datos (asi los huecos no se confunden con agua/sombra)
    Image.fromarray(img).save(MINIATURAS / "color_natural_2026.png")
    del rgb
    for nombre, archivo, vmin, vmax, mapa in (("ndvi", "ndvi_2026.tif", -0.1, 0.9, "RdYlGn"),
                                              ("bsi", "bsi_2026.tif", -0.3, 0.3, "YlOrBr")):
        with rasterio.open(SALIDA / archivo) as src:
            a = src.read(1)
        a[a == NODATA] = np.nan
        peq = reducir(a, factor)
        norm = np.clip((peq - vmin) / (vmax - vmin), 0, 1)
        color = (matplotlib.colormaps[mapa](np.nan_to_num(norm))[..., :3] * 255).astype("uint8")
        color[~np.isfinite(peq)] = (255, 0, 255)
        Image.fromarray(color).save(MINIATURAS / f"{nombre}_2026.png")
    print(f"  miniaturas guardadas (reduccion x{factor})", flush=True)


# ------------------------------------------------------------------ programa principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conservar-cache", action="store_true")
    ap.add_argument("--solo-seleccion", action="store_true")
    args = ap.parse_args()
    t_ini = time.time()
    red_ini = bytes_red()
    SALIDA.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    print(f"Grilla: {ANCHO} x {ALTO} px a {RES:.0f} m, esquina sup. izq. ({X0}, {Y1}), {CRS}", flush=True)

    # Mascara de la zona piloto en la grilla (para medir el % sin datos solo DENTRO de la zona)
    mascara_aoi = rasterize([(g, 1) for g in aoi_gdf.geometry], out_shape=(ALTO, ANCHO),
                            transform=TRANSFORM, fill=0, dtype="uint8").astype(bool)

    print("Buscando escenas en Planetary Computer...", flush=True)
    por_tile = buscar_escenas()
    print({t: len(v) for t, v in sorted(por_tile.items())}, flush=True)

    n_por_tile = ESCENAS_INICIO
    extra = {}
    historial = []
    while True:
        elegidas = elegir(por_tile, n_por_tile, extra)
        escenas = [e for t in sorted(elegidas) for e in elegidas[t]]
        print(f"\nEscenas elegidas ({len(escenas)}):", flush=True)
        for e in escenas:
            p = e.properties
            print(f"  {p['s2:mgrs_tile']} {e.datetime.date()} nubes {p['eo:cloud_cover']:.1f}% "
                  f"orbita {p['sat:relative_orbit']} baseline {p['s2:processing_baseline']} {e.id}", flush=True)
        if args.solo_seleccion:
            return
        print("Bajando escenas (solo la parte dentro de la zona, a 20 m)...", flush=True)
        for e in escenas:
            t0 = time.time()
            bajar_escena(e)
            print(f"  {e.id}: {time.time() - t0:.0f} s", flush=True)
        lista = cargar_cache(escenas)
        n = contar_observaciones(lista)
        sin_pct = 100 * float(((n == 0) & mascara_aoi).sum()) / float(mascara_aoi.sum())
        pocos_pct = 100 * float(((n < 3) & mascara_aoi).sum()) / float(mascara_aoi.sum())
        print(f"Sin datos dentro de la zona: {sin_pct:.3f} %; con menos de 3 observaciones: {pocos_pct:.2f} %", flush=True)
        historial.append({"escenas_por_tile": dict(extra) or n_por_tile, "n_escenas": len(escenas),
                          "sin_datos_aoi_pct": round(sin_pct, 3), "menos_de_3_obs_pct": round(pocos_pct, 2)})
        if sin_pct <= UMBRAL_HUECOS_PCT:
            break
        # Quedan huecos: pedir mas escenas solo en los tiles donde estan los huecos
        hueco = (n == 0) & mascara_aoi
        filas, cols = np.nonzero(hueco)
        nuevo = {}
        for tile, es in elegidas.items():
            with rasterio.open(es[0].assets["B04"].href) as src:
                b = src.bounds
            x = X0 + (cols + 0.5) * RES
            y = Y1 - (filas + 0.5) * RES
            dentro = ((x >= b.left) & (x < b.right) & (y >= b.bottom) & (y < b.top)).sum()
            actual = (extra or {}).get(tile, n_por_tile)
            if dentro > 0 and actual < ESCENAS_MAX and len(por_tile[tile]) > len(es):
                nuevo[tile] = min(ESCENAS_MAX, actual + PASO_EXTRA)
            else:
                nuevo[tile] = actual
        if nuevo == {t: (extra or {}).get(t, n_por_tile) for t in elegidas}:
            print("No hay mas escenas utiles que agregar; se sigue con los huecos que quedan.", flush=True)
            break
        extra = nuevo
        print(f"Se agregan escenas en los tiles con huecos: {extra}", flush=True)

    # Compuesto, indices y n_observaciones
    print("\nConstruyendo compuesto mediano por tiras...", flush=True)
    estad = construir_compuesto(lista, SALIDA / "bandas_2026_20m.tif", SALIDA / "n_observaciones.tif", mascara_aoi)
    sin_final = 100 * estad["sin_datos_aoi"] / estad["n_aoi"]
    print(f"Sin datos final dentro de la zona: {sin_final:.3f} %", flush=True)

    print("\nCalculando pendiente (DEM Copernicus GLO-30)...", flush=True)
    info_dem = pendiente_grados(SALIDA / "pendiente_grados.tif")

    print("\nMiniaturas...", flush=True)
    miniaturas(SALIDA / "bandas_2026_20m.tif")

    # Estadistica de n_observaciones dentro de la zona
    with rasterio.open(SALIDA / "n_observaciones.tif") as src:
        n_final = src.read(1)
    nn = n_final[mascara_aoi]
    distribucion = {"minimo": int(nn.min()), "maximo": int(nn.max()), "mediana": float(np.median(nn)),
                    "pct_con_0": round(100 * float((nn == 0).mean()), 3),
                    "pct_con_menos_de_3": round(100 * float((nn < 3).mean()), 2)}

    mb = (bytes_red() - red_ini) / 1e6
    meta = {
        "tarea": "T-003 simplificada (sin radar)",
        "periodo": PERIODO,
        "fuente": "Microsoft Planetary Computer: sentinel-2-l2a (STAC) y cop-dem-glo-30; sin credenciales",
        "fecha_ejecucion": datetime.datetime.now().isoformat(timespec="seconds"),
        "duracion_min": round((time.time() - t_ini) / 60, 1),
        "descarga_aprox_MB_red_del_equipo": round(mb) if psutil else "no medido (psutil no instalado)",
        "nota_descarga": "Es el trafico total de red del equipo durante la ejecucion; incluye otros programas.",
        "filtro_nubes_escena_pct": f"< {MAX_NUBES}",
        "escenas": [datos_escena(e) for e in escenas],
        "busqueda_de_escenas_historial": historial,
        "mascara_scl_descartados": {"valores": SCL_INVALIDOS,
                                    "significado": {"0": "sin datos", "1": "saturado", "3": "sombra de nube",
                                                    "8": "nube prob. media", "9": "nube prob. alta",
                                                    "10": "cirrus", "11": "nieve/hielo"}},
        "mascara_scl_conservados": "2 oscuro, 4 vegetacion, 5 suelo desnudo, 6 agua, 7 no clasificado",
        "compuesto": "mediana por pixel de las observaciones validas (mediana ignorando NaN)",
        "reflectancia": "(DN - offset) / 10000 con offset = 1000 si processing_baseline >= 04.00 (todas las escenas usadas "
                        "son 05.12 o 05.13); luego recorte a [0, 1.5]",
        "formulas_indices": FORMULAS,
        "bandas_archivo": {str(i): b for i, b in enumerate(BANDAS, 1)},
        "resolucion_m": RES,
        "reduccion_a_20m": "B02/B03/B04/B08 (10 m): promedio 2x2 (Resampling.average); B11/B12/SCL ya son de 20 m (SCL: nearest)",
        "crs": CRS,
        "grilla": {"ancho_px": ANCHO, "alto_px": ALTO, "xmin": X0, "ymax": Y1, "xmax": X1, "ymin": Y0},
        "pct_sin_datos_en_zona_piloto": round(sin_final, 3),
        "observaciones_por_pixel_en_zona": distribucion,
        "pendiente": dict(info_dem, metodo="np.gradient sobre el DEM interpolado a 20 m (map_coordinates, lineal); margen de 1 px para evitar efecto de borde"),
        "versiones": {"python": platform.python_version(), "rasterio": rasterio.__version__, "numpy": np.__version__,
                      "pystac_client": pystac_client.__version__, "scipy": scipy.__version__,
                      "pyproj": pyproj.__version__, "geopandas": gpd.__version__,
                      "planetary_computer": getattr(planetary_computer, "__version__", "sin version")},
        "semilla": "no aplica (no hay procesos aleatorios en este paso)",
        "nodata": NODATA,
    }
    (SALIDA / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    if not args.conservar_cache:
        # En Windows no se puede borrar un archivo que sigue "abierto" (memmap): se sueltan antes
        lista = None
        import gc
        gc.collect()
        shutil.rmtree(CACHE, ignore_errors=True)
    print(f"\nListo en {(time.time() - t_ini) / 60:.1f} min.", flush=True)


if __name__ == "__main__":
    main()
