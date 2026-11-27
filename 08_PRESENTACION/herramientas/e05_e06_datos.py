"""
Datos REALES para las escenas 5 (firma del pixel) y 6 (cerebro): 
  assets/capturas/e05_entorno.png          recorte natural (35 x 35 px de 20 m) alrededor del pixel de suelo removido
  assets/capturas/e05_entorno_pelado.png   solo los pixeles de la ventana de 300 m con NDVI < 0,3 ("suelo pelado"), RGBA
  assets/capturas/e05_entorno_agua.png     solo los pixeles de la ventana de 300 m con NDWI > 0 ("agua"), RGBA
  assets/capturas/e06_votos.json           voto (valor de hoja) de cada uno de los 300 arboles para los 5 pixeles de ejemplo
Se corre con el entorno g4g-ml:  python -I 08_PRESENTACION\herramientas\e05_e06_datos.py
"""
import json, sys
import numpy as np
from pathlib import Path
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "05_CODIGO"))
import analisis_bloque as ab  # noqa: E402

SAL = RAIZ / "08_PRESENTACION" / "assets" / "capturas"
SAL.mkdir(parents=True, exist_ok=True)
CLAVE_IMG = "ad9cae6574a9"
px = json.loads((RAIZ / "08_PRESENTACION/assets/datos/pixeles_ejemplo.json").read_text(encoding="utf-8"))
nom = px["variables"]

# ---------- entorno del pixel de suelo removido
z = np.load(ab.SALIDA / f"{CLAVE_IMG}_compuesto.npz")
ndvi, ndwi = np.asarray(z["ndvi"], "float32"), np.asarray(z["ndwi"], "float32")
nat = Image.open(ab.SALIDA / f"{CLAVE_IMG}_natural.png").convert("RGB")
p = next(q for q in px["pixeles"] if q["tipo"] == "suelo_removido")
f, c = p["fila"], p["col"]
R, K = 17, 18                                   # +-17 px => 35 x 35 px; cada px se dibuja de 18 px
crop = nat.crop((c - R, f - R, c + R + 1, f + R + 1))
crop.resize((crop.width * K, crop.height * K), Image.NEAREST).save(SAL / "e05_entorno.png")
sub_ndvi, sub_ndwi = ndvi[f - R:f + R + 1, c - R:c + R + 1], ndwi[f - R:f + R + 1, c - R:c + R + 1]
ven = np.zeros(sub_ndvi.shape, bool); ven[R - 7:R + 8, R - 7:R + 8] = True      # ventana de 15 x 15 px = 300 m
def mascara(m, rgb, nombre):
    a = np.zeros(m.shape + (4,), "uint8"); a[m] = (*rgb, 150)
    Image.fromarray(a, "RGBA").resize((m.shape[1] * K, m.shape[0] * K), Image.NEAREST).save(SAL / nombre)
mascara(ven & (sub_ndvi < 0.3) & ~(sub_ndwi > 0), (140, 70, 255), "e05_entorno_pelado.png")
mascara(ven & (sub_ndwi > 0), (0, 200, 255), "e05_entorno_agua.png")
print("pelado", (ven & (sub_ndvi < 0.3)).sum() / ven.sum(), "agua", (ven & (sub_ndwi > 0)).sum() / ven.sum())

# ---------- votos de los 300 arboles
d = ab.cargar_modelo().dump_model()
def camino(n, x, ruta):
    while "leaf_value" not in n:
        ok = x[n["split_feature"]] <= n["threshold"]
        ruta.append([nom[n["split_feature"]], round(n["threshold"], 3), bool(ok)])
        n = n["left_child"] if ok else n["right_child"]
    return n["leaf_value"]
sal = {"n_arboles": len(d["tree_info"]), "pixeles": {}}
for q in px["pixeles"]:
    x = [q["variables"][k] for k in nom]
    hojas, rutas = [], []
    for ti in d["tree_info"]:
        r = []; hojas.append(round(camino(ti["tree_structure"], x, r), 4)); rutas.append(r)
    tot = float(sum(hojas))
    sal["pixeles"][q["tipo"]] = {"puntaje": q["puntaje"], "suma": round(tot, 3), "puntaje_suma": round(100 / (1 + np.exp(-tot)), 1),
                                 "hojas": hojas, "rutas_3_primeros": rutas[:3]}
    print(q["tipo"], q["puntaje"], round(tot, 3), sal["pixeles"][q["tipo"]]["puntaje_suma"], "positivos", sum(h > 0 for h in hojas))
(SAL / "e06_votos.json").write_text(json.dumps(sal, ensure_ascii=False), encoding="utf-8")
