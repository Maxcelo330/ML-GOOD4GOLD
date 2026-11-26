"""
Recortes de imagen de una zona para la ventana de comparacion del visor (antes / despues).

Que hace: de un analisis de bloque ya guardado toma una zona y arma imagenes PNG de su entorno ya reproyectadas a
latitud/longitud (norte arriba), para ponerlas sobre el mapa en el lugar exacto:
  - natural : color natural de Sentinel-2 (mediana mayo-septiembre 2026): lo que ve el modelo
  - falso   : falso color infrarrojo/SWIR (el suelo removido se ve rosado)
  - puntaje : mapa de calor del puntaje del modelo (cada cuadro de 20 m): como "piensa" el modelo
Los recortes se guardan en 04_DATOS/analisis_bloques/recortes/ para no recalcularlos.

La capa "antes" del visor NO sale de aca: son imagenes historicas de Esri Wayback que el navegador baja directamente.
"""
import json
import re
from pathlib import Path

import numpy as np
import pyproj
from affine import Affine
from PIL import Image
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject
from shapely.geometry import shape
from shapely.ops import transform as sh_transform

import analisis_bloque as ab
import modelo_activo as ma
import nucleo_zonas as nz

SALIDA = ab.SALIDA
CACHE = SALIDA / "recortes"
CAPAS = ("natural", "falso", "puntaje")
ALTO_PX = 720          # alto del recorte reproyectado
ASPECTOS = (0.6, 1.0, 2.0)   # ancho / alto: el visor pide el que se parece a su pantalla (celular vertical, cuadrada, escritorio ancho)
MARGEN_PX = 40         # contexto extra (800 m) para calcular las variables de entorno del puntaje


class ErrorRecorte(Exception):
    """Error que se le explica a la persona."""


def _zona(clave, id_zona):
    if not re.fullmatch(r"[0-9a-f]{12}", clave or "") or not re.fullmatch(r"[A-Za-z0-9\-]{3,20}", id_zona or ""):
        raise ErrorRecorte("Zona no valida.")
    ruta = SALIDA / f"{clave}.json"
    if not ruta.exists():
        raise ErrorRecorte("No se encuentra el analisis de ese bloque.")
    res = json.loads(ruta.read_text(encoding="utf-8"))
    f = next((x for x in res["zonas"]["features"] if x["properties"]["id"] == id_zona), None)
    if f is None:
        raise ErrorRecorte("No se encuentra esa zona.")
    return res["resumen"], shape(f["geometry"])


def aspecto_valido(a):
    try:
        return min(ASPECTOS, key=lambda x: abs(x - float(a)))
    except (TypeError, ValueError):
        return 2.0


def ventana(geom, aspecto=2.0, pad_rel=0.8, pad_min_m=450):
    """(oeste, sur, este, norte) alrededor de la zona, con contexto. Ancho = aspecto veces el alto (en metros)."""
    w, s, e, n = geom.bounds
    lat = (s + n) / 2
    kx, ky = 111_320 * np.cos(np.radians(lat)), 110_570
    lado = max((e - w) * kx, (n - s) * ky)
    lado = lado + 2 * max(pad_rel * lado, pad_min_m)
    cx, cy = (w + e) / 2, (s + n) / 2
    return (cx - aspecto * lado / 2 / kx, cy - lado / 2 / ky, cx + aspecto * lado / 2 / kx, cy + lado / 2 / ky)


def info(clave, id_zona, aspecto=2.0):
    """Datos para el visor: donde poner la imagen y que capas hay."""
    res, geom = _zona(clave, id_zona)
    w, s, e, n = ventana(geom, aspecto_valido(aspecto))
    clave_img = res["clave_img"]
    capas = [c for c in CAPAS if c == "puntaje" and (SALIDA / f"{clave_img}_compuesto.npz").exists()
             or c != "puntaje" and (SALIDA / f"{clave_img}_{c}.png").exists()]
    return {"bounds": [[s, w], [n, e]], "capas": capas, "modelo": res.get("modelo") or "v2"}


def _a_float32(a):
    a = np.asarray(a, "float32")
    a[a < -9000] = nz.NODATA      # NODATA (-9999) queda como -10000 al guardarse en float16
    return a


def _reproyectar(canales, T, epsg, destino_T, resample, ancho):
    """Lista de capas 2D (en la rejilla UTM del bloque) -> arreglo (ALTO_PX, ancho, n) en lat/lon."""
    salida = []
    for c in canales:
        dst = np.zeros((ALTO_PX, ancho), c.dtype)
        reproject(c, dst, src_transform=T, src_crs=CRS.from_epsg(epsg), dst_transform=destino_T, dst_crs=CRS.from_epsg(4326),
                  resampling=resample)
        salida.append(dst)
    return np.stack(salida, -1)


