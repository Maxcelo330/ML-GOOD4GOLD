/* Escena 12 - La vista del funcionario (22 s).
   No hay capturas de esta vista: es un ESQUEMA ILUSTRATIVO con datos SIMULADOS (rotulado en pantalla).
   Fuente de los hechos: HECHOS.md (publico vs funcionario, pasivos, denuncias con estado y nota, detecciones revisadas, D-002).
   Todo es funcion pura de t. */
Pres.escena({
  id: 'funcionario', titulo: 'Lo que ve el funcionario', dur: 22,
  recursos: [],
  subs: [
    [0.5, 3.6, 'El público ve operadores en regla, en proceso y denuncias, sin relaves ni operadores marcados «No legal».'],
    [3.8, 7.3, 'El funcionario, con usuario y clave, ve además rojos, grises y los pasivos como hexágonos violeta.'],
    [7.5, 10.2, 'Los pasivos se ordenan por riesgo y por valor.'],
    [10.6, 14.6, 'Las denuncias llegan con su estado y una nota de seguimiento.'],
    [15.0, 19.2, 'Las zonas que una persona revisó en el visor pasan a la app, y solo las ve el funcionario.'],
    [19.6, 21.4, 'Cada rol ve lo que le corresponde.'],
  ],
  montar(raiz, H) {
    const { el, svg, pon, an, E, lerp, clamp, rng } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const VER = '#2fb344', AMA = '#f5b700', AZU = '#4dabf7', ROJ = '#e03131', GRI = '#adb5bd', VIO = '#9775fa', MORc = '#9775fa', ORO = '#e0a82a';

    const tit = A('titulo xs', 'Cada rol ve <span class="g-morado">lo que le corresponde</span>', raiz, { left: '90px', top: '36px', fontSize: '56px' });
    const aviso = A('pastilla', 'Esquema ilustrativo · datos simulados', raiz, { left: '1330px', top: '48px', fontSize: '24px', borderColor: 'rgba(224,168,42,.5)', background: 'rgba(224,168,42,.12)' });

    // ---------- mapas esquematicos
    const MW = 880, MHT = 190;
    const R = rng(11);
    const pts = (n, margen = 50) => Array.from({ length: n }, () => [margen + R() * (MW - 2 * margen), 26 + R() * (MHT - 52)]);
    const P = { verde: pts(10), amarillo: pts(5), azul: pts(4), rojo: pts(4), gris: pts(4), pasivo: pts(3) };

    const tarjeta = (top, h, titulo, sub, borde) => {
      const c = A('tarjeta', null, raiz, { left: '90px', top: top + 'px', width: MW + 'px', height: h + 'px', borderRadius: '26px', overflow: 'hidden', borderColor: borde });
      A('', titulo, c, { left: '28px', top: '16px', font: '800 34px var(--fuente-titulo)', letterSpacing: '-.02em', color: '#fff' });
      A('', sub, c, { right: '28px', top: '24px', font: '500 24px var(--fuente-num)', color: 'var(--suave)', textAlign: 'right' });
      const mp = A('', null, c, { left: '0', top: '68px', width: MW + 'px', height: MHT + 'px', background: 'linear-gradient(160deg,#1a2a1f,#14201a)' });
      const sv = svg('svg', { viewBox: `0 0 ${MW} ${MHT}`, width: MW, height: MHT }, mp);
      for (let x = 0; x <= MW; x += 80) svg('line', { x1: x, y1: 0, x2: x, y2: MHT, stroke: 'rgba(255,255,255,.05)', 'stroke-width': 2 }, sv);
      for (let y = 0; y <= MHT; y += 80) svg('line', { x1: 0, y1: y, x2: MW, y2: y, stroke: 'rgba(255,255,255,.05)', 'stroke-width': 2 }, sv);
      svg('path', { d: `M-10 60 C 160 20, 260 150, 420 120 S 700 60, ${MW + 10} 180`, fill: 'none', stroke: 'rgba(116,192,252,.35)', 'stroke-width': 10, 'stroke-linecap': 'round' }, sv);
      return { c, sv };
    };
    const dot = (sv, p, col) => { const d = svg('circle', { cx: p[0], cy: p[1], r: 0, fill: col, stroke: '#0a0a0f', 'stroke-width': 3 }, sv); return d; };
    const hexPath = (cx, cy, r) => Array.from({ length: 6 }, (_, k) => { const a = Math.PI / 3 * k + Math.PI / 6; return (k ? 'L' : 'M') + (cx + r * Math.cos(a)).toFixed(1) + ' ' + (cy + r * Math.sin(a)).toFixed(1); }).join('') + 'Z';

    const pub = tarjeta(130, 342, 'Público', 'sin cuenta', 'rgba(255,255,255,.14)');
    const fun = tarjeta(492, 430, 'Funcionario', 'con usuario y clave', 'rgba(151,117,250,.55)');
    const leg = (padre, top, items) => A('', items.map(([c, t, hex]) => `<span style="display:inline-flex;align-items:center;gap:10px;margin-right:30px"><i style="width:20px;height:20px;${hex ? 'clip-path:polygon(25% 5%,75% 5%,100% 50%,75% 95%,25% 95%,0 50%)' : 'border-radius:50%'};background:${c};display:inline-block"></i>${t}</span>`).join(''), padre, { left: '28px', top: top + 'px', font: '500 25px var(--fuente-texto)', color: '#fff', whiteSpace: 'nowrap' });
    const legPub = leg(pub.c, 270, [[VER, 'operador legal'], [AMA, 'en proceso'], [AZU, 'denuncias']]);
    const legFun1 = leg(fun.c, 270, [[VER, 'legal'], [AMA, 'en proceso'], [AZU, 'denuncias']]);
    const legFun2 = leg(fun.c, 316, [[ROJ, 'no legal / por verificar'], [GRI, 'sin verificar'], [VIO, 'pasivo (relave o cola)', 1]]);
    A('', 'No ve relaves, colas ni operadores «No legal».', pub.c, { left: '28px', top: '308px', font: '400 24px var(--fuente-texto)', color: 'var(--suave)' });
    const candado = A('', '<svg viewBox="0 0 48 48" width="26" height="26" fill="none" stroke="' + ORO + '" stroke-width="4" stroke-linecap="round"><rect x="10" y="21" width="28" height="20" rx="4"/><path d="M16 21v-6a8 8 0 0 1 16 0v6"/></svg><span>Zonas del modelo: datos sensibles, solo para el funcionario</span>', fun.c, { left: '28px', top: '366px', display: 'flex', alignItems: 'center', gap: '12px', font: '500 24px var(--fuente-texto)', color: ORO });

    const dPub = [].concat(P.verde.map(p => [dot(pub.sv, p, VER), 1.0 + R() * 1.2]), P.amarillo.map(p => [dot(pub.sv, p, AMA), 1.4 + R() * 1.0]), P.azul.map(p => [dot(pub.sv, p, AZU), 1.8 + R() * 0.8]));
    const dFun = [].concat(P.verde.map(p => [dot(fun.sv, p, VER), 4.0]), P.amarillo.map(p => [dot(fun.sv, p, AMA), 4.0]), P.azul.map(p => [dot(fun.sv, p, AZU), 4.0]));
    const dRojo = P.rojo.map((p, i) => [dot(fun.sv, p, ROJ), 4.8 + i * 0.12]);
    const dGris = P.gris.map((p, i) => [dot(fun.sv, p, GRI), 5.6 + i * 0.12]);
    const dHex = P.pasivo.map((p, i) => { const h = svg('path', { d: hexPath(p[0], p[1], 20), fill: VIO, stroke: '#0a0a0f', 'stroke-width': 3 }, fun.sv); h.style.transformBox = 'fill-box'; h.style.transformOrigin = 'center'; return [h, 6.4 + i * 0.15]; });

    // ---------- tarjetas de la derecha
    const RX = 1020, RW = 810, RH = 250;
    const card = (i, titulo) => { const c = A('tarjeta', null, raiz, { left: RX + 'px', top: (130 + i * (RH + 20)) + 'px', width: RW + 'px', height: RH + 'px', borderRadius: '26px' }); A('', titulo, c, { left: '28px', top: '20px', font: '800 36px var(--fuente-titulo)', letterSpacing: '-.02em', color: '#fff' }); return c; };
    // A) pasivos
    const cA = card(0, 'Pasivos · ranking riesgo × valor');
    const BARS = [['Pasivo 1', 0.94], ['Pasivo 2', 0.7], ['Pasivo 3', 0.44]];
    const bars = BARS.map((b, i) => {
      A('', b[0], cA, { left: '28px', top: (84 + i * 52) + 'px', width: '150px', font: '500 26px var(--fuente-texto)', color: 'var(--suave)' });
      A('', null, cA, { left: '190px', top: (86 + i * 52) + 'px', width: '580px', height: '34px', borderRadius: '10px', background: 'rgba(255,255,255,.06)' });
      return A('', null, cA, { left: '190px', top: (86 + i * 52) + 'px', width: (580 * b[1]) + 'px', height: '34px', borderRadius: '10px', background: 'linear-gradient(90deg,#7048e8,#9775fa)', transformOrigin: '0 50%' });
    });
    // B) denuncias
    const cB = card(1, 'Denuncias recibidas');
    const fila = A('', null, cB, { left: '28px', top: '84px', width: '754px', height: '140px', borderRadius: '18px', background: 'rgba(255,255,255,.05)' });
    A('', 'DEN-D41T17', fila, { left: '22px', top: '16px', font: '700 28px var(--fuente-num)', color: '#fff' });
    A('', 'Posible operación sin registro o licencia', fila, { left: '22px', top: '58px', font: '400 28px var(--fuente-texto)', color: 'var(--suave)' });
    const chip = A('', 'Por verificar', fila, { right: '22px', top: '14px', padding: '6px 20px', borderRadius: '999px', font: '700 26px var(--fuente-num)', background: 'rgba(245,183,0,.2)', color: AMA });
    const nota = A('', '', fila, { left: '22px', top: '98px', font: 'italic 400 26px var(--fuente-texto)', color: '#fff', whiteSpace: 'nowrap' });
    const NOTA = 'Nota de seguimiento: la escribe el funcionario';
    // C) detecciones revisadas
    const cC = card(2, 'Detecciones revisadas');
    const nodo = (x, txt, col) => A('', txt, cC, { left: x + 'px', top: '92px', width: '200px', height: '86px', borderRadius: '18px', border: '2px solid ' + col, background: 'rgba(255,255,255,.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', font: '700 30px var(--fuente-titulo)', color: '#fff' });
    const n1 = nodo(28, 'Visor', MORc), n2 = nodo(305, 'GeoJSON', ORO), n3 = nodo(582, 'App', VER);
    const flecha = x => A('', '<svg viewBox="0 0 80 24" width="70" height="24"><path d="M2 12H70M58 3l12 9-12 9" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>', cC, { left: x + 'px', top: '123px' });
    const f1 = flecha(228), f2 = flecha(505);
    A('', 'Solo las zonas que una persona marcó «Parece actividad minera». Se ven en mapa y en lista.', cC, { left: '28px', top: '192px', width: '754px', font: '400 25px/1.3 var(--fuente-texto)', color: 'var(--suave)' });

    const cards = [[cA, 7.4, 10.4], [cB, 10.4, 14.8], [cC, 14.8, 19.4]];

    return t => {
      ent(tit, an(t, 0.1, 0.9, E.out4), 25, 10);
      pon(aviso, { o: an(t, 0.6, 1.2) });
      ent(pub.c, an(t, 0.4, 1.3, E.out4), 50, 14);
      ent(fun.c, an(t, 3.6, 4.5, E.out4), 50, 14);
      pon(legPub, { o: an(t, 2.0, 2.6) });
      pon(legFun1, { o: an(t, 4.3, 4.9) }); pon(legFun2, { o: an(t, 6.0, 6.6) }); pon(candado, { o: an(t, 7.0, 7.6) });

      const pop = (list, base) => list.forEach(([d, t0]) => { const p = an(t, t0, t0 + 0.5, E.outBack); d.setAttribute('r', (base * p).toFixed(2)); });
      pop(dPub, 12); pop(dFun, 12); pop(dRojo, 14); pop(dGris, 13);
      dHex.forEach(([h, t0]) => { const p = an(t, t0, t0 + 0.6, E.outBack); h.style.transform = `scale(${p})`; h.style.opacity = clamp(p * 3); });
      // pasivos laten cuando se explican
      const lat = 1 + 0.18 * Math.sin(t * 6) * an(t, 7.4, 8.0) * (1 - an(t, 10.2, 10.6));
      dHex.forEach(([h, t0]) => { h.style.transform = `scale(${an(t, t0, t0 + 0.6, E.outBack) * lat})`; });

      cards.forEach(([c, t0, t1], i) => {
        const p = an(t, 1.4 + i * 0.3, 2.3 + i * 0.3, E.out4);
        ent(c, p, 40, 12);
        const act = an(t, t0, t0 + 0.3) * (1 - an(t, t1 - 0.2, t1 + 0.1));
        c.style.borderColor = `rgba(151,117,250,${0.14 + 0.7 * act})`;
      });
      bars.forEach((b, i) => pon(b, { sx: Math.max(0.0001, an(t, 7.6 + i * 0.25, 8.6 + i * 0.25, E.out4)), sy: 1 }));
      H.tipo(nota, NOTA, an(t, 12.8, 14.2));
      const cambio = t >= 12.6;
      chip.textContent = cambio ? 'En seguimiento' : 'Por verificar';
      chip.style.background = cambio ? 'rgba(77,171,247,.2)' : 'rgba(245,183,0,.2)';
      chip.style.color = cambio ? AZU : AMA;
      [[n1, 15.0], [f1, 15.5], [n2, 15.8], [f2, 16.3], [n3, 16.6]].forEach(([e, t0]) => { const p = an(t, t0, t0 + 0.5, E.out4); pon(e, { o: p, y: lerp(14, 0, p) }); });
    };
  },
});
