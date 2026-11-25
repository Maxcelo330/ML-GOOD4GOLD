"""
Paso 6 - Convertir el mapa de puntaje del modelo en una lista corta de ZONAS para la plataforma web.

Que hace:
  1. Lee el raster de puntaje que dejo el modelo (valores 0 a 1) y el indice de agua (NDWI).
  2. Descarta: el agua (rios y pozas: NDWI > 0), los pixeles dentro de los poligonos con los que se
     entreno el modelo (su puntaje esta inflado porque los "vio") y las manchas sueltas.
  3. Se queda con las zonas de al menos 5 hectareas y SOLO las N de mayor puntaje (por defecto 30),
     para que una persona las pueda revisar de verdad. No se publican cientos de alertas.
     Filtros contra falsos positivos conocidos (ver nota de metodo):
       - 600 m de margen alrededor de huecos sin datos (restos de nube que el modelo confunde con suelo);
       - la zona debe tener en su mediana 7 o mas fotos validas y NDVI menor a 0.45 (vegetacion baja);
       - la zona debe estar rodeada de vegetacion (NDVI mediano del entorno >= 0.5): descarta laderas
         altas de roca o suelo pardo natural;
       - se descartan los bordes pegados a zonas de entrenamiento aceptadas (no son hallazgos nuevos).
  4. Agrega las zonas "aceptadas" por lectura visual (las que Claude marco como minera en el paso 3),
     como filas aparte, SIN puntaje del modelo, rotuladas "sin verificar" y con aviso si son muy grandes.
  5. Exporta:
       - detecciones_plataforma.csv   -> para la seccion "Datos" del prototipo web (Cargar CSV)
       - detecciones.geojson          -> poligonos de las zonas (para mapas web)
       - detecciones.gpkg             -> lo mismo, para abrir en QGIS

IMPORTANTE sobre el significado de los numeros:
  - 'puntaje_modelo' es un puntaje RELATIVO para ordenar; NO es una probabilidad. El modelo se
    entreno dando mas peso a la clase minera, lo que sube los valores artificialmente.
  - La imagen detecta posible ACTIVIDAD minera, no legalidad ni mercurio. Tambien puede marcar
    suelo desnudo que no es mineria (laderas, derrumbes, playas). Todo debe verificarse en campo.
  - El cruce con el catastro minero (AJAM) NO se ha hecho, y el texto lo dice asi.

Distancias: dist_rio_m y dist_poblado_m se calculan con la capa de OpenStreetMap que deja paso7
(04_DATOS/referencia/rios_y_poblados.gpkg). Son una guia, no una medida oficial.

Como correrlo (entorno g4g-ml):
  python 05_CODIGO\\paso6_exportar_plataforma.py --prueba     (usa el mapa PRUEBA_, solo para probar el codigo)
  python 05_CODIGO\\paso6_exportar_plataforma.py              (usa el mapa real)
"""
# NOTA: este script usa las etiquetas de candidatos.gpkg tal como estan hoy.
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize

sys.path.insert(0, str(Path(__file__).resolve().parent))   # (con 'python -I' la carpeta del script no se agrega sola)
import nucleo_zonas  # noqa: E402  reglas compartidas con el visor

RAIZ = Path(__file__).resolve().parents[1]
RES = RAIZ / "04_DATOS" / "resultados"
COMP = RAIZ / "04_DATOS" / "imagenes" / "compuesto"

MIN_HA = nucleo_zonas.MIN_HA   # las zonas de lectura visual tambien deben tener al menos 5 ha
TOP_N = 30            # solo las N zonas de mayor puntaje (las que un equipo puede revisar)
GRANDE_HA = 1000           # una zona de lectura visual mayor a esto se avisa como "muy grande"
PERIODO_IMAGEN = "mayo-septiembre 2026 (Sentinel-2, compuesto de epoca seca)"
NOTA = ("Puntaje relativo del modelo, no es una probabilidad. Posible actividad minera (por verificar; registro AJAM "
        "aun no consultado): no indica legalidad ni presencia de mercurio. Puede incluir suelo desnudo, arena de rio "
        "o derrumbes que no son mineria. Es una lista para revisar, no una deteccion confirmada.")
NOTA_LV = ("Zona marcada por lectura visual de la imagen (propuesta de Claude, no verificada en campo). No tiene "
           "puntaje del modelo: fue ejemplo de entrenamiento. Posible actividad minera (por verificar; registro AJAM "
           "aun no consultado).")

