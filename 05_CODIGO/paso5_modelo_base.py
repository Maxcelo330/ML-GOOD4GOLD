"""
Paso 5 - Modelo base (LightGBM) que da un PUNTAJE de parecido a zonas de posible actividad minera.
(El puntaje sirve para ordenar zonas; NO es una probabilidad, porque se entreno dando mas peso a la clase minera.)

Que hace, en orden:
  1. Toma las decisiones del revisor sobre los candidatos (aceptar = mineria, descartar = no mineria).
  2. Saca una muestra de pixeles dentro de cada poligono y lee sus "variables" (bandas,
     indices y pendiente). Agrega pixeles de fondo (bosque, altiplano...) como negativos extra.
  3. PRUEBA HONESTA: reparte los datos por ZONAS del mapa, nunca pixel por pixel, y mide el
     modelo solo en zonas que no vio al entrenar (ver explicacion abajo).
  4. Compara contra una regla simple (linea base) para saber si el modelo aporta algo.
  5. Entrena con todo y genera el mapa de puntaje (raster) para QGIS.

Dos modos:
  - Normal (por defecto): usa la columna 'decision'. OJO: casi todas las decisiones son PROPUESTAS
    de Claude (ver 'decision_por'); solo las de 'decision_por' vacio las puso una persona. Por eso
    las cifras miden coincidencia con esa lectura visual, NO exactitud contra el terreno.
  - --provisional: usa el 'veredicto_claude' como etiqueta. SOLO sirve para probar que el codigo
    funciona; sus resultados NO se reportan y los archivos salen con el prefijo PRUEBA_.

Por que la prueba es por zonas y no al azar:
  Un pixel y su vecino se parecen casi igual. Si el examen incluye un pixel pegado a otro que el
  modelo ya estudio, es como copiar del companero de al lado y la nota sale inflada. Aqui el
  mapa se corta en cuadros de 5 x 5 km y cada cuadro entero va al entrenamiento O al examen,
  nunca a los dos. Ademas hay una prueba mas dura: entrenar con tres pueblos y examinar en el
  cuarto, que el modelo nunca vio.

Como correrlo (entorno g4g-ml):
  python 05_CODIGO\\paso5_modelo_base.py --provisional     (solo prueba del codigo)
  python 05_CODIGO\\paso5_modelo_base.py                    (con tus decisiones)
"""
import argparse
import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

import geopandas as gpd
import lightgbm as lgb
import numpy as np
import pandas as pd
import rasterio
import sklearn
from rasterio.windows import Window
from shapely import contains_xy
from shapely.ops import unary_union
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import GroupKFold

# ----------------------------------------------------------------- configuracion
SEMILLA = 42                 # semilla fija: mismos datos y mismo modelo cada vez
MAX_PIX_POR_POLIGONO = 400   # pixeles de 20 m que se toman de cada candidato (evita que un poligono enorme domine)
N_FONDO = 3000               # pixeles de fondo (negativos extra) lejos de todo candidato
DISTANCIA_FONDO_M = 500      # el fondo se toma a mas de 500 m de cualquier candidato
MIN_OBS = 3                  # un pixel con menos de 3 fotos validas se descarta (poco confiable: ahi quedan nubes sueltas)
B02_MAX = 0.25               # reflectancia azul muy alta = nube que se colo; se descarta
BLOQUE_M = 5000              # tamano del cuadro de la validacion por zonas (5 km)
N_PLIEGUES = 5               # en cuantas partes se reparte el mapa para la prueba
UMBRAL = 0.5                 # puntaje desde el cual se dice "mineria" (el puntaje no es una probabilidad)
VARIABLES = ["B02", "B03", "B04", "B08", "B11", "B12", "ndvi", "ndwi", "bsi", "pendiente"]

RAIZ = Path(__file__).resolve().parents[1]
COMP = RAIZ / "04_DATOS" / "imagenes" / "compuesto"
RES = RAIZ / "04_DATOS" / "resultados"

