// Prueba una o varias escenas: abre la presentacion, salta a instantes dados y guarda capturas.
//   node herramientas/probar.mjs <puerto_http> <id_escena|all> [t1,t2,t3,...] [carpeta_salida]
// Los instantes son LOCALES a la escena (segundos desde su inicio). Si no se dan, usa 5 instantes repartidos.
// Necesita un servidor estatico de la carpeta 08_PRESENTACION:  python -I -m http.server 8800 --directory 08_PRESENTACION
import { abrir, dormir } from './cdp.mjs';
import { mkdirSync } from 'node:fs';

const [puertoHttp = '8800', cual = 'all', instantes = '', salida = 'C:/Users/LENOVO~1/AppData/Local/Temp/claude/8c437e0bf7e07007/8a3d991a-7078-49ef-bf97-211167829301/scratchpad/pres'] = process.argv.slice(2);
mkdirSync(salida, { recursive: true });
const nav = await abrir({ puerto: 9400 + Math.floor(Math.random() * 90), ancho: 1920, alto: 1080 });
await nav.ir(`http://127.0.0.1:${puertoHttp}/presentacion.html?ui=0&auto=0&cap=1`, 800);
for (let i = 0; i < 80 && !(await nav.js('window.__listo === true')); i++) await dormir(250);
const info = await nav.js('window.__info()');
console.log('duracion total', info.dur, 's;', info.escenas.length, 'escenas con contenido registrado');
const lista = cual === 'all' ? info.escenas : info.escenas.filter(e => e.id === cual || e.id.startsWith(cual));
for (const e of lista) {
  const ts = instantes ? instantes.split(',').map(Number) : [0.15, 0.3, 0.5, 0.7, 0.92].map(f => +(f * e.dur).toFixed(2));
  for (const tl of ts) {
    await nav.js(`window.__render(${e.t0 + tl})`);
    await dormir(350);                       // deja cargar imagenes y fuentes
    const f = `${salida}/${e.id}_${String(tl).replace('.', '_')}.jpg`;
    await nav.foto(f, 82); console.log('captura', f);
  }
}
console.log('ERRORES:', nav.errores.length ? nav.errores.join('\n') : 'ninguno');
await nav.cerrar(); process.exit(0);
