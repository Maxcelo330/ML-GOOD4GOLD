"""
Paso 3b - Generar CANDIDATOS a actividad minera para que el humano los revise en QGIS.

Importante: esto NO es el modelo de ML ni confirma nada. Es una regla simple de color
sobre la imagen en color natural (Sentinel-2, epoca seca 2026) para proponer zonas de
suelo expuesto. Cada candidato queda con decision = "pendiente" y el humano decide si
lo acepta, lo corrige o lo descarta.

Regla de color (solo con rojo, verde y azul; los indices NDVI/BSI vendran en T-003):
  - suelo expuesto: el rojo es mayor o parecido al verde y claramente mayor que el azul
    (la vegetacion tiene el verde por encima del rojo).
  - se excluyen nubes (blancas) y sombras (muy oscuras).
  - se eliminan lineas finas (caminos) con una "apertura" morfologica.

Como correrlo (entorno g4g-ml):
  python 05_CODIGO\\paso3b_candidatos.py
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from PIL import Image, ImageDraw
from rasterio.features import shapes
from scipy import ndimage as ndi
from shapely.geometry import shape
from shapely.ops import unary_union

RAIZ = Path(__file__).resolve().parents[1]
PREVIA = RAIZ / "04_DATOS" / "imagenes" / "previa"
ETIQ = RAIZ / "04_DATOS" / "etiquetas"
ETIQ.mkdir(parents=True, exist_ok=True)

SECTORES = ["tipuani", "mapiri", "teoponte", "guanay"]
MIN_HA = 5            # candidatos menores a 5 hectareas se descartan (caminos, ruido)
MAX_POR_SECTOR = 25   # maximo de candidatos por sector (los mas grandes)
HA_POR_PIXEL = 0.01   # un pixel de 10 m = 100 m2 = 0.01 ha


def mascara_suelo(rgb):
    """True donde la imagen parece suelo expuesto (no vegetacion, nube ni sombra)."""
    r, g, b = (rgb[i].astype("int16") for i in range(3))
    brillo = (r + g + b) // 3
    nube = (r > 165) & (g > 165) & (b > 150)                     # blanco = nube
    nube = ndi.binary_dilation(nube, iterations=6)               # borde de la nube tambien
    sombra = brillo < 45
    suelo = (r >= g - 3) & (r - b >= 12) & (r > 70) & ~nube & ~sombra
    # Quitar lineas finas (caminos): abrir con un cuadrado de 3x3 pixeles (30 m)
    suelo = ndi.binary_opening(suelo, structure=np.ones((3, 3)))
    # Cerrar huecos pequenos dentro de una misma zona
    suelo = ndi.binary_closing(suelo, structure=np.ones((5, 5)))
    return suelo


def poligonos(mask, transf, nombre):
    """Convierte las regiones conectadas de la mascara en poligonos (en metros UTM)."""
    etiquetas, n = ndi.label(mask)
    areas = ndi.sum(mask, etiquetas, index=range(1, n + 1))
    orden = np.argsort(areas)[::-1]
    filas = []
    for k in orden:
        ha = areas[k] * HA_POR_PIXEL
        if ha < MIN_HA or len(filas) >= MAX_POR_SECTOR:
            break
        region = etiquetas == (k + 1)
        # Rellenar huecos pequenos y trazar el borde exacto de la region con rasterio
        relleno = ndi.binary_fill_holes(region).astype("uint8")
        piezas = [shape(g) for g, v in shapes(relleno, mask=relleno.astype(bool), transform=transf)]
        # Simplificar a ~15 m para no cargar el archivo de vertices innecesarios
        poli = unary_union(piezas).simplify(15)
        filas.append((ha, poli))
    return filas


def confianza_y_motivo(ha, sector):
    """Texto simple que explica por que se propone la zona. Es una hipotesis, no un hecho."""
    if ha >= 50:
        conf = "alta"
        motivo = (f"Zona extensa ({ha:.0f} ha) de suelo/sedimento expuesto sin vegetacion, "
                  "tipica de un cauce removido por mineria aluvial. Revisar si hay pozas y rio turbio al lado.")
    elif ha >= 15:
        conf = "media"
        motivo = (f"Parche de suelo expuesto de {ha:.0f} ha. Puede ser corte o poza minera, "
                  "pero tambien pasto, cultivo o derrumbe: confirmar con la imagen.")
    else:
        conf = "baja"
        motivo = (f"Parche pequeno ({ha:.0f} ha) de suelo expuesto. Con frecuencia son "
                  "chacos, pasto, derrumbes o pueblo: probable falso positivo.")
    return conf, motivo


todas = []
ident = 1
for sector in SECTORES:
    ruta = PREVIA / f"detalle_{sector}_10m.tif"
    with rasterio.open(ruta) as src:
        rgb = src.read([1, 2, 3])
        transf = src.transform
    suelo = mascara_suelo(rgb)
    cands = poligonos(suelo, transf, sector)
    print(f"{sector}: {suelo.mean() * 100:.1f}% de pixeles tipo suelo expuesto -> {len(cands)} candidatos")

    # Imagen de control: candidatos dibujados sobre la imagen (para revisarlos a ojo)
    img = Image.fromarray(rgb.transpose(1, 2, 0))
    dib = ImageDraw.Draw(img)
    for ha, poli in cands:
        conf, motivo = confianza_y_motivo(ha, sector)
        todas.append({"id": ident, "sector": sector.capitalize(), "area_ha": round(ha, 1),
                      "confianza": conf, "motivo": motivo, "decision": "pendiente",
                      "comentario": "", "origen": "claude (regla de color)", "geometry": poli})
        ident += 1
        if not poli.is_empty:
            polys = [poli] if poli.geom_type == "Polygon" else list(poli.geoms)
            for p in polys:
                px = [((x - transf.c) / transf.a, (y - transf.f) / transf.e) for x, y in p.exterior.coords]
                dib.line(px, fill=(255, 255, 0), width=3)
    img.thumbnail((1400, 1400))
    img.save(PREVIA / f"control_{sector}.png")

gdf = gpd.GeoDataFrame(todas, crs="EPSG:32719")
gdf = gdf[~gdf.geometry.is_empty]
salida = ETIQ / "candidatos.gpkg"
# PROTECCION: este archivo guarda las decisiones del revisor (aceptar/corregir/descartar).
# Si existe, no se sobrescribe, para no perder el trabajo humano.
import sys
if salida.exists() and "--forzar" not in sys.argv:
    sys.exit(f"{salida.name} ya existe y puede tener decisiones del revisor. "
             "No se sobrescribe. Si de verdad quieres rehacerlo, corre con --forzar.")
gdf.to_file(salida, layer="candidatos", driver="GPKG")
print(f"\nGuardado: {salida}  ({len(gdf)} candidatos)")
print(gdf.groupby(["sector", "confianza"]).size().unstack(fill_value=0))
