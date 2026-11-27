# Hechos que se pueden decir en la presentacion (todo verificado en el proyecto)

Regla: nada de cifras ni afirmaciones que no esten aqui. Lenguaje no punitivo: siempre "posible actividad minera, por verificar"; nunca "ilegal", nunca "hay mineria" como hecho confirmado. El puntaje del modelo NO es una probabilidad.

## El reto
- Equipo: **aurum80**. El proyecto NO tiene nombre propio: se presenta como "proyecto", sin nombre de marca. NO mencionar en el video ni que es un hackathon, ni su nombre, ni "desafio ORO 4.2" (decision del equipo, 26-11-2026). "Good4Gold" era solo el nombre del repositorio de la app; no es el nombre del proyecto.
- Zona piloto: norte de La Paz (Tipuani, Mapiri, Teoponte, Guanay), unos 13.000 km2 (13.035 km2).
- Dos tareas: "encontrar" posible actividad minera con imagenes de satelite, y una plataforma para "verificar, controlar y reportar".
- La imagen detecta ACTIVIDAD (suelo removido, pozas), no legalidad ni mercurio. El cruce con el catastro minero (AJAM) aun no se hizo: "por verificar en campo; registro AJAM aun no consultado".

## El satelite y la imagen
- Sentinel-2 (Copernicus, gratuito), via Microsoft Planetary Computer. Cada pixel mide 20 x 20 m (la receta usa bandas de 10 y 20 m llevadas a 20 m).
- Se usan fotos de mayo a septiembre de 2026 (epoca seca: menos nubes). Por pixel se toma la MEDIANA de varias fotos validas (hasta 16 guardadas por pixel; el bloque de ejemplo uso 24 fotos) para quitar nubes y sombras. Se descartan fotos con mas de 30 % de nubes en la escena y pixeles con azul muy alto (nube que se colo).
- Pendiente del terreno: del modelo de elevacion Copernicus GLO-30.
- Un pixel se puntua solo si tiene al menos 3 fotos validas.
- Bloque de ejemplo de la presentacion: 24,9 x 26,7 km, 14 zonas, 497,9 ha en total, imagen util 98 %, 135 s de analisis (la primera vez).

## Las 14 variables de cada pixel (modelo v2)
- 6 bandas: B02 azul, B03 verde, B04 rojo, B08 infrarrojo cercano, B11 y B12 infrarrojo de onda corta (SWIR).
- 3 indices: NDVI (vegetacion), NDWI (agua), BSI (suelo desnudo).
- 1 de relieve: pendiente.
- 4 de contexto (miran el entorno): textura del NDVI a 100 m, NDVI medio a 300 m, fraccion de agua a 300 m, fraccion de suelo pelado a 300 m. Sirven para distinguir un banco de arena de un rio (liso, junto al agua) o una ciudad (NDVI muy cambiante) de una mina (mucho suelo removido alrededor).
- Ejemplos REALES de pixel en assets/datos/pixeles_ejemplo.json (bosque, suelo removido, rio, banco de arena, pastizal). Ojo: el puntaje de pixel de un rio o de un banco de arena puede salir alto (76 y 85 en el ejemplo); por eso hay filtros despues (agua NDWI > 0 se excluye, entorno, tamano).

