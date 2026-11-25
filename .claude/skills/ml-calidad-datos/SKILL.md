---
name: ml-calidad-datos
description: Lista de control de calidad de datos geoespaciales antes de entrenar o reportar un modelo (CRS, geometrias validas, columna clase, solapes entre clases, balance, nodata, alineacion de rasters, semillas, metadata.json). Usar antes de entrenar, tras digitalizar etiquetas en QGIS, o al recibir nuevos rasters o GeoPackage.
argument-hint: "[ruta a .gpkg o carpeta de rasters]"
---

# ml-calidad-datos: control de calidad antes de entrenar

> [!note] Idea clave
> En ML la calidad de las etiquetas y de la grilla manda mas que el algoritmo: "basura entra, basura sale". Esta skill revisa lo mecanico con un script y lo criterioso con una lista que se discute con el usuario.

## 1. Correr el script de verificacion
El script esta en `.claude/skills/ml-calidad-datos/check_datos.py` y necesita el entorno `g4g-ml` (geopandas y rasterio):

```
& "$HOME\anaconda3\envs\g4g-ml\python.exe" -I ".claude\skills\ml-calidad-datos\check_datos.py" <ruta> [--capa NOMBRE] [--columna-clase clase] [--crs EPSG:32719]
```

- `<ruta>` puede ser un `.gpkg` (vectores), un `.tif` o una carpeta con varios `.tif` (rasters).
- El script solo lee; no modifica ningun dato.
- Si falta el entorno, avisar al usuario antes de crearlo (instalar software requiere visto bueno).

## 2. Que revisa el script
**Vectores (.gpkg)**
- CRS definido y, si se indica, igual a EPSG:32719.
- Geometrias nulas, vacias o invalidas.
- Si existe la columna de clase: valores nulos, conteo y porcentaje por clase, aviso de desbalance (una clase menor a 20 por ciento) o de pocas muestras (menos de 30 por clase).
- Solapes entre poligonos de clases distintas (la misma zona etiquetada como mina y no mina).
- Area de cada clase en km2 y poligonos diminutos (menores a 1 pixel de 20 m, es decir 400 m2).

**Rasters (.tif)**
- CRS, resolucion, tamano, tipo de dato y valor nodata definido.
- Porcentaje de pixeles nodata o NaN.
- Con varios rasters: misma grilla (CRS, resolucion, extension y transformada identicos). Si no coinciden, no se pueden apilar como variables del modelo.

## 3. Lista de criterio (revisar con el usuario, el script no la cubre)
- [ ] Hay positivos **y** negativos variados (bosque, rio limpio, agricultura, pueblo), no solo "mina vs bosque".
- [ ] Las etiquetas se digitalizaron sobre imagen de la misma epoca que las variables (epoca seca).
- [ ] Sesgo de muestreo: las etiquetas no estan todas en una sola subzona; se reparten por el area piloto.
- [ ] Las fuentes abiertas usadas como apoyo (MapBiomas, Global Mining Footprint) tienen licencia verificada por Gemini (V-004).
- [ ] Semillas fijas en todo el codigo que sortee datos; versiones de librerias anotadas.
- [ ] `metadata.json` con fechas, IDs de escena, fuente, versiones y semilla.
- [ ] Hay un plan de **validacion espacial por bloques** (no aleatoria) antes de entrenar.
- [ ] El Excel sintetico del desafio no se mezcla con los datos de entrenamiento.

## 4. Reportar
Entregar una tabla corta: item, resultado (`<mark>` verde ok / amarillo aviso / rojo error) y accion recomendada. Si hay errores rojos, **no entrenar** hasta corregirlos. Sin emojis. No arreglar los datos del usuario en silencio: explicar el hallazgo y proponer la correccion.
