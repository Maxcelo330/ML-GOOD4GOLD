/* Escena 14 - Limites honestos (12 s).
   Todo el texto sale de HECHOS.md, seccion "Limites honestos". Sin dramatismo: tarjetas sobrias y proximos pasos.
   Todo es funcion pura de t. */
Pres.escena({
  id: 'limites', titulo: 'Límites honestos', dur: 12,
  recursos: [],
  subs: [
    [0.5, 4.0, 'Lo que mostramos tiene límites, y los decimos de frente.'],
    [4.2, 7.4, 'Las etiquetas vienen de IA y MapBiomas, no de campo; y no se cruzó con el catastro.'],
    [7.6, 10.0, 'El modelo se equivoca en ciudades y grandes ríos, y no ve minas de menos de 5 hectáreas.'],
    [10.2, 11.6, 'El siguiente paso: validar en campo.'],
  ],
  montar(raiz, H) {
    const { el, pon, an, E, lerp } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const ORO = '#e0a82a', MORc = '#9775fa', VER = '#2fb344';

    const tit = A('titulo xs centro', 'Lo que <span class="g-oro">todavía no podemos decir</span>', raiz, { left: '0', right: '0', top: '54px', fontSize: '62px' });
    const LIM = [
      ['Etiquetas de IA', 'Y de MapBiomas: no son verificación en campo.'],
      ['Mide coincidencia', 'No exactitud frente al terreno.'],
      ['Sin catastro AJAM', 'No dice legalidad ni mercurio.'],
      ['F1 de 0,37 a 0,40', 'En la prueba espacial del piloto.'],
      ['Falsos positivos', 'Ciudades y grandes ríos con bancos de arena.'],
      ['Minas menores de 5 ha', 'No se ven con resolución de 20 m.'],
    ];
    const CW = 560, CH = 232, GX = 30, X0 = 90;
    const cards = LIM.map((l, i) => {
      const c = A('tarjeta', null, raiz, { left: (X0 + (i % 3) * (CW + GX)) + 'px', top: (150 + Math.floor(i / 3) * (CH + 24)) + 'px', width: CW + 'px', height: CH + 'px', borderRadius: '26px', overflow: 'hidden' });
      A('', null, c, { left: '0', top: '0', width: '8px', height: '100%', background: ORO });
      A('num', String(i + 1), c, { left: '38px', top: '22px', fontSize: '30px', color: ORO });
      A('', l[0], c, { left: '38px', top: '68px', width: (CW - 70) + 'px', font: '800 40px/1.1 var(--fuente-titulo)', letterSpacing: '-.02em', color: '#fff' });
      A('', l[1], c, { left: '38px', top: '140px', width: (CW - 70) + 'px', font: '400 29px/1.3 var(--fuente-texto)', color: 'var(--suave)' });
      return c;
    });
    const sig = A('', null, raiz, { left: X0 + 'px', top: '666px', width: '1740px', height: '205px', borderRadius: '26px', background: 'linear-gradient(180deg, rgba(47,179,68,.14), rgba(47,179,68,.04))', border: '2px solid rgba(47,179,68,.4)' });
    A('etiqueta', 'Próximos pasos', sig, { left: '40px', top: '26px', fontSize: '26px', color: '#8ce99a' });
    const PAS = ['Validar 20 a 30 zonas en campo', 'Cruzar con el catastro', 'Más lugares de entrenamiento', 'Backend en la nube con sesión de funcionario'];
    const pills = PAS.map((p, i) => A('pastilla', p, sig, { left: (40 + (i % 2) * 830) + 'px', top: (82 + Math.floor(i / 2) * 62) + 'px', fontSize: '30px' }));
    const nota = A('', 'Instalar es un doble clic, pero el instalador automático aún no se probó en una computadora nueva.', raiz, { left: '0', right: '0', top: '895px', textAlign: 'center', font: '400 26px var(--fuente-texto)', color: 'var(--suave)' });

    return t => {
      ent(tit, an(t, 0.2, 1.0, E.out4), 25, 10);
      cards.forEach((c, i) => ent(c, an(t, 0.8 + i * 0.4, 1.6 + i * 0.4, E.out4), 40, 12));
      ent(sig, an(t, 7.6, 8.6, E.out4), 40, 12);
      pills.forEach((p, i) => pon(p, { o: an(t, 8.2 + i * 0.25, 8.8 + i * 0.25) }));
      pon(nota, { o: an(t, 9.2, 9.8) });
    };
  },
});