## El modelo
- LightGBM: un conjunto de 300 arboles de decision pequenos (cada arbol hace preguntas de si/no sobre las variables del pixel; la suma de sus votos da el puntaje). Arboles reales: assets/datos/arbol_ejemplo.json. Peso de cada variable: assets/datos/importancia.json.
- Puntaje de 0 a 100 (relativo, no es probabilidad): sirve para ordenar que revisar primero. Umbral normal 50; "sensibilidad alta" 30.
- El modelo v1 se entreno solo con 9 poligonos mineros y 108 no mineros del norte de La Paz (etiquetas propuestas por Claude mirando imagen, sin campo).
- El modelo v2 se entreno con 31 lugares (12 con mineria y 19 sin: ciudades, rios con bancos de arena, pastos, cultivos) de Peru y Bolivia: la mineria viene de MapBiomas (clase 30 en 2023 Y 2024, clasificacion automatica Landsat 30 m, CC BY-SA 4.0) y se corrigio con la revision de 80 casos por subagentes de Claude (37 de 56 marcas "extra" eran falsos positivos: ciudades, bancos de arena, roca; 7 parecian mineria que MapBiomas no vio).
- Resultados de v1 a v2 (leave-one-block-out, medidos contra MapBiomas y revision con IA, NO contra el terreno): La Pampa (Madre de Dios, bloque que nunca entrena) cobertura 54 % -> 90 %; promedio de 11 bloques con mineria: 39 % -> 66-69 %; hectareas falsas medias en lugares sin mineria: 2.630 -> 1.043-1.528. Con la prueba espacial del piloto (cuadros de 5 km) el F1 del v1 fue 0,37-0,40 contra etiquetas sin verificar en campo.
- Sigue marcando falsos positivos en ciudades (Cochabamba, valle del Mantaro) y grandes rios con bancos de arena cuando no vio ese tipo de lugar. Resolucion de 20 m: una mina de menos de 5 ha no se ve (se descartan zonas < 5 ha).

## De puntos a zonas (reglas, nucleo_zonas.py)
- Un pixel cuenta si su puntaje >= umbral, no es agua (NDWI > 0), no esta a menos de 600 m de un hueco sin datos (nubes).
- Se agrupan pixeles vecinos; la zona debe tener al menos 5 ha, mediana de 7 o mas fotos validas, NDVI mediano < 0,45 y estar rodeada de vegetacion (NDVI del entorno >= 0,5) dentro del piloto. Fuera del piloto estas reglas solo marcan la zona como "confianza parcial".
- Se entregan 30 zonas para revisar en el piloto (mas 13 de lectura visual aparte).

## El visor del modelo (en el computador)
- Se dibuja un bloque (1 a 30 km por lado), con mouse o dedo; analisis de 1 a 3 minutos; barra de avance con 6 etapas (buscar imagenes, descargar, indices y pendiente, correr el modelo, filtrar y trazar zonas, medir distancias a rios y poblados).
- Comparacion antes/despues con cortina: imagen historica de Esri Wayback (fecha elegible) frente a Sentinel-2 2026, con contorno de la zona y mapa de calor del puntaje.
- La persona revisa: "Parece actividad minera" / "No parece" / "No estoy seguro".
- Segunda opinion de Claude (IA, boton naranja): mira 3 recortes y responde veredicto, confianza, que parece, motivos y que revisar. Cuesta unos 0,009 USD (un centavo) por zona (consulta real: 2.324 tokens de entrada y 428 de salida), con contador de gasto y tope de 2 USD. Pide usuario y contrasena (solo las acciones con IA).
- Ejemplo REAL de opinion de Claude (zona B5929-013, confianza media): "Banco de arena o barra de sedimentos pegada al cauce de un rio natural, con vegetacion de ribera, sin pozas visibles." = probable_no_mineria. Es un caso donde la IA corrige al modelo.
- Panel "Modelo vs Claude": porcentaje de zonas que Claude confirma, por rango de puntaje y por version del modelo.
- Aprendizaje: cada opinion de Claude y cada revision de una persona es una etiqueta; las de personas pesan 3, las de Claude 1 o 2. Al juntar 10 nuevas el modelo reentrena solo y SOLO se activa si no empeora en La Pampa (F1 no baja mas de 0,03, cobertura no baja mas de 5 puntos) y si coincide al menos igual con las revisiones en zonas que no vio. El modelo anterior no se borra. Meta: que dependa cada vez menos de Claude.
- Facil de instalar y de conectar con la app (agregado 26-11-2026; ver CONTRATO-DATOS.md): `EJECUTAR-VISOR.bat` revisa el equipo y, si falta Python o el entorno g4g-ml, ofrece instalarlo (pregunta antes; Miniforge solo para el usuario, sin administrador; necesita internet). `EJECUTAR-VISOR.bat /verificar` solo revisa. El instalador automatico NO se ha probado en una computadora limpia (solo la deteccion del entorno ya instalado).
- Boton "Preparar paquete para la app (ZIP)" (probado en el visor): un ZIP con zonas_revisadas.geojson (para Municipio > Detecciones revisadas > Cargar archivo de zonas), zonas_para_registro.xlsx (hoja "Zonas por verificar" con las columnas de la plantilla de pasivos de la app, mas columnas de apoyo), zonas_revisadas.csv, paquete.json (contrato g4g-zonas-v1) y LEEME.txt. Solo entran las zonas que una persona marco "Parece actividad minera". El Excel NO debe cargarse con "Datos > Cargar Excel" de la app: esa carga reemplaza toda la base.
- El visor adopto la identidad de la app (papel calido, tinta, acento dorado, tipografias del INE: Montserrat, Roboto, Roboto Condensed); el violeta sigue siendo el modelo y el naranja la IA.
- Se guardan: analisis de bloques (reaparecen en "Bloques analizados antes"), opiniones, revisiones, y las zonas "Parece actividad minera" se juntan en un GeoJSON para la app. Respaldo cifrado en el repo para llevar todo a otro computador.

