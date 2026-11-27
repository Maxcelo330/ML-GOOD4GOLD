# Guia para escribir una escena

Una escena es un archivo `js/escenas/eNN_nombre.js` que llama a `Pres.escena({...})`. **Lee primero** `js/motor.js` (API), `css/estilo.css` (clases y colores) y `js/escenas/e01_apertura.js` (escena de referencia: copia su estilo y su nivel).

## Contrato
```js
Pres.escena({
  id: 'satelite', titulo: 'Como ve el satelite', dur: 22,           // segundos; el id debe ser el del archivo (ver presentacion.html)
  recursos: ['assets/datos/pixeles_ejemplo.json', 'assets/real/bloque_natural.jpg'],   // se precargan; H.rec(url) los devuelve (JSON ya parseado o <img>)
  subs: [[0.5, 5, 'Frase de narracion.'], [5.5, 10, 'Otra frase.']],     // subtitulos [t0, t1, texto] en segundos LOCALES de la escena
  montar(raiz, H) {                                                  // se llama UNA vez: crea el DOM dentro de `raiz` (1920 x 1080, position absolute)
    ... crear elementos ...
    return t => { ... };                                             // actualizar(t): t = segundos desde el inicio de la escena (0..dur)
  },
});
```
- **actualizar(t) debe ser una funcion pura del tiempo**: pone TODO en el estado que corresponde a t, sin acumular estado ni usar setTimeout/CSS transitions/animaciones CSS (se pausa, salta y se graba cuadro a cuadro). Si necesitas aleatoriedad, usa `H.rng(semilla)` creado en `montar`.
- El motor hace un fundido de entrada y salida de 0,45 s alrededor de cada escena (no lo hagas tu), asi que en t=0 y t=dur todo puede estar "en reposo" y la escena aparecera/desaparecera suave. Cuida que en los ultimos 0,5 s no cambie nada brusco.
- Ayudantes en `H`: `an(t, a, b, curva)` (progreso suavizado entre a y b), `seg`, `lerp`, `clamp`, curvas `H.E.out3/out4/outExpo/outBack/io3/spring...`, `pon(el, {x,y,s,sx,sy,r,o,blur,br,sat})`, `el(tag, clase, html, padre)`, `svg(tag, attrs, padre)`, `trazo(path, p)` (dibuja una linea SVG), `tipo(el, texto, p)` (maquina de escribir), `num(el, valor, p, dec, sufijo)` (contador), `color(a,b,p)`, `rng`, `img`, `puntero(padre)` + `onda`/`ondaPaso` (mouse falso y clic para demos de pantallas).
- Posiciona con `left/top/width/height` en px (coordenadas 1920 x 1080) y anima con `pon` (transform/opacity/filter) o con atributos SVG/canvas. Para canvas: crea el `<canvas>` en `montar` y dibuja de nuevo en cada `actualizar` (es barato a este tamano).
- Para ver imagenes/capturas en marcos: clases `.marco-web` (navegador) y `.marco-cel` (telefono; un `<img>` hijo). Las capturas van en `assets/capturas/` (PNG/JPG) y las listas en `recursos`.

## Calidad que se espera (estilo keynote de Apple)
- UNA idea por escena y por momento; titulares enormes (`.titulo`, 80-130 px) y mucho aire; texto de apoyo `.sub` (>= 34 px). Nada pequeno ni apretado: se va a ver en un video de 1080p y a veces en un proyector.
- Movimiento fluido y con intencion: entradas escalonadas (stagger de 0,08-0,15 s), curvas `out4/outExpo/io3`, deslices cortos (40-80 px) con desenfoque que se aclara, escalas suaves, camara lenta que se acerca (zoom/pan) sobre imagenes reales, numeros que cuentan, lineas que se dibujan. Evita rebotes exagerados y parpadeos.
- Que se ENTIENDA solo con mirar: cada concepto tecnico se muestra con un dibujo animado simple (un pixel que se mide, un arbol que decide, una zona que se forma), no con parrafos. Maximo ~10 palabras por frase en pantalla; la explicacion fina va en los subtitulos.
- Usa datos e imagenes REALES de `assets/` (ver HECHOS.md). Si dibujas algo ilustrativo, que sea fiel (por ejemplo, los umbrales y variables del arbol son los reales de `arbol_ejemplo.json`).
- Colores con significado: morado = el modelo y la plataforma; naranja Claude = todo lo que usa IA; oro = acento de identidad del equipo aurum80 (igual que la app); verde / amarillo / azul / rojo / hexagono violeta = el mapa de la plataforma (ver variables CSS en estilo.css). Fondo oscuro siempre.
- Espanol con tildes, SIN emojis, tono no punitivo (ver HECHOS.md). Nada de cifras que no esten en HECHOS.md. NUNCA muestres contrasenas, claves ni coordenadas exactas de zonas (D-002): desenfoca o recorta si una captura las trae.

## Como probar (obligatorio, varias veces)
1. Servidor estatico de la presentacion (ya esta corriendo en el puerto 8800; si no, `python -I -m http.server 8800 --directory 08_PRESENTACION` con el Python del entorno g4g-ml: `C:\Users\LENOVO LEGION 5PRO\anaconda3\envs\g4g-ml\python.exe`).
2. `node 08_PRESENTACION/herramientas/probar.mjs 8800 <id_escena> 1,4,8,12,18` guarda capturas 1920x1080 en el scratchpad `.../scratchpad/pres/<id>_<t>.jpg` y lista errores de consola. **Abre las capturas con Read y mirelas**: busca texto cortado o encima de otro, elementos fuera de cuadro, cuadros vacios, mal contraste, animaciones que "saltan". Prueba muchos instantes (incluye t=0, justo despues de cada hito y los ultimos 2 s) y corrige hasta que se vea de nivel profesional.
3. Para una prueba de fluidez: `window.__render(t)` en pasos de 1/30 s no debe lanzar errores ni mostrar saltos de posicion de mas de unos pocos pixeles entre cuadros consecutivos en los movimientos continuos.

## Reglas de trabajo
- Edita SOLO tus archivos de escena y agrega assets propios en `assets/capturas/` (con prefijo de tu escena). No cambies `motor.js`, `estilo.css` ni las escenas de otros; si necesitas una clase CSS nueva, ponla con estilos inline o en un `<style>` creado dentro de tu `montar` con selectores que empiecen por `#esc-<tu id>`.
- Los procesos que lances (servidores, Chrome) deben ser tuyos y detenerlos al final; usa puertos de depuracion propios; no mates procesos ajenos (hay otros agentes trabajando en paralelo).
- No hagas commit ni push. No instales paquetes.
