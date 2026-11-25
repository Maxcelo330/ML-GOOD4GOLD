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
| `04_DATOS/resultados` | Mapa de puntaje (`puntaje_mineria.tif`) y CSV/GeoJSON para la plataforma |
| `05_CODIGO/` | Scripts y cuadernos del pipeline |
| `06_QGIS-PROYECTO/` | Proyecto `.qgz` |
| `07_VISOR/` | Visor interactivo: dibuja un bloque en el mapa y el modelo marca zonas (arranca con `EJECUTAR-VISOR.bat`; ver `LEEME.md`) |

## Entorno
```
conda env create -f 02_ENTORNO/environment.yml
conda activate g4g-ml
```
PyTorch con GPU (RTX 4060) se agrega después, solo si llegamos a la red neuronal.

## Cómo trabajamos
- **Un paso a la vez.** El plan está en `01_PLAN/Plan-guiado-ML.md`. Cada paso trae concepto, tu tarea, la tarea de Claude y una comprobación; no se avanza hasta confirmar la comprobación.
- **Todo con Claude y subagentes** (sin mezclar otras IAs). Claude explica y coordina; `ejecutor` (Sonnet) corre el pipeline; `verificador` (Opus) comprueba fuentes, licencias y coordenadas con búsqueda web; `revisor-ml` (Opus) revisa fugas de datos y métricas. El humano decide y digitaliza las etiquetas en QGIS.
- **Herramientas del proyecto** (en `.claude/`): skills `ml-paso` (enseña un paso) y `ml-calidad-datos` (revisa etiquetas y rasters antes de entrenar); agentes `ejecutor`, `verificador` y `revisor-ml`.
- **Carpeta oficial:** este repo. `E:\PROYECTO GOOD4GOLD\QGIS MACHINE LEARNING` queda solo como atajo (`EJECUTAR.bat`).

## Notas T-xxx y V-xxx: el vault manda
Las tareas para Codex y los pedidos a Gemini se escriben y se responden en el vault `GOOD4GOLD`. Las copias de `03_TAREAS-Y-VERIFICACIONES/` son solo de consulta, están marcadas como tales y no se editan. Cuando una nota se cierra, se vuelve a copiar aquí antes del siguiente commit.

## Reglas clave
- El Excel del desafío es sintético: no se usa para entrenar.
- La imagen detecta actividad minera, no legalidad ni mercurio.
- Lenguaje no punitivo; los puntos detectados no se muestran al público como "posible ilegal".

## Relación con el vault
Las versiones oficiales de T-003, V-004 y V-005 están en el vault `GOOD4GOLD` (`04_EJECUCION-CODEX/Tareas/` y `05_VALIDACION-GEMINI/Verificaciones/`), porque Codex y Gemini las leen ahí y la decisión D-003 enlaza a esas rutas. Aquí hay una copia de consulta.
