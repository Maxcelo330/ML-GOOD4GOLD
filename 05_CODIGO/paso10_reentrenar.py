"""
Paso 10 - Reentrenar el modelo con MUCHOS lugares (no solo el norte de La Paz) y medirlo contra una fuente independiente.

Por que: el modelo v1 se entreno con 9 zonas mineras de laderas del norte de La Paz y en Madre de Dios (terreno plano)
marca solo ~17 % del terreno removido. Aqui se le suman bloques de muchos lugares (banco_bloques.py) donde la
mineria viene de MapBiomas (clase 30 en 2023 Y 2024) y los "no mineria" incluyen rios con bancos de arena, pastizales,
agricultura, ciudad y laderas andinas, mas las revisiones que hagan una persona o Claude (ver abajo).

Etiquetas, de mayor a menor confianza (la de arriba manda sobre la de abajo):
  1. Revision de una persona en el visor        04_DATOS/etiquetas/revisiones_visor.jsonl
  2. Revision de Claude (IA) de objetos dudosos 04_DATOS/etiquetas/revision_ia.csv   (paso10b)
  3. MapBiomas (clasificacion automatica Landsat 30 m: NO es verdad de campo)
  4. Etiquetas del piloto (propuestas por Claude)  muestra_piloto.csv.gz

Como se mide (honesto): el bloque de La Pampa (Madre de Dios) NUNCA se usa para entrenar el modelo que se examina en el;
ademas se deja un bloque afuera cada vez ("leave-one-block-out"). Se compara contra el modelo v1. Las etiquetas de
MapBiomas son tambien una estimacion, asi que las cifras miden coincidencia con ese mapa, no exactitud contra el terreno.

Como correrlo (entorno g4g-ml):
  python 05_CODIGO\\paso10_reentrenar.py evaluar     compara v1 y el modelo nuevo
  python 05_CODIGO\\paso10_reentrenar.py entrenar    entrena con todo y guarda modelo_lgbm_v2.txt
"""
import json
import sys
import time
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from sklearn.metrics import average_precision_score, precision_recall_fscore_support

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nucleo_zonas as nz  # noqa: E402

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parents[1]
BANCO = RAIZ / "04_DATOS" / "banco_bloques"
RES = RAIZ / "04_DATOS" / "resultados"
ENT = RAIZ / "04_DATOS" / "entrenamiento"
REVISION_IA = RAIZ / "04_DATOS" / "etiquetas" / "revision_ia.csv"
VARIABLES = nz.VARIABLES                              # las 10 variables del modelo v1
TODAS = nz.VARIABLES + nz.VARIABLES_CONTEXTO         # + 4 de contexto (modelo v2)
SEMILLA = 42
CLASE_MB = 30
MAX_POS = 1500          # pixeles mineros que se toman de cada bloque
MAX_NEG_PELADO = 1500   # no mineros "dificiles" (poca vegetacion) por bloque
MAX_NEG_OTROS = 800     # no mineros "faciles" por bloque
BUFFER_PX = 5           # los no mineros se toman a mas de 100 m de cualquier mineria de MapBiomas
CON_CONTEXTO = True      # el modelo v2 final usa las variables de contexto (se decide con "evaluar")
PRUEBA = "mdd_prueba"  # bloque que nunca entrena el modelo que se examina en el
UMBRAL = 0.5


def log(m):
    print(f"[{time.time() - T0:5.0f} s] {m}", flush=True)


T0 = time.time()


# ---------------------------------------------------------------- lectura de un bloque del banco
def cargar(nombre):
    z = np.load(BANCO / f"{nombre}.npz", allow_pickle=False)
    d = {k: z[k] for k in z.files}
    d["meta"] = json.loads(str(d["meta"]))
    d["nombre"] = nombre
    d["datos"], d["valido"] = nz.variables_y_validez(d["bandas"], d["ndvi"], d["ndwi"], d["bsi"], d["pend"], d["n_obs"].astype("int16"), con_contexto=True)
    d["mb"] = (d["mb2023"] == CLASE_MB) & (d["mb2024"] == CLASE_MB)          # mineria en los dos anios
    d["mb_alguno"] = (d["mb2023"] == CLASE_MB) | (d["mb2024"] == CLASE_MB)
    return d


