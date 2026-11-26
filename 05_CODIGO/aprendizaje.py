"""
Aprendizaje - el modelo aprende de las revisiones que hacen las personas y Claude en el visor.

Para que sirve (en simple): cada vez que alguien marca una zona como "mineria" o "no mineria" (o Claude da su opinion sobre una
zona), esa respuesta es un ejemplo nuevo. Aqui se juntan esos ejemplos, se sacan los pixeles de cada zona de la imagen que se
guardo al analizar el bloque, y se entrena un modelo nuevo que suma los ejemplos al banco de bloques (paso10). El modelo nuevo
se guarda como un archivo aparte (modelo_lgbm_aprendido_001.txt, 002, ...) y solo pasa a ser el modelo activo si pasa dos pruebas.

Etiquetas, de mayor a menor confianza (la de arriba manda para la misma zona):
  1. Personas  04_DATOS/etiquetas/revisiones_visor.jsonl   (peso 3.0; vale la ultima revision de cada zona)
  2. Claude    04_DATOS/opiniones_ia/{clave}_{id}.json     (alta peso 2.0, media peso 1.0; se ignoran 'dudoso' y confianza baja)
Si una persona dejo la zona como 'dudoso', esa zona no se usa (ni la opinion de Claude): la duda humana manda.

Las dos pruebas antes de promover:
  - Acuerdo con las etiquetas en zonas que el modelo NO vio (validacion cruzada por imagen): el modelo que aprende no puede
    coincidir menos que el que no aprende.
  - No empeorar en La Pampa (bloque de prueba, nunca entra al entrenamiento comparado): F1 baja menos de 0.03 y cobertura menos de 5 puntos.

LIMITES HONESTOS:
  - La opinion de Claude es una OPINION sobre una imagen de 20 m, no verdad de campo. Aprender de la IA puede copiar sus errores
    (y los del modelo, porque las zonas revisadas son las que el modelo ya marco). Por eso la etiqueta humana pesa mas, y el modelo
    solo se promueve si no empeora en La Pampa. Con pocas etiquetas las medidas de acuerdo son ruidosas: tomalas como indicio.
  - El "acuerdo" mide coincidencia con las etiquetas, no exactitud contra el terreno.

Uso (entorno g4g-ml):  python -I -u 05_CODIGO\\aprendizaje.py [forzar]
"""
import json
import re
import sys
import threading
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modelo_activo as ma  # noqa: E402  (liviano: no importa lightgbm)

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parents[1]
ANALISIS = RAIZ / "04_DATOS" / "analisis_bloques"
OPINIONES = RAIZ / "04_DATOS" / "opiniones_ia"
REVISIONES = RAIZ / "04_DATOS" / "etiquetas" / "revisiones_visor.jsonl"
RES = RAIZ / "04_DATOS" / "resultados"
ENT = RAIZ / "04_DATOS" / "entrenamiento"      # aqui solo vive la cache de la muestra base
INFO = RES / "modelos_aprendizaje.json"        # historial de corridas (lista JSON)
MIN_NUEVAS = 10          # etiquetas nuevas que disparan un aprendizaje recomendado
MIN_POR_CLASE = 4        # minimo de zonas de cada clase para aprender (salvo forzar)
MAX_PX_ZONA = 600        # pixeles que se toman de cada zona etiquetada
MAX_PLIEGUES = 10        # tope de grupos en la validacion cruzada (costo de computo)
PESOS = {"humano": 3.0, "alta": 2.0, "media": 1.0}
CAMPOS_METRICAS = ["version", "fecha", "n_etiquetas", "n_mineria", "n_no_mineria", "n_humano", "n_claude", "acuerdo_antes", "acuerdo_despues",
                   "n_zonas_eval", "f1_prueba_antes", "f1_prueba_despues", "cobertura_prueba_antes", "cobertura_prueba_despues",
                   "precision_zonas_prueba_antes", "precision_zonas_prueba_despues", "promovido", "motivo"]
