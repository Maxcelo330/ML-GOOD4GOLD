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

Pendiente (no se calcula aqui): dist_rio_m y dist_poblado_m. Necesitan la capa completa de rios y de
centros poblados. Se agregan cuando esas capas esten listas.

Como correrlo (entorno g4g-ml):
  python 05_CODIGO\\paso6_exportar_plataforma.py --prueba     (usa el mapa PRUEBA_, solo para probar el codigo)
  python 05_CODIGO\\paso6_exportar_plataforma.py              (usa el mapa real)
"""
# NOTA: este script usa las etiquetas de candidatos.gpkg tal como estan hoy.
import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize, shapes
from scipy import ndimage as ndi
from shapely.geometry import shape

RAIZ = Path(__file__).resolve().parents[1]
RES = RAIZ / "04_DATOS" / "resultados"
COMP = RAIZ / "04_DATOS" / "imagenes" / "compuesto"

UMBRAL = 0.5          # puntaje minimo para considerar un pixel
MIN_HA = 5            # zonas menores a 5 hectareas se descartan
TOP_N = 30            # solo las N zonas de mayor puntaje (las que un equipo puede revisar)
MARGEN_SIN_DATOS_PX = 30   # 30 pixeles de 20 m = 600 m alrededor de huecos sin datos (nubes, sombras)
MIN_OBS_MEDIANA = 7        # la zona debe tener, en mediana, 7 o mas fotos validas
NDVI_MEDIANA_MAX = 0.45    # y vegetacion baja (NDVI mediano menor a 0.45)
BORDE_ENTRENAMIENTO_PX = 5 # 5 pixeles = 100 m: lo pegado a una zona minera de entrenamiento no es hallazgo nuevo
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
px_ha = abs(T.a * T.e) / 10_000

cand = gpd.read_file(RAIZ / "04_DATOS" / "etiquetas" / "candidatos.gpkg", layer="candidatos")
dup = cand["duplicado_de"].fillna(0).astype(int) != 0 if "duplicado_de" in cand.columns else pd.Series(False, index=cand.index)
entrenamiento = cand[cand.decision.isin(["aceptar", "descartar"]) & ~dup]

# 2. Mascara de actividad: puntaje alto, fuera del agua y fuera de lo que se uso para entrenar
valido = (prob != nodata) & np.isfinite(ndwi) & (ndwi != -9999)
agua = valido & (ndwi > 0)
en_entrenamiento = rasterize([(g, 1) for g in entrenamiento.geometry], out_shape=forma, transform=T,
                             fill=0, dtype="uint8").astype(bool)
# Zonas cerca de huecos sin datos (nubes, sombras): no se evaluan, porque ahi quedan restos de nube que
# el modelo confunde con suelo expuesto. 30 pixeles de 20 m = 600 m de margen.
cerca_sin_datos = ndi.binary_dilation(~valido, structure=np.ones((3, 3)), iterations=MARGEN_SIN_DATOS_PX)
# Borde de las zonas mineras de entrenamiento: lo que queda pegado a una mina ya conocida no es un hallazgo nuevo
aceptadas = entrenamiento[entrenamiento.decision == "aceptar"]
en_aceptadas = rasterize([(g, 1) for g in aceptadas.geometry], out_shape=forma, transform=T,
                         fill=0, dtype="uint8").astype(bool)
borde_aceptadas = ndi.binary_dilation(en_aceptadas, structure=np.ones((3, 3)), iterations=BORDE_ENTRENAMIENTO_PX)
mascara = valido & (prob >= UMBRAL) & ~agua & ~en_entrenamiento & ~cerca_sin_datos & ~borde_aceptadas
mascara = ndi.binary_closing(mascara, structure=np.ones((3, 3)))
mascara = ndi.binary_opening(mascara, structure=np.ones((3, 3)))
print(f"Pixeles con puntaje >= {UMBRAL}: {int((valido & (prob >= UMBRAL)).sum()):,} | de ellos agua: "
      f"{int((valido & (prob >= UMBRAL) & agua).sum()):,} | dentro de poligonos de entrenamiento: "
      f"{int((valido & (prob >= UMBRAL) & en_entrenamiento).sum()):,}")
etiquetas, n = ndi.label(mascara)
if n == 0:
    raise SystemExit("No quedan zonas; revisa el umbral o el modelo.")
tamanos = ndi.sum(mascara, etiquetas, index=np.arange(1, n + 1))
buenos = np.where(tamanos * px_ha >= MIN_HA)[0] + 1
print(f"Zonas con al menos {MIN_HA} ha: {len(buenos)}")
# Filtro por zona: suficientes fotos validas y vegetacion baja (descarta restos de nube y laderas con bosque)
med_obs = ndi.median(nobs, etiquetas, index=buenos)
med_ndvi = ndi.median(np.where(np.isfinite(ndvi), ndvi, np.nan), etiquetas, index=buenos)
pasa = (np.asarray(med_obs) >= MIN_OBS_MEDIANA) & (np.asarray(med_ndvi) < NDVI_MEDIANA_MAX)
print(f"Se descartan {int((~pasa).sum())} zonas por pocas fotos (mediana < {MIN_OBS_MEDIANA}) o NDVI mediano >= "
      f"{NDVI_MEDIANA_MAX}; quedan {int(pasa.sum())} (antes de quedarse con las {TOP_N} mejores)")
buenos = buenos[pasa]
# Filtro por entorno: la mineria aluvial de la zona esta rodeada de bosque. Una mancha rodeada de terreno sin
# vegetacion (laderas altas de roca o suelo pardo natural) es otro tipo de suelo desnudo. Se mira un anillo de
# unos 300 m alrededor de cada zona y se pide NDVI mediano >= 0.5 (en la revision visual del 25-nov, las dos
# laderas pardas del top-30 fallaban esta regla y las zonas mineras no).
ENTORNO_NDVI_MIN = 0.5
cajas = ndi.find_objects(etiquetas)
entorno_ok = []
for k in buenos:
    f, c = cajas[k - 1]
    f0, f1, c0, c1 = max(f.start - 16, 0), f.stop + 16, max(c.start - 16, 0), c.stop + 16
    zona_k = etiquetas[f0:f1, c0:c1] == k
    anillo = ndi.binary_dilation(zona_k, iterations=15) & ~ndi.binary_dilation(zona_k, iterations=2)
    v = ndvi[f0:f1, c0:c1][anillo & valido[f0:f1, c0:c1]]
    entorno_ok.append(v.size > 0 and np.median(v) >= ENTORNO_NDVI_MIN)
entorno_ok = np.array(entorno_ok)
print(f"Se descartan {int((~entorno_ok).sum())} zonas rodeadas de terreno sin vegetacion (NDVI del entorno < {ENTORNO_NDVI_MIN}); "
      f"quedan {int(entorno_ok.sum())}")
buenos = buenos[entorno_ok]
etiquetas = np.where(np.isin(etiquetas, buenos), etiquetas, 0).astype("int32")

# 3. Poligono, area y puntaje medio de cada zona
geoms, ids = [], []
for g, v in shapes(etiquetas, mask=etiquetas > 0, transform=T):
    geoms.append(shape(g).simplify(15))   # simplificar ~15 m para que el archivo pese poco
    ids.append(int(v))
pm = ndi.mean(np.where(valido, prob, 0), etiquetas, index=ids)
gdf = gpd.GeoDataFrame({"puntaje": np.round(pm, 3)}, geometry=geoms, crs="EPSG:32719")
gdf["area_ha"] = (gdf.geometry.area / 10_000).round(1)
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
    "dist_rio_m": "",          # pendiente: requiere capa de rios
    "dist_poblado_m": "",      # pendiente: requiere capa de centros poblados
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
