// Ayudante para controlar Chrome sin interfaz por el protocolo DevTools (Node 22+, sin instalar nada).
//   import { abrir } from './cdp.mjs';
//   const nav = await abrir({ puerto: 9401, ancho: 1920, alto: 1080 });
//   await nav.ir('http://127.0.0.1:8800/presentacion.html?ui=0');
//   await nav.js('window.__render(12)');           // evalua JavaScript en la pagina
//   await nav.foto('ruta/captura.png');             // captura de pantalla (PNG o .jpg)
//   await nav.cerrar();
// IMPORTANTE: usa un puerto de depuracion propio y cierra SOLO tu Chrome (cerrar()); no mates otros Chrome.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
export const dormir = ms => new Promise(r => setTimeout(r, ms));

export async function abrir({ puerto = 9401, ancho = 1920, alto = 1080, movil = false, extra = [] } = {}) {
  const dir = mkdtempSync(join(tmpdir(), 'cdp-'));
  const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${puerto}`, `--user-data-dir=${dir}`, `--window-size=${ancho},${alto}`,
    '--no-first-run', '--hide-scrollbars', '--force-device-scale-factor=1', '--autoplay-policy=no-user-gesture-required', ...extra, 'about:blank'], { stdio: 'ignore' });
  let ws;
  for (let i = 0; i < 60 && !ws; i++) {
    try { const l = await (await fetch(`http://127.0.0.1:${puerto}/json`)).json(); const p = l.find(x => x.type === 'page'); if (p) ws = new WebSocket(p.webSocketDebuggerUrl); } catch {}
    await dormir(250);
  }
  if (!ws) throw new Error('No se pudo conectar con Chrome');
  if (ws.readyState !== 1) await new Promise(r => ws.addEventListener('open', r));   // OJO: comprobar readyState antes de esperar 'open'
  let n = 0; const espera = new Map(); const errores = [];
  ws.addEventListener('message', m => {
    const d = JSON.parse(m.data);
    if (d.id && espera.has(d.id)) { espera.get(d.id)(d); espera.delete(d.id); }
    if (d.method === 'Runtime.exceptionThrown') errores.push('EXC: ' + (d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text));
    if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') errores.push('error: ' + d.params.args.map(a => a.value ?? a.description).join(' '));
  });
  const cmd = (method, params = {}) => new Promise(r => { const id = ++n; espera.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
  await cmd('Runtime.enable'); await cmd('Page.enable');
  if (movil) { await cmd('Emulation.setDeviceMetricsOverride', { width: ancho, height: alto, deviceScaleFactor: 2, mobile: true }); await cmd('Emulation.setTouchEmulationEnabled', { enabled: true }); }
  else await cmd('Emulation.setDeviceMetricsOverride', { width: ancho, height: alto, deviceScaleFactor: 1, mobile: false });
  return {
    errores, cmd,
    async ir(url, espera_ms = 1500) { await cmd('Page.navigate', { url }); await dormir(espera_ms); },
    async js(expr) { const r = await cmd('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails)); return r.result.result.value; },
    async foto(ruta, calidad = 90) { const jpg = /\.jpe?g$/i.test(ruta); const r = await cmd('Page.captureScreenshot', jpg ? { format: 'jpeg', quality: calidad } : { format: 'png' }); writeFileSync(ruta, Buffer.from(r.result.data, 'base64')); return ruta; },
    async cerrar() { try { ws.close(); } catch {} chrome.kill(); },
  };
}
