"""
Paso 3 - Vista previa en color natural de Sentinel-2 (epoca seca 2026) para mirar la zona.

Que hace:
  1. Consulta el catalogo STAC de Microsoft Planetary Computer (gratis, sin credenciales).
  2. Para cada "tile" (cuadro de 110 km del satelite) que cubre la zona, elige la escena
     de mayo a septiembre de 2026 con MENOS nubes.
  3. Baja solo lo necesario (los archivos son COG: se puede leer por partes y a menor
     resolucion, sin bajar la imagen entera).
  4. Guarda un mosaico de toda la zona a 40 m y un recorte de detalle a 10 m por pueblo.

Es una vista previa para MIRAR. No es el compuesto final (eso es la tarea T-003).

Como correrlo (entorno g4g-ml):
  python 05_CODIGO\\paso3_previa_sentinel.py
"""
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import planetary_computer
import pystac_client
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.windows import Window

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "04_DATOS" / "imagenes" / "previa"
SALIDA.mkdir(parents=True, exist_ok=True)

PERIODO = "2026-05-01/2026-09-30"   # epoca menos lluviosa
MAX_NUBES = 30                      # % maximo de nubes aceptado al buscar
LADO_DETALLE_M = 16_000             # recorte de 16 x 16 km alrededor de cada pueblo

# Zona piloto en UTM 19S (metros) y en grados (para buscar en el catalogo)
aoi_utm = gpd.read_file(RAIZ / "04_DATOS" / "zona_piloto.gpkg", layer="aoi_utm19s")
aoi_wgs = gpd.read_file(RAIZ / "04_DATOS" / "zona_piloto.gpkg", layer="aoi_wgs84")
bounds_utm = tuple(aoi_utm.total_bounds)           # (xmin, ymin, xmax, ymax) en metros
bbox_wgs = list(aoi_wgs.total_bounds)

# 1. Buscar escenas
catalogo = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,  # "firma" los enlaces para poder leerlos
)
escenas = list(catalogo.search(
    collections=["sentinel-2-l2a"], bbox=bbox_wgs, datetime=PERIODO,
    query={"eo:cloud_cover": {"lt": MAX_NUBES}},
).items())

# 2. Quedarse con la escena menos nublada de cada tile
mejor = {}
for e in escenas:
    tile = e.properties["s2:mgrs_tile"]
    if tile not in mejor or e.properties["eo:cloud_cover"] < mejor[tile].properties["eo:cloud_cover"]:
        mejor[tile] = e
print("Escenas elegidas:")
registro = []
for tile, e in sorted(mejor.items()):
    print(f"  {tile}  {e.datetime.date()}  nubes {e.properties['eo:cloud_cover']:.1f}%  {e.id}")
    registro.append({"tile": tile, "fecha": str(e.datetime.date()),
                     "nubes_pct": round(e.properties["eo:cloud_cover"], 1), "id": e.id})


def mosaico(bounds, res, nombre):
    """Une las escenas elegidas en un solo raster RGB recortado a 'bounds' (metros).

    Nota: no se usa rasterio.merge porque en este equipo falla con un error de librerias
    (0xc06d007f). Se hace la union a mano: los pixeles Sentinel-2 estan alineados a una
    grilla de 10 m, asi que basta con calcular que "ventana" de cada escena corresponde
    al cuadro que queremos y leerla ya reducida a 'res' metros.
    """
    # Ajustar los limites a multiplos de 'res' para que todo calce con la grilla de 10 m
    x0 = np.floor(bounds[0] / res) * res
    y1 = np.ceil(bounds[3] / res) * res
    x1 = np.ceil(bounds[2] / res) * res
    y0 = np.floor(bounds[1] / res) * res
    ancho, alto = int((x1 - x0) / res), int((y1 - y0) / res)
    salida = np.zeros((3, alto, ancho), dtype="uint8")

    for e in mejor.values():
        with rasterio.open(e.assets["visual"].href) as src:  # "visual" = RGB de 8 bits
            t = src.transform  # t.c = x del borde izquierdo, t.f = y del borde superior
            # Parte del cuadro que cae dentro de esta escena (en metros)
            ix0, ix1 = max(x0, src.bounds.left), min(x1, src.bounds.right)
            iy0, iy1 = max(y0, src.bounds.bottom), min(y1, src.bounds.top)
            if ix0 >= ix1 or iy0 >= iy1:
                continue  # esta escena no toca el cuadro
            ix0 = np.ceil((ix0 - x0) / res) * res + x0     # alinear a la grilla de salida
            iy1 = y1 - np.ceil((y1 - iy1) / res) * res
            ix1 = x0 + np.floor((ix1 - x0) / res) * res
            iy0 = y1 - np.floor((y1 - iy0) / res) * res
            if ix0 >= ix1 or iy0 >= iy1:
                continue
            # Columnas y filas de salida (destino) y de la escena (origen)
            c_dst, f_dst = int(round((ix0 - x0) / res)), int(round((y1 - iy1) / res))
            w_dst, h_dst = int(round((ix1 - ix0) / res)), int(round((iy1 - iy0) / res))
            ventana = Window(round((ix0 - t.c) / t.a), round((t.f - iy1) / -t.e),
                             round((ix1 - ix0) / t.a), round((iy1 - iy0) / -t.e))
            # Leer ya reducido a la resolucion pedida (promediando pixeles vecinos)
            trozo = src.read([1, 2, 3], window=ventana, out_shape=(3, h_dst, w_dst),
                             resampling=Resampling.average)
            destino = salida[:, f_dst:f_dst + h_dst, c_dst:c_dst + w_dst]
            vacio = destino.sum(axis=0) == 0       # donde aun no hay datos
            destino[:, vacio] = trozo[:, vacio]    # rellenar solo los huecos (no pisar lo ya puesto)

    transf = from_origin(x0, y1, res, res)
    perfil = dict(driver="GTiff", height=alto, width=ancho, count=3, dtype="uint8",
                  crs="EPSG:32719", transform=transf, compress="deflate", nodata=0)
    ruta = SALIDA / f"{nombre}.tif"
    with rasterio.open(ruta, "w", **perfil) as dst:
        dst.write(salida)
    print(f"  guardado {ruta.name}: {ancho} x {alto} px a {res} m", flush=True)
    return ruta


# 3. Mosaico de toda la zona a 40 m
print("Mosaico de la zona completa:")
mosaico(bounds_utm, 40, "previa_zona_40m")

# 4. Recortes de detalle (10 m) alrededor de cada pueblo
print("Recortes de detalle:")
pueblos = gpd.read_file(RAIZ / "04_DATOS" / "referencia_poblados.gpkg", layer="poblados")
for _, p in pueblos.iterrows():
    x, y, m = p.geometry.x, p.geometry.y, LADO_DETALLE_M / 2
    mosaico((x - m, y - m, x + m, y + m), 10, f"detalle_{p['nombre'].lower()}_10m")

(SALIDA / "escenas_usadas.json").write_text(
    json.dumps({"periodo": PERIODO, "fuente": "Microsoft Planetary Computer, sentinel-2-l2a",
                "escenas": registro}, indent=2), encoding="utf-8")
print("Listo.")