ETAPAS = [(0.0, "Reuniendo etiquetas"), (0.08, "Sacando pixeles de las zonas"), (0.2, "Muestra base del banco"),
          (0.3, "Midiendo acuerdo en zonas no vistas"), (0.6, "Comparando en La Pampa"), (0.85, "Entrenando el modelo final")]

_candado = threading.Lock()
_estado = {"corriendo": False, "progreso": {"etapa": "", "frac": 0.0, "mensaje": ""}, "error": None}


# ---------------------------------------------------------------- lectura tolerante
def _json(ruta):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _analisis():
    """clave -> contenido del analisis (solo los que se pueden leer y tienen zonas)."""
    out = {}
    for f in sorted(Path(ANALISIS).glob("*.json")):
        d = _json(f)
        if isinstance(d, dict) and isinstance(d.get("zonas"), dict) and isinstance(d.get("resumen"), dict):
            out[d["resumen"].get("clave") or f.stem] = d
    return out


def _zonas_de(analisis):
    """(clave, id) -> (feature, resumen) de todos los analisis."""
    out = {}
    for clave, d in analisis.items():
        for f in d["zonas"].get("features", []):
            idz = (f.get("properties") or {}).get("id")
            if idz:
                out[(clave, idz)] = (f, d["resumen"])
    return out


def _revisiones():
    """(clave, id) -> ultima revision de una persona (todas las etiquetas, tambien 'dudoso'). Lineas danadas se saltan."""
    out = {}
    try:
        lineas = Path(REVISIONES).read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for ln in lineas:
        try:
            r = json.loads(ln)
            if isinstance(r, dict) and r.get("clave") and r.get("id") and r.get("etiqueta") in ("mineria", "no_mineria", "dudoso"):
                out[(r["clave"], r["id"])] = r
        except ValueError:
            continue
    return out


def _opiniones():
    """Lista de opiniones de Claude (dicts con clave, id, veredicto, confianza, modelo)."""
    out = []
    for f in sorted(Path(OPINIONES).glob("*.json")):
        if f.name == "consumo.json":
            continue
        d = _json(f)
        if not isinstance(d, dict) or d.get("veredicto") not in ("probable_mineria", "dudoso", "probable_no_mineria"):
            continue
        clave = d.get("clave") or f.stem.split("_")[0]
        idz = d.get("id_zona") or d.get("id") or f.stem.split("_", 1)[-1]
        out.append({"clave": clave, "id": idz, "veredicto": d["veredicto"], "confianza": d.get("confianza", "baja"), "modelo": d.get("modelo")})
    return out


# ---------------------------------------------------------------- 1. etiquetas
def etiquetas():
    """DataFrame con las etiquetas utilizables: clave, clave_img, id, etiqueta, origen, confianza, puntaje_modelo, area_ha, modelo, geometria."""
    zonas = _zonas_de(_analisis())
    filas, humanas = [], _revisiones()
    for (clave, idz), r in humanas.items():
        if r["etiqueta"] == "dudoso":
            continue
        f, res = zonas.get((clave, idz), (None, {}))
        p = (f or {}).get("properties", {})
        geo = r.get("geometria") or (f or {}).get("geometry")
        if not geo:
            continue
        filas.append({"clave": clave, "clave_img": r.get("clave_img") or res.get("clave_img"), "id": idz, "etiqueta": r["etiqueta"], "origen": "humano",
                      "confianza": "humano", "puntaje_modelo": r.get("puntaje_modelo", p.get("puntaje_modelo")), "area_ha": p.get("area_ha"),
                      "modelo": res.get("modelo") or "v2", "geometria": geo})
    for o in _opiniones():
        llave = (o["clave"], o["id"])
        if llave in humanas or o["veredicto"] == "dudoso" or o["confianza"] not in ("alta", "media") or llave not in zonas:
            continue   # la persona manda (incluida su duda); sin zona en el analisis no hay geometria
        f, res = zonas[llave]
        p = f.get("properties", {})
        filas.append({"clave": o["clave"], "clave_img": res.get("clave_img"), "id": o["id"], "etiqueta": "mineria" if o["veredicto"] == "probable_mineria" else "no_mineria",
                      "origen": "claude", "confianza": o["confianza"], "puntaje_modelo": p.get("puntaje_modelo"), "area_ha": p.get("area_ha"),
                      "modelo": o["modelo"] or res.get("modelo") or "v2", "geometria": f.get("geometry")})
    cols = ["clave", "clave_img", "id", "etiqueta", "origen", "confianza", "puntaje_modelo", "area_ha", "modelo", "geometria"]
    return pd.DataFrame(filas, columns=cols)


