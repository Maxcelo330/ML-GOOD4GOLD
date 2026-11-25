"""
Paso 8 - Visor web simple de las zonas para revisar (un solo archivo HTML que se abre con doble clic).

Para que sirve: que cualquier persona, SIN QGIS, pueda ver las zonas sobre la imagen satelital, tocar una
zona para leer su ficha (area, distancia a rio y poblado, advertencias) y marcar si, mirando la imagen,
le parece o no actividad minera. Esa revision queda guardada en su navegador y se descarga como CSV
(sirve para el Paso 9: validar 20-30 zonas a ojo).

Que hace:
  1. Lee las zonas (detecciones.geojson) y la capa de rios y poblados (paso7).
  2. Simplifica los rios (~20 m) para que el archivo pese poco.
  3. Escribe 07_VISOR/visor.html con los datos adentro. La libreria del mapa (Leaflet) va en 07_VISOR/lib.

Limites:
  - La imagen de fondo (Esri) y los mapas de OpenStreetMap necesitan internet; las zonas, rios y poblados no.
  - Es de USO INTERNO del equipo: muestra zonas de posible actividad minera sin verificar. No publicar
    abiertamente (decision D-002: el publico no debe ver detecciones sensibles).
  - La revision se guarda solo en el navegador de quien la hace (no hay servidor ni base de datos).

Como correrlo (entorno g4g-ml), despues de paso6 y paso7:
  python 05_CODIGO\\paso8_visor_html.py
"""
import json
from pathlib import Path

import geopandas as gpd

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "07_VISOR" / "visor.html"

GEOJSON = RAIZ / "04_DATOS" / "resultados" / "detecciones.geojson"
# La lista del piloto no se versiona en git: si falta (por ejemplo en otro equipo), el visor igual sirve para analizar bloques.
zonas = gpd.read_file(GEOJSON) if GEOJSON.exists() else None
ref = RAIZ / "04_DATOS" / "referencia" / "rios_y_poblados.gpkg"
cauces = gpd.read_file(ref, layer="cauces").to_crs("EPSG:32719")
lugares = gpd.read_file(ref, layer="poblados_osm")

# Rios: simplificar a ~20 m y pasar a grados con 5 decimales
cauces["geometry"] = cauces.geometry.simplify(20)
cauces = cauces.to_crs("EPSG:4326")
rios_js = [{"t": r.tipo[0], "n": r.nombre or "", "p": [[round(y, 5), round(x, 5)] for x, y in r.geometry.coords]}
           for r in cauces.itertuples()]
# Poblados: solo los que tienen nombre (los sin nombre no aportan al leer el mapa)
lug_js = [{"n": r.nombre, "t": r.tipo, "p": [round(r.geometry.y, 5), round(r.geometry.x, 5)]}
          for r in lugares.itertuples() if r.nombre]

cols = ["id", "nombre", "tipo", "origen", "area_ha", "puntaje_modelo", "prioridad", "zona_cercana", "estado_verificacion",
        "dist_rio_m", "dist_poblado_m", "poblado_cercano", "actualizado", "deteccion", "nota", "lat", "lng"]
zonas_js = json.loads(zonas[cols + ["geometry"]].to_json()) if zonas is not None else {"type": "FeatureCollection", "features": []}

plantilla = (RAIZ / "05_CODIGO" / "visor_plantilla.html").read_text(encoding="utf-8")
html = (plantilla.replace("__ZONAS__", json.dumps(zonas_js, ensure_ascii=False, separators=(",", ":")))
        .replace("__RIOS__", json.dumps(rios_js, ensure_ascii=False, separators=(",", ":")))
        .replace("__LUGARES__", json.dumps(lug_js, ensure_ascii=False, separators=(",", ":"))))
SALIDA.parent.mkdir(parents=True, exist_ok=True)
SALIDA.write_text(html, encoding="utf-8")
print(f"Guardado {SALIDA} ({SALIDA.stat().st_size / 1e3:.0f} KB): {len(zonas_js['features'])} zonas del piloto, {len(rios_js)} cauces, {len(lug_js)} poblados con nombre")
