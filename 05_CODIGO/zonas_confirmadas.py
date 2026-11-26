"""
Zonas que la persona marco como "Parece actividad minera": se guardan en disco y salen en un archivo para la app.

De donde salen:
  1. 04_DATOS/etiquetas/revisiones_zonas.json   revisiones del visor de TODAS las zonas (piloto y bloques), que el visor envia
                                                 entero cuando se desbloquea con la contrasena (porque antes solo vivian en el navegador)
  2. 04_DATOS/etiquetas/revisiones_visor.jsonl  etiqueta de cada zona de bloque que se marco en el visor (con su geometria)
  De cada zona vale la revision mas reciente; si despues la cambias a "No parece" o "Sin revisar", sale de la lista.

Que genera (en local; NO se sube a git, son zonas "por verificar": decision D-002):
  04_DATOS/etiquetas/zonas_confirmadas.geojson          para la app (modulo "Detecciones revisadas")
  04_DATOS/resultados/zonas_confirmadas_plataforma.csv  la misma lista en el formato de la plataforma / para Excel o QGIS
Van tambien dentro del respaldo cifrado del repo (sincronizar.py), asi viajan a otros equipos.

Es posible actividad minera por verificar: no dice si es legal ni si hay mercurio. Revisada por una persona mirando imagen
de 20 m, no verificada en campo.
"""
import csv
import json
import re
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ANALISIS = RAIZ / "04_DATOS" / "analisis_bloques"
OPINIONES = RAIZ / "04_DATOS" / "opiniones_ia"
REVISIONES_ZONAS = RAIZ / "04_DATOS" / "etiquetas" / "revisiones_zonas.json"
REVISIONES_VISOR = RAIZ / "04_DATOS" / "etiquetas" / "revisiones_visor.jsonl"
SALIDA_GEOJSON = RAIZ / "04_DATOS" / "etiquetas" / "zonas_confirmadas.geojson"
SALIDA_CSV = RAIZ / "04_DATOS" / "resultados" / "zonas_confirmadas_plataforma.csv"
SI = "Parece actividad minera"
ESTADOS = {"mineria": SI, "no_mineria": "No parece actividad minera", "dudoso": "No estoy seguro"}
AVISO = ("Posible actividad minera revisada por una persona sobre imagen satelital de 20 m: por verificar en campo; registro AJAM aun "
         "no consultado. No indica legalidad ni presencia de mercurio.")
COLUMNAS = ["id", "nombre", "tipo", "origen", "lat", "lng", "area_ha", "puntaje_modelo", "prioridad", "zona_cercana", "estado_verificacion",
            "dist_rio_m", "dist_poblado_m", "poblado_cercano", "actualizado", "deteccion", "nota"]


def _fecha(f):
    """Fecha comparable 'YYYY-MM-DD HH:MM' (si solo viene el dia, se toma como las 00:00)."""
    f = str(f or "")
    return f if len(f) > 10 else f + " 00:00"