ap = argparse.ArgumentParser()
ap.add_argument("--provisional", action="store_true", help="usa el veredicto de Claude (solo prueba del codigo)")
args = ap.parse_args()
PREFIJO = "PRUEBA_" if args.provisional else ""
RES.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(SEMILLA)
t0 = time.time()


def log(msg):
    print(f"[{time.time() - t0:5.0f} s] {msg}", flush=True)


# ----------------------------------------------------------------- lectura de rasters
fuentes = {
    "bandas": rasterio.open(COMP / "bandas_2026_20m.tif"),
    "ndvi": rasterio.open(COMP / "ndvi_2026.tif"),
    "ndwi": rasterio.open(COMP / "ndwi_2026.tif"),
    "bsi": rasterio.open(COMP / "bsi_2026.tif"),
    "pendiente": rasterio.open(COMP / "pendiente_grados.tif"),
    "nobs": rasterio.open(COMP / "n_observaciones.tif"),
}
T = fuentes["bandas"].transform          # T.c = x del borde izquierdo, T.f = y del borde superior (metros)
ALTO, ANCHO = fuentes["bandas"].height, fuentes["bandas"].width
for nombre, s in fuentes.items():        # todos deben compartir la misma grilla
    assert (s.height, s.width) == (ALTO, ANCHO) and s.transform == T, f"{nombre} no coincide en grilla"
PX = T.a                                  # tamano de pixel: 20 m


def leer(fila0, alto, col0, ancho):
    """Lee una ventana de todas las variables. Devuelve (variables, alto, ancho) y la mascara de validez."""
    v = Window(col0, fila0, ancho, alto)
    capas = [fuentes["bandas"].read(i + 1, window=v).astype("float32") for i in range(6)]
    for k in ("ndvi", "ndwi", "bsi", "pendiente"):
        capas.append(fuentes[k].read(1, window=v).astype("float32"))
    datos = np.stack(capas)
    nobs = fuentes["nobs"].read(1, window=v)
    valido = np.isfinite(datos).all(axis=0) & (datos != -9999).all(axis=0) & (nobs >= MIN_OBS)
    with np.errstate(invalid="ignore"):
        valido &= datos[0] < B02_MAX                 # datos[0] = banda azul (B02)
    datos[:, ~valido] = np.nan
    return datos, valido


# ----------------------------------------------------------------- 1. etiquetas
cand = gpd.read_file(RAIZ / "04_DATOS" / "etiquetas" / "candidatos.gpkg", layer="candidatos")
if args.provisional:
    pos = cand["veredicto_claude"] == "probable_mineria"
    neg = cand["veredicto_claude"] == "probable_no"
    log("MODO PROVISIONAL: etiquetas = veredicto de Claude (solo prueba del codigo)")
else:
    pos = cand["decision"] == "aceptar"
    neg = cand["decision"] == "descartar"
# Se excluyen los duplicados y los que quedaron sin superficie (columna 'duplicado_de', ver paso3e)
dup = (cand["duplicado_de"].fillna(0).astype(int) != 0) if "duplicado_de" in cand.columns else pd.Series(False, index=cand.index)
cand = cand[(pos | neg) & ~dup].copy()
cand["clase"] = np.where(pos[cand.index], 1, 0)
log(f"Candidatos usados: {int((cand.clase == 1).sum())} mineria, {int((cand.clase == 0).sum())} no mineria "
    f"(los 'pendiente', 'corregir' y dudosos no se usan para entrenar)")
if (cand.clase == 1).sum() < 3 or (cand.clase == 0).sum() < 3:
    sys.exit("Hay muy pocos candidatos de alguna clase para entrenar. Revisa mas candidatos en QGIS.")

# Pueblo mas cercano a cada punto: sirve para la prueba "dejar un pueblo afuera"
pob = gpd.read_file(RAIZ / "04_DATOS" / "referencia_poblados.gpkg", layer="poblados")
pob_xy = np.array([(g.x, g.y) for g in pob.geometry])
pob_nombre = pob["nombre"].to_numpy()


