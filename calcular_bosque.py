"""
calcular_bosque.py
======================================================================
Calcula hectareas de bosque por celda de la grilla nacional de 5 km,
reproyectando Hansen Global Forest Change directamente sobre la propia
grilla -- sin depender de ninguna cuadricula externa.

Expone una sola funcion publica:

    bosque_ha_por_celda(cfg, grilla, mapa_celda) -> np.ndarray

Uso tipico (ver descargar_gfw.py):

    from calcular_bosque import bosque_ha_por_celda
    bosque = bosque_ha_por_celda(cfg, grilla, mapa_celda)

COMO FUNCIONA
-------------
Hansen viene en granulos de 10x10 grados en su propia proyeccion
geografica. Para convertir eso en "hectareas de bosque por celda de 5 km"
hace falta reproyectarlo a algun raster de referencia y despues asignar
cada pixel reproyectado a su celda.

Este modulo construye su PROPIO raster de referencia, directamente en la
proyeccion y alineacion de la grilla nacional (EPSG:3116, celdas de
grid_scale_m metros, alineadas al origen -- ver exportar_grilla.py):

  1. Se toma el rango de "ix"/"iy" (indices enteros de celda) de
     grilla_colombia_5km.csv y se parte en BLOQUES cuadrados de
     bosque_bloque_celdas celdas de lado. Solo se procesan los bloques
     que de verdad contienen alguna celda de la grilla (Colombia no es
     un rectangulo). Los bloques quedan alineados exactamente a bordes
     de celda, asi que nunca se solapan entre si.
  2. Por bloque se arma un `transform` afin sintetico a resolucion
     bosque_resolucion_m metros -- el raster "vive" directamente en
     EPSG:3116, asi que asignar cada pixel a su celda es aritmetica
     directa (floor(coord / grid_scale_m)): no hace falta reproyectar
     centros de pixel con pyproj, como si haria falta si el raster de
     referencia viniera en otra proyeccion.
  3. Se reproyecta cada granulo Hansen que trae datos sobre ese bloque
     (rasterio.warp.reproject, nearest neighbor porque son variables
     categoricas -- % de dosel y año de perdida no tiene sentido
     interpolarlos --, combinando granulos con np.maximum: donde uno no
     cubre nada, reproject() deja dst_nodata=0).
  4. Se aplica la definicion de bosque: treecover2000 >= umbral_dosel Y
     (sin perdida, o perdida en/despues de anio_mascara).
  5. Se cuenta, por celda, cuantos pixeles de bosque caen en ella
     (np.bincount sobre el indice de celda) y se multiplica por el area
     de un pixel.

Como los bloques no se solapan, sumar sus conteos es correcto
directamente -- no hace falta el max() que si hace falta cuando la
fuente de la cuadricula viene con piezas traslapadas.

Se cachea un solo array nacional, no uno por bloque: el resultado final
es pequeño (un valor por celda), asi que no hace falta un esquema de
cache por pieza -- una corrida completa tarda unos minutos: releerla
despues es instantaneo.
======================================================================
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject

from config_local import Config, DIR_CACHE, DIR_HANSEN, logger


# =====================================================================
# 1. BLOQUES DE LA GRILLA NACIONAL (reemplazan a los tiles MGRS)
# =====================================================================
def _bloques(cfg: Config, grilla: pd.DataFrame) -> List[Tuple[int, int, int, int]]:
    """
    Lista de bloques (ix0, iy0, ix1, iy1), con ix1/iy1 exclusivos, que
    cubren exactamente las celdas ocupadas de la grilla -- no todo el
    rectangulo envolvente, porque Colombia no es un rectangulo y la
    mayoria de esos bloques estarian vacios.

    Los bloques se alinean a multiplos de bosque_bloque_celdas DESDE EL
    ORIGEN (no desde el minimo de la grilla), para que el mismo bloque
    quede definido igual sin importar que subconjunto de celdas se
    procese (por ejemplo, si algun dia se filtra a una sola region).
    """
    paso = cfg.bosque_bloque_celdas
    bloques_ocupados = set(zip(grilla["ix"] // paso, grilla["iy"] // paso))
    return sorted((bx * paso, by * paso, (bx + 1) * paso, (by + 1) * paso)
                 for bx, by in bloques_ocupados)


def _perfil_bloque(cfg: Config, ix0: int, iy0: int, ix1: int, iy1: int) -> dict:
    """
    Transform/CRS/forma de un raster sintetico que cubre el bloque
    [ix0,ix1) x [iy0,iy1) (en indices de celda), a resolucion
    bosque_resolucion_m, directamente en cfg.grid_crs.
    """
    lado = cfg.grid_scale_m
    res = cfg.bosque_resolucion_m
    x_min, x_max = ix0 * lado, ix1 * lado
    y_min, y_max = iy0 * lado, iy1 * lado

    ancho = int(round((x_max - x_min) / res))
    alto = int(round((y_max - y_min) / res))
    # Affine(a, b, c, d, e, f): x = a*col + c ; y = e*fila + f.
    # Origen en la esquina superior-izquierda (y_max); e = -res porque
    # las filas del raster avanzan hacia abajo mientras Y geografico
    # avanza hacia arriba -- convencion estandar "north-up".
    transform = Affine(res, 0, x_min, 0, -res, y_max)
    return {"transform": transform, "crs": cfg.grid_crs, "height": alto, "width": ancho}


# =====================================================================
# 2. MASCARA DE BOSQUE DE UN BLOQUE
# =====================================================================
def _mascara_bosque_bloque(cfg: Config, perfil: dict) -> np.ndarray:
    """Mascara booleana de bosque para un bloque -- misma definicion de siempre."""
    def traer(capa: str) -> np.ndarray:
        salida = np.zeros((perfil["height"], perfil["width"]), dtype=np.uint8)
        gs = sorted(DIR_HANSEN.glob(f"Hansen_*_{capa}_*.tif"))
        if not gs:
            raise FileNotFoundError(
                f"No hay granulos de {capa} en {DIR_HANSEN}. "
                "Ejecute: python main_local.py hansen")
        for g in gs:
            with rasterio.open(g) as hsrc:
                trozo = np.zeros_like(salida)
                # rasterio.band(hsrc, 1) trae consigo el CRS/transform de
                # origen: reproject() los toma de ahi, no hace falta
                # pasarlos a mano.
                reproject(
                    source=rasterio.band(hsrc, 1),
                    destination=trozo,
                    dst_transform=perfil["transform"],
                    dst_crs=perfil["crs"],
                    resampling=Resampling.nearest,
                    src_nodata=None, dst_nodata=0,
                )
            salida = np.maximum(salida, trozo)
        return salida

    dosel = traer("treecover2000")     # % de cobertura de dosel en el año 2000
    perdida = traer("lossyear")        # año de perdida (1-24 = 2001-2024), 0 = sin perdida

    bosque = (dosel >= cfg.umbral_dosel)
    perdida_previa = (perdida > 0) & (perdida <= (cfg.anio_mascara - 2000))
    bosque &= ~perdida_previa
    return bosque


# =====================================================================
# 3. INDICE DE CELDA DE UN BLOQUE (sin pyproj: el raster ya esta en grid_crs)
# =====================================================================
def _indice_celdas_bloque(cfg: Config, perfil: dict,
                          mapa_celda: Dict[Tuple[int, int], int]) -> np.ndarray:
    """
    Array int32 del tamaño del bloque: posicion en la tabla de la
    grilla para cada pixel, o -1 si cae fuera de cualquier celda
    conocida (no deberia pasar dentro de un bloque ocupado, pero se
    verifica igual por seguridad).
    """
    lado = cfg.grid_scale_m
    tr = perfil["transform"]
    alto, ancho = perfil["height"], perfil["width"]

    cols = np.arange(ancho) + 0.5
    filas = np.arange(alto) + 0.5
    xs = tr.c + tr.a * cols   # tr.a = resolucion en x (positiva)
    ys = tr.f + tr.e * filas  # tr.e = -resolucion (filas avanzan hacia abajo)

    X, Y = np.meshgrid(xs, ys)
    ix = np.floor(X / lado).astype(np.int64)
    iy = np.floor(Y / lado).astype(np.int64)

    # Mismo truco que en cualquier otro indexado de celda de este
    # proyecto: resolver el diccionario solo sobre los pares (ix,iy)
    # UNICOS (np.unique) y repartir el resultado a todos los pixeles.
    pares, inverso = np.unique(np.stack([ix.ravel(), iy.ravel()], axis=1),
                               axis=0, return_inverse=True)
    resueltos = np.array([mapa_celda.get((int(a), int(b)), -1)
                          for a, b in pares], dtype=np.int32)
    return resueltos[inverso].reshape(alto, ancho)


# =====================================================================
# 4. ORQUESTADOR PUBLICO
# =====================================================================
def bosque_ha_por_celda(cfg: Config, grilla: pd.DataFrame,
                        mapa_celda: Dict[Tuple[int, int], int]) -> np.ndarray:
    """
    Hectareas de bosque por celda, calculadas sobre TODA la grilla
    nacional en bloques, sin ninguna cuadricula externa de por medio.
    """
    cache = (DIR_CACHE /
            f"bosque_am{cfg.anio_mascara}_ud{cfg.umbral_dosel}"
            f"_res{cfg.bosque_resolucion_m}.npy")
    if cache.exists():
        logger.info("Bosque nacional: reutilizando cache (%s)", cache.name)
        return np.load(cache)

    n_celdas = len(grilla)
    bosque_total = np.zeros(n_celdas)
    bloques = _bloques(cfg, grilla)
    logger.info("Calculando bosque nacional sobre %d bloques de %d x %d celdas "
               "(%d m/pixel)...", len(bloques), cfg.bosque_bloque_celdas,
               cfg.bosque_bloque_celdas, cfg.bosque_resolucion_m)

    for i, (ix0, iy0, ix1, iy1) in enumerate(bloques, 1):
        perfil = _perfil_bloque(cfg, ix0, iy0, ix1, iy1)
        bosque = _mascara_bosque_bloque(cfg, perfil)
        idx = _indice_celdas_bloque(cfg, perfil, mapa_celda)

        plano = idx.ravel()
        valido = (plano >= 0) & bosque.ravel()
        conteo = np.bincount(plano[valido], minlength=n_celdas).astype(np.float64)
        # Los bloques no se solapan (estan alineados a bordes de celda):
        # sumar es correcto, a diferencia de tiles traslapados donde
        # haria falta max() para no duplicar conteo.
        bosque_total += conteo[:n_celdas] * cfg.area_px_ha

        if i % 5 == 0 or i == len(bloques):
            logger.info("  [%d/%d] bosque acumulado: %.0f ha",
                        i, len(bloques), bosque_total.sum())

    np.save(cache, bosque_total)
    logger.info("Bosque nacional listo: %.0f ha", bosque_total.sum())
    return bosque_total
