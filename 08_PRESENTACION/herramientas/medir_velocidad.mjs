// Mide cuanto tarda capturar cuadros de la presentacion (para decidir como grabar el video).
import { abrir, dormir } from './cdp.mjs';
const nav = await abrir({ puerto: 9455, ancho: 1920, alto: 1080 });
await nav.ir('http://127.0.0.1:8800/presentacion.html?ui=0&auto=0&cap=1', 800);
for (let i = 0; i < 80 && !(await nav.js('window.__listo === true')); i++) await dormir(250);
for (const [calidad, formato] of [[85, 'jpeg'], [92, 'jpeg'], [0, 'png']]) {
  const n = 20; const t0 = performance.now(); let bytes = 0;
  for (let k = 0; k < n; k++) {
    await nav.js(`window.__render(${2 + k / 30})`);
    const r = await nav.cmd('Page.captureScreenshot', formato === 'jpeg' ? { format: 'jpeg', quality: calidad } : { format: 'png' });
    bytes += r.result.data.length * 0.75;
  }
  console.log(formato, calidad, ((performance.now() - t0) / n).toFixed(0), 'ms/cuadro;', (bytes / n / 1024).toFixed(0), 'KB/cuadro');
}
await nav.cerrar(); process.exit(0);
