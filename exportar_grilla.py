"""
exportar_grilla.py
======================================================================
UNICA vez que se usa Earth Engine, y solo con assets publicos
(GAUL y LSIB). Produce el CSV de la grilla de 5 km sobre Colombia.

    python exportar_grilla.py

Salida: datos/grilla/grilla_colombia_5km.csv

Columnas
--------
cell_id        identificador estable (mismo criterio que la version GEE)
lon, lat       centroide en EPSG:4326 (para el cruce DANE posterior)
x3116, y3116   centroide en EPSG:3116 (para el indexado local)
ix, iy         indice entero de celda = floor(coord / 5000)
departamento   nombre GAUL nivel 1

El script verifica que la grilla este alineada al origen de la
proyeccion. Si no lo estuviera, el indexado aritmetico local seria
invalido y avisa en lugar de producir basura silenciosa.
======================================================================
"""
from __future__ import annotations

import io

import ee
import pandas as pd
import requests

from config_local import Config, DIR_GRILLA, logger

SALIDA = "grilla_colombia_5km.csv"


def init_ee(cfg: Config) -> None:
    """Inicializa la conexion con Earth Engine.

    Intenta usar credenciales ya guardadas; si no las hay (primera vez
    en esta maquina, o expiraron), dispara el flujo interactivo de
    autenticacion (abre el navegador para iniciar sesion con Google).
    """
    try:
        ee.Initialize(project=cfg.ee_project)
    except Exception:
        logger.warning("Sin credenciales validas. Abriendo autenticacion...")
        ee.Authenticate()
        ee.Initialize(project=cfg.ee_project)
    logger.info("Earth Engine conectado | proyecto=%s", cfg.ee_project)


def construir(cfg: Config) -> ee.FeatureCollection:
    """Grilla regular sobre Colombia, anotada con centroides e indices.

    Todo el codigo de esta funcion corre del lado de los servidores de
    Earth Engine (es la API "ee", perezosa: no calcula nada hasta que
    se pide un resultado con .getInfo() o se exporta). Construye:
      1. el poligono de Colombia (asset publico LSIB),
      2. una malla de celdas cuadradas de 5 km sobre ese poligono,
      3. por cada celda, su centroide en dos proyecciones distintas,
         sus indices enteros de celda, y el departamento al que
         pertenece (por interseccion espacial con el asset GAUL).
    """
    # Poligono del territorio de Colombia (LSIB = Large Scale
    # International Boundary, un dataset publico de limites de paises).
    pais = (ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
            .filter(ee.Filter.eq("country_co", "CO")).geometry())

    # Proyeccion EPSG:3116 "a escala" de grid_scale_m: define el tamano
    # de celda que va a usar coveringGrid() para mallar el poligono.
    proj = ee.Projection(cfg.grid_crs).atScale(cfg.grid_scale_m)
    # coveringGrid: genera automaticamente las celdas cuadradas que
    # cubren la geometria de entrada, alineadas a la proyeccion 'proj'.
    grid = pais.coveringGrid(proj)
    lado = cfg.grid_scale_m

    def _anotar(f: ee.Feature) -> ee.Feature:
        """Por cada celda (Feature) de la grilla, calcula sus atributos."""
        # Centroide en 4326 (lon/lat "normal", para el cruce DANE posterior)
        c4326 = f.geometry().centroid(maxError=1).coordinates()
        lon, lat = ee.Number(c4326.get(0)), ee.Number(c4326.get(1))

        # El mismo centroide, pero transformado a EPSG:3116 (para el
        # indexado local por aritmetica de enteros en zonal_local.py)
        c3116 = (f.geometry().centroid(maxError=1)
                 .transform(cfg.grid_crs, 1).coordinates())
        x, y = ee.Number(c3116.get(0)), ee.Number(c3116.get(1))

        # Mismo criterio de cell_id que la version anterior del pipeline,
        # para que los identificadores sigan siendo comparables.
        # (lon * 10000 redondeado) + "_" + (lat * 10000 redondeado):
        # da un identificador de texto estable y unico por ubicacion.
        cid = (ee.String(lon.multiply(1e4).round().format("%d"))
               .cat("_").cat(lat.multiply(1e4).round().format("%d")))

        # ix, iy: indice entero de celda = floor(coordenada / lado).
        # Este es EXACTAMENTE el mismo calculo que usa zonal_local.py
        # para decidir a que celda pertenece cada pixel de un raster;
        # por eso la grilla debe quedar alineada al origen (ver
        # verificar_alineacion), o los dos calculos no coincidirian.
        return ee.Feature(f.geometry().centroid(maxError=1), {
            "cell_id": cid,
            "lon": lon, "lat": lat,
            "x3116": x, "y3116": y,
            "ix": x.divide(lado).floor(),
            "iy": y.divide(lado).floor(),
        })

    puntos = grid.map(_anotar)

    # Departamento por interseccion del centroide con GAUL nivel 1
    # (dataset publico de limites administrativos de la FAO).
    dptos = (ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level1")
             .filter(ee.Filter.eq("ADM0_NAME", "Colombia"))
             .select(["ADM1_NAME"]))

    # Join espacial: para cada punto (centroide de celda), busca el
    # primer poligono de departamento que lo contiene/interseca y lo
    # guarda temporalmente bajo la propiedad "d".
    unido = ee.Join.saveFirst("d").apply(
        puntos, dptos,
        ee.Filter.intersects(leftField=".geo", rightField=".geo"))

    # Extrae el nombre del departamento del resultado del join y
    # descarta la geometria (setGeometry(None)): para exportar a CSV
    # solo hacen falta los atributos, no la geometria.
    return unido.map(lambda f: f.set(
        "departamento",
        ee.Feature(f.get("d")).get("ADM1_NAME")).setGeometry(None))


