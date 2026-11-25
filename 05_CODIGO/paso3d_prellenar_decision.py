"""
Paso 3d - Pre-llenar la columna 'decision' a partir del veredicto de Claude (por pedido del usuario).

Reglas:
  - probable_mineria -> decision = aceptar
  - probable_no      -> decision = descartar
  - dudoso           -> se queda 'pendiente' (no se usa para entrenar hasta que el humano decida)
  - NUNCA se pisa una decision que ya puso el humano: solo se llenan las filas en 'pendiente'.
  - Cada fila llenada por este script queda marcada en 'decision_por' = 'claude (propuesta)'.
  - Los candidatos 1 (Tipuani) y 26 (Mapiri) incluyen un pueblo: se les recorta un circulo de
    700 m alrededor del pueblo (aproximado) para no ensenar que los techos son mineria.

Para que sirve la marca 'decision_por': el metodo debe decir con honestidad que estas etiquetas
son "veredicto de Claude, pendientes de revision humana" y no una revision independiente.

Como correrlo (entorno g4g-ml, con QGIS en modo lectura: lapiz apagado):
  python 05_CODIGO\\paso3d_prellenar_decision.py
"""
from pathlib import Path

import geopandas as gpd

RAIZ = Path(__file__).resolve().parents[1]
RUTA = RAIZ / "04_DATOS" / "etiquetas" / "candidatos.gpkg"
RADIO_PUEBLO_M = 700
RECORTAR_PUEBLO = {1: "Tipuani", 26: "Mapiri"}   # id de candidato -> pueblo que incluye

g = gpd.read_file(RUTA, layer="candidatos")
if "decision_por" not in g.columns:
    g["decision_por"] = ""
g["decision_por"] = g["decision_por"].fillna("")
g["comentario"] = g["comentario"].fillna("")

pob = gpd.read_file(RAIZ / "04_DATOS" / "referencia_poblados.gpkg", layer="poblados").set_index("nombre")

mapa = {"probable_mineria": "aceptar", "probable_no": "descartar"}
pendientes = g["decision"].eq("pendiente")
nuevas = g.loc[pendientes, "veredicto_claude"].map(mapa)          # los dudosos quedan en NaN = sin cambio
llenar = nuevas.dropna().index
g.loc[llenar, "decision"] = nuevas.loc[llenar]
g.loc[llenar, "decision_por"] = "claude (propuesta, pendiente de revision humana)"

# Recortar el pueblo de los candidatos que lo incluyen
for cid, nombre in RECORTAR_PUEBLO.items():
    i = g.index[g["id"] == cid]
    if len(i) == 0 or g.loc[i[0], "decision_por"] == "":
        continue
    circulo = pob.loc[nombre].geometry.buffer(RADIO_PUEBLO_M)
    antes = g.loc[i[0], "geometry"].area / 1e4
    g.loc[i[0], "geometry"] = g.loc[i[0], "geometry"].difference(circulo)
    despues = g.loc[i[0], "geometry"].area / 1e4
    g.loc[i[0], "area_ha"] = round(despues, 1)
    g.loc[i[0], "comentario"] = (f"Claude: se recorto un circulo de {RADIO_PUEBLO_M} m alrededor del pueblo de {nombre} "
                                 f"(de {antes:.0f} a {despues:.0f} ha). Recorte aproximado.")
    print(f"Candidato {cid}: recortado el pueblo de {nombre} ({antes:.0f} -> {despues:.0f} ha)")

g.to_file(RUTA, layer="candidatos", driver="GPKG")
print("\nDecision (despues):")
print(g["decision"].value_counts().to_string())
print("\nQuien decidio:")
print(g["decision_por"].replace("", "(vacio)").value_counts().to_string())
