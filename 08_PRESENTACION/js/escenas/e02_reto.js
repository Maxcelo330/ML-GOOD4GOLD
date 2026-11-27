/* Escena 2 - El reto (15 s).
   1) un territorio enorme: recuadro esquematico sobre la imagen real oscurecida, rotulos de los 4 pueblos, contador 13.035 km2
   2) la camara baja hacia la imagen real y aparecen las dos preguntas (donde hay actividad minera / como lo ve la comunidad)
   3) los dos retos del desafio en dos tarjetas: Encontrar (satelite) y Verificar, controlar y reportar (plataforma). */
Pres.escena({
  id: 'reto', titulo: 'El reto', dur: 15,
  recursos: ['assets/real/bloque_natural.jpg'],
  subs: [[0.5, 4.6, 'Unos 13.000 kilómetros cuadrados en el norte de La Paz.'],
    [5.0, 8.6, '¿Dónde hay posible actividad minera? Nadie puede recorrerlo todo a ojo.'],
    [8.8, 10.5, 'Y, ¿cómo lo ve la comunidad?'],
    [10.9, 14.5, 'Dos retos: encontrar desde el satélite, y verificar y reportar en una plataforma.']],
  montar(raiz, H) {
    const { el, svg, pon, an, E, lerp, trazo, num } = H;
    const W = 1920, HH = 1080, oro = '#e0a82a';
    const sombra = '0 4px 40px rgba(0,0,0,.8)';
    // marco esquematico: x, y, ancho, alto
    const FX = 140, FY = 370, FW = 960, FH = 510;

    /* ---- imagen real (ventana que se expande desde el recuadro) ---- */
    const ventana = el('div', 'capa', null, raiz); ventana.style.overflow = 'hidden';
    const foto = H.img('assets/real/bloque_natural.jpg', 'img-llena', ventana);
    Object.assign(foto.style, { width: '2300px', height: 'auto', left: '-720px', top: '-1180px', transformOrigin: '55% 62%' });
    const oscuro = el('div', 'capa', null, ventana); oscuro.style.background = 'rgba(5,6,12,1)';
    const esc = el('div', 'capa', null, ventana);            // barrido de busqueda
    const linea = el('div', 'abs', null, esc); Object.assign(linea.style, { left: 0, top: 0, width: '1920px', height: '4px', background: 'linear-gradient(90deg, transparent, #ffd978 20%, #ffd978 80%, transparent)', boxShadow: '0 0 60px 12px rgba(224,168,42,.45)' });
    const velo = el('div', 'capa', null, ventana);
    velo.style.background = 'radial-gradient(1300px 800px at 50% 50%, rgba(5,5,7,.35), rgba(5,5,7,.85))';

    /* ---- capa esquematica del primer momento ---- */
    const esq = el('div', 'capa', null, raiz);
    const h1 = el('div', 'abs centro titulo', null, esq);
    Object.assign(h1.style, { left: 0, right: 0, top: '62px', fontSize: '100px' });
    const l1 = el('div', null, 'Un territorio <span class="g-oro">enorme.</span>', h1), l2 = el('div', null, 'Una mirada que no alcanza.', h1);
    l2.style.color = '#a1a1aa'; l2.style.fontWeight = '700';
    const sv = svg('svg', { viewBox: `0 0 ${W} ${HH}`, width: W, height: HH }, esq); sv.style.cssText = 'position:absolute;left:0;top:0;overflow:visible';
    const marco = svg('path', { d: `M${FX} ${FY}H${FX + FW}V${FY + FH}H${FX}Z`, fill: 'none', stroke: oro, 'stroke-width': 4, 'stroke-linejoin': 'round' }, sv);
    const grids = [];
    for (let i = 1; i < 4; i++) grids.push(svg('line', { x1: FX + FW * i / 4, y1: FY, x2: FX + FW * i / 4, y2: FY + FH, stroke: 'rgba(255,255,255,.16)', 'stroke-width': 1.5, 'stroke-dasharray': '6 10' }, sv));
    for (let i = 1; i < 3; i++) grids.push(svg('line', { x1: FX, y1: FY + FH * i / 3, x2: FX + FW, y2: FY + FH * i / 3, stroke: 'rgba(255,255,255,.16)', 'stroke-width': 1.5, 'stroke-dasharray': '6 10' }, sv));
    const pueblos = [['Mapiri', .2, .2, 'der'], ['Tipuani', .4, .5, 'der'], ['Guanay', .6, .72, 'der'], ['Teoponte', .8, .36, 'izq']].map(([n, fx, fy, lado]) => {
      const g = el('div', 'abs', null, esq); Object.assign(g.style, { left: (FX + FW * fx) + 'px', top: (FY + FH * fy) + 'px', whiteSpace: 'nowrap' });
      const d = el('div', null, null, g); Object.assign(d.style, { position: 'absolute', left: '-11px', top: '-11px', width: '22px', height: '22px', borderRadius: '50%', background: oro, boxShadow: '0 0 0 6px rgba(224,168,42,.3), 0 0 30px rgba(224,168,42,.8)' });
      const tx = el('div', 'num', n, g); Object.assign(tx.style, { position: 'absolute', top: '-24px', fontSize: '38px', color: '#fff', textShadow: sombra, [lado === 'der' ? 'left' : 'right']: '26px', fontWeight: 600 });
      return g;
    });
    const nota = el('div', 'abs etiqueta', 'Ubicación esquemática, no a escala', esq); Object.assign(nota.style, { left: FX + 'px', top: (FY + FH + 22) + 'px', fontSize: '22px', color: '#8a8a97' });
    const cont = el('div', 'abs', null, esq); Object.assign(cont.style, { left: '1190px', top: '420px' });
    el('div', 'etiqueta', 'Norte de La Paz', cont).style.marginBottom = '10px';
    const nCont = el('div', 'num g-oro', '0', cont); Object.assign(nCont.style, { fontSize: '210px', lineHeight: 1, letterSpacing: '-0.03em' });
    el('div', 'sub', '<b>km²</b> de zona piloto', cont).style.cssText = 'font-size:48px;margin-top:6px';

    /* ---- preguntas ---- */
    const q1 = el('div', 'abs centro titulo', 'Dónde hay <span class="g-oro">actividad minera</span>?', raiz);
    q1.innerHTML = '¿Dónde hay<br><span class="g-oro">actividad minera?</span>';
    Object.assign(q1.style, { left: 0, right: 0, top: '320px', fontSize: '124px', textShadow: sombra });
    const q2 = el('div', 'abs centro titulo', 'Y, ¿cómo lo ve<br><span class="g-morado">la comunidad?</span>', raiz);
    Object.assign(q2.style, { left: 0, right: 0, top: '520px', fontSize: '112px', textShadow: sombra });
    // telefono con pin (anticipa la plataforma de reporte)
    const tel = el('div', 'abs', null, raiz); Object.assign(tel.style, { left: '840px', top: '120px', width: '240px', height: '360px' });
    tel.innerHTML = `<svg viewBox="0 0 160 240" width="240" height="360" style="overflow:visible">
      <rect x="10" y="6" width="140" height="228" rx="26" fill="rgba(20,18,40,.85)" stroke="#9775fa" stroke-width="5"/>
      <rect x="62" y="16" width="36" height="8" rx="4" fill="#9775fa" opacity=".7"/>
      <path d="M80 160c-24-30-34-48-34-66a34 34 0 0 1 68 0c0 18-10 36-34 66z" fill="#2f80ed" stroke="#fff" stroke-width="5" stroke-linejoin="round"/>
      <circle cx="80" cy="94" r="12" fill="#fff"/>
      <ellipse cx="80" cy="184" rx="30" ry="7" fill="rgba(47,128,237,.5)"/></svg>`;

    /* ---- los dos retos ---- */
    const etR = el('div', 'abs centro etiqueta', 'Los dos retos del proyecto', raiz); Object.assign(etR.style, { left: 0, right: 0, top: '110px', fontSize: '34px' });
    const icoSat = `<svg viewBox="0 0 300 160" width="190" height="100" style="overflow:visible">
      <rect x="8" y="48" width="98" height="64" rx="4" fill="#2b4f9e" stroke="#9ab6ee" stroke-width="3"/><rect x="194" y="48" width="98" height="64" rx="4" fill="#2b4f9e" stroke="#9ab6ee" stroke-width="3"/>
      <g stroke="rgba(255,255,255,.4)" stroke-width="2"><path d="M32 48V112M57 48V112M82 48V112M218 48V112M243 48V112M268 48V112M8 80H106M194 80H292"/></g>
      <rect x="120" y="42" width="60" height="76" rx="12" fill="#e0b84f" stroke="#fff3c9" stroke-width="3"/><line x1="150" y1="42" x2="150" y2="18" stroke="#ddd" stroke-width="4"/><circle cx="150" cy="14" r="7" fill="#ffd978"/><circle cx="150" cy="118" r="12" fill="#14110a" stroke="#ffe29a" stroke-width="4"/></svg>`;
    const icoTel = `<svg viewBox="0 0 160 240" width="76" height="114" style="overflow:visible">
      <rect x="10" y="6" width="140" height="228" rx="26" fill="rgba(20,18,40,.85)" stroke="#9775fa" stroke-width="8"/>
      <path d="M80 160c-24-30-34-48-34-66a34 34 0 0 1 68 0c0 18-10 36-34 66z" fill="#2f80ed" stroke="#fff" stroke-width="7" stroke-linejoin="round"/><circle cx="80" cy="94" r="12" fill="#fff"/></svg>`;
    const tarjeta = (x, clase, num_, ico, titulo, sub) => {
      const c = el('div', 'abs tarjeta ' + clase, null, raiz); Object.assign(c.style, { left: x + 'px', top: '220px', width: '800px', height: '600px' });
      const n = el('div', 'num', num_, c); Object.assign(n.style, { position: 'absolute', left: '50px', top: '36px', fontSize: '84px', color: clase ? '#b197fc' : oro, opacity: .95 });
      const i = el('div', null, ico, c); Object.assign(i.style, { position: 'absolute', right: '50px', top: '40px' });
      const t = el('div', 'titulo', titulo, c); Object.assign(t.style, { position: 'absolute', left: '50px', right: '50px', top: '215px', fontSize: '72px', lineHeight: 1.08 });
      const s = el('div', 'sub', sub, c); Object.assign(s.style, { position: 'absolute', left: '50px', right: '50px', top: '420px', fontSize: '40px' });
      return c;
    };
    const c1 = tarjeta(120, '', '1', icoSat, '<span class="g-oro">Encontrar</span>', 'posible actividad minera, con imágenes de satélite');
    const c2 = tarjeta(1000, 'morada', '2', icoTel, '<span class="g-morado">Verificar, controlar y reportar</span>', 'en una plataforma web, para todos');

    /* ---- actualizar(t) ---- */
    return t => {
      // ventana: del recuadro a pantalla completa
      const ex = an(t, 4.9, 6.4, E.io3);
      ventana.style.clipPath = `inset(${lerp(FY, 0, ex)}px ${lerp(W - FX - FW, 0, ex)}px ${lerp(HH - FY - FH, 0, ex)}px ${lerp(FX, 0, ex)}px round ${lerp(18, 0, ex)}px)`;
      ventana.style.opacity = an(t, 2.2, 3.2);
      pon(foto, { s: lerp(1.0, 1.32, an(t, 2, 15, E.lineal)) + lerp(0, 0.1, ex), x: lerp(0, -40, an(t, 4.9, 15, E.lineal)) });
      oscuro.style.opacity = lerp(.55, 0, an(t, 4.6, 6.4)) + lerp(0, .78, an(t, 10.5, 11.4));
      velo.style.opacity = an(t, 4.9, 6.2);
      // barrido de busqueda durante la primera pregunta
      const sc = an(t, 6.0, 8.4, E.io2);
      linea.style.top = lerp(-20, 1100, sc) + 'px'; linea.style.opacity = sc > 0 && sc < 1 ? 1 : 0;

      // esquema
      esq.style.opacity = 1 - an(t, 4.5, 5.5);
      esq.style.display = t > 5.6 ? 'none' : '';
      const a1 = an(t, 0.3, 1.5, E.out4), a2 = an(t, 1.0, 2.2, E.out4);
      pon(l1, { o: a1, y: lerp(50, 0, a1), blur: lerp(14, 0, a1) }); pon(l2, { o: a2, y: lerp(50, 0, a2), blur: lerp(14, 0, a2) });
      trazo(marco, an(t, 1.6, 3.2, E.io3)); marco.style.opacity = 1;
      grids.forEach((g, i) => g.setAttribute('opacity', an(t, 2.6 + i * 0.08, 3.4 + i * 0.08)));
      pueblos.forEach((g, i) => { const a = an(t, 3.0 + i * 0.28, 3.8 + i * 0.28, E.out4); pon(g, { o: a, s: lerp(.8, 1, a) }); });
      pon(nota, { o: an(t, 3.6, 4.2) });
      const ca = an(t, 2.8, 3.6, E.out4); pon(cont, { o: ca, x: lerp(50, 0, ca) });
      num(nCont, 13035, an(t, 2.9, 4.5, E.out3), 0, '');

      // preguntas
      const qa = an(t, 6.0, 6.9, E.out4), qb = an(t, 8.0, 8.5);
      pon(q1, { o: qa * (1 - qb), y: lerp(50, 0, qa) + lerp(0, -30, qb), blur: lerp(16, 0, qa) + lerp(0, 10, qb) });
      const qc = an(t, 8.8, 9.7, E.out4), qd = an(t, 10.0, 10.5);
      pon(q2, { o: qc * (1 - qd), y: lerp(50, 0, qc) + lerp(0, -30, qd), blur: lerp(16, 0, qc) + lerp(0, 10, qd) });
      const ta = an(t, 8.9, 9.8, E.outBack);
      pon(tel, { o: ta * (1 - qd), y: lerp(60, 0, ta) + lerp(0, -30, qd), s: lerp(.7, 1, ta) });

      // retos
      pon(etR, { o: an(t, 10.9, 11.6) });
      [c1, c2].forEach((c, i) => { const a = an(t, 11.0 + i * 0.5, 12.0 + i * 0.5, E.out4); pon(c, { o: a, y: lerp(80, 0, a), blur: lerp(14, 0, a), s: lerp(.96, 1, a) }); });
    };
  },
});
