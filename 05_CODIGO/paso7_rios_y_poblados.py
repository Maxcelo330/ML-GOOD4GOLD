"""
Paso 7 - Capa de rios y de poblados de TODA la zona piloto (para calcular distancias).

Para que sirve: el modulo "Datos" del prototipo pide dos columnas, dist_rio_m y dist_poblado_m.
Para calcularlas hacen falta los rios y los centros poblados de la zona. Aqui se descargan de
OpenStreetMap (datos abiertos, licencia ODbL: hay que citar "(c) colaboradores de OpenStreetMap").

Que hace:
  1. Pregunta a la API Overpass de OpenStreetMap por los cauces (rio, quebrada, canal, drenaje) y por
     los lugares poblados (ciudad, pueblo, aldea, caserio) dentro del recuadro de la zona piloto.
  2. Guarda la respuesta cruda (para no descargar de nuevo) y arma un GeoPackage en metros (EPSG:32719).

Limites que hay que decir:
  - OpenStreetMap esta hecho por voluntarios: en zonas remotas puede faltar algun cauce o caserio, y
    algunas quebradas pequenas no estan. La distancia es una GUIA, no una medida oficial.
  - Las quebradas que se secan o cambian de lecho no se ven reflejadas.

Como correrlo (entorno g4g-ml):
  python 05_CODIGO\\paso7_rios_y_poblados.py            (descarga si no hay copia local)
  python 05_CODIGO\\paso7_rios_y_poblados.py --bajar    (fuerza una descarga nueva)
"""
import argparse
import json
import time
from datetime import date
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import LineString, Point

RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "04_DATOS" / "referencia"
CRUDO = CARPETA / "osm_rios_poblados_crudo.json"
SALIDA = CARPETA / "rios_y_poblados.gpkg"
META = CARPETA / "rios_y_poblados_metadata.json"

# Recuadro de la zona piloto (sur, oeste, norte, este) = el de zona_piloto.gpkg
S, O, N, E = -15.90, -68.42, -15.00, -67.20
SERVIDORES = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
CONSULTA = f"""
[out:json][timeout:240];
(
  way["waterway"~"^(river|stream|canal|drain)$"]({S},{O},{N},{E});
  node["place"~"^(city|town|village|hamlet)$"]({S},{O},{N},{E});
);
out geom;
"""

ap = argparse.ArgumentParser()
ap.add_argument("--bajar", action="store_true", help="descarga de nuevo aunque ya exista la copia local")
args = ap.parse_args()
CARPETA.mkdir(parents=True, exist_ok=True)

# 1. Descarga (o lectura de la copia local)
if args.bajar or not CRUDO.exists():
    # Nombre de cliente generico: no se envia ningun dato personal ni del proyecto
    cabeceras = {"User-Agent": "ml-detector-zonas/0.1 (consulta de datos abiertos)"}
    for url in SERVIDORES:
        try:
            print("Consultando", url, "...")
            r = requests.post(url, data={"data": CONSULTA}, headers=cabeceras, timeout=300)
            r.raise_for_status()
            datos = r.json()
            break
        except Exception as e:  # noqa: BLE001  (se intenta con el servidor siguiente)
            print("  fallo:", e)
            time.sleep(5)
    else:
        raise SystemExit("Ningun servidor Overpass respondio. Intenta mas tarde.")
    CRUDO.write_text(json.dumps(datos), encoding="utf-8")
    print(f"Guardado {CRUDO.name} ({CRUDO.stat().st_size / 1e6:.1f} MB)")
else:
    datos = json.loads(CRUDO.read_text(encoding="utf-8"))
    print("Usando la copia local", CRUDO.name)

# 2. Armar las capas
lineas, puntos = [], []
for el in datos["elements"]:
    tags = el.get("tags", {})
    if el["type"] == "way" and "geometry" in el and len(el["geometry"]) >= 2:
        lineas.append({"osm_id": el["id"], "tipo": tags["waterway"], "nombre": tags.get("name", ""),
                       "geometry": LineString([(p["lon"], p["lat"]) for p in el["geometry"]])})
    elif el["type"] == "node" and "place" in tags:
        puntos.append({"osm_id": el["id"], "tipo": tags["place"], "nombre": tags.get("name", ""),
                       "geometry": Point(el["lon"], el["lat"])})
rios = gpd.GeoDataFrame(lineas, geometry="geometry", crs="EPSG:4326").to_crs("EPSG:32719")
pobl = gpd.GeoDataFrame(puntos, geometry="geometry", crs="EPSG:4326").to_crs("EPSG:32719")

if SALIDA.exists():
    SALIDA.unlink()
rios.to_file(SALIDA, layer="cauces", driver="GPKG")
pobl.to_file(SALIDA, layer="poblados_osm", driver="GPKG")
META.write_text(json.dumps({
    "fuente": "OpenStreetMap via Overpass API", "licencia": "ODbL (c) colaboradores de OpenStreetMap",
    "recuadro_s_o_n_e": [S, O, N, E], "fecha_archivo_crudo": date.fromtimestamp(CRUDO.stat().st_mtime).isoformat(),
    "cauces_por_tipo": rios.tipo.value_counts().to_dict(), "poblados_por_tipo": pobl.tipo.value_counts().to_dict(),
    "longitud_km_por_tipo": (rios.length.groupby(rios.tipo).sum() / 1000).round(0).to_dict(),
    "aviso": "Datos de voluntarios: pueden faltar cauces o caserios. Las distancias son una guia.",
}, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(json.loads(META.read_text(encoding="utf-8")), indent=2, ensure_ascii=False))