def revision_ia(d):
    """Mascaras (mineria, no_mineria, dudoso) de los objetos de este bloque que revisaron Claude o una persona (paso10b)."""
    forma = d["mb"].shape
    m = [np.zeros(forma, bool) for _ in range(3)]
    ruta_obj = ENT / "objetos_revision" / f"{d['nombre']}_objetos.npz"
    if REVISION_IA.exists() and ruta_obj.exists():
        t = pd.read_csv(REVISION_IA)
        t = t[t.bloque == d["nombre"]]
        lab = np.load(ruta_obj)["lab"]
        for fila in t.itertuples():
            k = {"mineria": 0, "no_mineria": 1, "dudoso": 2}.get(fila.etiqueta)
            if k is not None:
                m[k] |= lab == fila.objeto
    return m


def muestra(d, rng):
    """Pixeles de entrenamiento de un bloque: DataFrame con las 10 variables, clase, origen, grupo.

    Mineria = MapBiomas (2 anios), corregida por la revision de IA/persona: lo que dijeron 'no_mineria' sale de los
    positivos y pasa a ser un negativo dificil; lo 'dudoso' no se usa en ningun sentido."""
    ia_min, ia_no, ia_dud = revision_ia(d)
    valido = d["valido"]
    mb = (d["mb"] & ~ia_no & ~ia_dud) | ia_min
    mb_alguno = (d["mb_alguno"] & ~ia_no) | ia_min
    pos = mb & valid_ok(d) & ndi.binary_erosion(mb, iterations=1)
    cerca = ndi.binary_dilation(mb_alguno | ia_dud, iterations=BUFFER_PX)
    pelado = valido & ~cerca & (d["ndvi"] < 0.35) & (d["ndvi"] != nz.NODATA)
    otros = valido & ~cerca & ~pelado & ~ia_no
    ia_neg = valido & ia_no & ~ia_dud
    filas = []
    for mascara, k, clase, origen in ((pos, MAX_POS, 1, "mineria_mapbiomas_o_ia"), (pelado, MAX_NEG_PELADO, 0, "no_mineria_pelado"),
                                      (otros, MAX_NEG_OTROS, 0, "no_mineria_otros"), (ia_neg, MAX_NEG_PELADO, 0, "no_mineria_revision_ia")):
        ff, cc = np.nonzero(mascara)
        if len(ff) == 0:
            continue
        sel = rng.choice(len(ff), size=min(k, len(ff)), replace=False)
        df = pd.DataFrame(d["datos"][:, ff[sel], cc[sel]].T, columns=TODAS)
        df["clase"], df["origen"], df["grupo"] = clase, origen, d["nombre"]
        # cuadro de 5 km (250 px) dentro del bloque, para no mezclar vecinos entre entrenamiento y examen
        df["celda"] = d["nombre"] + "_" + (ff[sel] // 250).astype(str) + "_" + (cc[sel] // 250).astype(str)
        filas.append(df)
    return pd.concat(filas, ignore_index=True) if filas else pd.DataFrame()


def valid_ok(d):
    """Pixel utilizable y sin vegetacion densa (los bordes de MapBiomas a veces caen sobre monte)."""
    return d["valido"] & (d["ndvi"] < 0.45) & (d["ndvi"] != nz.NODATA)


def piloto():
    """Muestra de entrenamiento del piloto (paso5) con las 4 variables de contexto (se calculan una vez desde los rasters del piloto)."""
    cache = ENT / "muestra_piloto_ctx.csv.gz"
    if cache.exists():
        D = pd.read_csv(cache)
    else:
        import rasterio
        D = pd.read_csv(ENT / "muestra_piloto.csv.gz")
        comp = RAIZ / "04_DATOS" / "imagenes" / "compuesto"
        with rasterio.open(comp / "ndvi_2026.tif") as s1, rasterio.open(comp / "ndwi_2026.tif") as s2:
            ndvi, ndwi, T = s1.read(1).astype("float32"), s2.read(1).astype("float32"), s1.transform
        ctx = nz.contexto(ndvi, ndwi)
        col = np.clip(((D.x.to_numpy() - T.c) / T.a).astype(int), 0, ndvi.shape[1] - 1)
        fil = np.clip(((T.f - D.y.to_numpy()) / -T.e).astype(int), 0, ndvi.shape[0] - 1)
        for i, nombre in enumerate(nz.VARIABLES_CONTEXTO):
            D[nombre] = ctx[i, fil, col]
        D.to_csv(cache, index=False)
    D = D[TODAS + ["clase", "origen", "bloque", "pueblo"]].copy()
    D["grupo"] = "piloto"
    D["celda"] = "piloto_" + D.bloque.astype(str)
    D["origen"] = "piloto_" + D.origen
    return D.drop(columns=["bloque", "pueblo"])


def columnas_de(m):
    """Variables que usa un modelo (en orden)."""
    return list(m.feature_name_) if hasattr(m, "feature_name_") else TODAS[:m.num_feature()]


def matriz(d, m, mascara):
    idx = [TODAS.index(c) for c in columnas_de(m)]
    return d["datos"][idx][:, mascara].T


def nuevo_modelo(**kw):
    p = dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=20, subsample=0.8, subsample_freq=1,
             colsample_bytree=0.8, class_weight="balanced", random_state=SEMILLA, n_jobs=-1, verbose=-1)
    p.update(kw)
    return lgb.LGBMClassifier(**p)


