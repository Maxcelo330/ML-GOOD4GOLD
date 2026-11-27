# Contrato de datos entre el modelo y la app (g4g-zonas-v1)

Una sola regla: **el modelo propone, una persona revisa, la app muestra.** Lo único que cruza de este repo a la app son zonas que una persona marcó "Parece actividad minera". Nada sale solo ni sin revisión.

## Cómo viajan los datos
```
Visor (este repo)  ->  "Preparar paquete para la app (ZIP)"  ->  zonas_para_la_app.zip  ->  App (repo Good4gold)
  modelo + revisión                                             geojson + excel + csv         Municipio > Detecciones revisadas
```
Lo arma `05_CODIGO/paquete_app.py` (también: `python -I 05_CODIGO\paquete_app.py`). Queda una copia en `04_DATOS/para_la_app/` (no va a git: son datos sensibles, decisión D-002).

## Qué trae el ZIP
| Archivo | Para qué | Cómo entra a la app |
|---|---|---|
| `zonas_revisadas.geojson` | Polígonos de las zonas. Es la vía recomendada. | Municipio, "Detecciones revisadas", "Cargar archivo de zonas (GeoJSON)" |
| `zonas_para_registro.xlsx` | Hoja "Zonas por verificar" con las columnas de la plantilla de pasivos de la app, más columnas de apoyo. Hoja "LEEME". | Para quien ingresa datos: copiar las filas que decida registrar |
| `zonas_revisadas.csv` | Lo mismo que el Excel, en CSV (con BOM para Excel en español) | Igual que el Excel |
| `paquete.json` | Contrato, fecha, cantidad de zonas, versión del modelo, aviso | Para sistemas |
| `LEEME.txt` | Los pasos en lenguaje simple | Para la persona |

**Advertencia importante:** no cargar el Excel con "Datos, Cargar Excel o CSV" de la app. Esa carga reemplaza toda la base (operadores y pasivos). Se comprobó leyendo `js/modules/datos.js` y `js/core/importer.js` del repo de la app (`setDataset`).

## Reglas que cumple el GeoJSON (lo que la app valida al cargar)
- `FeatureCollection` de `Polygon` o `MultiPolygon` en WGS84.
- Cada `Feature` con `properties.id` único (se ignoran las repetidas o sin id).
- Propiedades que la app muestra: `area_ha`, `puntaje_modelo`, `poblado_cercano`, `dist_rio_m`, `dist_poblado_m`, `fecha_revision`, `nota_revision`, `opinion_claude`, `origen`.
- Extras del paquete: `contrato` = `g4g-zonas-v1`, `generado`, `equipo` = `aurum80`, `aviso`.

## Lenguaje y límites (no cambian)
- "Posible actividad minera, por verificar en campo". No dice si es legal ni si hay mercurio; el registro de la AJAM aún no se consultó.
- El puntaje del modelo es relativo, no una probabilidad. La opinión de Claude es de una IA sobre imagen de 20 m, no verificación en campo.
- Las zonas son sensibles: no se publican ni van a git.

## Si cambia el formato
Cambiar solo `paquete_app.py` y subir la versión del contrato (`g4g-zonas-v2`); avisar a quien mantiene la app. Las columnas de la plantilla vienen de `cabeceras('pasivos')` en `js/core/importer.js` de la app.
