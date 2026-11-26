"""
Servidor local del visor: abre el visor en el navegador y analiza el bloque que la persona dibuje.

Que hace:
  - Sirve el visor (07_VISOR/visor.html) en http://127.0.0.1:8765 (solo esta computadora puede entrar).
  - Recibe el bloque dibujado (POST /api/analizar), lo analiza con analisis_bloque.py en segundo plano y
    deja consultar el avance real (GET /api/estado): etapa, porcentaje y mensaje.
  - Un solo analisis a la vez (descarga imagenes y usa el procesador).

Seguridad: escucha solo en 127.0.0.1, no guarda datos de la persona, solo sirve archivos de 07_VISOR y
valida el bloque (tamano maximo) antes de descargar nada.

Como correrlo: doble clic en EJECUTAR-VISOR.bat (o, en el entorno g4g-ml:
  python 05_CODIGO\\servidor_visor.py)
"""
import json
import os
import sys
import threading
import time
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))   # (con 'python -I' la carpeta del script no se agrega sola)
import acceso  # noqa: E402
import analisis_bloque as ab  # noqa: E402
import modelo_activo as ma  # noqa: E402
import opinion_ia as oi  # noqa: E402
import recorte_zona as rz  # noqa: E402
import sincronizar as sy  # noqa: E402
import zonas_confirmadas as zc  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
VISOR = RAIZ / "07_VISOR"
PUERTO = int(os.environ.get("G4G_PUERTO", "8765"))    # (otro puerto solo para pruebas)
TIPOS = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".png": "image/png", ".json": "application/json; charset=utf-8", ".md": "text/plain; charset=utf-8"}
# Peso de cada etapa en la barra de avance total (suman 1): la descarga es lo que mas tarda
PESOS = [0.04, 0.50, 0.12, 0.10, 0.14, 0.10]

trabajos = {}                   # id -> estado del analisis
candado = threading.Lock()


ETIQUETAS = RAIZ / "04_DATOS" / "etiquetas" / "revisiones_visor.jsonl"


