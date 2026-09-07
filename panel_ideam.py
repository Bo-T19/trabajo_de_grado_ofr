"""
panel_ideam.py
======================================================================
TABLA 3 de 4: deforestacion oficial por celda y periodo, segun las
capas de cambio de bosque del SMByC (IDEAM).

    python main_local.py panel-ideam

Salida: datos/panel/panel_ideam.csv (+ .parquet)

    cell_id | periodo | def_ha | bosque_ideam_ha | sin_info_ha |
            | bosque_base_ha | cod_dane | ...

QUE MIDE
--------
Deforestacion en sentido estricto: conversion de bosque natural a otra
cobertura, con la definicion nacional de bosque. Es el insumo de la
cifra OFICIAL de Colombia, y la unica salida del proyecto que mide
directamente ese concepto.

Las tres tablas se comparan entre si; sus cifras nunca se suman, porque
cada una mide un concepto distinto.

PERIODOS DE TRANSICION
----------------------
Cada capa cubre una transicion entre dos composiciones anuales de
imagenes ("2020-2021"), cuya ventana difiere del año calendario. La
columna se llama "periodo" y conserva el texto completo para reflejarlo.
Su cifra corresponde al año FINAL de la transicion, verificado contra el
dato publicado. Todo cruce con la tabla de Hansen (año calendario) o con
la de alertas GFW (mensual) debe declarar ese desfase.

DOS DENOMINADORES, Y CUAL USAR
------------------------------
La tabla trae dos medidas del bosque disponible, y NO son intercambiables:

  bosque_ideam_ha  = bosque_estable_ha + def_ha. Es el bosque NATURAL al
                     inicio del periodo, con la definicion nacional. Es el
                     denominador CORRECTO para las tasas de esta tabla:
                     def_ha cuenta solo bosque natural destruido, asi que
                     dividirlo por otra cosa mezcla definiciones.

  bosque_base_ha   = la linea base de Hansen (dosel >= umbral_dosel), la
                     misma que usa la tabla de alertas. Se conserva para
                     poder comparar ambas tablas sobre el mismo
                     denominador y para comparacion internacional, ya que
                     Hansen aplica el mismo algoritmo en todo el planeta.

La brecha alcanza el 31%: a escala nacional Hansen ve ~77,7 millones de
hectareas de bosque y el IDEAM ~59,3 millones, sobre el mismo territorio
y el mismo ano. Hansen cuenta como bosque cualquier pixel con dosel
suficiente, plantaciones incluidas, mientras la definicion nacional de
bosque natural las excluye. Usar el denominador equivocado subestima las
tasas de esta tabla en un orden del 30-45%.

COLUMNAS DE CALIDAD
-------------------
sin_info_ha traduce la clase 3 de las capas: superficie que la nubosidad
persistente impidio observar. Funciona como indicador de calidad -- una
celda con mucha superficie sin informacion arrastra un dato de
deforestacion poco confiable ESE periodo -- y se conserva como columna
para poder filtrarla o ponderarla.
======================================================================
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from calcular_bosque import bosque_ha_por_celda
from config_local import Config, DIR_PANEL, logger
from consolidar import asignar_municipio
from descargar_ideam import ruta_local
from zonal import (bloques, cargar_grilla, contar_por_celda_y_clase,
                   indice_celdas_bloque, perfil_bloque,
                   reproyectar_sobre_bloque)

SALIDA = DIR_PANEL / "panel_ideam"

# Leyenda oficial (Contenido_Cambio.txt del servidor del SMByC).
CLASES = {
    1: "bosque_estable_ha",
    2: "def_ha",
    3: "sin_info_ha",
    4: "regeneracion_ha",
    5: "no_bosque_ha",
}
N_CLASES = 6      # 0..5; el 0 es "fuera de cobertura" y se descarta


def clases_por_celda(cfg: Config, periodos, grilla: pd.DataFrame,
                     mapa_celda) -> dict:
    """
    Para cada periodo, matriz (n_celdas x N_CLASES) con hectareas de
    cada clase de cambio por celda. Devuelve {periodo: matriz}.

    Los periodos se procesan TODOS DENTRO del recorrido de bloques, no
    uno despues de otro. El motivo es de costo: indice_celdas_bloque()
    resuelve a que celda pertenece cada uno de los 16 millones de
    pixeles del bloque, y ese calculo depende solo de la geometria del
    bloque -- no de que capa se este agregando. Con el bucle al reves
    (periodo por fuera) el mismo indice se recalcularia una vez por
    periodo: 156 bloques x 5 periodos = 780 veces en lugar de 156.

    La capa del IDEAM ya viene en EPSG:3116, igual que la grilla, pero
    a ~30,7 x 30,3 m y con su propio origen. Se reproyecta igual sobre
    el raster sintetico del bloque (a cfg.bosque_resolucion_m) para que
    el conteo quede en la MISMA rejilla que usan las otras dos tablas:
    sin eso, las hectareas del IDEAM y las de Hansen no serian
    comparables celda a celda. Al ser una variable categorica, la
    reproyeccion usa vecino mas cercano (ver zonal.py).
    """
    rutas = {}
    for p in periodos:
        r = ruta_local(p)
        if not r.exists():
            raise FileNotFoundError(
                f"No existe {r}. Ejecute primero:\n"
                f"  python main_local.py ideam")
        rutas[p] = r

    n_celdas = len(grilla)
    total = {p: np.zeros((n_celdas, N_CLASES), dtype=np.float64) for p in periodos}
    bs = bloques(cfg, grilla)

    logger.info("IDEAM: agregando %d periodos sobre %d bloques...",
                len(periodos), len(bs))
    for i, (ix0, iy0, ix1, iy1) in enumerate(bs, 1):
        perfil = perfil_bloque(cfg, ix0, iy0, ix1, iy1)
        # Una sola vez por bloque, compartido por todos los periodos.
        idx = indice_celdas_bloque(cfg, perfil, mapa_celda)
        for p in periodos:
            clases = reproyectar_sobre_bloque([rutas[p]], perfil)
            total[p] += contar_por_celda_y_clase(
                clases, idx, n_celdas, N_CLASES) * cfg.area_px_ha

        if i % 10 == 0 or i == len(bs):
            acum = sum(m[:, 2].sum() for m in total.values())
            logger.info("  [%d/%d] deforestacion acumulada (todos los periodos): %.0f ha",
                        i, len(bs), acum)
    return total


def construir(cfg: Config) -> pd.DataFrame:
    """Arma la tabla larga celda x periodo de deforestacion oficial."""
    grilla, mapa_celda = cargar_grilla()
    logger.info("Celdas en la grilla: %d", len(grilla))
    bosque = bosque_ha_por_celda(cfg, grilla, mapa_celda)

    por_periodo = clases_por_celda(cfg, cfg.ideam_periodos, grilla, mapa_celda)

    filas = []
    for periodo in cfg.ideam_periodos:
        matriz = por_periodo[periodo]
        bloque = pd.DataFrame({"cell_id": grilla["cell_id"].values,
                               "periodo": periodo})
        for codigo, columna in CLASES.items():
            bloque[columna] = matriz[:, codigo]
        filas.append(bloque)
        logger.info("IDEAM %s: %.0f ha deforestadas | %.0f ha sin informacion",
                    periodo, matriz[:, 2].sum(), matriz[:, 3].sum())

    largo = pd.concat(filas, ignore_index=True)

    # Bosque natural al INICIO del periodo, con la definicion del IDEAM:
    # lo que siguio siendo bosque mas lo que se deforesto durante el
    # periodo. Es el denominador propio de esta tabla (ver encabezado).
    largo["bosque_ideam_ha"] = largo["bosque_estable_ha"] + largo["def_ha"]

    meta = grilla[["cell_id", "lon", "lat", "departamento"]].copy()
    meta["bosque_base_ha"] = bosque
    largo = largo.merge(meta, on="cell_id", how="left")

    # Mismo filtro de dominio que las otras dos tablas, para que las
    # tres cubran exactamente el mismo conjunto de celdas.
    antes = largo["cell_id"].nunique()
    largo = largo[largo["bosque_base_ha"] >= cfg.bosque_minimo_ha].copy()
    logger.info("Celdas con bosque >= %.0f ha: %d de %d",
                cfg.bosque_minimo_ha, largo["cell_id"].nunique(), antes)

    # Mismo cruce municipal que la tabla de alertas: todas las salidas
    # deben poder agregarse por municipio, que es la unidad del caso de
    # uso. Descarga los limites del DANE si aun no estan en disco.
    largo = asignar_municipio(largo, None, cfg)

    return largo.sort_values(["cell_id", "periodo"]).reset_index(drop=True)


def main() -> int:
    cfg = Config()
    tabla = construir(cfg)

    csv = SALIDA.with_suffix(".csv")
    tabla.to_csv(csv, index=False)
    try:
        tabla.to_parquet(SALIDA.with_suffix(".parquet"), index=False)
        parquet = "si"
    except Exception as e:                      # pyarrow ausente: no es fatal
        logger.warning("No se pudo escribir el .parquet (%s)", e)
        parquet = "no"

    resumen = tabla.groupby("periodo")[
        ["def_ha", "sin_info_ha", "bosque_ideam_ha"]].sum()
    logger.info("=" * 62)
    logger.info("TABLA IDEAM LISTA")
    logger.info("  archivo : %s (parquet: %s)", csv, parquet)
    logger.info("  filas   : %d  (%d celdas x %d periodos)",
                len(tabla), tabla["cell_id"].nunique(), tabla["periodo"].nunique())
    logger.info("  deforestacion oficial por periodo (ha):")
    for periodo, fila in resumen.iterrows():
        logger.info("    %-10s def: %12s ha | bosque IDEAM: %14s ha | sin info: %10s ha",
                    periodo, f"{fila['def_ha']:,.0f}",
                    f"{fila['bosque_ideam_ha']:,.0f}", f"{fila['sin_info_ha']:,.0f}")
    logger.info("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
