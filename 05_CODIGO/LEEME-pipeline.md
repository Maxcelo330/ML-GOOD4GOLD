# LEEME - Pipeline del compuesto Sentinel-2 (paso 4, tarea T-003 simplificada, sin radar)

Resumen: construye un compuesto Sentinel-2 L2A de epoca seca 2026 (mayo a septiembre), sin nubes,
a 20 m, mas indices espectrales y pendiente del terreno, todo en la misma grilla de la zona piloto.

## Entorno
- Python: entorno conda `g4g-ml` (`02_ENTORNO/environment.yml`).
- Versiones usadas en la ejecucion real: ver `04_DATOS/imagenes/compuesto/metadata.json`, bloque `versiones`
  (python 3.11.18, rasterio 1.4.4, numpy 2.4.6, pystac_client 0.9.1, scipy 1.17.1, geopandas 1.2.0).
- No hacen falta credenciales: Microsoft Planetary Computer entrega los datos gratis (STAC) y el paquete
  `planetary_computer` solo "firma" los enlaces.

## Como reproducirlo desde cero
Desde la raiz del repo (PowerShell):

```powershell
& "$HOME\anaconda3\envs\g4g-ml\python.exe" -I -u 05_CODIGO\paso4_compuesto_indices.py
```

Opciones: `--solo-seleccion` (muestra las escenas que elegiria, sin descargar) y `--conservar-cache`
(no borra `04_DATOS/imagenes/compuesto/_cache_escenas`, la carpeta temporal con las escenas bajadas).
Descarga aproximada: ver `metadata.json`. Tiempo: ver `metadata.json` (`duracion_min`).

Despues, control de calidad:

```powershell
& "$HOME\anaconda3\envs\g4g-ml\python.exe" -I .claude\skills\ml-calidad-datos\check_datos.py 04_DATOS\imagenes\compuesto
```

## Que hace, paso a paso
1. Grilla: bordes de la zona (`aoi_utm19s` de `04_DATOS/zona_piloto.gpkg`) ajustados a multiplos de 20 m,
   EPSG:32719. Todas las salidas comparten exactamente esta grilla.
2. Escenas: coleccion STAC `sentinel-2-l2a`, 2026-05-01 a 2026-09-30, nubes de la escena < 30 %.
   Por cada tile MGRS (19LEC, 19LED, 19LFC, 19LFD) se eligen 6 escenas, mezclando las dos orbitas
   (relativas 96 y 139) que cubren la zona, porque cada orbita deja huecos en franjas distintas.
   Si tras eso queda mas de 0,5 % de la zona sin datos, se agregan 2 escenas por tile (hasta 12) en los
   tiles donde estan los huecos.
3. Bandas: B02, B03, B04, B08 (10 m, se reducen a 20 m promediando 2x2), B11 y B12 (20 m), y la mascara
   SCL (20 m, vecino mas cercano).
4. Mascara de nubes (SCL): se descartan 0 sin datos, 1 saturado, 3 sombra de nube, 8 y 9 nube media/alta,
   10 cirrus, 11 nieve. Se conservan 2, 4, 5, 6 y 7.
5. Reflectancia: `reflectancia = (DN - 1000) / 10000` porque todas las escenas tienen baseline de
   procesamiento >= 04.00 (05.12 o 05.13), que suma un offset de 1000 a los DN. Despues se recorta a [0, 1.5].
6. Compuesto: mediana por pixel de las observaciones validas (se procesa por tiras de 512 filas para no
   agotar la memoria).
7. Indices (sobre los compuestos medianos):
   - NDVI = (B08 - B04) / (B08 + B04)
   - NDWI = (B03 - B08) / (B03 + B08)
   - BSI  = ((B11 + B04) - (B08 + B02)) / ((B11 + B04) + (B08 + B02))
8. Pendiente: DEM Copernicus GLO-30 (coleccion `cop-dem-glo-30`), interpolado a la grilla de 20 m con
   `scipy.ndimage.map_coordinates` (lineal) y gradiente con numpy usando el pixel en metros; se calcula
   con 1 pixel de margen y luego se recorta para evitar el efecto de borde.

## Salidas (en `04_DATOS/imagenes/compuesto/`, no van a git)
| Archivo | Contenido |
|---|---|
| `bandas_2026_20m.tif` | 6 bandas float32 de reflectancia mediana: B02, B03, B04, B08, B11, B12 (con descripcion por banda) |
| `ndvi_2026.tif`, `ndwi_2026.tif`, `bsi_2026.tif` | indices float32 |
| `pendiente_grados.tif` | pendiente en grados, float32 |
| `n_observaciones.tif` | cuantas observaciones validas tiene cada pixel (uint8; 0 = sin datos) |
| `miniaturas/` | PNG de color natural (estirado 2-98 %), NDVI y BSI. Magenta = sin datos |
| `metadata.json` | escenas, fechas, nubes, versiones, reglas, formulas, % sin datos, etc. |
| `_log_ejecucion.txt` | registro de la ultima corrida |

Formato: GeoTIFF, float32, nodata = -9999 (n_observaciones: uint8, nodata 0), compresion deflate.

## Problema conocido del equipo
`rasterio.merge`, `rasterio.windows.from_bounds` y `rasterio.transform.rowcol` cierran Python sin
mensaje (codigo 0xc06d007f). Por eso el script calcula las ventanas a mano con aritmetica sobre
`src.transform` y no usa `rasterio.warp.reproject` (el DEM se remuestrea con scipy).

## Limites a tener en cuenta
- La mascara SCL no es perfecta: puede dejar sombras finas de nube o neblina. La mediana de varias fechas
  lo atenua, pero conviene mirar `n_observaciones.tif`: donde hay 1 o 2 observaciones el compuesto es menos confiable.
- Los indices son del compuesto de mayo a septiembre, no de una fecha concreta.
