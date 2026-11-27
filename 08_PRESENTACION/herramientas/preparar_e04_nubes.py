"""Escena 4 (como ve el satelite): genera las imagenes de la ilustracion de nubes y copia las imagenes nativas para el zoom.
Salida en assets/capturas/ con prefijo satelite_.  Se corre una vez:  python -I 08_PRESENTACION\herramientas\preparar_e04_nubes.py
- satelite_nat.png / satelite_fal.png : imagen nativa (1 pixel de la imagen = 1 pixel del analisis), para el zoom con rejilla.
- satelite_nube_1..4.jpg : recorte REAL del bloque con nubes y sombras SINTETICAS (ilustracion).
- satelite_nube_mediana.jpg : la mediana real (pixel a pixel) de esas 4 fotos -> las nubes desaparecen."""
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

RAIZ = Path(__file__).resolve().parents[2]
SAL = RAIZ / "08_PRESENTACION" / "assets" / "capturas"
SAL.mkdir(parents=True, exist_ok=True)
SRC = RAIZ / "04_DATOS" / "analisis_bloques"
shutil.copy(SRC / "ad9cae6574a9_natural.png", SAL / "satelite_nat.png")
shutil.copy(SRC / "ad9cae6574a9_falso.png", SAL / "satelite_fal.png")

nat = Image.open(RAIZ / "08_PRESENTACION" / "assets" / "real" / "bloque_natural.jpg").convert("RGB")
cx, cy, S = 1464, 1864, 600
base = np.asarray(nat.crop((cx - S // 2, cy - S // 2, cx + S // 2, cy + S // 2)), "float32") / 255.0
rng = np.random.default_rng(11)


def ruido(n):
    """Ruido fractal suave 0..1 de n x n."""
    acc = np.zeros((n, n), "float32")
    for k, a in ((4, 1.0), (8, .6), (16, .35), (32, .2), (64, .1)):
        g = Image.fromarray((rng.random((k, k)) * 255).astype("uint8")).resize((n, n), Image.BICUBIC)
        acc += a * np.asarray(g, "float32") / 255.0
    acc -= acc.min(); acc /= acc.max()
    return acc


def nube(centros, radio):
    yy, xx = np.mgrid[0:S, 0:S].astype("float32")
    env = np.zeros((S, S), "float32")
    for (x, y, r) in centros:
        env = np.maximum(env, np.exp(-(((xx - x) ** 2 + (yy - y) ** 2) / (2 * (r * radio) ** 2))))
    n = ruido(S)
    n2 = ruido(S)
    m = np.clip((env * (0.25 + 1.5 * n) - 0.42) * 2.4, 0, 1) * (0.62 + 0.38 * n2)
    img = Image.fromarray((m * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(2))
    return np.asarray(img, "float32") / 255.0


# cada foto tiene nubes en sitios distintos, sin que dos fotos coincidan en el mismo pixel
planes = [
    [(110, 120, 95), (450, 500, 60)],
    [(470, 130, 100), (90, 470, 65)],
    [(300, 300, 105)],
    [(110, 300, 70), (490, 280, 58), (300, 60, 55)],
]
fotos = []
for i, pl in enumerate(planes):
    m = nube(pl, 1.0)
    # sombra: la nube desplazada, oscura
    dx, dy = 38, 26
    sm = np.roll(np.roll(m, dy, 0), dx, 1) * 0.9
    sm = np.asarray(Image.fromarray((sm * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(6)), "float32") / 255.0
    f = base * (1 - 0.45 * sm[..., None] * (1 - m[..., None]))
    blanco = np.array([0.96, 0.97, 0.99], "float32")
    f = f * (1 - m[..., None]) + blanco * m[..., None]
    f = np.clip(f * (0.97 + 0.03 * i), 0, 1)           # pequena diferencia de brillo entre fechas
    fotos.append(f)
    Image.fromarray((f * 255).astype("uint8")).save(SAL / f"satelite_nube_{i+1}.jpg", quality=90)
med = np.median(np.stack(fotos), axis=0)
Image.fromarray((med * 255).astype("uint8")).save(SAL / "satelite_nube_mediana.jpg", quality=92)
print("listo", SAL)
