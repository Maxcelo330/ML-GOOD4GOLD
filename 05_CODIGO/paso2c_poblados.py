"""
Paso 2c - Crear una capa de referencia con los 4 pueblos de la zona piloto.

Para que sirve: poner puntos con nombre en el mapa de QGIS para ubicarte rapido.
NO es un dato de entrenamiento: es solo una guia visual.

Coordenadas: centro de cada poblado segun OpenStreetMap (consultadas el 2026-11-24,
ver nota V-005). Estan en grados (WGS84, EPSG:4326) y se guardan tambien en UTM 19S.

Como correrlo (entorno g4g-ml):
  python 05_CODIGO\\paso2c_poblados.py
"""
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "04_DATOS" / "referencia_poblados.gpkg"

# nombre, latitud, longitud (OpenStreetMap, V-005)
POBLADOS = [
    ("Tipuani", -15.5661, -68.0206),
    ("Mapiri", -15.3096, -68.2148),
    ("Teoponte", -15.4956, -67.8191),
    ("Guanay", -15.4977, -67.8798),
]

# Point(longitud, latitud): primero x (longitud) y luego y (latitud)
gdf = gpd.GeoDataFrame(
    {"nombre": [p[0] for p in POBLADOS], "fuente": "OpenStreetMap (V-005, 2026-11-24)"},
    geometry=[Point(p[2], p[1]) for p in POBLADOS],
    crs="EPSG:4326",
).to_crs("EPSG:32719")  # a metros, como el resto del proyecto

SALIDA.parent.mkdir(parents=True, exist_ok=True)
gdf.to_file(SALIDA, layer="poblados", driver="GPKG")
print(f"Guardado: {SALIDA} ({len(gdf)} poblados)")
