/* Escena 10 - El modelo aprende (22 s).
   Cuatro momentos: (1) el ciclo de 5 pasos, (2) la compuerta de seguridad (La Pampa), (3) cifras reales v1 -> v2, (4) la meta: depender menos de la IA.
   Todo es funcion pura de t. Las cifras salen de HECHOS.md y se rotulan como coincidencia con MapBiomas y revision por IA, no con el terreno. */
Pres.escena({
  id: 'aprende', titulo: 'El modelo aprende', dur: 22,
  recursos: [],
  subs: [
    [0.5, 3.8, 'El modelo propone zonas y una persona las revisa.'],
    [3.9, 7.2, 'Claude da una segunda opinión y cada revisión se vuelve una etiqueta.'],
    [7.9, 12.6, 'Un modelo nuevo solo se activa si no empeora en La Pampa.'],
    [13.2, 17.9, 'Mejoró frente a MapBiomas y la revisión por IA, no frente al terreno.'],
    [18.4, 21.6, 'La meta: depender cada vez menos de la IA.'],
  ],
  montar(raiz, H) {
    const { el, svg, pon, an, E, lerp, clamp } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const vis = (e, o) => { e.style.visibility = o <= 0.002 ? 'hidden' : 'visible'; };
    const fm = n => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    const MOR = '#7048e8', MORc = '#9775fa', NAR = '#d97757', NARc = '#f0a283', ORO = '#e0a82a', VER = '#2fb344', ROJ = '#e03131', AMA = '#f5b700';

    // ---------- iconos simples (48 x 48)
    const IC = {
      modelo: c => `<circle cx="24" cy="9" r="5" stroke="${c}"/><circle cx="10" cy="38" r="5" stroke="${c}"/><circle cx="38" cy="38" r="5" stroke="${c}"/><path stroke="${c}" d="M24 14v7M24 21L12.5 33M24 21l11.5 12"/>`,
      persona: c => `<circle cx="24" cy="15" r="8" stroke="${c}"/><path stroke="${c}" d="M8 43c0-9.5 7-15 16-15s16 5.500 16 15"/>`,
      claude: c => `<path fill="${c}" stroke="none" d="M24 3c1.800 12 7.500 18.500 21 21-13.500 2.500-19.200 9-21 21-1.800-12-7.500-18.500-21-21C16.500 21.500 22.200 15 24 3z"/>`,
      etiqueta: c => `<path stroke="${c}" d="M5 6h18l20 20-15 15L8 21z"/><circle cx="15" cy="16" r="2.800" fill="${c}" stroke="none"/>`,
      ciclo: c => `<path stroke="${c}" d="M39 20A16 16 0 0 0 11 14"/><path stroke="${c}" d="M9 5v10h10"/><path stroke="${c}" d="M9 28a16 16 0 0 0 28 6"/><path stroke="${c}" d="M39 43V33H29"/>`,
      mapa: c => `<path stroke="${c}" d="M5 11l12-5 14 5 12-5v31l-12 5-14-5-12 5z"/><path stroke="${c}" d="M17 6v31M31 11v31"/>`,
      ok: c => `<path stroke="${c}" d="M8 25l11 11L40 12"/>`,
    };
    const ico = (n, c, s) => `<svg viewBox="0 0 48 48" width="${s}" height="${s}" fill="none" stroke-width="3.200" stroke-linecap="round" stroke-linejoin="round" style="display:block">${IC[n](c)}</svg>`;

    // =====================================================================================
    // 1) EL CICLO
    // =====================================================================================
    const ring = A('capa', null, raiz);
    const tit1 = A('titulo xs centro', 'Un ciclo que <span class="g-morado">mejora solo</span>.', ring, { left: '0', right: '0', top: '70px', fontSize: '66px' });
    const CX = 960, CY = 580, RX = 560, RY = 240;
    const ang = [-90, -18, 54, 126, 198];
    const pt = th => [CX + RX * Math.cos(th * Math.PI / 180), CY + RY * Math.sin(th * Math.PI / 180)];
    const sv = svg('svg', { viewBox: '0 0 1920 1080', width: 1920, height: 1080 }, ring); sv.style.cssText = 'position:absolute;left:0;top:0;overflow:visible';
    const defs = svg('defs', {}, sv);
    const gr = svg('linearGradient', { id: 'ap-grad', gradientUnits: 'userSpaceOnUse', x1: 400, y1: 0, x2: 1520, y2: 0 }, defs);
    svg('stop', { offset: '0', 'stop-color': MORc }, gr); svg('stop', { offset: '.55', 'stop-color': MOR }, gr); svg('stop', { offset: '1', 'stop-color': NAR }, gr);
    const elip = svg('ellipse', { cx: CX, cy: CY, rx: RX, ry: RY, fill: 'none', stroke: 'rgba(255,255,255,.14)', 'stroke-width': 3, 'stroke-dasharray': '3 12', 'stroke-linecap': 'round' }, sv);
    const prog = svg('path', { d: '', fill: 'none', stroke: 'url(#ap-grad)', 'stroke-width': 6, 'stroke-linecap': 'round' }, sv);
    // chevrones de direccion en medio de cada tramo
    const chev = ang.map((a, i) => { const m = a + 36, [x, y] = pt(m); const tg = Math.atan2(RY * Math.cos(m * Math.PI / 180), -RX * Math.sin(m * Math.PI / 180)) * 180 / Math.PI;
      return svg('path', { d: 'M-9 -11L9 0L-9 11', fill: 'none', stroke: 'rgba(255,255,255,.55)', 'stroke-width': 4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', transform: `translate(${x} ${y}) rotate(${tg})` }, sv); });
    const trail = Array.from({ length: 7 }, (_, k) => svg('circle', { r: 13 - k * 1.500, fill: '#fff' }, sv));
    trail.forEach(c => { c.style.filter = 'drop-shadow(0 0 10px rgba(255,255,255,.9))'; });

    // nodos
    const ND = [
      { tag: 'MODELO', main: 'Propone zonas', sub: null, ic: 'modelo', col: MORc, bd: MOR },
      { tag: 'PERSONA', main: 'Revisa', sub: null, ic: 'persona', col: '#e8e8ee', bd: '#c9c9d4' },
      { tag: 'CLAUDE · IA', main: 'Segunda opinión', sub: null, ic: 'claude', col: NARc, bd: NAR },
      { tag: 'ETIQUETAS NUEVAS', main: 'Persona ×3<br>Claude ×1–2', sub: null, ic: 'etiqueta', col: ORO, bd: ORO },
      { tag: 'MODELO', main: 'Reentrena', sub: null, ic: 'ciclo', col: MORc, bd: MOR },
    ];
    const NW = 460, NH = 128;
    const nodos = ND.map((d, i) => {
      const [x, y] = pt(ang[i]);
      const n = A('tarjeta', null, ring, { left: (x - NW / 2) + 'px', top: (y - NH / 2) + 'px', width: NW + 'px', height: NH + 'px', background: 'linear-gradient(180deg,#171722,#0f0f17)', display: 'flex', alignItems: 'center', gap: '20px', padding: '0 24px', borderRadius: '26px', borderWidth: '2px' });
      const ib = el('div', null, ico(d.ic, d.col, 48), n); Object.assign(ib.style, { flex: 'none', width: '72px', height: '72px', borderRadius: '20px', display: 'grid', placeItems: 'center', background: 'rgba(255,255,255,.06)' });
      const tx = el('div', null, `<div style="font:600 22px/1 var(--fuente-num);letter-spacing:.2em;color:${d.col}">${d.tag}</div><div style="font:700 ${i === 3 ? 30 : 33}px/1.12 var(--fuente-titulo);letter-spacing:-.02em;margin-top:9px;color:#fff">${d.main}</div>`, n);
      n._d = d; return n;
    });
    // chip de version sobre el nodo 0 (v1 -> v2)
    const chipv = (txt, col) => A('', txt, ring, { left: (pt(ang[0])[0] + NW / 2 - 96) + 'px', top: (pt(ang[0])[1] - NH / 2 - 26) + 'px', width: '78px', height: '46px', borderRadius: '23px', background: col, color: '#fff', font: '700 28px/46px var(--fuente-num)', textAlign: 'center', boxShadow: '0 8px 24px rgba(0,0,0,.4)' });
    const chip1 = chipv('v1', '#4b4b57'), chip2 = chipv('v2', MOR);

    // indicador central: etiquetas nuevas n / 10
    const cen = A('', null, ring, { left: (CX - 125) + 'px', top: (CY - 125) + 'px', width: '250px', height: '250px' });
    const csv = svg('svg', { viewBox: '0 0 250 250', width: 250, height: 250 }, cen); csv.style.overflow = 'visible';
    svg('circle', { cx: 125, cy: 125, r: 112, fill: 'rgba(255,255,255,.03)', stroke: 'rgba(255,255,255,.1)', 'stroke-width': 12 }, csv);
    const carc = svg('circle', { cx: 125, cy: 125, r: 112, fill: 'none', stroke: ORO, 'stroke-width': 12, 'stroke-linecap': 'round', pathLength: 100, transform: 'rotate(-90 125 125)' }, csv);
    carc.setAttribute('stroke-dasharray', '100');
    const cnum = A('num centro', '0', cen, { left: '0', right: '0', top: '76px', fontSize: '88px', lineHeight: '1', color: '#fff' });
    const ctop = A('centro', 'ETIQUETAS', cen, { left: '0', right: '0', top: '50px', font: '600 22px/1 var(--fuente-num)', letterSpacing: '.22em', color: 'var(--suave)' });
    const ccap = A('centro', 'de 10', cen, { left: '0', right: '0', top: '168px', font: '500 30px/1.2 var(--fuente-texto)', color: 'var(--suave)' });
    const cfin = A('centro', 'Reentrena', cen, { left: '0', right: '0', top: '168px', font: '700 30px/1.2 var(--fuente-texto)', color: MORc });

    // =====================================================================================
    // 2) LA COMPUERTA
    // =====================================================================================
    const gate = A('capa', null, raiz);
    const tit2 = A('titulo xs centro', 'Solo se activa <span class="g-verde">si no empeora</span>.', gate, { left: '0', right: '0', top: '70px', fontSize: '66px' });
    // tarjeta izquierda: modelo nuevo
    const cL = A('tarjeta morada', `<div style="display:grid;place-items:center;height:76px">${ico('modelo', MORc, 64)}</div><div style="font:700 36px/1.1 var(--fuente-titulo);margin-top:14px">Modelo nuevo</div><div style="font-size:26px;color:var(--suave);margin-top:8px">recién reentrenado</div>`, gate, { left: '100px', top: '420px', width: '340px', height: '230px', padding: '26px 20px', textAlign: 'center' });
    // camara de prueba
    const cam = A('tarjeta', null, gate, { left: '600px', top: '290px', width: '700px', height: '430px', padding: '30px 40px', borderWidth: '2px' });
    A('', `<div style="display:flex;align-items:center;gap:20px"><div style="flex:none">${ico('mapa', '#e8e8ee', 52)}</div><div><div style="font:700 40px/1.1 var(--fuente-titulo);letter-spacing:-.02em">Prueba en La Pampa</div><div style="font-size:28px;color:var(--suave);margin-top:6px">un bloque que nunca entrena</div></div></div>`, cam, { left: '40px', top: '28px', right: '30px' });
    const RTXT = ['F1 no baja más de 0,03', 'Cobertura no baja más de 5 puntos', 'Coincide igual en zonas que no vio'];
    const filas2 = RTXT.map((tx, i) => {
      const f = A('', null, cam, { left: '40px', top: (150 + i * 86) + 'px', right: '30px', height: '70px', display: 'flex', alignItems: 'center', gap: '22px' });
      const c = el('div', null, null, f); Object.assign(c.style, { position: 'relative', flex: 'none', width: '50px', height: '50px', borderRadius: '50%', border: '3px solid rgba(255,255,255,.28)' });
      const s = svg('svg', { viewBox: '0 0 50 50', width: 50, height: 50 }, c); s.style.cssText = 'position:absolute;left:-3px;top:-3px;overflow:visible';
      const bg = svg('circle', { cx: 25, cy: 25, r: 26, fill: VER, opacity: 0 }, s);
      const ok = svg('path', { d: 'M13 26l8 8 16-17', fill: 'none', stroke: '#fff', 'stroke-width': 5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', pathLength: 1 }, s); ok.setAttribute('stroke-dasharray', '1');
      const no = svg('path', { d: 'M16 16l18 18M34 16L16 34', fill: 'none', stroke: '#fff', 'stroke-width': 5, 'stroke-linecap': 'round', pathLength: 1 }, s); no.setAttribute('stroke-dasharray', '1');
      const t = el('div', null, tx, f); t.style.cssText = 'font:500 31px/1.15 var(--fuente-texto);color:#f1f1f5';
      return { c, bg, ok, no, t };
    });
    // puerta
    const puerta = A('', null, gate, { left: '1330px', top: '330px', width: '90px', height: '350px' });
    A('', null, puerta, { left: '0', top: '0', width: '90px', height: '26px', borderRadius: '10px', background: '#2a2a33', boxShadow: '0 0 0 1px rgba(255,255,255,.14)', zIndex: 3 });
    const lampa = A('', null, puerta, { left: '33px', top: '5px', width: '16px', height: '16px', borderRadius: '50%', zIndex: 4 });
    A('', null, puerta, { left: '0', bottom: '0', width: '90px', height: '26px', borderRadius: '10px', background: '#2a2a33', boxShadow: '0 0 0 1px rgba(255,255,255,.14)', zIndex: 3 });
    const marcoP = A('', null, puerta, { left: '24px', top: '26px', width: '42px', height: '298px', overflow: 'hidden' });
    const losa = A('', null, marcoP, { left: '0', top: '0', width: '42px', height: '298px', borderRadius: '6px', background: `repeating-linear-gradient(45deg, ${AMA} 0 18px, #16161d 18px 36px)`, boxShadow: '0 0 30px rgba(245,183,0,.25)' });
    // tarjeta derecha: modelo activo
    const cR = A('tarjeta', `<div style="display:grid;place-items:center;height:76px">${ico('modelo', '#b2f2bb', 64)}</div><div style="font:700 36px/1.1 var(--fuente-titulo);margin-top:14px">Modelo activo</div><div style="font-size:26px;color:var(--suave);margin-top:8px">el que se usa</div>`, gate, { left: '1480px', top: '420px', width: '340px', height: '230px', padding: '26px 20px', textAlign: 'center', borderWidth: '2px' });
    const checkR = A('', ico('ok', '#fff', 30), gate, { left: '1782px', top: '398px', width: '52px', height: '52px', borderRadius: '50%', background: VER, display: 'grid', placeItems: 'center', boxShadow: '0 8px 24px rgba(47,179,68,.5)' });
    // pastillas de modelo viajando
    const pill = (col, txt) => A('', txt, gate, { left: '0', top: '0', width: '112px', height: '56px', borderRadius: '28px', background: col, font: '700 28px/56px var(--fuente-texto)', textAlign: 'center', color: '#fff', boxShadow: '0 10px 30px rgba(0,0,0,.5)', zIndex: 6 });
    const pA = pill(`linear-gradient(135deg,${MORc},${MOR})`, 'nuevo'), pB = pill(`linear-gradient(135deg,${MORc},${MOR})`, 'nuevo'), pC = pill('linear-gradient(135deg,#8a7aa8,#5b4f78)', 'nuevo');
    const resOk = A('centro', 'Pasa la prueba: se activa', gate, { left: '0', right: '0', top: '770px', font: '700 44px/1 var(--fuente-titulo)', color: '#8ce99a', letterSpacing: '-.02em' });
    const resNo = A('centro', 'Empeora: no se activa', gate, { left: '0', right: '0', top: '770px', font: '700 44px/1 var(--fuente-titulo)', color: '#ff8787', letterSpacing: '-.02em' });
    const nota = A('centro', 'El modelo anterior no se borra.', gate, { left: '0', right: '0', top: '836px', font: '400 32px/1 var(--fuente-texto)', color: 'var(--suave)' });
    // flechas fijas
    const sv2 = svg('svg', { viewBox: '0 0 1920 1080', width: 1920, height: 1080 }, gate); sv2.style.cssText = 'position:absolute;left:0;top:0;pointer-events:none';
    const fl = (x1, x2) => svg('path', { d: `M${x1} 535H${x2}`, stroke: 'rgba(255,255,255,.22)', 'stroke-width': 4, 'stroke-dasharray': '4 12', 'stroke-linecap': 'round', fill: 'none' }, sv2);
    const f1 = fl(455, 590), f2 = fl(1310, 1470);

    // =====================================================================================
    // 3) LAS CIFRAS
    // =====================================================================================
    const nums = A('capa', null, raiz);
    const chip = (x, w, col, borde, bgc, num, tx, sub) => {
      const c = A('tarjeta', null, nums, { left: x + 'px', top: '70px', width: w + 'px', height: '152px', borderColor: borde, background: bgc, display: 'flex', alignItems: 'center', gap: '26px', padding: '0 34px' });
      const n = el('div', 'num', '0', c); n.style.cssText = `font-size:104px;line-height:1;color:${col};min-width:130px;text-align:right`;
      el('div', null, `<div style="font:700 36px/1.12 var(--fuente-titulo);letter-spacing:-.02em">${tx}</div><div style="font-size:26px;color:var(--suave);margin-top:8px">${sub}</div>`, c);
      return { c, n };
    };
    const ch1 = chip(120, 780, '#fff', 'rgba(112,72,232,.5)', 'linear-gradient(180deg,rgba(112,72,232,.16),rgba(112,72,232,.05))', 0, 'lugares de entrenamiento', '12 con minería y 19 sin');
    const ch2 = chip(1020, 780, NARc, 'rgba(217,119,87,.5)', 'linear-gradient(180deg,rgba(217,119,87,.16),rgba(217,119,87,.05))', 0, 'casos revisados por IA', '37 de 56 marcas extra eran falsos positivos');
    const XB = 930, WB = 650;
    const DATA = [
      { etq: 'Cobertura en La Pampa', sub: 'un bloque que nunca entrena', a: 54, lo: 90, hi: 90, max: 100, u: ' %' },
      { etq: 'Promedio de 11 bloques con minería', sub: 'cobertura de la minería de referencia', a: 39, lo: 66, hi: 69, max: 100, u: ' %' },
      { etq: 'Hectáreas falsas medias', sub: 'en lugares sin minería · menos es mejor', a: 2630, lo: 1043, hi: 1528, max: 2630, u: ' ha' },
    ];
    const filas3 = DATA.map((d, i) => {
      const y = 280 + i * 168;
      const f = A('', null, nums, { left: '0', top: y + 'px', width: '1920px', height: '150px' });
      A('', `<div style="font:700 35px/1.15 var(--fuente-titulo);letter-spacing:-.02em">${d.etq}</div><div style="font-size:27px;color:var(--suave);margin-top:9px">${d.sub}</div>`, f, { left: '120px', top: '8px', width: '720px' });
      const pista = top => A('', null, f, { left: XB + 'px', top: top + 'px', width: WB + 'px', height: '44px', borderRadius: '10px', background: 'rgba(255,255,255,.06)' });
      const b1 = A('', null, f, { left: XB + 'px', top: '10px', height: '44px', borderRadius: '10px', background: 'linear-gradient(90deg,#4b4b57,#7b7b88)' });
      const b2a = A('', null, f, { left: XB + 'px', top: '80px', height: '44px', borderRadius: '10px 0 0 10px', background: `linear-gradient(90deg,${MOR},${MORc})` });
      const b2b = A('', null, f, { left: XB + 'px', top: '80px', height: '44px', borderRadius: '0 10px 10px 0', background: 'repeating-linear-gradient(135deg, rgba(151,117,250,.55) 0 8px, rgba(151,117,250,.22) 8px 16px)' });
      pista(10).style.zIndex = -1; pista(80).style.zIndex = -1;
      A('num', 'v1', f, { left: (XB - 62) + 'px', top: '10px', font: '700 30px/44px var(--fuente-num)', color: '#9a9aa8' });
      A('num', 'v2', f, { left: (XB - 62) + 'px', top: '80px', font: '700 30px/44px var(--fuente-num)', color: MORc });
      const v1 = A('num', '', f, { top: '4px', font: '700 52px/56px var(--fuente-num)', color: '#c4c4cf', whiteSpace: 'nowrap' });
      const v2 = A('num', '', f, { top: '74px', font: '700 52px/56px var(--fuente-num)', color: '#fff', whiteSpace: 'nowrap' });
      return { f, d, b1, b2a, b2b, v1, v2, y };
    });
    const aviso = A('', '<b style="color:#fff;font-weight:600">Coincidencia con MapBiomas y revisión por IA, no con el terreno.</b>', nums, { left: '120px', top: '805px', width: '1680px', height: '66px', borderLeft: `6px solid ${AMA}`, background: 'rgba(245,183,0,.09)', borderRadius: '0 14px 14px 0', padding: '0 30px', font: '400 32px/66px var(--fuente-texto)', color: '#e6e6ec', letterSpacing: '-.005em' });

    // =====================================================================================
    // 4) LA META
    // =====================================================================================
    const meta = A('capa', null, raiz);
    const TX0 = 260, TW = 1400, TY = 380, FIN = 0.28;
    A('titulo xs centro', 'Dependencia de la <span class="g-naranja">IA</span>', meta, { left: '0', right: '0', top: '170px', fontSize: '64px' });
    const pistaM = A('', null, meta, { left: TX0 + 'px', top: TY + 'px', width: TW + 'px', height: '78px', borderRadius: '39px', background: 'rgba(255,255,255,.07)', boxShadow: 'inset 0 0 0 1px rgba(255,255,255,.1)' });
    const relM = A('', null, meta, { left: TX0 + 'px', top: TY + 'px', height: '78px', borderRadius: '39px', background: `linear-gradient(90deg,${NAR},${NARc})`, boxShadow: '0 0 50px rgba(217,119,87,.35)' });
    const mx = TX0 + TW * FIN;
    const marc = A('', null, meta, { left: (mx - 2) + 'px', top: (TY - 42) + 'px', width: '0', height: '160px', borderLeft: `4px dashed ${ORO}` });
    const metaChip = A('', 'META · ilustrativa', meta, { left: (mx - 150) + 'px', top: (TY - 112) + 'px', width: '300px', height: '56px', borderRadius: '28px', border: `3px dashed ${ORO}`, color: '#ffe8a3', font: '700 28px/50px var(--fuente-num)', letterSpacing: '.1em', textAlign: 'center', textTransform: 'uppercase', background: 'rgba(224,168,42,.1)' });
    const eje = A('', null, meta, { left: TX0 + 'px', top: (TY + 130) + 'px', width: TW + 'px', height: '40px' });
    const svE = svg('svg', { viewBox: `0 0 ${TW} 40`, width: TW, height: 40 }, eje);
    svg('path', { d: `M0 20H${TW - 16}`, stroke: 'rgba(255,255,255,.3)', 'stroke-width': 3, 'stroke-linecap': 'round' }, svE);
    svg('path', { d: `M${TW - 30} 8L${TW - 10} 20L${TW - 30} 32`, fill: 'none', stroke: 'rgba(255,255,255,.3)', 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, svE);
    A('', 'más ciclos de revisión', meta, { left: TX0 + 'px', top: (TY + 178) + 'px', font: '500 28px/1 var(--fuente-texto)', color: 'var(--suave)' });
    A('', 'Es una meta, no un resultado', meta, { left: (TX0 + TW - 520) + 'px', width: '520px', textAlign: 'right', top: (TY + 178) + 'px', font: '500 28px/1 var(--fuente-texto)', color: AMA });
    const fin = A('titulo m centro', 'Cada revisión <span class="g-naranja">enseña.</span>', meta, { left: '0', right: '0', top: '690px', fontSize: '108px' });

    // =====================================================================================
    return t => {
      // ---------- 1) ciclo
      const oR = 1 - an(t, 7.1, 7.9, E.io2);
      ring.style.visibility = oR <= 0.002 ? 'hidden' : 'visible';
      pon(ring, { o: oR, s: lerp(1, 0.94, an(t, 7.1, 7.9)), blur: lerp(0, 10, an(t, 7.1, 7.9)) });
      ent(tit1, an(t, 0.15, 1.1, E.out4), 40, 14);
      const s = clamp((t - 1.8) / 1.0, 0, 5);
      const k = Math.min(4, Math.floor(s)), ue = s >= 5 ? 5 : k + E.io3(s - k);
      const th = -90 + 72 * ue;
      // arco de progreso
      const [sx, sy] = pt(-90);
      if (ue > 0.01) { const [ex, ey] = pt(Math.min(th, 269.5)), big = (th + 90) > 180 ? 1 : 0; prog.setAttribute('d', `M${sx} ${sy}A${RX} ${RY} 0 ${big} 1 ${ex} ${ey}`); } else prog.setAttribute('d', '');
      prog.style.opacity = an(t, 1.8, 2.2);
      elip.style.opacity = an(t, 0.6, 1.6);
      trail.forEach((c, j) => { const sj = clamp((t - 0.045 * j - 1.8) / 1.0, 0, 5), kj = Math.min(4, Math.floor(sj)), uj = sj >= 5 ? 5 : kj + E.io3(sj - kj); const [x, y] = pt(-90 + 72 * uj); c.setAttribute('cx', x); c.setAttribute('cy', y); c.style.opacity = (1 - j / 8) * an(t, 1.7, 2.1) * (1 - an(t, 6.8, 7.1)); });
      chev.forEach((c, i) => { c.style.opacity = an(t, 1.0 + i * 0.12, 1.6 + i * 0.12) * (ue > i + 0.5 ? 1 : 0.55); });
      // nodos
      nodos.forEach((n, i) => {
        const p = an(t, 0.45 + 0.25 * i, 1.35 + 0.25 * i, E.out4);
        const dist = i === 0 ? Math.min(Math.abs(ue), Math.abs(ue - 5)) : Math.abs(ue - i);
        const pul = t > 1.8 ? 1 - clamp(dist / 0.6) : 0;
        const vist = t > 1.8 && (i === 0 ? true : ue >= i - 0.05) ? 1 : 0;
        ent(n, p, 50, 16, { s: 1 + 0.035 * pul });
        n.style.borderColor = `rgba(${H.hex(n._d.bd).join(',')},${0.28 + 0.55 * Math.max(pul, vist * 0.35)})`;
        n.style.boxShadow = `0 30px 80px rgba(0,0,0,.45), 0 0 ${70 * pul}px rgba(${H.hex(n._d.bd).join(',')},${0.55 * pul})`;
      });
      // v1 -> v2
      const cv = an(ue, 4.55, 5, E.out3);
      const pv = an(t, 0.55, 1.4, E.out4);
      pon(chip1, { o: pv * (1 - cv), y: -cv * 14 + lerp(30, 0, pv) }); pon(chip2, { o: pv * cv, y: lerp(14, 0, cv) + lerp(30, 0, pv), s: lerp(.8, 1, cv) });
      // centro
      const pc = an(t, 1.5, 2.3, E.out4);
      ent(cen, pc, 30, 12);
      const n = clamp((ue - 2) / 2) * 10;
      cnum.textContent = Math.round(n); carc.setAttribute('stroke-dashoffset', 100 * (1 - n / 10));
      const lleno = an(ue, 3.8, 4.1);
      carc.setAttribute('stroke', H.color(ORO, MORc, lleno));
      pon(ccap, { o: 1 - lleno }); pon(cfin, { o: lleno });
      cnum.style.color = lleno > 0.5 ? '#ffffff' : '#ffffff';

      // ---------- 2) compuerta
      const pG = an(t, 7.7, 8.7, E.out4), oG = pG * (1 - an(t, 12.65, 13.2, E.io2));
      gate.style.visibility = oG <= 0.002 ? 'hidden' : 'visible'; gate.style.opacity = oG;
      ent(tit2, pG, 40, 14);
      const e1 = an(t, 8.1, 9.0, E.out4);
      pon(cL, { o: e1, x: lerp(-60, 0, e1), blur: lerp(14, 0, e1) });
      pon(cam, { o: an(t, 8.2, 9.1, E.out4), y: lerp(50, 0, an(t, 8.2, 9.1, E.out4)), blur: lerp(14, 0, an(t, 8.2, 9.1, E.out4)) });
      pon(puerta, { o: an(t, 8.4, 9.3, E.out4), y: lerp(40, 0, an(t, 8.4, 9.3, E.out4)) });
      const e4 = an(t, 8.3, 9.2, E.out4); pon(cR, { o: e4, x: lerp(60, 0, e4), blur: lerp(14, 0, e4) });
      sv2.style.opacity = an(t, 8.6, 9.4);
      // filas de la prueba
      const rReset = 1 - an(t, 11.1, 11.35);
      filas2.forEach((r, i) => {
        const ok1 = an(t, 9.55 + 0.3 * i, 9.85 + 0.3 * i, E.out3) * rReset;
        const ok2 = i === 0 ? an(t, 11.62, 11.85, E.out3) : 0, no2 = i === 1 ? an(t, 11.9, 12.1, E.out3) : 0;
        const ok = Math.max(ok1, ok2);
        r.bg.setAttribute('opacity', Math.max(ok, no2)); r.bg.setAttribute('fill', no2 > 0.01 ? ROJ : VER);
        r.ok.setAttribute('stroke-dashoffset', 1 - ok); r.ok.style.opacity = no2 > 0.01 ? 0 : (ok > 0.01 ? 1 : 0);
        r.no.setAttribute('stroke-dashoffset', 1 - no2); r.no.style.opacity = no2 > 0.01 ? 1 : 0;
        r.c.style.borderColor = ok > 0.01 ? 'transparent' : (no2 > 0.01 ? 'transparent' : 'rgba(255,255,255,.28)');
        r.t.style.color = no2 > 0.5 ? '#ffa8a8' : '#f1f1f5';
      });
      // borde de la camara
      const gPas = an(t, 10.45, 10.8) * (1 - an(t, 11.1, 11.35)), gNo = an(t, 11.9, 12.1) * (1 - an(t, 12.5, 12.7));
      cam.style.borderColor = gNo > 0.01 ? `rgba(224,49,49,${.3 + .6 * gNo})` : `rgba(47,179,68,${.2 + .7 * gPas})`;
      cam.style.boxShadow = `0 30px 80px rgba(0,0,0,.45), 0 0 ${70 * gPas}px rgba(47,179,68,${.35 * gPas}), 0 0 ${70 * gNo}px rgba(224,49,49,${.35 * gNo})`;
      // puerta: se abre al pasar y se cierra detras
      const abre = an(t, 10.5, 10.95, E.io3) * (1 - an(t, 11.3, 11.65, E.io3));
      const sac = Math.sin(t * 70) * 6 * an(t, 11.92, 11.98) * (1 - an(t, 12.25, 12.4));
      pon(losa, { y: -abre * 300, x: sac });
            lampa.style.background = abre > 0.5 ? VER : (gNo > 0.3 ? ROJ : AMA);
      lampa.style.boxShadow = `0 0 16px ${abre > 0.5 ? VER : (gNo > 0.3 ? ROJ : AMA)}`;
      // pastillas
      const pe = (p, x, o, s) => pon(p, { x: x - 56, y: 507, o, s });
      { const m = an(t, 8.95, 9.65, E.io3), ent_ = an(t, 9.45, 9.75); pe(pA, lerp(380, 585, m), an(t, 8.8, 9.1) * (1 - ent_), lerp(1, .5, ent_)); }
      { const m = an(t, 10.95, 11.45, E.io3); pe(pB, lerp(1330, 1530, m), an(t, 10.85, 11.0) * (1 - an(t, 11.3, 11.5)), lerp(.7, 1, an(t, 10.85, 11.2)) * lerp(1, .5, an(t, 11.3, 11.5))); }
      { const m = an(t, 11.0, 11.55, E.io3) , sal = an(t, 12.15, 12.7, E.io3); pe(pC, lerp(380, 585, m) - sal * 190, an(t, 10.95, 11.15) * (1 - an(t, 11.45, 11.6)) + an(t, 12.1, 12.25) * (1 - an(t, 12.4, 12.7)), 1); }
      // tarjeta derecha: se enciende al llegar el modelo bueno
      const ac = an(t, 11.35, 11.7, E.out3);
      cR.style.borderColor = `rgba(47,179,68,${.12 + .8 * ac})`; cR.style.boxShadow = `0 30px 80px rgba(0,0,0,.45), 0 0 ${60 * ac}px rgba(47,179,68,${.3 * ac})`;
      pon(checkR, { o: ac * pG, s: lerp(.4, 1, E.outBack(ac)) });
      pon(resOk, { o: an(t, 10.6, 10.95) * (1 - an(t, 11.3, 11.5)), y: lerp(14, 0, an(t, 10.6, 10.95)) });
      pon(resNo, { o: an(t, 12.0, 12.25) * (1 - an(t, 12.55, 12.7)), y: lerp(14, 0, an(t, 12.0, 12.25)) });
      pon(nota, { o: an(t, 12.15, 12.4) * (1 - an(t, 12.55, 12.7)) });

      // ---------- 3) cifras
      const pN = an(t, 12.95, 13.6, E.out3), oN = pN * (1 - an(t, 17.85, 18.4, E.io2));
      nums.style.visibility = oN <= 0.002 ? 'hidden' : 'visible'; nums.style.opacity = oN;
      const c1 = an(t, 13.0, 13.8, E.out4), c2 = an(t, 13.15, 13.95, E.out4);
      ent(ch1.c, c1, 40, 14); ent(ch2.c, c2, 40, 14);
      ch1.n.textContent = Math.round(31 * an(t, 13.2, 14.2, E.out3)); ch2.n.textContent = Math.round(80 * an(t, 13.35, 14.35, E.out3));
      filas3.forEach((r, i) => {
        const s0 = 13.9 + i * 1.05, d = r.d;
        ent(r.f, an(t, s0 - 0.3, s0 + 0.4, E.out4), 36, 12);
        const p1 = an(t, s0, s0 + 0.85, E.out4), p2 = an(t, s0 + 0.5, s0 + 1.45, E.out4);
        const w = v => v / d.max * WB;
        r.b1.style.width = (w(d.a) * p1) + 'px';
        r.b2a.style.width = (w(d.lo) * p2) + 'px';
        r.b2b.style.left = (XB + w(d.lo) * p2) + 'px'; r.b2b.style.width = (w(d.hi - d.lo) * p2) + 'px';
        r.v1.style.left = (XB + w(d.a) * p1 + 20) + 'px'; r.v1.textContent = fm(d.a * p1) + d.u; r.v1.style.opacity = p1;
        r.v2.style.left = (XB + w(d.hi) * p2 + 20) + 'px';
        r.v2.textContent = (d.hi === d.lo ? fm(d.lo * p2) : fm(d.lo * p2) + '–' + fm(d.hi * p2)) + d.u; r.v2.style.opacity = p2;
      });
      ent(aviso, an(t, 13.9, 14.7, E.out4), 30, 10);

      // ---------- 4) meta
      const pM = an(t, 18.2, 19.0, E.out4);
      meta.style.visibility = pM <= 0.002 ? 'hidden' : 'visible'; meta.style.opacity = pM;
      const bP = an(t, 18.75, 20.5, E.io3);
      relM.style.width = (TW * lerp(1, FIN, bP)) + 'px';
      pon(pistaM, { o: pM });
      pon(marc, { o: an(t, 18.4, 19.0), sy: an(t, 18.4, 19.2, E.out4), origen: '50% 100%' });
      ent(metaChip, an(t, 18.5, 19.2, E.out4), 20, 8);
      eje.style.opacity = an(t, 18.6, 19.2);
      ent(fin, an(t, 19.9, 20.9, E.out4), 50, 18);
    };
  },
});
