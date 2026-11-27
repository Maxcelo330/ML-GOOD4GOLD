"""
Servidor del visor del modelo para GRABAR capturas de la presentacion: usa los analisis REALES (solo lectura), pero guarda lo que se haga
(opiniones, revisiones, modelos) en una carpeta temporal y responde con una API de Claude SIMULADA para lo que no tenga opinion real.
La opinion real guardada (zona B5929-013) se copia a la carpeta temporal para que la IA "ya haya opinado" sobre esa zona.

Uso (entorno g4g-ml):  python -I -u 08_PRESENTACION\\herramientas\\servidor_visor_demo.py [puerto]     (por defecto 8767)
Abre http://127.0.0.1:<puerto>/ ; usuario y contrasena de la IA: Aurum80 / Aurum80 (NO mostrarlos en el video).
Detener: cerrar el proceso (solo el propio).
"""
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "05_CODIGO"))
puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8767
tmp = Path(tempfile.mkdtemp(prefix="g4gdemo_"))
print("carpeta temporal:", tmp, flush=True)
os.environ["G4G_URL_API"] = "http://127.0.0.1:%d/v1/messages" % (puerto + 1000)
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-demo"
os.environ["G4G_CLAVE_RESPALDO"] = "demo-respaldo"
os.environ["G4G_AUTO_APRENDER"] = "0"

import modelo_activo as ma  # noqa: E402
ma.RES = tmp / "res"; ma.RES.mkdir(); ma.ARCHIVO = ma.RES / "modelo_activo.json"
import opinion_ia as oi  # noqa: E402
oi.OPINIONES = tmp / "op"; oi.OPINIONES.mkdir(); oi.CONSUMO = oi.OPINIONES / "consumo.json"
real = RAIZ / "04_DATOS" / "opiniones_ia"
for f in real.glob("*_*.json"):                                  # las opiniones REALES de Claude ya guardadas
    shutil.copy(f, oi.OPINIONES)
import aprendizaje as ap  # noqa: E402
ap.RES = ma.RES; ap.OPINIONES = oi.OPINIONES; ap.REVISIONES = tmp / "rev.jsonl"; ap.INFO = ma.RES / "modelos_aprendizaje.json"
import servidor_visor as sv  # noqa: E402
sv.ETIQUETAS = tmp / "rev.jsonl"
import sincronizar as sy  # noqa: E402
sy.ARCHIVO = tmp / "respaldo.g4g"; sy.OPINIONES = oi.OPINIONES; sy.REVISIONES = tmp / "rev.jsonl"; sy.RES = ma.RES
import zonas_confirmadas as zc  # noqa: E402
zc.REVISIONES_ZONAS = tmp / "revisiones_zonas.json"; zc.REVISIONES_VISOR = tmp / "rev.jsonl"; zc.SALIDA_GEOJSON = tmp / "zc.geojson"; zc.SALIDA_CSV = tmp / "zc.csv"; zc.OPINIONES = oi.OPINIONES
sy.REVISIONES_ZONAS = zc.REVISIONES_ZONAS
import paquete_app as pa  # noqa: E402
pa.SALIDA = tmp / "para_la_app"                      # el paquete para la app tambien va a la carpeta temporal (no pisa el real)


class ApiSimulada(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        c = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        txt = c["messages"][0]["content"][-1]["text"]
        pt = int(re.search(r"puntaje del modelo (\d+)/100", txt).group(1))
        v = "probable_mineria" if pt >= 64 else "probable_no_mineria"
        time.sleep(0.4)
        cuerpo = {"stop_reason": "end_turn", "usage": {"input_tokens": 2324, "output_tokens": 428},
                  "content": [{"type": "text", "text": json.dumps({"veredicto": v, "confianza": "media", "que_parece": "Zona de prueba (respuesta simulada)",
                                                                   "motivos": ["motivo simulado"], "que_revisar": "imagen de alta resolucion"})}]}
        d = json.dumps(cuerpo).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(d))); self.end_headers(); self.wfile.write(d)


threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", puerto + 1000), ApiSimulada).serve_forever, daemon=True).start()
print("visor demo en http://127.0.0.1:%d/ (API de Claude simulada en %d)" % (puerto, puerto + 1000), flush=True)
ThreadingHTTPServer(("127.0.0.1", puerto), sv.Manejador).serve_forever()
