# Nota de método y límites del modelo (versión del 26-nov-2026)

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

## 5b. Análisis de bloques en cualquier lugar (visor con servidor local)
El visor permite dibujar un bloque (hasta 30 × 30 km) en cualquier lugar. El programa baja la imagen Sentinel-2 de ese bloque (mayo a septiembre 2026), calcula los mismos índices y la pendiente, corre el modelo guardado (`modelo_lgbm.txt`) y aplica los mismos filtros de la sección 5 (`nucleo_zonas.py`).

> [!warning] Fuera del norte de La Paz el modelo NO está validado
> Se entrenó y se midió solo en Tipuani, Mapiri, Teoponte y Guanay. En otras regiones (por ejemplo la selva baja de Madre de Dios, con pozas grandes y terreno plano) no sabemos cuánto acierta, y la pendiente como atajo (sección 4) hace que encuentre mal la minería en terreno plano. Un resultado ahí solo sirve como **demostración de la herramienta**, no como evidencia de minería.

- Comprobación hecha: en un bloque de Tipuani el análisis encontró la zona conocida (75,6 ha, puntaje 72) frente a la lista del piloto (78,6 ha, puntaje 73), con imágenes bajadas de nuevo. La diferencia viene de elegir fotos distintas para la mediana.
- El modelo guardado se reentrenó con la misma semilla y dio métricas y mapa idénticos al original.
- **Prueba fuera del piloto (La Pampa, Madre de Dios, bloque de 9,8 × 8,8 km, 25-nov-2026):** hay unas 6.100 ha de terreno sin vegetación (prácticamente todo minería). Con sensibilidad normal el modelo marca 1.271 ha (17 % de ese terreno); con sensibilidad alta, entre 2.750 y 3.100 ha (36 a 39 %), a costa de más marcas fuera de ese terreno (~19 %). **Detecta zonas reales dentro de la minería pero deja sin marcar buena parte; la cobertura es baja fuera de donde se entrenó.** Se compara contra "terreno sin vegetación", no contra una verdad de campo.
- Dos reglas del piloto (mediana de 7+ fotos limpias y "entorno con vegetación") eliminaban casi todo en la selva baja (nublada y con minas enormes). Fuera del piloto ahora solo **marcan** la zona como "confianza parcial" y el visor lo avisa; dentro del piloto siguen eliminando, y la lista del piloto no cambió (CSV idéntico). En el modo relajado también se unen pedazos separados por menos de unos 120 m.
- La sensibilidad alta (puntaje mínimo 0,3 en vez de 0,5) es una opción de quien analiza, con el costo explicado en el visor.
- Lo que el visor dice: "zonas con parecido a posible actividad minera (por verificar; registro AJAM aún no consultado)". Nunca "hay minería" ni "ilegal".

## 5c. Modelo v2: entrenado con muchos lugares y con ayuda de IA (26-nov-2026)
> [!warning] Qué cambió y qué no
> La **lista de 30 zonas del piloto no cambia**: sigue saliendo del modelo v1 y de sus reglas estrictas. El modelo v2 se usa en el **análisis de bloques** del visor (cualquier lugar). Aun así, v2 sigue encontrando 26 de las 30 zonas del piloto (puntaje medio de 0,5 o más dentro de cada zona).

**Por qué.** El modelo v1 solo conocía 9 minas de laderas del norte de La Paz y fallaba en terreno plano (Madre de Dios): marcaba poco de lo que era minería.

**Qué se hizo** (`banco_bloques.py`, `paso10_reentrenar.py`, `paso10b_objetos_revision.py`):
1. Se bajaron imágenes Sentinel-2 (misma receta) de **31 bloques de unos 11 km**: 12 con mucha minería (Madre de Dios, Puno, Pataz y tres del piloto) y 19 **sin minería** (ciudades, ríos con bancos de arena, pastizales, agricultura, valles).
2. Segunda fuente de etiquetas, **independiente de las propuestas de Claude**: el mapa **MapBiomas Perú y Bolivia, clase 30 (Minería), 2023 y 2024** (CC BY-SA 4.0). Un píxel es minero solo si lo es en los dos años. MapBiomas es una clasificación automática de Landsat a 30 m, **no es verdad de campo**.
3. Cuatro variables nuevas de **contexto** (textura del NDVI a 100 m; NDVI medio, fracción de agua y fracción de suelo sin vegetación a 300 m).
4. **Revisión con IA de los desacuerdos:** con un modelo que no vio el bloque se buscaron manchas de más de 5 ha donde el modelo y MapBiomas no coinciden (80 casos). Claude (4 subagentes) las miró en tres vistas (color natural con contorno, de cerca y falso color) y las etiquetó. Resultado: de 56 marcas del modelo que MapBiomas no tenía, **37 eran falsos positivos reales** (ciudades, bancos de arena, roca), **7 parecen minería que MapBiomas no vio** y 12 quedaron dudosas; de 24 minas de MapBiomas que el modelo no marcó, 19 son minería (error del modelo) y 5 dudosas. Los "dudosos" no se usan para entrenar.

**Cómo se midió.** Cada bloque se examina con un modelo que **no lo vio**, y el bloque de La Pampa nunca entra al entrenamiento de ningún modelo examinado. Se mide el producto final (las zonas que ve la persona, con las reglas relajadas de fuera del piloto) contra MapBiomas.

| 11 bloques con más de 1.000 ha de minería en MapBiomas (media) | v1 | v2 (sin revisión IA) | v2 (con revisión IA) |
|---|---|---|---|
| Minería de MapBiomas cubierta por zonas | 39 % | 69 % | 66 % |
| De lo marcado, % que MapBiomas también marca | 57 % | 64 % | 65 % |
| Hectáreas marcadas en **bloques de control sin minería** (media de 19 bloques) | 2.630 | 1.528 | 1.043 |

