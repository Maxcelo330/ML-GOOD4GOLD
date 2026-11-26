"""
Analisis de un BLOQUE dibujado en el visor: de un rectangulo en el mapa a una lista de zonas.

Que hace, en orden (cada etapa avisa su avance, el visor lo muestra):
  1. Busca en Microsoft Planetary Computer (STAC, gratis, sin credenciales) las fotos Sentinel-2 L2A de
     mayo a septiembre de 2026 con pocas nubes que cubren el bloque.
  2. Descarga SOLO la parte del bloque (mas 1 km de margen) de las bandas B02, B03, B04, B08, B11, B12 y de
     la mascara de nubes SCL, a 20 m. Misma receta que el paso 4: mediana de las fotos sin nube.
  3. Calcula NDVI, NDWI, BSI y la pendiente (DEM Copernicus GLO-30), igual que el paso 4.
  4. Corre el MODELO GUARDADO (04_DATOS/resultados/modelo_lgbm.txt) sobre cada pixel: puntaje de 0 a 1.
  5. Aplica las mismas reglas que la lista del piloto (nucleo_zonas.py) y traza las zonas.
  6. Calcula distancia al rio y al poblado mas cercanos (OpenStreetMap; si no hay internet, queda vacia).

LIMITES (se muestran tambien en el visor):
  - El modelo se entreno SOLO en el norte de La Paz (Tipuani, Mapiri, Teoponte, Guanay) con etiquetas
    propuestas por Claude. Fuera de esa zona no esta validado: puede confundir suelo agricola, roca, playas
    de rio u otro terreno. El resultado es "zonas con parecido a actividad minera", no "hay mineria".
  - Se usa la imagen de mayo-septiembre 2026. No ve el cambio en el tiempo ni imagenes mas nuevas.
  - Un bloque mide como maximo 30 x 30 km (los grandes tardan varios minutos). Zonas menores a 5 ha no se ven.
  - El puntaje es relativo, no una probabilidad. No indica legalidad ni mercurio.

Como probarlo desde la consola (entorno g4g-ml):
  python 05_CODIGO\\analisis_bloque.py <lon_oeste> <lat_sur> <lon_este> <lat_norte>
"""
import hashlib
import json
import math
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import geopandas as gpd
import lightgbm as lgb
import numpy as np
import planetary_computer
import pyproj
import pystac_client
import rasterio
import requests
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.windows import Window
from scipy.ndimage import map_coordinates
from shapely.geometry import LineString, Point, box, mapping, shape

sys.path.insert(0, str(Path(__file__).resolve().parent))   # (con 'python -I' la carpeta del script no se agrega sola)
import modelo_activo as ma  # noqa: E402
import nucleo_zonas as nz  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
MODELO_V1 = RAIZ / "04_DATOS" / "resultados" / "modelo_lgbm_v1.txt"
MODELO_V2 = RAIZ / "04_DATOS" / "resultados" / "modelo_lgbm_v2.txt"
MODELO = ma.ruta()   # modelo activo al arrancar (v2, o el que haya aprendido de las revisiones); cargar_modelo() lo vuelve a leer si cambia
SALIDA = RAIZ / "04_DATOS" / "analisis_bloques"
REF = RAIZ / "04_DATOS" / "referencia" / "rios_y_poblados.gpkg"

URL_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
PERIODO = "2026-05-01/2026-09-30"
MAX_NUBES = 30                 # % maximo de nubes de la escena completa
RES = 20.0
MARGEN_M = 1000                # se analiza 1 km mas alla del bloque para que los filtros de borde no corten zonas
MAX_LADO_KM = 30
MIN_LADO_KM = 1
MAX_ZONAS = 80
PROF = 16                      # observaciones maximas guardadas por pixel (en bloques grandes hay varias escenas encima)
PARALELO_ESCENAS = 3           # escenas que se bajan a la vez
BANDAS = ["B02", "B03", "B04", "B08", "B11", "B12"]
SCL_INVALIDOS = [0, 1, 3, 8, 9, 10, 11]
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
NOTA = ("Puntaje relativo del modelo, no es una probabilidad. Posible actividad minera (por verificar; registro AJAM "
        "aun no consultado): no indica legalidad ni presencia de mercurio. Puede incluir suelo desnudo, arena de rio "
        "o derrumbes que no son mineria. Es una lista para revisar, no una deteccion confirmada.")

UMBRALES = {"normal": 0.5, "alta": 0.3}
ETAPAS = ["Buscando imagenes satelitales", "Descargando la imagen del bloque", "Calculando indices y pendiente",
          "Corriendo el modelo", "Filtrando y trazando zonas", "Midiendo distancias a rios y poblados"]


