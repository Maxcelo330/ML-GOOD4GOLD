"""
Paso 3c - Agregar el VEREDICTO DE CLAUDE a cada candidato (columnas aparte de la decision del humano).

Lectura visual hecha por Claude el 2026-11-24 sobre la imagen Sentinel-2 en color natural
(epoca seca 2026), mirando cada candidato dibujado y numerado sobre la imagen.

Limites (importantes):
  - Es una HIPOTESIS visual, no una confirmacion. Con pixeles de 10 m se pueden confundir
    minería, pasto, chacos, derrumbes y pueblos.
  - La imagen NO permite saber si la actividad es de una empresa, una cooperativa o un
    particular, ni si es legal. Solo si "parece actividad minera".
  - No toca la columna 'decision', que es solo del humano.

Valores de 'veredicto_claude':
  probable_mineria  -> varias senales juntas (suelo removido + cauce + pozas/sedimento)
  dudoso            -> alguna senal, pero se confunde con camino, derrumbe, pueblo o rio turbio
  probable_no       -> parece pasto, chaco, ladera descubierta o parche aislado pequeno

Como correrlo (entorno g4g-ml):
  python 05_CODIGO\\paso3c_veredicto_claude.py
"""
from pathlib import Path

import geopandas as gpd

RAIZ = Path(__file__).resolve().parents[1]
RUTA = RAIZ / "04_DATOS" / "etiquetas" / "candidatos.gpkg"

# Candidatos con veredicto especifico (id -> (veredicto, motivo))
ESPECIFICOS = {
    1: ("probable_mineria", "Valle del Tipuani con terrazas removidas y pozas verdes junto al rio: patron tipico de mineria aluvial."),
    2: ("probable_mineria", "Zona excavada con sedimento gris en el valle, aguas abajo del anterior."),
    26: ("probable_mineria", "Corredor ancho del rio Mapiri con sedimento removido, pozas oscuras y cauce turbio. INCLUYE el pueblo de Mapiri: hay que recortarlo."),
    38: ("probable_mineria", "Parche naranja brillante (suelo rojizo recien removido) junto a la terraza del rio."),
    46: ("probable_mineria", "Parches naranja brillante en la terraza del rio, junto al corredor minero."),
    81: ("probable_mineria", "Quebrada angosta con sedimento naranja: patron de mineria en un cauce pequeno."),
    51: ("dudoso", "Cauce turbio con arena y sedimento, mas el pueblo de Teoponte y caminos. Indica actividad en la cuenca, pero no ubica el punto exacto."),
    52: ("dudoso", "Cauce angosto y turbio del rio (Kaka). Sedimento visible, pero no se distingue minería directa en la orilla."),
    76: ("dudoso", "Rio turbio con arena, el pueblo de Guanay y caminos. Mezcla varias cosas: recortar solo lo minero."),
    77: ("dudoso", "Cauce turbio con arena y sedimento; no se distingue minería directa en las orillas."),
}
DUDOSOS = {3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 17, 19, 27, 28, 33, 35, 37, 41, 56, 62, 84, 85, 88, 96}
MOTIVO_DUDOSO = ("Suelo expuesto junto a un rio, camino o quebrada. Podria ser minería, pero tambien "
                 "derrumbe, camino o ladera descubierta. Revisar en el mapa.")
MOTIVO_NO = ("Parche marron de forma regular o en ladera, lejos del cauce, o muy pequeno y aislado. "
             "Parece pasto, chaco o ladera descubierta; probable falso positivo.")

g = gpd.read_file(RUTA, layer="candidatos")
ver, mot = [], []
for i in g["id"]:
    if i in ESPECIFICOS:
        v, m = ESPECIFICOS[i]
    elif i in DUDOSOS:
        v, m = "dudoso", MOTIVO_DUDOSO
    else:
        v, m = "probable_no", MOTIVO_NO
    ver.append(v)
    mot.append(m)
g["veredicto_claude"] = ver
g["motivo_claude"] = mot
g.to_file(RUTA, layer="candidatos", driver="GPKG")
print(g["veredicto_claude"].value_counts().to_string())
print(g.groupby(["sector", "veredicto_claude"]).size().unstack(fill_value=0))
