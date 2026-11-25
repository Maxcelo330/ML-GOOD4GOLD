# Plan guiado: aprender ML construyendo un detector de zonas de posible actividad minera (QGIS + imagenes satelitales)

Reemplaza el plan anterior de superpowers (`/plugin` no esta disponible en este entorno).

## Context
Hackathon Gold4Good, desafio ORO-4.2 "Colas con mercurio". Deck el jue 26 nov 23:59; hoy es lun 23 nov. `07_EQUIPO/Apuntes.md` ya pide usar QGIS con imagenes satelitales y deteccion automatica con ML. El usuario no tiene experiencia en machine learning y quiere que el proyecto sirva tambien para aprender: se trabaja paso a paso, cada paso explica el concepto, dice que hace el usuario y que hace Claude, y termina con una comprobacion simple antes de seguir.

Decisiones ya tomadas: resultado = mapa de puntaje de parecido a zonas de posible actividad minera (el puntaje ordena zonas para revisar; no es una probabilidad); zona piloto = norte de La Paz (Tipuani, Mapiri, Teoponte, Guanay); laptop con RTX 4060; alcance hackathon 26 nov.

## Hechos que condicionan el plan
- <mark style="background:#FF000040">El Excel del desafio es sintetico</mark> (nombres "Demo", puntos aleatorios): no sirve para entrenar. Las etiquetas hay que construirlas con fuentes abiertas y digitalizando en QGIS (ese trabajo es parte del aprendizaje).
- No hay datos geoespaciales reales en el vault. QGIS y geopandas no estan instalados; Python por defecto es 3.15 (incompatible con PyTorch), asi que se usara un entorno conda con Python 3.11.
- <mark style="background:#FFD70066">La imagen satelital detecta actividad minera, no legalidad.</mark> "Ilegal" solo se infiere cruzando con el catastro minero (AJAM); sin eso el resultado se llama "posible actividad minera (por verificar; registro AJAM aun no consultado)". "Sin registro conocido" solo se usa despues de cruzar con el catastro. Lenguaje no punitivo, como pide el desafio.
- Noviembre es epoca de lluvias: se usaran imagenes de epoca seca (mayo-sep) y radar.

## Ruta de aprendizaje y trabajo (cada paso = concepto + tu tarea + mi tarea + comprobacion)

### Paso 0 - Fundamentos en 15 minutos (concepto)
Que es aprender de ejemplos: etiquetas (lo que sabemos), variables (lo que mide la imagen), modelo, prediccion, y por que se separa entrenamiento y prueba. Analogia con tu trabajo: un geologo que aprende a reconocer una mina viendo muchos ejemplos.

### Paso 1 - Preparar el taller (hoy)
- Tu: instalar QGIS LTR (te dare el enlace y la guia con capturas de lo que debes ver).
- Yo: crear el entorno conda (Python 3.11 con geopandas, rasterio, lightgbm, scikit-learn, torch) y un `environment.yml`; verificar GPU.
- Comprobacion: QGIS abre un mapa base; en Python `import geopandas, rasterio` funciona.

### Paso 2 - Definir la zona y ver imagenes en QGIS
- Concepto: CRS (WGS84 vs UTM 19S), pixel, resolucion, bandas.
- Tu: dibujar el rectangulo del area piloto en QGIS y cargar imagen satelital de fondo (Esri/Sentinel).
- Yo: descargar Sentinel-2 y Sentinel-1 del area por STAC y cargarlos en QGIS contigo.
- Comprobacion: ves en QGIS una imagen reciente donde se distinguen rio, bosque y zonas removidas.

### Paso 3 - Entender las bandas e indices
- Concepto: NDVI, NDWI, BSI (vegetacion, agua, suelo desnudo); por que la mineria se ve distinta.
- Tu: en QGIS calcular NDVI con la calculadora raster y compararlo con tu ojo.
- Yo: automatizar los mismos indices en Python y mostrar que da lo mismo.

