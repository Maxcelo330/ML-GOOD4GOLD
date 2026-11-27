/* Escena 6 - El cerebro del modelo (26 s).
   Cuatro momentos: (1) un arbol real de preguntas y la ruta de un pixel, (2) los 300 votos que se suman,
   (3) la curva que convierte la suma en puntaje (0 a 100), (4) las variables que mas pesan.
   Datos REALES: assets/capturas/e06_votos.json (hojas por arbol de pixeles del bloque) y arbol_ejemplo.json (umbrales del arbol 1).
   El puntaje es RELATIVO, no una probabilidad. Todo es funcion pura de t. */
Pres.escena({
  id: 'cerebro', titulo: 'El cerebro del modelo', dur: 26,
  recursos: ['assets/capturas/e06_votos.json'],
  subs: [
    [0.5, 4.2, 'Dentro del modelo hay 300 árboles de preguntas de sí o no.'],
    [4.4, 8.2, 'Cada píxel baja por cada árbol y termina en una hoja con un valor.'],
    [8.8, 12.8, 'Se suman los 300 valores: cada árbol aporta su voto.'],
    [13.0, 15.8, 'La suma pasa por una curva y se convierte en un puntaje de 0 a 100.'],
    [16.2, 20.8, 'Bosque casi 0, río 76, suelo removido 97. Es un puntaje relativo, no una probabilidad.'],
    [21.3, 25.4, 'Lo que más pesa: cuánto suelo pelado y cuánta agua hay alrededor.'],
  ],
  montar(raiz, H) {
    const { el, svg, pon, an, E, lerp, clamp, rec } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const vis = (e, o) => { e.style.visibility = o <= 0.002 ? 'hidden' : 'visible'; };
    const MOR = '#7048e8', MORc = '#9775fa', NAR = '#d97757', NARc = '#f0a283', ORO = '#e0a82a', VER = '#2fb344', AZU = '#74c0fc';
    const fc = (v, d = 2) => v.toLocaleString('es', { minimumFractionDigits: d, maximumFractionDigits: d });

    // ---------- datos reales (con respaldo si no cargan)
    const D = rec('assets/capturas/e06_votos.json') || {};
    const PX = (D.pixeles) || {};
    const HOJAS = (PX.suelo_removido && PX.suelo_removido.hojas) || new Array(300).fill(0);
    const SUMAS = {
      bosque: (PX.bosque && PX.bosque.suma) != null ? PX.bosque.suma : -6.672,
      rio: (PX.rio && PX.rio.suma) != null ? PX.rio.suma : 1.158,
      suelo: (PX.suelo_removido && PX.suelo_removido.suma) != null ? PX.suelo_removido.suma : 3.444,
    };
    const NH = HOJAS.length;
    const CUM = []; { let s = 0; for (let i = 0; i < NH; i++) { s += HOJAS[i]; CUM.push(s); } }
    const sig = s => 100 / (1 + Math.exp(-s));

    // capas de cada momento
    const capa = () => { const c = A('capa', null, raiz, { left: '0', top: '0', width: '1920px', height: '1080px' }); return c; };
    const c1 = capa(), c2 = capa(), c3 = capa(), c4 = capa();

    // =====================================================================================
    // 1) UN ARBOL DE PREGUNTAS
    // =====================================================================================
    const t1 = A('titulo xs centro', '<span class="g-morado">300 árboles</span> de preguntas', c1, { left: '0', right: '0', top: '70px', fontSize: '64px' });
    // tarjeta del pixel (suelo removido real)
    const pc = A('tarjeta morada', null, c1, { left: '90px', top: '210px', width: '600px', height: '760px', padding: '0' });
    A('etiqueta', 'Un píxel real', pc, { left: '34px', top: '28px', fontSize: '24px' });
    A('', 'Suelo removido', pc, { left: '34px', top: '66px', font: '800 46px/1 var(--fuente-titulo)', letterSpacing: '-.03em', color: '#fff' });
    const VARS = [['pelado en 300 m', '0,88', 'frac_pelado_300m'], ['agua en 300 m', '0,11', 'frac_agua_300m'], ['pendiente', '5,6', 'pendiente'], ['ndvi', '0,04', 'ndvi'], ['ndwi', '−0,16', 'ndwi'], ['bsi', '0,18', 'bsi']];
    const filas = VARS.map((v, i) => {
      const r = A('', null, pc, { left: '34px', right: '34px', top: (150 + i * 62) + 'px', height: '50px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,.08)' });
      el('span', null, v[0], r).style.cssText = 'font:400 28px var(--fuente-texto);color:var(--suave)';
      el('span', 'num', v[1], r).style.cssText = 'font-size:32px;color:#fff';
      return r;
    });
    A('', '+ 8 variables más: bandas del satélite y contexto', pc, { left: '34px', right: '34px', top: '532px', font: '400 25px/1.3 var(--fuente-texto)', color: 'var(--suave)' });
    A('', '14 variables en total', pc, { left: '34px', right: '34px', top: '640px', font: '700 30px var(--fuente-titulo)', color: MORc });
    A('', 'Valores reales de un píxel del bloque analizado', pc, { left: '34px', right: '34px', top: '690px', font: '400 22px/1.3 var(--fuente-texto)', color: 'var(--suave)' });

    // arbol (svg) - umbrales reales del arbol 1
    const sv1 = svg('svg', { viewBox: '0 0 1920 1080', width: 1920, height: 1080 }, c1); sv1.style.cssText = 'position:absolute;left:0;top:0;overflow:visible;pointer-events:none';
    const ND = [
      { id: 'r', x: 1295, y: 310, t: 'pelado ≤ 0,089 ?' },
      { id: 'a', x: 1005, y: 490, t: 'pelado ≤ 0,022 ?' },
      { id: 'b', x: 1585, y: 490, t: 'agua ≤ 0,338 ?' },
      { id: 'c', x: 1450, y: 660, t: 'agua ≤ 0,004 ?' },
      { id: 'd', x: 1720, y: 660, t: 'B03 ≤ 0,18 ?' },
    ];
    const LF = [
      { id: 'l1', x: 905, y: 670, v: '+0,056', pad: 'a' }, { id: 'l2', x: 1110, y: 670, v: '+0,100', pad: 'a' },
      { id: 'l3', x: 1385, y: 830, v: null, pad: 'c' }, { id: 'l4', x: 1515, y: 830, v: '+0,217', pad: 'c', ruta: true },
      { id: 'l5', x: 1655, y: 830, v: null, pad: 'd' }, { id: 'l6', x: 1785, y: 830, v: '+0,231', pad: 'd' },
    ];
    const byId = {}; ND.forEach(n => { byId[n.id] = n; }); LF.forEach(n => { byId[n.id] = n; });
    // aristas: [padre, hijo, etiqueta, esRuta]
    const AR = [['r', 'a', 'sí', 0], ['r', 'b', 'no', 1], ['a', 'l1', 'sí', 0], ['a', 'l2', 'no', 0], ['b', 'c', 'sí', 1], ['b', 'd', 'no', 0], ['c', 'l3', 'sí', 0], ['c', 'l4', 'no', 1], ['d', 'l5', 'sí', 0], ['d', 'l6', 'no', 0]];
    const aristas = AR.map(([p, h, et, ruta]) => {
      const P0 = byId[p], P1 = byId[h];
      const y0 = P0.y + 34, y1 = P1.y - (h[0] === 'l' ? 30 : 34);
      const d = `M${P0.x} ${y0} C ${P0.x} ${(y0 + y1) / 2}, ${P1.x} ${(y0 + y1) / 2}, ${P1.x} ${y1}`;
      const base = svg('path', { d, fill: 'none', stroke: 'rgba(255,255,255,.2)', 'stroke-width': 3, 'stroke-linecap': 'round' }, sv1);
      const luz = svg('path', { d, fill: 'none', stroke: MORc, 'stroke-width': 7, 'stroke-linecap': 'round' }, sv1);
      luz.style.filter = 'drop-shadow(0 0 8px rgba(151,117,250,.9))';
      const lx = (P0.x + P1.x) / 2 + (P1.x < P0.x ? -26 : 26), ly = (y0 + y1) / 2 - 4;
      const tx = A('', et, c1, { left: (lx - 24) + 'px', top: (ly - 18) + 'px', width: '48px', textAlign: 'center', font: '600 24px var(--fuente-num)', color: 'rgba(255,255,255,.55)' });
      return { base, luz, tx, ruta, h };
    });
    const nodos = ND.map(n => {
      const e = A('', n.t, c1, { left: (n.x - 125) + 'px', top: (n.y - 34) + 'px', width: '250px', height: '68px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '18px', background: '#171722', border: '2px solid rgba(255,255,255,.2)', font: '600 26px var(--fuente-num)', color: '#fff', whiteSpace: 'nowrap' });
      e._n = n; return e;
    });
    const hojas = LF.map(n => {
      const e = A('', n.v == null ? '·' : n.v, c1, { left: (n.x - 58) + 'px', top: (n.y - 30) + 'px', width: '116px', height: '60px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '30px', background: n.v == null ? 'rgba(255,255,255,.05)' : 'rgba(112,72,232,.22)', border: '2px solid ' + (n.v == null ? 'rgba(255,255,255,.12)' : 'rgba(151,117,250,.7)'), font: '700 26px var(--fuente-num)', color: n.v == null ? 'rgba(255,255,255,.3)' : '#fff' });
      e._n = n; return e;
    });
    const nota1 = A('', 'Árbol 1 de 300 · umbrales reales', c1, { left: '780px', top: '212px', font: '600 24px var(--fuente-num)', letterSpacing: '.12em', color: 'var(--suave)', textTransform: 'uppercase' });
    // pulso del pixel que baja por la ruta
    const pulso = svg('circle', { r: 16, fill: '#fff' }, sv1); pulso.style.filter = 'drop-shadow(0 0 14px rgba(255,255,255,.95))';
    const RUTA = ['r', 'b', 'c', 'l4'];
    const rutaPos = u => { // u en 0..1 a lo largo de r->b->c->l4
      const k = clamp(u) * 3, i = Math.min(2, Math.floor(k)), f = k - i;
      const a = byId[RUTA[i]], b = byId[RUTA[i + 1]];
      return [lerp(a.x, b.x, E.io2(f)), lerp(a.y, b.y, E.io2(f))];
    };
    const vot = A('', '+0,217', c1, { left: '1415px', top: '905px', width: '200px', textAlign: 'center', font: '800 54px var(--fuente-num)', color: '#fff' });
    const vot2 = A('', 'el voto de este árbol', c1, { left: '1365px', top: '975px', width: '300px', textAlign: 'center', font: '400 26px var(--fuente-texto)', color: 'var(--suave)' });

    // =====================================================================================
    // 2) LOS 300 VOTOS
    // =====================================================================================
    const t2 = A('titulo xs centro', '300 árboles, <span class="g-morado">300 votos</span>', c2, { left: '0', right: '0', top: '70px', fontSize: '64px' });
    const sv2 = svg('svg', { viewBox: '0 0 1920 1080', width: 1920, height: 1080 }, c2); sv2.style.cssText = 'position:absolute;left:0;top:0;overflow:visible;pointer-events:none';
    const X0 = 150, WW = 1620, YB = 400, SB = 560;       // barras: centro en y=YB, 560 px por unidad
    const defs2 = svg('defs', {}, sv2);
    const cp = svg('clipPath', { id: 'cer-clip' }, defs2); const cpr = svg('rect', { x: X0, y: 0, width: 0, height: 1080 }, cp);
    const g2 = svg('g', { 'clip-path': 'url(#cer-clip)' }, sv2);
    svg('line', { x1: X0, y1: YB, x2: X0 + WW, y2: YB, stroke: 'rgba(255,255,255,.25)', 'stroke-width': 2 }, sv2);
    const bw = WW / NH;
    HOJAS.forEach((v, i) => {
      const h = Math.abs(v) * SB;
      svg('rect', { x: X0 + i * bw + 0.5, y: v >= 0 ? YB - h : YB, width: Math.max(1.5, bw - 1.5), height: Math.max(1, h), fill: v >= 0 ? MORc : '#7aa2d6', opacity: 0.95 }, g2);
    });
    // curva de la suma acumulada (base y=870, 175 px por unidad)
    const YC = 880, SC = 150;
    svg('line', { x1: X0, y1: YC, x2: X0 + WW, y2: YC, stroke: 'rgba(255,255,255,.25)', 'stroke-width': 2 }, sv2);
    let dc = ''; CUM.forEach((s, i) => { dc += (i ? 'L' : 'M') + (X0 + (i + 0.5) * bw).toFixed(1) + ' ' + (YC - s * SC).toFixed(1); });
    svg('path', { d: dc, fill: 'none', stroke: ORO, 'stroke-width': 6, 'stroke-linejoin': 'round' }, g2);
    const barra = svg('line', { x1: X0, y1: 240, x2: X0, y2: 900, stroke: 'rgba(255,255,255,.8)', 'stroke-width': 2, 'stroke-dasharray': '6 8' }, sv2);
    A('etiqueta', 'Voto de cada árbol', c2, { left: X0 + 'px', top: '196px', fontSize: '23px' });
    A('', '<span style="color:' + MORc + '">▮</span> a favor &nbsp; <span style="color:#7aa2d6">▮</span> en contra', c2, { left: '1250px', top: '196px', width: '520px', textAlign: 'right', font: '400 25px var(--fuente-texto)', color: 'var(--suave)' });
    A('etiqueta', 'Suma acumulada', c2, { left: X0 + 'px', top: '500px', fontSize: '23px', color: ORO });
    const sumaT = A('num', '0,00', c2, { left: '1330px', top: '640px', width: '440px', textAlign: 'right', fontSize: '84px', color: ORO });
    const arbT = A('', 'árbol 0 de 300', c2, { left: '1330px', top: '735px', width: '440px', textAlign: 'right', font: '600 28px var(--fuente-num)', color: 'var(--suave)' });
    const piePx = A('', 'Píxel de suelo removido del bloque analizado', c2, { left: X0 + 'px', top: '906px', font: '400 26px var(--fuente-texto)', color: 'var(--suave)' });

    // =====================================================================================
    // 3) LA CURVA: SUMA -> PUNTAJE
    // =====================================================================================
    const t3 = A('titulo xs centro', 'De la suma al <span class="g-morado">puntaje</span>', c3, { left: '0', right: '0', top: '70px', fontSize: '64px' });
    const sv3 = svg('svg', { viewBox: '0 0 1920 1080', width: 1920, height: 1080 }, c3); sv3.style.cssText = 'position:absolute;left:0;top:0;overflow:visible;pointer-events:none';
    const GX = 160, GW = 1100, GY0 = 300, GH = 560, SMIN = -8, SMAX = 5;
    const mx = s => GX + (s - SMIN) / (SMAX - SMIN) * GW, my = p => GY0 + GH - p / 100 * GH;
    [0, 50, 100].forEach(p => {
      svg('line', { x1: GX, y1: my(p), x2: GX + GW, y2: my(p), stroke: 'rgba(255,255,255,.12)', 'stroke-width': 2, 'stroke-dasharray': '4 10' }, sv3);
      A('num', String(p), c3, { left: (GX - 90) + 'px', top: (my(p) - 20) + 'px', width: '70px', textAlign: 'right', fontSize: '28px', color: 'var(--suave)' });
    });
    svg('line', { x1: GX, y1: GY0 + GH, x2: GX + GW, y2: GY0 + GH, stroke: 'rgba(255,255,255,.35)', 'stroke-width': 2 }, sv3);
    A('etiqueta', 'suma de los 300 votos', c3, { left: GX + 'px', top: (GY0 + GH + 36) + 'px', width: GW + 'px', textAlign: 'center', fontSize: '23px' });
    A('etiqueta', 'puntaje', c3, { left: (GX - 100) + 'px', top: (GY0 - 56) + 'px', fontSize: '23px' });
    let dsg = ''; for (let k = 0; k <= 80; k++) { const s = SMIN + (SMAX - SMIN) * k / 80; dsg += (k ? 'L' : 'M') + mx(s).toFixed(1) + ' ' + my(sig(s)).toFixed(1); }
    const curva = svg('path', { d: dsg, fill: 'none', stroke: MORc, 'stroke-width': 7, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, sv3);
    curva.style.filter = 'drop-shadow(0 0 10px rgba(151,117,250,.7))';
    const PTS = [
      { k: 'bosque', n: 'Bosque', s: SUMAS.bosque, col: VER, dx: 34, dy: -140 },
      { k: 'rio', n: 'Río', s: SUMAS.rio, col: AZU, dx: 40, dy: 34, nota: 'también puntúa alto: por eso se revisa' },
      { k: 'suelo', n: 'Suelo removido', s: SUMAS.suelo, col: ORO, dx: -350, dy: -108 },
    ];
    PTS.forEach(p => {
      const sc = sig(p.s);
      p.x = mx(p.s); p.y = my(sc);
      p.dot = svg('circle', { cx: p.x, cy: p.y, r: 17, fill: p.col, stroke: '#0a0a0f', 'stroke-width': 4 }, sv3);
      p.dot.style.filter = 'drop-shadow(0 0 12px ' + p.col + ')';
      p.lab = A('', `<div style="font:700 30px var(--fuente-titulo);color:${p.col}">${p.n}</div><div style="font:600 26px var(--fuente-num);color:#fff;margin-top:4px">suma ${fc(p.s, 2)} → puntaje ${Math.round(sc) < 1 && sc < 0.5 ? '0' : Math.round(sc)}</div>` + (p.nota ? `<div style="font:400 23px/1.25 var(--fuente-texto);color:var(--suave);margin-top:6px;max-width:330px">${p.nota}</div>` : ''), c3, { left: (p.x + p.dx) + 'px', top: (p.y + p.dy) + 'px', whiteSpace: 'nowrap' });
    });
    // tarjeta explicativa
    const ex = A('tarjeta morada', null, c3, { left: '1360px', top: '300px', width: '470px', height: '560px', padding: '0' });
    A('etiqueta', 'La regla', ex, { left: '36px', top: '30px', fontSize: '24px' });
    A('', '100 ÷ (1 + e<sup style="font-size:.55em">−suma</sup>)', ex, { left: '36px', top: '84px', width: '400px', font: '700 40px/1.2 var(--fuente-num)', color: '#fff' });
    A('', 'Una suma muy negativa da un puntaje cercano a 0; una muy positiva, cercano a 100.', ex, { left: '36px', top: '190px', width: '400px', font: '400 29px/1.35 var(--fuente-texto)', color: 'var(--suave)' });
    A('', '<b style="color:#fff">Es relativo,</b> no una probabilidad: sirve para ordenar qué mirar primero.', ex, { left: '36px', top: '388px', width: '400px', font: '400 29px/1.35 var(--fuente-texto)', color: 'var(--suave)' });

    // =====================================================================================
    // 4) LAS VARIABLES QUE MAS PESAN
    // =====================================================================================
    const t4 = A('titulo xs centro', 'Qué <span class="g-morado">mira</span> el modelo', c4, { left: '0', right: '0', top: '70px', fontSize: '64px' });
    const IMP = [
      ['pelado en 300 m', 15.5, 'contexto'], ['agua en 300 m', 14.8, 'contexto'], ['ndvi', 12.3, 'índice'], ['ndwi', 12.3, 'índice'],
      ['pendiente', 9.8, 'terreno'], ['ndvi medio 300 m', 6.3, 'contexto'], ['textura ndvi 100 m', 6.2, 'contexto'], ['banda B12', 5.6, 'banda'],
    ];
    const COLT = { contexto: MORc, 'índice': ORO, terreno: VER, banda: AZU };
    const BX = 560, BW = 900, BY0 = 230, BH = 62;
    const filasI = IMP.map((r, i) => {
      const y = BY0 + i * (BH + 18);
      A('', r[0], c4, { left: '120px', top: (y + 10) + 'px', width: '420px', textAlign: 'right', font: '600 30px var(--fuente-texto)', color: '#fff' });
      A('', null, c4, { left: BX + 'px', top: y + 'px', width: BW + 'px', height: BH + 'px', borderRadius: '14px', background: 'rgba(255,255,255,.05)' });
      const b = A('', null, c4, { left: BX + 'px', top: y + 'px', width: (r[1] / 16 * BW) + 'px', height: BH + 'px', borderRadius: '14px', background: `linear-gradient(90deg, ${COLT[r[2]]}, ${COLT[r[2]]}cc)`, transformOrigin: '0 50%' });
      const v = A('num', fc(r[1], 1) + ' %', c4, { left: (BX + r[1] / 16 * BW + 18) + 'px', top: (y + 8) + 'px', fontSize: '32px', color: '#fff' });
      return { b, v };
    });
    // leyenda
    const ley = A('', Object.keys(COLT).map(k => `<span style="display:inline-flex;align-items:center;gap:10px;margin-right:34px"><i style="width:18px;height:18px;border-radius:5px;background:${COLT[k]};display:inline-block"></i>${k}</span>`).join(''), c4, { left: '560px', top: '860px', font: '400 27px var(--fuente-texto)', color: 'var(--suave)', whiteSpace: 'nowrap' });
    const pie4 = A('', '14 variables: 6 bandas del satélite, 3 índices, la pendiente y 4 de contexto. Peso relativo de cada una en el modelo.', c4, { left: '120px', right: '120px', top: '930px', textAlign: 'center', font: '400 28px/1.35 var(--fuente-texto)', color: 'var(--suave)' });

    // =====================================================================================
    // ACTUALIZACION
    // =====================================================================================
    const capaOp = (t, a, b, c, d) => an(t, a, b, E.out3) * (1 - an(t, c, d, E.io2));
    return t => {
      // ---- capas
      const o1 = capaOp(t, 0.1, 0.7, 8.0, 8.8), o2 = capaOp(t, 8.6, 9.3, 15.3, 16.0), o3 = capaOp(t, 15.8, 16.5, 20.7, 21.4), o4 = capaOp(t, 21.2, 21.9, 25.5, 26);
      [[c1, o1], [c2, o2], [c3, o3], [c4, o4]].forEach(([c, o]) => { pon(c, { o }); vis(c, o); });

      // ---- 1) arbol
      if (o1 > 0.002) {
        ent(t1, an(t, 0.2, 1.0, E.out4), 30, 12);
        ent(pc, an(t, 0.4, 1.3, E.out4), 50, 14);
        filas.forEach((r, i) => { const p = an(t, 0.8 + i * 0.12, 1.5 + i * 0.12, E.out4); pon(r, { o: p, x: lerp(-30, 0, p) }); });
        // niveles del arbol: raiz -> hijos -> hojas
        const apar = (n, t0) => an(t, t0, t0 + 0.6, E.out4);
        nodos.forEach(e => { const n = e._n; const t0 = n.id === 'r' ? 1.6 : (n.id === 'a' || n.id === 'b') ? 2.1 : 2.5; const p = apar(n, t0); ent(e, p, 18, 8); });
        hojas.forEach(e => { const n = e._n; const t0 = (n.pad === 'a') ? 2.5 : 2.9; const p = apar(n, t0); ent(e, p, 18, 8); });
        pon(nota1, { o: an(t, 1.4, 2.0) });
        aristas.forEach(a => {
          const t0 = a.h === 'a' || a.h === 'b' ? 2.0 : a.h[0] === 'l' && (a.h === 'l1' || a.h === 'l2') ? 2.4 : 2.4;
          pon(a.tx, { o: an(t, t0 + 0.2, t0 + 0.7) });
          H.trazo(a.base, an(t, t0, t0 + 0.7, E.out3));
          // la ruta se ilumina cuando pasa el pixel
          const u = an(t, 4.6, 7.0, E.io2);
          let lit = 0;
          if (a.ruta) { const idx = RUTA.indexOf(a.h); const lo = (idx - 1) / 3, hi = idx / 3; lit = clamp((u - lo) / (hi - lo)); }
          a.luz.style.opacity = a.ruta ? (lit > 0 ? 1 : 0) : 0;
          H.trazo(a.luz, lit);
        });
        // resaltar nodos y hoja de la ruta
        const u = an(t, 4.6, 7.0, E.io2);
        nodos.forEach(e => { const k = RUTA.indexOf(e._n.id); const on = k >= 0 && u >= k / 3 - 0.001 && t > 4.6 ? 1 : 0; e.style.borderColor = on ? MORc : 'rgba(255,255,255,.2)'; e.style.background = on ? 'rgba(112,72,232,.35)' : '#171722'; });
        hojas.forEach(e => { if (e._n.ruta) { const on = u > 0.999 ? 1 : 0; e.style.background = on ? ORO : 'rgba(112,72,232,.22)'; e.style.color = on ? '#1a1205' : '#fff'; } });
        // pulso
        const pp = rutaPos(u);
        pulso.setAttribute('cx', pp[0]); pulso.setAttribute('cy', pp[1]);
        pulso.style.opacity = t > 4.4 && t < 7.1 ? clamp(an(t, 4.4, 4.7) * (1 - an(t, 6.9, 7.1))) : 0;
        const pv = an(t, 7.0, 7.6, E.out4);
        ent(vot, pv, 20, 8); ent(vot2, an(t, 7.2, 7.8, E.out4), 20, 8);
      }

      // ---- 2) votos
      if (o2 > 0.002) {
        ent(t2, an(t, 8.8, 9.5, E.out4), 30, 12);
        const p = an(t, 9.6, 14.0, E.io2);
        const xr = X0 + WW * p;
        cpr.setAttribute('width', Math.max(0, WW * p));
        barra.setAttribute('x1', xr); barra.setAttribute('x2', xr);
        barra.style.opacity = p > 0 && p < 0.999 ? 1 : 0;
        const k = Math.min(NH, Math.max(0, Math.floor(p * NH + 0.0001)));
        const suma = k > 0 ? CUM[k - 1] : 0;
        sumaT.textContent = fc(suma, 2);
        arbT.textContent = 'árbol ' + k + ' de ' + NH;
        pon(sumaT, { o: an(t, 9.4, 10.0) }); pon(arbT, { o: an(t, 9.4, 10.0) });
        pon(piePx, { o: an(t, 9.8, 10.5) });
      }

      // ---- 3) curva
      if (o3 > 0.002) {
        ent(t3, an(t, 16.0, 16.7, E.out4), 30, 12);
        H.trazo(curva, an(t, 16.2, 17.6, E.io2));
        PTS.forEach((p, i) => {
          const a = 17.4 + i * 0.9, pp = an(t, a, a + 0.5, E.outBack);
          p.dot.setAttribute('r', 17 * pp); p.dot.style.opacity = pp > 0 ? 1 : 0;
          const q = an(t, a + 0.1, a + 0.7, E.out4); pon(p.lab, { o: q, y: lerp(14, 0, q) });
        });
        ent(ex, an(t, 16.6, 17.5, E.out4), 40, 12);
      }

      // ---- 4) variables
      if (o4 > 0.002) {
        ent(t4, an(t, 21.4, 22.1, E.out4), 30, 12);
        filasI.forEach((f, i) => {
          const a = 21.9 + i * 0.28, p = an(t, a, a + 0.9, E.out4);
          pon(f.b, { sx: Math.max(0.0001, p), sy: 1 });
          pon(f.v, { o: an(t, a + 0.5, a + 1.1) });
        });
        pon(ley, { o: an(t, 24.2, 24.8) });
        pon(pie4, { o: an(t, 24.4, 25.0) });
      }
    };
  },
});
