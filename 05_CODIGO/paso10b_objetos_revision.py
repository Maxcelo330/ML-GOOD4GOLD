"""
Paso 10b - Revision con IA de los desacuerdos entre el modelo y MapBiomas (la IA ayuda a limpiar las etiquetas).

Que hace:
  generar : con el modelo v2 provisional, busca en cada bloque del banco dos tipos de "objetos" (manchas de mas de 5 ha):
              - FP: el modelo marca mineria y MapBiomas no  (puede ser un falso positivo del modelo o mineria que MapBiomas no vio)
              - FN: MapBiomas marca mineria y el modelo no  (puede ser un error del modelo o un error de MapBiomas)
            y arma hojas de imagenes (color natural con contorno, color natural de cerca, falso color) para que Claude (con
            subagentes) o una persona las mire y diga: mineria / no_mineria / dudoso.
  aplicar : lee las respuestas (04_DATOS/etiquetas/revision_ia.csv) y las deja listas para paso10_reentrenar.py.

Las respuestas son la opinion de una IA sobre una imagen de 20 m: NO son verdad de campo. Se usan para limpiar etiquetas
dudosas, y todo lo que dice "dudoso" se ignora al entrenar.

Salida: 04_DATOS/entrenamiento/objetos_revision/  (hojas PNG, indice.csv y las mascaras de cada bloque; no va a git)
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nucleo_zonas as nz  # noqa: E402
import paso10_reentrenar as p10  # noqa: E402

RAIZ = p10.RAIZ
OUT = RAIZ / "04_DATOS" / "entrenamiento" / "objetos_revision"
MIN_PX = 125                # 5 ha a 20 m
POR_BLOQUE = {"mineria": (2, 2), "control": (2, 0)}     # (FP, FN) maximos por bloque
POR_HOJA = 6
LADO = 300


def _estirar(a, lo, hi):
    ok = np.isfinite(a) & (a != nz.NODATA)
    return np.clip((np.where(ok, a, lo) - lo) / (hi - lo), 0, 1)


def imagenes(d):
    B = d["bandas"]
    nat = (np.stack([_estirar(B[2], .02, .28), _estirar(B[1], .02, .28), _estirar(B[0], .02, .28)], -1) ** 0.75 * 255).astype("uint8")
    fal = (np.stack([_estirar(B[4], .03, .40), _estirar(B[3], .05, .50), _estirar(B[2], .02, .28)], -1) * 255).astype("uint8")
    return Image.fromarray(nat), Image.fromarray(fal)


def objetos_de_bloque(d, modelo):
    """Devuelve la imagen de etiquetas de objetos (0 = nada) y la lista de objetos del bloque."""
    p = np.full(d["valido"].shape, nz.NODATA, "float32")
    p[d["valido"]] = modelo.predict_proba(p10.matriz(d, modelo, d["valido"]))[:, 1]
    agua = np.isfinite(d["ndwi"]) & (d["ndwi"] > 0)
    cerca = ndi.binary_dilation(d["mb_alguno"], iterations=p10.BUFFER_PX)
    fp = (p >= p10.UMBRAL) & d["valido"] & ~cerca & ~agua
    fn = d["mb"] & d["valido"] & (p < p10.UMBRAL) & ~agua
    nfp, nfn = POR_BLOQUE[d["meta"]["tipo"]]
    lab = np.zeros(p.shape, "int32")
    objs, k = [], 0
    for tipo, m, tope in (("FP", fp, nfp), ("FN", fn, nfn)):
        if tope == 0:
            continue
        m = ndi.binary_opening(ndi.binary_closing(m, np.ones((3, 3)), iterations=2), np.ones((3, 3)))
        et, n = ndi.label(m)
        if n == 0:
            continue
        tam = ndi.sum(m, et, np.arange(1, n + 1))
        for i in np.argsort(-tam)[:tope]:
            if tam[i] < MIN_PX:
                break
            k += 1
            lab[et == i + 1] = k
            ff, cc = np.nonzero(et == i + 1)
            objs.append({"bloque": d["nombre"], "objeto": k, "tipo": tipo, "area_ha": round(float(tam[i]) * 0.04, 1),
                         "puntaje_medio": round(float(p[et == i + 1].mean()), 2), "mb_pct": round(100 * float(d["mb"][et == i + 1].mean()), 0),
                         "f0": int(ff.min()), "f1": int(ff.max()), "c0": int(cc.min()), "c1": int(cc.max())})
    return lab, objs


def recorte(img, o, lab, margen, contorno):
    h, w = lab.shape
    m = max(int(margen), 20)
    c = (max(o["c0"] - m, 0), max(o["f0"] - m, 0), min(o["c1"] + 1 + m, w), min(o["f1"] + 1 + m, h))
    im = img.crop(c)
    esc = LADO / max(im.size)
    im = im.resize((max(1, round(im.width * esc)), max(1, round(im.height * esc))), Image.LANCZOS)
    if contorno:
        borde = (lab[c[1]:c[3], c[0]:c[2]] == o["objeto"]) & ~ndi.binary_erosion(lab[c[1]:c[3], c[0]:c[2]] == o["objeto"])
        m_img = Image.fromarray((borde * 255).astype("uint8")).resize(im.size, Image.NEAREST)
        a = np.array(im)
        a[np.array(m_img) > 0] = (255, 235, 0)
        im = Image.fromarray(a)
    lienzo = Image.new("RGB", (LADO, LADO), (30, 30, 30))
    lienzo.paste(im, ((LADO - im.width) // 2, (LADO - im.height) // 2))
    return lienzo


def generar():
    OUT.mkdir(parents=True, exist_ok=True)
    todos = []
    nombres = p10.bloques_disponibles()
    rng0 = np.random.default_rng(p10.SEMILLA)
    for n in nombres:
        # Cada bloque se mira con un modelo que NO lo vio (si no, el modelo ya "sabe la respuesta" y no habria desacuerdos utiles)
        D = p10.ensamblar([x for x in nombres if x not in (n, p10.PRUEBA)], rng0)
        modelo = p10.nuevo_modelo().fit(D[p10.TODAS], D.clase)
        d = p10.cargar(n)
        lab, objs = objetos_de_bloque(d, modelo)
        np.savez_compressed(OUT / f"{n}_objetos.npz", lab=lab)
        nat, fal = imagenes(d)
        for o in objs:
            o["_nat"], o["_fal"], o["_lab"] = nat, fal, lab
        todos += objs
        print(f"{n}: {len(objs)} objetos ({sum(o['tipo'] == 'FP' for o in objs)} FP, {sum(o['tipo'] == 'FN' for o in objs)} FN)", flush=True)
    # orden mezclado (semilla fija) para que cada hoja tenga de todo
    rng = np.random.default_rng(p10.SEMILLA)
    orden = rng.permutation(len(todos))
    filas = []
    for h in range(0, len(todos), POR_HOJA):
        grupo = [todos[i] for i in orden[h:h + POR_HOJA]]
        hoja = Image.new("RGB", (LADO * 3 + 160, (LADO + 6) * len(grupo)), (255, 255, 255))
        d_ = ImageDraw.Draw(hoja)
        for r, o in enumerate(grupo):
            y = r * (LADO + 6)
            lado_px = max(o["f1"] - o["f0"], o["c1"] - o["c0"]) + 1
            hoja.paste(recorte(o["_nat"], o, o["_lab"], lado_px * 1.5, True), (160, y))
            hoja.paste(recorte(o["_nat"], o, o["_lab"], lado_px * 0.25, False), (160 + LADO, y))
            hoja.paste(recorte(o["_fal"], o, o["_lab"], lado_px * 0.25, False), (160 + 2 * LADO, y))
            idh = f"H{h // POR_HOJA + 1:02d}-{r + 1}"
            d_.text((8, y + 8), idh, fill=(0, 0, 0))
            d_.text((8, y + 28), f"{o['tipo']}  {o['area_ha']} ha", fill=(0, 0, 0))
            d_.text((8, y + 48), f"puntaje {o['puntaje_medio']}", fill=(0, 0, 0))
            d_.text((8, y + 68), f"MapBiomas {int(o['mb_pct'])}%", fill=(0, 0, 0))
            filas.append({"id_hoja": idh, "bloque": o["bloque"], "objeto": o["objeto"], "tipo": o["tipo"], "area_ha": o["area_ha"],
                          "puntaje_medio": o["puntaje_medio"], "mb_pct": o["mb_pct"]})
        hoja.save(OUT / f"hoja_{h // POR_HOJA + 1:02d}.png", optimize=True)
    pd.DataFrame(filas).to_csv(OUT / "indice.csv", index=False)
    print(f"{len(filas)} objetos en {len(filas) // POR_HOJA + (len(filas) % POR_HOJA > 0)} hojas -> {OUT}")


def aplicar():
    """Une las respuestas (id_hoja, etiqueta, motivo) con el indice y escribe revision_ia.csv (bloque, objeto, etiqueta, motivo)."""
    idx = pd.read_csv(OUT / "indice.csv")
    resp = pd.concat([pd.read_csv(f) for f in sorted(OUT.glob("respuestas_*.csv"))], ignore_index=True)   # una por revisor/subagente
    resp["etiqueta"] = resp["etiqueta"].str.strip().str.lower()
    t = idx.merge(resp, on="id_hoja", how="inner")
    t = t[t.etiqueta.isin(["mineria", "no_mineria", "dudoso"])]
    p10.REVISION_IA.parent.mkdir(parents=True, exist_ok=True)
    t[["bloque", "objeto", "tipo", "etiqueta", "motivo"]].to_csv(p10.REVISION_IA, index=False)
    print(t.groupby(["tipo", "etiqueta"]).size())


if __name__ == "__main__":
    {"generar": generar, "aplicar": aplicar}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
