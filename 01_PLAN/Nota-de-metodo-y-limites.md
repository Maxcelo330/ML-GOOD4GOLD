# Nota de método y límites del modelo (versión del 25-nov-2026)

> [!warning] Lectura obligatoria antes de usar cualquier cifra en el deck
> Esta nota dice qué se puede afirmar y qué no. Las cifras miden **coincidencia con etiquetas propuestas por Claude, sin verificación en campo**. No miden exactitud contra el terreno.

## 1. Qué hace el sistema
Con imágenes Sentinel-2 (mayo a septiembre 2026, 20 m) y la pendiente del terreno, un modelo LightGBM da a cada píxel un **puntaje de parecido** a las zonas mineras que le enseñamos. Luego se agrupan los píxeles de puntaje alto en zonas y se entregan **30 zonas para revisar** (más 13 zonas de lectura visual, aparte).

- Zona piloto: norte de La Paz (Tipuani, Mapiri, Teoponte, Guanay), unos 13.000 km².
- Resultado: una **lista de zonas a revisar**, no detecciones confirmadas.
- Lenguaje oficial: "posible actividad minera (por verificar; registro AJAM aún no consultado)". La imagen detecta actividad, no legalidad ni mercurio.

## 2. De dónde salen las etiquetas (límite principal)
| Hecho | Consecuencia |
|---|---|
| Casi todas las etiquetas son **propuestas de Claude** mirando la imagen (columna `decision_por`). Solo una decisión la tomó una persona | El modelo aprende lo que Claude ve; si Claude se equivoca, el modelo se equivoca igual |
| No hay verificación en campo ni cruce con el catastro AJAM | No se puede hablar de "exactitud" ni de legalidad |
| Solo hay **9 polígonos mineros** y **108 no mineros** para entrenar | Pocas minas: el resultado cambia mucho según cuáles caigan en el examen (F1 entre 0,24 y 0,50 por parte del mapa) |
| 52 de los 108 no mineros son **bancos de arena de río** que se agregaron después de ver que el primer modelo los confundía (todos en Teoponte) | Es "minado de errores": mejora el modelo pero **hace las cifras algo optimistas** |

## 3. Cómo se midió y qué salió
La prueba es **espacial**: el mapa se corta en cuadros de 5 km y cada cuadro va al entrenamiento o al examen, nunca a los dos. Hay otra prueba más dura: entrenar con tres pueblos y examinar en el cuarto. Se comparó con reglas simples de vegetación.

| Prueba | Modelo (F1) | Regla NDVI < 0,3 (F1) |
|---|---|---|
| Por cuadros de 5 km, con los bancos de arena | 0,40 | 0,22 |
| Por cuadros de 5 km, **sin** los bancos de arena | 0,46 | 0,49 |
| Dejando un pueblo afuera | 0,46 | 0,58 |
| Por cuadros, con 3 km de exclusión entre entrenamiento y examen | 0,37 | no calculado |

> [!important] Lo que se puede decir
> - "Con zonas del mapa que el modelo no vio al entrenar, el F1 es de unos 0,37 a 0,40, contra etiquetas sin verificar en campo (9 zonas mineras y 108 no mineras)."
> - "Una regla simple de vegetación rinde igual o mejor, salvo en bancos de arena de río, donde el modelo ayuda."
> - "Las 30 zonas son una lista para revisar, no detecciones confirmadas."

> [!danger] Lo que NO se puede decir
> - "El modelo supera a la regla simple de vegetación."
> - Cualquier "exactitud" o "precisión" contra el terreno.
> - "Probabilidad del 83 %": el puntaje **no es una probabilidad** (el modelo se entrenó dando más peso a la clase minera).
> - "Probado en los cuatro pueblos" o "zonas revisadas".

## 4. Límites conocidos del modelo
1. **La pendiente es un atajo.** Los bancos de arena están en terreno plano y las minas de entrenamiento en valles con pendiente. El modelo usa la pendiente para separarlos, por lo que **encuentra mal la minería en terreno plano**.
2. **Solo 3 de 4 pueblos se pudieron examinar.** Teoponte no tiene ninguna mina etiquetada; ahí solo hay negativos.
3. **Fuga residual pequeña:** con 3 km de exclusión el F1 baja de 0,40 a 0,37. Por eso se reporta el rango.
4. **Confusiones conocidas:** bancos de arena de ríos grandes, pastizales, derrumbes y laderas de roca o suelo pardo natural, restos de nube.
5. **Resolución de 20 m:** una mina pequeña (menos de 5 ha) no se ve. Se descartan zonas menores a 5 ha.
6. **Distancias a río y a poblado:** `dist_rio_m` y `dist_poblado_m` van vacías. Falta la capa de ríos.

## 5. Filtros aplicados a la lista de 30 zonas
Se aplicaron tras la segunda revisión independiente (25-nov):
- Se quitan las zonas con menos de 7 fotos válidas (mediana) o con NDVI mediano de 0,45 o más.
- Margen de 600 m alrededor de huecos sin datos (restos de nube).
- Se quitan los bordes pegados (100 m) a zonas mineras de entrenamiento: no son hallazgos nuevos.
- Se quitan las zonas rodeadas de terreno sin vegetación (NDVI del entorno menor a 0,5): laderas de roca o suelo pardo natural.
- Prioridad única "por revisar": las diferencias de puntaje entre zonas son de décimas y no justifican "alta, media, baja".
- Revisión visual de las 30 zonas sobre la imagen (hoja de contacto): todas son suelo removido dentro de bosque. Que lo parezca **no confirma** que sea minería.

Las 13 zonas de lectura visual (LV) son ejemplos de entrenamiento, sin puntaje, rotuladas "sin verificar". Dos miden más de 1.000 ha y probablemente agrupan varias áreas.

## 6. Reproducibilidad
- Semilla fija (42), versiones y fechas en `04_DATOS/resultados/modelo_info.json` y `04_DATOS/imagenes/compuesto/metadata.json`.
- `05_CODIGO/paso3f_agregar_errores_modelo.py` **no se puede volver a correr desde cero** (usa posiciones de un ranking que ya cambió). Queda como registro; el resultado está en `04_DATOS/etiquetas/candidatos.gpkg`.
- Los pasos 3b a 3f no deben correrse sobre `candidatos.gpkg` sin copia de respaldo: pueden sobrescribir decisiones.

## 7. Qué falta para que sea defendible
1. Verificar en campo (o con el catastro AJAM) una muestra de las 30 zonas.
2. Que una persona revise las ~28 candidatas dudosas y las 9 mineras etiquetadas.
3. Etiquetar minas en Teoponte para poder examinar el cuarto pueblo.
4. Agregar la capa de ríos (`dist_rio_m`) y el cruce con AJAM.
