"""
Paso 2b - Crear el proyecto de QGIS con la zona piloto y un mapa satelital de fondo.

Para que sirve: en vez de agregar capas a mano en QGIS, este script arma un
"proyecto" (archivo .qgz) que ya trae todo cargado. Despues solo haces doble clic.

Que contiene el proyecto:
  1. La capa aoi_utm19s (el rectangulo de la zona piloto), solo con borde rojo.
  2. Un mapa de fondo con imagen satelital (Esri World Imagery, se baja de internet).

Se corre con el Python que trae QGIS (no con el entorno g4g-ml):
  & "C:\\Program Files\\QGIS 3.44.15\\bin\\python-qgis-ltr.bat" 05_CODIGO\\paso2b_proyecto_qgis.py
"""
import os
from pathlib import Path

# QGIS sin ventana: este script trabaja "por detras", no abre el programa.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsFillSymbol,
    QgsRendererCategory,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsRasterLayer,
    QgsReferencedRectangle,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtGui import QColor

# Rutas: la raiz del repo es la carpeta que contiene a 05_CODIGO.
RAIZ = Path(__file__).resolve().parents[1]
GPKG = RAIZ / "04_DATOS" / "zona_piloto.gpkg"
SALIDA = RAIZ / "06_QGIS-PROYECTO" / "zona_piloto.qgz"
SALIDA.parent.mkdir(parents=True, exist_ok=True)

# Iniciar el motor de QGIS (sin interfaz grafica)
qgs = QgsApplication([], False)
qgs.initQgis()

proyecto = QgsProject.instance()
proyecto.clear()
# CRS del proyecto: UTM 19S (metros), el mismo que usaremos para medir.
proyecto.setCrs(QgsCoordinateReferenceSystem("EPSG:32719"))
# Guardar las rutas relativas, para que el proyecto funcione aunque muevas la carpeta.
proyecto.setFilePathStorage(Qgis.FilePathType.Relative)

# Color de lo SELECCIONADO: por defecto QGIS lo pinta de amarillo solido y tapa la imagen.
# Lo cambiamos a cian semitransparente para ver el terreno a traves del poligono.
try:
    proyecto.setSelectionColor(QColor(0, 255, 255, 70))
except AttributeError:  # versiones sin este metodo: se guarda como propiedad del proyecto
    for clave, valor in (("Red", 0), ("Green", 255), ("Blue", 255), ("Alpha", 70)):
        proyecto.writeEntry("Gui", f"/SelectionColor{clave}Part", valor)

# Capa 1: el rectangulo de la zona piloto
aoi = QgsVectorLayer(f"{GPKG}|layername=aoi_utm19s", "Zona piloto (AOI)", "ogr")
if not aoi.isValid():
    raise SystemExit(f"No se pudo leer la capa en {GPKG}")
# Estilo: relleno transparente y borde rojo, para ver la imagen por debajo
aoi.renderer().setSymbol(
    QgsFillSymbol.createSimple(
        {"color": "0,0,0,0", "outline_color": "255,0,0,255", "outline_width": "0.8"}
    )
)

# Capa 2: imagen satelital de fondo (mosaicos XYZ de Esri)
url = (
    "type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D&zmax=19&zmin=0"
)
fondo = QgsRasterLayer(url, "Imagen satelital (Esri World Imagery)", "wms")
if not fondo.isValid():
    raise SystemExit("No se pudo crear la capa de fondo satelital")

# Capa 3 (opcional): los 4 pueblos con su nombre, solo como guia visual.
# Se crea antes con paso2c_poblados.py.
poblados = None
GPKG_POB = RAIZ / "04_DATOS" / "referencia_poblados.gpkg"
if GPKG_POB.exists():
    poblados = QgsVectorLayer(f"{GPKG_POB}|layername=poblados", "Poblados (referencia)", "ogr")
    if poblados.isValid():
        # Punto amarillo con borde negro
        poblados.renderer().setSymbol(
            QgsMarkerSymbol.createSimple(
                {"name": "circle", "color": "255,255,0,255", "outline_color": "0,0,0,255", "size": "7", "outline_width": "0.6"}
            )
        )
        # Etiqueta con el nombre, texto blanco con halo negro para leerse sobre la imagen
        formato = QgsTextFormat()
        formato.setSize(18)
        formato.setColor(QColor("white"))
        halo = QgsTextBufferSettings()
        halo.setEnabled(True)
        halo.setSize(2)
        halo.setColor(QColor("black"))
        formato.setBuffer(halo)
        etiqueta = QgsPalLayerSettings()
        etiqueta.fieldName = "nombre"
        etiqueta.setFormat(formato)
        etiqueta.placement = Qgis.LabelPlacement.AroundPoint  # junto al punto, sin taparlo
        etiqueta.dist = 2
        poblados.setLabeling(QgsVectorLayerSimpleLabeling(etiqueta))
        poblados.setLabelsEnabled(True)
    else:
        poblados = None

