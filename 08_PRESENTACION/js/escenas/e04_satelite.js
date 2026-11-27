/* Escena 4 - Como ve el satelite (22 s).
   1) satelite en orbita + haz hacia el bloque  2) imagen real a pantalla completa, cortina natural / falso color
   3) zoom profundo hasta la rejilla de pixeles de 20 x 20 m  4) las nubes: pila de fotos -> UNA imagen limpia (mediana).
   Imagenes propias (herramientas/preparar_e04_nubes.py): satelite_nat.png (nativa, para el zoom), satelite_nube_1..4.jpg y satelite_nube_mediana.jpg. */
Pres.escena({
  id: 'satelite', titulo: 'Cómo ve el satélite', dur: 22,
  recursos: ['assets/real/bloque_natural.jpg', 'assets/real/bloque_falso.jpg', 'assets/capturas/satelite_nat.png',
    'assets/real/px_bosque.png', 'assets/real/px_suelo_removido.png',
    'assets/capturas/satelite_nube_1.jpg', 'assets/capturas/satelite_nube_2.jpg', 'assets/capturas/satelite_nube_3.jpg', 'assets/capturas/satelite_nube_4.jpg', 'assets/capturas/satelite_nube_mediana.jpg'],
  subs: [[0.5, 4.6, 'Sentinel-2 es un satélite gratuito que pasa cada pocos días.'],
    [4.8, 7.2, 'Estas son sus imágenes del norte de La Paz.'],
    [7.3, 10.7, 'Ve más colores que el ojo: el suelo removido se ve rosado.'],
    [10.9, 13.8, 'Si hacemos zoom, la imagen es una rejilla de cuadros.'],
    [13.9, 16.0, 'Cada cuadro, cada píxel, mide 20 por 20 metros.'],
    [16.4, 19.2, 'Las nubes tapan partes de cada foto.'],
    [19.3, 21.8, 'Con la mediana de varias fotos de mayo a septiembre, las nubes desaparecen.']],
  montar(raiz, H) {
    const { el, svg, pon, an, E, lerp, rng } = H;
    const W = 1920, HH = 1080, NW = 1352;              // tamano del escenario y ancho nativo de la imagen (1 pixel = 1 pixel del analisis)
    const oro = '#e0a82a';
    const R = u => H.rec(u);
    const jn = R('assets/real/bloque_natural.jpg'), jf = R('assets/real/bloque_falso.jpg'), nn = R('assets/capturas/satelite_nat.png');
    const sombraTxt = '0 4px 30px rgba(0,0,0,.7)';

    /* ============================ capa 1: espacio, Tierra, satelite, haz ============================ */
    const cielo = el('div', 'capa', null, raiz);
    const r = rng(5);
    const sv = svg('svg', { viewBox: `0 0 ${W} ${HH}`, width: W, height: HH }, cielo);
    sv.style.cssText = 'position:absolute;left:0;top:0;overflow:visible';
    const defs = svg('defs', {}, sv);
    const gTierra = svg('radialGradient', { id: 'sat-tierra', cx: '50%', cy: '0%', r: '70%' }, defs);
    svg('stop', { offset: '0', 'stop-color': '#12304d' }, gTierra); svg('stop', { offset: '1', 'stop-color': '#050a14' }, gTierra);
    const gHaz = svg('linearGradient', { id: 'sat-haz', gradientUnits: 'userSpaceOnUse', x1: 0, y1: 330, x2: 0, y2: 730 }, defs);
    svg('stop', { offset: '0', 'stop-color': '#ffd978', 'stop-opacity': .75 }, gHaz); svg('stop', { offset: '1', 'stop-color': '#e0a82a', 'stop-opacity': .12 }, gHaz);
    const gBorde = svg('linearGradient', { id: 'sat-borde', x1: 0, y1: 0, x2: 1, y2: 0 }, defs);
    svg('stop', { offset: '0', 'stop-color': '#4f8fd6', 'stop-opacity': 0 }, gBorde); svg('stop', { offset: '.5', 'stop-color': '#8fc4ff', 'stop-opacity': .9 }, gBorde); svg('stop', { offset: '1', 'stop-color': '#4f8fd6', 'stop-opacity': 0 }, gBorde);
    const estrellas = [];
    for (let i = 0; i < 110; i++) { const x = r() * W, y = r() * 640, c = svg('circle', { cx: x, cy: y, r: 0.8 + r() * 1.6, fill: '#fff' }, sv); estrellas.push([c, 0.25 + r() * 0.6, r() * 6]); }
    const orbita = svg('ellipse', { cx: 1300, cy: 330, rx: 380, ry: 110, fill: 'none', stroke: 'rgba(255,255,255,.22)', 'stroke-width': 2, 'stroke-dasharray': '4 14' }, sv);
    const tierra = svg('g', {}, sv);
    svg('circle', { cx: 960, cy: 1790, r: 1100, fill: 'url(#sat-tierra)' }, tierra);
    svg('circle', { cx: 960, cy: 1790, r: 1100, fill: 'none', stroke: '#7db8ff', 'stroke-opacity': .22, 'stroke-width': 26, style: 'filter:blur(14px)' }, tierra);
    svg('circle', { cx: 960, cy: 1790, r: 1100, fill: 'none', stroke: 'url(#sat-borde)', 'stroke-width': 3 }, tierra);
    // paralelos y meridianos muy suaves sobre la Tierra
    for (let i = 1; i <= 4; i++) svg('ellipse', { cx: 960, cy: 1790, rx: 1100 - i * 120, ry: 1100, fill: 'none', stroke: 'rgba(125,184,255,.07)', 'stroke-width': 2 }, tierra);
    const haz = svg('polygon', { fill: 'url(#sat-haz)' }, sv);
    const hazN = svg('line', { stroke: '#ffe29a', 'stroke-width': 2, 'stroke-opacity': .8 }, sv);
    const huella = svg('rect', { x: 1060, y: 724, width: 240, height: 150, rx: 14, fill: 'none', stroke: oro, 'stroke-width': 4 }, sv);
    const sat = el('div', null, null, cielo);
    sat.style.cssText = 'position:absolute;left:0;top:0;width:300px;height:160px';
    sat.innerHTML = `<svg viewBox="0 0 300 160" width="300" height="160" style="overflow:visible">
      <defs><linearGradient id="sat-cuerpo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f2d27a"/><stop offset="1" stop-color="#9b7420"/></linearGradient>
      <linearGradient id="sat-panel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3a6ac4"/><stop offset="1" stop-color="#1c3470"/></linearGradient></defs>
      <line x1="105" y1="80" x2="120" y2="80" stroke="#aaa" stroke-width="5"/><line x1="180" y1="80" x2="195" y2="80" stroke="#aaa" stroke-width="5"/>
      <rect x="8" y="48" width="98" height="64" rx="4" fill="url(#sat-panel)" stroke="#9ab6ee" stroke-width="2"/><rect x="194" y="48" width="98" height="64" rx="4" fill="url(#sat-panel)" stroke="#9ab6ee" stroke-width="2"/>
      <g stroke="rgba(255,255,255,.4)" stroke-width="1.5"><path d="M32 48V112M57 48V112M82 48V112M218 48V112M243 48V112M268 48V112M8 80H106M194 80H292"/></g>
      <rect x="120" y="42" width="60" height="76" rx="12" fill="url(#sat-cuerpo)" stroke="#fff3c9" stroke-opacity=".7" stroke-width="2"/>
      <line x1="150" y1="42" x2="150" y2="18" stroke="#ddd" stroke-width="3"/><circle cx="150" cy="14" r="6" fill="#ffd978"/>
      <circle cx="150" cy="118" r="12" fill="#14110a" stroke="#ffe29a" stroke-width="3"/><circle cx="150" cy="118" r="5" fill="#ffd978"/></svg>`;
    const tTit = el('div', 'abs', '<div class="etiqueta" style="margin-bottom:26px">Copernicus · el ojo en el cielo</div><div class="titulo m g-blanco">Sentinel-2</div>', cielo);
    Object.assign(tTit.style, { left: '120px', top: '190px', textShadow: sombraTxt });
    const pil = ['Gratuito', 'Cada pocos días'].map((x, i) => { const p = el('div', 'pastilla', x, cielo); Object.assign(p.style, { position: 'absolute', left: '120px', top: (420 + i * 84) + 'px', fontSize: '34px', padding: '12px 30px', borderColor: 'rgba(224,168,42,.5)', background: 'rgba(224,168,42,.12)' }); return p; });

    /* ============================ capa 2: lienzo con la imagen real (camara) ============================ */
    const marco = el('div', 'capa', null, raiz);
    marco.style.cssText += ';overflow:hidden';
    const cv = el('canvas', null, null, marco); cv.width = W; cv.height = HH; cv.style.cssText = 'position:absolute;left:0;top:0;width:1920px;height:1080px';
    const ctx = cv.getContext('2d');
    const velo = el('div', 'capa', null, raiz); velo.style.background = 'radial-gradient(1500px 900px at 50% 50%, transparent 55%, rgba(0,0,0,.55))';
    const velo2 = el('div', 'abs', null, raiz); Object.assign(velo2.style, { left: 0, top: 0, width: '1920px', height: '260px', background: 'linear-gradient(180deg, rgba(0,0,0,.6), transparent)' });
    const pill = (txt, lado, col) => { const p = el('div', 'pastilla', txt, raiz); Object.assign(p.style, { position: 'absolute', top: '58px', fontSize: '34px', padding: '14px 32px', background: 'rgba(5,5,7,.6)', backdropFilter: 'blur(10px)', borderColor: col }); p.style[lado] = '70px'; return p; };
    const pN = pill('Color natural · lo que ve el ojo', 'right', 'rgba(255,255,255,.35)');
    const pF = pill('Falso color · el suelo removido se ve <b style="color:#ff9ec7">rosado</b>', 'left', 'rgba(255,158,199,.55)');

    // panel del zoom
    const panel = el('div', 'abs', null, raiz); Object.assign(panel.style, { left: 0, top: 0, width: '1150px', height: '1080px', background: 'linear-gradient(90deg, rgba(5,5,7,.95) 0, rgba(5,5,7,.86) 55%, transparent)' });
    const pT1 = el('div', 'abs titulo m g-blanco', '1 píxel', raiz); Object.assign(pT1.style, { left: '110px', top: '120px', textShadow: sombraTxt });
    const pT2 = el('div', 'abs titulo m g-oro', '20 × 20 m', raiz); Object.assign(pT2.style, { left: '110px', top: '240px' });
    const pT3 = el('div', 'abs sub', 'como una cancha pequeña', raiz); Object.assign(pT3.style, { left: '114px', top: '378px', fontSize: '46px' });
    const tiles = [['assets/real/px_bosque.png', 'Bosque', 110], ['assets/real/px_suelo_removido.png', 'Suelo removido', 400]].map(([u, nombre, x]) => {
      const d = el('div', 'abs', null, raiz); Object.assign(d.style, { left: x + 'px', top: '560px', width: '250px' });
      const c = el('div', null, null, d); Object.assign(c.style, { width: '250px', height: '250px', borderRadius: '16px', overflow: 'hidden', position: 'relative', boxShadow: '0 20px 60px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.18)' });
      const im = H.img(u, null, c); Object.assign(im.style, { width: '250px', height: '250px', imageRendering: 'pixelated', display: 'block' });
      const g = el('div', null, null, c); g.style.cssText = 'position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.22) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.22) 1px,transparent 1px);background-size:10px 10px';
      el('div', 'etiqueta', nombre, d).style.cssText = 'margin-top:16px;font-size:26px;letter-spacing:.12em;color:#f5f5f7';
      return d;
    });
    const pT4 = el('div', 'abs sub s', 'Cada cuadro guarda sus propios colores.', raiz); Object.assign(pT4.style, { left: '110px', top: '890px', fontSize: '30px', display: 'none' });
    const dim1 = el('div', 'abs num', '20 m', raiz), dim2 = el('div', 'abs num', '20 m', raiz);
    [dim1, dim2].forEach(d => Object.assign(d.style, { left: 0, top: 0, fontSize: '44px', color: '#ffe29a', whiteSpace: 'nowrap', opacity: 0, background: 'rgba(5,5,7,.72)', padding: '2px 16px', borderRadius: '12px' }));

    /* ============================ capa 3: pila de fotos con nubes ============================ */
    const nubes = el('div', 'capa', null, raiz);
    const tA = el('div', 'abs centro titulo xs', 'Las nubes tapan partes de cada foto', nubes); Object.assign(tA.style, { left: 0, right: 0, top: '90px', fontSize: '66px' });
    const tB = el('div', 'abs centro titulo xs', 'Mediana de varias fotos: <span class="g-oro">las nubes desaparecen</span>', nubes); Object.assign(tB.style, { left: 0, right: 0, top: '90px', fontSize: '66px' });
    const eA = el('div', 'abs centro etiqueta', 'Fotos de mayo a septiembre de 2026 · época seca', nubes); Object.assign(eA.style, { left: 0, right: 0, top: '250px' });
    const eB = el('div', 'abs centro etiqueta', 'Ilustración · nubes dibujadas sobre un recorte real del bloque', nubes); Object.assign(eB.style, { left: 0, right: 0, top: '878px', color: '#c9c9d2' });
    const CS = 380, FILA = 380, CY = FILA + CS / 2;
    const cartas = [1, 2, 3, 4].map(i => {
      const c = el('div', 'abs', null, nubes); Object.assign(c.style, { left: 0, top: 0, width: CS + 'px', height: CS + 'px', borderRadius: '22px', overflow: 'hidden', boxShadow: '0 30px 80px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.2)' });
      const im = H.img(`assets/capturas/satelite_nube_${i}.jpg`, null, c); Object.assign(im.style, { width: '100%', height: '100%', objectFit: 'cover', display: 'block' });
      const p = el('div', 'pastilla', 'Foto ' + i, c); Object.assign(p.style, { position: 'absolute', left: '16px', bottom: '16px', fontSize: '26px', padding: '6px 18px', background: 'rgba(5,5,7,.65)' });
      return c;
    });
    const limpia = el('div', 'abs', null, nubes); Object.assign(limpia.style, { left: 0, top: 0, width: CS + 'px', height: CS + 'px', borderRadius: '22px', overflow: 'hidden', boxShadow: '0 0 0 4px rgba(224,168,42,.95), 0 0 90px rgba(224,168,42,.4), 0 40px 100px rgba(0,0,0,.6)' });
    { const im = H.img('assets/capturas/satelite_nube_mediana.jpg', null, limpia); Object.assign(im.style, { width: '100%', height: '100%', objectFit: 'cover', display: 'block' }); }

    /* ============================ camara y dibujo del lienzo ============================ */
    const TX = 909.5, TY = 1109.5, Z0 = 1.78, ZEND = 72;          // pixel real del suelo removido (el de la miniatura px_suelo_removido.png)
    function camara(t) {
      let z, cx, cy;
      if (t <= 10.8) { const p = an(t, 4.3, 10.8, E.io2); z = lerp(1.45, Z0, p); cx = lerp(690, 790, p); cy = lerp(700, 930, p); }
      else {
        z = Z0 * Math.pow(ZEND / Z0, an(t, 10.8, 15.2, E.io3));
        const pp = an(t, 10.8, 15.2, E.io2), s0x = 960 + (TX - 790) * Z0, s0y = 540 + (TY - 930) * Z0;
        const sx = lerp(s0x, 1280, pp), sy = lerp(s0y, 540, pp);
        cx = TX - (sx - 960) / z; cy = TY - (sy - 540) / z;
      }
      return { z, vx: cx - 960 / z, vy: cy - 540 / z };
    }
    function dibujar(t) {
      const { z, vx, vy } = camara(t), sw = W / z, sh = HH / z, k = jn.naturalWidth / NW;
      ctx.clearRect(0, 0, W, HH);
      ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(jn, vx * k, vy * k, sw * k, sh * k, 0, 0, W, HH);
      const a = an(z, 2.6, 4.4, E.lineal);                           // al acercar mucho, se ven los pixeles reales (sin suavizar)
      if (a > 0) { ctx.globalAlpha = a; ctx.imageSmoothingEnabled = false; ctx.drawImage(nn, vx, vy, sw, sh, 0, 0, W, HH); ctx.globalAlpha = 1; }
      // cortina natural -> falso color
      let w = 0;
      if (t > 7.0 && t < 10.9) w = t < 8.7 ? lerp(0, 1980, an(t, 7.0, 8.7, E.io3)) : t < 9.8 ? 1980 : lerp(1980, -60, an(t, 9.8, 10.8, E.io3));
      if (w > 0 && z < 3) {
        ctx.save(); ctx.beginPath(); ctx.rect(0, 0, w, HH); ctx.clip();
        ctx.imageSmoothingEnabled = true; ctx.drawImage(jf, vx * k, vy * k, sw * k, sh * k, 0, 0, W, HH); ctx.restore();
        if (w < 1930) {
          const g = ctx.createLinearGradient(w - 70, 0, w + 6, 0); g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(1, 'rgba(255,255,255,.28)');
          ctx.fillStyle = g; ctx.fillRect(w - 70, 0, 76, HH);
          ctx.fillStyle = 'rgba(255,255,255,.95)'; ctx.fillRect(w - 1.5, 0, 3, HH);
        }
      }
      // rejilla de pixeles
      const ga = an(z, 6.5, 14, E.lineal);
      if (ga > 0) {
        ctx.strokeStyle = `rgba(255,255,255,${0.34 * ga})`; ctx.lineWidth = 1.5; ctx.beginPath();
        for (let i = Math.floor(vx); i <= vx + sw + 1; i++) { const x = Math.round((i - vx) * z) + .5; ctx.moveTo(x, 0); ctx.lineTo(x, HH); }
        for (let j = Math.floor(vy); j <= vy + sh + 1; j++) { const y = Math.round((j - vy) * z) + .5; ctx.moveTo(0, y); ctx.lineTo(W, y); }
        ctx.stroke();
      }
      // el pixel resaltado y sus medidas
      const h = an(t, 14.2, 15.0, E.out3);
      if (h > 0) {
        const x0 = (909 - vx) * z, y0 = (1109 - vy) * z;
        ctx.fillStyle = `rgba(224,168,42,${0.12 * h})`; ctx.fillRect(x0, y0, z, z);
        ctx.strokeStyle = `rgba(0,0,0,${0.75 * h})`; ctx.lineWidth = 11; ctx.strokeRect(x0, y0, z, z);
        ctx.strokeStyle = `rgba(255,226,140,${h})`; ctx.lineWidth = 5; ctx.strokeRect(x0, y0, z, z);
        ctx.lineWidth = 3; ctx.strokeStyle = `rgba(255,226,154,${h})`; ctx.beginPath();
        const yb = y0 - 24, xb = x0 + z + 24;
        ctx.moveTo(x0, yb); ctx.lineTo(x0 + z * h, yb); ctx.moveTo(x0, yb - 12); ctx.lineTo(x0, yb + 12); ctx.moveTo(x0 + z * h, yb - 12); ctx.lineTo(x0 + z * h, yb + 12);
        ctx.moveTo(xb, y0); ctx.lineTo(xb, y0 + z * h); ctx.moveTo(xb - 12, y0); ctx.lineTo(xb + 12, y0); ctx.moveTo(xb - 12, y0 + z * h); ctx.lineTo(xb + 12, y0 + z * h);
        ctx.stroke();
        const fo = h * (1 - an(t, 15.9, 16.4));
        pon(dim1, { x: x0 + z / 2 - 55, y: yb - 74, o: fo }); pon(dim2, { x: xb + 28, y: y0 + z / 2 - 28, o: fo });
      } else { pon(dim1, { o: 0, x: -400, y: 0 }); pon(dim2, { o: 0, x: -400, y: 0 }); }
    }

    /* ============================ actualizar(t) ============================ */
    const FILA_X = i => 110 + i * 440;
    const PILA = { x: 960 - CS / 2, y: CY - CS / 2 };
    return t => {
      // ---- beat 1: orbita, haz, huella
      const ent = an(t, 0, 1.4, E.out3);
      pon(tierra, { o: ent }); tierra.style.transform = `translateY(${lerp(80, 0, ent)}px)`;
      estrellas.forEach(([c, o, f]) => c.setAttribute('opacity', (o * (0.6 + 0.4 * Math.sin(t * 1.3 + f)) * ent).toFixed(3)));
      orbita.setAttribute('opacity', an(t, 0.4, 1.4));
      const th = lerp(0.26 * Math.PI, 0.76 * Math.PI, an(t, 0, 5.6, E.io2));
      const sx = 1300 + 380 * Math.cos(th), sy = 330 - 110 * Math.sin(th) + 4 * Math.sin(t * 1.6);
      const sa = an(t, 0.2, 1.2, E.out3);
      pon(sat, { x: sx - 150, y: sy - 80 + lerp(-80, 0, sa), o: sa, s: 1 });
      const lx = sx, ly = sy + 40;
      const b = an(t, 1.8, 2.8, E.out4);
      const ex = lerp(lx, 1060, b), ey = lerp(ly, 724, b), fx = lerp(lx, 1300, b), fy = lerp(ly, 724, b);
      haz.setAttribute('points', `${lx},${ly} ${ex},${ey} ${fx},${fy}`); haz.setAttribute('opacity', b * (1 - an(t, 4.6, 5.3)));
      hazN.setAttribute('x1', lx); hazN.setAttribute('y1', ly); hazN.setAttribute('x2', lerp(lx, 1180, b)); hazN.setAttribute('y2', lerp(ly, 724, b)); hazN.setAttribute('opacity', b * (1 - an(t, 4.6, 5.3)));
      huella.setAttribute('opacity', an(t, 2.5, 3.1) * (1 - an(t, 4.4, 5.2)));
      const aT = an(t, 0.6, 1.6, E.out4); pon(tTit, { o: aT * (1 - an(t, 4.0, 4.7)), y: lerp(50, 0, aT), blur: lerp(14, 0, aT) });
      pil.forEach((p, i) => { const a = an(t, 1.5 + i * 0.35, 2.4 + i * 0.35, E.out4); pon(p, { o: a * (1 - an(t, 4.0, 4.7)), x: lerp(-50, 0, a), blur: lerp(10, 0, a) }); });
      cielo.style.opacity = 1 - an(t, 4.9, 5.9);
      cielo.style.display = t > 6 ? 'none' : '';

      // ---- beat 2/3: lienzo (ventana que se expande desde la huella)
      const ex2 = an(t, 4.3, 5.9, E.io3);
      const ins = [lerp(724, 0, ex2), lerp(620, 0, ex2), lerp(206, 0, ex2), lerp(1060, 0, ex2)];
      marco.style.clipPath = `inset(${ins[0]}px ${ins[1]}px ${ins[2]}px ${ins[3]}px round ${lerp(14, 0, ex2)}px)`;
      marco.style.opacity = an(t, 2.2, 3.0) * (1 - an(t, 15.9, 16.5));
      marco.style.display = (t < 2 || t > 16.6) ? 'none' : '';
      if (t >= 2 && t <= 16.6) dibujar(t); else { dim1.style.opacity = 0; dim2.style.opacity = 0; }
      const vis = an(t, 5.0, 6.0) * (1 - an(t, 15.9, 16.5));
      velo.style.opacity = vis; velo2.style.opacity = vis * (1 - an(t, 10.8, 11.6));
      pon(pN, { y: lerp(-24, 0, an(t, 5.6, 6.4, E.out3)) });
      pN.style.opacity = Math.max(0, an(t, 5.6, 6.4) * (1 - an(t, 8.2, 8.8)) + an(t, 10.0, 10.5) * (1 - an(t, 10.9, 11.4)));
      pF.style.opacity = an(t, 7.4, 8.0) * (1 - an(t, 10.0, 10.5));
      pon(pF, { y: lerp(-24, 0, an(t, 7.4, 8.0, E.out3)) });

      // ---- beat 3: panel de la rejilla
      const pa = an(t, 13.0, 13.9) * (1 - an(t, 15.9, 16.4));
      panel.style.opacity = pa;
      const a1 = an(t, 13.3, 14.1, E.out4); pon(pT1, { o: a1 * (1 - an(t, 15.9, 16.4)), y: lerp(40, 0, a1), blur: lerp(12, 0, a1) });
      const a2 = an(t, 13.9, 14.7, E.out4); pon(pT2, { o: a2 * (1 - an(t, 15.9, 16.4)), y: lerp(40, 0, a2), blur: lerp(12, 0, a2) });
      const a3 = an(t, 14.6, 15.3, E.out4); pon(pT3, { o: a3 * (1 - an(t, 15.9, 16.4)), y: lerp(30, 0, a3) });
      tiles.forEach((d, i) => { const a = an(t, 14.5 + i * 0.25, 15.3 + i * 0.25, E.out4); pon(d, { o: a * (1 - an(t, 15.9, 16.4)), y: lerp(40, 0, a), blur: lerp(10, 0, a) }); });

      // ---- beat 4: nubes y mediana
      nubes.style.display = t < 16.2 ? 'none' : '';
      pon(tA, { o: an(t, 16.4, 17.2) * (1 - an(t, 18.9, 19.5)), y: lerp(30, 0, an(t, 16.4, 17.2, E.out4)) });
      pon(eA, { o: an(t, 17.0, 17.7) * (1 - an(t, 18.9, 19.4)) });
      const bB = an(t, 19.3, 20.1, E.out4); pon(tB, { o: bB, y: lerp(30, 0, bB), blur: lerp(12, 0, bB) });
      pon(eB, { o: an(t, 20.9, 21.5) });
      cartas.forEach((c, i) => {
        const ent = an(t, 16.4 + i * 0.16, 17.4 + i * 0.16, E.out4);
        const pl = an(t, 18.8 + 0.06 * Math.abs(i - 1.5), 19.8 + 0.06 * Math.abs(i - 1.5), E.io3);
        const rot = (i - 1.5) * 5, ox = (i - 1.5) * 16, oy = -Math.abs(i - 1.5) * 4;
        const x = lerp(FILA_X(i), PILA.x + ox, pl), y = lerp(FILA, PILA.y + oy, pl) + lerp(90, 0, ent);
        const fade = 1 - an(t, 19.9, 20.5);
        pon(c, { x, y, r: lerp(0, rot, pl), s: lerp(.92, 1, ent) * lerp(1, .97, pl), o: ent * fade, blur: lerp(14, 0, ent) });
      });
      const ap = an(t, 19.7, 20.4, E.out3), gr = an(t, 20.0, 21.2, E.outExpo);
      pon(limpia, { x: PILA.x, y: PILA.y, s: lerp(.97, 1.5, gr), o: ap, blur: lerp(8, 0, ap) });
    };
  },
});
