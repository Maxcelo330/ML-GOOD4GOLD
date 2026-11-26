"""
Banco de bloques de entrenamiento: imagenes Sentinel-2 de MUCHOS lugares (no solo el norte de La Paz) con una
segunda fuente independiente de "donde hay mineria": el mapa MapBiomas (clase 30 = Mineria).

Para que sirve: el primer modelo se entreno con solo 9 zonas mineras, todas en laderas del norte de La Paz,
y por eso falla en terreno plano (Madre de Dios). Aqui se baja la misma imagen (misma receta que el analisis
de bloques) en lugares con mucha mineria y en lugares SIN mineria (rios con bancos de arena, pastizales,
agricultura, ciudad, laderas andinas) para ensenarle al modelo lo que es y lo que no es.

Fuente de las etiquetas: MapBiomas Peru y MapBiomas Bolivia, anios 2023 y 2024 (espejo en Source Cooperative,
licencia CC BY-SA 4.0). Es una clasificacion automatica de Landsat a 30 m: NO es verdad de campo. Un pixel
se toma como "mineria" solo si es mineria en AMBOS anios. Lo que MapBiomas deja sin marcar (minas chicas
o nuevas) se revisa aparte con ojos (humano o Claude) antes de usarlo; ver paso10_*.

Cada bloque se guarda en 04_DATOS/banco_bloques/<nombre>.npz (no va a git: es pesado y se regenera).

Como correrlo (entorno g4g-ml; tarda ~1,5 min por bloque, se puede cortar y retomar):
  python 05_CODIGO\\banco_bloques.py            (todos los bloques que falten)
  python 05_CODIGO\\banco_bloques.py lapampa    (solo uno)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pyproj
import rasterio
from rasterio.windows import Window
from scipy.ndimage import map_coordinates

sys.path.insert(0, str(Path(__file__).resolve().parent))   # (con 'python -I' la carpeta del script no se agrega sola)
import analisis_bloque as ab  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
BANCO = RAIZ / "04_DATOS" / "banco_bloques"
URL_MB = "https://data.source.coop/tristangruppwri/mapbiomas/mapbiomas-{pais}/mapbiomas_{pais}_{anio}/mapbiomas_{pais}_{anio}.tif"
ANIOS = (2023, 2024)
CLASE_MINERIA = 30

CS = 0.0992   # lado de las celdas del escaneo de MapBiomas (grados, ~11 km)


def celda(lon_oeste, lat_norte):
    """Bloque cuadrado de ~11 km con esquina noroeste en (lon_oeste, lat_norte)."""
    return (round(lon_oeste, 4), round(lat_norte - CS, 4), round(lon_oeste + CS, 4), round(lat_norte, 4))


# nombre: (bbox, pais_mapbiomas, tipo, nota). Las celdas de mineria son las de mayor proporcion de clase 30 en el escaneo de MapBiomas;
# las de control, celdas SIN mineria con mucho suelo sin vegetacion, rios, pasto, agricultura o ciudad.
BLOQUES = {
    # --- con mineria
    "mdd_prueba": (celda(-70.097, -12.876), "peru", "mineria", "La Pampa, Madre de Dios (bloque de PRUEBA: nunca entrena el modelo que se examina en el)"),
    "mdd_a": (celda(-70.593, -12.776), "peru", "mineria", "Madre de Dios"),
    "mdd_b": (celda(-70.593, -12.975), "peru", "mineria", "Madre de Dios"),
    "mdd_c": (celda(-70.494, -12.975), "peru", "mineria", "Madre de Dios"),
    "mdd_d": (celda(-69.899, -12.677), "peru", "mineria", "Madre de Dios"),
    "mdd_e": (celda(-69.502, -12.578), "peru", "mineria", "Madre de Dios"),
    "mdd_f": (celda(-70.494, -12.578), "peru", "mineria", "Madre de Dios"),
    "puno_sandia": (celda(-69.502, -14.661), "peru", "mineria", "Puno, selva alta"),
    "bol_guanay": (celda(-68.376, -15.231), "bolivia", "mineria", "norte de La Paz (zona piloto)"),
    "bol_mapiri": (celda(-67.681, -15.33), "bolivia", "mineria", "norte de La Paz (zona piloto)"),
    "bol_tipuani": (celda(-68.078, -15.529), "bolivia", "mineria", "norte de La Paz (zona piloto)"),
    # --- sin mineria: terrenos que el modelo suele confundir
    "n_mdd_arena": (celda(-70.99, -13.57), "peru", "control", "Madre de Dios, suelo sin vegetacion sin mineria"),
    "n_mdd_rio1": (celda(-71.089, -13.768), "peru", "control", "Madre de Dios, rio grande con bancos de arena"),
    "n_mdd_rio2": (celda(-69.006, -12.479), "peru", "control", "Madre de Dios, rio con bancos de arena"),
    "n_mdd_rio3": (celda(-69.601, -12.876), "peru", "control", "Madre de Dios, rio con bancos de arena"),
    "n_ucayali": (celda(-74.758, -8.909), "peru", "control", "selva con pasto y cultivos"),
    "n_puno_agro": (celda(-70.097, -15.553), "peru", "control", "altiplano, agricultura"),
    "n_beni_rio": (celda(-67.086, -13.942), "bolivia", "control", "rio Beni"),
    "n_beni_pasto": (celda(-66.789, -14.24), "bolivia", "control", "pastizal, Beni"),
    "n_lapaz_urbano": (celda(-68.276, -16.521), "bolivia", "control", "La Paz y El Alto, ciudad"),
    "n_madidi": (celda(-68.475, -14.636), "bolivia", "control", "rios y laderas, Madidi"),
    "pataz": (celda(-78.527, -6.925), "peru", "mineria", "norte del Peru, Andes (oro)"),
    "n_pucallpa_urbano": (celda(-74.659, -8.314), "peru", "control", "Pucallpa, ciudad amazonica"),
    "n_junin_urbano": (celda(-75.254, -11.983), "peru", "control", "Valle del Mantaro, ciudad andina"),
    "n_peru_nv1": (celda(-75.353, -6.429), "peru", "control", "selva alta, suelo sin vegetacion"),
    "n_peru_nv2": (celda(-74.362, -8.611), "peru", "control", "selva, suelo sin vegetacion"),
    "n_peru_rio1": (celda(-74.262, -8.909), "peru", "control", "rio Ucayali"),
    "n_peru_rio2": (celda(-75.651, -5.041), "peru", "control", "rio Maranon"),
    "n_sc_urbano": (celda(-63.219, -17.711), "bolivia", "control", "Santa Cruz, ciudad"),
    "n_cbba_urbano": (celda(-66.194, -17.413), "bolivia", "control", "Cochabamba, ciudad"),
    "n_bol_nv1": (celda(-65.896, -17.512), "bolivia", "control", "valles, suelo sin vegetacion"),
}


def mapbiomas_en_grilla(g, pais, anio):
    """Clases de MapBiomas (30 m, lon/lat) llevadas a la grilla de 20 m del bloque (vecino mas cercano)."""
    url = URL_MB.format(pais=pais, anio=anio)
    tr = pyproj.Transformer.from_crs(g.epsg, 4326, always_xy=True)
    xs = g.X0 + RES_PX * (np.arange(g.ancho) + 0.5)
    ys = g.Y1 - RES_PX * (np.arange(g.alto) + 0.5)
    gx, gy = np.meshgrid(xs, ys)
    lon, lat = tr.transform(gx, gy)
    with rasterio.open(url) as s:
        t = s.transform
        c0 = max(0, int(np.floor((lon.min() - t.c) / t.a)) - 2)
        c1 = min(s.width, int(np.ceil((lon.max() - t.c) / t.a)) + 2)
        f0 = max(0, int(np.floor((t.f - lat.max()) / -t.e)) - 2)
        f1 = min(s.height, int(np.ceil((t.f - lat.min()) / -t.e)) + 2)
        if c1 <= c0 or f1 <= f0:
            raise RuntimeError(f"El bloque cae fuera del mapa MapBiomas {pais}.")
        a = s.read(1, window=Window(c0, f0, c1 - c0, f1 - f0))
        col = (lon - t.c) / t.a - 0.5 - c0
        fil = (lat - t.f) / t.e - 0.5 - f0
    return map_coordinates(a, [fil, col], order=0, mode="nearest").astype("uint8")


RES_PX = ab.RES


def construir(nombre):
    bbox, pais, tipo, nota = BLOQUES[nombre]
    destino = BANCO / f"{nombre}.npz"
    t0 = time.time()
    print(f"[{nombre}] {nota}", flush=True)
    g, bandas, ndvi, ndwi, bsi, n_obs, usadas, pend, items, bbox_pad = ab.preparar_bloque(
        bbox, lambda e, f, m: print(f"   [{ab.ETAPAS[e]}] {f * 100:3.0f}% {m}", flush=True) if f >= 1.0 else None)
    mb = {anio: mapbiomas_en_grilla(g, pais, anio) for anio in ANIOS}
    ndvi_ok = ndvi[ndvi != -9999]
    print(f"   listo en {time.time() - t0:.0f} s | mineria MapBiomas: "
          + ", ".join(f"{a}={100 * np.mean(m == CLASE_MINERIA):.1f}%" for a, m in mb.items()) + f" | NDVI mediano {np.median(ndvi_ok):.2f}", flush=True)
    BANCO.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destino, bandas=bandas, ndvi=ndvi, ndwi=ndwi, bsi=bsi, pend=pend, n_obs=n_obs.astype("uint8"),
                        mb2023=mb[2023], mb2024=mb[2024], T=np.array(g.T)[:6], epsg=np.array([g.epsg]), bbox=np.array(bbox),
                        meta=np.array(json.dumps({"nombre": nombre, "pais": pais, "tipo": tipo, "nota": nota, "escenas": usadas}, ensure_ascii=False)))


if __name__ == "__main__":
    pedidos = sys.argv[1:] or list(BLOQUES)
    for n in pedidos:
        if n not in BLOQUES:
            raise SystemExit(f"No existe el bloque {n}. Disponibles: {', '.join(BLOQUES)}")
        if (BANCO / f"{n}.npz").exists():
            print(f"[{n}] ya esta", flush=True)
            continue
        try:
            construir(n)
        except Exception as e:  # noqa: BLE001  (un bloque con problema no frena a los demas)
            print(f"[{n}] FALLO: {type(e).__name__}: {e}", flush=True)
