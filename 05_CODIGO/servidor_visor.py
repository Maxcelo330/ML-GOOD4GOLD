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
import analisis_bloque as ab  # noqa: E402
import opinion_ia as oi  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
VISOR = RAIZ / "07_VISOR"
PUERTO = 8765
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
    return {"ok": True}


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

    def _json(self, codigo, datos):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/salud":
            return self._json(200, {"ok": True, "modelo": ab.MODELO.exists(), "etapas": ab.ETAPAS,
                                    "max_lado_km": ab.MAX_LADO_KM, "min_lado_km": ab.MIN_LADO_KM,
                                    "ia": oi.disponible(), "modelo_ia": oi.MODELO_IA})
        if url.path == "/api/estado":
            id_ = parse_qs(url.query).get("id", [""])[0]
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

    def _cuerpo(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(min(n, 10_000)))

    def do_POST(self):
        ruta = urlparse(self.path).path
        if ruta == "/api/opinion":      # segunda opinion de Claude sobre una zona (tarda ~10 s)
            try:
                c = self._cuerpo()
                return self._json(200, oi.pedir_opinion(c.get("clave"), c.get("id")))
            except oi.ErrorOpinion as e:
                return self._json(400, {"error": str(e)})
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                return self._json(500, {"error": "Fallo inesperado al pedir la opinion. Revisa la consola del servidor."})
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
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    url = f"http://127.0.0.1:{PUERTO}/"
    print(f"Visor listo en {url}  (cierra esta ventana para apagarlo)")
    if "--sin-navegador" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("Apagado.")
