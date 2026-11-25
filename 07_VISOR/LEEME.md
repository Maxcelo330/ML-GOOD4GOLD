# Visor de zonas para revisar (uso interno)

Un solo archivo, `visor.html`, que se abre con doble clic en Chrome o Edge. No necesita QGIS ni instalar nada.

- Se genera con `python 05_CODIGO\paso8_visor_html.py` (después de paso6 y paso7). No va a git porque muestra zonas de posible actividad minera sin verificar (decisión D-002).
- La imagen de fondo necesita internet. Las zonas, ríos y poblados no.
- "Mi revisión" se guarda solo en el navegador de quien la hace; se descarga como CSV.
- Ríos y poblados: (c) colaboradores de OpenStreetMap (ODbL). Son una guía: pueden faltar cauces o caseríos.
- La biblioteca del mapa (Leaflet 1.9.4, licencia BSD-2) está copiada en `lib/leaflet`.
