/* Escena 11 - Denunciar desde el celular (25 s).
   Capturas REALES de la app (modo demostracion: los datos son SIMULADOS y la app lo dice con una franja).
   Asistente de 3 pasos (que viste, donde, foto y envio) -> codigo de seguimiento -> sin senal: queda "Sin enviar" y se envia sola.
   Las coordenadas aparecen parcialmente ocultas en la propia app. Un puntero falso hace los toques. Todo es funcion pura de t. */
Pres.escena({
  id: 'denuncia', titulo: 'Denunciar desde el celular', dur: 25,
  recursos: ['inicio', 'paso1', 'paso1_sel', 'paso2', 'paso3b', 'paso3c', 'exito', 'exito_sinsenal', 'lista_sinenviar', 'lista_enviada'].map(n => 'assets/capturas/app_cel_' + n + '.png'),
  subs: [
    [0.5, 3.0, 'Cualquier persona puede reportar desde el celular, sin crear una cuenta.'],
    [3.2, 6.3, 'Primero, qué viste.'],
    [6.5, 9.7, 'Después, dónde: se toca el punto en el mapa.'],
    [9.9, 13.4, 'Por último, una foto opcional y declarar que lo reportado es lo que se observó directamente.'],
    [13.8, 17.2, 'Queda registrada con un código de seguimiento y va a la autoridad del municipio para su verificación.'],
    [17.6, 20.4, 'Sin señal, la denuncia queda guardada en el celular.'],
    [20.8, 24.4, 'Y se envía sola cuando vuelve la conexión.'],
  ],
  montar(raiz, H) {
    const { el, pon, an, E, lerp, clamp, img } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const VER = '#2fb344', ORO = '#e0a82a';

    // ---------- telefono
    const PL = 150, PT = 80, PW = 440, PH = 920, K = (PW - 28) / 390;
    const tel = A('marco-cel', null, raiz, { left: PL + 'px', top: PT + 'px', width: PW + 'px', height: PH + 'px', boxSizing: 'border-box' });
    const pant = el('div', 'pantalla', null, tel); Object.assign(pant.style, { position: 'relative', overflow: 'hidden', borderRadius: '52px', background: '#f3efe8' });
    const PANT = [['inicio', 0], ['paso1', 3.0], ['paso1_sel', 4.8], ['paso2', 6.4], ['paso3b', 9.8], ['paso3c', 11.7], ['exito', 13.6], ['exito_sinsenal', 17.4], ['lista_sinenviar', 20.6], ['lista_enviada', 22.7]];
    const imgs = PANT.map(([n]) => { const i = img('assets/capturas/app_cel_' + n + '.png', null, pant); Object.assign(i.style, { position: 'absolute', left: '0', top: '0', width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top center', borderRadius: '0' }); return i; });
    const sp = (x, y) => [PL + 14 + x * K, PT + 14 + y * K];

    // puntero y ondas
    const cur = H.puntero(raiz);
    const CLICKS = [[2.8, 195, 542.6], [4.7, 195, 354.5], [6.2, 309, 985.5], [8.0, 195, 402], [9.6, 309, 771.8], [11.6, 62.5, 566], [13.4, 277.7, 665.5]];
    const ondas = CLICKS.map(() => H.onda(raiz, 'rgba(47,179,68,.9)'));
    const MOV = [[0.9, 2.3, 195, 542.6], [3.2, 4.3, 195, 354.5], [4.9, 5.8, 309, 985.5], [6.7, 7.5, 195, 402], [8.2, 9.1, 309, 771.8], [10.0, 11.4, 62.5, 566], [12.0, 13.0, 277.7, 665.5], [13.9, 14.8, 271, 261.5]];

    // resalte del codigo de seguimiento
    const hc = sp(271, 261.5);
    const resCod = A('', null, raiz, { left: (sp(105, 250)[0]) + 'px', top: (sp(0, 242)[1]) + 'px', width: (570 * K / 2 * 1.0 + 0) + 'px', height: (38 * K) + 'px', border: '4px solid ' + ORO, borderRadius: '10px', boxShadow: '0 0 28px ' + ORO, opacity: 0 });
    // el codigo ocupa (en pantalla 390 CSS px) de x=52 a x=338, y=241 a y=284
    Object.assign(resCod.style, { left: sp(52, 0)[0] + 'px', top: sp(0, 241)[1] + 'px', width: (286 * K) + 'px', height: (43 * K) + 'px' });
    const resChip = A('', null, raiz, { left: sp(279, 0)[0] + 'px', top: sp(0, 521)[1] + 'px', width: (76 * K) + 'px', height: (27.4 * K) + 'px', border: '4px solid ' + ORO, borderRadius: '10px', boxShadow: '0 0 28px ' + ORO, opacity: 0 });

    // ---------- panel derecho
    const tit = A('titulo xs', 'Denunciar en <span class="g-verde">tres pasos</span>', raiz, { left: '720px', top: '70px', fontSize: '62px' });
    const demo = A('pastilla', '<i style="width:14px;height:14px;border-radius:50%;background:' + ORO + ';display:inline-block"></i>Demostración · datos simulados', raiz, { left: '720px', top: '160px', fontSize: '26px', borderColor: 'rgba(224,168,42,.5)', background: 'rgba(224,168,42,.12)' });
    const PASOS = [
      ['1', 'Qué viste', 'Eliges una opción simple, por ejemplo una posible operación sin registro o licencia.', 3.0, 6.4],
      ['2', 'Dónde', 'Tocas el punto en el mapa. Las coordenadas se muestran parcialmente ocultas.', 6.4, 9.8],
      ['3', 'Foto y envío', 'Foto opcional y una declaración: lo reportado es lo que observaste directamente.', 9.8, 13.6],
      ['✓', 'Código de seguimiento', 'Se envía a la autoridad del municipio para su verificación. Guardas el código.', 13.6, 17.4],
      ['↻', 'Sin señal: queda en el celular', 'Figura como «Sin enviar» y se envía sola cuando vuelve la conexión.', 17.4, 25],
    ];
    const RH = 128, RG = 16, RY = 240;
    const cards = PASOS.map((p, i) => {
      const c = A('tarjeta', null, raiz, { left: '720px', top: (RY + i * (RH + RG)) + 'px', width: '1090px', height: RH + 'px', borderRadius: '24px' });
      const n = A('num', p[0], c, { left: '24px', top: '30px', width: '68px', height: '68px', borderRadius: '50%', background: 'rgba(255,255,255,.09)', textAlign: 'center', font: '700 34px/68px var(--fuente-num)', color: '#fff' });
      A('', p[1], c, { left: '120px', top: '12px', font: '800 35px/1.1 var(--fuente-titulo)', letterSpacing: '-.02em', color: '#fff' });
      A('', p[2], c, { left: '120px', top: '56px', width: '930px', font: '400 25px/1.25 var(--fuente-texto)', color: 'var(--suave)' });
      c._n = n; return c;
    });

    return t => {
      ent(tit, an(t, 0.2, 1.0, E.out4), 25, 10);
      pon(demo, { o: an(t, 0.5, 1.2) });
      ent(tel, an(t, 0.2, 1.2, E.out4), 60, 16);

      // pantallas
      PANT.forEach(([n, tin], i) => { imgs[i].style.opacity = i === 0 ? 1 : an(t, tin, tin + 0.35); });

      // puntero
      let x = 300, y = 760;
      MOV.forEach(([t0, t1, tx, ty]) => { const p = an(t, t0, t1, E.io2); x = lerp(x, tx, p); y = lerp(y, ty, p); });
      const [sx, sy] = sp(x, y);
      pon(cur, { x: sx - 8, y: sy - 4 });
      cur.style.opacity = an(t, 0.8, 1.2) * (1 - an(t, 17.0, 17.6));
      CLICKS.forEach((c, i) => { const [cx, cy] = sp(c[1], c[2]); H.ondaPaso(ondas[i], cx, cy, clamp((t - c[0]) / 0.7)); });

      // resaltes
      resCod.style.opacity = an(t, 14.6, 15.1) * (1 - an(t, 17.0, 17.4));
      resChip.style.opacity = an(t, 20.9, 21.4) * (1 - an(t, 24.2, 24.6));
      const bc = t >= 22.7 ? VER : ORO; resChip.style.borderColor = bc; resChip.style.boxShadow = '0 0 28px ' + bc;

      // tarjetas de pasos
      cards.forEach((c, i) => {
        const [, , , t0, t1] = PASOS[i];
        const p = an(t, 0.9 + i * 0.2, 1.7 + i * 0.2, E.out4);
        ent(c, p, 30, 10);
        const act = an(t, t0, t0 + 0.3) * (1 - an(t, t1 - 0.2, t1 + 0.1));
        c.style.borderColor = `rgba(47,179,68,${0.12 + 0.75 * act})`;
        c.style.background = `linear-gradient(180deg, rgba(47,179,68,${0.04 + 0.14 * act}), rgba(255,255,255,.03))`;
        c._n.style.background = act > 0.5 ? VER : 'rgba(255,255,255,.09)';
      });
    };
  },
});
