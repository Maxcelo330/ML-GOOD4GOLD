"""
Respaldo cifrado de lo analizado, para llevarlo en el repo a otros equipos.

Que guarda (todo en UN archivo: 04_DATOS/respaldo_cifrado/respaldo.g4g):
  - los analisis de bloques (zonas y resumen; NO las imagenes, que son pesadas y se pueden volver a bajar)
  - las opiniones de Claude
  - tus revisiones del visor
  - los modelos que aprendieron (modelo_lgbm_aprendido_*.txt) y su historial

Por que cifrado: el repo es publico y las zonas son "por verificar" (decision D-002: los puntos detectados son datos
sensibles). En el repo solo queda texto ilegible; sin la contrasena no se puede leer. La clave es la del respaldo (clave_respaldo.txt, se
crea al azar la primera vez, o G4G_CLAVE_RESPALDO), distinta del usuario del visor: en el otro equipo hay que poner LA MISMA clave.

Como se usa:
  - En el visor: "Guardar en el repo" y "Traer del repo" (pantalla de inicio), o
  - python 05_CODIGO\\sincronizar.py exportar   |   importar
  Despues de exportar, el archivo se sube al repo con git (commit y push) como cualquier otro.
  Importar solo AGREGA lo que falta (nunca borra ni pisa lo que ya hay). Exportar primero importa, asi no se pierde lo del otro equipo.
  El servidor importa solo al arrancar si encuentra el archivo.

Cifrado (solo biblioteca estandar, sin instalar nada): clave = scrypt(contrasena, sal) -> dos claves; el contenido se cifra
con un flujo HMAC-SHA256 en modo contador y se autentica con HMAC-SHA256 (cifrar y luego autenticar). Si se cambia la
contrasena o el archivo se altera, no abre. Si prefieres una biblioteca estandar de cifrado (AES-GCM), se puede cambiar:
el archivo lleva una marca de version.
"""
import hashlib
import hmac
import io
import json
import os
import re
import struct
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceso  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO = RAIZ / "04_DATOS" / "respaldo_cifrado" / "respaldo.g4g"
ANALISIS = RAIZ / "04_DATOS" / "analisis_bloques"
OPINIONES = RAIZ / "04_DATOS" / "opiniones_ia"
REVISIONES = RAIZ / "04_DATOS" / "etiquetas" / "revisiones_visor.jsonl"
REVISIONES_ZONAS = RAIZ / "04_DATOS" / "etiquetas" / "revisiones_zonas.json"
RES = RAIZ / "04_DATOS" / "resultados"
MAGIA = b"G4GENC1\n"
NOMBRE_OK = re.compile(r"[A-Za-z0-9_\-]+\.(json|txt)")


class ErrorRespaldo(Exception):
    """Error que se le explica a la persona."""


# ---------------------------------------------------------------- cifrado
def _claves(clave, sal):
    k = hashlib.scrypt(clave.encode("utf-8"), salt=sal, n=2 ** 15, r=8, p=1, dklen=64, maxmem=96 * 1024 * 1024)
    return k[:32], k[32:]


def _flujo(k, nonce, n):
    out, i = bytearray(), 0
    while len(out) < n:
        out += hmac.new(k, nonce + struct.pack(">Q", i), hashlib.sha256).digest()
        i += 1
    return bytes(out[:n])


def _xor(a, b):
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(len(a), "big") if a else b""


def cifrar(datos, clave):
    sal, nonce = os.urandom(16), os.urandom(16)
    ke, km = _claves(clave, sal)
    c = _xor(datos, _flujo(ke, nonce, len(datos)))
    tag = hmac.new(km, MAGIA + sal + nonce + c, hashlib.sha256).digest()
    return MAGIA + sal + nonce + tag + c


def descifrar(blob, clave):
    if blob[:len(MAGIA)] != MAGIA or len(blob) < len(MAGIA) + 64:
        raise ErrorRespaldo("El archivo de respaldo no tiene el formato esperado.")
    o = len(MAGIA)
    sal, nonce, tag, c = blob[o:o + 16], blob[o + 16:o + 32], blob[o + 32:o + 64], blob[o + 64:]
    ke, km = _claves(clave, sal)
    if not hmac.compare_digest(tag, hmac.new(km, MAGIA + sal + nonce + c, hashlib.sha256).digest()):
        raise ErrorRespaldo("No se pudo abrir el respaldo: la contrasena es distinta de la que lo guardo (en este equipo pon la misma en "
                            "clave_respaldo.txt) o el archivo se altero.")
    return _xor(c, _flujo(ke, nonce, len(c)))


# ---------------------------------------------------------------- que se guarda
def _recolectar():
    """arcname -> bytes de todo lo que va al respaldo."""
    f = {}
    for p in sorted(ANALISIS.glob("*.json")):
        if re.fullmatch(r"[0-9a-f]{12}\.json", p.name):
            f[f"analisis/{p.name}"] = p.read_bytes()
    for p in sorted(OPINIONES.glob("*.json")):
        if re.fullmatch(r"[0-9a-f]{12}_[A-Za-z0-9\-]+\.json", p.name):
            f[f"opiniones/{p.name}"] = p.read_bytes()
    if REVISIONES.exists():
        f["etiquetas/revisiones_visor.jsonl"] = REVISIONES.read_bytes()
    if REVISIONES_ZONAS.exists():
        f["etiquetas/revisiones_zonas.json"] = REVISIONES_ZONAS.read_bytes()
    for p in sorted(RES.glob("modelo_lgbm_aprendido_*.txt")):
        f[f"modelos/{p.name}"] = p.read_bytes()
    for n in ("modelo_activo.json", "modelos_aprendizaje.json"):
        if (RES / n).exists():
            f[f"modelos/{n}"] = (RES / n).read_bytes()
    return f


