"""
Segunda opinion de Claude sobre una zona detectada.

Que hace: toma la imagen Sentinel-2 del bloque (ya guardada por analisis_bloque.py), recorta tres vistas de
la zona (color natural con el contorno, color natural de cerca y falso color infrarrojo/SWIR), se las manda a
Claude por la API junto con los datos del modelo, y devuelve un veredicto con sus motivos.

Para que sirve: el modelo solo mira numeros de cada pixel; Claude mira la FORMA y el CONTEXTO (pozas, cicatrices
en el bosque, parcelas, banco de arena junto a un rio...) y puede detectar falsos positivos. Cada opinion se
guarda en 04_DATOS/opiniones_ia/ y sirve despues como etiqueta para reentrenar el modelo (paso10).

Limites (se muestran en el visor):
  - Es la opinion de una IA mirando una imagen de 20 m. NO es verificacion de campo ni dice si algo es legal.
  - Necesita una clave de la API de Claude (variable de entorno ANTHROPIC_API_KEY, o un archivo
    'clave_api.txt' en la raiz del proyecto; ese archivo NO va a git) e internet. Cada opinion cuesta centavos.
  - Puede equivocarse. Cuando discrepa del modelo, la decision la toma la persona.
"""
import base64
import io
import json
import os
import re
from pathlib import Path

import pyproj
import requests
from PIL import Image, ImageDraw
from shapely.geometry import shape
from shapely.ops import transform as sh_transform

RAIZ = Path(__file__).resolve().parents[1]
BLOQUES = RAIZ / "04_DATOS" / "analisis_bloques"
OPINIONES = RAIZ / "04_DATOS" / "opiniones_ia"
URL_API = "https://api.anthropic.com/v1/messages"
MODELO_IA = os.environ.get("G4G_MODELO_IA", "claude-sonnet-5-5")
RES = 20.0
LADO_PX = 640
VEREDICTOS = ("probable_mineria", "dudoso", "probable_no_mineria")


class ErrorOpinion(Exception):
    """Error que se le explica a la persona."""


def clave_api():
    k = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not k:
        f = RAIZ / "clave_api.txt"
        if f.exists():
            k = f.read_text(encoding="utf-8").strip()
    return k


def disponible():
    return bool(clave_api())


def _vistas(resumen, geom_wgs):
    """Tres imagenes PNG (bytes) de la zona: contexto con contorno, cerca natural, cerca en falso color."""
    clave_img = resumen["clave_img"]
    nat_p, fal_p = BLOQUES / f"{clave_img}_natural.png", BLOQUES / f"{clave_img}_falso.png"
    if not (nat_p.exists() and fal_p.exists()):
        raise ErrorOpinion("No esta la imagen guardada de este bloque. Vuelve a analizar el bloque.")
    nat, fal = Image.open(nat_p).convert("RGB"), Image.open(fal_p).convert("RGB")
    x0, y1 = resumen["origen_m"]
    tr = pyproj.Transformer.from_crs(4326, resumen["epsg_m"], always_xy=True)
    z = sh_transform(tr.transform, geom_wgs)
    # a pixeles de la imagen (columna, fila)
    zp = sh_transform(lambda x, y, zz=None: ((x - x0) / RES, (y1 - y) / RES), z)
    minx, miny, maxx, maxy = zp.bounds
    lado = max(maxx - minx, maxy - miny)

    def recorte(img, margen, contorno):
        m = max(margen, 20)
        c = (int(max(minx - m, 0)), int(max(miny - m, 0)), int(min(maxx + m, img.width)), int(min(maxy + m, img.height)))
        im = img.crop(c)
        esc = LADO_PX / max(im.size)
        im = im.resize((max(1, round(im.width * esc)), max(1, round(im.height * esc))), Image.LANCZOS)
        if contorno:
            d = ImageDraw.Draw(im)
            geoms = zp.geoms if hasattr(zp, "geoms") else [zp]
            for p in geoms:
                pts = [((x - c[0]) * esc, (y - c[1]) * esc) for x, y in p.exterior.coords]
                d.line(pts, fill=(255, 235, 0), width=2)
        b = io.BytesIO()
        im.save(b, "PNG")
        return b.getvalue()

    return [recorte(nat, lado * 1.5, True), recorte(nat, lado * 0.25, False), recorte(fal, lado * 0.25, False)]