## La plataforma web / app (repositorio Good4gold)
- PWA "Registro y Control Minero": HTML y JS, instalable en el celular, funciona sin conexion (service worker). Mapa base Esri.
- Publico (sin cuenta): Inicio (buscador "esta operacion esta en regla?"), Mapa (toca un punto: "Que hay aqui?" con operaciones a menos de 5 km y boton Denunciar), Consultar (operadores y que requisitos les faltan), Denunciar (asistente de 3 pasos: que viste, donde, foto y envio, con codigo de seguimiento; si no hay senal queda "Sin enviar" y se envia sola al volver la conexion).
- Colores del mapa publico: verde = operador legal, amarillo = en proceso, azul = denuncias. El publico NO ve relaves ni colas ni operadores "No legal".
- Funcionario (con usuario y clave): ademas ve rojos (no legal / denuncias por verificar), gris (sin verificar) y los pasivos (relaves y colas) como hexagonos violeta; Resumen, Pasivos (ranking riesgo x valor), Datos, Registrar datos, Denuncias recibidas (estado y nota de seguimiento) y Detecciones revisadas (carga el GeoJSON del visor y muestra las zonas en mapa y lista).
- Interconexion: con el backend (Google Apps Script + Hoja de Google) las denuncias van a la Hoja y se ven en todos los dispositivos (mapa se actualiza solo cada 60 s). Sin backend: modo demostracion, solo en el dispositivo. Los datos de la demostracion son SIMULADOS (la app lo dice con una franja).
- Confidencialidad (decision D-002): las zonas detectadas por el modelo son datos sensibles; solo las ve el funcionario; no se publican en el repositorio publico.

## Limites honestos (para la escena final)
- Las etiquetas son propuestas por IA y MapBiomas, no verificacion en campo. Las cifras miden coincidencia, no exactitud contra el terreno.
- No se cruzo con el catastro AJAM. No dice legalidad ni mercurio.
- F1 de unos 0,37-0,40 en prueba espacial del piloto; una regla simple de vegetacion rinde parecido salvo en bancos de arena.
- Falsos positivos en ciudades y grandes rios; mina < 5 ha no se ve; analizar bloques nuevos requiere un computador con Windows (aun no desde el celular); el instalador automatico aun no se probo en una computadora nueva.
- Proximos pasos: validar en campo 20-30 zonas, cruzar con el catastro, mas lugares de entrenamiento, backend en la nube con sesion de funcionario.
