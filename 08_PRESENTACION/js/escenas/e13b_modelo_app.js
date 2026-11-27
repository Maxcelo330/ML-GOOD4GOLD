/* Escena 13b - El modelo y la app, un solo flujo (22 s).
   Muestra lo facil que es usar el modelo y como se conecta con la app:
     1) un doble clic (EJECUTAR-VISOR.bat: revisa el equipo, instala lo que falte preguntando antes, abre el visor)
     2) una persona revisa cada zona (parece / no parece actividad minera)
     3) un boton arma UN archivo para la app (ZIP: GeoJSON + Excel con las columnas de la app + CSV + LEEME)
     -> en la app: Municipio > Detecciones revisadas > Cargar archivo de zonas.
   La captura es del visor REAL (con el diseno nuevo) en modo demostracion: la revision de la zona es de prueba, no es un hallazgo.
   Se recorto para no mostrar coordenadas. Todo es funcion pura de t. */
Pres.escena({
  id: 'modeloapp', titulo: 'Del modelo a la app', dur: 22,
  recursos: ['assets/capturas/visor_nuevo_mapa.jpg'],
  subs: [
    [0.5, 4.5, 'Usar el modelo no pide saber de programación: basta un doble clic.'],
    [4.7, 8.6, 'El programa revisa el equipo y, si falta algo, lo instala preguntando antes.'],
    [8.8, 12.4, 'Una persona revisa cada zona y marca si parece o no actividad minera.'],
    [12.6, 16.6, 'Un botón arma un solo archivo para la app: el mapa, un Excel con sus columnas, un CSV y los pasos.'],
    [16.8, 21.2, 'En la app, el funcionario carga el mapa y las zonas aparecen listas para verificar en campo.'],
  ],
  montar(raiz, H) {
    const { el, pon, an, E, lerp, img } = H;
    const A = (clase, html, padre, st) => { const e = el('div', clase, html, padre); e.style.position = 'absolute'; Object.assign(e.style, st || {}); return e; };
    const ent = (e, p, dy = 40, bl = 14, extra) => pon(e, Object.assign({ o: p, y: lerp(dy, 0, p), blur: lerp(bl, 0, p) }, extra || {}));
    const ORO = '#e0a82a', MOR = '#9775fa';

    const tit = A('titulo xs centro', 'Del modelo a <span class="g-oro">la app</span>', raiz, { left: '0', right: '0', top: '44px', fontSize: '62px' });

    // ---- captura del visor (izquierda). Imagen natural 1080 x 900; se muestra a F = 842 / 1080
    const F = 842 / 1080, FX = 80, FY = 150;
    const marco = el('div', 'marco-web', null, raiz);
    Object.assign(marco.style, { left: FX + 'px', top: FY + 'px', width: '842px', height: (44 + Math.round(900 * F)) + 'px' });
    const im = img('assets/capturas/visor_nuevo_mapa.jpg', null, marco);
    // caja de resalte sobre el boton y el mensaje del paquete (coordenadas de la imagen recortada: x 60..312, y 460..565)
    const caja = A('', null, raiz, { left: (FX + 60 * F) + 'px', top: (FY + 44 + 460 * F) + 'px', width: (252 * F) + 'px', height: (105 * F) + 'px',
      border: '4px solid ' + ORO, borderRadius: '10px', boxShadow: '0 0 40px rgba(224,168,42,.55)' });
    const demo = A('pastilla', 'Captura del visor · revisión de demostración', raiz, { left: (FX + 18) + 'px', top: (FY + 44 + Math.round(900 * F) - 66) + 'px', fontSize: '24px', background: 'rgba(0,0,0,.7)', borderColor: 'rgba(224,168,42,.6)' });

    // ---- tres pasos (derecha)
    const CX = 980, CW = 860, CH = 188, GAP = 22;
    const PASOS = [
      ['1', 'Un doble clic', 'EJECUTAR-VISOR.bat revisa el equipo, instala lo que falte (pregunta antes) y abre el visor.'],
      ['2', 'Una persona revisa', 'Cada zona se marca: parece o no parece actividad minera. El modelo propone, la persona decide.'],
      ['3', 'Un botón: paquete para la app', 'Un ZIP con el mapa (GeoJSON), un Excel con las columnas de la app, un CSV y los pasos.'],
    ];
    const cards = PASOS.map((p, i) => {
      const c = A('tarjeta', null, raiz, { left: CX + 'px', top: (FY + i * (CH + GAP)) + 'px', width: CW + 'px', height: CH + 'px', borderRadius: '26px', overflow: 'hidden' });
      const n = A('num', p[0], c, { left: '28px', top: '34px', width: '62px', height: '62px', borderRadius: '50%', display: 'grid', placeItems: 'center', fontSize: '36px', color: '#1a1a22', background: ORO });
      A('', p[1], c, { left: '116px', top: '26px', width: (CW - 140) + 'px', font: '800 38px/1.1 var(--fuente-titulo)', letterSpacing: '-.02em', color: '#fff' });
      A('', p[2], c, { left: '116px', top: '84px', width: (CW - 150) + 'px', font: '400 27px/1.3 var(--fuente-texto)', color: 'var(--suave)' });
      c._n = n; return c;
    });

    // ---- destino: ZIP -> app
    const DY = FY + 3 * (CH + GAP) - 6;
    const zip = A('pastilla mono', 'zonas_para_la_app.zip', raiz, { left: CX + 'px', top: DY + 'px', fontSize: '26px', borderColor: 'rgba(224,168,42,.6)', background: 'rgba(224,168,42,.12)' });
    const flecha = A('', '→', raiz, { left: (CX + 372) + 'px', top: (DY - 4) + 'px', width: '70px', textAlign: 'center', font: '700 46px var(--fuente-num)', color: ORO, transformOrigin: '0 50%' });
    const app = A('pastilla', 'App › Detecciones revisadas', raiz, { left: (CX + 452) + 'px', top: DY + 'px', fontSize: '26px', whiteSpace: 'nowrap', borderColor: 'rgba(151,117,250,.55)', background: 'rgba(151,117,250,.14)' });

    return t => {
      ent(tit, an(t, 0.2, 1.0, E.out4), 25, 10);
      ent(marco, an(t, 0.6, 1.6, E.out4), 40, 14);
      pon(demo, { o: an(t, 1.6, 2.2) });
      // pasos: entran uno a uno y se iluminan mientras se explican
      [[1.6, 2.0, 8.8], [7.0, 7.4, 12.6], [11.0, 11.4, 16.8]].forEach(([t0, a0, a1], i) => {
        ent(cards[i], an(t, t0, t0 + 0.9, E.out4), 40, 12);
        const act = an(t, a0, a0 + 0.5) * (1 - an(t, a1, a1 + 0.5));
        cards[i].style.borderColor = `rgba(224,168,42,${0.12 + 0.8 * act})`;
        cards[i]._n.style.transform = `scale(${1 + 0.12 * act})`;
      });
      // resalte del boton "Preparar paquete" y su mensaje
      const r = an(t, 12.6, 13.2, E.out3) * (1 - an(t, 16.4, 17.0));
      pon(caja, { o: r, s: lerp(1.08, 1, an(t, 12.6, 13.4, E.out3)) * (1 + 0.012 * Math.sin(Math.max(0, t - 13) * 5) * r) });
      // destino
      pon(zip, { o: an(t, 15.8, 16.5) });
      pon(flecha, { o: an(t, 16.4, 16.9), sx: lerp(0.2, 1, an(t, 16.4, 17.0, E.out4)) });
      const a = an(t, 16.9, 17.7, E.out4); ent(app, a, 16, 8);
      app.style.boxShadow = `0 0 ${Math.round(34 * an(t, 18.0, 18.8) * (1 - an(t, 20.8, 21.6)))}px rgba(151,117,250,.6)`;
    };
  },
});
