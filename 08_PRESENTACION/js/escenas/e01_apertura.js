/* Escena 1 - Apertura (12 s). Es la escena de REFERENCIA: las demas siguen el mismo estilo (ver GUIA-ESCENAS.md). */
Pres.escena({
  id: 'apertura', titulo: 'Apertura', dur: 13, sinFundido: false,
  recursos: ['assets/real/bloque_natural.jpg', 'assets/datos/zonas_pixel.json'],
  subs: [[0.6, 4.2, 'Somos el equipo aurum80. Un satélite mira el territorio todos los días.'], [4.4, 8.2, 'Nuestro modelo convierte esas imágenes en una lista de zonas para revisar.'], [8.4, 12.6, 'Y una plataforma permite que cualquiera pueda reportar.']],
  montar(raiz, H) {
    const { el, img, svg, pon, an, E, seg, lerp } = H;
    // Fondo: el bloque real, muy grande, con un lento movimiento de camara
    const mapa = el('div', 'capa', null, raiz); mapa.style.overflow = 'hidden';
    const foto = img('assets/real/bloque_natural.jpg', 'img-llena', mapa);
    Object.assign(foto.style, { width: '2600px', height: 'auto', left: '-300px', top: '-420px', transformOrigin: '60% 70%' });
    const velo = el('div', 'capa', null, raiz); velo.style.background = 'radial-gradient(1100px 700px at 50% 50%, rgba(5,5,7,.55), rgba(5,5,7,.92))';
    // Contornos de las zonas del modelo, dibujados sobre la foto
    const Z = H.rec('assets/datos/zonas_pixel.json');
    const sv = svg('svg', { viewBox: `0 0 ${Z.ancho} ${Z.alto}` }, mapa);
    sv.style.cssText = 'position:absolute;left:-300px;top:-420px;width:2600px;height:' + (2600 * Z.alto / Z.ancho) + 'px;transform-origin:60% 70%;overflow:visible';
    const caminos = Z.zonas.map(z => { const p = svg('path', { d: z.anillos.map(a => 'M' + a.map(q => q.join(',')).join('L') + 'Z').join(' '), fill: 'rgba(224,168,42,.18)', stroke: '#e0a82a', 'stroke-width': 3.2, 'stroke-linejoin': 'round', 'vector-effect': 'non-scaling-stroke' }, sv); return p; });
    // Texto
    const t1 = el('div', 'abs centro', '<div class="etiqueta" style="margin-bottom:34px">Equipo aurum80 · Bolivia</div><div class="titulo g-blanco">Mirar el <span class="g-oro">territorio</span></div>', raiz);
    Object.assign(t1.style, { left: '0', right: '0', top: '330px' });
    const t2 = el('div', 'abs centro sub', 'Un modelo propone <b>zonas por verificar</b>.<br>Una plataforma permite <b>reportar</b>.', raiz);
    Object.assign(t2.style, { left: '0', right: '0', top: '640px', fontSize: '52px' });
    const lin = el('div', 'abs', null, raiz); Object.assign(lin.style, { left: '860px', width: '200px', top: '300px', height: '3px', background: 'linear-gradient(90deg, transparent, #e0a82a, transparent)' });
    return t => {
      const k = an(t, 0, 13, E.lineal);
      pon(foto, { s: lerp(1.0, 1.18, k) }); pon(sv, { s: lerp(1.0, 1.18, k) });
      pon(foto, { o: an(t, 0, 1.4, E.out3) }); pon(velo, { o: lerp(.35, 1, an(t, 2, 6, E.io2)) });
      // los contornos "se encienden" uno por uno
      caminos.forEach((p, i) => { const a = an(t, 1 + i * 0.12, 2.2 + i * 0.12, E.out3); p.style.opacity = a; });
      const a1 = an(t, 1.2, 2.8, E.out4);
      pon(t1, { o: a1, y: lerp(60, 0, a1), blur: lerp(20, 0, a1) });
      pon(lin, { o: an(t, 1.0, 2.0), sx: an(t, 1.0, 2.2, E.out4) });
      const a2 = an(t, 3.6, 5.0, E.out4); pon(t2, { o: a2, y: lerp(40, 0, a2), blur: lerp(14, 0, a2) });
      // al final todo se aleja y se desvanece para dar paso a la siguiente escena
      pon(t1, { y: lerp(0, -40, an(t, 11, 13)) + lerp(60, 0, a1) * 0, o: a1 * (1 - an(t, 11.4, 12.8)) });
      pon(t2, { o: a2 * (1 - an(t, 11.4, 12.8)) });
    };
  },
});