def guardar_revisiones(lista):
    """Une las revisiones que manda el visor con las ya guardadas (gana la mas reciente por zona). Devuelve cuantas hay."""
    try:
        mias = json.loads(REVISIONES_ZONAS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        mias = {}
    for r in lista:
        id_ = str(r.get("id", ""))
        if not re.fullmatch(r"[A-Za-z0-9\-]{3,20}", id_) or r.get("estado") not in (*ESTADOS.values(), "Sin revisar"):
            continue
        ant = mias.get(id_)
        if ant and _fecha(ant.get("fecha")) > _fecha(r.get("fecha")):
            continue
        mias[id_] = {"id": id_, "estado": r["estado"], "nota": str(r.get("nota", ""))[:500], "fecha": r.get("fecha") or time.strftime("%Y-%m-%d"),
                     "tipo": r.get("tipo"), "propiedades": r.get("propiedades") or {}, "geometria": r.get("geometria")}
    REVISIONES_ZONAS.parent.mkdir(parents=True, exist_ok=True)
    REVISIONES_ZONAS.write_text(json.dumps(mias, ensure_ascii=False), encoding="utf-8")
    return len(mias)


def _analisis_por_prefijo():
    """prefijo de clave (4 letras) -> (clave, analisis) para completar las zonas de bloque."""
    out = {}
    for p in ANALISIS.glob("*.json"):
        if re.fullmatch(r"[0-9a-f]{12}\.json", p.name):
            out[p.stem[:4]] = p
    return out


def _vigentes():
    """id -> registro vigente (la revision mas reciente de cada zona)."""
    todas = {}
    try:
        for id_, r in json.loads(REVISIONES_ZONAS.read_text(encoding="utf-8")).items():
            todas[id_] = r
    except (OSError, ValueError):
        pass
    if REVISIONES_VISOR.exists():
        for linea in REVISIONES_VISOR.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(linea)
            except ValueError:
                continue
            reg = {"id": r["id"], "estado": ESTADOS.get(r.get("etiqueta"), "Sin revisar"), "nota": "", "fecha": r.get("fecha"), "tipo": "an",
                   "propiedades": {"clave": r.get("clave"), "puntaje_modelo": r.get("puntaje_modelo")}, "geometria": r.get("geometria")}
            if r["id"] not in todas or _fecha(todas[r["id"]].get("fecha")) <= _fecha(reg["fecha"]):
                # la revision del visor no trae la nota: se conserva la que ya habia
                if r["id"] in todas:
                    reg["nota"] = todas[r["id"]].get("nota", "")
                todas[r["id"]] = reg
    return todas


def construir():
    """Arma la lista de zonas confirmadas y escribe el GeoJSON y el CSV. Devuelve {'n': ..., 'geojson': ruta}."""
    prefijos = _analisis_por_prefijo()
    feats, filas = [], []
    for id_, r in sorted(_vigentes().items()):
        if r.get("estado") != SI:
            continue
        p = dict(r.get("propiedades") or {})
        geom = r.get("geometria")
        if id_.startswith("B") and id_[1:5] in prefijos:      # zonas de bloque: se completan con el analisis guardado
            try:
                a = json.loads(prefijos[id_[1:5]].read_text(encoding="utf-8"))
                f = next(x for x in a["zonas"]["features"] if x["properties"]["id"] == id_)
                p = {**f["properties"], **{k: v for k, v in p.items() if v not in (None, "")}}
                geom = geom or f["geometry"]
            except (OSError, ValueError, StopIteration):
                pass
        if not geom:
            continue                                            # sin forma no se puede mostrar en el mapa
        clave = p.get("clave")
        claude = None
        if clave and (OPINIONES / f"{clave}_{id_}.json").exists():
            try:
                o = json.loads((OPINIONES / f"{clave}_{id_}.json").read_text(encoding="utf-8"))
                claude = {"veredicto": o.get("veredicto"), "confianza": o.get("confianza"), "que_parece": o.get("que_parece")}
            except (OSError, ValueError):
                pass
        origen = {"ML": "piloto (modelo)", "LV": "piloto (lectura visual)"}.get(id_[:2], "bloque analizado")
        props = {"id": id_, "origen": origen, "estado": SI, "fecha_revision": r.get("fecha"), "nota_revision": r.get("nota", ""),
                 "area_ha": p.get("area_ha"), "puntaje_modelo": p.get("puntaje_modelo"), "lat": p.get("lat"), "lng": p.get("lng"),
                 "dist_rio_m": p.get("dist_rio_m"), "dist_poblado_m": p.get("dist_poblado_m"),
                 "poblado_cercano": p.get("poblado_cercano") or p.get("zona_cercana") or "", "opinion_claude": claude,
                 "deteccion": "imagen satelital (ML) + revision visual de una persona", "estado_verificacion": "por verificar en campo; registro AJAM aun no consultado"}
        feats.append({"type": "Feature", "geometry": geom, "properties": props})
        filas.append({"id": id_, "nombre": f"Posible actividad minera revisada {id_}", "tipo": "zona revisada: parece actividad minera", "origen": origen,
                      "lat": props["lat"], "lng": props["lng"], "area_ha": props["area_ha"], "puntaje_modelo": props["puntaje_modelo"],
                      "prioridad": "revisada por una persona", "zona_cercana": props["poblado_cercano"], "estado_verificacion": props["estado_verificacion"],
                      "dist_rio_m": props["dist_rio_m"], "dist_poblado_m": props["dist_poblado_m"], "poblado_cercano": props["poblado_cercano"],
                      "actualizado": r.get("fecha"), "deteccion": "imagen satelital (ML)", "nota": (r.get("nota") or "") + (" " if r.get("nota") else "") + AVISO})
    coleccion = {"type": "FeatureCollection", "generado": time.strftime("%Y-%m-%d %H:%M"), "aviso": AVISO, "features": feats}
    SALIDA_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_GEOJSON.write_text(json.dumps(coleccion, ensure_ascii=False), encoding="utf-8")
    SALIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(SALIDA_CSV, "w", encoding="utf-8-sig", newline="") as fh:       # BOM: Excel lee las tildes
        w = csv.DictWriter(fh, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)
    return {"n": len(feats), "geojson": "04_DATOS/etiquetas/zonas_confirmadas.geojson", "csv": "04_DATOS/resultados/zonas_confirmadas_plataforma.csv"}


def leer():
    """El GeoJSON ya generado (o uno vacio)."""
    try:
        return json.loads(SALIDA_GEOJSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"type": "FeatureCollection", "generado": None, "aviso": AVISO, "features": []}


if __name__ == "__main__":
    print(json.dumps(construir(), indent=1, ensure_ascii=False))
