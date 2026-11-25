# CLAUDE.md - Proyecto ML-GOOD4GOLD

Detector de zonas de posible actividad minera (QGIS + imagenes satelitales + machine learning) para el hackathon Gold4Good Bolivia 2026, desafio ORO-4.2 "Colas con mercurio". Zona piloto: norte de La Paz (Tipuani, Mapiri, Teoponte, Guanay). Deck: jueves 26 nov 2026 hasta las 23:59.

Este repo es la carpeta oficial de trabajo. `E:\PROYECTO GOOD4GOLD\QGIS MACHINE LEARNING` queda solo como atajo (`EJECUTAR.bat`).

## Metodologia obligatoria: paso a paso
La fuente de verdad es `01_PLAN/Plan-guiado-ML.md`. El usuario no tiene experiencia previa en ML y quiere aprender mientras se construye. Por eso:

1. Se trabaja **un solo paso a la vez**. No se adelanta el siguiente sin confirmacion.
2. Cada paso tiene cuatro partes: **concepto** (en lenguaje de geologo, con analogias), **que hace el usuario**, **que hago yo**, **comprobacion simple**.
3. Se explica cada linea de codigo importante con comentarios en espanol.
4. Antes de ejecutar algo que instale software, descargue datos pesados o modifique el sistema, se pide visto bueno.
5. Las metricas se reportan tal cual salgan, sin maquillar.

## Reglas cientificas (no negociables)
- El Excel del desafio es **sintetico**: no se usa para entrenar ni validar.
- La imagen detecta **actividad minera**, no legalidad ni mercurio. Nunca escribir "ilegal" como resultado del modelo. Formula correcta: "posible actividad minera (por verificar en campo; registro AJAM aun no consultado)". La frase "sin registro conocido" solo se puede usar despues de cruzar con el catastro minero.
- Las cifras del modelo miden coincidencia con las etiquetas (propuestas por Claude, sin verificacion de campo), no exactitud contra el terreno. Los puntajes no son probabilidades.
- Tono **no punitivo** hacia las cooperativas. Los puntos detectados no se muestran al publico como "posible ilegal".
- Validacion **espacial por bloques**, nunca aleatoria (evita fuga por vecindad).
- Imagenes de **epoca seca** (mayo a septiembre) y radar; noviembre es epoca de lluvias.
- CRS de trabajo: **EPSG:32719** (UTM 19S, metros). EPSG:4326 solo para intercambio.
- Semillas fijas y versiones registradas; todo reproducible desde `02_ENTORNO/environment.yml`.
- Ningun dato factual (fuentes, licencias, cifras, coordenadas) pasa a entregables sin verificacion del subagente `verificador`, con enlace y fecha. Sin fuente = "no verificado".

## Roles: todo con Claude y subagentes (decision del usuario, 2026-11-24)
No se mezclan otras IAs (ya no se usan Codex ni Gemini). Los subagentes viven en `.claude/agents/`.

| Quien | Modelo | Hace | No hace |
|---|---|---|---|
| Claude (sesion principal) | el de la sesion | Explica paso a paso, decide el diseno, coordina subagentes, escribe notas T-xxx y V-xxx | Trabajo pesado de descarga o entrenamiento; dar por cierto un dato sin verificar |
| `ejecutor` | Sonnet | Ejecuta el pipeline (T-003, T-004...): descargas, indices, entrenamiento, exportes | Decidir diseno; instalar o descargar sin visto bueno |
| `verificador` | Opus | Verifica fuentes, licencias, coordenadas y cifras con busqueda web (V-004, V-005...) | Editar archivos; afirmar algo sin enlace y fecha |
| `revisor-ml` | Opus | Revisa fugas de datos, metricas, CRS, reproducibilidad y lenguaje | Editar archivos |
| Humano | - | Decide, digitaliza etiquetas en QGIS, edita `07_EQUIPO/` del vault | - |

`07_EQUIPO/` del vault lo editan **solo los humanos**. Las notas T-xxx y V-xxx oficiales viven en el vault; aqui hay copia de consulta. Los archivos `AGENTS.md` y `GEMINI.md` del vault quedan como historial y no se usan.

## Estructura
- `01_PLAN/` plan guiado · `02_ENTORNO/` entorno conda `g4g-ml` (Python 3.11)
- `03_TAREAS-Y-VERIFICACIONES/` T-003 y V-004
- `04_DATOS/` imagenes (no van a git), etiquetas, resultados
- `05_CODIGO/` scripts y cuadernos · `06_QGIS-PROYECTO/` proyecto `.qgz`

## Estilo
- Sin emojis. Para resaltar usar `<mark>` y callouts de Obsidian.
- Comentarios y documentacion en espanol; nombres de archivos sin tildes ni espacios.
- Nunca guardar credenciales en el repo.
