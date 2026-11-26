"""
Nucleo compartido: de un mapa de puntaje a una lista de ZONAS de posible actividad minera.

Lo usan dos programas, para que ambos apliquen exactamente las mismas reglas:
  - paso6_exportar_plataforma.py : la lista de zonas de toda la zona piloto.
  - analisis_bloque.py           : el analisis de un bloque dibujado en el visor (cualquier lugar).

Reglas (ver 01_PLAN/Nota-de-metodo-y-limites.md):
  - Para PUNTUAR un pixel: al menos MIN_OBS fotos validas y azul (B02) menor a B02_MAX (si no, es nube).
  - Un pixel cuenta si su puntaje es >= UMBRAL, no es agua (NDWI > 0), no esta dentro de una zona de
    entrenamiento, no esta a menos de 600 m de un hueco sin datos y no esta pegado (100 m) a una zona
    minera de entrenamiento.
  - Se agrupan los pixeles vecinos; una zona debe tener al menos MIN_HA hectareas, mediana de 7 o mas
    fotos validas, NDVI mediano menor a 0.45 y estar rodeada de vegetacion (NDVI del entorno >= 0.5).
El puntaje NO es una probabilidad: sirve para ordenar zonas a revisar.
"""
import geopandas as gpd
import numpy as np
from rasterio.features import shapes
from scipy import ndimage as ndi
from shapely.geometry import shape

VARIABLES = ["B02", "B03", "B04", "B08", "B11", "B12", "ndvi", "ndwi", "bsi", "pendiente"]
# Variables de CONTEXTO (modelo v2): miran el entorno del pixel (un pixel de suelo desnudo junto a agua y con textura lisa suele
# ser un banco de arena; en una ciudad el NDVI cambia mucho de un pixel a otro; en una mina hay mucho suelo removido alrededor).
VARIABLES_CONTEXTO = ["ndvi_textura_100m", "ndvi_media_300m", "frac_agua_300m", "frac_pelado_300m"]
NODATA = -9999.0
MIN_OBS = 3                  # un pixel con menos de 3 fotos validas no se puntua (quedan nubes sueltas)
B02_MAX = 0.25               # azul muy alto = nube que se colo
UMBRAL = 0.5
MIN_HA = 5
MARGEN_SIN_DATOS_PX = 30     # 30 px de 20 m = 600 m alrededor de huecos sin datos
MIN_OBS_MEDIANA = 7
NDVI_MEDIANA_MAX = 0.45
BORDE_ENTRENAMIENTO_PX = 5   # 100 m
ENTORNO_NDVI_MIN = 0.5
# Parametros del analisis de bloques FUERA del piloto (reglas relajadas): se marcan, no se eliminan, y se tolera mas ruido
RELAJADO = dict(estricto=False, unir_px=3, margen_px=5, rellenar_huecos=True)
ANILLO_PX = 15               # el "entorno" son unos 300 m alrededor de la zona


