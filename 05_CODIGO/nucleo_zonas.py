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


def variables_y_validez(bandas, ndvi, ndwi, bsi, pendiente, nobs):
    """Arma la pila de 10 variables (orden de VARIABLES) y la mascara de pixeles que se pueden puntuar.

    bandas: (6, alto, ancho) en el orden B02, B03, B04, B08, B11, B12.
    """
    datos = np.concatenate([bandas, ndvi[None], ndwi[None], bsi[None], pendiente[None]]).astype("float32")
    valido = np.isfinite(datos).all(axis=0) & (datos != NODATA).all(axis=0) & (nobs >= MIN_OBS)
    with np.errstate(invalid="ignore"):
        valido &= datos[0] < B02_MAX
    datos[:, ~valido] = np.nan
    return datos, valido


def puntuar(modelo, datos, valido):
    """Puntaje (0 a 1) de cada pixel valido con un lightgbm.Booster; -9999 donde no se puede puntuar."""
    prob = np.full(valido.shape, NODATA, dtype="float32")
    if valido.any():
        prob[valido] = modelo.predict(datos[:, valido].T)
    return prob


def extraer_zonas(prob, ndvi, ndwi, nobs, T, crs, excluir=None, aceptadas=None):
    """Convierte el mapa de puntaje en zonas. Devuelve (GeoDataFrame, info).

    excluir:   mascara booleana de lo que el modelo ya vio al entrenar (se ignora).
    aceptadas: mascara booleana de las zonas mineras de entrenamiento (se ignora su borde de 100 m).
    El GeoDataFrame trae: puntaje (media), area_ha, obs_mediana, ndvi_mediano y la geometria en 'crs'.
    """
    forma = prob.shape
    px_ha = abs(T.a * T.e) / 10_000
    valido = (prob != NODATA) & np.isfinite(ndwi) & (ndwi != NODATA)
    agua = valido & (ndwi > 0)
    excluir = np.zeros(forma, bool) if excluir is None else excluir
    aceptadas = np.zeros(forma, bool) if aceptadas is None else aceptadas
    cerca_sin_datos = ndi.binary_dilation(~valido, structure=np.ones((3, 3)), iterations=MARGEN_SIN_DATOS_PX)
    borde_aceptadas = ndi.binary_dilation(aceptadas, structure=np.ones((3, 3)), iterations=BORDE_ENTRENAMIENTO_PX)
    base = valido & (prob >= UMBRAL)
    mascara = base & ~agua & ~excluir & ~cerca_sin_datos & ~borde_aceptadas
    mascara = ndi.binary_closing(mascara, structure=np.ones((3, 3)))
    mascara = ndi.binary_opening(mascara, structure=np.ones((3, 3)))
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

    # Filtro por zona: suficientes fotos validas y vegetacion baja
    med_obs = np.asarray(ndi.median(nobs.astype("float32"), etiquetas, index=buenos))
    med_ndvi = np.asarray(ndi.median(np.where(np.isfinite(ndvi), ndvi, np.nan), etiquetas, index=buenos))
    pasa = (med_obs >= MIN_OBS_MEDIANA) & (med_ndvi < NDVI_MEDIANA_MAX)
    info["descartadas_fotos_o_ndvi"] = int((~pasa).sum())
    buenos, med_obs, med_ndvi = buenos[pasa], med_obs[pasa], med_ndvi[pasa]

    # Filtro por entorno: la mineria aluvial de la zona esta rodeada de bosque
    cajas = ndi.find_objects(etiquetas)
    entorno_ok = []
    for k in buenos:
        f, c = cajas[k - 1]
        f0, f1, c0, c1 = max(f.start - 16, 0), f.stop + 16, max(c.start - 16, 0), c.stop + 16
        zona_k = etiquetas[f0:f1, c0:c1] == k
        anillo = ndi.binary_dilation(zona_k, iterations=ANILLO_PX) & ~ndi.binary_dilation(zona_k, iterations=2)
        v = ndvi[f0:f1, c0:c1][anillo & valido[f0:f1, c0:c1]]
        entorno_ok.append(v.size > 0 and np.median(v) >= ENTORNO_NDVI_MIN)
    entorno_ok = np.array(entorno_ok, dtype=bool)
    info["descartadas_entorno"] = int((~entorno_ok).sum())
    buenos, med_obs, med_ndvi = buenos[entorno_ok], med_obs[entorno_ok], med_ndvi[entorno_ok]
    info["zonas_finales"] = int(len(buenos))
    if len(buenos) == 0:
        return vacio, info

    etiquetas = np.where(np.isin(etiquetas, buenos), etiquetas, 0).astype("int32")
    geoms, ids = [], []
    for g, v in shapes(etiquetas, mask=etiquetas > 0, transform=T):
        geoms.append(shape(g).simplify(15))   # ~15 m: el archivo pesa poco
        ids.append(int(v))
    pm = ndi.mean(np.where(valido, prob, 0), etiquetas, index=ids)
    por_etiqueta = {int(k): (o, nd) for k, o, nd in zip(buenos, med_obs, med_ndvi)}
    gdf = gpd.GeoDataFrame({"puntaje": np.round(pm, 3),
                            "obs_mediana": [round(float(por_etiqueta[i][0]), 1) for i in ids],
                            "ndvi_mediano": [round(float(por_etiqueta[i][1]), 3) for i in ids]},
                           geometry=geoms, crs=crs)
    gdf["area_ha"] = (gdf.geometry.area / 10_000).round(1)
    return gdf, info
