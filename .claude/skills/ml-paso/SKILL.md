---
name: ml-paso
description: Ensena un paso del plan guiado de ML (01_PLAN/Plan-guiado-ML.md) con el formato concepto, tarea del usuario, tarea de Claude y comprobacion, y espera confirmacion antes de avanzar. Usar cuando el usuario pida empezar, continuar o explicar un paso del proyecto de deteccion minera con QGIS y ML, o diga "siguiente paso".
argument-hint: "[numero de paso, opcional]"
---

# ml-paso: ensenar un paso a la vez

El usuario es geologo/a sin experiencia en machine learning. Este proyecto sirve tambien para aprender. Esta skill impone el ritmo: **un paso, una confirmacion**.

## 1. Ubicar el paso
- Si se paso un numero (`$ARGUMENTS`), ese es el paso. Si no, deducir el paso actual: leer `01_PLAN/Plan-guiado-ML.md` y revisar que existe ya en el repo (`02_ENTORNO/`, `04_DATOS/`, `05_CODIGO/`) y en el historial de la conversacion.
- Decir en una linea en que paso estamos y por que (ej. "Paso 2: ya existe zona_piloto.gpkg, falta ver imagenes en QGIS").
- Nunca avanzar al paso siguiente sin que el usuario confirme que la comprobacion del anterior salio bien.

## 2. Entregar el paso con esta estructura exacta
Usar estos cuatro encabezados, en este orden:

**Concepto**
- Maximo unas 10 lineas. Lenguaje de geologo, con una analogia de su trabajo (ej. aprender a reconocer una mina viendo muchos ejemplos).
- Definir cada termino tecnico la primera vez que aparece (CRS, banda, NDVI, etiqueta, sobreajuste...).
- Resaltar lo clave con `<mark>` o callouts de Obsidian (`> [!note]`, `> [!warning]`). Sin emojis.

**Que haces tu**
- Pasos numerados, concretos, uno por accion (menu de QGIS, boton, valor a escribir).
- Decir que deberia verse en pantalla en cada paso importante.
- Maximo 5 a 7 acciones; si hay mas, partir el paso.

**Que hago yo**
- Lo que ejecuto o escribo (script, comando, descarga), con el comando exacto.
- Si implica instalar software, descargar datos pesados o tocar el sistema: **pedir visto bueno antes**.
- Todo codigo con comentarios en espanol que expliquen cada bloque.

**Comprobacion**
- Una verificacion simple y observable (algo que se ve en QGIS o una salida de terminal) que diga "paso completo".
- Indicar que hacer si no sale (error comun y como resolverlo).

## 3. Cerrar y esperar
- Terminar preguntando una sola cosa: si la comprobacion salio bien o que vio el usuario.
- **No continuar solo.** No ejecutar el siguiente paso, no preguntar por varios pasos a la vez.

## 4. Reglas que siempre aplican
- Respetar `CLAUDE.md`: el Excel del desafio es sintetico; la imagen detecta actividad minera, no legalidad; tono no punitivo; validacion espacial por bloques; CRS EPSG:32719 para medir.
- En pasos de modelo (5 en adelante), pedir al usuario que **prediga la metrica antes de verla** y reportar los resultados tal cual salgan.
- Antes de reportar metricas, sugerir pasar el agente `revisor-ml` (cuando exista).
- Si el usuario se atasca o pide ir mas rapido, simplificar el concepto, no saltar la comprobacion.
- Si el paso exige un dato factual (fuente, licencia, cifra), delegarlo a Gemini via una nota V-xxx en lugar de afirmarlo.

## 5. Registro
Al cerrar un paso confirmado, resumir en 2 lineas: que se aprendio y que archivo/capa quedo creado. Si cambia el plan o el cronograma, proponer editar `01_PLAN/Plan-guiado-ML.md` (no editarlo sin confirmacion).
