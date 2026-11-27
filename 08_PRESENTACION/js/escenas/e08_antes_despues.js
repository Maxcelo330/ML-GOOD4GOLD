/* Escena 8 - Antes y despues (18 s).
   Capturas REALES del visor: cortina entre la imagen historica (Esri Wayback) y Sentinel-2 actual, contorno de la zona y mapa de calor.
   Lenguaje no punitivo: lo marcado es "posible actividad minera, por verificar". Sin coordenadas. Todo es funcion pura de t. */
Pres.escena({
  id: 'antes_despues', titulo: 'Antes y después', dur: 18,
  recursos: ['assets/capturas/visor_comp_antes.jpg', 'assets/capturas/visor_comp_ahora.jpg', 'assets/capturas/visor_comp_ahora_c.jpg', 'assets/capturas/visor_comp_calor_c.jpg'],
  subs: [
    [0.5, 3.4, 'Antes de decidir, la persona compara el lugar con una imagen histórica.'],
    [3.6, 8.6, 'La cortina deja ver cómo era antes y cómo se ve hoy en Sentinel-2.'],
    [9.2, 12.0, 'El contorno muestra lo que el modelo marcó: posible actividad minera, por verificar.'],
    [12.4, 15.6, 'El mapa de calor muestra dónde el puntaje es más alto.'],
    [16.0, 17.5, 'La decisión final es de una persona.'],
  ],
  montar(raiz, H) {
    const { el, pon, an, E, lerp, clamp, img } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const MORc = '#9775fa', ORO = '#e0a82a';

    const tit = A('titulo xs centro', 'Mirar <span class="g-morado">antes y ahora</span>', raiz, { left: '0', right: '0', top: '44px', fontSize: '60px' });
    const FW = 1560, FH = 780, FX = 180, FY = 150;
    const marco = A('', null, raiz, { left: FX + 'px', top: FY + 'px', width: FW + 'px', height: FH + 'px', borderRadius: '22px', overflow: 'hidden', background: '#111', boxShadow: '0 50px 120px rgba(0,0,0,.65), 0 0 0 1px rgba(255,255,255,.14)' });
    const cap = src => { const i = img(src, null, marco); Object.assign(i.style, { position: 'absolute', left: '0', top: '0', width: '100%', height: '100%', objectFit: 'cover' }); return i; };
    const ahora = cap('assets/capturas/visor_comp_ahora.jpg');
    const antes = cap('assets/capturas/visor_comp_antes.jpg');
    const cont = cap('assets/capturas/visor_comp_ahora_c.jpg'); cont.style.opacity = 0;
    const calor = cap('assets/capturas/visor_comp_calor_c.jpg'); calor.style.opacity = 0;

    // cortina
    const div = A('', null, marco, { top: '0', width: '6px', height: '100%', marginLeft: '-3px', background: '#fff', boxShadow: '0 0 24px rgba(255,255,255,.8)' });
    const asa = A('', '<svg viewBox="0 0 48 48" width="40" height="40" fill="none" stroke="#111" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"><path d="M16 12L6 24l10 12M32 12l10 12-10 12"/></svg>', marco, { top: (FH / 2 - 34) + 'px', width: '68px', height: '68px', marginLeft: '-34px', borderRadius: '50%', background: '#fff', display: 'grid', placeItems: 'center', boxShadow: '0 10px 30px rgba(0,0,0,.5)' });
    const rot = (txt, col) => A('', txt, marco, { top: '22px', padding: '10px 22px', borderRadius: '999px', background: 'rgba(10,10,15,.78)', font: '600 28px var(--fuente-texto)', color: '#fff', whiteSpace: 'nowrap', borderLeft: '8px solid ' + col });
    const rAntes = rot('Antes · imagen histórica (Esri Wayback)', '#adb5bd'); rAntes.style.left = '22px';
    const rAhora = rot('Ahora · Sentinel-2', '#74c0fc'); rAhora.style.right = '22px';
    const rCont = rot('Contorno de la zona del modelo', MORc); rCont.style.left = '22px';
    const rCalor = rot('Mapa de calor del puntaje', '#ff6b3d'); rCalor.style.left = '22px';

    // fichas de paso
    const PASOS = ['Cortina antes / ahora', 'Contorno del modelo', 'Mapa de calor'];
    const fichas = PASOS.map((p, i) => A('pastilla', p, raiz, { left: (FX + i * 420) + 'px', top: '956px', fontSize: '28px' }));
    const nota = A('', 'Detectar no es confirmar: la persona decide.', raiz, { left: (FX + 1260) + 'px', top: '962px', width: '300px', font: '500 24px/1.25 var(--fuente-texto)', color: 'var(--suave)', textAlign: 'right' });

    return t => {
      ent(tit, an(t, 0.1, 0.9, E.out4), 20, 10);
      ent(marco, an(t, 0.3, 1.3, E.out4), 50, 16);
      fichas.forEach((f, i) => { pon(f, { o: an(t, 1.0 + i * 0.15, 1.6 + i * 0.15) }); });
      pon(nota, { o: an(t, 14.6, 15.4) });

      // posicion de la cortina (fraccion de ancho que muestra "antes")
      let f;
      const a1 = an(t, 1.8, 4.2, E.io2), a2 = an(t, 4.4, 7.6, E.io2), a3 = an(t, 7.8, 9.0, E.io2), a4 = an(t, 9.2, 10.2, E.io2);
      f = 0.5 + (0.08 - 0.5) * a1 + (0.92 - 0.08) * a2 + (0.5 - 0.92) * a3 + (0 - 0.5) * a4;
      f = clamp(f, 0, 1);
      antes.style.clipPath = `inset(0 ${((1 - f) * 100).toFixed(2)}% 0 0)`;
      div.style.left = (f * 100) + '%'; asa.style.left = (f * 100) + '%';
      const dv = 1 - an(t, 9.0, 9.8);
      div.style.opacity = dv; asa.style.opacity = dv;
      const lab = 1 - an(t, 9.0, 9.8);
      pon(rAntes, { o: an(t, 1.4, 2.0) * lab * clamp(f * 8) }); pon(rAhora, { o: an(t, 1.4, 2.0) * lab * clamp((1 - f) * 8) });

      // contorno y calor
      const c = an(t, 10.2, 11.6, E.io2), k = an(t, 12.4, 13.8, E.io2);
      cont.style.opacity = c; calor.style.opacity = k;
      pon(rCont, { o: an(t, 10.6, 11.2) * (1 - an(t, 12.4, 12.9)) });
      pon(rCalor, { o: an(t, 13.2, 13.8) * (1 - an(t, 16.2, 16.8)) });
      fichas.forEach((fi, i) => {
        const act = i === 0 ? (t < 10.0 ? 1 : 0) : i === 1 ? (t >= 10.0 && t < 12.4 ? 1 : 0) : (t >= 12.4 ? 1 : 0);
        fi.style.background = act ? 'rgba(151,117,250,.35)' : 'rgba(255,255,255,.06)';
        fi.style.borderColor = act ? MORc : 'rgba(255,255,255,.16)';
      });
    };
  },
});