def _llaves(E):
    return [f"{r.clave}|{r.id}|{r.etiqueta}" for r in E.itertuples()]


# ---------------------------------------------------------------- 2. estado barato
def _historial():
    h = _json(INFO)
    return h if isinstance(h, list) else []


def estado():
    """Resumen barato para el visor (no carga rasters ni lightgbm)."""
    E = etiquetas()
    h = _historial()
    previas = set(h[-1].get("llaves", [])) if h else set()
    n_nuevas = sum(1 for k in _llaves(E) if k not in previas)
    with _candado:
        corriendo, progreso, error = _estado["corriendo"], dict(_estado["progreso"]), _estado["error"]
    return {"n_etiquetas": int(len(E)), "n_humano": int((E.origen == "humano").sum()), "n_claude": int((E.origen == "claude").sum()),
            "n_nuevas": n_nuevas, "recomendado": n_nuevas >= MIN_NUEVAS, "modelo_activo": ma.version(),
            "ultima": ({k: v for k, v in h[-1].items() if k != "llaves"} if h else None),
            "historial": [{k: x.get(k) for k in CAMPOS_METRICAS} for x in h[-10:]],
            "corriendo": corriendo, "progreso": progreso, "error": error}


# ---------------------------------------------------------------- 3. pixeles de las zonas etiquetadas
def _cargar_compuesto(ruta):
    """Lee un compuesto del visor (capas float16: NODATA -9999 queda -10000) y devuelve (datos 14xHxW, valido, ndvi, T)."""
    import nucleo_zonas as nz
    from affine import Affine
    z = np.load(ruta, allow_pickle=False)

    def capa(a):
        a = a.astype("float32")
        a[a < -9000] = nz.NODATA
        return a
    datos, valido = nz.variables_y_validez(capa(z["bandas"]), capa(z["ndvi"]), capa(z["ndwi"]), capa(z["bsi"]), capa(z["pend"]),
                                           z["n_obs"].astype("int16"), con_contexto=True)
    return datos, valido, capa(z["ndvi"]), Affine(*[float(v) for v in z["T"]]), int(z["epsg"][0])


