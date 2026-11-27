"""
Paquete para la app: UN solo archivo (ZIP) con todo lo que la plataforma web necesita de este modelo.

Para que sirve: que quien revisa las zonas en el visor no tenga que saber de formatos. Pulsa un boton, baja un ZIP,
lo abre y lo sube a la app siguiendo el LEEME que viene adentro.

Que lleva (todo sale de las zonas que una persona marco "Parece actividad minera"; ver zonas_confirmadas.py):
  zonas_revisadas.geojson   poligonos para la seccion "Detecciones revisadas" de la app (la via recomendada)
  zonas_para_registro.xlsx  hoja "Zonas por verificar" con las MISMAS columnas de la plantilla de la app (para quien
                            ingresa datos al registro) y hoja "LEEME"
  zonas_revisadas.csv       lo mismo en CSV (Excel en espanol: separador coma, tildes con BOM)
  paquete.json              datos del paquete para sistemas: contrato, fecha, cantidad, version del modelo
  LEEME.txt                 los pasos, en lenguaje simple

Contrato de datos "g4g-zonas-v1" (lo que la app espera; ver CONTRATO-DATOS.md):
  - GeoJSON FeatureCollection de Polygon/MultiPolygon en WGS84, cada Feature con properties.id unico.
  - Columnas del Excel/CSV con los nombres de la plantilla de la app (id, nombre, tipo, lat, lng, dist_rio_m,
    dist_poblado_m, actualizado, deteccion), seguidas de columnas extra que la app ignora sin problema.

IMPORTANTE:
  - Son zonas de POSIBLE actividad minera POR VERIFICAR en campo. No dicen si es legal ni si hay mercurio; el registro
    de la AJAM aun no se consulto. El puntaje es relativo, no una probabilidad.
  - NO cargar el Excel con "Datos > Cargar Excel o CSV" de la app: esa carga REEMPLAZA toda la base (operadores y
    pasivos). El Excel es para copiar filas al registro con "Registrar datos" o a la hoja de Google.
  - Son datos sensibles (decision D-002): la carpeta 04_DATOS/para_la_app/ no va a git.

Como correrlo (entorno g4g-ml):  python 05_CODIGO\\paquete_app.py
"""
import csv
import io
import json
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # (con 'python -I' la carpeta del script no se agrega sola)
import zonas_confirmadas as zc  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "04_DATOS" / "para_la_app"
CONTRATO = "g4g-zonas-v1"
EQUIPO = "aurum80"

# Orden de la plantilla de pasivos de la app (js/core/importer.js, cabeceras('pasivos')) y despues las columnas extra
COLS_APP = ["id", "operador_id", "nombre", "tipo", "lat", "lng", "volumen_m3", "dist_rio_m", "dist_poblado_m", "estructura",
            "uso_hg", "muestra", "ley_au_gt", "actualizado", "deteccion"]
COLS_EXTRA = ["area_ha", "puntaje_modelo", "poblado_cercano", "origen", "fecha_revision", "nota_revision", "opinion_claude",
              "estado_verificacion"]
COLUMNAS = COLS_APP + COLS_EXTRA

LEEME = """PAQUETE DE ZONAS PARA LA APP  (equipo {equipo})
Generado: {fecha}    Zonas: {n}    Contrato de datos: {contrato}

QUE ES
Son las zonas que una persona revisó en el visor y marcó "Parece actividad minera". Es POSIBLE actividad minera, POR VERIFICAR
en campo. No dice si es legal ni si hay mercurio, y el registro de la AJAM aún no se consultó. El puntaje del modelo es relativo,
no es una probabilidad. Son datos sensibles: no los publiques.

ARCHIVOS
  zonas_revisadas.geojson   El mapa de las zonas. Es lo que sube a la app (la vía recomendada).
  zonas_para_registro.xlsx  Para quien ingresa datos: la hoja "Zonas por verificar" usa las columnas de la plantilla de la app.
  zonas_revisadas.csv       Lo mismo que el Excel, en CSV.
  paquete.json              Datos del paquete para sistemas (fecha, cantidad, versión del modelo).

COMO SUBIRLO A LA APP (3 pasos)
  1. Abre la app y pulsa "Ingresar" (arriba a la derecha) con tu cuenta de funcionario.
  2. Menú Municipio > "Detecciones revisadas" > "Cargar archivo de zonas (GeoJSON)" y elige zonas_revisadas.geojson.
  3. La app dice cuántas zonas entraron y cuántas ignoró (y por qué). Las zonas se guardan solo en ese dispositivo.

SI LLEVAS EL REGISTRO (Excel o la hoja de Google)
  Abre zonas_para_registro.xlsx, hoja "Zonas por verificar". Las primeras 15 columnas son las mismas de la hoja "Pasivos" de la app,
  así que puedes copiar las filas que decidas registrar. Las columnas que siguen (area_ha, puntaje_modelo, ...) son de apoyo.
  ATENCION: no uses "Datos > Cargar Excel o CSV" con este archivo. Esa carga reemplaza toda la base (operadores y pasivos).

RECUERDA
  Una zona del modelo no es un pasivo ni una denuncia confirmada: es un lugar para ir a mirar. Verifica en campo antes de decidir.
"""


def _centro(geom):
    """(lat, lng) de un punto dentro de la zona (para zonas que no traen lat/lng guardados)."""
    from shapely.geometry import shape
    p = shape(geom).representative_point()
    return round(p.y, 6), round(p.x, 6)


def _opinion(o):
    if not isinstance(o, dict) or not o.get("veredicto"):
        return ""
    texto = f"Claude: {o['veredicto']}" + (f" ({o['confianza']})" if o.get("confianza") else "")
    if o.get("que_parece"):
        texto += f" - {o['que_parece']}"
    return texto + " (opinion de una IA sobre imagen de 20 m; no es verificacion en campo)"


