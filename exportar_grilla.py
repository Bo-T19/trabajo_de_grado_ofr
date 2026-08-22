"""
exportar_grilla.py
======================================================================
Genera el CSV de la grilla de 5 km sobre Colombia, enteramente en el
computador local: sin Google Earth Engine, sin ninguna cuenta de Google.

    python exportar_grilla.py

Salida: datos/grilla/grilla_colombia_5km.csv

Columnas
--------
cell_id        identificador estable: "{lon*1e4 redondeado}_{lat*1e4 redondeado}"
lon, lat       centroide en EPSG:4326 (para el cruce DANE posterior)
x3116, y3116   centroide en EPSG:3116 (para el indexado local)
ix, iy         indice entero de celda = floor(coord / 5000)
departamento   nombre del departamento (DANE, Marco Geoestadistico Nacional)

POR QUE YA NO SE USA EARTH ENGINE
----------------------------------
La cuenta gratuita/academica de Earth Engine prohibe explicitamente su uso
para "actividades de pago por servicio" o para "recibir compensacion de una
entidad comercial por aplicaciones o datos creados usando Earth Engine"
(ver terminos de la edicion no comercial: https://earthengine.google.com/noncommercial/).
Como este panel es insumo de consultorias comerciales del Observatorio,
seguir usando esa cuenta violaria los terminos. Earth Engine se usaba en
UN SOLO lugar (este script, una sola vez) para dos cosas triviales de
reproducir localmente: el poligono de Colombia y su division por
departamento, y la generacion de una malla regular de celdas cuadradas.
Ninguna de las dos necesita la infraestructura de computo de Earth Engine.

FUENTE DE LOS LIMITES ADMINISTRATIVOS
--------------------------------------
DANE, Marco Geoestadistico Nacional (MGN) 2023, nivel Departamento,
servido como Feature Service publico de ArcGIS (sin autenticacion):
    https://services.arcgis.com/ioNRSZMYYlx0PUaB/arcgis/rest/services/
    MarcoGeoestadisticoNacional2023_NivelDepartamento/FeatureServer/0

Licencia confirmada: Creative Commons Attribution 4.0 (CC BY), uso
comercial permitido con atribucion. El DANE especifica la atribucion asi:
"Departamento Administrativo Nacional de Estadistica - DANE: www.dane.gov.co"
-- inclúyala en cualquier producto/reporte que use este panel.

Es ademas la MISMA fuente cartografica que ya usaba opcionalmente
consolidar.py (--dane) para el cruce municipal: con este cambio, todo el
pipeline usa una unica fuente administrativa (DANE), no dos (antes GAUL
para departamento + DANE opcional para municipio).

El script verifica que la grilla quede alineada al origen de la
proyeccion. A diferencia de la version con Earth Engine (donde había que
verificar la alineación porque coveringGrid() era una caja negra), aquí la
alineación queda GARANTIZADA por construcción: cada celda se arma
directamente como múltiplo entero del lado, así que la verificación es
una prueba de regresión, no una esperanza.
======================================================================
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely.geometry as sg

from config_local import Config, DIR_GRILLA, logger

SALIDA = "grilla_colombia_5km.csv"

DANE_MGN_DEPARTAMENTOS = (
    "https://services.arcgis.com/ioNRSZMYYlx0PUaB/arcgis/rest/services/"
    "MarcoGeoestadisticoNacional2023_NivelDepartamento/FeatureServer/0/query"
)


def descargar_departamentos(cfg: Config) -> gpd.GeoDataFrame:
    """
    Trae los poligonos de los 33 departamentos (32 + Bogota D.C.) del
    Marco Geoestadistico Nacional del DANE, ya en la proyeccion de la
    grilla (EPSG:3116) -- se le pide a ArcGIS que reproyecte del lado
    del servidor (outSR), asi no hace falta hacerlo despues.
    """
    logger.info("Descargando limites departamentales del DANE...")
    r = requests.get(DANE_MGN_DEPARTAMENTOS, params={
        "where": "1=1",
        "outFields": "dpto_ccdgo,dpto_cnmbr",
        "outSR": cfg.grid_crs.split(":")[-1],   # "EPSG:3116" -> "3116"
        "f": "geojson",
    }, timeout=cfg.timeout_s)
    r.raise_for_status()

    gdf = gpd.GeoDataFrame.from_features(r.json()["features"], crs=cfg.grid_crs)
    gdf = gdf.rename(columns={"dpto_cnmbr": "departamento", "dpto_ccdgo": "cod_dpto"})
    # El DANE entrega el nombre en mayusculas sostenidas ("ANTIOQUIA");
    # se normaliza a una capitalizacion legible para reportes/graficas.
    gdf["departamento"] = gdf["departamento"].str.title()
    logger.info("  %d departamentos descargados.", len(gdf))
    return gdf


def construir_grilla(cfg: Config, pais: sg.base.BaseGeometry) -> gpd.GeoDataFrame:
    """
    Malla regular de celdas cuadradas de `grid_scale_m` metros, alineada
    EXACTAMENTE al origen (0, 0) de EPSG:3116 -- cada celda es
    literalmente [ix*lado, (ix+1)*lado) x [iy*lado, (iy+1)*lado) para
    algun par de enteros (ix, iy), asi que su alineacion no depende de
    ningun calculo posterior: es correcta por construccion.

    Se generan primero TODAS las celdas candidatas dentro del rectangulo
    que envuelve a Colombia (varios cientos de miles), y se descartan
    las que no tocan el poligono real del pais -- exactamente lo que
    hacia coveringGrid() en Earth Engine, aqui con un filtro espacial
    vectorizado de geopandas (usa un indice espacial internamente, no
    compara celda por celda con un bucle Python).
    """
    lado = cfg.grid_scale_m
    minx, miny, maxx, maxy = pais.bounds

    ix0, ix1 = int(np.floor(minx / lado)), int(np.ceil(maxx / lado))
    iy0, iy1 = int(np.floor(miny / lado)), int(np.ceil(maxy / lado))
    logger.info("  candidatas: %d x %d = %d celdas (antes de filtrar por el pais)",
                ix1 - ix0, iy1 - iy0, (ix1 - ix0) * (iy1 - iy0))

    ix = np.arange(ix0, ix1)
    iy = np.arange(iy0, iy1)
    IX, IY = np.meshgrid(ix, iy)
    IX, IY = IX.ravel(), IY.ravel()

    cajas = [sg.box(i * lado, j * lado, (i + 1) * lado, (j + 1) * lado)
             for i, j in zip(IX, IY)]
    candidatas = gpd.GeoDataFrame({"ix": IX, "iy": IY}, geometry=cajas,
                                  crs=cfg.grid_crs)

    # Filtro espacial: solo las celdas que efectivamente intersectan el
    # poligono de Colombia. sjoin usa el indice espacial (R-tree) de
    # geopandas, por eso es viable con cientos de miles de candidatas.
    pais_gdf = gpd.GeoDataFrame(geometry=[pais], crs=cfg.grid_crs)
    grilla = gpd.sjoin(candidatas, pais_gdf, predicate="intersects", how="inner")
    grilla = grilla.drop(columns=["index_right"]).drop_duplicates(["ix", "iy"])
    logger.info("  celdas que tocan Colombia: %d", len(grilla))
    return grilla.reset_index(drop=True)


def anotar(cfg: Config, grilla: gpd.GeoDataFrame,
          departamentos: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Por cada celda: su centroide (que, al ser una celda alineada al
    origen, cae EXACTAMENTE en el punto medio -- no hace falta
    calcularlo geometricamente, es aritmetica directa sobre ix/iy), el
    mismo centroide en EPSG:4326, el cell_id, y el departamento por
    interseccion espacial del centroide con los poligonos del DANE.
    """
    lado = cfg.grid_scale_m
    x3116 = (grilla["ix"] + 0.5) * lado
    y3116 = (grilla["iy"] + 0.5) * lado
    centroides = gpd.GeoSeries(gpd.points_from_xy(x3116, y3116), crs=cfg.grid_crs)

    centroides_4326 = centroides.to_crs("EPSG:4326")
    lon = centroides_4326.x
    lat = centroides_4326.y

    # Mismo criterio de cell_id que las versiones anteriores del
    # pipeline (con Earth Engine primero, GEE despues), para que los
    # identificadores de celda sigan siendo comparables si se cruzan
    # paneles de distintas corridas.
    cell_id = ((lon * 1e4).round().astype("int64").astype(str) + "_"
              + (lat * 1e4).round().astype("int64").astype(str))

    out = pd.DataFrame({
        "cell_id": cell_id,
        "lon": lon.values, "lat": lat.values,
        "x3116": x3116.values, "y3116": y3116.values,
        "ix": grilla["ix"].values, "iy": grilla["iy"].values,
    })

    # Join espacial: departamento del poligono del DANE que contiene
    # cada centroide. predicate="within": el centroide (no la celda
    # completa) debe caer dentro del poligono -- una celda de borde
    # entre dos departamentos se asigna por donde cae su centro, igual
    # que hacia la version con Earth Engine.
    puntos = gpd.GeoDataFrame(out, geometry=centroides.values, crs=cfg.grid_crs)
    unido = gpd.sjoin(puntos, departamentos[["departamento", "geometry"]],
                      predicate="within", how="left")
    out["departamento"] = unido["departamento"].values
    return out


