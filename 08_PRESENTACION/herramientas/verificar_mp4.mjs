// Comprueba que un MP4 se reproduce en Chrome: duracion, tamano, y guarda una captura de un instante.
//   node herramientas/verificar_mp4.mjs <archivo.mp4> [segundo=2] [captura.jpg]
import { abrir, dormir } from './cdp.mjs';
const [archivo, seg = '2', captura = 'verif_mp4.jpg'] = process.argv.slice(2);
const nav = await abrir({ puerto: 9477, ancho: 1280, alto: 720 });
await nav.ir('file:///' + archivo.split('\\').join('/'), 1500);
const v = await nav.js(`(async () => { const v = document.querySelector('video'); await new Promise(r => v.readyState >= 2 ? r() : v.addEventListener('loadeddata', r, {once: true})); v.pause(); v.currentTime = ${+seg}; await new Promise(r => v.addEventListener('seeked', r, {once: true})); return JSON.stringify({dur: v.duration, w: v.videoWidth, h: v.videoHeight, t: v.currentTime, err: v.error && v.error.message}); })()`);
console.log(v);
await dormir(500); await nav.foto(captura, 85);
await nav.cerrar(); process.exit(0);
