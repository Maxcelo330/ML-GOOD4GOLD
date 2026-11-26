# Plan: llevar el visor a la web, al celular y a la app de Good4Gold

Estado: propuesta (26-nov-2026). Nada de esto está construido todavía salvo lo marcado como **listo**.

## 1. El problema de fondo
El visor tiene dos mitades distintas:

| Mitad | Qué hace | ¿Puede vivir en una página web estática (GitHub Pages)? |
|---|---|---|
| **Ver y verificar** | Mapa, lista de zonas, ficha, comparación antes / después (Esri Wayback), mapa de calor, revisión de la persona | **Sí.** Son HTML, JS y imágenes. |
| **Opinión de Claude** | Llama a la API con una clave secreta | **No directo**: la clave quedaría a la vista de cualquiera. Necesita un intermediario con contraseña. |
| **Analizar un bloque nuevo** | Baja Sentinel-2 (1 a 3 min), corre LightGBM, filtros | **No.** Es Python con rasterio y lightgbm; necesita un servidor. |
| **Aprender** | Reentrena con las revisiones | **No.** Python; se hace en el "laboratorio". |

## 2. La app de Good4Gold ya trae lo que falta
El repositorio `Good4gold` (PWA "Registro y Control Minero", HTML y JS por módulos, instalable en el celular, funciona sin conexión) ya resuelve tres cosas:
- **Módulos:** una sección nueva es un archivo `js/modules/<nombre>.js` con `G4G.app.register({...})` y una línea `<script>` en `index.html`. Nada más se toca.
- **Login con roles:** el backend `backend/Codigo.gs` (Google Apps Script) ya tiene usuarios, claves cifradas y perfil "funcionario". Esa sesión puede ser la "contraseña" de la IA.
- **Publicación:** GitHub Pages + `sw.js`, con https (necesario para instalar en el celular).

## 3. Arquitectura recomendada (3 niveles)
```
[Celular / web / app Good4Gold]            <- HTML estático (GitHub Pages)
   mapa + zonas + comparación + revisión
        |                    |
        | zonas.json         | "pedir opinión" (con sesión de funcionario)
        v                    v
 archivos estáticos      Apps Script (Codigo.gs)  --> API de Claude
 (zonas, recortes)       guarda la clave, cuenta el gasto, pone tope
        ^
        | publica resultados (script del laboratorio)
 [Laboratorio: este computador]
   analiza bloques, aprende, reentrena
```
- **Nivel 1, la página (nueva):** módulo `js/modules/deteccion.js` en la app, grupo "técnico" (solo funcionarios). Usa las zonas ya calculadas, la comparación antes / después con Esri Wayback (el navegador baja las imágenes directo, no necesita servidor), y guarda la revisión en la hoja de Google mediante el backend que ya existe.
- **Nivel 2, la IA protegida:** una función nueva en `Codigo.gs` (`opinionIA`) que recibe la zona y las imágenes, usa la clave guardada en las propiedades del script (nunca en el navegador), exige sesión de funcionario, lleva un contador de gasto y un tope diario, y devuelve el JSON del veredicto. Costo: lo mismo que hoy, centavos por zona.
- **Nivel 3, el laboratorio:** lo que ya existe. Analiza bloques nuevos y reentrena. Publica a la web un `zonas.json` y los recortes de imagen de cada zona (script nuevo `publicar_web.py`). Las revisiones de la hoja de Google se leen de vuelta para aprender.

## 4. Qué se logra y qué no
- **Se logra:** que cualquier funcionario con sesión abra el mapa en el celular, vea las zonas ya detectadas, compare antes / después, pida la opinión de Claude y marque su revisión, todo sin instalar Python.
- **No se logra con esto:** analizar un bloque nuevo desde el celular. Eso necesita un servidor con Python. Opciones si se quiere más adelante: (a) dejar el laboratorio encendido con un túnel https (Cloudflare Tunnel, gratis) y que la página llame a `G4G_API_BASE` (ya soportado por el visor, con contraseña y CORS por `G4G_ORIGENES`); (b) un contenedor en un servicio en la nube (por ejemplo Hugging Face Spaces o Cloud Run), con costo o límites de uso.

## 5. Pasos propuestos (en orden, cada uno se puede probar solo)
1. **Hecho:** el visor usa colores de IA en naranja, pide contraseña para IA / analizar / guardar, se adapta al celular y puede apuntar a otro servidor (`window.G4G_API_BASE`).
2. `publicar_web.py` (laboratorio): exporta `zonas.json` (zonas del piloto y de los bloques elegidos) y los recortes `natural` y `puntaje` de cada zona como imágenes pequeñas. *Prueba:* abrir los archivos y ver que coinciden con el visor local.
3. Módulo `deteccion.js` en `Good4gold`: lista + mapa + ficha + comparación con cortina (se reutiliza casi todo el código del visor). *Prueba:* abrir `index.html` en el celular y comparar una zona.
4. `opinionIA` en `Codigo.gs` con sesión, tope y contador. *Prueba:* una zona, ver el costo y el veredicto; probar que sin sesión rechaza.
5. Revisión de la persona hacia la hoja de Google y de vuelta al laboratorio para aprender.
6. Publicar en GitHub Pages y probar instalada en un celular (https).

## 5b. Ya hecho: respaldo cifrado en el repo (26-nov-2026)
Para llevar lo analizado a otros equipos sin exponer las zonas: `05_CODIGO/sincronizar.py` y los botones "Guardar en el repo" y "Traer del repo" del visor (ver `07_VISOR/LEEME.md`). El archivo `04_DATOS/respaldo_cifrado/respaldo.g4g` va al repo cifrado con su propia clave (`clave_respaldo.txt`, distinta del usuario y contraseña de la IA); sin ella no se lee. Es un puente mientras no exista el backend web: en la etapa web, las zonas se sirven con sesión de funcionario y este respaldo deja de ser necesario. Límite: la protección es tan fuerte como la clave del respaldo (es larga y al azar; no usar una corta como la de acceso) y el cifrado usa solo la biblioteca estándar de Python (scrypt + HMAC-SHA256, cifrar y autenticar); si se prefiere AES-GCM hay que instalar la biblioteca `cryptography` en el entorno.

## 6. Decisiones que hay que tomar
- **Datos y confidencialidad (D-002):** las zonas son "por verificar". Publicarlas en una página pública las hace públicas. Recomendación: solo detrás del login de funcionario, y no subir `zonas.json` a un repositorio público; servirlo desde el backend con sesión.
- **Quién paga la API:** la clave del script queda a nombre de quien la cree. Definir el tope diario.
- **Límites de Esri Wayback:** los términos de uso de Esri para producción deben revisarse (el README de la app ya lo avisa para el mapa base).