def _lineas(b):
    return [x for x in b.decode("utf-8", "replace").splitlines() if x.strip()]


def importar():
    """Agrega lo que falta en este equipo desde el respaldo. Devuelve {'ok', 'nuevos': {...}} (no borra ni pisa nada)."""
    if not ARCHIVO.exists():
        return {"ok": False, "motivo": "Todavia no hay respaldo en el repo."}
    datos = descifrar(ARCHIVO.read_bytes(), acceso.clave_respaldo())
    z = zipfile.ZipFile(io.BytesIO(datos))
    nuevos = {"analisis": 0, "opiniones": 0, "revisiones": 0, "modelos": 0}
    for nombre in z.namelist():
        parte, _, base = nombre.partition("/")
        contenido = z.read(nombre)
        if parte == "analisis" and NOMBRE_OK.fullmatch(base):
            destino = ANALISIS / base
            clave_n = "analisis"
        elif parte == "opiniones" and NOMBRE_OK.fullmatch(base):
            destino, clave_n = OPINIONES / base, "opiniones"
        elif parte == "modelos" and NOMBRE_OK.fullmatch(base):
            destino, clave_n = RES / base, "modelos"
            if base == "modelos_aprendizaje.json":          # historial: se unen las versiones que falten
                try:
                    mio = json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else []
                    ajeno = json.loads(contenido.decode("utf-8"))
                    versiones = {x.get("version") for x in mio}
                    faltan = [x for x in ajeno if x.get("version") not in versiones]
                    if faltan:
                        destino.write_text(json.dumps(mio + faltan, indent=1, ensure_ascii=False), encoding="utf-8")
                        nuevos["modelos"] += 1
                except (OSError, ValueError):
                    pass
                continue
        elif nombre == "etiquetas/revisiones_zonas.json":      # revisiones de todas las zonas: gana la mas reciente de cada una
            try:
                import zonas_confirmadas as zc
                zc.REVISIONES_ZONAS = REVISIONES_ZONAS
                mias = json.loads(REVISIONES_ZONAS.read_text(encoding="utf-8")) if REVISIONES_ZONAS.exists() else {}
                antes = len(mias)
                zc.guardar_revisiones([r for r in json.loads(contenido.decode("utf-8")).values() if r.get("id") not in mias
                                       or zc._fecha(mias[r["id"]].get("fecha")) < zc._fecha(r.get("fecha"))] + list(mias.values()))
                despues = json.loads(REVISIONES_ZONAS.read_text(encoding="utf-8"))
                nuevos["revisiones"] += max(0, len(despues) - antes)
            except (OSError, ValueError):
                pass
            continue
        elif nombre == "etiquetas/revisiones_visor.jsonl":
            mias = _lineas(REVISIONES.read_bytes()) if REVISIONES.exists() else []
            faltan = [x for x in _lineas(contenido) if x not in set(mias)]
            if faltan:
                REVISIONES.parent.mkdir(parents=True, exist_ok=True)
                with open(REVISIONES, "a", encoding="utf-8") as fh:
                    fh.write("\n".join(faltan) + "\n")
                nuevos["revisiones"] += len(faltan)
            continue
        else:
            continue
        if not destino.exists():            # solo se agrega lo que falta
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(contenido)
            nuevos[clave_n] += 1
    return {"ok": True, "nuevos": nuevos}


def exportar():
    """Guarda todo en el archivo cifrado (antes trae lo que tenga el otro equipo, para no perderlo)."""
    if ARCHIVO.exists():
        importar()          # si la contrasena es otra, falla aqui y NO se pisa el respaldo existente
    archivos = _recolectar()
    if not archivos:
        return {"ok": False, "motivo": "Todavia no hay nada analizado para guardar."}
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for n, b in archivos.items():
            z.writestr(n, b)
        z.writestr("meta.json", json.dumps({"fecha": time.strftime("%Y-%m-%d %H:%M"), "archivos": len(archivos)}))
    blob = cifrar(memoria.getvalue(), acceso.clave_respaldo())
    ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
    tmp = ARCHIVO.with_suffix(".tmp")
    tmp.write_bytes(blob)
    tmp.replace(ARCHIVO)
    return {"ok": True, "archivos": len(archivos), "bytes": len(blob), "ruta": "04_DATOS/respaldo_cifrado/respaldo.g4g"}


def estado():
    """Barato (no abre el archivo): si existe, cuanto pesa y cuando se guardo."""
    if not ARCHIVO.exists():
        return {"existe": False}
    s = ARCHIVO.stat()
    return {"existe": True, "bytes": s.st_size, "fecha": time.strftime("%Y-%m-%d %H:%M", time.localtime(s.st_mtime))}


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else ""
    if accion not in ("exportar", "importar"):
        raise SystemExit(__doc__)
    try:
        print(json.dumps({"exportar": exportar, "importar": importar}[accion](), indent=1, ensure_ascii=False))
    except ErrorRespaldo as e:
        raise SystemExit(str(e))