### Paso 4 - Crear las etiquetas (el paso mas importante del ML)
- Concepto: "basura entra, basura sale"; positivos y negativos; sesgo de muestreo.
- Tu: digitalizar en QGIS 100-300 poligonos de zonas mineras (cortes, pozas, dragas, colas) y de zonas no mineras (bosque, rio limpio, agricultura, pueblo).
- Yo: traer poligonos abiertos de mineria (MapBiomas / Global Mining Footprint, previa verificacion de licencia por Gemini) como ayuda y apoyo de control; mezclar todo en un GeoPackage.
- Comprobacion: capa de etiquetas con columna `clase`, revisada visualmente.

### Paso 5 - Primer modelo simple (baseline)
- Concepto: arbol de decision y random forest/LightGBM; sobreajuste; metricas (precision, recall, F1, matriz de confusion).
- Yo: entrenar un modelo con los indices; explicarte cada linea con comentarios y una version en celdas tipo cuaderno.
- Tu: predecir las metricas antes de verlas y discutir donde se equivoca.
- Comprobacion: tabla de metricas con division espacial por bloques (honesta, no aleatoria).

### Paso 6 - Mapa de puntaje en QGIS
- Yo: generar el raster de puntaje y exportarlo.
- Tu: cargarlo en QGIS, estilizarlo (rampa de color), superponer rios y comparar con la imagen; marcar falsos positivos y falsos negativos.
- Resultado: primer mapa visual "donde puede haber mineria".

### Paso 7 - Mejorar con lo que aprendiste
- Corregir etiquetas segun los errores del paso 6, agregar variables (pendiente, distancia a rio, cambio 2025 vs 2026), reentrenar. Opcional si hay tiempo y ganas: red neuronal U-Net (concepto de deep learning) en la RTX 4060.

### Paso 8 - De mapa a lista de puntos para la plataforma
- Yo: convertir el puntaje en poligonos y centroides; calcular `dist_rio_m`, `dist_poblado_m`, area; exportar CSV/GeoJSON con las columnas del modulo "Datos" y "Pasivos" del prototipo (`deteccion = "imagen satelital (ML)"`).
- Tu: cargarlo en `04_EJECUCION-CODEX/codigo/prototipo-web` y ver los puntos en el mapa.
- Cuando se consiga el catastro AJAM/`APM_*`: cruce para el estado "sin registro conocido: verificar".

### Paso 9 - Validar y contar la historia
- Gemini verifica fuentes y cifras; revisamos 20-30 detecciones al azar a ojo; documentamos limites. Preparar la lamina del deck con el flujo: imagen -> modelo -> mapa -> ficha de campo -> priorizacion.

## Cronograma realista (deadline 26 nov 23:59)
- Lun 23: pasos 0, 1 y 2.
- Mar 24: pasos 3 y 4 (digitalizar); en la mentoria de tecnologia pedir catastro AJAM y las capas `residuos_mineros_puntos` / `APM_*`.
- Mie 25: pasos 5, 6 y 8.
- Jue 26: pasos 7 (si alcanza), 9 y entrega con margen.

## Organizacion en el vault (respeta roles)
- Claude: decision D-003 en `03_CEREBRO-CLAUDE/Decisiones.md`, `Arquitectura-solucion.md`, `06_ENTREGABLES/Metodo.md`; ademas una nota guia de aprendizaje (glosario de ML con callouts, sin emojis).
- Codex: codigo en `04_EJECUCION-CODEX/codigo/ml-pipeline/` y tareas T-003+.
- Gemini: `05_VALIDACION-GEMINI/Verificaciones/V-004` (fuentes y licencias) y revision de metricas.
- `07_EQUIPO/` solo lo editan los humanos.

## Verificacion global
- QGIS abre el GeoPackage de etiquetas y el raster de puntaje con CRS correcto.
- El pipeline corre desde `environment.yml` y es reproducible (semillas fijas).
- Metricas con validacion espacial y revision visual documentadas, reportadas tal cual salgan.
- El CSV exportado se carga en el prototipo sin errores.

## Primer paso al aprobar
Empezar por el Paso 0 y el Paso 1: explicarte los conceptos base, darte el enlace y la guia de instalacion de QGIS, y crear el entorno conda con verificacion de GPU (instalar software en tu maquina se hace con tu visto bueno en cada comando).
