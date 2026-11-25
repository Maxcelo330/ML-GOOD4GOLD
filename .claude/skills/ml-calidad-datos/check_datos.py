"""
Control de calidad de datos geoespaciales para el proyecto ML-GOOD4GOLD.

Solo LEE los datos; nunca los modifica.

Uso (entorno g4g-ml):
  python check_datos.py RUTA [--capa NOMBRE] [--columna-clase clase] [--crs EPSG:32719]

RUTA puede ser:
  - un .gpkg (vectores: AOI o etiquetas)
  - un .tif (un raster)
  - una carpeta con varios .tif (se compara que compartan la misma grilla)

Codigo de salida: 0 si no hay errores, 1 si hay al menos un ERROR.
"""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio

MIN_POR_CLASE = 30          # menos muestras que esto = aviso
MAX_DESBALANCE = 0.20       # una clase por debajo de este porcentaje = aviso
AREA_MINIMA_M2 = 400        # 1 pixel Sentinel a 20 m

resultados = []  # (nivel, item, detalle)


def anotar(nivel, item, detalle):
    """nivel: OK, AVISO o ERROR."""
    resultados.append((nivel, item, detalle))
    print(f"[{nivel:<5}] {item}: {detalle}")


# ---------------------------------------------------------------- vectores
def revisar_vector(ruta, capa, col_clase, crs_esperado):
    print(f"\n== Vector: {ruta} (capa: {capa or 'primera'}) ==")
    gdf = gpd.read_file(ruta, layer=capa) if capa else gpd.read_file(ruta)
    anotar("OK", "Filas", str(len(gdf)))

    # CRS
    if gdf.crs is None:
        anotar("ERROR", "CRS", "no esta definido")
    elif crs_esperado and gdf.crs.to_string().upper() != crs_esperado.upper():
        anotar("AVISO", "CRS", f"es {gdf.crs.to_string()}, se esperaba {crs_esperado}")
    else:
        anotar("OK", "CRS", gdf.crs.to_string())

    # Geometrias
    nulas = int(gdf.geometry.isna().sum() + gdf.geometry.is_empty.sum())
    invalidas = int((~gdf.geometry.is_valid & ~gdf.geometry.isna()).sum())
    anotar("ERROR" if nulas else "OK", "Geometrias nulas/vacias", str(nulas))
    anotar("ERROR" if invalidas else "OK", "Geometrias invalidas", str(invalidas))
    if gdf.crs is None or nulas or invalidas:
        return  # sin esto no se pueden medir areas ni solapes con seguridad

    # Poligonos diminutos (se mide en metros)
    gdf_m = gdf.to_crs("EPSG:32719") if gdf.crs.to_string() != "EPSG:32719" else gdf
    if gdf_m.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        chicos = int((gdf_m.geometry.area < AREA_MINIMA_M2).sum())
        anotar("AVISO" if chicos else "OK",
               f"Poligonos menores a {AREA_MINIMA_M2} m2", str(chicos))

    if not col_clase:
        return
    if col_clase not in gdf.columns:
        anotar("AVISO", f"Columna '{col_clase}'", "no existe en esta capa (normal si es el AOI)")
        return

    # Clases
    nulos = int(gdf[col_clase].isna().sum())
    anotar("ERROR" if nulos else "OK", f"Nulos en '{col_clase}'", str(nulos))
    conteo = gdf[col_clase].value_counts(dropna=True)
    total = int(conteo.sum())
    for clase, n in conteo.items():
        pct = n / total
        area_km2 = gdf_m.loc[gdf[col_clase] == clase].geometry.area.sum() / 1e6
        nivel = "OK"
        notas = []
        if n < MIN_POR_CLASE:
            nivel = "AVISO"
            notas.append(f"menos de {MIN_POR_CLASE} muestras")
        if pct < MAX_DESBALANCE and len(conteo) > 1:
            nivel = "AVISO"
            notas.append("clase minoritaria (<20%)")
        anotar(nivel, f"Clase '{clase}'",
               f"{n} poligonos ({pct:.0%}), {area_km2:.2f} km2" + (f" - {'; '.join(notas)}" if notas else ""))

    # Solapes entre clases distintas
    if len(conteo) > 1:
        solapes = 0
        sindex = gdf_m.sindex
        for i, fila in gdf_m.iterrows():
            for j in sindex.query(fila.geometry, predicate="intersects"):
                if j > gdf_m.index.get_loc(i) and gdf_m.iloc[j][col_clase] != fila[col_clase]:
                    inter = fila.geometry.intersection(gdf_m.iloc[j].geometry)
                    if inter.area > 1:  # mas de 1 m2 (ignora bordes que solo se tocan)
                        solapes += 1
        anotar("ERROR" if solapes else "OK",
               "Solapes entre clases distintas", f"{solapes} pares")