def _pixeles_zonas(E, rng, aviso):
    """DataFrame de entrenamiento de las zonas etiquetadas (columnas TODAS + clase, origen, grupo, celda, peso, zona)."""
    import pyproj
    import paso10_reentrenar as p10
    from rasterio.features import rasterize
    from shapely.geometry import shape
    from shapely.ops import transform as sh_tr
    partes, sin_imagen, sin_pixeles = [], 0, 0
    for img, sub in E.groupby("clave_img", dropna=True):
        ruta = Path(ANALISIS) / f"{img}_compuesto.npz"
        if not ruta.exists():
            sin_imagen += len(sub)
            continue
        datos, valido, ndvi, T, epsg = _cargar_compuesto(ruta)   # una sola vez por imagen
        tr = pyproj.Transformer.from_crs(4326, epsg, always_xy=True).transform
        buenos = valido & (ndvi < 0.45) & (ndvi != -9999.0)      # como valid_ok del paso10
        for r in sub.itertuples():
            masc = rasterize([(sh_tr(tr, shape(r.geometria)), 1)], out_shape=valido.shape, transform=T, fill=0, dtype="uint8").astype(bool)
            masc &= buenos if r.etiqueta == "mineria" else valido
            ff, cc = np.nonzero(masc)
            if len(ff) == 0:
                sin_pixeles += 1
                continue
            sel = rng.choice(len(ff), size=min(MAX_PX_ZONA, len(ff)), replace=False)
            df = pd.DataFrame(datos[:, ff[sel], cc[sel]].T, columns=p10.TODAS)
            df["clase"] = 1 if r.etiqueta == "mineria" else 0
            df["origen"] = "visor_humano" if r.origen == "humano" else "visor_claude"
            df["grupo"] = df["celda"] = img
            df["peso"] = PESOS[r.confianza]
            df["zona"] = f"{r.clave}|{r.id}"
            partes.append(df)
    if sin_imagen:
        aviso.append(f"{sin_imagen} zonas etiquetadas no tienen la imagen guardada del bloque y no se usaron.")
    if sin_pixeles:
        aviso.append(f"{sin_pixeles} zonas no tienen pixeles utilizables (nubes o vegetacion densa) y no se usaron.")
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


# ---------------------------------------------------------------- muestra base (cache)
def _huella(p10, nombres):
    def sello(p):
        try:
            s = Path(p).stat()
            return [int(s.st_mtime), s.st_size]
        except OSError:
            return None
    return {"revision_ia": sello(p10.REVISION_IA), "bloques": [[n, sello(p10.BANCO / f"{n}.npz")] for n in nombres]}


def _muestra_base(p10, progreso):
    """Muestra del banco + piloto (la misma de entrenar() del paso10); lenta, por eso se guarda en cache."""
    nombres = p10.bloques_disponibles()
    huella = _huella(p10, nombres)
    cache, cache_h = Path(ENT) / "muestra_banco_cache.csv.gz", Path(ENT) / "muestra_banco_cache.json"
    if cache.exists() and _json(cache_h) == huella:
        try:
            return pd.read_csv(cache), True
        except (OSError, ValueError):
            pass
    progreso(0.2, "Armando la muestra del banco de bloques (lento; se guarda para la proxima vez)")
    D = p10.ensamblar(nombres, np.random.default_rng(p10.SEMILLA))
    D["peso"] = 1.0
    Path(ENT).mkdir(parents=True, exist_ok=True)
    D.to_csv(cache, index=False)
    cache_h.write_text(json.dumps(huella), encoding="utf-8")
    return D, False


# ---------------------------------------------------------------- 4. evaluacion
def _ajustar(p10, D):
    return p10.nuevo_modelo().fit(D[p10.TODAS], D.clase, sample_weight=D.peso)


def _por_zona(m, p10, Z):
    """Mediana del puntaje por pixel de cada zona -> Series indexada por zona."""
    p = m.predict_proba(Z[p10.TODAS])[:, 1]
    return pd.Series(p, index=Z.index).groupby(Z.zona).median()


def _acuerdo(pred, Z):
    """% de zonas donde la clase predicha (mediana >= UMBRAL) coincide con la etiqueta: total y por origen."""
    import paso10_reentrenar as p10
    z = Z.drop_duplicates("zona").set_index("zona")
    ok = ((pred.reindex(z.index) >= p10.UMBRAL).astype(int) == z.clase)
    tot = {"total": round(100 * float(ok.mean()), 1), "n": int(len(z))}
    for o in ("visor_humano", "visor_claude"):
        s = ok[z.origen == o]
        tot[o] = (round(100 * float(s.mean()), 1) if len(s) else None, int(len(s)))
    return tot