class ErrorAnalisis(Exception):
    """Error que se le explica a la persona (no es un fallo del programa)."""


_modelo = None
_modelo_ruta = None


def cargar_modelo():
    """Carga el modelo activo (si aprendio algo nuevo y cambio el activo, lo vuelve a cargar)."""
    global _modelo, MODELO, _modelo_ruta
    MODELO = ma.ruta()
    if _modelo is None or _modelo_ruta != MODELO:
        if not MODELO.exists():
            raise ErrorAnalisis("Falta el modelo guardado (modelo_lgbm.txt). Corre paso5_modelo_base.py.")
        _modelo, _modelo_ruta = lgb.Booster(model_file=str(MODELO)), MODELO
    return _modelo


def _km(bbox):
    lon0, lat0, lon1, lat1 = bbox
    lat_c = (lat0 + lat1) / 2
    return (lon1 - lon0) * 111.32 * math.cos(math.radians(lat_c)), (lat1 - lat0) * 110.57


def validar_bbox(bbox):
    lon0, lat0, lon1, lat1 = [float(v) for v in bbox]
    if not (-180 <= lon0 < lon1 <= 180 and -90 <= lat0 < lat1 <= 90):
        raise ErrorAnalisis("El bloque no es valido.")
    ancho, alto = _km((lon0, lat0, lon1, lat1))
    if max(ancho, alto) > MAX_LADO_KM:
        raise ErrorAnalisis(f"El bloque es muy grande ({ancho:.1f} x {alto:.1f} km). El maximo es {MAX_LADO_KM} x {MAX_LADO_KM} km.")
    if min(ancho, alto) < MIN_LADO_KM:
        raise ErrorAnalisis(f"El bloque es muy chico ({ancho:.1f} x {alto:.1f} km). El minimo es {MIN_LADO_KM} km por lado.")
    return lon0, lat0, lon1, lat1


# ------------------------------------------------------------------ 1. escenas
def _epsg(item):
    e = item.properties.get("proj:epsg")
    if e:
        return int(e)
    code = item.properties.get("proj:code")
    if code:
        return int(str(code).split(":")[1])
    with rasterio.open(planetary_computer.sign(item).assets["B04"].href) as s:
        return s.crs.to_epsg()


def buscar_escenas(bbox_pad, progreso):
    catalogo = pystac_client.Client.open(URL_STAC, modifier=planetary_computer.sign_inplace)
    items = list(catalogo.search(collections=["sentinel-2-l2a"], bbox=list(bbox_pad), datetime=PERIODO,
                                 query={"eo:cloud_cover": {"lt": MAX_NUBES}}).items())
    if not items:
        raise ErrorAnalisis("No hay imagenes Sentinel-2 con pocas nubes de mayo a septiembre de 2026 para este lugar.")
    por_epsg = {}
    for it in items:
        por_epsg.setdefault(_epsg(it), []).append(it)
    epsg = max(por_epsg, key=lambda e: len(por_epsg[e]))   # se trabaja en la proyeccion con mas imagenes
    return epsg, por_epsg[epsg]


