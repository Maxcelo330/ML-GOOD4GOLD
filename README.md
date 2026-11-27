# QGIS + Machine Learning: detección de actividad minera (zona piloto norte de La Paz)

Proyecto del equipo **aurum80** (decisión D-003 del hackathon Gold4Good, desafío ORO-4.2; el proyecto aún no tiene nombre propio). Esta carpeta reúne todo lo necesario para trabajar y aprender paso a paso. Es la mitad "modelo" de un sistema de dos partes: este repo mira imágenes de satélite y propone zonas por verificar; el repo de la app (`Good4gold`) las muestra a los funcionarios y recibe denuncias de la ciudadanía.

## Empezar sin saber nada (3 pasos)
1. **Haz doble clic en `EJECUTAR-VISOR.bat`.** Si falta Python, el programa te pregunta y lo instala solo (pide internet y tarda unos 15 minutos la primera vez; solo para tu usuario, sin permisos de administrador).
2. **Dibuja un bloque en el mapa** y pulsa "Analizar". El modelo marca zonas de posible actividad minera. Toca una zona y marca "Parece / No parece actividad minera".
3. **Pulsa "Preparar paquete para la app (ZIP)".** Baja un solo archivo con todo lo que la app necesita y un LEEME con los pasos (ver `CONTRATO-DATOS.md`).

Para solo revisar que el equipo esté bien, sin abrir nada: `EJECUTAR-VISOR.bat /verificar`.

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
| `04_DATOS/banco_bloques` | Imágenes de 31 lugares con etiquetas MapBiomas para reentrenar (pesado, no va a git; `banco_bloques.py`) |
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
