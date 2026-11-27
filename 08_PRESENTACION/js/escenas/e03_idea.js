/* Escena 3 - La idea (12 s). Cuatro piezas conectadas: satelite -> modelo -> revision (persona + IA) -> plataforma.
   Un pulso recorre la cadena y termina en el lema "Mirar. Verificar. Reportar." Todo es funcion pura de t. */
Pres.escena({
  id: 'idea', titulo: 'La idea', dur: 12,
  recursos: [],
  subs: [
    [0.5, 4.0, 'Cuatro piezas conectadas, de la imagen al reporte.'],
    [4.3, 8.2, 'El satélite mira, el modelo propone, personas e IA verifican, y cualquiera puede reportar.'],
    [8.7, 11.6, 'Mirar. Verificar. Reportar.'],
  ],
  montar(raiz, H) {
    const { el, svg, pon, an, E, lerp, clamp } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const MOR = '#7048e8', MORc = '#9775fa', NAR = '#d97757', NARc = '#f0a283', VER = '#2fb344', AZU = '#74c0fc';

    // iconos (viewBox 48 x 48)
    const IC = {
      satelite: c => `<g transform="rotate(-40 24 22)"><rect x="19" y="14" width="10" height="16" rx="2" stroke="${c}"/><rect x="3" y="16" width="12" height="12" rx="1.5" stroke="${c}"/><rect x="33" y="16" width="12" height="12" rx="1.5" stroke="${c}"/><path stroke="${c}" d="M15 22h4M29 22h4"/></g><path stroke="${c}" d="M20 37l-6 7M26 39v6M32 37l6 7"/>`,
      modelo: c => `<circle cx="24" cy="9" r="5" stroke="${c}"/><circle cx="10" cy="38" r="5" stroke="${c}"/><circle cx="38" cy="38" r="5" stroke="${c}"/><path stroke="${c}" d="M24 14v7M24 21L12.5 33M24 21l11.5 12"/>`,
      persona: c => `<circle cx="22" cy="17" r="8" stroke="${c}"/><path stroke="${c}" d="M6 44c0-9.500 7-15 16-15s16 5.500 16 15"/>`,
      claude: c => `<path fill="${c}" stroke="none" d="M24 3c1.800 12 7.500 18.500 21 21-13.500 2.500-19.200 9-21 21-1.800-12-7.500-18.500-21-21C16.500 21.500 22.200 15 24 3z"/>`,
      telefono: c => `<rect x="13" y="3" width="22" height="42" rx="5" stroke="${c}"/><path stroke="${c}" d="M21 39h6"/><path stroke="${c}" d="M24 11a6 6 0 0 1 6 6c0 5-6 10-6 10s-6-5-6-10a6 6 0 0 1 6-6z"/><circle cx="24" cy="17" r="2" fill="${c}" stroke="none"/>`,
    };
    const ico = (n, c, s) => `<svg viewBox="0 0 48 48" width="${s}" height="${s}" fill="none" stroke-width="2.600" stroke-linecap="round" stroke-linejoin="round" style="display:block">${IC[n](c)}</svg>`;

    // titulo
    const tit = A('titulo xs centro', 'Cuatro piezas, <span class="g-morado">un solo flujo</span>.', raiz, { left: '0', right: '0', top: '96px', fontSize: '68px' });

    // linea de conexion (debajo de las tarjetas)
    const CW = 360, CH = 430, TOP = 330, X0 = 135, PASO = 430;
    const cx = i => X0 + CW / 2 + i * PASO;
    const sv = svg('svg', { viewBox: '0 0 1920 1080', width: 1920, height: 1080 }, raiz); sv.style.cssText = 'position:absolute;left:0;top:0;overflow:visible;pointer-events:none';
    const defs = svg('defs', {}, sv);
    const gr = svg('linearGradient', { id: 'idea-grad', gradientUnits: 'userSpaceOnUse', x1: cx(0), y1: 0, x2: cx(3), y2: 0 }, defs);
    svg('stop', { offset: '0', 'stop-color': AZU }, gr); svg('stop', { offset: '.4', 'stop-color': MORc }, gr); svg('stop', { offset: '.7', 'stop-color': NAR }, gr); svg('stop', { offset: '1', 'stop-color': VER }, gr);
    const YL = TOP + CH / 2;
    const base = svg('path', { d: `M${cx(0)} ${YL}H${cx(3)}`, stroke: 'rgba(255,255,255,.14)', 'stroke-width': 6, 'stroke-linecap': 'round', fill: 'none', 'stroke-dasharray': '4 14' }, sv);
    const linea = svg('path', { d: `M${cx(0)} ${YL}H${cx(3)}`, stroke: 'url(#idea-grad)', 'stroke-width': 7, 'stroke-linecap': 'round', fill: 'none' }, sv);
    const cola = Array.from({ length: 6 }, (_, k) => svg('circle', { r: 15 - k * 2, fill: '#fff' }, sv));
    cola.forEach(c => { c.style.filter = 'drop-shadow(0 0 12px rgba(255,255,255,.9))'; });

    // tarjetas
    const D = [
      { n: '1', t: 'Mira', f: 'Imágenes del satélite cada pocos días', ic: 'satelite', col: AZU, bd: [116, 192, 252] },
      { n: '2', t: 'Propone', f: 'El modelo puntúa cada píxel', ic: 'modelo', col: MORc, bd: [112, 72, 232] },
      { n: '3', t: 'Verifica', f: 'Una persona decide; la IA opina', ic: 'persona', col: '#e8e8ee', bd: [217, 119, 87] },
      { n: '4', t: 'Reporta', f: 'Cualquiera puede avisar desde el celular', ic: 'telefono', col: '#8ce99a', bd: [47, 179, 68] },
    ];
    const tarjetas = D.map((d, i) => {
      const c = A('tarjeta', null, raiz, { left: (X0 + i * PASO) + 'px', top: TOP + 'px', width: CW + 'px', height: CH + 'px', background: 'linear-gradient(180deg,#171722,#0f0f17)', borderWidth: '2px', borderRadius: '30px' });
      A('', d.n, c, { left: '26px', top: '24px', width: '52px', height: '52px', borderRadius: '50%', background: 'rgba(255,255,255,.09)', font: '700 30px/52px var(--fuente-num)', textAlign: 'center', color: '#fff' });
      const ib = A('', ico(d.ic, d.col, 130), c, { left: '0', right: '0', top: '60px', height: '140px', display: 'grid', placeItems: 'center' });
      if (i === 2) A('', ico('claude', NARc, 54), c, { left: '218px', top: '58px', width: '54px', height: '54px' });
      A('', d.t, c, { left: '0', right: '0', top: '230px', textAlign: 'center', font: '800 50px/1 var(--fuente-titulo)', letterSpacing: '-.03em', color: '#fff' });
      A('', d.f, c, { left: '30px', right: '30px', top: '306px', textAlign: 'center', font: '400 30px/1.25 var(--fuente-texto)', color: 'var(--suave)' });
      c._d = d; return c;
    });

    // lema final
    const lema = A('titulo m centro', '<span style="color:' + AZU + '">Mirar.</span> <span class="g-naranja">Verificar.</span> <span class="g-verde">Reportar.</span>', raiz, { left: '0', right: '0', top: '830px', fontSize: '104px' });

    return t => {
      ent(tit, an(t, 0.15, 1.0, E.out4), 40, 14);
      const pl = an(t, 1.6, 4.6, E.io3);
      linea.style.strokeDasharray = '1000'; // se redefine con trazo
      H.trazo(linea, pl);
      pon(base, { o: an(t, 1.2, 2.0) });
      tarjetas.forEach((c, i) => {
        const p = an(t, 0.8 + 0.75 * i, 1.7 + 0.75 * i, E.out4);
        ent(c, p, 60, 16);
      });
      // pulso: viaja de la pieza 1 a la 4
      const u = an(t, 4.8, 8.0, E.io3);
      const x = lerp(cx(0), cx(3), u);
      cola.forEach((cc, k) => {
        const uk = an(t, 4.8 + 0.05 * k, 8.0 + 0.05 * k, E.io3);
        cc.setAttribute('cx', lerp(cx(0), cx(3), uk)); cc.setAttribute('cy', YL);
        cc.style.opacity = (1 - k / 7) * an(t, 4.7, 5.0) * (1 - an(t, 8.0, 8.5));
      });
      tarjetas.forEach((c, i) => {
        const pul = t > 4.7 ? 1 - clamp(Math.abs(x - cx(i)) / 260) : 0;
        const vist = t > 4.7 && x >= cx(i) - 4 ? 1 : 0;
        const bd = c._d.bd.join(',');
        c.style.borderColor = `rgba(${bd},${0.28 + 0.6 * Math.max(pul, vist * 0.4)})`;
        c.style.boxShadow = `0 30px 80px rgba(0,0,0,.45), 0 0 ${80 * pul}px rgba(${bd},${0.5 * pul})`;
      });
      // lema
      ent(lema, an(t, 8.6, 9.8, E.out4), 50, 18);
      const sal = an(t, 11.2, 11.9);
      pon(lema, { o: an(t, 8.6, 9.8, E.out4) * (1 - sal), y: lerp(50, 0, an(t, 8.6, 9.8, E.out4)), blur: lerp(18, 0, an(t, 8.6, 9.8, E.out4)) });
    };
  },
});
