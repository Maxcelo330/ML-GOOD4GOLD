/* Escena 5 - La firma de cada pixel (22 s).
   Un pixel real de suelo removido -> 6 bandas (lo que mide el satelite) -> 3 indices + pendiente -> 4 variables de entorno
   -> ficha de 14 numeros -> comparacion de 3 pixeles reales (bosque / suelo removido / rio) como "huella" en un radar.
   Todos los valores salen de assets/datos/pixeles_ejemplo.json. Las imagenes del entorno salen de herramientas/e05_e06_datos.py. */
Pres.escena({
  id: 'firma', titulo: 'La firma de cada píxel', dur: 22,
  recursos: ['assets/datos/pixeles_ejemplo.json', 'assets/real/px_suelo_removido.png', 'assets/real/px_bosque.png', 'assets/real/px_rio.png',
    'assets/capturas/e05_entorno.png', 'assets/capturas/e05_entorno_pelado.png', 'assets/capturas/e05_entorno_agua.png'],
  subs: [
    [0.6, 5.9, 'Cada píxel mide 20 por 20 metros. El satélite lo mide en 6 colores de luz, y tres de ellos el ojo no los ve.'],
    [6.3, 10.1, 'Con esas bandas se calculan índices: cuánta vegetación, cuánta agua, cuánto suelo desnudo. Más la pendiente.'],
    [10.5, 15.0, 'Y se mira el entorno, a 100 y a 300 metros: textura, vegetación, agua y suelo pelado alrededor.'],
    [15.4, 17.9, 'El resultado es una ficha de 14 números por cada píxel.'],
    [18.4, 21.7, 'Cada terreno tiene su propia huella: un bosque, un suelo removido y un río no se parecen.'],
  ],
  montar(raiz, H) {
    const { el, svg, pon, an, E, lerp, clamp } = H;
    const D = H.rec('assets/datos/pixeles_ejemplo.json');
    const PX = {}; D.pixeles.forEach(p => { PX[p.tipo] = p; });
    const S = PX.suelo_removido.variables;
    const fmt = (v, dmin = 2, dmax = 3) => v.toLocaleString('es', { minimumFractionDigits: dmin, maximumFractionDigits: dmax }).replace('-', '−');
    const GC = ['#74c0fc', '#69db7c', '#ffa94d', '#b197fc'];           // colores de grupo: bandas, indices, relieve, entorno
    const css = (e, o) => { Object.assign(e.style, o); return e; };
    const abs = (clase, html, o, padre) => css(el('div', 'abs ' + (clase || ''), html, padre || raiz), o);
    // salida/entrada de un elemento con la mezcla "desliza + aclara"
    const entra = (e, p, dy = 40) => pon(e, { o: p, y: lerp(dy, 0, p), blur: lerp(14, 0, p) });

    // color real del pixel (promedio de su celda central de 12 x 12 en la miniatura de 25 x 25)
    let colorPx = '#e6a974';
    try {
      const im = H.rec('assets/real/px_suelo_removido.png'), c = document.createElement('canvas'); c.width = c.height = 12;
      const g = c.getContext('2d'); g.drawImage(im, 144, 144, 12, 12, 0, 0, 12, 12);
      const d = g.getImageData(0, 0, 12, 12).data; let r = 0, gg = 0, b = 0; for (let i = 0; i < d.length; i += 4) { r += d[i]; gg += d[i + 1]; b += d[i + 2]; }
      const n = d.length / 4; colorPx = `rgb(${Math.round(r / n)},${Math.round(gg / n)},${Math.round(b / n)})`;
    } catch (e) { /* si el navegador bloquea el canvas queda el color de respaldo */ }

    // ------------------------------------------------------------------ riel de 4 grupos (6 + 3 + 1 + 4 = 14)
    const riel = [['6 bandas', 0], ['3 índices', 1], ['1 de relieve', 2], ['4 de entorno', 3]].map(([txt, i]) => {
      const c = abs('', `<i style="display:inline-block;width:16px;height:16px;border-radius:50%;background:${GC[i]};margin-right:14px"></i>${txt}`,
        { left: (190 + i * 400) + 'px', top: '42px', width: '340px', height: '62px', lineHeight: '58px', textAlign: 'center', borderRadius: '31px',
          border: '2px solid rgba(255,255,255,.12)', fontSize: '30px', fontFamily: 'var(--fuente-num)', fontWeight: 600, letterSpacing: '.04em' });
      if (i < 3) abs('', '+', { left: (190 + i * 400 + 340) + 'px', top: '42px', width: '60px', height: '62px', lineHeight: '58px', textAlign: 'center', fontSize: '36px', color: 'var(--tenue)' });
      return c;
    });
    const tramos = [[0.5, 6.3], [6.3, 10.3], [8.9, 10.3], [10.3, 15.3]];   // cuando cada grupo esta "activo"
    const actualizarRiel = t => riel.forEach((c, i) => {
      const [a, b] = tramos[i];
      const on = an(t, a, a + 0.5, E.out3), off = an(t, b, b + 0.5, E.out3) * (i === 2 ? 0 : 1), fin = an(t, 15.3, 15.9);
      const k = Math.max(0, Math.min(1, on - off * 0.45 + fin * 0.45));
      pon(c, { o: lerp(0.0, 1, an(t, 0.2, 0.9, E.out3)) * lerp(0.35, 1, k) });
      c.style.borderColor = k > 0.55 ? GC[i] : 'rgba(255,255,255,.12)';
      c.style.background = `rgba(${H.hex(GC[i]).join(',')},${(0.16 * k).toFixed(3)})`;
    });

    // ------------------------------------------------------------------ titulos
    const titulos = [
      'El satélite mide más de lo que ve el ojo', 'Con esas bandas se calculan índices', 'Y también mira su entorno', '14 números por píxel: su ficha', 'Cada terreno tiene su huella'
    ].map(txt => abs('titulo', txt, { left: '0', right: '0', top: '132px', textAlign: 'center', fontSize: '66px', letterSpacing: '-0.03em' }));

    // ================================================================== BLOQUE 1: el pixel y sus 6 bandas
    const b1 = abs('', null, { inset: '0' });
    const gPx = abs('', null, { inset: '0' }, b1);       // todo lo que NO son barras: se apaga cuando llegan los indices
    const thumb = abs('', null, { left: '90px', top: '330px', width: '330px', height: '330px', borderRadius: '18px', overflow: 'hidden', boxShadow: '0 30px 80px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.16)' }, gPx);
    const im1 = H.img('assets/real/px_suelo_removido.png', 'img-llena', thumb); css(im1, { left: 0, top: 0, width: '330px', height: '330px', imageRendering: 'pixelated' });
    const rej = svg('svg', { width: 330, height: 330, viewBox: '0 0 330 330' }, thumb); css(rej, { position: 'absolute', left: 0, top: 0 });
    for (let i = 1; i < 25; i++) { const p = i * 13.2; svg('path', { d: `M${p} 0V330M0 ${p}H330`, stroke: 'rgba(255,255,255,.14)', 'stroke-width': 1 }, rej); }
    const cx0 = 90 + 12 * 13.2, cy0 = 330 + 12 * 13.2, cs = 13.2;                  // celda central en el cuadro de 1920 x 1080
    const celda = abs('', null, { left: cx0 + 'px', top: cy0 + 'px', width: cs + 'px', height: cs + 'px', border: '3px solid #e0a82a', boxShadow: '0 0 24px rgba(224,168,42,.9)', boxSizing: 'border-box' }, gPx);
    abs('sub s', 'Vista real del satélite', { left: '90px', top: '676px', width: '330px', textAlign: 'center', fontSize: '26px' }, gPx);
    const cono = svg('svg', { width: 1920, height: 1080, viewBox: '0 0 1920 1080' }, gPx); css(cono, { position: 'absolute', left: 0, top: 0, overflow: 'visible' });
    const conoP = svg('path', { d: `M${cx0 + cs} ${cy0}L560 372L560 612L${cx0 + cs} ${cy0 + cs}Z`, fill: 'rgba(224,168,42,.09)', stroke: 'rgba(224,168,42,.45)', 'stroke-width': 2 }, cono);
    const zoom = abs('', null, { left: '520px', top: '362px', width: '250px', height: '250px', borderRadius: '14px', background: colorPx, border: '4px solid #e0a82a',
      boxShadow: '0 0 60px rgba(224,168,42,.35), 0 30px 80px rgba(0,0,0,.55)', transformOrigin: '0 50%' }, gPx);
    css(zoom, { backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,.18), rgba(0,0,0,.12))' });
    const zoomTxt = abs('sub s', '1 píxel = <b>20 × 20 m</b>', { left: '470px', top: '630px', width: '350px', textAlign: 'center', fontSize: '30px' }, gPx);

    // rayos y barras
    const BANDAS = [['B02', 'Azul', '#4dabf7'], ['B03', 'Verde', '#51cf66'], ['B04', 'Rojo', '#ff6b6b'], ['B08', 'Infrarrojo<br>cercano', '#e599f7'], ['B11', 'Onda corta<br>B11', '#ffa94d'], ['B12', 'Onda corta<br>B12', '#f76707']];
    const colX = i => 905 + 165 * i, BASE = 780, ALTO = 400, MAXV = 0.5;
    const rayos = svg('svg', { width: 1920, height: 1080, viewBox: '0 0 1920 1080' }, gPx); css(rayos, { position: 'absolute', left: 0, top: 0, overflow: 'visible' });
    const gBarras = abs('', null, { inset: '0', transformOrigin: '0 0' }, b1);
    const gEtiq = abs('', null, { inset: '0' }, gBarras);
    const rayo = [], foton = [], pto = [], barra = [], valor = [];
    BANDAS.forEach(([cod, nom, col], i) => {
      const x = colX(i), v = S[cod];
      const p = svg('path', { d: `M772 487C ${900 + i * 30} 487, ${x - 80} 380, ${x} 364`, fill: 'none', stroke: col, 'stroke-width': 3.5, 'stroke-linecap': 'round', opacity: .85 }, rayos); rayo.push(p);
      foton.push(svg('circle', { r: 9, fill: '#fff', style: `filter:drop-shadow(0 0 10px ${col})` }, rayos));
      pto.push(svg('circle', { cx: x, cy: 364, r: 9, fill: col }, rayos));
      abs('', null, { left: (x - 65) + 'px', top: (BASE - ALTO) + 'px', width: '130px', height: ALTO + 'px', borderRadius: '16px 16px 6px 6px', background: 'rgba(255,255,255,.06)' }, gBarras);
      const b = abs('', null, { left: (x - 65) + 'px', top: BASE + 'px', width: '130px', height: '0px', borderRadius: '16px 16px 6px 6px', background: `linear-gradient(180deg, ${col}, ${H.color(col, '#000000', .45)})`, boxShadow: `0 0 40px ${col}55` }, gBarras);
      barra.push(b);
      valor.push(abs('num', '0', { left: (x - 80) + 'px', top: (BASE - 60) + 'px', width: '160px', textAlign: 'center', fontSize: '44px', color: '#fff' }, gEtiq));
      abs('', `<div style="font-size:30px;font-weight:600;line-height:1.1">${nom}</div>` + (nom.includes('<br>') ? '' : `<div class="mono" style="font-size:22px;color:var(--tenue);margin-top:6px">${cod}</div>`),
        { left: (x - 82) + 'px', top: (BASE + 18) + 'px', width: '164px', textAlign: 'center' }, gEtiq);
    });
    const llaves = [[0, 2, 'Lo que ve el ojo', 'var(--suave)'], [3, 5, 'Lo que el ojo no ve', '#e0a82a']].map(([a, b, txt, col]) => {
      const x0 = colX(a) - 65, x1 = colX(b) + 65;
      return abs('', `<div style="font-size:28px;font-weight:600;letter-spacing:.04em;color:${col};margin-bottom:10px">${txt}</div><div style="height:4px;border-radius:2px;background:${col};opacity:.7"></div>`,
        { left: x0 + 'px', top: '262px', width: (x1 - x0) + 'px', textAlign: 'center' }, b1);
    });

    // ================================================================== BLOQUE 2: indices + pendiente
    const b2 = abs('', null, { inset: '0' });
    const FILAS = [
      { nom: 'NDVI', d: 'cuánta vegetación', h: 'infrarrojo cercano vs. rojo', v: S.ndvi, lo: -1, hi: 1, g: ['#8d6e4e', '#cdb35a', '#2fb344'], a: 'sin vegetación', z: 'mucha', c: '#69db7c' },
      { nom: 'NDWI', d: 'cuánta agua', h: 'verde vs. infrarrojo cercano', v: S.ndwi, lo: -1, hi: 1, g: ['#b08968', '#7fb6e6', '#2f80ed'], a: 'seco', z: 'agua', c: '#74c0fc' },
      { nom: 'BSI', d: 'cuánto suelo desnudo', h: 'onda corta + rojo vs. infrarrojo + azul', v: S.bsi, lo: -1, hi: 1, g: ['#2fb344', '#d9b26f', '#b5651d'], a: 'vegetal', z: 'suelo pelado', c: '#ffa94d' },
      { nom: 'Pendiente', d: 'inclinación del terreno', h: 'desde el modelo de elevación', v: S.pendiente, lo: 0, hi: 30, g: ['#3a3a4a', '#7a6fb0', '#b197fc'], a: 'plano', z: 'empinado', c: '#ffa94d', un: '°' },
    ];
    const TX0 = 1010, TW = 540;
    const filas = FILAS.map((f, i) => {
      const y = 330 + i * 140;
      const caja = abs('', null, { inset: '0' }, b2);
      abs('', `<div style="font-size:50px;font-weight:700;font-family:var(--fuente-titulo);letter-spacing:-0.02em;line-height:1">${f.nom}</div>
               <div style="font-size:30px;color:var(--texto);margin-top:8px">${f.d}</div><div style="font-size:22px;color:var(--tenue);margin-top:4px">${f.h}</div>`,
        { left: '540px', top: (y - 52) + 'px', width: '440px' }, caja);
      const pista = abs('', null, { left: TX0 + 'px', top: (y - 12) + 'px', width: TW + 'px', height: '24px', borderRadius: '12px', background: `linear-gradient(90deg, ${f.g.join(',')})`, boxShadow: 'inset 0 0 0 1px rgba(255,255,255,.2)' }, caja);
      abs('', `<span style="float:left">${f.a}</span><span style="float:right">${f.z}</span>`, { left: TX0 + 'px', top: (y + 20) + 'px', width: TW + 'px', fontSize: '22px', color: 'var(--tenue)' }, caja);
      if (f.lo < 0) abs('', null, { left: (TX0 + TW / 2 - 1) + 'px', top: (y - 20) + 'px', width: '2px', height: '40px', background: 'rgba(255,255,255,.45)' }, caja);
      const marca = abs('', null, { left: (TX0 - 20) + 'px', top: (y - 20) + 'px', width: '40px', height: '40px', borderRadius: '50%', background: '#fff', border: `6px solid ${f.c}`, boxShadow: '0 6px 20px rgba(0,0,0,.6)' }, caja);
      const val = abs('num', '0', { left: '1590px', top: (y - 40) + 'px', width: '230px', textAlign: 'right', fontSize: '72px', color: f.c }, caja);
      return { caja, marca, val, f, y };
    });
    const conect = svg('svg', { width: 1920, height: 1080, viewBox: '0 0 1920 1080' }, b2); css(conect, { position: 'absolute', left: 0, top: 0, overflow: 'visible' });
    const cx = FILAS.slice(0, 3).map((f, i) => svg('path', { d: `M470 480C 505 480, 505 ${330 + i * 140}, 530 ${330 + i * 140}`, fill: 'none', stroke: 'rgba(255,255,255,.35)', 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-dasharray': '2 8' }, conect));

    // ================================================================== BLOQUE 3: el entorno
    const b3 = abs('', null, { inset: '0' });
    const IMX = 150, IMY = 250, IMS = 630, K = 18;
    const marcoE = abs('', null, { left: IMX + 'px', top: IMY + 'px', width: IMS + 'px', height: IMS + 'px', borderRadius: '20px', overflow: 'hidden', boxShadow: '0 40px 100px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.16)' }, b3);
    const imE = H.img('assets/capturas/e05_entorno.png', 'img-llena', marcoE); css(imE, { left: 0, top: 0, width: IMS + 'px', height: IMS + 'px', imageRendering: 'pixelated' });
    const maskP = H.img('assets/capturas/e05_entorno_pelado.png', 'img-llena', marcoE); css(maskP, { left: 0, top: 0, width: IMS + 'px', height: IMS + 'px', imageRendering: 'pixelated' });
    const maskA = H.img('assets/capturas/e05_entorno_agua.png', 'img-llena', marcoE); css(maskA, { left: 0, top: 0, width: IMS + 'px', height: IMS + 'px', imageRendering: 'pixelated' });
    const svE = svg('svg', { width: IMS, height: IMS, viewBox: `0 0 ${IMS} ${IMS}` }, marcoE); css(svE, { position: 'absolute', left: 0, top: 0, overflow: 'visible' });
    const c0 = IMS / 2, rc = (n) => { const h = n * K / 2; return `M${c0 - h} ${c0 - h}H${c0 + h}V${c0 + h}H${c0 - h}Z`; };
    const v100 = svg('path', { d: rc(5), fill: 'none', stroke: '#fff', 'stroke-width': 4 }, svE);
    const v300 = svg('path', { d: rc(15), fill: 'none', stroke: '#b197fc', 'stroke-width': 5, 'stroke-dasharray': '1 0' }, svE);
    const puntoE = svg('rect', { x: c0 - K / 2, y: c0 - K / 2, width: K, height: K, fill: 'none', stroke: '#e0a82a', 'stroke-width': 4, style: 'filter:drop-shadow(0 0 8px #e0a82a)' }, svE);
    const etq100 = abs('', '100 m', { left: (IMX + c0 + 5 * K / 2 + 10) + 'px', top: (IMY + c0 - 40) + 'px', fontSize: '26px', fontWeight: 700, color: '#fff', textShadow: '0 2px 8px #000' }, b3);
    const etq300 = abs('', '300 m', { left: (IMX + c0 + 15 * K / 2 + 10) + 'px', top: (IMY + c0 - 150) + 'px', fontSize: '26px', fontWeight: 700, color: '#d0bfff', textShadow: '0 2px 8px #000' }, b3);
    const ENT = [
      { t: 'Textura · 100 m', d: 'cuánto cambia la vegetación entre vecinos', v: S.ndvi_textura_100m, f: v => fmt(v), c: '#ffffff' },
      { t: 'Vegetación · 300 m', d: 'casi no hay árboles alrededor', v: S.ndvi_media_300m, f: v => fmt(v), c: '#d0bfff' },
      { t: 'Agua · 300 m', d: 'parte del entorno que es agua', v: S.frac_agua_300m, f: v => Math.round(v * 100) + ' %', c: '#4cc9f0' },
      { t: 'Suelo pelado · 300 m', d: 'parte del entorno sin vegetación', v: S.frac_pelado_300m, f: v => Math.round(v * 100) + ' %', c: '#b197fc' },
    ];
    const entRows = ENT.map((r, i) => {
      const y = 262 + i * 140;
      const caja = abs('', null, { left: '900px', top: y + 'px', width: '900px', height: '116px', borderRadius: '22px', border: '1px solid rgba(255,255,255,.12)', background: 'rgba(255,255,255,.05)' }, b3);
      abs('', null, { left: '0', top: '22px', width: '8px', height: '72px', borderRadius: '4px', background: r.c }, caja);
      abs('', `<div style="font-size:38px;font-weight:600;line-height:1.1">${r.t}</div><div style="font-size:26px;color:var(--suave);margin-top:8px">${r.d}</div>`, { left: '36px', top: '22px', width: '600px' }, caja);
      const val = abs('num', '0', { left: '600px', top: '18px', width: '270px', textAlign: 'right', fontSize: '78px', color: r.c }, caja);
      return { caja, val, r };
    });
    const nota3 = abs('sub s', 'Un banco de arena es liso y está junto al agua.<br>Una mina tiene <b>mucho suelo removido</b> alrededor.', { left: '900px', top: '828px', width: '900px', fontSize: '28px', lineHeight: 1.3 }, b3);

    // ================================================================== BLOQUE 4: la ficha de 14 numeros
    const b4 = abs('', null, { inset: '0' });
    const ficha = abs('tarjeta', null, { left: '130px', top: '236px', width: '1660px', height: '590px' }, b4);
    const GRUPOS = [
      ['BANDAS', [['Azul · B02', 'B02'], ['Verde · B03', 'B03'], ['Rojo · B04', 'B04'], ['Infrarrojo · B08', 'B08'], ['Onda corta · B11', 'B11'], ['Onda corta · B12', 'B12']]],
      ['ÍNDICES', [['Vegetación · NDVI', 'ndvi'], ['Agua · NDWI', 'ndwi'], ['Suelo desnudo · BSI', 'bsi']]],
      ['RELIEVE', [['Pendiente', 'pendiente']]],
      ['ENTORNO', [['Textura · 100 m', 'ndvi_textura_100m'], ['Vegetación · 300 m', 'ndvi_media_300m'], ['Agua · 300 m', 'frac_agua_300m'], ['Suelo pelado · 300 m', 'frac_pelado_300m']]],
    ];
    const fichaFilas = []; const fichaCab = [];
    GRUPOS.forEach(([nom, vars], gi) => {
      const x = 40 + gi * 405;
      fichaCab.push(abs('etiqueta', nom, { left: x + 'px', top: '34px', width: '370px', color: GC[gi], fontSize: '28px', paddingBottom: '14px', borderBottom: `3px solid ${GC[gi]}` }, ficha));
      vars.forEach(([txt, k], ri) => {
        const v = S[k]; const s = k === 'pendiente' ? fmt(v, 1, 1) + '°' : fmt(v);
        const r = abs('', `<span style="font-size:27px;color:var(--suave)">${txt}</span><span class="num" style="float:right;font-size:40px;color:#fff">${s}</span>`,
          { left: x + 'px', top: (110 + ri * 74) + 'px', width: '370px', height: '56px', lineHeight: '56px', borderBottom: '1px solid rgba(255,255,255,.08)', whiteSpace: 'nowrap' }, ficha);
        fichaFilas.push({ r, gi, ri, n: GRUPOS.slice(0, gi).reduce((a, g) => a + g[1].length, 0) + ri });
      });
    });
    const pieFicha = abs('', '<b style="color:#fff">14</b> números = la firma de este píxel', { left: '0', right: '0', top: '838px', textAlign: 'center', fontSize: '34px', color: 'var(--suave)' }, b4);

    // ================================================================== BLOQUE 5: comparacion (radar = huella)
    const b5 = abs('', null, { inset: '0' });
    const COMP = [['bosque', 'Bosque', '#51cf66'], ['suelo_removido', 'Suelo removido', '#f5b700'], ['rio', 'Río', '#4dabf7']];
    const NORM = {
      B02: v => v / 0.4, B03: v => v / 0.4, B04: v => v / 0.4, B08: v => v / 0.4, B11: v => v / 0.4, B12: v => v / 0.4,
      ndvi: v => (v + 0.5) / 1.4, ndwi: v => (v + 0.8) / 1.3, bsi: v => (v + 0.3) / 0.6, pendiente: v => v / 20,
      ndvi_textura_100m: v => v / 0.35, ndvi_media_300m: v => v / 0.9, frac_agua_300m: v => v / 0.3, frac_pelado_300m: v => v,
    };
    const VARS = D.variables, NV = VARS.length, GRP = i => (i < 6 ? 0 : i < 9 ? 1 : i < 10 ? 2 : 3);
    const RR = 190, RC = 250;
    const radares = COMP.map(([tipo, nom, col], ci) => {
      const cxr = 340 + ci * 620;
      const caja = abs('', null, { left: (cxr - RC) + 'px', top: '240px', width: RC * 2 + 'px', height: RC * 2 + 'px' }, b5);
      const sv = svg('svg', { width: RC * 2, height: RC * 2, viewBox: `0 0 ${RC * 2} ${RC * 2}` }, caja); css(sv, { position: 'absolute', left: 0, top: 0, overflow: 'visible' });
      [1 / 3, 2 / 3, 1].forEach(f => svg('circle', { cx: RC, cy: RC, r: RR * f, fill: 'none', stroke: 'rgba(255,255,255,.12)', 'stroke-width': 1.5 }, sv));
      const ang = i => -Math.PI / 2 + (i / NV) * Math.PI * 2;
      VARS.forEach((v, i) => svg('line', { x1: RC, y1: RC, x2: RC + RR * Math.cos(ang(i)), y2: RC + RR * Math.sin(ang(i)), stroke: 'rgba(255,255,255,.14)', 'stroke-width': 1.5 }, sv));
      const poly = svg('path', { fill: col, 'fill-opacity': .3, stroke: col, 'stroke-width': 5, 'stroke-linejoin': 'round' }, sv);
      const puntos = VARS.map((v, i) => svg('circle', { r: 7.5, fill: GC[GRP(i)], stroke: '#0d0d14', 'stroke-width': 2.5 }, sv));
      const pie = abs('', null, { left: (cxr - 250) + 'px', top: '760px', width: '500px', height: '100px' }, b5);
      const mi = H.img('assets/real/px_' + tipo + '.png', null, pie); css(mi, { position: 'absolute', left: '100px', top: '6px', width: '88px', height: '88px', borderRadius: '14px', imageRendering: 'pixelated', boxShadow: `0 0 0 3px ${col}` });
      abs('', nom, { left: '210px', top: '18px', fontSize: '44px', fontWeight: 700, fontFamily: 'var(--fuente-titulo)', letterSpacing: '-0.02em', whiteSpace: 'nowrap', color: '#fff' }, pie);
      return { caja, poly, puntos, pie, tipo, ang };
    });
    const leyenda = abs('', GRUPOS.map((g, i) => `<span style="margin:0 26px"><i style="display:inline-block;width:18px;height:18px;border-radius:50%;background:${GC[i]};margin-right:12px;vertical-align:-2px"></i>${g[0][0] + g[0].slice(1).toLowerCase()}</span>`).join(''),
      { left: '0', right: '0', top: '884px', textAlign: 'center', fontSize: '28px', color: 'var(--suave)' }, b5);

    // ------------------------------------------------------------------ actualizar(t)
    const fund = (t, a, b, c, d) => an(t, a, b, E.out3) * (1 - an(t, c, d, E.io2));      // entra en [a,b], sale en [c,d]
    const ptRayo = (p, k) => { const L = p._L || (p._L = p.getTotalLength()); return p.getPointAtLength(L * k); };
    return t => {
      actualizarRiel(t);
      // ---- titulos
      const tw = [[0.4, 1.5, 5.8, 6.3], [6.4, 7.3, 9.9, 10.4], [10.4, 11.3, 14.8, 15.4], [15.4, 16.3, 17.7, 18.3], [18.4, 19.3, 22.1, 22.2]];
      titulos.forEach((e, i) => { const [a, b, c, d] = tw[i]; entra(e, fund(t, a, b, c, d), 36); });

      // ---- bloque 1
      const o1 = 1 - an(t, 5.9, 6.5);
      gPx.style.opacity = o1;
      pon(thumb, { o: an(t, 0.5, 1.5, E.out3) * o1, y: lerp(40, 0, an(t, 0.5, 1.6, E.out4)), blur: lerp(14, 0, an(t, 0.5, 1.5)) });
      const pulso = 1 + 0.25 * Math.sin(t * 7) * (1 - an(t, 2.4, 3.0));
      pon(celda, { o: an(t, 1.3, 1.9) * o1 * (1 - an(t, 2.6, 3.2) * 0.2), s: pulso });
      conoP.setAttribute('opacity', an(t, 1.9, 2.8) * o1);
      pon(zoom, { o: an(t, 1.9, 2.6) * o1, sx: lerp(0.05, 1, an(t, 1.9, 3.0, E.out4)), sy: lerp(0.05, 1, an(t, 1.9, 3.0, E.out4)) });
      pon(zoomTxt, { o: an(t, 2.9, 3.6) * o1 });
      // rayos
      rayo.forEach((p, i) => {
        const a = 3.0 + i * 0.12, k = an(t, a, a + 0.8, E.io2);
        H.trazo(p, k); p.setAttribute('opacity', (k > 0 ? 0.85 - 0.45 * an(t, a + 0.9, a + 1.6) : 0) * o1);
        const q = ptRayo(p, k); foton[i].setAttribute('cx', q.x); foton[i].setAttribute('cy', q.y);
        foton[i].setAttribute('opacity', (k > 0 && k < 1 ? 1 : 0) * o1);
        pto[i].setAttribute('opacity', an(t, a + 0.7, a + 1.0) * o1); pto[i].setAttribute('r', 9 + 5 * Math.max(0, 1 - Math.abs(t - (a + 0.85)) * 4));
      });
      // barras
      BANDAS.forEach(([cod], i) => {
        const a = 3.7 + i * 0.12, k = an(t, a, a + 1.0, E.out4), v = S[cod];
        const hh = ALTO * (v / MAXV) * k;
        barra[i].style.top = (BASE - hh) + 'px'; barra[i].style.height = hh + 'px';
        H.num(valor[i], v, k, 3); valor[i].textContent = valor[i].textContent; valor[i].style.top = (BASE - hh - 62) + 'px';
        valor[i].style.opacity = an(t, a, a + 0.3);
      });
      llaves.forEach((l, i) => pon(l, { o: an(t, 4.9 + i * 0.35, 5.6 + i * 0.35, E.out3) * o1, y: lerp(20, 0, an(t, 4.9 + i * 0.35, 5.7 + i * 0.35)) }));
      // el grupo de barras se encoge hacia la izquierda para dar paso a los indices
      const kb = an(t, 6.0, 7.0, E.io3), esc = lerp(1, 0.36, kb);
      gBarras.style.transform = `translate(${lerp(0, -192, kb)}px,${lerp(0, 270, kb)}px) scale(${esc})`;
      pon(gEtiq, { o: 1 - an(t, 5.9, 6.5) });
      b1.style.opacity = 1;
      pon(gBarras, { o: an(t, 0.2, 0.3) * (1 - an(t, 9.9, 10.5)) });
      // los elementos del bloque 1 que no son barras se apagan con o1 (ver arriba); las llaves tambien
      // ---- bloque 2
      conect.setAttribute('opacity', an(t, 7.0, 7.8) * (1 - an(t, 9.9, 10.4)));
      cx.forEach((p, i) => H.trazo(p, an(t, 6.9 + i * 0.15, 7.6 + i * 0.15)));
      filas.forEach((o, i) => {
        const a = 6.9 + i * (i === 3 ? 0 : 0.32) + (i === 3 ? 1.9 : 0);        // la pendiente llega despues
        const ap = an(t, a, a + 0.8, E.out4), sal = 1 - an(t, 9.9, 10.5, E.io2);
        pon(o.caja, { o: ap * sal, x: lerp(60, 0, ap) - lerp(0, 40, 1 - sal), blur: lerp(12, 0, ap) });
        const k = an(t, a + 0.5, a + 1.7, E.out4), f = o.f;
        const xv = TX0 + TW * (f.v - f.lo) / (f.hi - f.lo) * k;
        o.marca.style.left = (xv - 20) + 'px';
        H.num(o.val, f.v, k, f.un ? 1 : 3, f.un || '');
        o.val.textContent = o.val.textContent.replace('-', '−');
        o.marca.style.opacity = k > 0.001 ? 1 : 0;
      });

      // ---- bloque 3
      const o3 = fund(t, 10.4, 11.4, 14.9, 15.5);
      pon(marcoE, { o: o3, s: lerp(0.95, 1, an(t, 10.4, 11.6, E.out4)), blur: lerp(16, 0, an(t, 10.4, 11.4)) });
      pon(etq100, { o: an(t, 12.1, 12.7) * o3 }); pon(etq300, { o: an(t, 12.9, 13.5) * o3 });
      // (los elementos del bloque 3 hijos de marcoE heredan su opacidad; las etiquetas son hermanas)
      puntoE.setAttribute('opacity', an(t, 11.2, 11.8));
      H.trazo(v100, an(t, 11.8, 12.6, E.io2)); H.trazo(v300, an(t, 12.6, 13.4, E.io2));
      v100.style.strokeDasharray = an(t, 11.8, 12.6) >= 1 ? 'none' : v100.style.strokeDasharray; v300.style.strokeDasharray = an(t, 12.6, 13.4) >= 1 ? 'none' : v300.style.strokeDasharray;
      pon(maskA, { o: an(t, 13.2, 13.9) * 0.95 }); pon(maskP, { o: an(t, 13.8, 14.5) * 0.9 });
      entRows.forEach((o, i) => {
        const a = 12.0 + i * 0.5, ap = an(t, a, a + 0.7, E.out4);
        pon(o.caja, { o: ap * (1 - an(t, 14.9, 15.5)), x: lerp(50, 0, ap), blur: lerp(10, 0, ap) });
        const k = an(t, a + 0.3, a + 1.3, E.out4);
        if (i < 2) H.num(o.val, o.r.v, k, 3); else H.num(o.val, o.r.v * 100, k, 0, ' %');
        o.val.textContent = o.val.textContent.replace('-', '−');
      });
      pon(nota3, { o: an(t, 14.0, 14.8) * (1 - an(t, 14.9, 15.5)), y: lerp(20, 0, an(t, 14.0, 14.8)) });

      // ---- bloque 4
      const o4 = fund(t, 15.3, 16.0, 17.7, 18.3);
      pon(ficha, { o: o4, y: lerp(40, 0, an(t, 15.3, 16.1, E.out4)), s: lerp(0.97, 1, an(t, 15.3, 16.2, E.out4)), blur: lerp(14, 0, an(t, 15.3, 16.0)) });
      fichaCab.forEach((c, i) => pon(c, { o: an(t, 15.5 + i * 0.1, 16.0 + i * 0.1) }));
      fichaFilas.forEach(o => { const a = 15.7 + o.n * 0.07, ap = an(t, a, a + 0.5, E.out3); pon(o.r, { o: ap, x: lerp(24, 0, ap) }); });
      pon(pieFicha, { o: an(t, 16.9, 17.4) * (1 - an(t, 17.7, 18.3)) });

      // ---- bloque 5
      radares.forEach((r, ci) => {
        const a = 18.6 + ci * 0.45, ap = an(t, a, a + 0.7, E.out3), k = an(t, a + 0.2, a + 1.5, E.out4);
        pon(r.caja, { o: ap, blur: lerp(12, 0, ap) });
        const P = VARS.map((v, i) => { const f = clamp(NORM[v](PX[r.tipo].variables[v]), 0.03, 1) * k; const an_ = r.ang(i); return [RC + RR * f * Math.cos(an_), RC + RR * f * Math.sin(an_)]; });
        r.poly.setAttribute('d', 'M' + P.map(p => p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('L') + 'Z');
        r.puntos.forEach((c, i) => { c.setAttribute('cx', P[i][0]); c.setAttribute('cy', P[i][1]); });
        pon(r.pie, { o: an(t, a + 0.8, a + 1.4), y: lerp(20, 0, an(t, a + 0.8, a + 1.5)) });
      });
      pon(leyenda, { o: an(t, 20.4, 21.0) });
    };
  },
});