# ----------------------------------------------------------------- rasters
def info_raster(ruta):
    with rasterio.open(ruta) as src:
        return {
            "ruta": ruta, "crs": src.crs.to_string() if src.crs else None,
            "res": (round(src.res[0], 6), round(src.res[1], 6)),
            "size": (src.width, src.height), "bounds": tuple(round(b, 3) for b in src.bounds),
            "dtype": src.dtypes[0], "nodata": src.nodata, "bandas": src.count,
        }


def revisar_raster(ruta, crs_esperado):
    info = info_raster(ruta)
    print(f"\n== Raster: {ruta.name} ==")
    if info["crs"] is None:
        anotar("ERROR", "CRS", "no esta definido")
    elif crs_esperado and info["crs"].upper() != crs_esperado.upper():
        anotar("AVISO", "CRS", f"es {info['crs']}, se esperaba {crs_esperado}")
    else:
        anotar("OK", "CRS", info["crs"])
    anotar("OK", "Resolucion / tamano / bandas / tipo",
           f"{info['res']} / {info['size']} / {info['bandas']} / {info['dtype']}")
    anotar("OK" if info["nodata"] is not None else "AVISO", "Valor nodata",
           str(info["nodata"]) if info["nodata"] is not None else "no definido")

    # Porcentaje de nodata/NaN (se lee la banda 1 reducida para no gastar memoria)
    with rasterio.open(ruta) as src:
        factor = max(1, max(src.width, src.height) // 2000)
        banda = src.read(1, out_shape=(src.height // factor or 1, src.width // factor or 1),
                         masked=True).astype("float64")
    invalidos = np.ma.getmaskarray(banda) | ~np.isfinite(banda.filled(0))
    pct = float(invalidos.mean()) * 100
    anotar("AVISO" if pct > 20 else "OK", "Pixeles nodata/NaN (banda 1)", f"{pct:.1f}%")
    return info


def revisar_rasters(rutas, crs_esperado):
    infos = [revisar_raster(r, crs_esperado) for r in rutas]
    if len(infos) > 1:
        print("\n== Alineacion de grilla entre rasters ==")
        base = infos[0]
        for campo in ("crs", "res", "size", "bounds"):
            distintos = [i["ruta"].name for i in infos if i[campo] != base[campo]]
            anotar("ERROR" if distintos else "OK", f"Mismo {campo}",
                   f"difieren: {', '.join(distintos)}" if distintos else "todos iguales")


# -------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ruta")
    p.add_argument("--capa", default=None, help="capa del GeoPackage")
    p.add_argument("--columna-clase", default=None, help="columna con la clase (ej. clase)")
    p.add_argument("--crs", default="EPSG:32719", help="CRS esperado (por defecto EPSG:32719)")
    a = p.parse_args()

    ruta = Path(a.ruta)
    if not ruta.exists():
        sys.exit(f"No existe: {ruta}")

    if ruta.is_dir():
        tifs = sorted(ruta.glob("*.tif"))
        if not tifs:
            sys.exit(f"No hay .tif en {ruta}")
        revisar_rasters(tifs, a.crs)
    elif ruta.suffix.lower() in (".tif", ".tiff"):
        revisar_raster(ruta, a.crs)
    else:
        revisar_vector(ruta, a.capa, a.columna_clase, a.crs)

    n = {k: sum(1 for r in resultados if r[0] == k) for k in ("OK", "AVISO", "ERROR")}
    print(f"\nResumen: {n['OK']} OK, {n['AVISO']} AVISO, {n['ERROR']} ERROR")
    sys.exit(1 if n["ERROR"] else 0)


if __name__ == "__main__":
    main()
