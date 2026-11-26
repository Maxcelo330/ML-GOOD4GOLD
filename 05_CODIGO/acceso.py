"""
Usuario y contrasena del visor, SOLO para las acciones con inteligencia artificial.

Que pide usuario y contrasena (y nada mas):
  - pedir la opinion de Claude sobre una zona o sobre varias (gasta dinero de la API)
  - hacer que el modelo aprenda de esas opiniones (botones del panel naranja "Claude (IA)")
Mirar el mapa, dibujar y analizar bloques, ver la lista, marcar tus revisiones, descargar las zonas y el respaldo NO piden nada.

Credenciales (en este orden):
  1. variables de entorno G4G_USUARIO y G4G_CLAVE_ACCESO
  2. archivo acceso_ia.txt en la carpeta del proyecto: linea 1 = usuario, linea 2 = contrasena (NO se sube a git)
  3. por defecto: usuario Aurum80, contrasena Aurum80
Proteccion contra adivinar: 5 intentos fallidos bloquean 5 minutos a esa direccion; la comparacion es en tiempo constante.
Importante: esto protege el gasto de la API; no cifra la conexion (si se expone fuera de la red local, usar https).

Clave del respaldo cifrado (sincronizar.py): es OTRA, aparte del usuario, porque el respaldo se sube a un repo publico y una
contrasena corta como la de acceso se podria adivinar. Se guarda en clave_respaldo.txt (se crea al azar la primera vez y se
muestra en la ventana del servidor; hay que copiarla al otro equipo) o en la variable G4G_CLAVE_RESPALDO.
"""
import hashlib
import hmac
import os
import secrets
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO = RAIZ / "acceso_ia.txt"
ARCHIVO_RESPALDO = RAIZ / "clave_respaldo.txt"
USUARIO_DEFECTO = "Aurum80"
CLAVE_DEFECTO = "Aurum80"
MAX_FALLOS = 5
BLOQUEO_S = 300
_fallos = {}            # direccion -> (n_fallos, bloqueado_hasta)
_candado = threading.Lock()
_cred = None
_clave_respaldo = None


def credenciales():
    """(usuario, contrasena) vigentes."""
    global _cred
    if _cred is None:
        u, c = os.environ.get("G4G_USUARIO", "").strip(), os.environ.get("G4G_CLAVE_ACCESO", "").strip()
        if not (u and c) and ARCHIVO.exists():
            lineas = [x.strip() for x in ARCHIVO.read_text(encoding="utf-8").splitlines() if x.strip()]
            if len(lineas) >= 2:
                u, c = u or lineas[0], c or lineas[1]
        _cred = (u or USUARIO_DEFECTO, c or CLAVE_DEFECTO)
    return _cred


def clave_respaldo():
    """Clave del respaldo cifrado (se crea al azar la primera vez si no hay)."""
    global _clave_respaldo
    if _clave_respaldo is None:
        c = os.environ.get("G4G_CLAVE_RESPALDO", "").strip()
        if not c and ARCHIVO_RESPALDO.exists():
            c = ARCHIVO_RESPALDO.read_text(encoding="utf-8").strip()
        if not c:
            c = secrets.token_urlsafe(12)
            ARCHIVO_RESPALDO.write_text(c + "\n", encoding="utf-8")
            print(f"\n  Clave del respaldo cifrado creada: {c}\n  (queda en {ARCHIVO_RESPALDO.name}; en el otro equipo hay que poner la misma)\n", flush=True)
        _clave_respaldo = c
    return _clave_respaldo


def direccion(handler):
    """Direccion de quien pide (si hay un tunel o proxy, la que informa en la cabecera)."""
    for cab in ("CF-Connecting-IP", "X-Forwarded-For"):
        v = handler.headers.get(cab)
        if v:
            return v.split(",")[0].strip()
    return handler.client_address[0]


def _igual(a, b):
    return hmac.compare_digest(hashlib.sha256(a.encode()).digest(), hashlib.sha256(b.encode()).digest())


def autorizar(handler):
    """Devuelve (True, None) o (False, (codigo_http, mensaje)). Cuenta los intentos fallidos."""
    quien, ahora = direccion(handler), time.time()
    with _candado:
        n, hasta = _fallos.get(quien, (0, 0))
        if hasta > ahora:
            return False, (429, f"Demasiados intentos. Espera {int(hasta - ahora) + 1} segundos.")
        u, c = handler.headers.get("X-Usuario", ""), handler.headers.get("X-Acceso", "")
        if not (u or c):        # todavia no los escribio: se le piden, no cuenta como intento fallido
            return False, (401, "Esta accion con inteligencia artificial pide usuario y contrasena.")
        usuario, clave = credenciales()
        # se evalua todo (sin cortar antes) para que el tiempo no delate cual de los dos fallo
        ok_u, ok_c = _igual(u, usuario), _igual(c, clave)
        if ok_u and ok_c:
            _fallos.pop(quien, None)
            return True, None
        n += 1
        _fallos[quien] = (0, ahora + BLOQUEO_S) if n >= MAX_FALLOS else (n, 0)
        return False, (401, "Usuario o contrasena incorrectos.")