def _acuerdo_cruzado(p10, base, Z, progreso):
    """Acuerdo antes (modelo solo con base) y despues (base + etiquetas de OTROS grupos) en zonas no vistas."""
    antes = _acuerdo(_por_zona(_ajustar(p10, base), p10, Z), Z)
    grupos = sorted(Z.grupo.unique())
    if len(grupos) < 3:                                       # pocas imagenes: se deja una zona afuera cada vez
        clave_g = Z.zona
        grupos = sorted(Z.zona.unique())
    else:
        clave_g = Z.grupo
    pliegue = {g: i % MAX_PLIEGUES for i, g in enumerate(grupos)}
    num = clave_g.map(pliegue)
    pred = []
    for k in sorted(num.unique()):
        fuera = num == k
        pred.append(_por_zona(_ajustar(p10, pd.concat([base, Z[~fuera]], ignore_index=True)), p10, Z[fuera]))
        progreso(0.3 + 0.3 * (k + 1) / (num.max() + 1), f"Validacion cruzada {k + 1} de {num.max() + 1}")
    return antes, _acuerdo(pd.concat(pred), Z)


def _f(x):
    """Numero listo para JSON (NaN -> None)."""
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else x


def _prueba_la_pampa(p10, base, Z, aviso):
    """Compara en La Pampa el modelo solo con banco contra el que suma las etiquetas. Devuelve dict con metricas y no_empeora."""
    if p10.PRUEBA not in p10.bloques_disponibles():
        aviso.append(f"Falta el bloque de prueba {p10.PRUEBA}: no se pudo comprobar que no empeore.")
        return {"no_empeora": False}
    sin = base[base.grupo != p10.PRUEBA]
    modelos = {"antes": _ajustar(p10, sin), "despues": _ajustar(p10, pd.concat([sin, Z], ignore_index=True))}
    d = p10.cargar(p10.PRUEBA)
    px = {r["modelo"]: r for r in p10.evaluar_en_bloque(modelos, d)}
    zn = {r["modelo"]: r for r in p10.evaluar_zonas(modelos, d)}
    out = {}
    for k in ("antes", "despues"):
        out[f"f1_prueba_{k}"] = _f(px[k]["f1"])
        out[f"cobertura_prueba_{k}"] = _f(zn[k]["cobertura_pct"])
        out[f"precision_zonas_prueba_{k}"] = _f(zn[k]["precision_zonas_pct"])
    try:
        out["no_empeora"] = bool(out["f1_prueba_antes"] - out["f1_prueba_despues"] < 0.03
                                 and out["cobertura_prueba_antes"] - out["cobertura_prueba_despues"] < 5)
    except TypeError:
        out["no_empeora"] = False
        aviso.append("En La Pampa no se pudo calcular alguna medida; se asume que no se puede confirmar que no empeore.")
    return out


# ---------------------------------------------------------------- 5. aprender
def _siguiente_version():
    nums = [int(m.group(1)) for f in Path(RES).glob("modelo_lgbm_aprendido_*.txt") if (m := re.search(r"_(\d+)\.txt$", f.name))]
    return f"{max(nums, default=0) + 1:03d}"


