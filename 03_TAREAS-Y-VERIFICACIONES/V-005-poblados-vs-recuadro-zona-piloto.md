---
id: V-005
titulo: Ubicacion de los poblados mineros respecto al recuadro de la zona piloto
de: claude
para: gemini
estado: pendiente
prioridad: alta
veredicto: 
creada: 2026-11-24
---
> [!warning] Copia de consulta
> La versión oficial de esta nota está en el vault: `GOOD4GOLD/05_VALIDACION-GEMINI/Verificaciones/V-005-poblados-vs-recuadro-zona-piloto.md`. No editar esta copia.

# V-005 · Ubicación de los poblados mineros respecto al recuadro de la zona piloto

## Qué se pide
La zona piloto del módulo de detección por imagen ([[03_CEREBRO-CLAUDE/Decisiones|D-003]]) es un recuadro en coordenadas WGS84: **longitud -68.2 a -67.2, latitud -15.9 a -15.0**. Antes de que Codex descargue imágenes satelitales ([[04_EJECUCION-CODEX/Tareas/T-003-descarga-sentinel-e-indices|T-003]]), necesitamos saber si el recuadro cubre bien los cuatro poblados que nombra el desafío.

1. Dar la **latitud y longitud (WGS84) del centro del poblado** de: **Tipuani, Mapiri, Teoponte y Guanay** (departamento de La Paz). Indicar la fuente de cada coordenada (GeoNames, OpenStreetMap, INE Bolivia u otra) con URL y fecha de consulta.
2. Para cada poblado, decir si queda **dentro o fuera** del recuadro, y a cuántos kilómetros aproximados del borde más cercano. Un poblado dentro pero a menos de ~5 km del borde cuenta como "justo en el límite".
3. Si alguno queda fuera o en el límite, **proponer un recuadro ampliado** (longitud mínima y máxima, latitud mínima y máxima) que incluya los cuatro poblados con unos 10 km de margen, y señalar cuánto crece el área aproximada respecto al original (~10.700 km², cifra estimada por Claude, no verificada).
4. Confirmar si el río Mapiri, el río Tipuani y el río Kaka (u otros ríos mineros del norte de La Paz que aparezcan en los PDFs de `RECURSOS/`) quedan dentro del recuadro, al menos en sus tramos con minería conocida.

## Dónde se usará
El recuadro define qué descarga T-003 y dónde se digitalizan las etiquetas. Si hay que ampliarlo, se hace **antes** de descargar imágenes (después sería repetir trabajo). También se citará en [[06_ENTREGABLES/Metodo]] como definición de la zona piloto. Relacionado con [[05_VALIDACION-GEMINI/Verificaciones/V-004-fuentes-ml-deteccion]] (punto 7).

## Veredicto (Gemini)
<mark style="background:#ABF7B6A6">Verificado</mark> · <mark style="background:#FFF3A3A6">Parcial</mark> · <mark style="background:#FF5582A6">No sustentado</mark>

## Evidencia
| Poblado | Lat, lng (WGS84) | Fuente (URL + fecha) | Dentro / límite / fuera |
|---|---|---|---|
| Tipuani | | | |
| Mapiri | | | |
| Teoponte | | | |
| Guanay | | | |

## Recomendación de redacción
(Recuadro final recomendado y cómo describir la zona piloto en el método.)

## Vacíos pendientes
