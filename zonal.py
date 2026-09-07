"""
zonal.py
======================================================================
Maquinaria compartida para agregar CUALQUIER raster sobre la grilla
nacional de 5 km.

Este modulo existe porque todas las salidas del proyecto (linea base de
bosque, alertas GFW, deforestacion oficial del IDEAM, causas WUR)
resuelven el mismo problema geometrico: repartir los pixeles de un
raster entre las celdas de la grilla. Tenerlo en un solo lugar garantiza
que todas usen EXACTAMENTE el mismo indexado -- si cada una lo
implementara por su cuenta, una diferencia de medio pixel en el borde de
una celda haria que las tablas dejaran de ser comparables entre si, que
es justamente lo unico que no se puede permitir aqui.

La estrategia (heredada de calcular_bosque.py, ver ese modulo para el
detalle del diseño): se parte la grilla en BLOQUES cuadrados, y por
bloque se arma un raster sintetico ya en cfg.grid_crs (EPSG:3116) y
alineado a bordes de celda. Como el raster de destino vive en la misma
proyeccion que la grilla, asignar cada pixel a su celda es aritmetica
directa -- floor(coord / grid_scale_m) -- sin reproyectar centros de
pixel con pyproj. Y como los bloques se alinean a bordes de celda,
nunca se solapan: sumar los conteos de bloques distintos es correcto.
======================================================================
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject

from config_local import Config, DIR_GRILLA, logger

ARCHIVO_GRILLA = DIR_GRILLA / "grilla_colombia_5km.csv"

# Tipo del indice de celda: (ix, iy) -> posicion en la tabla de la grilla.
MapaCelda = Dict[Tuple[int, int], int]


# =====================================================================
# 1. GRILLA
# =====================================================================
def cargar_grilla() -> Tuple[pd.DataFrame, MapaCelda]:
    """
    Lee la grilla nacional y arma el diccionario (ix, iy) -> fila.

    Devuelve las dos cosas juntas porque nunca se necesita una sin la
    otra: la tabla da los metadatos por celda (cell_id, lon, lat,
    departamento) y el diccionario permite pasar de coordenada de pixel
    a posicion en esa tabla.
    """
    if not ARCHIVO_GRILLA.exists():
        raise FileNotFoundError(
            f"No existe {ARCHIVO_GRILLA}. Ejecute primero:\n"
            f"  python main_local.py grilla")
    grilla = pd.read_csv(ARCHIVO_GRILLA)
    mapa = {(int(r.ix), int(r.iy)): i for i, r in enumerate(grilla.itertuples())}
    return grilla, mapa


# =====================================================================
# 2. BLOQUES DE LA GRILLA NACIONAL
# =====================================================================
def bloques(cfg: Config, grilla: pd.DataFrame) -> List[Tuple[int, int, int, int]]:
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
    ocupados = set(zip(grilla["ix"] // paso, grilla["iy"] // paso))
    return sorted((bx * paso, by * paso, (bx + 1) * paso, (by + 1) * paso)
                  for bx, by in ocupados)


def perfil_bloque(cfg: Config, ix0: int, iy0: int, ix1: int, iy1: int) -> dict:
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
# 3. INDICE DE CELDA (sin pyproj: el raster de destino ya esta en grid_crs)
# =====================================================================
def indice_celdas_bloque(cfg: Config, perfil: dict, mapa_celda: MapaCelda) -> np.ndarray:
    """
    Array int32 del tamaño del bloque: posicion en la tabla de la
    grilla para cada pixel, o -1 si cae fuera de cualquier celda
    conocida (pasa en los bordes del pais, donde el bloque cubre mar o
    territorio de otro pais).

    SEPARABILIDAD -- por que esto es rapido
    ---------------------------------------
    El raster del bloque es "north-up" sin rotacion (lo construye
    perfil_bloque, con los terminos b y d del affine en cero). En ese
    caso la coordenada X de un pixel depende UNICAMENTE de su columna y
    la Y UNICAMENTE de su fila. Por lo tanto ix es constante a lo largo
    de cada columna e iy a lo largo de cada fila: el indice es el
    producto exterior de dos vectores, no un problema bidimensional.

    Eso permite resolver el diccionario sobre una tabla diminuta (las
    celdas distintas del bloque: 20x20 = 400 con la configuracion por
    defecto) y expandirla por indexado, en vez de recorrer los 16
    millones de pixeles del bloque. La version anterior hacia
    np.unique(..., axis=0) sobre esos 16 millones de pares, lo que
    costaba ~12 s por bloque; asi cuesta ~0,04 s, con resultado
    identico (verificado bloque a bloque).

    Si alguna vez el raster de destino llevara rotacion, la
    separabilidad deja de valer y se cae al camino general.
    """
    lado = cfg.grid_scale_m
    tr = perfil["transform"]
    alto, ancho = perfil["height"], perfil["width"]

    # +0.5: se usa el CENTRO del pixel, no su esquina, para decidir a
    # que celda pertenece. Con la esquina, un pixel que arranca justo
    # en el borde de la celda se asignaria a la celda anterior.
    cols = np.arange(ancho) + 0.5
    filas = np.arange(alto) + 0.5

    if tr.b == 0 and tr.d == 0:
        # Camino separable (el normal).
        ix_col = np.floor((tr.c + tr.a * cols) / lado).astype(np.int64)
        iy_fila = np.floor((tr.f + tr.e * filas) / lado).astype(np.int64)

        ux, pos_x = np.unique(ix_col, return_inverse=True)
        uy, pos_y = np.unique(iy_fila, return_inverse=True)
        tabla = np.array(
            [[mapa_celda.get((int(a), int(b)), -1) for a in ux] for b in uy],
            dtype=np.int32)
        return tabla[pos_y[:, None], pos_x[None, :]]

    # Camino general, por si el affine llevara rotacion.
    X, Y = np.meshgrid(tr.c + tr.a * cols, tr.f + tr.e * filas)
    ix = np.floor(X / lado).astype(np.int64)
    iy = np.floor(Y / lado).astype(np.int64)
    pares, inverso = np.unique(np.stack([ix.ravel(), iy.ravel()], axis=1),
                               axis=0, return_inverse=True)
    resueltos = np.array([mapa_celda.get((int(a), int(b)), -1)
                          for a, b in pares], dtype=np.int32)
    return resueltos[inverso].reshape(alto, ancho)


# =====================================================================
# 4. REPROYECCION DE UN RASTER SOBRE UN BLOQUE
# =====================================================================
def reproyectar_sobre_bloque(rutas: Iterable[Path], perfil: dict,
                             dtype=np.uint8) -> np.ndarray:
    """
    Reproyecta uno o varios rasteres fuente sobre el raster sintetico
    del bloque y los combina.

    resampling=nearest SIEMPRE: todas las capas que agrega este proyecto
    son categoricas (% de dosel, año de perdida, clase de cambio), y
    promediar categorias no tiene sentido -- interpolar entre "clase 2 =
    deforestacion" y "clase 4 = regeneracion" daria "clase 3 = sin
    informacion", que es un disparate.

    Se combinan varios granulos con np.maximum porque reproject() deja
    dst_nodata=0 donde el granulo no aporta datos: el maximo se queda
    con el valor real de cualquier granulo que si cubra ese pixel. Esto
    supone que 0 significa "sin dato" en todas las capas usadas aqui,
    lo cual se cumple en Hansen (0 = sin perdida) y en el IDEAM (las
    clases van de 1 a 5, el 0 es fuera de cobertura).
    """
    salida = np.zeros((perfil["height"], perfil["width"]), dtype=dtype)
    for r in rutas:
        with rasterio.open(r) as src:
            trozo = np.zeros_like(salida)
            # rasterio.band(src, 1) trae consigo el CRS/transform de
            # origen: reproject() los toma de ahi, no hace falta
            # pasarlos a mano.
            reproject(
                source=rasterio.band(src, 1),
                destination=trozo,
                dst_transform=perfil["transform"],
                dst_crs=perfil["crs"],
                resampling=Resampling.nearest,
                src_nodata=None, dst_nodata=0,
            )
        salida = np.maximum(salida, trozo)
    return salida


# =====================================================================
# 5. CONTEO POR CELDA Y CATEGORIA
# =====================================================================
def contar_por_celda_y_clase(valores: np.ndarray, idx: np.ndarray,
                             n_celdas: int, n_clases: int) -> np.ndarray:
    """
    Matriz (n_celdas x n_clases) con el conteo de pixeles de cada clase
    en cada celda.

    Se hace con UN SOLO np.bincount sobre un indice combinado
    (celda * n_clases + clase) en vez de un bincount por clase: para
    Hansen son 26 valores posibles de lossyear, y recorrer el bloque 26
    veces cuesta 26 veces mas que recorrerlo una.

    Se descartan los pixeles fuera de la grilla (idx = -1) y los que
    traen clase 0 (sin dato) o fuera del rango declarado.
    """
    plano_idx = idx.ravel()
    plano_val = valores.ravel().astype(np.int64)
    ok = (plano_idx >= 0) & (plano_val > 0) & (plano_val < n_clases)
    combinado = plano_idx[ok] * n_clases + plano_val[ok]
    conteo = np.bincount(combinado, minlength=n_celdas * n_clases)
    return conteo[:n_celdas * n_clases].reshape(n_celdas, n_clases)
