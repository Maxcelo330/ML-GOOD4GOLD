"""
Cual es el modelo que se esta usando ahora.

El modelo puede "aprender" de las revisiones de Claude y de las personas (aprendizaje.py): cada vez que aprende se guarda
un archivo NUEVO (modelo_lgbm_aprendido_001.txt, 002, ...) y el anterior no se borra. Este archivo dice cual es el activo:

    04_DATOS/resultados/modelo_activo.json   {"archivo": "modelo_lgbm_aprendido_001.txt", "version": "aprendido_001", ...}

Si no existe, el activo es el modelo v2 (modelo_lgbm_v2.txt). Para volver atras basta borrar modelo_activo.json.
Es un modulo liviano (no importa lightgbm) para que lo use el analisis de bloques sin dependencias circulares.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RES = RAIZ / "04_DATOS" / "resultados"
ARCHIVO = RES / "modelo_activo.json"
V2 = RES / "modelo_lgbm_v2.txt"
V1 = RES / "modelo_lgbm.txt"


def leer():
    """Contenido de modelo_activo.json (dict vacio si no existe o esta danado)."""
    try:
        return json.loads(ARCHIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ruta():
    """Ruta del archivo del modelo activo."""
    a = leer().get("archivo")
    if a and (RES / a).exists():
        return RES / a
    return V2 if V2.exists() else V1


def version():
    """Nombre corto de la version activa: 'v2' o 'aprendido_001'."""
    a = leer()
    if a.get("archivo") and (RES / a["archivo"]).exists():
        return a.get("version") or Path(a["archivo"]).stem
    return "v2" if V2.exists() else "v1"


def fijar(archivo, version, **extra):
    """Deja como activo un modelo ya guardado en 04_DATOS/resultados/."""
    if not (RES / archivo).exists():
        raise FileNotFoundError(archivo)
    ARCHIVO.write_text(json.dumps({"archivo": archivo, "version": version, **extra}, indent=1, ensure_ascii=False), encoding="utf-8")
