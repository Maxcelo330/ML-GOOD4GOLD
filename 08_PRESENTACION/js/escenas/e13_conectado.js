/* Escena 13 - Todo conectado (14 s).
   Diagrama animado (esquema, sin datos reales): celular -> backend (Google Apps Script + Hoja de Google) -> funcionario y otros celulares.
   Hechos de HECHOS.md: el mapa se actualiza solo cada 60 s; sin senal la denuncia queda "Sin enviar" y se envia sola; sin backend = modo demostracion.
   Todo es funcion pura de t. */
Pres.escena({
  id: 'conectado', titulo: 'Todo conectado', dur: 14,
  recursos: [],
  subs: [
    [0.5, 3.4, 'Con el backend, las denuncias van a una Hoja de Google.'],
    [3.8, 7.0, 'Y se ven en todos los dispositivos: el mapa se actualiza solo cada 60 segundos.'],
    [7.4, 10.4, 'Sin señal, la denuncia espera en el celular.'],
    [10.6, 12.4, 'Cuando vuelve la conexión, se envía sola.'],
    [12.5, 13.6, 'Sin backend: modo demostración.'],
  ],
  montar(raiz, H) {
    const { el, svg, pon, an, E, lerp, clamp } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const VER = '#2fb344', AMA = '#f5b700', ROJ = '#e03131', AZU = '#74c0fc', MORc = '#9775fa', ORO = '#e0a82a';

    const tit = A('titulo xs centro', 'Una denuncia, <span class="g-verde">todos los dispositivos</span>', raiz, { left: '0', right: '0', top: '60px', fontSize: '62px' });

    const ICON = {
      cel: c => `<rect x="14" y="3" width="20" height="42" rx="5" stroke="${c}"/><path d="M21 39h6" stroke="${c}"/><circle cx="24" cy="17" r="4" stroke="${c}"/>`,
      hoja: c => `<rect x="6" y="6" width="36" height="36" rx="5" stroke="${c}"/><path d="M6 17h36M6 28h36M20 6v36" stroke="${c}"/>`,
      lap: c => `<rect x="8" y="9" width="32" height="22" rx="3" stroke="${c}"/><path d="M3 38h42" stroke="${c}"/>`,
    };
    const ico = (n, c, s) => `<svg viewBox="0 0 48 48" width="${s}" height="${s}" fill="none" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" style="display:block">${ICON[n](c)}</svg>`;

    const NW = 270, NH = 270;
    const POS = { a: [270, 560], s: [960, 560], f: [1650, 400], b: [1650, 740] };
    const nodo = (k, icn, col, titulo, sub, w = NW) => {
      const [x, y] = POS[k];
      const c = A('tarjeta', null, raiz, { left: (x - w / 2) + 'px', top: (y - NH / 2) + 'px', width: w + 'px', height: NH + 'px', borderRadius: '30px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px', background: 'linear-gradient(180deg,#171722,#0f0f17)', borderWidth: '2px' });
      el('div', null, ico(icn, col, 96), c);
      el('div', null, titulo, c).style.cssText = 'font:800 34px var(--fuente-titulo);letter-spacing:-.02em;color:#fff;text-align:center';
      el('div', null, sub, c).style.cssText = 'font:400 24px/1.2 var(--fuente-texto);color:var(--suave);text-align:center;padding:0 14px';
      c._col = col; return c;
    };
    const nA = nodo('a', 'cel', VER, 'Ciudadano', 'denuncia desde el celular');
    const nS = nodo('s', 'hoja', ORO, 'Hoja de Google', 'Google Apps Script', 330);
    const nF = nodo('f', 'lap', MORc, 'Funcionario', 've las denuncias en la web');
    const nB = nodo('b', 'cel', AZU, 'Otro celular', 'el mapa se actualiza solo');

    const sv = svg('svg', { viewBox: '0 0 1920 1080', width: 1920, height: 1080 }, raiz); sv.style.cssText = 'position:absolute;left:0;top:0;overflow:visible;pointer-events:none';
    const enl = (a, b, ox0, ox1) => { const [x0, y0] = POS[a], [x1, y1] = POS[b]; return [x0 + ox0, y0, x1 + ox1, y1]; };
    const E1 = enl('a', 's', NW / 2 + 12, -(165 + 12)), E2 = enl('s', 'f', 165 + 12, -(NW / 2 + 12)), E3 = enl('s', 'b', 165 + 12, -(NW / 2 + 12));
    const linea = L => svg('line', { x1: L[0], y1: L[1], x2: L[2], y2: L[3], stroke: 'rgba(255,255,255,.2)', 'stroke-width': 5, 'stroke-dasharray': '4 14', 'stroke-linecap': 'round' }, sv);
    const l1 = linea(E1), l2 = linea(E2), l3 = linea(E3);
    const cruz = svg('g', {}, sv);
    const cx = (E1[0] + E1[2]) / 2, cy = (E1[1] + E1[3]) / 2;
    svg('circle', { cx, cy, r: 34, fill: ROJ, stroke: '#0a0a0f', 'stroke-width': 5 }, cruz);
    svg('path', { d: `M${cx - 13} ${cy - 13}L${cx + 13} ${cy + 13}M${cx + 13} ${cy - 13}L${cx - 13} ${cy + 13}`, stroke: '#fff', 'stroke-width': 7, 'stroke-linecap': 'round' }, cruz);
    const pk = col => { const c = svg('circle', { r: 17, fill: col }, sv); c.style.filter = `drop-shadow(0 0 14px ${col})`; c.style.opacity = 0; return c; };
    const p1 = pk(VER), p2 = pk(MORc), p3 = pk(AZU), p4 = pk(VER);
    const mover = (c, L, u) => { c.setAttribute('cx', lerp(L[0], L[2], u)); c.setAttribute('cy', lerp(L[1], L[3], u)); };

    // anillo de 60 s
    const ring = svg('circle', { cx: 960, cy: 560, r: 188, fill: 'none', stroke: ORO, 'stroke-width': 7, 'stroke-linecap': 'round', transform: 'rotate(-90 960 560)' }, sv);
    const t60 = A('', '↻ cada 60 s', raiz, { left: '810px', top: '730px', width: '300px', textAlign: 'center', font: '700 34px var(--fuente-num)', color: ORO });

    // chips de estado del celular
    const chipA = A('', 'Sin enviar', raiz, { left: (POS.a[0] - 90) + 'px', top: (POS.a[1] + NH / 2 + 24) + 'px', width: '180px', textAlign: 'center', padding: '8px 0', borderRadius: '999px', font: '700 28px var(--fuente-num)', background: 'rgba(245,183,0,.2)', color: AMA });
    const demo = A('pastilla', 'Sin backend: modo demostración, solo en el dispositivo', raiz, { left: '0', right: '0', margin: '0 auto', width: 'fit-content', top: '930px', fontSize: '30px', borderColor: 'rgba(224,168,42,.5)', background: 'rgba(224,168,42,.12)' });

    return t => {
      ent(tit, an(t, 0.1, 0.9, E.out4), 25, 10);
      [[nA, 0.5], [nS, 0.8], [nF, 1.1], [nB, 1.4]].forEach(([n, t0]) => ent(n, an(t, t0, t0 + 0.9, E.out4), 50, 14));
      [l1, l2, l3].forEach(l => { l.style.opacity = an(t, 1.2, 1.8); });

      // 1) denuncia: celular -> hoja
      const u1 = an(t, 1.6, 3.0, E.io2);
      mover(p1, E1, u1); p1.style.opacity = u1 > 0 && u1 < 1 ? 1 : 0;
      const guardado = an(t, 3.0, 3.4) * (1 - an(t, 4.0, 4.4));
      nS.style.borderColor = `rgba(224,168,42,${0.15 + 0.8 * guardado})`;
      // 2) hoja -> funcionario y otro celular
      const u2 = an(t, 4.2, 5.6, E.io2);
      mover(p2, E2, u2); mover(p3, E3, u2); p2.style.opacity = p3.style.opacity = u2 > 0 && u2 < 1 ? 1 : 0;
      nF.style.borderColor = `rgba(151,117,250,${0.15 + 0.8 * an(t, 5.5, 5.9) * (1 - an(t, 6.6, 7.0))})`;
      nB.style.borderColor = `rgba(116,192,252,${0.15 + 0.8 * an(t, 5.5, 5.9) * (1 - an(t, 6.6, 7.0))})`;
      // 3) reloj de 60 s
      const r = an(t, 5.6, 7.2, E.io2);
      H.trazo(ring, r); ring.style.opacity = an(t, 5.4, 5.8) * (1 - an(t, 7.2, 7.8));
      pon(t60, { o: an(t, 5.6, 6.2) * (1 - an(t, 7.2, 7.8)) });
      // 4) sin senal
      const off = an(t, 7.4, 7.9) * (1 - an(t, 10.2, 10.6));
      cruz.style.opacity = off; l1.style.stroke = off > 0.5 ? 'rgba(224,49,49,.6)' : 'rgba(255,255,255,.2)';
      const enviada = t >= 12.0;
      chipA.textContent = enviada ? 'Enviada' : 'Sin enviar';
      chipA.style.background = enviada ? 'rgba(47,179,68,.2)' : 'rgba(245,183,0,.2)';
      chipA.style.color = enviada ? VER : AMA;
      pon(chipA, { o: an(t, 7.6, 8.2) * (1 - an(t, 12.8, 13.2)) });
      // 5) vuelve la conexion
      const u4 = an(t, 10.6, 12.0, E.io2);
      mover(p4, E1, u4); p4.style.opacity = u4 > 0 && u4 < 1 ? 1 : 0;
      // nota
      const d = an(t, 12.4, 13.0, E.out4); pon(demo, { o: d, y: lerp(16, 0, d) });
    };
  },
});