PROMPT = """Eres analista de teledetección y ayudas a revisar zonas que un modelo marcó como POSIBLE actividad minera de oro (aluvial o artesanal). \
Recibes tres recortes de Sentinel-2 (20 m por píxel, mediana de mayo a septiembre de 2026):
1) color natural con el contorno de la zona en amarillo y bastante contexto alrededor;
2) color natural de cerca, sin contorno;
3) falso color (SWIR-infrarrojo-rojo: suelo desnudo en tonos rosados/salmón, vegetación verde intenso, agua oscura o azul).

Datos del modelo: área {area_ha} ha; puntaje del modelo {puntaje}/100 (relativo, no es una probabilidad); NDVI mediano de la zona {ndvi}; \
distancia al río más cercano {rio}; distancia al poblado más cercano {pob}; {lugar}.

Pistas de minería aluvial/artesanal: pozas o lagunas de agua turbia (verde, turquesa o café) con bordes irregulares o rectangulares, \
suelo removido claro con textura de montículos y cicatrices, patrón de piscinas conectadas, caminos o pistas que llegan a la zona, \
bosque arrasado alrededor, y a veces maquinaria o campamentos.
Confusiones frecuentes (NO son minería): banco de arena o playa de un río natural (forma alargada y pegada al cauce, sin pozas), \
parcelas agrícolas o pastizales (geometría regular, tonos uniformes), quemas y derrumbes naturales (sin pozas ni caminos), \
suelo o roca natural en laderas, nubes o sombras, ciudades y caminos.

Responde SOLO con un JSON, sin texto antes ni después, con estas claves:
{{"veredicto": "probable_mineria" | "dudoso" | "probable_no_mineria",
  "confianza": "alta" | "media" | "baja",
  "que_parece": "una frase corta: qué tipo de terreno es",
  "motivos": ["2 a 4 motivos concretos que ves en las imágenes"],
  "que_revisar": "una frase: qué conviene comprobar (imagen de alta resolución, catastro, visita)"}}
Usa lenguaje no punitivo: nunca digas que algo es ilegal; solo describe lo que ves. Si no puedes decidir con estas imágenes, di "dudoso"."""


def pedir_opinion(clave, id_zona):
    """Pide la opinion sobre una zona de un analisis guardado. Devuelve un dict (y lo guarda)."""
    if not disponible():
        raise ErrorOpinion("Falta la clave de la API de Claude. Pon ANTHROPIC_API_KEY en el entorno o guarda la clave en un archivo "
                           "'clave_api.txt' en la carpeta del proyecto (no se sube a git).")
    if not re.fullmatch(r"[0-9a-f]{12}", clave or "") or not re.fullmatch(r"[A-Za-z0-9\-]{3,20}", id_zona or ""):
        raise ErrorOpinion("Zona no valida.")
    ruta = BLOQUES / f"{clave}.json"
    if not ruta.exists():
        raise ErrorOpinion("No se encuentra el analisis de ese bloque.")
    res = json.loads(ruta.read_text(encoding="utf-8"))
    feat = next((f for f in res["zonas"]["features"] if f["properties"]["id"] == id_zona), None)
    if feat is None:
        raise ErrorOpinion("No se encuentra esa zona.")
    destino = OPINIONES / f"{clave}_{id_zona}.json"
    if destino.exists():
        return json.loads(destino.read_text(encoding="utf-8"))
    p = feat["properties"]
    vistas = _vistas(res["resumen"], shape(feat["geometry"]))
    m = lambda v: "sin dato" if v is None else f"{v} m"  # noqa: E731
    texto = PROMPT.format(area_ha=p["area_ha"], puntaje=p["puntaje_modelo"], ndvi=p.get("ndvi_mediano", "?"), rio=m(p.get("dist_rio_m")),
                          pob=m(p.get("dist_poblado_m")), lugar=f"ubicación {p['lat']}, {p['lng']}")
    contenido = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(v).decode()}} for v in vistas]
    contenido.append({"type": "text", "text": texto})
    try:
        r = requests.post(URL_API, timeout=90, headers={"x-api-key": clave_api(), "anthropic-version": "2023-06-01", "content-type": "application/json"},
                          json={"model": MODELO_IA, "max_tokens": 700, "messages": [{"role": "user", "content": contenido}]})
    except requests.RequestException:
        raise ErrorOpinion("No se pudo conectar con la API de Claude (sin internet?).")
    if r.status_code == 401:
        raise ErrorOpinion("La clave de la API no es valida.")
    if r.status_code == 429:
        raise ErrorOpinion("La API de Claude pide esperar un momento (limite de uso). Intenta de nuevo en un minuto.")
    if r.status_code >= 400:
        raise ErrorOpinion(f"La API de Claude respondio con error {r.status_code}.")
    try:
        txt = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
        j = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
        if j.get("veredicto") not in VEREDICTOS:
            raise ValueError("veredicto")
    except Exception:  # noqa: BLE001
        raise ErrorOpinion("Claude respondio, pero no en el formato esperado. Intenta de nuevo.")
    salida = {"clave": clave, "id_zona": id_zona, "modelo_ia": MODELO_IA, "veredicto": j["veredicto"], "confianza": j.get("confianza", "baja"),
              "que_parece": str(j.get("que_parece", ""))[:200], "motivos": [str(x)[:240] for x in (j.get("motivos") or [])][:4],
              "que_revisar": str(j.get("que_revisar", ""))[:240],
              "aviso": "Opinion de una IA sobre una imagen de 20 m. No es verificacion de campo ni indica legalidad."}
    OPINIONES.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    return salida
