/* Escena 7 - De puntos a zonas (20 s).
   Sobre el mapa de puntaje REAL del bloque (24,9 x 26,7 km) se quitan, regla por regla, los pixeles que no cuentan
   (agua, manchas < 5 ha, pocas fotos, entorno sin vegetacion). Lo que queda son 14 zonas, 497,9 ha: posible actividad minera, por verificar.
   Sin coordenadas geograficas (D-002). Todo es funcion pura de t. */
Pres.escena({
  id: 'zonas', titulo: 'De puntos a zonas', dur: 20,
  recursos: ['assets/real/bloque_puntaje.png', 'assets/capturas/e07_quita_agua.png', 'assets/capturas/e07_quita_chicas.png',
    'assets/capturas/e07_quita_fotos.png', 'assets/capturas/e07_quita_entorno.png', 'assets/capturas/e07_queda.png', 'assets/datos/zonas_pixel.json'],
  subs: [
    [0.5, 3.4, 'El modelo puntúa cada píxel del bloque: amarillo bajo, rojo alto.'],
    [3.6, 6.4, 'Primera regla: se descarta el agua.'],
    [6.6, 9.4, 'Segunda: las manchas de menos de 5 hectáreas.'],
    [9.6, 12.4, 'Tercera: se exigen al menos 7 fotos válidas del lugar.'],
    [12.6, 15.0, 'Cuarta: el entorno debe ser vegetación.'],
    [15.4, 19.3, 'Quedan 14 zonas, 497,9 hectáreas: posible actividad minera, por verificar.'],
  ],
  montar(raiz, H) {
    const { el, svg, pon, an, E, lerp, clamp, img, rec } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const MORc = '#9775fa', ORO = '#e0a82a', ROJ = '#ff6b3d';
    const fc = (v, d = 1) => v.toLocaleString('es', { minimumFractionDigits: d, maximumFractionDigits: d });

    const Z = rec('assets/datos/zonas_pixel.json') || {};
    const W = Z.ancho || 1352, HH = Z.alto || 1442;

    const tit = A('titulo xs', 'De puntos a <span class="g-morado">zonas</span>', raiz, { left: '100px', top: '34px', fontSize: '50px' });

    // ---------- mapa
    const MW = 840, MH = Math.round(MW * 2400 / 2250), MX = 100, MY = 110;
    const mapa = A('', null, raiz, { left: MX + 'px', top: MY + 'px', width: MW + 'px', height: MH + 'px', borderRadius: '20px', overflow: 'hidden', background: '#111', boxShadow: '0 40px 100px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.14)' });
    const cap = (src, st) => { const i = img(src, null, mapa); Object.assign(i.style, { position: 'absolute', left: '0', top: '0', width: '100%', height: '100%' }, st || {}); return i; };
    const base = cap('assets/real/bloque_puntaje.png');
    const L = ['agua', 'chicas', 'fotos', 'entorno'].map(k => cap('assets/capturas/e07_quita_' + k + '.png', { filter: 'brightness(0)', opacity: 0 }));
    const queda = cap('assets/capturas/e07_queda.png', { opacity: 0 });
    const sv = svg('svg', { viewBox: `0 0 ${W} ${HH}`, width: MW, height: MH }, mapa); sv.style.cssText = 'position:absolute;left:0;top:0';
    const contornos = [];
    (Z.zonas || []).forEach(z => {
      let d = '';
      (z.anillos || []).forEach(r => { if (Array.isArray(r) && Array.isArray(r[0])) r.forEach((p, i) => { d += (i ? 'L' : 'M') + p[0] + ' ' + p[1]; }); d += 'Z'; });
      if (d) contornos.push(svg('path', { d, fill: 'rgba(255,255,255,.12)', stroke: '#fff', 'stroke-width': 7, 'stroke-linejoin': 'round' }, sv));
    });
    const etMapa = A('', 'Bloque real analizado · sin coordenadas', raiz, { left: MX + 'px', top: (MY + MH + 12) + 'px', font: '400 24px var(--fuente-texto)', color: 'var(--suave)' });
    const leyenda = A('', '<span style="color:#ffd43b">▮</span> puntaje bajo &nbsp; <span style="color:#ff3d00">▮</span> alto &nbsp; <span style="color:#000;background:#fff;padding:0 6px">▮</span> descartado', mapa, { left: '18px', top: '16px', padding: '8px 16px', borderRadius: '12px', background: 'rgba(10,10,15,.8)', font: '500 22px var(--fuente-texto)', color: '#fff', whiteSpace: 'nowrap' });

    // ---------- reglas
    const REG = [
      ['1', 'Sin agua', 'NDWI mayor que 0 = agua'],
      ['2', 'Al menos 5 ha', 'las manchas chicas no cuentan'],
      ['3', '7 fotos válidas o más', 'mediana de las imágenes del lugar'],
      ['4', 'Entorno con vegetación', 'NDVI del entorno de 0,5 o más'],
    ];
    const RX = 1010, RW = 810, RH = 128;
    const cards = REG.map((r, i) => {
      const c = A('tarjeta', null, raiz, { left: RX + 'px', top: (130 + i * (RH + 22)) + 'px', width: RW + 'px', height: RH + 'px', borderRadius: '24px' });
      const n = A('num', r[0], c, { left: '26px', top: '30px', width: '68px', height: '68px', borderRadius: '50%', background: 'rgba(255,255,255,.09)', textAlign: 'center', font: '700 36px/68px var(--fuente-num)', color: '#fff' });
      A('', r[1], c, { left: '120px', top: '22px', font: '800 36px/1.1 var(--fuente-titulo)', letterSpacing: '-.02em', color: '#fff' });
      A('', r[2], c, { left: '120px', top: '76px', font: '400 28px var(--fuente-texto)', color: 'var(--suave)' });
      const ok = A('', 'descartado', c, { right: '26px', top: '44px', padding: '6px 18px', borderRadius: '999px', background: 'rgba(255,255,255,.1)', font: '600 24px var(--fuente-num)', color: '#fff', letterSpacing: '.06em', textTransform: 'uppercase' });
      c._n = n; c._ok = ok; return c;
    });
    // resultado
    const res = A('tarjeta morada', null, raiz, { left: RX + 'px', top: '130px', width: RW + 'px', height: '630px', borderRadius: '28px' });
    A('etiqueta', 'Lo que queda', res, { left: '44px', top: '36px', fontSize: '26px' });
    const nZ = A('num', '0', res, { left: '44px', top: '100px', fontSize: '210px', lineHeight: '1', color: '#fff' });
    A('', 'zonas por verificar', res, { left: '44px', top: '330px', font: '700 46px var(--fuente-titulo)', color: MORc });
    const nH = A('num', '0', res, { left: '44px', top: '410px', fontSize: '100px', lineHeight: '1', color: ORO });
    A('', 'en total, de <b style="color:#fff">posible actividad minera</b>. Todavía nadie las revisó.', res, { left: '44px', top: '530px', width: '720px', font: '400 28px/1.35 var(--fuente-texto)', color: 'var(--suave)' });

    return t => {
      ent(tit, an(t, 0.1, 0.8, E.out4), 20, 10);
      ent(mapa, an(t, 0.3, 1.3, E.out4), 50, 16);
      pon(etMapa, { o: an(t, 1.0, 1.6) });
      base.style.filter = `brightness(${lerp(1, 0.38, an(t, 14.6, 15.6))}) saturate(${lerp(1, 0.4, an(t, 14.6, 15.6))})`;
      leyenda.style.opacity = an(t, 1.2, 1.8) * (1 - an(t, 14.4, 15.0));

      // reglas: cada una descarta su capa
      const T0 = [3.5, 6.5, 9.5, 12.5];
      const tarjetasFuera = 1 - an(t, 14.6, 15.4);
      cards.forEach((c, i) => {
        const p = an(t, 0.9 + i * 0.12, 1.7 + i * 0.12, E.out4);
        const act = an(t, T0[i] - 0.1, T0[i] + 0.4);
        const hecho = an(t, T0[i] + 2.4, T0[i] + 2.9);
        ent(c, p * tarjetasFuera, 40, 12);
        c.style.borderColor = `rgba(151,117,250,${0.15 + 0.7 * act * (1 - hecho * 0.6)})`;
        c._ok.style.opacity = an(t, T0[i] + 0.6, T0[i] + 1.1);
        c._n.style.background = act > 0.5 ? MORc : 'rgba(255,255,255,.09)';
        L[i].style.opacity = 0.9 * an(t, T0[i], T0[i] + 1.2, E.io2);
      });
      c_vis(cards, tarjetasFuera);

      // resultado
      const r = an(t, 15.0, 15.9, E.out4);
      ent(res, r, 50, 14); res.style.visibility = r <= 0.002 ? 'hidden' : 'visible';
      queda.style.opacity = an(t, 14.6, 15.6);
      contornos.forEach((c, i) => { c.style.opacity = an(t, 16.0 + i * 0.05, 16.8 + i * 0.05); });
      H.num(nZ, 14, an(t, 15.4, 17.0, E.out3), 0);
      nH.textContent = fc(497.9 * an(t, 15.6, 17.4, E.out3), 1) + ' ha';

      function c_vis(cs, o) { cs.forEach(c => { c.style.visibility = o <= 0.002 ? 'hidden' : 'visible'; }); }
    };
  },
});
