/* Escena 15 - Cierre (8 s).
   Fondo: el bloque real analizado (sin coordenadas) con sus zonas, muy tenue. Lema "Mirar. Verificar. Reportar." y la firma del proyecto.
   Los ultimos 0.5 s quedan quietos. Todo es funcion pura de t. */
Pres.escena({
  id: 'cierre', titulo: 'Cierre', dur: 8,
  recursos: ['assets/real/bloque_natural.jpg', 'assets/datos/zonas_pixel.json'],
  subs: [
    [0.5, 3.8, 'Mirar. Verificar. Reportar.'],
    [4.2, 7.3, 'Equipo aurum80: para que las personas decidan con mejor información.'],
  ],
  montar(raiz, H) {
    const { el, svg, pon, an, E, lerp, clamp, img, rec } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const AZU = '#74c0fc', VER = '#2fb344';

    const Z = rec('assets/datos/zonas_pixel.json') || {};
    const W = Z.ancho || 1352, HH = Z.alto || 1442;
    const VW = 1920, VH = Math.round(VW * HH / W);
    const vp = A('', null, raiz, { left: '0', top: '0', width: '1920px', height: '1080px', overflow: 'hidden' });
    const fondo = A('', null, vp, { left: '0', top: Math.round(-(VH * 0.72 - 540)) + 'px', width: VW + 'px', height: VH + 'px', transformOrigin: '50% 0.72' });
    fondo.style.transformOrigin = '960px ' + Math.round(VH * 0.72) + 'px';
    const im = img('assets/real/bloque_natural.jpg', null, fondo); Object.assign(im.style, { position: 'absolute', left: '0', top: '0', width: '100%', height: '100%' });
    const sv = svg('svg', { viewBox: `0 0 ${W} ${HH}`, width: VW, height: VH }, fondo); sv.style.cssText = 'position:absolute;left:0;top:0';
    const zs = [];
    (Z.zonas || []).forEach(z => {
      let d = '';
      (z.anillos || []).forEach(r => { if (Array.isArray(r) && Array.isArray(r[0])) { r.forEach((p, i) => { d += (i ? 'L' : 'M') + p[0] + ' ' + p[1]; }); d += 'Z'; } });
      if (d) zs.push(svg('path', { d, fill: 'rgba(151,117,250,.18)', stroke: '#b197fc', 'stroke-width': 6, 'stroke-linejoin': 'round' }, sv));
    });
    const velo = A('', null, raiz, { left: '0', top: '0', width: '1920px', height: '1080px', background: 'radial-gradient(ellipse at 50% 50%, rgba(10,10,15,.55), rgba(10,10,15,.9) 75%)' });

    const palabras = [['Mirar.', AZU], ['Verificar.', '#f0a283'], ['Reportar.', '#8ce99a']];
    const ws = palabras.map(([w, c], i) => A('titulo', w, raiz, { left: '0', right: '0', top: (200 + i * 150) + 'px', textAlign: 'center', fontSize: '150px', color: c }));
    const firma = A('', null, raiz, { left: '0', right: '0', top: '720px', textAlign: 'center' });
    el('div', 'titulo s g-oro', 'aurum80', firma);
    el('div', 'etiqueta', 'Detección de posible actividad minera y reporte ciudadano', firma).style.cssText = 'margin-top:16px;font-size:24px';
    const pie = A('', 'Una herramienta para que las personas decidan con mejor información.', raiz, { left: '0', right: '0', top: '960px', textAlign: 'center', font: '400 32px var(--fuente-texto)', color: 'var(--suave)' });

    return t => {
      const k = an(t, 0, 7.5, E.lineal);
      pon(fondo, { s: lerp(1.0, 1.07, E.out2(k)) });
      pon(velo, { o: an(t, 0, 0.8) });
      im.style.opacity = an(t, 0, 0.8);
      zs.forEach((z, i) => { z.style.opacity = an(t, 1.0 + i * 0.05, 1.8 + i * 0.05) * (0.7 + 0.3 * Math.sin(Math.min(t, 7.0) * 1.6 + i)); });
      ws.forEach((w, i) => { const p = an(t, 0.8 + i * 0.8, 1.7 + i * 0.8, E.out4); ent(w, p, 50, 18); });
      const f = an(t, 4.0, 5.0, E.out4); ent(firma, f, 30, 10);
      pon(pie, { o: an(t, 5.0, 5.8) });
    };
  },
});
