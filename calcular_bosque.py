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

Este es el DENOMINADOR comun de las salidas del proyecto (alertas GFW,
deforestacion del IDEAM, causas WUR): al calcularse una sola vez y
reutilizarse en todas, quedan sobre el mismo conjunto de celdas y son
comparables entre si.

OJO: las TASAS de la tabla del IDEAM usan otro denominador,
bosque_ideam_ha (bosque natural, definicion nacional). Ver el encabezado
de panel_ideam.py.

COMO FUNCIONA
-------------
Hansen viene en granulos de 10x10 grados en su propia proyeccion
geografica. Para convertir eso en "hectareas de bosque por celda de 5 km"
hace falta reproyectarlo a algun raster de referencia y despues asignar
cada pixel reproyectado a su celda.

La geometria de ese reparto (bloques de la grilla, raster sintetico en
EPSG:3116, indice de celda por aritmetica directa) vive en zonal.py,
compartida con las demas tablas. Aqui solo queda lo especifico de
Hansen: la DEFINICION de bosque.

  1. Se recorren los bloques de la grilla (zonal.bloques).
  2. Por bloque se reproyectan las capas treecover2000 y lossyear
     (zonal.reproyectar_sobre_bloque).
  3. Se aplica la definicion de bosque: treecover2000 >= umbral_dosel Y
     (sin perdida, o perdida en/despues de anio_mascara).
  4. Se cuenta, por celda, cuantos pixeles de bosque caen en ella
     (np.bincount sobre el indice de celda) y se multiplica por el area
     de un pixel.

Como los bloques no se solapan, sumar sus conteos es correcto
directamente -- no hace falta el max() que si haria falta si la
cuadricula viniera con piezas traslapadas.

Se cachea un solo array nacional, no uno por bloque: el resultado final
es pequeño (un valor por celda), asi que no hace falta un esquema de
cache por pieza -- una corrida completa tarda unos minutos: releerla
despues es instantaneo.
======================================================================
"""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd

from config_local import Config, DIR_CACHE, DIR_HANSEN, logger
from zonal import (bloques, indice_celdas_bloque, perfil_bloque,
                   reproyectar_sobre_bloque)


def _granulos(capa: str):
    """Granulos de Hansen de una capa, con un error util si faltan."""
    gs = sorted(DIR_HANSEN.glob(f"Hansen_*_{capa}_*.tif"))
    if not gs:
        raise FileNotFoundError(
            f"No hay granulos de {capa} en {DIR_HANSEN}. "
            "Ejecute: python main_local.py hansen")
    return gs


def _mascara_bosque_bloque(cfg: Config, perfil: dict) -> np.ndarray:
    """
    Mascara booleana de bosque para un bloque.

    Definicion: el pixel tenia dosel suficiente en el año 2000 Y no
    habia perdido esa cobertura antes del año de corte. El segundo
    termino es lo que evita el doble conteo: si un pixel ya se habia
    deforestado antes de que arranque la ventana de eventos, no debe
    figurar como bosque disponible para perderse otra vez.
    """
    dosel = reproyectar_sobre_bloque(_granulos("treecover2000"), perfil)
    perdida = reproyectar_sobre_bloque(_granulos("lossyear"), perfil)

    bosque = (dosel >= cfg.umbral_dosel)
    perdida_previa = (perdida > 0) & (perdida <= (cfg.anio_mascara - 2000))
    bosque &= ~perdida_previa
    return bosque


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
    bs = bloques(cfg, grilla)
    logger.info("Calculando bosque nacional sobre %d bloques de %d x %d celdas "
                "(%d m/pixel)...", len(bs), cfg.bosque_bloque_celdas,
                cfg.bosque_bloque_celdas, cfg.bosque_resolucion_m)

    for i, (ix0, iy0, ix1, iy1) in enumerate(bs, 1):
        perfil = perfil_bloque(cfg, ix0, iy0, ix1, iy1)
        bosque = _mascara_bosque_bloque(cfg, perfil)
        idx = indice_celdas_bloque(cfg, perfil, mapa_celda)

        plano = idx.ravel()
        valido = (plano >= 0) & bosque.ravel()
        conteo = np.bincount(plano[valido], minlength=n_celdas).astype(np.float64)
        # Los bloques no se solapan (estan alineados a bordes de celda):
        # sumar es correcto, a diferencia de tiles traslapados donde
        # haria falta max() para no duplicar conteo.
        bosque_total += conteo[:n_celdas] * cfg.area_px_ha

        if i % 5 == 0 or i == len(bs):
            logger.info("  [%d/%d] bosque acumulado: %.0f ha",
                        i, len(bs), bosque_total.sum())

    np.save(cache, bosque_total)
    logger.info("Bosque nacional listo: %.0f ha", bosque_total.sum())
    return bosque_total