# Capa 4 (opcional): candidatos a revisar (se crean con paso3b_candidatos.py).
# El color del contorno cambia segun la decision del revisor, para ver el avance de un vistazo.
candidatos = None
GPKG_CAND = RAIZ / "04_DATOS" / "etiquetas" / "candidatos.gpkg"
if GPKG_CAND.exists():
    candidatos = QgsVectorLayer(f"{GPKG_CAND}|layername=candidatos", "Candidatos a revisar", "ogr")
    if candidatos.isValid():
        def estilo(relleno, borde, ancho="0.8"):
            return QgsFillSymbol.createSimple(
                {"color": relleno, "outline_color": borde, "outline_width": ancho})
        categorias = [
            QgsRendererCategory("pendiente", estilo("255,255,0,40", "255,215,0,255"), "Pendiente (amarillo)"),
            QgsRendererCategory("aceptar", estilo("0,200,0,90", "0,160,0,255", "1.0"), "ACEPTAR - es mineria (verde)"),
            QgsRendererCategory("corregir", estilo("255,140,0,90", "255,100,0,255", "1.0"), "CORREGIR (naranja)"),
            QgsRendererCategory("descartar", estilo("120,120,120,25", "200,0,0,255", "0.6"), "DESCARTAR - no es mineria (rojo)"),
        ]
        candidatos.setRenderer(QgsCategorizedSymbolRenderer("decision", categorias))

        # Formulario facil: la columna "decision" es una lista desplegable con 4 opciones.
        idx = candidatos.fields().indexOf("decision")
        candidatos.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("ValueMap", {"map": [
            {"Pendiente": "pendiente"},
            {"ACEPTAR (es mineria)": "aceptar"},
            {"CORREGIR (explica en comentario)": "corregir"},
            {"DESCARTAR (no es mineria)": "descartar"},
        ]}))
        # Para poligonos NUEVOS que dibuje el humano: ya vienen como aceptados y de origen "humano".
        candidatos.setDefaultValueDefinition(idx, QgsDefaultValue("'aceptar'"))
        candidatos.setDefaultValueDefinition(
            candidatos.fields().indexOf("origen"), QgsDefaultValue("'humano'"))

        # Etiqueta con el numero del candidato (para poder hablar de "el candidato 37")
        f2 = QgsTextFormat()
        f2.setSize(13)
        f2.setColor(QColor("white"))
        h2 = QgsTextBufferSettings()
        h2.setEnabled(True)
        h2.setSize(1.5)
        h2.setColor(QColor("black"))
        f2.setBuffer(h2)
        e2 = QgsPalLayerSettings()
        e2.fieldName = "id"
        e2.setFormat(f2)
        e2.placement = Qgis.LabelPlacement.OverPoint
        candidatos.setLabeling(QgsVectorLayerSimpleLabeling(e2))
        candidatos.setLabelsEnabled(True)
    else:
        candidatos = None

# Imagenes Sentinel-2 de la vista previa (apagadas por defecto; se prenden con la casilla)
previas = []
for nombre, archivo in [("Sentinel-2 zona completa (40 m)", "previa_zona_40m.tif"),
                        ("Sentinel-2 detalle Tipuani (10 m)", "detalle_tipuani_10m.tif"),
                        ("Sentinel-2 detalle Mapiri (10 m)", "detalle_mapiri_10m.tif"),
                        ("Sentinel-2 detalle Teoponte (10 m)", "detalle_teoponte_10m.tif"),
                        ("Sentinel-2 detalle Guanay (10 m)", "detalle_guanay_10m.tif")]:
    ruta = RAIZ / "04_DATOS" / "imagenes" / "previa" / archivo
    if ruta.exists():
        r = QgsRasterLayer(str(ruta), nombre)
        if r.isValid():
            previas.append(r)

# El orden importa: la primera capa de la lista queda ARRIBA en el mapa.
proyecto.addMapLayer(fondo, False)
proyecto.addMapLayer(aoi, False)
raiz_arbol = proyecto.layerTreeRoot()
if candidatos is not None:
    proyecto.addMapLayer(candidatos, False)
    raiz_arbol.addLayer(candidatos)
if poblados is not None:
    proyecto.addMapLayer(poblados, False)
    raiz_arbol.addLayer(poblados)
raiz_arbol.addLayer(aoi)
for r in previas:
    proyecto.addMapLayer(r, False)
    nodo = raiz_arbol.addLayer(r)
    nodo.setItemVisibilityChecked(False)   # apagada: se prende con la casilla
raiz_arbol.addLayer(fondo)

# Vista inicial: que el mapa abra enfocado en la zona piloto
proyecto.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(aoi.extent(), aoi.crs()))

ok = proyecto.write(str(SALIDA))
print(f"Proyecto guardado: {SALIDA}" if ok else "ERROR: no se pudo guardar el proyecto")
print(f"Capas: {[c.name() for c in proyecto.mapLayers().values()]}")
qgs.exitQgis()