def mediana_pila(pila):
    """Mediana por pixel ignorando NaN. Devuelve (mediana, n_observaciones_validas)."""
    pila = np.sort(pila, axis=0)
    n = np.sum(~np.isnan(pila), axis=0).astype("int16")
    nmax = pila.shape[0]
    bajo = np.clip((n - 1) // 2, 0, nmax - 1)[None]
    alto = np.clip(n // 2, 0, nmax - 1)[None]
    v1 = np.take_along_axis(pila, bajo, axis=0)[0]
    v2 = np.take_along_axis(pila, alto, axis=0)[0]
    med = (v1 + v2) / 2
    med[n == 0] = np.nan
    return med.astype("float32"), n


def _media_local(x, ok, k):
    """Media de x en una ventana de k x k pixeles usando solo los pixeles validos (ok)."""
    num = ndi.uniform_filter(np.where(ok, x, 0.0).astype("float32"), k, mode="nearest")
    den = ndi.uniform_filter(ok.astype("float32"), k, mode="nearest")
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(den > 0.05, num / den, np.nan).astype("float32")


def contexto(ndvi, ndwi):
    """4 capas de contexto (orden de VARIABLES_CONTEXTO). Entradas con NODATA donde no hay dato."""
    ok = np.isfinite(ndvi) & (ndvi != NODATA)
    m5, m5c = _media_local(ndvi, ok, 5), _media_local(ndvi ** 2, ok, 5)
    textura = np.sqrt(np.clip(m5c - m5 ** 2, 0, None))
    ok_w = ok & np.isfinite(ndwi) & (ndwi != NODATA)
    return np.stack([textura, _media_local(ndvi, ok, 15), _media_local((ndwi > 0).astype("float32"), ok_w, 15),
                     _media_local((ndvi < 0.3).astype("float32"), ok, 15)]).astype("float32")


def variables_y_validez(bandas, ndvi, ndwi, bsi, pendiente, nobs, con_contexto=False):
    """Arma la pila de variables (orden de VARIABLES, y VARIABLES_CONTEXTO si con_contexto) y la mascara de pixeles que se pueden puntuar.

    bandas: (6, alto, ancho) en el orden B02, B03, B04, B08, B11, B12.
    """
    datos = np.concatenate([bandas, ndvi[None], ndwi[None], bsi[None], pendiente[None]]).astype("float32")
    valido = np.isfinite(datos).all(axis=0) & (datos != NODATA).all(axis=0) & (nobs >= MIN_OBS)
    with np.errstate(invalid="ignore"):
        valido &= datos[0] < B02_MAX
    datos[:, ~valido] = np.nan
    if con_contexto:
        datos = np.concatenate([datos, contexto(ndvi, ndwi)])
        datos[len(VARIABLES):, ~valido] = np.nan
    return datos, valido


def puntuar(modelo, datos, valido):
    """Puntaje (0 a 1) de cada pixel valido con un lightgbm.Booster; -9999 donde no se puede puntuar."""
    prob = np.full(valido.shape, NODATA, dtype="float32")
    if valido.any():
        prob[valido] = modelo.predict(datos[:modelo.num_feature()][:, valido].T)   # el modelo v1 usa 10 variables; el v2, 14 (con contexto)
    return prob


def extraer_zonas(prob, ndvi, ndwi, nobs, T, crs, excluir=None, aceptadas=None, estricto=True, unir_px=0, umbral=UMBRAL,
                  margen_px=MARGEN_SIN_DATOS_PX, rellenar_huecos=False):
    """Convierte el mapa de puntaje en zonas. Devuelve (GeoDataFrame, info).

    excluir:   mascara booleana de lo que el modelo ya vio al entrenar (se ignora).
    aceptadas: mascara booleana de las zonas mineras de entrenamiento (se ignora su borde de 100 m).
    estricto: True = las reglas de fotos y de entorno eliminan zonas (piloto). False = solo las marcan (otros lugares).
    umbral: puntaje minimo del pixel (0.5 normal; mas bajo = mas sensible y mas falsos positivos).
    margen_px: margen alrededor de huecos sin datos (600 m en el piloto; en bloques fuera del piloto se usa mucho menos, ver RELAJADO).
    rellenar_huecos: rellena los huecos de cada zona (pozas dentro de una zona minera no la parten ni la reducen).
    unir_px: une pedazos separados por menos de ~2*unir_px pixeles (20 m cada uno). El piloto no une (0).
    El GeoDataFrame trae: puntaje (media), area_ha, obs_mediana, ndvi_mediano y la geometria en 'crs'.
    """
    forma = prob.shape
    px_ha = abs(T.a * T.e) / 10_000
    valido = (prob != NODATA) & np.isfinite(ndwi) & (ndwi != NODATA)
    agua = valido & (ndwi > 0)
    excluir = np.zeros(forma, bool) if excluir is None else excluir
    aceptadas = np.zeros(forma, bool) if aceptadas is None else aceptadas
    cerca_sin_datos = ndi.binary_dilation(~valido, structure=np.ones((3, 3)), iterations=margen_px)
    borde_aceptadas = ndi.binary_dilation(aceptadas, structure=np.ones((3, 3)), iterations=BORDE_ENTRENAMIENTO_PX)
    base = valido & (prob >= umbral)
    mascara = base & ~agua & ~excluir & ~cerca_sin_datos & ~borde_aceptadas
    mascara = ndi.binary_closing(mascara, structure=np.ones((3, 3)))
    mascara = ndi.binary_opening(mascara, structure=np.ones((3, 3)))
    if unir_px:   # areas mineras grandes salen en pedacitos (efecto panal): se unen los que estan muy cerca
        mascara = ndi.binary_closing(mascara, structure=np.ones((3, 3)), iterations=unir_px) & ~agua
    if rellenar_huecos:   # las pozas de agua dentro de una zona minera forman parte de ella
        mascara = ndi.binary_fill_holes(mascara)
    info = {"pixeles_sobre_umbral": int(base.sum()), "de_ellos_agua": int((base & agua).sum()),
            "de_ellos_entrenamiento": int((base & excluir).sum())}
    vacio = gpd.GeoDataFrame({"puntaje": [], "area_ha": [], "obs_mediana": [], "ndvi_mediano": []},
                             geometry=[], crs=crs)
    etiquetas, n = ndi.label(mascara)
    if n == 0:
        info.update(zonas_5ha=0, descartadas_fotos_o_ndvi=0, descartadas_entorno=0, zonas_finales=0)
        return vacio, info
    tamanos = ndi.sum(mascara, etiquetas, index=np.arange(1, n + 1))
    buenos = np.where(tamanos * px_ha >= MIN_HA)[0] + 1
    info["zonas_5ha"] = int(len(buenos))
    if len(buenos) == 0:
        info.update(descartadas_fotos_o_ndvi=0, descartadas_entorno=0, zonas_finales=0)
        return vacio, info

    # Reglas por zona. Todas se calculan siempre:
    #   color   : NDVI mediano < 0.45 (suelo con poca vegetacion). Siempre elimina: una zona verde no es mineria.
    #   fotos   : mediana de 7+ fotos validas por pixel.
    #   entorno : rodeada de vegetacion (NDVI del entorno >= 0.5). Pensada para el norte de La Paz, donde la mineria
    #             aluvial esta dentro del bosque; en una gran area minera el entorno de un pedazo es mas mina.
    # estricto=True (la lista del piloto): fotos y entorno ELIMINAN la zona.
    # estricto=False (analisis de bloques fuera del piloto): solo se MARCAN y la zona queda con confianza "parcial".
    med_obs = np.asarray(ndi.median(nobs.astype("float32"), etiquetas, index=buenos))
    med_ndvi = np.asarray(ndi.median(np.where(np.isfinite(ndvi), ndvi, np.nan), etiquetas, index=buenos))
    color_ok = med_ndvi < NDVI_MEDIANA_MAX
    buenos, med_obs, med_ndvi = buenos[color_ok], med_obs[color_ok], med_ndvi[color_ok]
    fotos_ok = med_obs >= MIN_OBS_MEDIANA
    cajas = ndi.find_objects(etiquetas)
    entorno_ok, ndvi_entorno = [], []
    for k in buenos:
        f, c = cajas[k - 1]
        f0, f1, c0, c1 = max(f.start - 16, 0), f.stop + 16, max(c.start - 16, 0), c.stop + 16
        zona_k = etiquetas[f0:f1, c0:c1] == k
        anillo = ndi.binary_dilation(zona_k, iterations=ANILLO_PX) & ~ndi.binary_dilation(zona_k, iterations=2)
        v = ndvi[f0:f1, c0:c1][anillo & valido[f0:f1, c0:c1]]
        m = float(np.median(v)) if v.size else np.nan
        ndvi_entorno.append(m)
        entorno_ok.append(bool(v.size > 0 and m >= ENTORNO_NDVI_MIN))
    entorno_ok, ndvi_entorno = np.array(entorno_ok, dtype=bool), np.array(ndvi_entorno)
    info["descartadas_color"] = int((~color_ok).sum())
    info["con_pocas_fotos"] = int((~fotos_ok).sum())
    info["con_entorno_sin_vegetacion"] = int((~entorno_ok).sum())
    if estricto:
        info["descartadas_fotos_o_ndvi"] = int((~color_ok).sum()) + int((~fotos_ok).sum())
        info["descartadas_entorno"] = int((fotos_ok & ~entorno_ok).sum())
        mantener = fotos_ok & entorno_ok
    else:
        info["descartadas_fotos_o_ndvi"] = int((~color_ok).sum())
        info["descartadas_entorno"] = 0
        mantener = np.ones(len(buenos), dtype=bool)
    buenos, med_obs, med_ndvi = buenos[mantener], med_obs[mantener], med_ndvi[mantener]
    fotos_ok, entorno_ok, ndvi_entorno = fotos_ok[mantener], entorno_ok[mantener], ndvi_entorno[mantener]
    info["zonas_finales"] = int(len(buenos))
    if len(buenos) == 0:
        return vacio, info

    etiquetas = np.where(np.isin(etiquetas, buenos), etiquetas, 0).astype("int32")
    geoms, ids = [], []
    for g, v in shapes(etiquetas, mask=etiquetas > 0, transform=T):
        geoms.append(shape(g).simplify(15))   # ~15 m: el archivo pesa poco
        ids.append(int(v))
    pm = ndi.mean(np.where(valido, prob, 0), etiquetas, index=ids)
    por_etiqueta = {int(k): (o, nd, fo, eo, ne) for k, o, nd, fo, eo, ne in
                    zip(buenos, med_obs, med_ndvi, fotos_ok, entorno_ok, ndvi_entorno)}
    gdf = gpd.GeoDataFrame({"puntaje": np.round(pm, 3),
                            "obs_mediana": [round(float(por_etiqueta[i][0]), 1) for i in ids],
                            "ndvi_mediano": [round(float(por_etiqueta[i][1]), 3) for i in ids],
                            "fotos_ok": [bool(por_etiqueta[i][2]) for i in ids],
                            "entorno_ok": [bool(por_etiqueta[i][3]) for i in ids],
                            "ndvi_entorno": [round(float(por_etiqueta[i][4]), 3) for i in ids]},
                           geometry=geoms, crs=crs)
    gdf["area_ha"] = (gdf.geometry.area / 10_000).round(1)
    return gdf, info