La Pampa (bloque que el modelo nunca vio): v1 cubre 54 % de la minería de MapBiomas; v2, 90 %. En los tres bloques del piloto: de 5 a 12 % (v1) a 41 a 73 % (v2).

> [!danger] Lo que NO se puede decir
> - "Exactitud" o "precisión contra el terreno": todo se mide contra MapBiomas (otra estimación) y contra la lectura de una IA, sin verificación en campo.
> - Que el falso positivo esté resuelto: en **ciudades** (por ejemplo Cochabamba y el valle del Mantaro) y en **grandes ríos con bancos de arena** (Madre de Dios) sigue marcando cientos o miles de hectáreas cuando el modelo no vio ese tipo de lugar. Por eso cada zona de un bloque fuera del piloto lleva "confianza parcial" y el aviso del visor.
> - Que lo que MapBiomas no marca sea "no minería": en La Pampa el modelo marca más hectáreas que MapBiomas (11.300 contra 6.500) y 26 % de lo marcado no está en MapBiomas; parte serán minas que MapBiomas no vio y parte falsos positivos. No se sabe sin verificar.
> - Los números por bloque cambian bastante (hay bloques donde v2 no mejora); son pocos bloques.

**Límites propios de este paso:** 12 bloques con minería, casi todos en Madre de Dios; en Pataz la cobertura sube poco (14 a 27 %) y en Puno baja (98 a 74 %), aunque con mucha más coincidencia con MapBiomas en lo marcado (23 a 59 %). Las etiquetas de la IA son una opinión sobre una imagen de 20 m; 80 casos revisados es poco. MapBiomas puede equivocarse en los bordes de las minas.

**Segunda opinión en el visor.** Cada zona de un bloque tiene el botón "Pedir segunda opinión a Claude": se envían a la API de Claude tres recortes de la zona y los datos del modelo, y vuelve un veredicto (parece minería, dudosa, no parece), los motivos y qué comprobar. Necesita una clave de la API (`clave_api.txt`, fuera de git) y tiene un costo pequeño por zona (una consulta real costó US$ 0,009, unos 2.300 tokens de entrada y 430 de salida; el visor muestra un contador y tiene un tope de gasto). La revisión que hace la persona en el visor queda guardada en `04_DATOS/etiquetas/revisiones_visor.jsonl` y es la etiqueta de más valor para el próximo reentrenamiento.

## 5d. Verificación en el visor y aprendizaje continuo (26-nov-2026)
- **Comparación antes / después.** Para cada zona de un bloque se abre una ventana con una cortina: imagen histórica de Esri Wayback (fecha elegible) frente a Sentinel-2 de 2026, con el contorno de la zona y, si se pide, el mapa de calor del puntaje del modelo (`recorte_zona.py`). Sirve para ver si hubo cambio de monte a suelo removido o si ya era río o suelo claro. Límite: la fecha de Esri es la de la versión del mapa, la foto puede ser anterior, y la resolución de Sentinel-2 (20 m) es menor que la de Esri.
- **Selección con Claude y precisión según Claude.** Se pueden elegir zonas y pedir la opinión de Claude en lote (3 a la vez, con costo estimado, contador y tope). El panel compara lo que marca el modelo con lo que Claude confirma (precisión estimada = confirmadas / (confirmadas + descartadas), sin contar dudosas), por rango de puntaje y por versión del modelo. Es coincidencia con la opinión de una IA, no exactitud contra el terreno.
- **Aprendizaje (`aprendizaje.py`).** Las opiniones de Claude (confianza alta o media, no dudosas) y las revisiones de personas se usan como etiquetas de píxel dentro de cada zona (las de personas pesan 3, las de Claude 1 o 2). Se entrena un modelo nuevo con el banco de 31 lugares, el piloto y esas etiquetas, y **solo se activa si**: (a) en La Pampa (que no entra a ese entrenamiento de prueba) el F1 no baja más de 0,03 ni la cobertura más de 5 puntos, y (b) coincide al menos igual con las revisiones en zonas que no había visto (validación cruzada por bloque). El modelo anterior no se borra. Con esto se busca que dependa cada vez menos de Claude; el panel muestra la coincidencia antes y después.
- **Límites.** Las zonas revisadas son las que el modelo ya marcó, así que lo que se aprende son sobre todo falsos positivos y confirmaciones, no minas que el modelo no ve. Aprender de una IA puede copiar sus errores: por eso pesa menos que una persona y se exige no empeorar en La Pampa. Con pocas revisiones la medida de coincidencia es ruidosa (la prueba técnica con 14 zonas simuladas dio 43 % antes y después, sin valor estadístico). No se ha medido todavía con revisiones reales de Claude ni con revisiones de personas.

## 6. Reproducibilidad
- Semilla fija (42), versiones y fechas en `04_DATOS/resultados/modelo_info.json` y `04_DATOS/imagenes/compuesto/metadata.json`.
- `05_CODIGO/paso3f_agregar_errores_modelo.py` **no se puede volver a correr desde cero** (usa posiciones de un ranking que ya cambió). Queda como registro; el resultado está en `04_DATOS/etiquetas/candidatos.gpkg`.
- Los pasos 3b a 3f no deben correrse sobre `candidatos.gpkg` sin copia de respaldo: pueden sobrescribir decisiones.

## 7. Qué falta para que sea defendible
1. Verificar en campo (o con el catastro AJAM) una muestra de las 30 zonas.
2. Que una persona revise las ~28 candidatas dudosas y las 9 mineras etiquetadas.
3. Etiquetar minas en Teoponte para poder examinar el cuarto pueblo.
4. Agregar la capa de ríos (`dist_rio_m`) y el cruce con AJAM.
