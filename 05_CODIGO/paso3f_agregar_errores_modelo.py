"""
Paso 3f - Agregar a las etiquetas los ERRORES del modelo que se vieron a ojo (negativos dificiles).

Contexto: el primer modelo puso en su "top" casi solo bancos de arena de los rios grandes (se confunden
con mineria). Se miraron las 60 zonas mejor puntuadas una por una sobre la imagen (25-nov-2026) y
se clasificaron:
  - arena de rio / orilla de rio sin mineria -> 'descartar'  (le ensena al modelo lo que NO es mineria)
  - excavaciones mineras con pozas, vistas fuera de los recortes -> 'aceptar'  (041 y 051)
  - dudosas -> 'pendiente' (no se usan para entrenar)

HONESTIDAD: esto es "minado de errores dificiles". Mejora el modelo pero hace que las cifras de la
prueba sean algo optimistas (se corrigio donde se habia visto fallar). Debe decirse en el metodo.

ATENCION - NO SE PUEDE VOLVER A CORRER DESDE CERO: los numeros ACEPTAR/DUDOSAS (041, 051, 025...)
son posiciones del ranking del primer modelo (antes de agregar estas etiquetas, y antes de
endurecer el filtro de nubes). Hoy ese ranking es otro. Este script queda como REGISTRO de lo que
se hizo; el resultado esta guardado en 04_DATOS/etiquetas/candidatos.gpkg (candidatos 101 a 160,
origen "claude (error del modelo revisado en imagen, 2026-11-25)").
Cuando se corrio, requeria:  python 05_CODIGO\\paso6_exportar_plataforma.py --top-n 60
(dejaba las 60 zonas en 04_DATOS/resultados/detecciones.gpkg). Si las etiquetas ya incluyen estos
errores, no se agrega nada (no duplica).

Como correrlo (entorno g4g-ml):
  python 05_CODIGO\\paso3f_agregar_errores_modelo.py
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RUTA = RAIZ / "04_DATOS" / "etiquetas" / "candidatos.gpkg"
ORIGEN = "claude (error del modelo revisado en imagen, 2026-11-25)"

# Lectura visual de las 60 zonas del top (numero = ML-0NN en esa exportacion)
ACEPTAR = {41: "Excavacion minera con pozas verdes y suelo removido, fuera de los recortes originales.",
           51: "Gran zona removida con sedimento gris y zonas naranjas a lo largo de un cauce; patron de mineria."}
DUDOSAS = {25: "Orilla de rio junto a una zona minera con suelos naranjas; mezcla arena y posible mineria.",
           30: "Franja de arena junto a una gran zona minera en la otra orilla.",
           39: "Quebrada con agua anaranjada (sedimento) en bosque; podria venir de actividad aguas arriba.",
           53: "Parche pelado junto a un sendero en bosque; sin rasgos claros de mineria.",
           55: "Parche pelado en una quebrada cerca de un camino; sin rasgos claros.",
           59: "Quebrada con orilla arenosa y poca superficie expuesta."}

z = gpd.read_file(RAIZ / "04_DATOS" / "resultados" / "detecciones.gpkg", layer="zonas")
z = z[z["id"].str.startswith("ML")].copy()
assert len(z) == 60, f"Se esperaban 60 zonas (corre paso6 con --top-n 60); hay {len(z)}"
z["n"] = z["id"].str[3:].astype(int)

g = gpd.read_file(RUTA, layer="candidatos")
if (g["origen"] == ORIGEN).any():
    raise SystemExit("Los errores del modelo ya estan agregados; no se duplican.")

filas = []
nuevo_id = int(g["id"].max()) + 1
for _, r in z.sort_values("n").iterrows():
    if r.n in ACEPTAR:
        dec, ver, motivo = "aceptar", "probable_mineria", ACEPTAR[r.n]
    elif r.n in DUDOSAS:
        dec, ver, motivo = "pendiente", "dudoso", DUDOSAS[r.n]
    else:
        dec, ver = "descartar", "probable_no"
        motivo = "Banco de arena, playa o orilla de un rio (visto en la imagen). Error del modelo: no es mineria."
    filas.append({"id": nuevo_id, "sector": str(r["zona_cercana"]), "area_ha": r["area_ha"], "confianza": "media",
                  "motivo": motivo, "decision": dec, "comentario": f"Zona {r['id']} del top-60 del modelo.",
                  "origen": ORIGEN, "veredicto_claude": ver, "motivo_claude": motivo,
                  "decision_por": "claude (lectura visual de la imagen)", "duplicado_de": 0,
                  "geometry": r.geometry})
    nuevo_id += 1

nuevos = gpd.GeoDataFrame(filas, geometry="geometry", crs=g.crs)
g2 = pd.concat([g, nuevos], ignore_index=True)
g2 = gpd.GeoDataFrame(g2, geometry="geometry", crs=g.crs)
g2.drop(columns=[c for c in g2.columns if c == "fid"], errors="ignore").to_file(RUTA, layer="candidatos", driver="GPKG")
print("Agregados:", nuevos["decision"].value_counts().to_dict(), "| ids", int(nuevos.id.min()), "a", int(nuevos.id.max()))
print("Total de candidatos:", len(g2))