def guardar_etiqueta(clave, id_zona, etiqueta):
    """Guarda la decision de una persona sobre una zona (mineria / no_mineria / dudoso) junto con su geometria.

    Es la etiqueta de mas valor: paso10_reentrenar.py la usa con prioridad sobre la de la IA y la de MapBiomas."""
    import re
    if etiqueta not in ("mineria", "no_mineria", "dudoso") or not re.fullmatch(r"[0-9a-f]{12}", clave or ""):
        raise ab.ErrorAnalisis("Etiqueta no valida.")
    ruta = ab.SALIDA / f"{clave}.json"
    if not ruta.exists():
        raise ab.ErrorAnalisis("No se encuentra ese analisis.")
    res = json.loads(ruta.read_text(encoding="utf-8"))
    f = next((x for x in res["zonas"]["features"] if x["properties"]["id"] == id_zona), None)
    if f is None:
        raise ab.ErrorAnalisis("No se encuentra esa zona.")
    op = oi.OPINIONES / f"{clave}_{id_zona}.json"
    fila = {"fecha": time.strftime("%Y-%m-%d %H:%M"), "clave": clave, "clave_img": res["resumen"].get("clave_img"), "id": id_zona, "etiqueta": etiqueta,
            "origen": "humano (visor)", "puntaje_modelo": f["properties"]["puntaje_modelo"], "geometria": f["geometry"],
            "opinion_ia": json.loads(op.read_text(encoding="utf-8")).get("veredicto") if op.exists() else None}
    ETIQUETAS.parent.mkdir(parents=True, exist_ok=True)
    with candado, open(ETIQUETAS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
    threading.Thread(target=auto_aprender, daemon=True).start()
    try:
        zc.construir()
    except Exception:  # noqa: BLE001  (el archivo para la app es un extra)
        traceback.print_exc()
    return {"ok": True}


def _aprendizaje():
    """El modulo de aprendizaje se carga cuando se necesita (trae lightgbm y pandas, que no hacen falta para ver el visor)."""
    import aprendizaje
    return aprendizaje


def auto_aprender():
    """Si ya hay suficientes revisiones nuevas (de Claude o de personas), el modelo aprende solo en segundo plano.
    Se apaga con la variable G4G_AUTO_APRENDER=0. Solo se queda con el modelo nuevo si no empeora (lo decide aprendizaje.py)."""
    if os.environ.get("G4G_AUTO_APRENDER", "1") == "0":
        return
    try:
        ap = _aprendizaje()
        if ap.estado().get("recomendado"):
            ap.aprender_en_segundo_plano()
    except Exception:  # noqa: BLE001  (aprender es un extra: si falla no debe afectar al visor)
        traceback.print_exc()


URL_WAYBACK ="https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json"
_wayback = []


def wayback():
    """Fechas de imagen historica de Esri Wayback (una por trimestre) con su plantilla de mosaicos. Se baja una vez y queda en memoria."""
    global _wayback
    if not _wayback:
        import re
        import requests
        try:
            cfg = requests.get(URL_WAYBACK, timeout=20).json()
        except Exception:  # noqa: BLE001
            raise ab.ErrorAnalisis("No se pudo consultar el catalogo de imagenes historicas (sin internet?).")
        por_trim = {}
        for k, v in cfg.items():
            m = re.search(r"(\d{4})-(\d{2})-(\d{2})", v.get("itemTitle", ""))
            if m and "{level}" in v.get("itemURL", ""):
                por_trim[(m.group(1), (int(m.group(2)) - 1) // 3)] = (f"{m.group(1)}-{m.group(2)}-{m.group(3)}",
                                                                      v["itemURL"].replace("{level}", "{z}").replace("{row}", "{y}").replace("{col}", "{x}"))
        _wayback = [{"fecha": f, "url": u} for f, u in sorted(por_trim.values())]
    return _wayback


lotes = {}                      # id -> estado de una revision en lote con Claude


def correr_lote(id_, clave, ids):
    """Pide la opinion de Claude para varias zonas (3 a la vez). Se frena si se llega al tope de gasto."""
    from concurrent.futures import ThreadPoolExecutor
    est = lotes[id_]

    def uno(z):
        if est["parar"]:
            return
        try:
            r = oi.pedir_opinion(clave, z)
            est["cache" if r.get("desde_cache") else "nuevas"] += 1
        except oi.ErrorOpinion as e:
            est["errores"].append(f"{z}: {e}")
            if "tope" in str(e).lower() or "clave" in str(e).lower():
                est["parar"] = True
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            est["errores"].append(f"{z}: fallo inesperado ({type(e).__name__})")
        est["hechas"] += 1
        est["consumo"] = oi.consumo()

    with ThreadPoolExecutor(3) as ex:
        list(ex.map(uno, ids))
    est["estado"] = "listo"
    est["consumo"] = oi.consumo()
    auto_aprender()


def leer_analisis(clave):
    """Resultado guardado de un analisis (o None)."""
    import re
    if not re.fullmatch(r"[0-9a-f]{12}", clave or ""):
        return None
    ruta = ab.SALIDA / f"{clave}.json"
    try:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if "zonas" not in r or "resumen" not in r:
        return None
    r["resumen"]["desde_cache"] = True
    return r


def historial():
    """Lista de bloques analizados antes (el mas reciente de cada bloque y sensibilidad), mas nuevos primero."""
    import re
    vistos, out = set(), []
    for f in sorted(ab.SALIDA.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        if not re.fullmatch(r"[0-9a-f]{12}", f.stem):
            continue
        r = leer_analisis(f.stem)
        if not r:
            continue
        res = r["resumen"]
        llave = (tuple(round(v, 3) for v in r["bbox"]), res.get("sensibilidad"))
        if llave in vistos:
            continue
        vistos.add(llave)
        out.append({"clave": f.stem, "bbox": r["bbox"], "fecha": time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime)),
                    "n_zonas": res.get("n_zonas"), "area_total_ha": res.get("area_total_ha"), "bloque_km": res.get("bloque_km"),
                    "sensibilidad": res.get("sensibilidad"), "modelo": res.get("modelo") or "v2"})
    return out


# Lo que pide usuario y contrasena: SOLO las acciones con inteligencia artificial (opinion de Claude y aprendizaje del modelo)
PROTEGIDAS = {"/api/opinion", "/api/lote", "/api/aprender"}


def correr(id_):
    estado = trabajos[id_]

    def progreso(etapa, frac, msg):
        total = sum(PESOS[:etapa]) + PESOS[etapa] * max(0.0, min(1.0, frac))
        estado.update(etapa=etapa, etapa_frac=round(frac, 3), progreso=round(total, 3), mensaje=msg)

    try:
        estado["resultado"] = ab.analizar(estado["bbox"], progreso, sensibilidad=estado["sens"])
        estado.update(estado="listo", progreso=1.0, etapa=len(ab.ETAPAS))
    except ab.ErrorAnalisis as e:
        estado.update(estado="error", error=str(e))
    except Exception as e:  # noqa: BLE001  (error inesperado: se informa sin detalles internos)
        traceback.print_exc()
        estado.update(estado="error", error=f"Fallo inesperado: {type(e).__name__}. Revisa la consola del servidor.")


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):   # consola limpia
        pass

    def _cors(self):
        """Permite que una pagina web de otro sitio (por ejemplo la app en GitHub Pages) hable con este servidor.
        Solo los sitios listados en G4G_ORIGENES (separados por coma); por defecto ninguno."""
        origen = self.headers.get("Origin")
        if origen and origen in [o.strip() for o in os.environ.get("G4G_ORIGENES", "").split(",") if o.strip()]:
            self.send_header("Access-Control-Allow-Origin", origen)
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Acceso")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Vary", "Origin")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _json(self, codigo, datos):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/salud":
            return self._json(200, {"ok": True, "modelo": ab.MODELO.exists(), "etapas": ab.ETAPAS,
                                    "max_lado_km": ab.MAX_LADO_KM, "min_lado_km": ab.MIN_LADO_KM,
                                    "ia": oi.disponible(), "modelo_ia": oi.MODELO_IA, "consumo": oi.consumo(), "modelo_version": ma.version(),
                                    "acceso": True})
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        if url.path == "/api/confirmadas":    # zonas marcadas "Parece actividad minera" (GeoJSON para la app)
            zc.construir()
            return self._json(200, zc.leer())
        if url.path == "/api/respaldo":       # estado del respaldo cifrado del repo (no lo abre)
            return self._json(200, sy.estado())
        if url.path == "/api/historial":      # bloques ya analizados (para volver a abrirlos despues de cerrar el visor)
            return self._json(200, historial())
        if url.path == "/api/analisis":
            r = leer_analisis(q.get("clave"))
            return self._json(200, r) if r else self._json(404, {"error": "No existe ese analisis."})
        if url.path == "/api/opiniones":      # opiniones de Claude ya guardadas de un analisis (no gasta)
            return self._json(200, oi.opiniones_de(q.get("clave")))
        if url.path == "/api/opinion":        # leer una opinion ya guardada: no gasta, no pide contrasena
            o = oi.opinion_guardada(q.get("clave"), q.get("id"))
            return self._json(200, o) if o else self._json(404, {"error": "Esa zona aun no tiene opinion de Claude."})
        if url.path == "/api/lote":
            e = lotes.get(q.get("id", ""))
            return self._json(200, e) if e else self._json(404, {"error": "No existe esa revision."})
        if url.path == "/api/recorte_info":
            try:
                i = rz.info(q.get("clave"), q.get("id"), q.get("asp", 2.0))
                return self._json(200, {**i, "bounds": [[float(a) for a in p] for p in i["bounds"]]})
            except rz.ErrorRecorte as e:
                return self._json(400, {"error": str(e)})
        if url.path == "/api/recorte.png":
            try:
                datos = rz.recorte_png(q.get("clave"), q.get("id"), q.get("capa"), q.get("asp", 2.0)).read_bytes()
            except rz.ErrorRecorte as e:
                return self._json(400, {"error": str(e)})
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                return self._json(500, {"error": "No se pudo armar la imagen."})
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(datos)))
            self.send_header("Cache-Control", "max-age=3600")
            self._cors()
            self.end_headers()
            self.wfile.write(datos)
            return
        if url.path == "/api/wayback":
            try:
                return self._json(200, wayback())
            except ab.ErrorAnalisis as e:
                return self._json(502, {"error": str(e)})
        if url.path == "/api/precision":      # comparacion modelo vs Claude (y personas)
            try:
                return self._json(200, _aprendizaje().precision_vs_ia())
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                return self._json(500, {"error": "No se pudo calcular la comparacion."})
        if url.path == "/api/aprendizaje":
            try:
                return self._json(200, _aprendizaje().estado())
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                return self._json(500, {"error": "No se pudo leer el estado del aprendizaje."})
        if url.path == "/api/estado":
            id_ = q.get("id", "")
            e = trabajos.get(id_)
            if not e:
                return self._json(404, {"error": "No existe ese analisis."})
            salida = {k: v for k, v in e.items() if k not in ("bbox", "resultado", "sens")}
            salida["transcurrido_s"] = round(time.time() - e["inicio"], 1)
            if e["estado"] == "listo":
                salida["resultado"] = e["resultado"]
            return self._json(200, salida)
        # Archivos del visor (solo dentro de 07_VISOR)
        ruta = "visor.html" if url.path in ("/", "") else url.path.lstrip("/")
        destino = (VISOR / ruta).resolve()
        if VISOR.resolve() not in destino.parents or not destino.is_file() or destino.suffix not in TIPOS:
            self.send_error(404)
            return
        datos = destino.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TIPOS[destino.suffix])
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def _cuerpo(self, limite=10_000):
        n = int(self.headers.get("Content-Length", 0))
        if n > limite:
            raise ValueError("cuerpo demasiado grande")
        return json.loads(self.rfile.read(n))

    def do_POST(self):
        ruta = urlparse(self.path).path
        if ruta == "/api/acceso" or ruta in PROTEGIDAS:
            ok, error = acceso.autorizar(self)
            if not ok:
                return self._json(error[0], {"error": error[1], "acceso": False})
            if ruta == "/api/acceso":
                return self._json(200, {"ok": True})
        if ruta == "/api/opinion":      # segunda opinion de Claude sobre una zona (tarda ~10 s)
            try:
                c = self._cuerpo()
                r = oi.pedir_opinion(c.get("clave"), c.get("id"))
                if not r.get("desde_cache"):
                    threading.Thread(target=auto_aprender, daemon=True).start()
                return self._json(200, r)
            except oi.ErrorOpinion as e:
                return self._json(400, {"error": str(e)})
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                return self._json(500, {"error": "Fallo inesperado al pedir la opinion. Revisa la consola del servidor."})
        if ruta == "/api/revisiones":   # el visor manda TODAS sus revisiones (piloto y bloques): quedan en disco y se actualizan las zonas confirmadas
            try:
                c = self._cuerpo(1_500_000)
                lista = c.get("revisiones")
                if not isinstance(lista, list) or len(lista) > 2000:
                    return self._json(400, {"error": "Lista de revisiones no valida."})
                n = zc.guardar_revisiones(lista)
                return self._json(200, {"ok": True, "revisiones": n, **zc.construir()})
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                return self._json(400, {"error": "Pedido no valido."})
        if ruta in ("/api/respaldo/exportar", "/api/respaldo/importar"):     # respaldo cifrado en el repo (ver sincronizar.py)
            try:
                r = sy.exportar() if ruta.endswith("exportar") else sy.importar()
                return self._json(200 if r.get("ok") else 400, r if r.get("ok") else {"error": r.get("motivo", "No se pudo.")})
            except sy.ErrorRespaldo as e:
                return self._json(400, {"error": str(e)})
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                return self._json(500, {"error": "Fallo inesperado con el respaldo. Revisa la consola del servidor."})
        if ruta == "/api/lote":         # revisar varias zonas con Claude (en segundo plano; se consulta con GET /api/lote?id=)
            try:
                c = self._cuerpo()
                clave, ids = c.get("clave"), c.get("ids")
                if not oi.disponible():
                    return self._json(400, {"error": "Falta la clave de la API de Claude (ver 07_VISOR/LEEME.md)."})
                if not isinstance(ids, list) or not 0 < len(ids) <= ab.MAX_ZONAS or not all(isinstance(z, str) for z in ids):
                    return self._json(400, {"error": "Lista de zonas no valida."})
                with candado:
                    if any(l["estado"] == "corriendo" for l in lotes.values()):
                        return self._json(429, {"error": "Ya hay una revision con Claude en curso."})
                    id_ = uuid.uuid4().hex[:10]
                    lotes[id_] = {"estado": "corriendo", "total": len(ids), "hechas": 0, "nuevas": 0, "cache": 0, "errores": [], "parar": False, "consumo": oi.consumo()}
                threading.Thread(target=correr_lote, args=(id_, clave, ids), daemon=True).start()
                return self._json(202, {"id": id_})
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                return self._json(400, {"error": "Pedido no valido."})
        if ruta == "/api/aprender":     # el modelo aprende de las revisiones de Claude y de las personas (en segundo plano)
            try:
                _aprendizaje().aprender_en_segundo_plano()
                return self._json(202, {"ok": True})
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                return self._json(500, {"error": "No se pudo iniciar el aprendizaje."})
        if ruta == "/api/etiqueta":     # la revision de la persona sobre una zona: queda guardada para reentrenar el modelo
            try:
                c = self._cuerpo()
                return self._json(200, guardar_etiqueta(c.get("clave"), c.get("id"), c.get("etiqueta")))
            except ab.ErrorAnalisis as e:
                return self._json(400, {"error": str(e)})
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                return self._json(500, {"error": "No se pudo guardar la etiqueta."})
        if ruta != "/api/analizar":
            return self._json(404, {"error": "Ruta desconocida."})
        try:
            n = int(self.headers.get("Content-Length", 0))
            cuerpo = json.loads(self.rfile.read(min(n, 10_000)))
            bbox = ab.validar_bbox(cuerpo["bbox"])
            sens = cuerpo.get("sensibilidad", "normal")
            if sens not in ab.UMBRALES:
                raise ab.ErrorAnalisis("Sensibilidad no valida.")
        except ab.ErrorAnalisis as e:
            return self._json(400, {"error": str(e)})
        except Exception:  # noqa: BLE001
            return self._json(400, {"error": "Pedido no valido."})
        with candado:
            if any(t["estado"] == "corriendo" for t in trabajos.values()):
                return self._json(429, {"error": "Ya hay un analisis en curso. Espera a que termine."})
            id_ = uuid.uuid4().hex[:10]
            trabajos[id_] = {"estado": "corriendo", "bbox": list(bbox), "sens": sens, "etapa": 0, "etapa_frac": 0.0, "progreso": 0.0,
                             "mensaje": "Iniciando", "inicio": time.time()}
        threading.Thread(target=correr, args=(id_,), daemon=True).start()
        self._json(202, {"id": id_})


