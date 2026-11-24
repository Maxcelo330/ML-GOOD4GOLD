"""
Paso 2 - Crear la zona piloto (AOI = "Area Of Interest", area de interes).

Que hace este script:
  1. Define un rectangulo con coordenadas de latitud/longitud (grados).
  2. Lo guarda en un GeoPackage (.gpkg), el formato abierto que QGIS lee directo.
  3. Guarda dos versiones del mismo rectangulo:
       - EPSG:4326 (WGS84): grados. Es el "idioma comun" para intercambiar datos.
       - EPSG:32719 (UTM zona 19 Sur): metros. Sirve para medir distancias y areas.

Como correrlo (en "Anaconda Prompt"):
  conda activate g4g-ml
  python "E:\\PROYECTO GOOD4GOLD\\QGIS MACHINE LEARNING\\05_CODIGO\\paso2_zona_piloto.py"
"""
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

# Carpeta del proyecto (dos niveles arriba de este archivo)
RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "04_DATOS" / "zona_piloto.gpkg"

# Limites de la zona piloto: norte de La Paz (Tipuani, Mapiri, Teoponte, Guanay).
# Es el mismo recuadro que usa la hidrografia del prototipo web (hidro-zona.js).
LNG_MIN, LNG_MAX = -68.2, -67.2   # longitud: oeste (-) / este
LAT_MIN, LAT_MAX = -15.9, -15.0   # latitud: sur (-) / norte

# box(xmin, ymin, xmax, ymax): x = longitud, y = latitud
rectangulo = box(LNG_MIN, LAT_MIN, LNG_MAX, LAT_MAX)

aoi_wgs84 = gpd.GeoDataFrame(
    {"nombre": ["Zona piloto norte de La Paz"]},
    geometry=[rectangulo],
    crs="EPSG:4326",
)

# Reproyectar a metros (UTM 19S) para poder medir el area
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
print(f"Pixeles Sentinel-2 a 10 m: {area_km2 * 10_000:,.0f}")
