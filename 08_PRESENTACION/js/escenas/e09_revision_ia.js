/* Escena 9 - La segunda opinion de Claude (22 s).
   Tres recortes -> Claude (naranja = todo lo que usa IA) -> opinion en el visor -> la persona decide.
   Capturas REALES del visor. Caso real zona B5929-013: la IA corrige al modelo (banco de arena, no suelo removido).
   Costo ~0,009 USD por zona, tope 2 USD (HECHOS.md). Es opinion de una IA, no verificacion de campo. Todo es funcion pura de t. */
Pres.escena({
  id: 'revision_ia', titulo: 'La segunda opinión', dur: 22,
  recursos: ['assets/capturas/e09_recorte_1.png', 'assets/capturas/e09_recorte_2.png', 'assets/capturas/e09_recorte_3.png',
    'assets/capturas/visor_pie_001_a.png', 'assets/capturas/visor_pie_013.png'],
  subs: [
    [0.5, 4.0, 'Claude mira tres recortes de la zona y da una segunda opinión.'],
    [4.2, 8.0, 'Cuesta unos 0,009 dólares por zona, con un tope de gasto de 2 dólares.'],
    [8.8, 11.6, 'Un clic pide la opinión desde el visor.'],
    [12.2, 16.8, 'Caso real: Claude dice que parece un banco de arena junto al río, no suelo removido.'],
    [17.0, 19.0, 'Es la opinión de una IA sobre una imagen de 20 metros: no verifica en campo.'],
    [19.4, 21.5, 'La revisión final es de una persona, y también enseña al modelo.'],
  ],
  montar(raiz, H) {
    const { el, svg, pon, an, E, lerp, clamp, img } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const vis = (e, o) => { e.style.visibility = o <= 0.002 ? 'hidden' : 'visible'; };
    const NAR = '#d97757', NARc = '#f0a283', MORc = '#9775fa';
    const claude = (c, s) => `<svg viewBox="0 0 48 48" width="${s}" height="${s}" style="display:block"><path fill="${c}" d="M24 3c1.8 12 7.5 18.5 21 21-13.5 2.5-19.2 9-21 21-1.8-12-7.5-18.5-21-21C16.5 21.5 22.2 15 24 3z"/></svg>`;

    const tit = A('titulo xs centro', 'La <span class="g-naranja">segunda opinión</span>', raiz, { left: '0', right: '0', top: '60px', fontSize: '64px' });

    // ---------- A) recortes -> Claude -> costo
    const capA = A('capa', null, raiz, { left: '0', top: '0', width: '1920px', height: '1080px' });
    const rec = [1, 2, 3].map((n, i) => {
      const c = A('', null, capA, { left: (110 + i * 330) + 'px', top: '230px', width: '300px', height: '320px', borderRadius: '20px', overflow: 'hidden', boxShadow: '0 30px 80px rgba(0,0,0,.55), 0 0 0 1px rgba(255,255,255,.15)', background: '#111' });
      const im = img('assets/capturas/e09_recorte_' + n + '.png', null, c); Object.assign(im.style, { position: 'absolute', left: '0', top: '0', width: '100%', height: '100%', objectFit: 'cover' });
      A('', 'Recorte ' + n, c, { left: '12px', bottom: '12px', padding: '4px 14px', borderRadius: '999px', background: 'rgba(10,10,15,.8)', font: '600 22px var(--fuente-num)', color: '#fff' });
      return c;
    });
    A('etiqueta', 'Lo que ve la IA', capA, { left: '110px', top: '186px', fontSize: '24px' });
    const flecha = svg('svg', { viewBox: '0 0 1920 1080', width: 1920, height: 1080 }, capA); flecha.style.cssText = 'position:absolute;left:0;top:0;overflow:visible';
    const fl = svg('path', { d: 'M1110 390 L1310 390', stroke: NAR, 'stroke-width': 8, 'stroke-linecap': 'round', fill: 'none' }, flecha);
    const fh = svg('path', { d: 'M1288 362 L1322 390 L1288 418', stroke: NAR, 'stroke-width': 8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', fill: 'none' }, flecha);
    const cl = A('tarjeta naranja', null, capA, { left: '1350px', top: '260px', width: '460px', height: '260px', borderRadius: '30px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '14px' });
    el('div', null, claude(NARc, 96), cl);
    el('div', null, 'Claude', cl).style.cssText = 'font:800 56px var(--fuente-titulo);letter-spacing:-.03em;color:#fff';
    el('div', null, 'IA · segunda opinión', cl).style.cssText = 'font:600 24px var(--fuente-num);letter-spacing:.14em;text-transform:uppercase;color:' + NARc;
    const costos = [['≈ 0,009 USD', 'por zona'], ['Tope de 2 USD', 'contador de gasto'], ['Con usuario y clave', 'solo las acciones con IA']].map((c, i) => {
      const k = A('tarjeta naranja', null, capA, { left: (110 + i * 600) + 'px', top: '650px', width: '560px', height: '200px', borderRadius: '26px' });
      A('num', c[0], k, { left: '34px', top: '40px', fontSize: '52px', color: '#fff' });
      A('', c[1], k, { left: '34px', top: '116px', font: '400 32px var(--fuente-texto)', color: 'var(--suave)' });
      return k;
    });

    // ---------- B) el visor real
    const capB = A('capa', null, raiz, { left: '0', top: '0', width: '1920px', height: '1080px' });
    const BX = 110, BW = 1700, BY = 250, BH13 = Math.round(BW * 845 / 2800), BHa = Math.round(BW * 334 / 2800);
    const cont = A('', null, capB, { left: BX + 'px', top: BY + 'px', width: BW + 'px', height: BH13 + 'px', borderRadius: '18px', overflow: 'hidden', background: '#fff', boxShadow: '0 40px 110px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.14)' });
    const pa = img('assets/capturas/visor_pie_001_a.png', null, cont); Object.assign(pa.style, { position: 'absolute', left: '0', top: '0', width: '100%' });
    const pb = img('assets/capturas/visor_pie_013.png', null, cont); Object.assign(pb.style, { position: 'absolute', left: '0', top: '0', width: '100%', opacity: 0 });
    const rect = (x0, x1, y0, y1, col) => A('', null, cont, { left: (x0 * 100) + '%', top: (y0 * 100) + '%', width: ((x1 - x0) * 100) + '%', height: ((y1 - y0) * 100) + '%', border: '5px solid ' + col, borderRadius: '14px', boxShadow: '0 0 30px ' + col, opacity: 0 });
    const hBtn = rect(0.337, 0.662, 0.0, 1.0, NAR); hBtn.style.top = '19%'; hBtn.style.height = '48%'; // boton "Pedir opinion"
    hBtn.style.top = (0.2 * BHa) + 'px'; hBtn.style.height = (0.26 * BHa) + 'px'; hBtn.style.border = '5px solid ' + NAR;
    const hVer = rect(0.343, 0.44, 0.085, 0.15, NAR);
    const hCl = rect(0.338, 0.662, 0.065, 0.975, NAR);
    const hPer = rect(0.665, 0.97, 0.065, 0.14, MORc);
    const cur = H.puntero(capB); const onda = H.onda(capB, 'rgba(240,162,131,.9)');
    const cap1 = A('', 'Caso real: <b style="color:#fff">la IA corrige al modelo</b>. Parece un banco de arena pegado al río, no suelo removido.', capB, { left: '110px', right: '110px', top: '800px', textAlign: 'center', font: '400 34px/1.3 var(--fuente-texto)', color: 'var(--suave)' });
    const cap2 = A('', 'Opinión de una IA sobre una imagen de 20 m: no es verificación de campo ni indica legalidad.', capB, { left: '110px', right: '110px', top: '890px', textAlign: 'center', font: '500 30px/1.3 var(--fuente-texto)', color: NARc });
    const cap3 = A('', 'Mi revisión: <b style="color:#fff">la persona decide</b>, y su decisión también le enseña al modelo.', capB, { left: '110px', right: '110px', top: '800px', textAlign: 'center', font: '400 34px/1.3 var(--fuente-texto)', color: 'var(--suave)' });

    return t => {
      ent(tit, an(t, 0.1, 0.9, E.out4), 25, 10);
      // A
      const oA = an(t, 0.1, 0.5) * (1 - an(t, 8.0, 8.7));
      pon(capA, { o: oA }); vis(capA, oA);
      rec.forEach((c, i) => ent(c, an(t, 0.7 + i * 0.25, 1.6 + i * 0.25, E.out4), 50, 12));
      pon(fl, { o: an(t, 2.4, 3.0) }); fh.style.opacity = an(t, 2.8, 3.2); fl.style.opacity = an(t, 2.4, 3.0);
      H.trazo(fl, an(t, 2.4, 3.2, E.out3));
      ent(cl, an(t, 2.8, 3.8, E.out4), 40, 12);
      costos.forEach((k, i) => ent(k, an(t, 4.2 + i * 0.5, 5.2 + i * 0.5, E.out4), 40, 12));

      // B
      const oB = an(t, 8.4, 9.0) * (1 - an(t, 21.3, 21.9));
      pon(capB, { o: oB }); vis(capB, oB);
      ent(cont, an(t, 8.6, 9.6, E.out4), 50, 14);
      cont.style.height = (lerp(BHa, BH13, an(t, 11.0, 12.2, E.io2))) + 'px';
      pa.style.opacity = 1 - an(t, 11.2, 11.9); pb.style.opacity = an(t, 11.2, 11.9);
      // puntero: llega al boton y hace clic
      const px = BX + 0.5 * BW, py = BY + 0.33 * BHa;
      const mv = an(t, 9.3, 10.4, E.io2);
      pon(cur, { x: lerp(BX + BW * 0.9, px, mv), y: lerp(BY + 160, py, mv) });
      cur.style.opacity = an(t, 9.2, 9.6) * (1 - an(t, 11.0, 11.4));
      H.ondaPaso(onda, px, py, clamp((t - 10.5) / 0.8));
      hBtn.style.opacity = an(t, 9.8, 10.3) * (1 - an(t, 11.0, 11.4));
      hVer.style.opacity = an(t, 12.6, 13.1) * (1 - an(t, 14.4, 14.9));
      hCl.style.opacity = an(t, 14.6, 15.1) * (1 - an(t, 17.0, 17.5));
      hPer.style.opacity = an(t, 19.4, 19.9) * (1 - an(t, 21.0, 21.3));
      const c1 = an(t, 12.8, 13.6, E.out4) * (1 - an(t, 19.0, 19.4));
      pon(cap1, { o: c1, y: lerp(14, 0, c1) });
      const c2 = an(t, 17.0, 17.8, E.out4) * (1 - an(t, 19.0, 19.4));
      pon(cap2, { o: c2, y: lerp(14, 0, c2) });
      const c3 = an(t, 19.4, 20.1, E.out4);
      pon(cap3, { o: c3, y: lerp(14, 0, c3) });
    };
  },
});