def verificar_alineacion(df: pd.DataFrame, lado: int) -> bool:
    """
    El indexado local supone que las celdas estan alineadas al origen
    de EPSG:3116. Si lo estan, el centroide cae exactamente en el
    medio de la celda: coord modulo 5000 == 2500.

    Por que importa: zonal_local.py asigna cada pixel de un raster a
    una celda calculando floor(coordenada / 5000), SIN mirar la grilla
    real, asumiendo que la celda "ix" cubre exactamente el rango
    [ix*5000, (ix+1)*5000). Eso solo es cierto si la grilla generada
    por Earth Engine arranca justo en el origen de EPSG:3116 (offset 0).
    Si coveringGrid() hubiera usado un offset distinto, el indice
    calculado aqui (ix, iy) no coincidiria con el que calcula
    zonal_local.py para el mismo punto en el espacio, y cada pixel
    quedaria silenciosamente mal asignado. Esta funcion detecta ese
    desajuste ANTES de que contamine el resto del pipeline.
    """
    rx = (df["x3116"] % lado).round(1)
    ry = (df["y3116"] % lado).round(1)
    esperado = lado / 2   # el centro de la celda cae a medio lado del borde

    ok_x = (rx - esperado).abs().max() < 1.0
    ok_y = (ry - esperado).abs().max() < 1.0

    logger.info("Alineacion | resto x: %.1f a %.1f (esperado %.1f)",
                rx.min(), rx.max(), esperado)
    logger.info("Alineacion | resto y: %.1f a %.1f (esperado %.1f)",
                ry.min(), ry.max(), esperado)

    if ok_x and ok_y:
        logger.info("Grilla alineada al origen. El indexado local es valido.")
        return True

    logger.error("GRILLA NO ALINEADA AL ORIGEN.")
    logger.error("El indexado aritmetico de zonal_local.py seria incorrecto.")
    logger.error("Avise antes de continuar: hay que introducir un offset.")
    return False


def main() -> int:
    cfg = Config()
    init_ee(cfg)

    # Construye la definicion de la grilla (perezoso: no se calcula aun).
    fc = construir(cfg)
    # getInfo() SI dispara el calculo en los servidores de Earth Engine
    # y trae el resultado (aqui, solo el conteo) al cliente.
    n = fc.size().getInfo()
    logger.info("Celdas en la grilla: %d", n)

    cols = ["cell_id", "lon", "lat", "x3116", "y3116",
            "ix", "iy", "departamento"]

    # getDownloadURL genera una URL temporal desde la que Earth Engine
    # sirve el resultado ya como CSV; se descarga con una solicitud HTTP
    # normal (no hace falta cliente EE para esta parte).
    logger.info("Solicitando el CSV a Earth Engine...")
    url = fc.getDownloadURL(filetype="CSV", selectors=cols,
                            filename="grilla_colombia_5km")
    r = requests.get(url, timeout=cfg.timeout_s)
    r.raise_for_status()

    # Earth Engine a veces responde con una pagina HTML de error (p.ej.
    # cuota excedida o calculo demasiado grande) en vez de lanzar un
    # error HTTP claro; se detecta a mano inspeccionando el contenido.
    if r.content[:5].lower().startswith(b"<html"):
        logger.error("GEE devolvio HTML, no CSV. Reintente en unos minutos.")
        return 1

    df = pd.read_csv(io.BytesIO(r.content))
    df = df.dropna(subset=["cell_id", "ix", "iy"])
    df["ix"] = df["ix"].astype("int32")
    df["iy"] = df["iy"].astype("int32")

    # Punto de control critico: si la grilla no quedo alineada, se
    # detiene aqui en vez de dejar pasar un archivo que produciria
    # resultados incorrectos mas adelante, en zonal_local.py.
    if not verificar_alineacion(df, cfg.grid_scale_m):
        return 1

    dup = df["cell_id"].duplicated().sum()
    if dup:
        logger.warning("Hay %d cell_id duplicados; se conserva el primero.", dup)
        df = df.drop_duplicates("cell_id")

    destino = DIR_GRILLA / SALIDA
    df.to_csv(destino, index=False)

    logger.info("=" * 62)
    logger.info("GRILLA EXPORTADA")
    logger.info("  celdas        : %d", len(df))
    logger.info("  departamentos : %d", df["departamento"].nunique())
    logger.info("  sin dpto      : %d", df["departamento"].isna().sum())
    logger.info("  archivo       : %s", destino)
    logger.info("=" * 62)
    logger.info("Earth Engine ya no se vuelve a usar en este pipeline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