# ---------------------------------------------------------------- evaluacion sobre un bloque completo
def evaluar_en_bloque(modelos, d):
    """Para cada modelo (nombre -> Booster/LGBM), mide pixel a pixel contra MapBiomas en un bloque entero.

    Positivos = mineria de MapBiomas (2 anios). Negativos = lo demas a mas de 100 m de cualquier mineria de MapBiomas.
    Devuelve una lista de dicts."""
    valido = d["valido"]
    cerca = ndi.binary_dilation(d["mb_alguno"], iterations=BUFFER_PX)
    eval_ = valido & (d["mb"] | ~cerca)
    y = d["mb"][eval_].astype(int)
    out = []
    for nombre, m in modelos.items():
        X = matriz(d, m, eval_)
        p = m.predict(X) if isinstance(m, lgb.Booster) else m.predict_proba(X)[:, 1]
        pred = p >= UMBRAL
        if y.sum() and y.sum() < len(y):
            pr, rc, f1, _ = precision_recall_fscore_support(y, pred, labels=[1], zero_division=0)
            ap = average_precision_score(y, p)
        else:
            pr = rc = f1 = [float("nan")]
            ap = float("nan")
        out.append({"bloque": d["nombre"], "modelo": nombre, "pos_mapbiomas_px": int(y.sum()), "neg_px": int((1 - y).sum()),
                    "precision": round(float(pr[0]), 3), "recall": round(float(rc[0]), 3), "f1": round(float(f1[0]), 3), "ap": round(float(ap), 3),
                    "pixeles_marcados": int(pred.sum())})
    return out


def probabilidad(m, d):
    """Puntaje de cada pixel del bloque (NODATA donde no se puede puntuar), con un Booster o un LGBMClassifier."""
    p = np.full(d["valido"].shape, nz.NODATA, "float32")
    X = matriz(d, m, d["valido"])
    p[d["valido"]] = m.predict(X) if isinstance(m, lgb.Booster) else m.predict_proba(X)[:, 1]
    return p


def evaluar_zonas(modelos, d):
    """Mide el PRODUCTO (las zonas que ve la persona): las mismas reglas del analisis de bloques fuera del piloto (modo relajado).

    ha_marcadas      : hectareas de zonas que salen
    precision_zonas  : % de esas hectareas que MapBiomas tambien marca como mineria (algun anio)
    cobertura        : % de la mineria de MapBiomas (2 anios) que queda dentro de alguna zona
    """
    from affine import Affine
    from rasterio.features import rasterize
    T = Affine(*[float(v) for v in d["T"]])
    out = []
    for nombre, m in modelos.items():
        p = probabilidad(m, d)
        gdf, info = nz.extraer_zonas(p, d["ndvi"], d["ndwi"], d["n_obs"].astype("float32"), T, f"EPSG:{int(d['epsg'][0])}", **nz.RELAJADO)
        if len(gdf):
            zp = rasterize([(g, 1) for g in gdf.geometry], out_shape=p.shape, transform=T, fill=0, dtype="uint8").astype(bool)
        else:
            zp = np.zeros(p.shape, bool)
        ha = float(zp.sum()) * 0.04
        out.append({"bloque": d["nombre"], "modelo": nombre, "zonas": int(len(gdf)), "ha_marcadas": round(ha, 0),
                    "ha_mineria_mapbiomas": round(float(d["mb"].sum()) * 0.04, 0),
                    "precision_zonas_pct": round(100 * float(d["mb_alguno"][zp].mean()), 0) if zp.any() else float("nan"),
                    "cobertura_pct": round(100 * float(zp[d["mb"]].mean()), 0) if d["mb"].any() else float("nan")})
    return out