def _puntaje_rgba(res, caja_px, T):
    """Mapa de calor del puntaje del modelo sobre un recorte del compuesto (en la rejilla UTM)."""
    z = np.load(SALIDA / f"{res['clave_img']}_compuesto.npz", allow_pickle=False)
    c0, f0, c1, f1 = caja_px
    sl = (slice(f0, f1), slice(c0, c1))
    bandas = _a_float32(z["bandas"][(slice(None),) + sl])
    ndvi, ndwi, bsi, pend = (_a_float32(z[k][sl]) for k in ("ndvi", "ndwi", "bsi", "pend"))
    n_obs = z["n_obs"][sl].astype("int16")
    modelo = ab.cargar_modelo()
    datos, valido = nz.variables_y_validez(bandas, ndvi, ndwi, bsi, pend, n_obs, con_contexto=modelo.num_feature() > len(nz.VARIABLES))
    p = nz.puntuar(modelo, datos, valido)
    ok = p != nz.NODATA
    rgba = np.zeros(p.shape + (4,), "uint8")
    # amarillo (0.3) -> naranja (0.5) -> rojo (1.0); por debajo de 0.3 transparente
    t = np.clip((p - 0.3) / 0.7, 0, 1)
    rgba[..., 0] = 255
    rgba[..., 1] = (210 - 190 * t).astype("uint8")
    rgba[..., 2] = (40 - 40 * t).astype("uint8")
    rgba[..., 3] = np.where(ok & (p >= 0.3), 120 + 100 * t, 0).astype("uint8")
    return rgba


def recorte_png(clave, id_zona, capa, aspecto=2.0):
    """Ruta del PNG (RGBA, lat/lon, norte arriba) de la capa pedida para la zona. Lo crea si no existe."""
    if capa not in CAPAS:
        raise ErrorRecorte("Capa no valida.")
    res, geom = _zona(clave, id_zona)
    asp = aspecto_valido(aspecto)
    ancho = int(ALTO_PX * asp)
    CACHE.mkdir(parents=True, exist_ok=True)
    ver = (res.get("modelo") or "v2") if capa == "puntaje" else "img"
    destino = CACHE / f"{clave}_{id_zona}_{capa}_{ver}_a{int(asp * 10)}.png"
    if destino.exists():
        return destino
    w, s, e, n = ventana(geom, asp)
    destino_T = from_bounds(w, s, e, n, ancho, ALTO_PX)
    epsg = int(res["epsg_m"])
    x0, y1 = res["origen_m"]
    T = Affine(ab.RES, 0, x0, 0, -ab.RES, y1)
    if capa == "puntaje":
        arch = SALIDA / f"{res['clave_img']}_compuesto.npz"
        if not arch.exists():
            raise ErrorRecorte("No esta guardada la imagen de este bloque. Vuelve a analizarlo.")
        h, wd = np.load(arch)["n_obs"].shape
        tr = pyproj.Transformer.from_crs(4326, epsg, always_xy=True)
        xs, ys = zip(*[tr.transform(x, y) for x, y in ((w, s), (w, n), (e, s), (e, n))])
        c0 = int(max(0, (min(xs) - x0) // ab.RES - MARGEN_PX)); c1 = int(min(wd, (max(xs) - x0) // ab.RES + MARGEN_PX + 1))
        f0 = int(max(0, (y1 - max(ys)) // ab.RES - MARGEN_PX)); f1 = int(min(h, (y1 - min(ys)) // ab.RES + MARGEN_PX + 1))
        if c1 - c0 < 10 or f1 - f0 < 10:
            raise ErrorRecorte("La zona cae fuera de la imagen guardada.")
        rgba = _puntaje_rgba(res, (c0, f0, c1, f1), T)
        Tc = T * Affine.translation(c0, f0)
        img = _reproyectar([np.ascontiguousarray(rgba[..., i]) for i in range(4)], Tc, epsg, destino_T, Resampling.nearest, ancho)
    else:
        origen = SALIDA / f"{res['clave_img']}_{capa}.png"
        if not origen.exists():
            raise ErrorRecorte("No esta guardada la imagen de este bloque. Vuelve a analizarlo.")
        rgb = np.array(Image.open(origen).convert("RGB"))
        uno = np.full(rgb.shape[:2], 255, "uint8")
        img = _reproyectar([np.ascontiguousarray(rgb[..., i]) for i in range(3)] + [uno], T, epsg, destino_T, Resampling.bilinear, ancho)
    Image.fromarray(img, "RGBA").save(destino, optimize=True)
    return destino
