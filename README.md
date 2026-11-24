# QGIS + Machine Learning: detección de actividad minera (zona piloto norte de La Paz)

Proyecto de la decisión D-003 del hackathon Gold4Good (desafío ORO-4.2). Esta carpeta reúne todo lo necesario para trabajar y aprender paso a paso.

## Contenido
| Carpeta | Qué hay |
|---|---|
| `01_PLAN/` | Plan guiado de 10 pasos (Plan-guiado-ML.md) |
| `02_ENTORNO/` | `environment.yml` del entorno conda `g4g-ml` (Python 3.11) |
| `03_TAREAS-Y-VERIFICACIONES/` | T-003 (para Codex) y V-004 (para Gemini) |
| `04_DATOS/imagenes` | Rasters Sentinel y DEM (pesados, no van a git) |
| `04_DATOS/etiquetas` | GeoPackage con polígonos que digitalizas en QGIS |
| `04_DATOS/resultados` | Mapa de probabilidad y CSV/GeoJSON para la plataforma |
| `05_CODIGO/` | Scripts y cuadernos del pipeline |
| `06_QGIS-PROYECTO/` | Proyecto `.qgz` |

## Entorno
```
conda env create -f 02_ENTORNO/environment.yml
conda activate g4g-ml
```
PyTorch con GPU (RTX 4060) se agrega después, solo si llegamos a la red neuronal.

## Reglas clave
- El Excel del desafío es sintético: no se usa para entrenar.
- La imagen detecta actividad minera, no legalidad ni mercurio.
- Lenguaje no punitivo; los puntos detectados no se muestran al público como "posible ilegal".

## Relación con el vault
Las copias de T-003 y V-004 que usan los agentes siguen en el vault `GOOD4GOLD` (`04_EJECUCION-CODEX/Tareas/` y `05_VALIDACION-GEMINI/Verificaciones/`), porque Codex y Gemini las leen ahí y la decisión D-003 enlaza a esas rutas. Aquí hay una copia de consulta.