def bloques_disponibles():
    return sorted(p.stem for p in BANCO.glob("*.npz"))


def ensamblar(nombres, rng, incluir_piloto=True):
    partes = [muestra(cargar(n), rng) for n in nombres]
    if incluir_piloto:
        partes.append(piloto())
    return pd.concat([p for p in partes if len(p)], ignore_index=True)


def evaluar():
    nombres = bloques_disponibles()
    if PRUEBA not in nombres:
        sys.exit(f"Falta el bloque de prueba {PRUEBA}. Corre banco_bloques.py.")
    log(f"Bloques en el banco: {len(nombres)}  ({', '.join(nombres)})")
    v1 = lgb.Booster(model_file=str(RES / "modelo_lgbm_v1.txt"))
    px, zn = [], []
    rng = np.random.default_rng(SEMILLA)
    # Cada bloque se examina con un modelo que NO lo vio (y el bloque de La Pampa nunca entra al entrenamiento de ningun modelo examinado)
    for n in nombres:
        D = ensamblar([x for x in nombres if x not in (n, PRUEBA)], rng)
        m = nuevo_modelo().fit(D[VARIABLES], D.clase)
        mc = nuevo_modelo().fit(D[TODAS], D.clase)
        d = cargar(n)
        modelos = {"v1 (solo piloto)": v1, "v2 (banco, 10 vars)": m, "v2c (banco, + contexto)": mc}
        px += evaluar_en_bloque(modelos, d)
        zn += evaluar_zonas(modelos, d)
        log(f"   {n}: listo")
    tp, tz = pd.DataFrame(px), pd.DataFrame(zn)
    ENT.mkdir(parents=True, exist_ok=True)
    tp.to_csv(ENT / "evaluacion_pixeles.csv", index=False)
    tz.to_csv(ENT / "evaluacion_zonas.csv", index=False)
    pd.set_option("display.width", 220)
    print("\n=== POR ZONAS (lo que ve la persona; mismas reglas que el visor fuera del piloto) ===")
    print(tz.to_string(index=False))
    mi = tp[tp.pos_mapbiomas_px > 1000]
    for modelo in sorted(mi.modelo.unique()):
        s = mi[mi.modelo == modelo]
        print(f"\nPixel a pixel, bloques con mineria, {modelo}: F1 medio {s.f1.mean():.2f} | precision {s.precision.mean():.2f} | recall {s.recall.mean():.2f}")


def entrenar():
    nombres = bloques_disponibles()
    rng = np.random.default_rng(SEMILLA)
    D = ensamblar(nombres, rng)    # el modelo final SI usa todos los bloques (tambien La Pampa)
    log(f"Entrenando con {len(D)} pixeles de {len(nombres)} bloques + piloto | mineria {int(D.clase.sum())}")
    cols = TODAS if CON_CONTEXTO else VARIABLES
    m = nuevo_modelo().fit(D[cols], D.clase)
    m.booster_.save_model(str(RES / "modelo_lgbm_v2.txt"))
    imp = pd.DataFrame({"variable": cols, "importancia": m.booster_.feature_importance("gain")})
    imp["importancia"] = (imp.importancia / imp.importancia.sum()).round(3)
    print(imp.sort_values("importancia", ascending=False).to_string(index=False))
    (RES / "modelo_v2_info.json").write_text(json.dumps({
        "fecha": time.strftime("%Y-%m-%d"), "semilla": SEMILLA, "variables": cols, "bloques": nombres, "pixeles": int(len(D)),
        "pixeles_mineria": int(D.clase.sum()), "por_origen": D.origen.value_counts().to_dict(),
        "aviso": "Mineria = MapBiomas 2023 y 2024 (clasificacion automatica, no verdad de campo) + etiquetas propuestas por Claude del piloto. "
                 "Los puntajes no son probabilidades."}, indent=2, ensure_ascii=False), encoding="utf-8")
    log("Guardado modelo_lgbm_v2.txt")


if __name__ == "__main__":
    {"evaluar": evaluar, "entrenar": entrenar}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
