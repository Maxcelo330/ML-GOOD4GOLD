"""
Paso 2 - Crear la zona piloto (AOI = "Area Of Interest", area de interes).

Que hace este script:
  1. Define un rectangulo con coordenadas de latitud/longitud (grados).
  2. Lo guarda en un GeoPackage (.gpkg), el formato abierto que QGIS lee directo.
  3. Guarda dos versiones del mismo rectangulo:
       - EPSG:4326 (WGS84): grados. Es el "idioma comun" para intercambiar datos.
       - EPSG:32719 (UTM zona 19 Sur): metros. Sirve para medir distancias y areas.

Como correrlo (en "Anaconda Prompt", estando dentro de la carpeta del repo ML-GOOD4GOLD):
  conda activate g4g-ml
  python 05_CODIGO\\paso2_zona_piloto.py
"""
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

# Carpeta raiz del proyecto: la que contiene a 05_CODIGO.
# __file__ es este script; parents[0] seria 05_CODIGO y parents[1] es la raiz.
RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "04_DATOS" / "zona_piloto.gpkg"

# Limites de la zona piloto: norte de La Paz (Tipuani, Mapiri, Teoponte, Guanay).
# Ampliado al oeste el 2026-11-24 (V-005): con -68.2 el pueblo de Mapiri y el tramo
# minero de su rio quedaban fuera. Ahora llega a -68.42 (~13.000 km2).
# OJO: ya NO coincide con el recuadro de la hidrografia del prototipo web (hidro-zona.js).
LNG_MIN, LNG_MAX = -68.42, -67.2  # longitud: oeste (-) / este
LAT_MIN, LAT_MAX = -15.9, -15.0   # latitud: sur (-) / norte

# box(xmin, ymin, xmax, ymax): x = longitud, y = latitud
rectangulo = box(LNG_MIN, LAT_MIN, LNG_MAX, LAT_MAX)

aoi_wgs84 = gpd.GeoDataFrame(
    {"nombre": ["Zona piloto norte de La Paz"]},
    geometry=[rectangulo],
    crs="EPSG:4326",
)

# Reproyectar a metros (UTM 19S) para poder medir el area.
# Nota: al pasar de grados a metros, el rectangulo queda un poco inclinado
# (la Tierra es curva), asi que el tamano que se imprime abajo es aproximado.
aoi_utm = aoi_wgs84.to_crs("EPSG:32719")
area_km2 = aoi_utm.geometry.area.iloc[0] / 1_000_000
aoi_wgs84["area_km2"] = round(area_km2, 1)
aoi_utm["area_km2"] = round(area_km2, 1)

SALIDA.parent.mkdir(parents=True, exist_ok=True)
aoi_wgs84.to_file(SALIDA, layer="aoi_wgs84", driver="GPKG")
aoi_utm.to_file(SALIDA, layer="aoi_utm19s", driver="GPKG")

ancho_km = (aoi_utm.total_bounds[2] - aoi_utm.total_bounds[0]) / 1000
alto_km = (aoi_utm.total_bounds[3] - aoi_utm.total_bounds[1]) / 1000
print(f"Guardado: {SALIDA}")
print(f"Tamano aproximado: {ancho_km:.0f} km x {alto_km:.0f} km = {area_km2:,.0f} km2")
# 1 km2 = 1.000.000 m2. Un pixel de 10 m cubre 100 m2 (10.000 pixeles por km2)
# y uno de 20 m cubre 400 m2 (2.500 pixeles por km2).
print(f"Pixeles Sentinel-2 a 10 m: {area_km2 * 10_000:,.0f}")
print(f"Pixeles Sentinel-2 a 20 m (primera corrida de T-003): {area_km2 * 2_500:,.0f}")
