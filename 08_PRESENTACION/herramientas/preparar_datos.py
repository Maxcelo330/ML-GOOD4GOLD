"""
Prepara los datos REALES que usa la presentacion animada (imagenes del bloque, puntaje del modelo, pixeles de ejemplo, un arbol real).

Salida (todo en 08_PRESENTACION/assets/):
  real/bloque_natural.jpg   color natural Sentinel-2 del bloque de ejemplo (24,9 x 26,7 km, mayo-septiembre 2026)
  real/bloque_falso.jpg     falso color (SWIR - infrarrojo - rojo): el suelo removido se ve rosado
  real/bloque_puntaje.png   mapa de calor del puntaje del modelo (RGBA transparente)
  datos/zonas_pixel.json    las zonas que marco el modelo, en coordenadas de pixel de esa imagen (sin coordenadas geograficas)
  datos/pixeles_ejemplo.json  5 pixeles reales con sus 14 variables y su puntaje, y una miniatura de cada uno
  datos/arbol_ejemplo.json  los primeros niveles de un arbol REAL del modelo (variables y umbrales)
  datos/importancia.json    cuanto pesa cada variable en el modelo
Se corre una vez: python -I 08_PRESENTACION\herramientas\preparar_datos.py  (entorno g4g-ml)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pyproj
from PIL import Image
from rasterio.features import rasterize
from shapely.geometry import shape
from shapely.ops import transform as sh_transform

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "05_CODIGO"))
import analisis_bloque as ab  # noqa: E402
import nucleo_zonas as nz  # noqa: E402

CLAVE, CLAVE_IMG = "5929e2f0a24d", "ad9cae6574a9"
SAL = RAIZ / "08_PRESENTACION" / "assets"
(SAL / "real").mkdir(parents=True, exist_ok=True)
(SAL / "datos").mkdir(parents=True, exist_ok=True)

res = json.loads((ab.SALIDA / f"{CLAVE}.json").read_text(encoding="utf-8"))
resumen = res["resumen"]
z = np.load(ab.SALIDA / f"{CLAVE_IMG}_compuesto.npz")


def f32(a):
    a = np.asarray(a, "float32")
    a[a < -9000] = nz.NODATA
    return a


bandas, ndvi, ndwi, bsi, pend = f32(z["bandas"]), f32(z["ndvi"]), f32(z["ndwi"]), f32(z["bsi"]), f32(z["pend"])
n_obs = z["n_obs"].astype("int16")
modelo = ab.cargar_modelo()
datos, valido = nz.variables_y_validez(bandas, ndvi, ndwi, bsi, pend, n_obs, con_contexto=modelo.num_feature() > len(nz.VARIABLES))
prob = nz.puntuar(modelo, datos, valido)
H, W = prob.shape
print("bloque", W, "x", H, "px; modelo", ab.MODELO.name)

# ---------- imagenes
nat = Image.open(ab.SALIDA / f"{CLAVE_IMG}_natural.png").convert("RGB")
fal = Image.open(ab.SALIDA / f"{CLAVE_IMG}_falso.png").convert("RGB")
esc = 2400 / max(nat.size)       # se amplian un poco para que se vean suaves al hacer zoom
tam = (round(nat.width * esc), round(nat.height * esc))
nat.resize(tam, Image.LANCZOS).save(SAL / "real" / "bloque_natural.jpg", quality=88)
fal.resize(tam, Image.LANCZOS).save(SAL / "real" / "bloque_falso.jpg", quality=88)
t = np.clip((prob - 0.3) / 0.7, 0, 1)
ok = (prob != nz.NODATA) & (prob >= 0.3)
rgba = np.zeros((H, W, 4), "uint8")
rgba[..., 0] = 255
rgba[..., 1] = (210 - 190 * t).astype("uint8")
rgba[..., 2] = (40 - 40 * t).astype("uint8")
rgba[..., 3] = np.where(ok, 130 + 110 * t, 0).astype("uint8")
Image.fromarray(rgba, "RGBA").resize(tam, Image.NEAREST).save(SAL / "real" / "bloque_puntaje.png", optimize=True)

# ---------- zonas en pixeles
x0, y1 = resumen["origen_m"]
tr = pyproj.Transformer.from_crs(4326, int(resumen["epsg_m"]), always_xy=True)
zonas = []
for f in res["zonas"]["features"]:
    g = sh_transform(lambda x, y, zz=None: tr.transform(x, y), shape(f["geometry"]))
    gp = sh_transform(lambda x, y, zz=None: ((x - x0) / ab.RES, (y1 - y) / ab.RES), g)
    partes = list(gp.geoms) if hasattr(gp, "geoms") else [gp]
    anillos = [[[round(x, 1), round(y, 1)] for x, y in p.exterior.coords] for p in partes]
    zonas.append({"id": f["properties"]["id"], "area_ha": f["properties"]["area_ha"], "puntaje": f["properties"]["puntaje_modelo"], "anillos": anillos})
(SAL / "datos" / "zonas_pixel.json").write_text(json.dumps({"ancho": W, "alto": H, "zonas": zonas}, ensure_ascii=False), encoding="utf-8")

# ---------- pixeles de ejemplo
rng = np.random.default_rng(7)
nombres = nz.VARIABLES + nz.VARIABLES_CONTEXTO
base = valido & (prob != nz.NODATA)


def elegir(mascara, etiqueta):
    ff, cc = np.nonzero(mascara & base)
    if not len(ff):
        raise SystemExit("sin pixeles para " + etiqueta)
    i = rng.integers(len(ff))
    return int(ff[i]), int(cc[i])


zona_arena = next(x for x in res["zonas"]["features"] if x["properties"]["id"] == "B5929-013")
g_arena = sh_transform(lambda x, y, zz=None: tr.transform(x, y), shape(zona_arena["geometry"]))
T = ab.Affine(ab.RES, 0, x0, 0, -ab.RES, y1) if hasattr(ab, "Affine") else None
from affine import Affine  # noqa: E402
T = Affine(ab.RES, 0, x0, 0, -ab.RES, y1)
m_arena = rasterize([(g_arena, 1)], out_shape=prob.shape, transform=T, fill=0, dtype="uint8").astype(bool)
cand = {
    "bosque": (ndvi > 0.85) & (prob < 0.03),
    "suelo_removido": (prob > 0.9) & (ndvi < 0.2) & (ndwi < 0),
    "rio": (ndwi > 0.1),
    "banco_de_arena": m_arena & (prob > 0.4),
    "pastizal": (ndvi > 0.4) & (ndvi < 0.55) & (prob < 0.05),
}
ejemplos = []
for etiqueta, m in cand.items():
    f, c = elegir(m, etiqueta)
    f0, f1_, c0, c1 = max(f - 12, 0), min(f + 13, H), max(c - 12, 0), min(c + 13, W)
    mini = nat.crop((c0, f0, c1, f1_)).resize((25 * 12, 25 * 12), Image.NEAREST)
    mini.save(SAL / "real" / f"px_{etiqueta}.png")
    ejemplos.append({"tipo": etiqueta, "fila": f, "col": c, "puntaje": round(float(prob[f, c]) * 100),
                     "variables": {n: round(float(datos[i, f, c]), 3) for i, n in enumerate(nombres)}, "miniatura": f"real/px_{etiqueta}.png"})
(SAL / "datos" / "pixeles_ejemplo.json").write_text(json.dumps({"variables": nombres, "pixeles": ejemplos}, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------- un arbol real del modelo y la importancia de cada variable
d = modelo.dump_model()
nom = d["feature_names"]


def simplificar(n, prof=0, maxp=3):
    if "leaf_value" in n:
        return {"hoja": round(n["leaf_value"], 3)}
    if prof >= maxp:
        return {"hoja": None}
    return {"variable": nom[n["split_feature"]], "umbral": round(n["threshold"], 3), "si": simplificar(n["left_child"], prof + 1, maxp), "no": simplificar(n["right_child"], prof + 1, maxp)}


arboles = [simplificar(d["tree_info"][i]["tree_structure"]) for i in range(3)]
(SAL / "datos" / "arbol_ejemplo.json").write_text(json.dumps({"n_arboles": len(d["tree_info"]), "arboles": arboles}, ensure_ascii=False, indent=1), encoding="utf-8")
imp = modelo.feature_importance("gain")
imp = imp / imp.sum()
(SAL / "datos" / "importancia.json").write_text(json.dumps(sorted([{"variable": n, "peso": round(float(v), 3)} for n, v in zip(nom, imp)], key=lambda x: -x["peso"]), ensure_ascii=False, indent=1), encoding="utf-8")
print("listo ->", SAL)
