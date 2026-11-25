"""
Paso 3e - Limpiar las etiquetas antes de entrenar (correccion del revisor-ml).

Problemas que arregla:
  1. CONTRADICCIONES: los recortes de Tipuani, Teoponte y Guanay se pisan, asi que el mismo suelo
     pudo quedar como "mina" en un recorte y "no mina" en otro. Regla: un "descartar" NUNCA puede
     cubrir un poligono que sea 'aceptar' o 'pendiente'. Se le resta la parte en comun al descartar.
     Si hay mas de un criterio, manda la persona sobre Claude (decision_por vacio = persona).
  2. DUPLICADOS: el mismo terreno aparece dos veces (uno por recorte) y contaria doble. Cuando dos
     poligonos con la misma decision comparten mas de la mitad del menor, el de id mayor queda marcado
     en la columna 'duplicado_de' y no se usa para entrenar.
  3. CONGELAR: guarda una huella (hash) del archivo para que cada corrida del modelo diga con
     que etiquetas exactas se hizo.

No borra nada: los poligonos siguen en el archivo; solo cambian su forma o quedan marcados.
Respaldo previo: candidatos_respaldo_antes_de_limpiar.gpkg

Como correrlo (entorno g4g-ml, con QGIS cerrado o con el lapiz apagado):
  python 05_CODIGO\\paso3e_limpiar_etiquetas.py
"""
import hashlib
from pathlib import Path

import geopandas as gpd

RAIZ = Path(__file__).resolve().parents[1]
RUTA = RAIZ / "04_DATOS" / "etiquetas" / "candidatos.gpkg"
MIN_SOLAPE = 0.5           # fraccion del poligono menor que debe compartirse para llamarlo duplicado
HA_MINIMA_TRAS_RECORTE = 1.0

g = gpd.read_file(RUTA, layer="candidatos")
g["decision_por"] = g["decision_por"].fillna("") if "decision_por" in g.columns else ""
g["comentario"] = g["comentario"].fillna("")
if "duplicado_de" not in g.columns:
    g["duplicado_de"] = 0
g["duplicado_de"] = g["duplicado_de"].fillna(0).astype(int)

# ---- 1. Un 'descartar' no puede cubrir a un 'aceptar' ni a un 'pendiente'
recortes = []
for i in g.index[g.decision == "descartar"]:
    for j in g.index[g.decision != "descartar"]:
        inter = g.at[i, "geometry"].intersection(g.at[j, "geometry"])
        if inter.area > 100:   # mas de 100 m2: se toca de verdad
            g.at[i, "geometry"] = g.at[i, "geometry"].difference(g.at[j, "geometry"])
            recortes.append((int(g.at[i, "id"]), int(g.at[j, "id"]), round(inter.area / 1e4, 1)))
for i in g.index:
    g.at[i, "area_ha"] = round(g.at[i, "geometry"].area / 1e4, 1)
    if g.at[i, "geometry"].is_empty or g.at[i, "area_ha"] < HA_MINIMA_TRAS_RECORTE:
        g.at[i, "duplicado_de"] = -1   # -1 = quedo sin superficie util tras el recorte
for d_id, otro, ha in recortes:
    k = g.index[g["id"] == d_id][0]
    g.at[k, "comentario"] = (g.at[k, "comentario"] + f" | Claude: se resto {ha} ha que se solapaban con el candidato {otro}.").strip(" |")
print("Recortes (descartar, quien manda, ha):", recortes)

# ---- 2. Duplicados entre recortes (misma decision, mas de la mitad compartida)
dups = []
usables = g[(g.decision.isin(["aceptar", "descartar"])) & (g.duplicado_de == 0)].sort_values("id")
ids = list(usables.index)
for a in range(len(ids)):
    for b in range(a + 1, len(ids)):
        i, j = ids[a], ids[b]                      # i tiene el id menor: es el que se conserva
        if g.at[j, "duplicado_de"] != 0 or g.at[i, "decision"] != g.at[j, "decision"]:
            continue
        inter = g.at[i, "geometry"].intersection(g.at[j, "geometry"]).area
        menor = min(g.at[i, "geometry"].area, g.at[j, "geometry"].area)
        if menor > 0 and inter / menor >= MIN_SOLAPE:
            g.at[j, "duplicado_de"] = int(g.at[i, "id"])
            dups.append((int(g.at[j, "id"]), int(g.at[i, "id"])))
print("Duplicados (se marca el primero como copia del segundo):", dups)

g.to_file(RUTA, layer="candidatos", driver="GPKG")

# ---- 3. Resumen y huella
usa = g[g.decision.isin(["aceptar", "descartar"]) & (g.duplicado_de == 0)]
print("\nQuedan para entrenar:", usa.decision.value_counts().to_dict())
print("Marcados duplicado/sin superficie:", int((g.duplicado_de != 0).sum()))
print("Quien decidio los que se usan:", usa.decision_por.replace("", "persona").value_counts().to_dict())
print("Huella (SHA256) de candidatos.gpkg:", hashlib.sha256(RUTA.read_bytes()).hexdigest()[:16])