def pueblo_cercano(x, y):
    d = (x[:, None] - pob_xy[None, :, 0]) ** 2 + (y[:, None] - pob_xy[None, :, 1]) ** 2
    return pob_nombre[d.argmin(axis=1)]


# ----------------------------------------------------------------- 2. muestreo de pixeles
filas = []
for _, c in cand.iterrows():
    minx, miny, maxx, maxy = c.geometry.bounds
    col0 = max(int(np.floor((minx - T.c) / PX)), 0)
    col1 = min(int(np.ceil((maxx - T.c) / PX)), ANCHO)
    fila0 = max(int(np.floor((T.f - maxy) / PX)), 0)
    fila1 = min(int(np.ceil((T.f - miny) / PX)), ALTO)
    if col1 <= col0 or fila1 <= fila0:
        continue
    datos, valido = leer(fila0, fila1 - fila0, col0, col1 - col0)
    ff, cc = np.nonzero(valido)
    xs, ys = T.c + (cc + col0 + 0.5) * PX, T.f - (ff + fila0 + 0.5) * PX       # centro de cada pixel
    dentro = contains_xy(c.geometry, xs, ys)                                      # solo los que caen en el poligono
    ff, cc, xs, ys = ff[dentro], cc[dentro], xs[dentro], ys[dentro]
    if len(ff) == 0:
        continue
    sel = rng.choice(len(ff), size=min(MAX_PIX_POR_POLIGONO, len(ff)), replace=False)
    df = pd.DataFrame(datos[:, ff[sel], cc[sel]].T, columns=VARIABLES)
    df["x"], df["y"], df["clase"], df["origen"], df["id_cand"] = xs[sel], ys[sel], c.clase, "candidato", c["id"]
    # CORRECCION DE LA FUGA ESPACIAL: todos los pixeles de un poligono llevan el MISMO bloque (el de
    # su punto central) y el mismo "pueblo" (su sector). Asi una mina entera va al estudio O al
    # examen, nunca partida entre los dos.
    rp = c.geometry.representative_point()
    df["bloque"] = int(np.floor(rp.x / BLOQUE_M)) * 1000 + int(np.floor(rp.y / BLOQUE_M))
    df["pueblo"] = c["sector"]
    filas.append(df)

# Fondo: pixeles al azar lejos de cualquier candidato. Son negativos "faciles" (en su mayoria bosque; composicion
# NO verificada). OJO: pueden incluir mineria no marcada y casi no incluyen bancos de arena de rios grandes,
# que el modelo termina confundiendo con mineria (ver paso6).
prohibido = unary_union(list(gpd.read_file(RAIZ / "04_DATOS" / "etiquetas" / "candidatos.gpkg", layer="candidatos").geometry)).buffer(DISTANCIA_FONDO_M)
fondo, intentos = [], 0
while sum(len(f) for f in fondo) < N_FONDO and intentos < 60:
    intentos += 1
    cc = rng.integers(0, ANCHO, 400)
    ff = rng.integers(0, ALTO, 400)
    xs, ys = T.c + (cc + 0.5) * PX, T.f - (ff + 0.5) * PX
    libres = ~contains_xy(prohibido, xs, ys)
    filas_ok = []
    for f_, c_, x_, y_ in zip(ff[libres], cc[libres], xs[libres], ys[libres]):
        d, v = leer(int(f_), 1, int(c_), 1)
        if v[0, 0]:
            filas_ok.append((*d[:, 0, 0], x_, y_))
    if filas_ok:
        a = np.array(filas_ok)
        df = pd.DataFrame(a[:, :10], columns=VARIABLES)
        df["x"], df["y"], df["clase"], df["origen"], df["id_cand"] = a[:, 10], a[:, 11], 0, "fondo", -1
        fondo.append(df)
