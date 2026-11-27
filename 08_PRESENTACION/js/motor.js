/* ==========================================================================
   Motor de la presentacion animada.
   - Escenario fijo de 1920 x 1080 que se escala a la ventana.
   - Una linea de tiempo global (en segundos). Cada escena ocupa un tramo y se dibuja como una FUNCION DEL TIEMPO:
     actualizar(t) pone todo en su lugar para ese instante (sin animaciones CSS). Asi se puede pausar, saltar, y
     grabar cuadro a cuadro (window.__render(t)).
   - Cada escena se registra con Pres.escena({ id, titulo, dur, recursos, subs, montar(raiz, H) -> actualizar(t) }).
   Controles: espacio pausa, flechas cambian de escena, F pantalla completa, C subtitulos, R reiniciar, clic en la barra salta.
   Parametros de la direccion: ?auto=1 (empieza solo)  ?t=45 (empieza en el segundo 45)  ?ui=0 (sin barra ni ayuda)  ?cap=0 (sin subtitulos)
   ========================================================================== */
(() => {
  'use strict';
  const Q = new URLSearchParams(location.search);
  const AN = 1920, AL = 1080, FADE = 0.45;
  const P = window.Pres = { escenas: [], t: 0, reproduciendo: false, dur: 0, rec: {}, listo: false };

  // ------------------------------------------------------------------ ayudantes para las escenas
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, p) => a + (b - a) * p;
  const seg = (t, a, b) => (b === a ? (t >= b ? 1 : 0) : clamp((t - a) / (b - a)));      // progreso 0..1 de t entre a y b
  const E = {                                                                                // curvas de suavizado: p (0..1) -> 0..1
    lineal: p => p, in2: p => p * p, in3: p => p * p * p, out2: p => 1 - (1 - p) * (1 - p), out3: p => 1 - Math.pow(1 - p, 3),
    out4: p => 1 - Math.pow(1 - p, 4), out5: p => 1 - Math.pow(1 - p, 5),
    io2: p => (p < .5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2), io3: p => (p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    io4: p => (p < .5 ? 8 * p * p * p * p : 1 - Math.pow(-2 * p + 2, 4) / 2),
    outExpo: p => (p >= 1 ? 1 : 1 - Math.pow(2, -10 * p)),
    outBack: p => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); },
    outElastic: p => (p === 0 || p === 1 ? p : Math.pow(2, -10 * p) * Math.sin((p * 10 - 0.75) * (2 * Math.PI / 3)) + 1),
    spring: p => 1 - Math.exp(-6 * p) * Math.cos(10 * p),                                    // resorte amortiguado
  };
  // Combina progreso y curva: an(t, a, b, E.out3)
  const an = (t, a, b, f) => (f || E.io3)(seg(t, a, b));
  const mezclaN = (a, b, p) => a.map((v, i) => lerp(v, b[i], p));
  const hex = h => { h = h.replace('#', ''); if (h.length === 3) h = h.split('').map(c => c + c).join(''); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)); };
  const color = (a, b, p) => { const m = mezclaN(hex(a), hex(b), p).map(Math.round); return `rgb(${m[0]},${m[1]},${m[2]})`; };
  const rng = (semilla = 1) => { let s = semilla >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };

  const NS = 'http://www.w3.org/2000/svg';
  function el(tag, clase, html, padre) {                      // crea un elemento HTML
    const e = document.createElement(tag);
    if (clase) e.className = clase;
    if (html != null) e.innerHTML = html;
    if (padre) padre.appendChild(e);
    return e;
  }
  function svg(tag, atributos, padre) {                       // crea un elemento SVG (tag 'svg' o cualquier forma)
    const e = document.createElementNS(NS, tag);
    for (const k in (atributos || {})) e.setAttribute(k, atributos[k]);
    if (padre) padre.appendChild(e);
    return e;
  }
  // Pone transformacion, opacidad y filtros de un elemento. x,y (px), s (escala) o sx,sy, r (grados), o (opacidad), blur (px), br (brillo), sat.
  function pon(e, o) {
    const s = e.style;
    if ('o' in o) s.opacity = o.o;
    const tr = [];
    if ('x' in o || 'y' in o || 'z' in o) tr.push(`translate3d(${o.x || 0}px,${o.y || 0}px,${o.z || 0}px)`);
    if ('r' in o) tr.push(`rotate(${o.r}deg)`);
    if ('s' in o) tr.push(`scale(${o.s})`);
    if ('sx' in o || 'sy' in o) tr.push(`scale(${'sx' in o ? o.sx : 1},${'sy' in o ? o.sy : 1})`);
    if (tr.length) s.transform = tr.join(' ');
    if ('blur' in o || 'br' in o || 'sat' in o) {
      const f = [];
      if (o.blur > 0.05) f.push(`blur(${o.blur}px)`);
      if ('br' in o && o.br !== 1) f.push(`brightness(${o.br})`);
      if ('sat' in o && o.sat !== 1) f.push(`saturate(${o.sat})`);
      s.filter = f.join(' ') || 'none';
    }
    if ('origen' in o) s.transformOrigin = o.origen;
    return e;
  }
  const tipo = (e, texto, p) => { e.textContent = texto.slice(0, Math.round(texto.length * clamp(p))); };    // maquina de escribir
  const num = (e, valor, p, dec = 0, sufijo = '') => { e.textContent = (valor * clamp(p)).toLocaleString('es', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + sufijo; };
  const trazo = (path, p) => {                                // dibuja una linea SVG poco a poco (0..1)
    const L = path._L || (path._L = path.getTotalLength());
    path.style.strokeDasharray = L; path.style.strokeDashoffset = L * (1 - clamp(p));
  };
  const img = (src, clase, padre) => { const i = new Image(); i.src = src; i.draggable = false; if (clase) i.className = clase; if (padre) padre.appendChild(i); return i; };
  const rec = url => P.rec[url];                              // dato o imagen ya cargados de los 'recursos' de la escena
  // Puntero de mouse falso para escenas de demostracion de pantallas: pon(p, {x, y}) lo mueve; H.clic(ondaEl, p) hace un destello
  function puntero(padre) {
    const e = el('div', 'puntero', null, padre);
    e.style.cssText = 'position:absolute;left:0;top:0;width:48px;height:48px;z-index:40;pointer-events:none;filter:drop-shadow(0 6px 10px rgba(0,0,0,.5))';
    e.innerHTML = '<svg viewBox="0 0 24 24" width="48" height="48"><path d="M4 2l15 9-6.5 1.6L9 19z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>';
    return e;
  }
  function onda(padre, color_ = 'rgba(255,255,255,.7)') {      // anillo de clic: pon(o, {x,y}) y luego ondaPaso(o, p)
    const e = el('div', null, null, padre);
    e.style.cssText = `position:absolute;left:-40px;top:-40px;width:80px;height:80px;border-radius:50%;border:4px solid ${color_};opacity:0;pointer-events:none;z-index:39`;
    return e;
  }
  const ondaPaso = (e, x, y, p) => { pon(e, { x, y, s: lerp(.3, 2.2, E.out3(p)), o: p <= 0 || p >= 1 ? 0 : 1 - p }); };
  const H = { clamp, lerp, seg, E, an, mezclaN, hex, color, rng, el, svg, pon, tipo, num, trazo, img, rec, puntero, onda, ondaPaso, AN, AL, P };

  // ------------------------------------------------------------------ registro de escenas
  P.escena = def => { P.escenas.push(def); };

  // ------------------------------------------------------------------ montaje y dibujo
  let escenario, subt, subtSpan, barra, barraI, ayuda, inicio;
  function calcular() {
    let t = 0;
    P.escenas.forEach(e => { e.t0 = t; e.t1 = t + e.dur; t += e.dur; });
    P.dur = t;
  }
  function montar(e) {
    e.el = el('section', 'escena', null, escenario); e.el.id = 'esc-' + e.id;
    const r = el('div', 'capa', null, e.el);
    e.act = () => {}; e.montada = true;                       // si montar falla, la escena queda vacia pero la presentacion sigue
    try {
      const f = e.montar(r, H);
      e.act = typeof f === 'function' ? f : (f && f.actualizar) || (() => {});
    } catch (err) { console.error('[Pres] Error al montar la escena', e.id, err); }
  }
  function render(t) {
    P.t = clamp(t, 0, P.dur);
    for (const e of P.escenas) {
      const tl = P.t - e.t0, viva = tl >= -1e-6 && tl <= e.dur + 1e-6 && !(tl >= e.dur && e !== P.escenas[P.escenas.length - 1]);
      if (viva) {
        if (!e.montada) montar(e);
        e.el.classList.add('activa');
        const tt = clamp(tl, 0, e.dur);
        const o = Math.min(E.out3(seg(tt, 0, FADE)), 1 - E.in2(seg(tt, e.dur - FADE, e.dur)));
        e.el.style.opacity = e.sinFundido ? 1 : o;
        e.el.style.transform = e.sinFundido ? 'none' : `scale(${lerp(0.992, 1, E.out3(seg(tt, 0, FADE * 1.6)))})`;
        try { e.act(tt); } catch (err) { if (!e._err) { e._err = true; console.error('[Pres] Error al dibujar la escena', e.id, 'en t =', tt.toFixed(2), err); } }
        pintarSubtitulo(e, tt);
      } else if (e.montada) e.el.classList.remove('activa');
    }
    if (barraI) barraI.style.width = (100 * P.t / P.dur) + '%';
  }
  function pintarSubtitulo(e, tt) {
    if (!subt || Q.get('cap') === '0') { if (subt) subt.style.display = 'none'; return; }
    const s = (e.subs || []).find(x => tt >= x[0] && tt < x[1]);
    if (s) { if (subtSpan.textContent !== s[2]) subtSpan.textContent = s[2]; subtSpan.classList.add('v'); } else subtSpan.classList.remove('v');
  }
  function ajustar() {
    const k = Math.min(innerWidth / AN, innerHeight / AL);
    escenario.style.transform = `translate(-50%,-50%) scale(${k})`;
  }
  function ir(t) { render(t); }
  function irEscena(i) { i = clamp(i, 0, P.escenas.length - 1); P.t0reloj = null; ir(P.escenas[i].t0 + 0.001); }
  function escenaActual() { return Math.max(0, P.escenas.findIndex(e => P.t >= e.t0 && P.t < e.t1)); }
  function alternar() { P.reproduciendo = !P.reproduciendo; if (P.reproduciendo && P.t >= P.dur - 0.05) ir(0); P.ultimo = performance.now(); mostrarAyuda(); }
  function mostrarAyuda() { if (!ayuda) return; ayuda.classList.add('v'); clearTimeout(P._ay); P._ay = setTimeout(() => ayuda.classList.remove('v'), 2200); ayuda.textContent = P.reproduciendo ? 'REPRODUCIENDO' : 'PAUSA'; }

  function bucle(ahora) {
    if (P.reproduciendo) {
      const dt = Math.min(0.1, (ahora - P.ultimo) / 1000); P.ultimo = ahora;
      if (P.t + dt >= P.dur) { render(P.dur); P.reproduciendo = false; } else render(P.t + dt);
    } else P.ultimo = ahora;
    requestAnimationFrame(bucle);
  }

  async function precargar() {
    const urls = [...new Set(P.escenas.flatMap(e => e.recursos || []))];
    let hechos = 0;
    await Promise.all(urls.map(async u => {
      try {
        if (/\.json$/i.test(u)) P.rec[u] = await (await fetch(u)).json();
        else { const i = new Image(); i.src = u; await i.decode(); P.rec[u] = i; }
      } catch (err) { console.warn('No se pudo cargar', u, err); }
      hechos++;
    }));
    await Promise.all(['800 100px Montserrat', '400 40px Roboto', '700 40px "Roboto Condensed"'].map(f => document.fonts.load(f).catch(() => {})));
    await document.fonts.ready;
  }

  async function iniciar() {
    escenario = document.getElementById('escenario');
    subt = document.getElementById('subtitulo'); subtSpan = subt.querySelector('span');
    barra = document.getElementById('barra'); barraI = barra.querySelector('i'); ayuda = document.getElementById('ayuda'); inicio = document.getElementById('inicio');
    if (Q.get('ui') === '0') document.body.classList.add('sinui');
    calcular(); ajustar(); addEventListener('resize', ajustar);
    P.escenas.forEach(e => { const b = document.createElement('b'); b.style.left = (100 * e.t0 / P.dur) + '%'; if (e.t0 > 0) barra.appendChild(b); });
    await precargar();
    P.listo = true; window.__listo = true;
    const t0 = parseFloat(Q.get('t') || '0') || 0;
    render(t0);
    const auto = Q.get('auto') === '1';
    if (auto) { inicio.style.display = 'none'; P.reproduciendo = true; P.ultimo = performance.now(); }
    inicio.onclick = () => { inicio.style.display = 'none'; P.reproduciendo = true; P.ultimo = performance.now(); mostrarAyuda(); document.documentElement.requestFullscreen && Q.get('fs') !== '0' && document.documentElement.requestFullscreen().catch(() => {}); };
    barra.onclick = ev => { const r = barra.getBoundingClientRect(); ir(P.dur * (ev.clientX - r.left) / r.width); };
    addEventListener('keydown', ev => {
      const k = ev.key;
      if (k === ' ') { ev.preventDefault(); inicio.style.display = 'none'; alternar(); }
      else if (k === 'ArrowRight') irEscena(escenaActual() + 1);
      else if (k === 'ArrowLeft') { const i = escenaActual(); irEscena(P.t - P.escenas[i].t0 > 1.5 ? i : i - 1); }
      else if (k === 'Home') ir(0); else if (k === 'End') ir(P.dur - 0.01);
      else if (k === 'f' || k === 'F') { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen(); }
      else if (k === 'c' || k === 'C') { Q.set('cap', Q.get('cap') === '0' ? '1' : '0'); if (subt) subt.style.display = Q.get('cap') === '0' ? 'none' : ''; }
      else if (k === 'r' || k === 'R') { ir(0); }
      else if (k === '.') { P.reproduciendo = false; ir(P.t + 1 / 30); } else if (k === ',') { P.reproduciendo = false; ir(P.t - 1 / 30); }
      else if (/^[1-9]$/.test(k)) irEscena(parseInt(k, 10) - 1);
    });
    requestAnimationFrame(bucle);
  }
  window.__render = t => { P.reproduciendo = false; render(t); return P.t; };
  window.__info = () => ({ dur: P.dur, escenas: P.escenas.map(e => ({ id: e.id, titulo: e.titulo, t0: e.t0, dur: e.dur })) });
  addEventListener('DOMContentLoaded', () => setTimeout(iniciar, 0));
})();