def _guardar_info(registro):
    h = _historial()
    h.append(registro)
    Path(INFO).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(INFO).with_suffix(".tmp")
    tmp.write_text(json.dumps(h, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(INFO)


def aprender(progreso=lambda frac, msg: None, forzar=False):
    """Aprende de las etiquetas nuevas. Devuelve el registro de la corrida (tambien se agrega a INFO) o {'ok': False, 'motivo': ...}."""
    t0 = time.time()
    progreso(0.0, "Reuniendo las etiquetas de personas y de Claude")
    E = etiquetas()
    n_min, n_no = int((E.etiqueta == "mineria").sum()), int((E.etiqueta == "no_mineria").sum())
    if (n_min < MIN_POR_CLASE or n_no < MIN_POR_CLASE) and not forzar:
        return {"ok": False, "motivo": f"Aun hay pocas revisiones (mineria {n_min}, no mineria {n_no}; hacen falta al menos {MIN_POR_CLASE} de cada una)."}
    if n_min == 0 or n_no == 0:
        return {"ok": False, "motivo": f"Sin etiquetas de las dos clases no se puede entrenar (mineria {n_min}, no mineria {n_no})."}
    import paso10_reentrenar as p10
    aviso = []
    rng = np.random.default_rng(p10.SEMILLA)
    progreso(0.08, "Sacando los pixeles de cada zona etiquetada")
    Z = _pixeles_zonas(E, rng, aviso)
    if Z.empty or Z.clase.nunique() < 2:
        return {"ok": False, "motivo": "Las zonas etiquetadas no dan pixeles utilizables de las dos clases (falta la imagen del bloque o hay nubes).", "aviso": aviso}
    base, _ = _muestra_base(p10, progreso)
    progreso(0.3, "Midiendo el acuerdo con las etiquetas en zonas que el modelo no vio")
    antes, despues = _acuerdo_cruzado(p10, base, Z, progreso)
    progreso(0.6, "Comparando contra el bloque de prueba (La Pampa)")
    prueba = _prueba_la_pampa(p10, base, Z, aviso)
    progreso(0.85, "Entrenando el modelo final con todo")
    final = _ajustar(p10, pd.concat([base, Z], ignore_index=True))
    num = _siguiente_version()
    archivo, version = f"modelo_lgbm_aprendido_{num}.txt", f"aprendido_{num}"
    Path(RES).mkdir(parents=True, exist_ok=True)
    final.booster_.save_model(str(Path(RES) / archivo))
    sube = despues["total"] >= antes["total"]
    if prueba["no_empeora"] and sube:
        promovido, motivo = True, "Mejoro o mantuvo el acuerdo con las revisiones y no empeoro en La Pampa."
    elif not prueba["no_empeora"]:
        promovido, motivo = False, "Empeoro en La Pampa (o no se pudo comprobar); se guardo el modelo pero se sigue usando el anterior."
    else:
        promovido, motivo = False, "Coincide menos con las revisiones en zonas nuevas que el modelo anterior; se guardo pero no se uso."
    reg = {"ok": True, "version": version, "archivo": archivo, "fecha": time.strftime("%Y-%m-%d %H:%M"), "n_etiquetas": int(len(E)), "n_mineria": n_min,
           "n_no_mineria": n_no, "n_humano": int((E.origen == "humano").sum()), "n_claude": int((E.origen == "claude").sum()),
           "acuerdo_antes": antes["total"], "acuerdo_despues": despues["total"], "n_zonas_eval": antes["n"],
           "acuerdo_por_origen": {"antes": {o: antes[o] for o in ("visor_humano", "visor_claude")}, "despues": {o: despues[o] for o in ("visor_humano", "visor_claude")}},
           **{k: v for k, v in prueba.items() if k != "no_empeora"}, "no_empeora": prueba["no_empeora"], "promovido": promovido, "motivo": motivo,
           "llaves": _llaves(E), "pixeles_etiquetas": int(len(Z)), "pixeles_total": int(len(base) + len(Z)), "segundos": round(time.time() - t0),
           "aviso": " ".join(aviso + ["Las etiquetas de Claude son una opinion sobre una imagen de 20 m, no verdad de campo; aprender de ellas puede copiar sus errores."])}
    if promovido:
        ma.fijar(archivo, version, fecha=reg["fecha"], acuerdo_antes=reg["acuerdo_antes"], acuerdo_despues=reg["acuerdo_despues"])
    _guardar_info(reg)
    progreso(1.0, "Listo: " + motivo)
    return reg


# ---------------------------------------------------------------- 6. en segundo plano
def _avance(frac, msg):
    etapa = [n for c, n in ETAPAS if c <= frac][-1]
    with _candado:
        _estado["progreso"] = {"etapa": etapa, "frac": round(float(frac), 3), "mensaje": msg}


def aprender_en_segundo_plano(forzar=False):
    """Lanza aprender() en un hilo y vuelve de inmediato. Si ya hay uno corriendo no lanza otro. Errores en estado()['error']."""
    with _candado:
        if _estado["corriendo"]:
            return {"iniciado": False, "corriendo": True}
        _estado.update(corriendo=True, error=None, progreso={"etapa": ETAPAS[0][1], "frac": 0.0, "mensaje": "Empezando"})

    def trabajo():
        try:
            r = aprender(_avance, forzar=forzar)
            if not r.get("ok"):
                with _candado:
                    _estado["error"] = r.get("motivo", "No se pudo aprender.")
        except Exception as e:  # noqa: BLE001  (no debe tumbar el servidor)
            with _candado:
                _estado["error"] = f"{type(e).__name__}: {e}"
        finally:
            with _candado:
                _estado["corriendo"] = False
    threading.Thread(target=trabajo, daemon=True, name="aprendizaje").start()
    return {"iniciado": True, "corriendo": True}


# ---------------------------------------------------------------- 7. modelo vs Claude
def _tabla(grupos, campo):
    out = []
    for nombre, c in grupos:
        den = c["mineria"] + c["no_mineria"]
        out.append({campo: nombre, "n": c["n"], "mineria": c["mineria"],
                    "no_mineria": c["no_mineria"], "dudoso": c["dudoso"], "precision_pct": round(100 * c["mineria"] / den, 1) if den else None})
    return out


def precision_vs_ia():
    """Comparacion modelo vs Claude para el visor (sin rasters): totales, por banda de puntaje, por version del modelo y humano vs Claude."""
    an = _analisis()
    zonas = _zonas_de(an)
    op = _opiniones()
    humanas = _revisiones()
    cuenta = {"probable_mineria": 0, "dudoso": 0, "probable_no_mineria": 0}
    bandas, modelos, hc = {}, {}, [0, 0]
    clave_v = {"probable_mineria": "mineria", "dudoso": "dudoso", "probable_no_mineria": "no_mineria"}
    for o in op:
        cuenta[o["veredicto"]] += 1
        f, res = zonas.get((o["clave"], o["id"]), (None, {}))
        punt = ((f or {}).get("properties") or {}).get("puntaje_modelo")
        banda = None if punt is None else "0-50" if punt < 50 else "50-70" if punt < 70 else "70-100"
        for dic, k in ((bandas, banda), (modelos, o["modelo"] or res.get("modelo") or "v2")):
            if k is not None:
                c = dic.setdefault(k, {"n": 0, "mineria": 0, "no_mineria": 0, "dudoso": 0})
                c["n"] += 1
                c[clave_v[o["veredicto"]]] += 1
        h = humanas.get((o["clave"], o["id"]))
        if h and h["etiqueta"] != "dudoso" and o["veredicto"] != "dudoso":
            hc[0] += 1
            hc[1] += int(clave_v[o["veredicto"]] == h["etiqueta"])
    den = cuenta["probable_mineria"] + cuenta["probable_no_mineria"]
    orden = ["0-50", "50-70", "70-100"]
    return {"n_zonas": len(op), "claude_mineria": cuenta["probable_mineria"], "claude_dudoso": cuenta["dudoso"], "claude_no_mineria": cuenta["probable_no_mineria"],
            "precision_estimada_pct": round(100 * cuenta["probable_mineria"] / den, 1) if den else None,
            "por_banda": _tabla([(b, bandas[b]) for b in orden if b in bandas], "banda"),
            "por_modelo": _tabla([(m, modelos[m]) for m in sorted(modelos)], "modelo"),
            "humano_vs_claude": {"n": hc[0], "coinciden": hc[1], "pct": round(100 * hc[1] / hc[0], 1) if hc[0] else None}}


if __name__ == "__main__":
    r = aprender(lambda f, m: print(f"  [{f * 100:3.0f}%] {m}", flush=True), forzar="forzar" in sys.argv[1:])
    print(json.dumps({k: v for k, v in r.items() if k != "llaves"}, indent=1, ensure_ascii=False))