def _filas(coleccion):
    filas = []
    for f in coleccion.get("features", []):
        p = f.get("properties") or {}
        lat, lng = p.get("lat"), p.get("lng")
        if lat in (None, "") or lng in (None, ""):
            try:
                lat, lng = _centro(f["geometry"])
            except Exception:  # noqa: BLE001  (sin centro valido no se puede ubicar la fila)
                lat, lng = "", ""
        filas.append({
            "id": p.get("id"), "operador_id": "",
            "nombre": f"Posible actividad minera (por verificar) {p.get('id')}",
            "tipo": "zona revisada: parece actividad minera",
            "lat": lat, "lng": lng, "volumen_m3": "",
            "dist_rio_m": p.get("dist_rio_m") if p.get("dist_rio_m") is not None else "",
            "dist_poblado_m": p.get("dist_poblado_m") if p.get("dist_poblado_m") is not None else "",
            "estructura": "", "uso_hg": "", "muestra": "", "ley_au_gt": "",
            "actualizado": p.get("fecha_revision") or "",
            "deteccion": "imagen satelital (ML) + revision visual de una persona",
            "area_ha": p.get("area_ha") if p.get("area_ha") is not None else "",
            "puntaje_modelo": p.get("puntaje_modelo") if p.get("puntaje_modelo") is not None else "",
            "poblado_cercano": p.get("poblado_cercano") or "", "origen": p.get("origen") or "",
            "fecha_revision": p.get("fecha_revision") or "", "nota_revision": p.get("nota_revision") or "",
            "opinion_claude": _opinion(p.get("opinion_claude")),
            "estado_verificacion": p.get("estado_verificacion") or "por verificar en campo; registro AJAM aun no consultado",
        })
    return filas


def _csv(filas):
    b = io.StringIO(newline="")
    w = csv.DictWriter(b, fieldnames=COLUMNAS)
    w.writeheader()
    w.writerows(filas)
    return ("﻿" + b.getvalue()).encode("utf-8")      # BOM: Excel lee las tildes


def _xlsx(filas, leeme):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Zonas por verificar"
    ws.append(COLUMNAS)
    for f in filas:
        ws.append([f[c] for c in COLUMNAS])
    oro = PatternFill("solid", fgColor="F3E7C6")
    gris = PatternFill("solid", fgColor="EBE5D9")
    for i, c in enumerate(ws[1], start=1):
        c.font = Font(bold=True, color="1D1B18")
        c.fill = oro if COLUMNAS[i - 1] in COLS_APP else gris     # dorado = columnas de la plantilla de la app; gris = apoyo
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "D2"
    ancho = {"id": 10, "nombre": 44, "tipo": 34, "deteccion": 40, "nota_revision": 40, "opinion_claude": 60, "estado_verificacion": 46,
             "origen": 22, "poblado_cercano": 22, "actualizado": 16, "fecha_revision": 16}
    for i, c in enumerate(COLUMNAS, start=1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = ancho.get(c, 14)
    ws2 = wb.create_sheet("LEEME")
    ws2.column_dimensions["A"].width = 130
    for linea in leeme.splitlines():
        ws2.append([linea])
    ws2["A1"].font = Font(bold=True, size=13)
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


def _version_modelo():
    try:
        import modelo_activo
        return str(modelo_activo.version())
    except Exception:  # noqa: BLE001
        return None


def construir():
    """Arma el paquete. Escribe la carpeta 04_DATOS/para_la_app/ y devuelve {'n', 'zip' (bytes), 'carpeta', 'archivos'}."""
    zc.construir()                       # al dia con las ultimas revisiones
    coleccion = zc.leer()
    filas = _filas(coleccion)
    fecha = time.strftime("%Y-%m-%d %H:%M")
    n = len(filas)
    leeme = LEEME.format(equipo=EQUIPO, fecha=fecha, n=n, contrato=CONTRATO)
    coleccion = {**coleccion, "contrato": CONTRATO, "generado": fecha, "equipo": EQUIPO}
    manifiesto = {"contrato": CONTRATO, "equipo": EQUIPO, "generado": fecha, "n_zonas": n, "modelo": _version_modelo(),
                  "aviso": zc.AVISO, "archivos": ["zonas_revisadas.geojson", "zonas_para_registro.xlsx", "zonas_revisadas.csv", "paquete.json", "LEEME.txt"]}
    archivos = {
        "LEEME.txt": leeme.encode("utf-8"),
        "zonas_revisadas.geojson": json.dumps(coleccion, ensure_ascii=False).encode("utf-8"),
        "zonas_para_registro.xlsx": _xlsx(filas, leeme),
        "zonas_revisadas.csv": _csv(filas),
        "paquete.json": json.dumps(manifiesto, ensure_ascii=False, indent=1).encode("utf-8"),
    }
    SALIDA.mkdir(parents=True, exist_ok=True)
    for nombre, datos in archivos.items():
        (SALIDA / nombre).write_bytes(datos)
    z = io.BytesIO()
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre, datos in archivos.items():
            zf.writestr(nombre, datos)
    (SALIDA / "zonas_para_la_app.zip").write_bytes(z.getvalue())
    return {"n": n, "zip": z.getvalue(), "carpeta": "04_DATOS/para_la_app", "archivos": list(archivos)}


if __name__ == "__main__":
    r = construir()
    print(f"Paquete listo: {r['n']} zonas en {SALIDA}")
    for a in r["archivos"] + ["zonas_para_la_app.zip"]:
        print("  ", a)
    if r["n"] == 0:
        print("AVISO: aun no hay zonas marcadas 'Parece actividad minera'. Revisa zonas en el visor y vuelve a correr esto.")
