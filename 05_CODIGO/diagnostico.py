"""
Diagnostico del equipo: revisa en palabras simples que este todo para abrir el visor.

Lo usa EJECUTAR-VISOR.bat antes de abrir el visor. Tambien se puede correr solo (entorno g4g-ml):
  python -I 05_CODIGO\\diagnostico.py            muestra cada revision
  python -I 05_CODIGO\\diagnostico.py --silencioso   solo escribe si algo falla
Codigo de salida: 0 = todo bien, 1 = falta algo (la lista dice que).
No lee claves ni usa internet.
"""
import importlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PAQUETES = [("numpy", "numpy"), ("pandas", "pandas"), ("geopandas", "geopandas"), ("shapely", "shapely"), ("pyproj", "pyproj"),
            ("rasterio", "rasterio"), ("scipy", "scipy"), ("sklearn", "scikit-learn"), ("lightgbm", "lightgbm"), ("requests", "requests"),
            ("PIL", "pillow"), ("pystac_client", "pystac-client"), ("planetary_computer", "planetary-computer"), ("openpyxl", "openpyxl")]
ARCHIVOS = [("04_DATOS/resultados/modelo_lgbm.txt", "el modelo guardado (viene en el repo: haz git pull)"),
            ("07_VISOR/lib/leaflet/leaflet.js", "la libreria del mapa (viene en el repo: haz git pull)"),
            ("04_DATOS/referencia/rios_y_poblados.gpkg", "la capa de rios y poblados (viene en el repo: haz git pull)")]


def main():
    callado = "--silencioso" in sys.argv
    fallas = []

    def decir(texto):
        if not callado:
            print(texto)

    decir(f"Python {sys.version.split()[0]} en {sys.executable}")
    if sys.version_info < (3, 10):
        fallas.append("La version de Python es vieja (hace falta 3.10 o mas; el entorno g4g-ml trae 3.11).")
    for modulo, nombre in PAQUETES:
        try:
            m = importlib.import_module(modulo)
            decir(f"  OK      {nombre} {getattr(m, '__version__', '')}".rstrip())
        except Exception as e:  # noqa: BLE001  (un paquete roto tambien cuenta como faltante)
            fallas.append(f"Falta o no abre el paquete: {nombre} ({type(e).__name__})")
    for ruta, que in ARCHIVOS:
        if (RAIZ / ruta).exists():
            decir(f"  OK      {ruta}")
        else:
            fallas.append(f"Falta {ruta}: {que}")
    if fallas:
        print("\nLo que falta:")
        for f in fallas:
            print("  -", f)
        return 1
    decir("\nTodo en orden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