D = pd.concat(filas + fondo, ignore_index=True)
# Los pixeles de FONDO (no pertenecen a ningun poligono) toman bloque y pueblo segun su propia posicion
es_fondo = (D.origen == "fondo").to_numpy()
D.loc[es_fondo, "bloque"] = np.floor(D.x[es_fondo] / BLOQUE_M).astype(int) * 1000 + np.floor(D.y[es_fondo] / BLOQUE_M).astype(int)
D.loc[es_fondo, "pueblo"] = pueblo_cercano(D.x[es_fondo].to_numpy(), D.y[es_fondo].to_numpy())
D["bloque"] = D["bloque"].astype(int)
log(f"Muestra: {len(D)} pixeles | mineria {int((D.clase == 1).sum())} | no mineria {int((D.clase == 0).sum())} "
    f"(de ellos {int((D.origen == 'fondo').sum())} de fondo) | {D.bloque.nunique()} bloques de {BLOQUE_M // 1000} km")
# Se guarda la muestra de entrenamiento del piloto: paso10_reentrenar.py la combina con la de otros lugares (no va a git)
(RAIZ / "04_DATOS" / "entrenamiento").mkdir(parents=True, exist_ok=True)
if not args.provisional:
    D.to_csv(RAIZ / "04_DATOS" / "entrenamiento" / "muestra_piloto.csv.gz", index=False)


# ----------------------------------------------------------------- 3. modelo y prueba por zonas
def nuevo_modelo():
    return lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=20,
                              subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                              class_weight="balanced", random_state=SEMILLA, n_jobs=-1, verbose=-1)