ap = argparse.ArgumentParser()
ap.add_argument("--prueba", action="store_true", help="usa PRUEBA_puntaje_mineria.tif (solo prueba del codigo)")
ap.add_argument("--top-n", type=int, default=TOP_N, help="cuantas zonas del modelo exportar (por defecto 30)")
args = ap.parse_args()
P = "PRUEBA_" if args.prueba else ""
TOP_N = args.top_n

with rasterio.open(RES / f"{P}puntaje_mineria.tif") as src:
    prob = src.read(1)   # (nombre historico 'prob'; es el puntaje del modelo, no una probabilidad)
    T = src.transform
    nodata = src.nodata
    forma = prob.shape
with rasterio.open(COMP / "ndwi_2026.tif") as s:
    ndwi = s.read(1)
with rasterio.open(COMP / "ndvi_2026.tif") as s:
    ndvi = s.read(1)
with rasterio.open(COMP / "n_observaciones.tif") as s:
    nobs = s.read(1).astype("float32")

cand = gpd.read_file(RAIZ / "04_DATOS" / "etiquetas" / "candidatos.gpkg", layer="candidatos")
dup = cand["duplicado_de"].fillna(0).astype(int) != 0 if "duplicado_de" in cand.columns else pd.Series(False, index=cand.index)
entrenamiento = cand[cand.decision.isin(["aceptar", "descartar"]) & ~dup]

# 2. Zonas: toda la logica (mascaras, filtros por zona, poligonos) vive en nucleo_zonas.py, compartida con el
#    analisis de bloques del visor, para que las dos usen exactamente las mismas reglas.
en_entrenamiento = rasterize([(g, 1) for g in entrenamiento.geometry], out_shape=forma, transform=T,
                             fill=0, dtype="uint8").astype(bool)
aceptadas = entrenamiento[entrenamiento.decision == "aceptar"]   # sus bordes no son hallazgos nuevos
en_aceptadas = rasterize([(g, 1) for g in aceptadas.geometry], out_shape=forma, transform=T,
                         fill=0, dtype="uint8").astype(bool)
gdf, info = nucleo_zonas.extraer_zonas(prob, ndvi, ndwi, nobs, T, "EPSG:32719",
                                       excluir=en_entrenamiento, aceptadas=en_aceptadas)
print(f"Pixeles con puntaje >= {nucleo_zonas.UMBRAL}: {info['pixeles_sobre_umbral']:,} | de ellos agua: "
      f"{info['de_ellos_agua']:,} | dentro de poligonos de entrenamiento: {info['de_ellos_entrenamiento']:,}")
print(f"Zonas con al menos {nucleo_zonas.MIN_HA} ha: {info['zonas_5ha']} | descartadas por pocas fotos o NDVI alto: "
      f"{info['descartadas_fotos_o_ndvi']} | descartadas por entorno sin vegetacion: {info['descartadas_entorno']} | "
      f"quedan {info['zonas_finales']} (antes de quedarse con las {TOP_N} mejores)")
if len(gdf) == 0:
    raise SystemExit("No quedan zonas; revisa el umbral o el modelo.")
gdf = gdf.sort_values("puntaje", ascending=False).head(TOP_N).reset_index(drop=True)   # solo las mejores
gdf["origen"] = "modelo (puntaje relativo)"
gdf["id"] = [f"ML-{i + 1:03d}" for i in range(len(gdf))]
# Una sola categoria: las diferencias de puntaje entre zonas son de decimas y no justifican "alta/media/baja"
gdf["prioridad"] = "por revisar"
gdf["nombre"] = "Posible actividad minera (por verificar) " + gdf["id"]
gdf["tipo"] = "zona sugerida por el modelo"
gdf["nota"] = NOTA
gdf["deteccion"] = "imagen satelital (ML)"

# 4. Zonas aceptadas por lectura visual (no son predicciones: son las que sirvieron de ejemplo)
vis = entrenamiento[entrenamiento.decision == "aceptar"].copy()
vis = vis.explode(index_parts=False)
vis = vis[vis.geometry.area / 1e4 >= MIN_HA].reset_index(drop=True)
vis = gpd.GeoDataFrame({"puntaje": np.nan, "area_ha": (vis.geometry.area / 1e4).round(1),
                        "origen": "lectura visual (propuesta de Claude, no verificada)"}, geometry=vis.geometry, crs="EPSG:32719")
