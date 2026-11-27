# Presentación animada del equipo aurum80 (video tipo keynote)

Una presentación de ~4,5 minutos hecha en HTML, que se puede **ver en el navegador** y **grabar a un video MP4**. Muestra lo que hace el modelo de detección (cómo ve el satélite, cómo "piensa" el modelo, cómo se forman las zonas, cómo se verifican, cómo aprende) y la plataforma web para reportar (ciudadano, funcionario, sincronización entre dispositivos).

## Verla
1. **Doble clic en `ABRIR-PRESENTACION.bat`** (en esta carpeta). Levanta un servidor local, elige un puerto libre (desde el 8811) y abre la presentación en el navegador. Deja la ventana negra abierta; ciérrala para apagarlo. Abrir `presentacion.html` con doble clic NO funciona (el navegador bloquea la lectura de los datos).
   A mano (entorno g4g-ml): `python -I -m http.server 8811` dentro de `08_PRESENTACION`, y abrir `http://127.0.0.1:8811/presentacion.html`.
2. Pulsar el botón de play (o usar `?auto=1` en la dirección).
- Si sale "Error 404 File not found": hay otro servidor viejo en ese puerto sirviendo otra carpeta. Cierra esa ventana o usa el `.bat`, que busca un puerto libre.
- Controles: **espacio** pausa, **flechas** cambian de escena, **F** pantalla completa, **C** subtítulos, **R** reinicia, clic en la barra de abajo salta a ese momento, **1 a 9** van a la escena.
- Parámetros en la dirección: `?auto=1` empieza sola, `?t=45` empieza en el segundo 45, `?ui=0` sin barra, `?cap=0` sin subtítulos.

## Grabar el video (MP4 1080p, sin instalar nada)
`node 08_PRESENTACION/herramientas/grabar.mjs 8811 salida.mp4 30` (con la presentación abierta en el puerto 8811, ver arriba)
Graba cuadro a cuadro con Chrome (la presentación es una función del tiempo, así que el resultado es perfecto aunque el computador sea lento; tarda unos 20 a 30 minutos). El MP4 usa H.264 y no lleva audio: se puede agregar narración o música en cualquier editor (los textos de narración están como subtítulos en cada escena).
Comprobar el video: `node 08_PRESENTACION/herramientas/verificar_mp4.mjs salida.mp4 60 captura.jpg`.

## Escenas (16, 295 s = 4 min 55 s)
| # | Escena | s | | # | Escena | s |
|---|---|---|---|---|---|---|
| 1 | Apertura | 13 | | 9 | Segunda opinión de Claude | 22 |
| 2 | El reto | 15 | | 10 | El modelo aprende | 22 |
| 3 | La idea | 12 | | 11 | Denunciar desde el celular | 25 |
| 4 | El satélite | 22 | | 12 | Vista del funcionario (esquema) | 22 |
| 5 | La firma de un píxel | 22 | | 13 | Todo conectado | 14 |
| 6 | El cerebro (300 árboles, puntaje) | 26 | | 14 | **Del modelo a la app** (nueva: instalar, revisar, paquete) | 22 |
| 7 | De puntos a zonas | 20 | | 15 | Límites honestos | 12 |
| 8 | Antes y después | 18 | | 16 | Cierre | 8 |

Las capturas de la app (escena 11) y el esquema del funcionario (escena 12) usan **datos de demostración simulados**; lo mismo se rotula en pantalla. La escena 14 muestra una captura del visor con el diseño nuevo y una revisión de demostración (rotulada). Las 16 escenas se probaron renderizándolas en Chrome sin interfaz (sin errores de código; el 26-11-2026 se corrigieron solapes de texto en las escenas 6, 7, 11, 12 y 15). No se vio la animación en tiempo real, solo cuadros sueltos. Las capturas del visor de las escenas 8 y 9 son del diseño anterior del visor; si se quiere el diseño nuevo en todas, hay que volver a capturarlas (`herramientas/servidor_visor_demo.py`).
**Nombre y mensaje:** el proyecto se presenta como "proyecto" del equipo aurum80, sin nombre de marca y sin mencionar el hackathon (ver `HECHOS.md`).

## Cómo está hecha
- `js/motor.js`: motor de animación (línea de tiempo, controles, escenario de 1920x1080 escalado). Cada escena se dibuja como función del tiempo.
- `js/escenas/eNN_*.js`: una escena por archivo (ver `GUIA-ESCENAS.md`).
- `assets/real/` y `assets/datos/`: imágenes y datos REALES del modelo (bloque de 24,9 x 26,7 km, puntaje, píxeles de ejemplo, árboles reales); se regeneran con `herramientas/preparar_datos.py`.
- `assets/capturas/`: capturas del visor y de la app (datos de demostración).
- `HECHOS.md`: las únicas cifras y afirmaciones permitidas (lenguaje no punitivo, límites honestos).

## Aviso
La presentación muestra imágenes y zonas reales de un bloque analizado, sin coordenadas. Las zonas del modelo son "posible actividad minera, por verificar" (decisión D-002: datos sensibles); revisar antes de publicar el video.
