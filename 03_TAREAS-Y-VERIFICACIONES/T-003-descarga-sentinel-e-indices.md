---
id: T-003
titulo: Descarga de Sentinel-2/1 de la zona piloto y cálculo de índices
de: claude
para: codex
estado: pendiente
prioridad: alta
entregable: "[[06_ENTREGABLES/Metodo]]"
creada: 2026-11-23
---
# T-003 · Descarga de Sentinel-2/1 de la zona piloto y cálculo de índices

## Objetivo
Un pipeline reproducible en Python que, para la zona piloto (norte de La Paz), descargue imágenes Sentinel-2 L2A y Sentinel-1 de **época seca**, cree compuestos sin nubes y calcule las variables que usará el modelo de detección de actividad minera. Es la primera fase de la decisión de añadir un módulo de detección por imagen (la alternativa A de la guía), orientado a priorizar zonas por verificar. **No** clasifica legalidad.

## Entradas
- Entorno: `environment.yml` (conda, `g4g-ml`, Python 3.11) que prepara Claude/el humano y se copia a `04_EJECUCION-CODEX/codigo/ml-pipeline/` al iniciar la tarea.
- Zona piloto (bbox WGS84): lat -15.9 a -15.0, lng -68.2 a -67.2 (la misma de `js/data/hidro-zona.js` del prototipo).
- [[01_DESAFIO-4.2/Restricciones]] y [[03_CEREBRO-CLAUDE/Decisiones]] (D-001, D-003)
- Fuentes: Microsoft Planetary Computer (STAC, sin costo) o Copernicus Data Space. Documentar cuál se usó.

## Criterio de aceptación
- [ ] Compuesto mediano Sentinel-2 L2A de mayo a septiembre de 2026 (y otro de 2025 para comparar), con máscara de nubes (SCL), bandas B2, B3, B4, B8, B11, B12
- [ ] Compuesto Sentinel-1 (VV y VH) del mismo periodo
- [ ] Índices NDVI, NDWI y BSI como rasters aparte, con la fórmula escrita en el README
- [ ] Pendiente (slope) calculada desde el DEM Copernicus GLO-30
- [ ] Primera corrida a 20 m de resolución para la zona completa; opción de 10 m en una subzona
- [ ] Todos los rasters en GeoTIFF con CRS EPSG:32719 (UTM 19S) abribles en QGIS, más un `metadata.json` con fechas, ID de escenas, versiones y semilla
- [ ] Un `README` con versiones fijadas y los comandos para reproducir desde cero
- [ ] No se descarga nada con credenciales guardadas en el vault

## Formato de entrega
Código en `04_EJECUCION-CODEX/codigo/ml-pipeline/`. Los rasters pesados **no** se guardan en el vault: van a `E:\PROYECTO GOOD4GOLD\QGIS MACHINE LEARNING\04_DATOS\imagenes\` (fuera del vault; ahí también está `zona_piloto.gpkg` con el AOI) y el README indica la ruta. Una miniatura PNG de cada compuesto en `04_EJECUCION-CODEX/Entregas/`.

## Bloqueo
Ninguno para esta fase. La fase de entrenamiento (T-004) queda bloqueada hasta que el humano entregue el GeoPackage de etiquetas digitalizadas en QGIS (carpeta `07_EQUIPO/` o la que indique el equipo).

## Resultado