def verificar_alineacion(df: pd.DataFrame, lado: int) -> bool:
    """
    El indexado local supone que las celdas estan alineadas al origen
    de EPSG:3116. Si lo estan, el centroide cae exactamente en el
    medio de la celda: coord modulo 5000 == 2500.

    Por que importa: zonal_local.py asigna cada pixel de un raster a
    una celda calculando floor(coordenada / 5000), SIN mirar la grilla
    real, asumiendo que la celda "ix" cubre exactamente el rango
    [ix*5000, (ix+1)*5000). En esta version del script eso es cierto
    por construccion (ver construir_grilla), asi que esta funcion es
    ahora una prueba de regresion -- pero se conserva intacta porque
    detectar este tipo de desajuste ANTES de que contamine el resto del
    pipeline es exactamente el tipo de chequeo que no cuesta nada
    mantener y puede ahorrar horas de depuracion si algo cambia.
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

    departamentos = descargar_departamentos(cfg)
    pais = departamentos.geometry.union_all()   # union de los 33 departamentos = pais

    # El MGN del DANE es precision catastral completa (no generalizada
    # como el GAUL_SIMPLIFIED que se usaba antes): el poligono nacional
    # sale con cientos de miles de vertices, lo que vuelve el filtro
    # espacial de mas abajo impracticamente lento. Se simplifica con
    # una tolerancia de 100 m -- irrelevante frente al lado de la celda
    # (5000 m): ningun borde puede moverse lo suficiente como para que
    # una celda entre o salga de la grilla por este motivo. No se
    # simplifican los poligonos departamentales usados para el cruce
    # de "departamento" (mas abajo), solo esta copia auxiliar.
    pais = pais.simplify(100, preserve_topology=True)

    logger.info("Construyendo grilla de %d m...", cfg.grid_scale_m)
    grilla = construir_grilla(cfg, pais)

    df = anotar(cfg, grilla, departamentos)
    df["ix"] = df["ix"].astype("int32")
    df["iy"] = df["iy"].astype("int32")

    # Punto de control: si la grilla no quedo alineada, se detiene aqui
    # en vez de dejar pasar un archivo que produciria resultados
    # incorrectos mas adelante, en zonal_local.py.
    if not verificar_alineacion(df, cfg.grid_scale_m):
        return 1

    dup = df["cell_id"].duplicated().sum()
    if dup:
        logger.warning("Hay %d cell_id duplicados; se conserva el primero.", dup)
        df = df.drop_duplicates("cell_id")

    sin_dpto = df["departamento"].isna().sum()
    if sin_dpto:
        # Puede pasar en celdas de borde costero cuyo centro cae justo
        # en el mar, fuera de todo poligono departamental por unos
        # metros. Se descartan: sin bosque real que medir ahi de todas
        # formas (zonal_local.py las filtraria despues por bosque_ha=0).
        logger.warning("%d celdas sin departamento asignado; se descartan.", sin_dpto)
        df = df.dropna(subset=["departamento"])

    destino = DIR_GRILLA / SALIDA
    cols = ["cell_id", "lon", "lat", "x3116", "y3116", "ix", "iy", "departamento"]
    df[cols].to_csv(destino, index=False)

    logger.info("=" * 62)
    logger.info("GRILLA EXPORTADA")
    logger.info("  celdas        : %d", len(df))
    logger.info("  departamentos : %d", df["departamento"].nunique())
    logger.info("  archivo       : %s", destino)
    logger.info("  fuente        : DANE, Marco Geoestadistico Nacional 2023 (CC BY)")
    logger.info("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