vis["id"] = [f"LV-{i + 1:03d}" for i in range(len(vis))]
vis["prioridad"] = "sin verificar"
vis["nota"] = np.where(vis["area_ha"] > GRANDE_HA,
                       NOTA_LV + f" Zona muy grande (mas de {GRANDE_HA} ha): probablemente agrupa varias areas; revisar por partes.",
                       NOTA_LV)
vis["deteccion"] = "lectura visual de imagen (Claude)"
vis["nombre"] = "Posible actividad minera (lectura visual, por verificar) " + vis["id"]
vis["tipo"] = "zona identificada por lectura visual"
todo = pd.concat([gdf, vis], ignore_index=True)

# Pueblo de referencia mas cercano (solo los 4 del piloto; es una guia, no una distancia oficial)
pob = gpd.read_file(RAIZ / "04_DATOS" / "referencia_poblados.gpkg", layer="poblados")
cent = todo.geometry.representative_point()
d = np.array([[c.distance(p) for p in pob.geometry] for c in cent])
todo["zona_cercana"] = pob["nombre"].to_numpy()[d.argmin(axis=1)]

# Distancias (en metros, desde el borde de la zona) al cauce y al poblado mas cercanos de OpenStreetMap.
# Es una GUIA: OSM lo hacen voluntarios y pueden faltar cauces o caserios (ver paso7).
REF = RAIZ / "04_DATOS" / "referencia" / "rios_y_poblados.gpkg"
if REF.exists():
    cauces = gpd.read_file(REF, layer="cauces")
    lugares = gpd.read_file(REF, layer="poblados_osm")
    union_cauces = cauces.geometry.union_all()
    todo["dist_rio_m"] = (todo.geometry.distance(union_cauces) / 10).round().astype(int) * 10
    dl = np.array([[g.distance(p) for p in lugares.geometry] for g in todo.geometry])
    todo["dist_poblado_m"] = (dl.min(axis=1) / 10).round().astype(int) * 10
    nombres = lugares["nombre"].fillna("").to_numpy()[dl.argmin(axis=1)]
    todo["poblado_cercano"] = [n if n else "(sin nombre en OSM)" for n in nombres]
else:
    print("AVISO: falta 04_DATOS/referencia/rios_y_poblados.gpkg (corre paso7); las distancias van vacias.")
    todo["dist_rio_m"], todo["dist_poblado_m"], todo["poblado_cercano"] = "", "", ""

# 5. Exportar
wgs = todo.to_crs("EPSG:4326")
c4326 = wgs.geometry.representative_point()
tabla = pd.DataFrame({
    "id": todo["id"],
    "nombre": todo["nombre"],
    "tipo": todo["tipo"],
    "origen": todo["origen"],
    "lat": np.round(c4326.y, 6),
    "lng": np.round(c4326.x, 6),
    "area_ha": todo["area_ha"],
    "puntaje_modelo": (todo["puntaje"] * 100).round(0),     # 0-100, relativo; vacio en las de lectura visual
    "prioridad": todo["prioridad"],
    "zona_cercana": todo["zona_cercana"],
    "estado_verificacion": "por verificar en campo; registro AJAM aun no consultado",
    "dist_rio_m": todo["dist_rio_m"],              # al rio o quebrada mas cercano (OSM, guia)
    "dist_poblado_m": todo["dist_poblado_m"],      # al poblado mas cercano (OSM, guia)
    "poblado_cercano": todo["poblado_cercano"],
    "actualizado": PERIODO_IMAGEN,
    "deteccion": todo["deteccion"],
    "nota": todo["nota"],
})
tabla.to_csv(RES / f"{P}detecciones_plataforma.csv", index=False, encoding="utf-8-sig")
geo = wgs[["id", "geometry"]].merge(tabla, on="id")
geo.to_file(RES / f"{P}detecciones.geojson", driver="GeoJSON")
geo.to_crs("EPSG:32719").to_file(RES / f"{P}detecciones.gpkg", layer="zonas", driver="GPKG")

print(tabla[["id", "origen", "area_ha", "puntaje_modelo", "prioridad", "zona_cercana"]].to_string(index=False))
print(f"\nPrioridades: {tabla.prioridad.value_counts().to_dict()} | area total {tabla.area_ha.sum():,.0f} ha")
print(f"Guardado en {RES}: {P}detecciones_plataforma.csv, {P}detecciones.geojson, {P}detecciones.gpkg")
