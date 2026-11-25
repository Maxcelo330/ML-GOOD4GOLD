# Visor de zonas de posible actividad minera (uso interno)

## Cómo abrirlo
- **Con análisis de bloques (recomendado):** doble clic en `EJECUTAR-VISOR.bat` (en la raíz del proyecto). Abre el visor en `http://127.0.0.1:8765`. Cierra la ventana negra para apagarlo.
- **Solo ver la lista del piloto:** doble clic en `07_VISOR/visor.html`. No analiza bloques.

## Cómo se usa
1. **Ir a un lugar:** escribe un lugar (por ejemplo "La Pampa, Madre de Dios") y el mapa vuela ahí.
2. **Dibujar un bloque:** botón "Dibujar un bloque", y arrastra sobre el mapa. Tamaño: de 1 × 1 a 12 × 12 km (se pone rojo si no cumple).
3. **Analizar:** el programa busca imágenes Sentinel-2 de mayo a septiembre 2026, baja la parte del bloque, calcula índices y pendiente, corre el modelo y aplica los filtros. Tarda cerca de 1 a 2 minutos la primera vez (queda guardado).
4. **Resultado:** las zonas aparecen en violeta con su ficha. Toca una para ver área, puntaje, distancia a río y poblado, y marcar "Mi revisión".
5. **Descargar:** CSV con tu revisión o con la lista completa.

## Trabajar desde otro equipo
1. `git pull` del repo y crear el entorno: `conda env create -f 02_ENTORNO/environment.yml` (queda `g4g-ml`).
2. Doble clic en `EJECUTAR-VISOR.bat`. El repo trae el modelo guardado (`04_DATOS/resultados/modelo_lgbm.txt`), las etiquetas, la zona piloto y la capa de ríos y poblados, así que el análisis de bloques funciona sin descargar nada más que las imágenes del bloque.
3. La **lista de zonas del piloto** no está en git (son zonas sin verificar y el repo es público). En otro equipo el visor arranca sin ella; se regenera con el pipeline (pasos 4 a 6) si se tienen las imágenes del piloto.

## Sensibilidad y confianza
- **Sensibilidad normal** (puntaje mínimo 0,5) es la de la lista del piloto. **Alta** (0,3) marca más terreno removido pero también más falsos positivos.
- Fuera del norte de La Paz, cada zona lleva **confianza "parcial"** si no cumple las reglas del piloto (pocas fotos limpias, entorno sin vegetación). La ficha explica cuál.
- Prueba en La Pampa (Madre de Dios): detecta zonas dentro de la minería pero cubre solo 17 % (normal) a 36 % (alta) del terreno removido. Ver la nota de método, sección 5b.

## Qué hace el análisis y qué no
- Corre el **mismo modelo y las mismas reglas** que la lista del piloto (`nucleo_zonas.py`). Prueba en Tipuani: 75,6 ha y puntaje 72 en el bloque, contra 78,6 ha y puntaje 73 en la lista del piloto.
- **Solo está validado (con límites) en el norte de La Paz.** Fuera de ahí puede confundir suelo agrícola, roca o playas de río con minería. El visor avisa cuando el bloque está fuera de esa zona.
- Resultado = "zonas con parecido a posible actividad minera (por verificar; registro AJAM aún no consultado)". No dice si es legal ni si hay mercurio. El puntaje no es una probabilidad.
- Usa la imagen de mayo-septiembre 2026: no ve cambios en el tiempo.
- Necesita internet para la imagen de fondo, para bajar las imágenes del bloque y para calcular distancias fuera del piloto.

## Datos y licencias
- Ríos y poblados: (c) colaboradores de OpenStreetMap (ODbL). Son una guía.
- Imágenes Sentinel-2 y DEM Copernicus GLO-30 vía Microsoft Planetary Computer (sin credenciales).
- Biblioteca del mapa: Leaflet 1.9.4 (BSD-2), copiada en `lib/leaflet`.

## No se versiona
`visor.html` se genera con `python 05_CODIGO\paso8_visor_html.py` y no va a git (muestra zonas sin verificar; decisión D-002). Los análisis guardados están en `04_DATOS/analisis_bloques/` (tampoco va a git).
