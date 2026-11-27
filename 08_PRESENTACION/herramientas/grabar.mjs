// Graba la presentacion a un video MP4 (H.264) cuadro a cuadro, sin instalar nada (Chrome + WebCodecs + empaquetador propio).
//   node herramientas/grabar.mjs <puerto_http> <salida.mp4> [fps=30] [t_inicio=0] [t_fin=duracion] [ancho=1920] [alto=1080] [bitrate_Mbps=12]
// Necesita el servidor estatico: python -I -m http.server 8800 --directory 08_PRESENTACION
// Como es determinista (la presentacion es una funcion del tiempo), el video sale perfecto aunque el computador sea lento; solo tarda mas.
import { abrir, dormir } from './cdp.mjs';
import { writeFileSync, appendFileSync } from 'node:fs';

const [puerto = '8800', salida = 'presentacion.mp4', fpsS = '30', t0S = '0', t1S = '', anchoS = '1920', altoS = '1080', mbps = '12'] = process.argv.slice(2);
const fps = +fpsS, ancho = +anchoS, alto = +altoS;
const pag = await abrir({ puerto: 9500 + Math.floor(Math.random() * 90), ancho, alto });            // la presentacion
const cod = await abrir({ puerto: 9600 + Math.floor(Math.random() * 90), ancho: 800, alto: 600 });   // el codificador
await pag.ir(`http://127.0.0.1:${puerto}/presentacion.html?ui=0&auto=0&cap=1`, 800);
for (let i = 0; i < 120 && !(await pag.js('window.__listo === true')); i++) await dormir(250);
await cod.ir(`http://127.0.0.1:${puerto}/herramientas/codificador.html`, 500);
const info = await pag.js('window.__info()');
const t0 = +t0S, t1 = t1S ? +t1S : info.dur;
const r0 = await cod.js(`Codificador.iniciar(${ancho}, ${alto}, ${fps}, ${Math.round(+mbps * 1e6)})`);
if (!r0.ok) throw new Error('Codificador: ' + r0.motivo);
// Calentamiento: pasa por todas las escenas para que carguen imagenes y fuentes antes de grabar
for (const e of info.escenas) { for (const f of [0.05, 0.5, 0.95]) { await pag.js(`window.__render(${e.t0 + f * e.dur})`); await dormir(120); } }
console.log(`Grabando ${t0}-${t1.toFixed(1)} s a ${fps} fps, ${ancho}x${alto} (${Math.round((t1 - t0) * fps)} cuadros)...`);
const total = Math.round((t1 - t0) * fps); const ini = Date.now();
for (let k = 0; k < total; k++) {
  const t = t0 + k / fps;
  await pag.js(`window.__render(${t.toFixed(4)}); new Promise(r => requestAnimationFrame(() => r(1)))`);
  const shot = await pag.cmd('Page.captureScreenshot', { format: 'jpeg', quality: 90 });
  const r = await cod.js(`Codificador.empujar(${JSON.stringify(shot.result.data)})`);
  if (!r.ok) throw new Error('Codificador: ' + r.motivo);
  if (k % 300 === 0) console.log(`  ${k}/${total}  (${(k / fps).toFixed(0)} s de video; ${Math.round((Date.now() - ini) / 1000)} s transcurridos)`);
}
const fin = await cod.js('Codificador.terminar()');
console.log('Codificado:', fin);
const TAM = 4_000_000; const partes = Math.ceil(fin.bytes / TAM);
writeFileSync(salida, Buffer.alloc(0));
for (let i = 0; i < partes; i++) appendFileSync(salida, Buffer.from(await cod.js(`Codificador.parte(${i}, ${TAM})`), 'base64'));
console.log('Guardado', salida, '-', (fin.bytes / 1e6).toFixed(1), 'MB; errores de la pagina:', pag.errores.length ? pag.errores.join(' | ') : 'ninguno');
await pag.cerrar(); await cod.cerrar(); process.exit(0);