def elegir(items, region_wgs, n_por_tile):
    """Por cada tile, hasta n escenas: primero las de menos nubes de cada orbita (cubren franjas distintas)."""
    cobertura = {}
    for it in items:
        g = shape(it.geometry)
        cobertura[it.id] = g
    por_tile = {}
    for it in items:
        por_tile.setdefault(it.properties["s2:mgrs_tile"], []).append(it)
    elegidas = []
    for tile, lista in por_tile.items():
        lista.sort(key=lambda e: e.properties["eo:cloud_cover"])
        util = [e for e in lista if cobertura[e.id].intersects(region_wgs)]
        orbitas = sorted({e.properties["sat:relative_orbit"] for e in util})
        sel = []
        for orb in orbitas:
            sel += [e for e in util if e.properties["sat:relative_orbit"] == orb][:max(1, min(3, n_por_tile // len(orbitas)))]
        for e in util:
            if len(sel) >= n_por_tile:
                break
            if e not in sel:
                sel.append(e)
        elegidas += sel[:n_por_tile]
    return sorted(elegidas, key=lambda e: e.datetime)


# ------------------------------------------------------------------ 2. descarga de la parte del bloque
class Grilla:
    """Rectangulo de trabajo en metros (proyeccion UTM), alineado a multiplos de 20 m como los tiles Sentinel-2."""

    def __init__(self, epsg, bbox_pad):
        self.epsg = epsg
        self.crs = f"EPSG:{epsg}"
        tr = pyproj.Transformer.from_crs(4326, epsg, always_xy=True)
        lon0, lat0, lon1, lat1 = bbox_pad
        xs, ys = tr.transform([lon0, lon1, lon0, lon1], [lat0, lat0, lat1, lat1])
        self.X0 = float(np.floor(min(xs) / RES) * RES)
        self.X1 = float(np.ceil(max(xs) / RES) * RES)
        self.Y0 = float(np.floor(min(ys) / RES) * RES)
        self.Y1 = float(np.ceil(max(ys) / RES) * RES)
        self.ancho = int(round((self.X1 - self.X0) / RES))
        self.alto = int(round((self.Y1 - self.Y0) / RES))
        self.T = from_origin(self.X0, self.Y1, RES, RES)
        self.region = box(self.X0, self.Y0, self.X1, self.Y1)

    def ventana(self, src):
        """Parte de la grilla que cubre esta escena: (col, fila, ancho, alto) en pixeles de 20 m, o None."""
        ix0, ix1 = max(self.X0, src.bounds.left), min(self.X1, src.bounds.right)
        iy0, iy1 = max(self.Y0, src.bounds.bottom), min(self.Y1, src.bounds.top)
        if ix0 >= ix1 or iy0 >= iy1:
            return None
        c0, c1 = int(np.ceil((ix0 - self.X0) / RES)), int(np.floor((ix1 - self.X0) / RES))
        f0, f1 = int(np.ceil((self.Y1 - iy1) / RES)), int(np.floor((self.Y1 - iy0) / RES))
        if c1 <= c0 or f1 <= f0:
            return None
        return c0, f0, c1 - c0, f1 - f0

    def leer(self, href, rect, remuestreo):
        c0, f0, w, h = rect
        x_izq, y_sup = self.X0 + c0 * RES, self.Y1 - f0 * RES
        with rasterio.open(href) as src:
            t = src.transform
            v = Window(round((x_izq - t.c) / t.a), round((t.f - y_sup) / -t.e), round(w * RES / t.a), round(h * RES / -t.e))
            return src.read(1, window=v, out_shape=(h, w), resampling=remuestreo)


def _leer_con_reintentos(g, href, rect, remuestreo):
    for intento in range(3):
        try:
            return g.leer(href, rect, remuestreo)
        except Exception:  # error de red: reintentar
            if intento == 2:
                raise
            time.sleep(2)


def descargar_compuesto(g, escenas, progreso):
    """Mediana de las escenas sin nube. Devuelve bandas (6,alto,ancho), ndvi, ndwi, bsi, n_obs y datos de las escenas.

    Cada pixel guarda hasta PROF observaciones validas (en una sola pila de numeros enteros, para gastar poca memoria);
    asi un bloque grande que cruza varias escenas vecinas no necesita una pila por escena.
    """
    pila = np.full((len(BANDAS), PROF, g.alto, g.ancho), 65535, dtype="uint16")   # reflectancia x 10000; 65535 = vacio
    cnt = np.zeros((g.alto, g.ancho), dtype="uint8")
    candado, usadas, hechas = threading.Lock(), [], [0]

    def una_escena(it):
        it = planetary_computer.sign(it)
        with rasterio.open(it.assets["B04"].href) as src:
            rect = g.ventana(src)
        if rect is not None:
            base = it.properties.get("s2:processing_baseline", "04.00")
            offset = 1000 if float(base) >= 4.0 else 0     # baseline >= 04.00: los valores traen -1000 de desplazamiento
            c0, f0, w, h = rect
            nombres = BANDAS + ["SCL"]
            with ThreadPoolExecutor(max_workers=4) as pool:
                lect = list(pool.map(lambda n: _leer_con_reintentos(
                    g, it.assets[n].href, rect, Resampling.nearest if n == "SCL" else Resampling.average), nombres))
            ok = ~np.isin(lect[-1], SCL_INVALIDOS)
            for dn in lect[:-1]:
                ok &= dn != 0
            with candado:
                sub = cnt[f0:f0 + h, c0:c0 + w]
                rr, cc = np.nonzero(ok & (sub < PROF))
                slot = sub[rr, cc]
                for b, dn in enumerate(lect[:-1]):
                    v = np.clip(dn.astype("float32") - offset, 0, 15000).astype("uint16")
                    pila[b, slot, f0 + rr, c0 + cc] = v[rr, cc]
                sub[rr, cc] += 1
                usadas.append({"id": it.id, "fecha": str(it.datetime.date()), "nubes_pct": round(it.properties["eo:cloud_cover"], 1),
                               "tile": it.properties["s2:mgrs_tile"]})
        with candado:
            hechas[0] += 1
            progreso(1, hechas[0] / len(escenas), f"Escena {hechas[0]} de {len(escenas)} ({it.datetime.date()})")

    with ThreadPoolExecutor(max_workers=PARALELO_ESCENAS) as pool:
        for fut in [pool.submit(una_escena, it) for it in escenas]:
            fut.result()
    if not usadas:
        raise ErrorAnalisis("Las imagenes encontradas no cubren el bloque.")
    usadas.sort(key=lambda u: u["fecha"])
    # Mediana por pixel de cada banda (como el paso 4); observaciones validas = fotos guardadas en ese pixel
    med = []
    for b in range(len(BANDAS)):
        a = pila[b].astype("float32") / 10000.0
        a[pila[b] == 65535] = np.nan
        m, _ = nz.mediana_pila(a)
        med.append(m)
        del a
    del pila
    n_obs = cnt.astype("int16")
    sin = np.zeros((g.alto, g.ancho), dtype=bool)
    for m in med:
        sin |= np.isnan(m)
    n_obs[sin] = 0
    B2, B3, B4, B8, B11 = med[0], med[1], med[2], med[3], med[4]
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (B8 - B4) / (B8 + B4)
        ndwi = (B3 - B8) / (B3 + B8)
        bsi = ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))
    bandas = np.stack([np.where(sin, nz.NODATA, m) for m in med]).astype("float32")
    idx = [np.where(sin | ~np.isfinite(i), nz.NODATA, i).astype("float32") for i in (ndvi, ndwi, bsi)]
    return bandas, idx[0], idx[1], idx[2], n_obs, usadas


# ------------------------------------------------------------------ 3. pendiente
def pendiente(g, bbox_pad):
    """Pendiente en grados del DEM Copernicus GLO-30, interpolada a la grilla de 20 m (como el paso 4)."""
    lon0, lat0, lon1, lat1 = bbox_pad
    m = 0.01
    catalogo = pystac_client.Client.open(URL_STAC, modifier=planetary_computer.sign_inplace)
    items = list(catalogo.search(collections=["cop-dem-glo-30"], bbox=[lon0 - m, lat0 - m, lon1 + m, lat1 + m]).items())
    if not items:
        raise ErrorAnalisis("No hay datos de elevacion (DEM) para este lugar.")
    trozos = []
    for it in items:
        with rasterio.open(it.assets["data"].href) as src:
            t = src.transform
            c0 = max(0, int(np.floor((lon0 - m - t.c) / t.a)) - 1)
            c1 = min(src.width, int(np.ceil((lon1 + m - t.c) / t.a)) + 1)
            f0 = max(0, int(np.floor((t.f - (lat1 + m)) / -t.e)) - 1)
            f1 = min(src.height, int(np.ceil((t.f - (lat0 - m)) / -t.e)) + 1)
            if c1 <= c0 or f1 <= f0:
                continue
            a = src.read(1, window=Window(c0, f0, c1 - c0, f1 - f0)).astype("float32")
            if src.nodata is not None:
                a = np.where(a == src.nodata, np.nan, a)
            trozos.append((t.c + c0 * t.a, t.f + f0 * t.e, t.a, a))
    pix = trozos[0][2]
    lon_min = min(x for x, _, _, _ in trozos)
    lat_max = max(y for _, y, _, _ in trozos)
    lon_max = max(x + pix * a.shape[1] for x, _, _, a in trozos)
    lat_min = min(y - pix * a.shape[0] for _, y, _, a in trozos)
    dem = np.full((int(round((lat_max - lat_min) / pix)), int(round((lon_max - lon_min) / pix))), np.nan, "float32")
    for x, y, _, a in trozos:
        c, f = int(round((x - lon_min) / pix)), int(round((lat_max - y) / pix))
        dem[f:f + a.shape[0], c:c + a.shape[1]] = a
    tr = pyproj.Transformer.from_crs(g.epsg, 4326, always_xy=True)
    alto, ancho = g.alto + 2, g.ancho + 2
    xs = g.X0 - RES / 2 + RES * np.arange(ancho)
    ys = g.Y1 + RES / 2 - RES * np.arange(alto)
    gx, gy = np.meshgrid(xs, ys)
    lon, lat = tr.transform(gx, gy)
    z = map_coordinates(dem, [(lat_max - lat) / pix - 0.5, (lon - lon_min) / pix - 0.5], order=1, mode="nearest").astype("float32")
    dz_f, dz_c = np.gradient(z, RES, RES)
    p = np.degrees(np.arctan(np.hypot(dz_f, dz_c)))[1:-1, 1:-1].astype("float32")
    p[~np.isfinite(p)] = nz.NODATA
    return p


# ------------------------------------------------------------------ 6. rios y poblados
def _osm_en_vivo(bbox):
    lon0, lat0, lon1, lat1 = bbox
    consulta = (f'[out:json][timeout:40];(way["waterway"~"^(river|stream|canal|drain)$"]({lat0},{lon0},{lat1},{lon1});'
                f'node["place"~"^(city|town|village|hamlet)$"]({lat0},{lon0},{lat1},{lon1}););out geom;')
    for url in OVERPASS:
        try:
            r = requests.post(url, data={"data": consulta}, headers={"User-Agent": "ml-detector-zonas/0.1 (consulta de datos abiertos)"},
                              timeout=45)
            r.raise_for_status()
            lineas, puntos = [], []
            for el in r.json()["elements"]:
                tags = el.get("tags", {})
                if el["type"] == "way" and len(el.get("geometry", [])) >= 2:
                    lineas.append(LineString([(p["lon"], p["lat"]) for p in el["geometry"]]))
                elif el["type"] == "node" and "place" in tags:
                    puntos.append((tags.get("name", ""), Point(el["lon"], el["lat"])))
            return lineas, puntos
        except Exception:  # noqa: BLE001  (se prueba el servidor siguiente)
            continue
    return None


def distancias(gdf, g, bbox):
    """Distancia (m, desde el borde de la zona) al cauce y al poblado mas cercanos. Devuelve listas o None."""
    pad = [bbox[0] - 0.05, bbox[1] - 0.05, bbox[2] + 0.05, bbox[3] + 0.05]
    cauces = lugares = None
    # El archivo local (paso 7) solo sirve si cubre el bloque con holgura: es la zona piloto
    O, S, E, N = -68.42, -15.90, -67.20, -15.00
    if REF.exists() and bbox[0] >= O + 0.05 and bbox[2] <= E - 0.05 and bbox[1] >= S + 0.05 and bbox[3] <= N - 0.05:
        # (el archivo esta en metros; se lee completo, pesa poco, y se filtra despues)
        o = gpd.read_file(REF, layer="cauces")
        l = gpd.read_file(REF, layer="poblados_osm")
        cauces = o.to_crs(g.crs).geometry.union_all() if len(o) else None
        lugares = [(n, p) for n, p in zip(l["nombre"].fillna(""), l.to_crs(g.crs).geometry)]
    else:
        osm = _osm_en_vivo(pad)
        if osm is None:
            return None
        tr = pyproj.Transformer.from_crs(4326, g.epsg, always_xy=True)
        from shapely.ops import transform as sh_tr
        lineas, puntos = osm
        cauces = gpd.GeoSeries([sh_tr(tr.transform, ln) for ln in lineas]).union_all() if lineas else None
        lugares = [(n, sh_tr(tr.transform, p)) for n, p in puntos]
    d_rio = [int(round(z.distance(cauces) / 10) * 10) if cauces is not None else None for z in gdf.geometry]
    d_pob, n_pob = [], []
    for z in gdf.geometry:
        if lugares:
            dd = [z.distance(p) for _, p in lugares]
            i = int(np.argmin(dd))
            d_pob.append(int(round(dd[i] / 10) * 10))
            n_pob.append(lugares[i][0] or "(sin nombre en OSM)")
        else:
            d_pob.append(None)
            n_pob.append("")
    return d_rio, d_pob, n_pob


def preparar_bloque(bbox, progreso=lambda etapa, frac, msg: None):
    """Etapas 1 a 3: busca las escenas, baja el compuesto del bloque y calcula la pendiente (sin correr el modelo)."""
    pad = MARGEN_M / 111_000
    bbox_pad = (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
    progreso(0, 0.1, "Consultando el catalogo de imagenes")
    epsg, items = buscar_escenas(bbox_pad, progreso)
    g = Grilla(epsg, bbox_pad)
    # La regla de zonas pide mediana de 7+ fotos validas por pixel (nucleo_zonas.MIN_OBS_MEDIANA): hacen falta bastantes escenas
    # (12 por tile, como en el piloto). El costo lo fija el area del bloque, no el numero de tiles.
    escenas = elegir(items, box(*bbox_pad), 12)
    if not escenas:
        raise ErrorAnalisis("No se encontraron imagenes que cubran el bloque.")
    progreso(0, 1.0, f"{len(escenas)} imagenes elegidas de {len(items)} disponibles")
    bandas, ndvi, ndwi, bsi, n_obs, usadas = descargar_compuesto(g, escenas, progreso)
    progreso(2, 0.2, "Calculando la pendiente del terreno")
    pend = pendiente(g, bbox_pad)
    progreso(2, 1.0, "Indices y pendiente listos")
    return g, bandas, ndvi, ndwi, bsi, n_obs, usadas, pend, items, bbox_pad


# ------------------------------------------------------------------ imagenes del bloque (para la segunda opinion y el reentrenamiento)
def _estirar(a, lo=None, hi=None):
    """Estira una banda a 0-255 (2% a 98% de los pixeles validos) para que se vea bien en pantalla."""
    ok = np.isfinite(a) & (a != nz.NODATA)
    if lo is None:
        lo, hi = np.percentile(a[ok], [2, 98]) if ok.any() else (0.0, 1.0)
    return np.clip((np.where(ok, a, lo) - lo) / max(hi - lo, 1e-6), 0, 1)


def guardar_imagenes(clave, g, bandas, ndvi, ndwi, bsi, pend, n_obs):
    """Guarda el color natural, un falso color (infrarrojo y SWIR) y el compuesto completo (para reentrenar)."""
    from PIL import Image
    B2, B3, B4, B8, B11 = bandas[0], bandas[1], bandas[2], bandas[3], bandas[4]
    natural = np.stack([_estirar(B4, 0.02, 0.28), _estirar(B3, 0.02, 0.28), _estirar(B2, 0.02, 0.28)], -1) ** 0.75   # gamma: mas claro en pantalla
    falso = np.stack([_estirar(B11, 0.03, 0.40), _estirar(B8, 0.05, 0.50), _estirar(B4, 0.02, 0.28)], -1)
    for nombre, a in (("natural", natural), ("falso", falso)):
        Image.fromarray((a * 255).astype("uint8")).save(SALIDA / f"{clave}_{nombre}.png", optimize=True)
    np.savez_compressed(SALIDA / f"{clave}_compuesto.npz", bandas=bandas.astype("float16"), ndvi=ndvi.astype("float16"), ndwi=ndwi.astype("float16"),
                        bsi=bsi.astype("float16"), pend=pend.astype("float16"), n_obs=n_obs.astype("uint8"),
                        T=np.array(g.T)[:6], epsg=np.array([g.epsg]))


# ------------------------------------------------------------------ flujo completo
def analizar(bbox, progreso=lambda etapa, frac, msg: None, usar_cache=True, sensibilidad="normal"):
    """Analiza un bloque (lon_oeste, lat_sur, lon_este, lat_norte). Devuelve un dict listo para el visor.

    sensibilidad: "normal" (puntaje minimo 0.5, como la lista del piloto) o "alta" (0.3: marca mas terreno, con mas falsos positivos).
    """
    if sensibilidad not in UMBRALES:
        raise ErrorAnalisis("Sensibilidad no valida.")
    umbral = UMBRALES[sensibilidad]
    t0 = time.time()
    bbox = validar_bbox(bbox)
    SALIDA.mkdir(parents=True, exist_ok=True)
    clave = hashlib.sha1(json.dumps([[round(v, 4) for v in bbox], sensibilidad, ma.ruta().name]).encode()).hexdigest()[:12]
    clave_img = hashlib.sha1(json.dumps([round(v, 4) for v in bbox]).encode()).hexdigest()[:12]   # las imagenes no dependen de la sensibilidad
    ruta_cache = SALIDA / f"{clave}.json"
    if usar_cache and ruta_cache.exists():
        r = json.loads(ruta_cache.read_text(encoding="utf-8"))
        r["resumen"]["desde_cache"] = True
        if not (SALIDA / f"{clave_img}_compuesto.npz").exists():    # resultado traido del respaldo: faltan las imagenes (no van al repo); se vuelven a bajar
            g, bandas, ndvi, ndwi, bsi, n_obs, usadas, pend, items, bbox_pad = preparar_bloque(bbox, progreso)
            guardar_imagenes(clave_img, g, bandas, ndvi, ndwi, bsi, pend, n_obs)
        return r
    modelo = cargar_modelo()
    g, bandas, ndvi, ndwi, bsi, n_obs, usadas, pend, items, bbox_pad = preparar_bloque(bbox, progreso)

    progreso(3, 0.2, "Puntuando cada pixel con el modelo")
    datos, valido = nz.variables_y_validez(bandas, ndvi, ndwi, bsi, pend, n_obs, con_contexto=modelo.num_feature() > len(nz.VARIABLES))
    prob = nz.puntuar(modelo, datos, valido)
    progreso(3, 1.0, f"{int(valido.sum()):,} pixeles puntuados")
    guardar_imagenes(clave_img, g, bandas, ndvi, ndwi, bsi, pend, n_obs)

    progreso(4, 0.2, "Aplicando los filtros contra falsos positivos")
    cand = gpd.read_file(RAIZ / "04_DATOS" / "etiquetas" / "candidatos.gpkg", layer="candidatos")
    dup = cand["duplicado_de"].fillna(0).astype(int) != 0
    ent = cand[cand.decision.isin(["aceptar", "descartar"]) & ~dup].to_crs(g.crs)
    acp = ent[ent.decision == "aceptar"]
    ent = ent[ent.intersects(g.region)]
    acp = acp[acp.intersects(g.region)]
    excluir = rasterize([(x, 1) for x in ent.geometry], out_shape=prob.shape, transform=g.T, fill=0, dtype="uint8").astype(bool) if len(ent) else None
    aceptadas = rasterize([(x, 1) for x in acp.geometry], out_shape=prob.shape, transform=g.T, fill=0, dtype="uint8").astype(bool) if len(acp) else None
    # Dentro del piloto: las mismas reglas estrictas de la lista. Fuera: las reglas de fotos y de entorno solo MARCAN la zona
    # (confianza "parcial"), porque fueron pensadas para el bosque del norte de La Paz y en otros lugares borrarian
    # areas mineras reales (por ejemplo, el interior de una gran area minera no esta "rodeado de bosque").
    aoi = gpd.read_file(RAIZ / "04_DATOS" / "zona_piloto.gpkg", layer="aoi_wgs84").geometry.union_all()
    b_wgs = box(*bbox)
    frac_piloto = float(b_wgs.intersection(aoi).area / b_wgs.area)
    estricto = frac_piloto >= 0.5
    gdf, info = nz.extraer_zonas(prob, ndvi, ndwi, n_obs.astype("float32"), g.T, g.crs, excluir=excluir, aceptadas=aceptadas,
                                 umbral=umbral, **({} if estricto else nz.RELAJADO))
    info["modo"] = "estricto (zona piloto)" if estricto else "relajado (fuera del piloto: reglas marcadas, no eliminadas)"
    if os.environ.get("G4G_DEBUG"):   # solo para revisar un bloque a mano (guarda las capas calculadas)
        np.savez_compressed(SALIDA / f"{clave}_debug.npz", bandas=bandas, ndvi=ndvi, ndwi=ndwi, n_obs=n_obs, prob=prob, pend=pend, T=np.array(g.T)[:6])

    # Solo lo que cae dentro del bloque dibujado: las zonas que cruzan el borde se RECORTAN (el margen de 1 km es solo contexto)
    caja = gpd.GeoSeries([box(*bbox)], crs=4326).to_crs(g.crs).iloc[0]
    if len(gdf):
        gdf = gdf[gdf.intersects(caja)].copy()
        gdf["geometry"] = gdf.geometry.intersection(caja)
        gdf = gdf[~gdf.geometry.is_empty]
        gdf["area_ha"] = (gdf.geometry.area / 10_000).round(1)
        gdf = gdf[gdf.area_ha >= nz.MIN_HA]          # un recorte de menos de 5 ha ya no es una zona
        gdf = gdf.sort_values("puntaje", ascending=False).head(MAX_ZONAS).reset_index(drop=True)
    progreso(4, 1.0, f"{len(gdf)} zonas")

    progreso(5, 0.2, "Buscando rios y poblados cercanos")
    dist = distancias(gdf, g, bbox) if len(gdf) else None
    progreso(5, 1.0, "Distancias listas" if dist or not len(gdf) else "Sin datos de rios y poblados (sin internet?)")

    # Cobertura: que parte del bloque dibujado tiene datos utilizables
    c = rasterize([(caja, 1)], out_shape=prob.shape, transform=g.T, fill=0, dtype="uint8").astype(bool)
    cobertura = float(valido[c].mean()) if c.any() else 0.0

    wgs = gdf.to_crs(4326)
    feats = []
    for i, (fila, w) in enumerate(zip(gdf.itertuples(), wgs.geometry)):
        rp = w.representative_point()
        feats.append({"type": "Feature", "geometry": mapping(w),
                      "properties": {"id": f"B{clave[:4]}-{i + 1:03d}", "clave": clave, "area_ha": float(fila.area_ha), "puntaje_modelo": int(round(fila.puntaje * 100)),
                                     "dist_rio_m": dist[0][i] if dist else None, "dist_poblado_m": dist[1][i] if dist else None,
                                     "poblado_cercano": dist[2][i] if dist else "", "lat": round(rp.y, 6), "lng": round(rp.x, 6),
                                     "ndvi_mediano": float(fila.ndvi_mediano), "obs_mediana": float(fila.obs_mediana),
                                     "confianza": "completa" if (fila.fotos_ok and fila.entorno_ok) else "parcial",
                                     "avisos_zona": ([] if fila.fotos_ok else [f"Pocas fotos limpias (mediana {fila.obs_mediana:g} de 7 recomendadas): puede haber restos de nube o sombra."])
                                                    + ([] if fila.entorno_ok else [f"El entorno tiene poca vegetacion (NDVI {fila.ndvi_entorno:g}): puede ser el interior de una gran area minera, o roca y suelo natural. Compara con la imagen."]),
                                     "estado_verificacion": "por verificar en campo; registro AJAM aun no consultado",
                                     "nota": NOTA}})
    ancho_km, alto_km = _km(bbox)
    ha = round(float(sum(f["properties"]["area_ha"] for f in feats)), 1)
    avisos = []
    if frac_piloto < 0.5:
        avisos.append("Este bloque esta fuera de la zona donde se entreno el modelo (norte de La Paz). No fue validado aqui: puede "
                      "confundir suelo agricola, roca, arena de rio u otro terreno con actividad minera.")
    if cobertura < 0.7:
        avisos.append(f"Solo {cobertura * 100:.0f}% del bloque tiene imagen utilizable (nubes o sin datos): el resultado esta incompleto.")
    if len(usadas) < 3:
        avisos.append("Se usaron pocas imagenes; el resultado puede tener restos de nube.")
    if sensibilidad == "alta":
        avisos.append("Sensibilidad alta: marca mas terreno removido, pero tambien mas falsos positivos. Revisa cada zona.")
    if info.get("zonas_5ha", 0) > 0 and info.get("zonas_finales", 0) == 0:
        avisos.append(f"El modelo marco {info['zonas_5ha']} manchas de mas de 5 ha, pero los filtros contra falsos positivos las descartaron "
                      f"todas (fotos validas, vegetacion del entorno o color). Este lugar es distinto al de entrenamiento y los filtros "
                      f"pueden estar siendo demasiado estrictos para este tipo de terreno.")
    if dist is None and len(feats):
        avisos.append("No se pudieron calcular las distancias a rios y poblados (sin conexion al servicio de OpenStreetMap).")
    if len(feats) == 0:
        veredicto = "No se encontraron zonas con parecido a actividad minera en este bloque, con la imagen de mayo a septiembre de 2026."
    else:
        parc = sum(1 for f in feats if f["properties"]["confianza"] == "parcial")
        veredicto = (f"Se encontraron {len(feats)} zonas con parecido a posible actividad minera ({ha} ha en total)"
                     + (f"; {parc} con confianza parcial (ver avisos de cada zona)" if parc else "")
                     + ". Son zonas para revisar, no detecciones confirmadas.")
    resultado = {
        "bbox": list(bbox),
        "zonas": {"type": "FeatureCollection", "features": feats},
        "resumen": {"clave": clave, "clave_img": clave_img, "origen_m": [g.X0, g.Y1], "epsg_m": g.epsg, "veredicto": veredicto, "n_zonas": len(feats), "area_total_ha": ha, "bloque_km": [round(ancho_km, 1), round(alto_km, 1)],
                    "bloque_km2": round(ancho_km * alto_km, 1), "cobertura_imagen_pct": round(cobertura * 100),
                    "dentro_zona_entrenamiento_pct": round(frac_piloto * 100), "imagenes_usadas": usadas,
                    "pixeles_puntuados": int(valido.sum()), "filtros": info, "modo": info["modo"], "sensibilidad": sensibilidad, "umbral": umbral, "epsg": g.epsg, "modelo": ma.version(),
                    "segundos": round(time.time() - t0, 1), "periodo": PERIODO, "avisos": avisos, "desde_cache": False},
    }
    ruta_cache.write_text(json.dumps(resultado, ensure_ascii=False), encoding="utf-8")
    return resultado


if __name__ == "__main__":
    if len(sys.argv) not in (5, 6):
        raise SystemExit(__doc__)
    sens = sys.argv[5] if len(sys.argv) > 5 else "normal"
    r = analizar([float(v) for v in sys.argv[1:5]], lambda e, f, m: print(f"  [{ETAPAS[e]}] {f * 100:3.0f}% {m}", flush=True), usar_cache=False, sensibilidad=sens)
    print(json.dumps(r["resumen"], indent=2, ensure_ascii=False))
    for f in r["zonas"]["features"]:
        p = f["properties"]
        print(p["id"], p["area_ha"], "ha  puntaje", p["puntaje_modelo"], " rio", p["dist_rio_m"], "m  poblado", p["dist_poblado_m"], p["poblado_cercano"])