def metricas(y, p, etiqueta):
    """Precision y recall de la clase 'mineria' (1), F1 y area bajo la curva precision-recall."""
    pred = (p >= UMBRAL).astype(int)
    pr, rc, f1, _ = precision_recall_fscore_support(y, pred, labels=[1], zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    ap_ = average_precision_score(y, p) if 0 < y.sum() < len(y) else float("nan")
    return {"prueba": etiqueta, "n": int(len(y)), "positivos": int(y.sum()), "precision": round(float(pr[0]), 3),
            "recall": round(float(rc[0]), 3), "f1": round(float(f1[0]), 3), "ap": round(float(ap_), 3),
            "verdaderos_pos": int(tp), "falsos_pos": int(fp), "falsos_neg": int(fn), "verdaderos_neg": int(tn)}


def validar(grupos, nombre, cortes, cols=VARIABLES):
    """Predice cada pixel con un modelo entrenado SIN esa zona (la mina entera queda afuera).
    Devuelve las predicciones y los resultados por parte. 'cols' = variables que se usan."""
    oof = np.full(len(D), np.nan)
    por_parte = []
    for i, (ent, test) in enumerate(cortes):
        yt = D.clase.to_numpy()[test]
        if D.clase.to_numpy()[ent].sum() == 0 or yt.sum() == 0 or yt.sum() == len(yt):
            log(f"   {nombre} parte {i + 1}: sin mineria o sin no-mineria en entrenamiento o examen; se omite")
            continue
        m = nuevo_modelo().fit(D.loc[ent, cols], D.clase.to_numpy()[ent])
        oof[test] = m.predict_proba(D.loc[test, cols])[:, 1]
        por_parte.append({**metricas(yt, oof[test], f"{nombre} parte {i + 1}"), "zona_examen": str(sorted(set(grupos[test]))[:4])})
    return oof, por_parte


y = D.clase.to_numpy()
cortes_bloque = list(GroupKFold(n_splits=N_PLIEGUES).split(D, y, groups=D.bloque))
cortes_pueblo = [(np.where(D.pueblo != p)[0], np.where(D.pueblo == p)[0]) for p in pob_nombre]
oof_b, partes_b = validar(D.bloque.to_numpy(), "bloques de 5 km", cortes_bloque)
oof_p, partes_p = validar(D.pueblo.to_numpy(), "pueblo afuera", cortes_pueblo)
# Comparacion extra: un modelo que usa SOLO la vegetacion (NDVI). Si el modelo completo no lo supera, las demas variables no aportan.
oof_n, _ = validar(D.bloque.to_numpy(), "bloques de 5 km (solo NDVI)", cortes_bloque, cols=["ndvi"])

# DIAGNOSTICO DE FUGA: cuantos poligonos tienen pixeles en el entrenamiento Y en el examen a la vez.
# Debe dar 0. (Antes de la correccion, el 83% de los pixeles mineros del examen estaban en esa situacion.)
compartidos = 0
for ent, test in cortes_bloque:
    en_ent = set(D.loc[ent][D.loc[ent].origen == "candidato"].id_cand)
    en_test = set(D.loc[test][D.loc[test].origen == "candidato"].id_cand)
    compartidos += len(en_ent & en_test)
log(f"DIAGNOSTICO DE FUGA: poligonos compartidos entre entrenamiento y examen = {compartidos} (debe ser 0)")

# LINEAS BASE (reglas simples sin entrenar). Si el modelo no las supera, no aporta.
ndvi = D.ndvi.to_numpy()
lb_05 = (ndvi < 0.5).astype(float)    # regla floja: marca casi todo lo que no es bosque denso
lb_03 = (ndvi < 0.3).astype(float)    # regla mas exigente (umbral elegido mirando 3 valores: algo optimista)
puntaje_ndvi = -ndvi                  # "ordenar por poca vegetacion": mas pelado = mas sospechoso


def fila_ap(y_, score, etiqueta):
    """Solo el AP de un puntaje que ordena (no hay umbral, por eso no hay precision ni recall)."""
    return {"prueba": etiqueta, "n": int(len(y_)), "positivos": int(y_.sum()), "precision": np.nan, "recall": np.nan,
            "f1": np.nan, "ap": round(float(average_precision_score(y_, score)), 3)}


resultados = []
for nombre, oof in (("bloques de 5 km", oof_b), ("pueblo afuera", oof_p)):
    ok = ~np.isnan(oof)
    if ok.sum() == 0:
        continue
    resultados.append(metricas(y[ok], oof[ok], f"MODELO - {nombre} (todo junto)"))
    dif = ok & (D.origen.to_numpy() == "candidato")                      # solo los negativos "dificiles" (pasto, ladera...)
    if dif.sum() and y[dif].sum() and y[dif].sum() < dif.sum():
        resultados.append(metricas(y[dif], oof[dif], f"MODELO - {nombre} (solo candidatos, mas dificil)"))
    resultados.append(metricas(y[ok], lb_05[ok], f"LINEA BASE NDVI<0.5 - {nombre}"))
    resultados.append(metricas(y[ok], lb_03[ok], f"LINEA BASE NDVI<0.3 - {nombre}"))
    resultados.append(fila_ap(y[ok], puntaje_ndvi[ok], f"LINEA BASE ordenar por -NDVI (solo AP) - {nombre}"))
ok_n = ~np.isnan(oof_n)
resultados.append(metricas(y[ok_n], oof_n[ok_n], "MODELO SOLO NDVI - bloques de 5 km (todo junto)"))
tabla = pd.DataFrame(resultados)
partes = pd.DataFrame(partes_b + partes_p)
print("\n=== RESULTADOS DE LA PRUEBA (el modelo examinado en zonas que no vio) ===")
print(tabla[["prueba", "n", "positivos", "precision", "recall", "f1", "ap"]].to_string(index=False))
print("\n=== Por parte (cuanto varia entre zonas) ===")
if len(partes):
    print(partes[["prueba", "positivos", "n", "precision", "recall", "f1"]].to_string(index=False))
    for tipo in ("bloques de 5 km parte", "pueblo afuera parte"):    # se promedian por separado
        sub = partes[partes.prueba.str.startswith(tipo)]
        if len(sub):
            print(f"F1 por parte ({tipo.replace(' parte', '')}): minimo {sub.f1.min():.2f}, media {sub.f1.mean():.2f}, "
                  f"maximo {sub.f1.max():.2f} ({len(sub)} partes)")

# ----------------------------------------------------------------- 4. modelo final y mapa
final = nuevo_modelo().fit(D[VARIABLES], y)
# Se guarda el modelo entrenado para poder usarlo despues sobre bloques nuevos (servidor del visor, paso 9b)
final.booster_.save_model(str(RES / f"{PREFIJO}modelo_lgbm.txt"))
imp =pd.DataFrame({"variable": VARIABLES, "importancia": final.booster_.feature_importance("gain")})
imp["importancia"] = (imp.importancia / imp.importancia.sum()).round(3)
imp = imp.sort_values("importancia", ascending=False)
print("\n=== Variables que mas usa el modelo ===")
print(imp.to_string(index=False))

perfil = dict(driver="GTiff", height=ALTO, width=ANCHO, count=1, dtype="float32", crs="EPSG:32719",
              transform=T, compress="deflate", nodata=-9999)
salida_mapa = RES / f"{PREFIJO}puntaje_mineria.tif"
log("Generando el mapa de puntaje por franjas...")
with rasterio.open(salida_mapa, "w", **perfil) as dst:
    PASO = 200
    for f0 in range(0, ALTO, PASO):
        h = min(PASO, ALTO - f0)
        datos, valido = leer(f0, h, 0, ANCHO)
        franja = np.full((h, ANCHO), -9999, dtype="float32")
        if valido.any():
            franja[valido] = final.predict_proba(pd.DataFrame(datos[:, valido].T, columns=VARIABLES))[:, 1]
        dst.write(franja, 1, window=Window(0, f0, ANCHO, h))

# ----------------------------------------------------------------- 5. guardar resultados
tabla.to_csv(RES / f"{PREFIJO}metricas.csv", index=False)
partes.to_csv(RES / f"{PREFIJO}metricas_por_parte.csv", index=False)
imp.to_csv(RES / f"{PREFIJO}importancia_variables.csv", index=False)
(RES / f"{PREFIJO}modelo_info.json").write_text(json.dumps({
    "modo": "PROVISIONAL (solo prueba del codigo, no reportar)" if args.provisional else "normal",
    "fecha": str(date.today()), "semilla": SEMILLA, "umbral": UMBRAL, "variables": VARIABLES,
    "pixeles_por_poligono_max": MAX_PIX_POR_POLIGONO, "fondo": N_FONDO, "bloque_m": BLOQUE_M,
    "candidatos_mineria": int((cand.clase == 1).sum()), "candidatos_no_mineria": int((cand.clase == 0).sum()),
    # De donde salen las etiquetas (importante para declararlo en el metodo y en el deck)
    "origen_etiquetas": (cand["decision_por"].fillna("").replace("", "humano").value_counts().to_dict()
                         if "decision_por" in cand.columns else {"veredicto_claude (modo provisional)": len(cand)}),
    "poligonos_compartidos_entre_entrenamiento_y_examen": compartidos,
    "huella_sha256_candidatos": hashlib.sha256((RAIZ / "04_DATOS" / "etiquetas" / "candidatos.gpkg").read_bytes()).hexdigest(),
    "aviso": "Etiquetas propuestas por Claude (lectura visual), sin verificacion de campo. Los puntajes no son probabilidades.",
    "versiones": {"python": sys.version.split()[0], "lightgbm": lgb.__version__, "scikit-learn": sklearn.__version__,
                  "numpy": np.__version__, "pandas": pd.__version__, "geopandas": gpd.__version__,
                  "rasterio": rasterio.__version__},
}, indent=2, ensure_ascii=False), encoding="utf-8")
log(f"Listo. Resultados en {RES}")