if __name__ == "__main__":
    if not (VISOR / "visor.html").exists():
        raise SystemExit("Falta 07_VISOR/visor.html. Corre primero paso8_visor_html.py.")
    class Servidor(ThreadingHTTPServer):
        allow_reuse_address = False      # en Windows, si no, dos visores abiertos a la vez comparten el puerto y el viejo sigue respondiendo
    try:
        servidor = Servidor(("127.0.0.1", PUERTO), Manejador)
    except OSError:
        raise SystemExit(f"El visor ya esta abierto en el puerto {PUERTO}. Cierra su ventana (la negra) y vuelve a abrir EJECUTAR-VISOR.bat para que tome los cambios.")
    url = f"http://127.0.0.1:{PUERTO}/"
    acceso.clave_respaldo()      # crea la clave del respaldo cifrado la primera vez (y la muestra aqui)
    try:                # si hay un respaldo cifrado en el repo, se agrega lo que falte en este equipo
        r = sy.importar()
        if r.get("ok") and any(r["nuevos"].values()):
            print("  Respaldo del repo importado:", ", ".join(f"{v} {k}" for k, v in r["nuevos"].items() if v), flush=True)
    except sy.ErrorRespaldo as e:
        print("  Aviso del respaldo:", e, flush=True)
    except Exception as e:  # noqa: BLE001
        print("  No se pudo leer el respaldo:", type(e).__name__, flush=True)
    print(f"Visor listo en {url}  (cierra esta ventana para apagarlo)")
    if "--sin-navegador" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("Apagado.")
