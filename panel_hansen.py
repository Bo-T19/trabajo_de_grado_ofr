"""
panel_hansen.py
======================================================================
TABLA 2 de 4: perdida anual de cobertura arborea por celda, segun
Hansen Global Forest Change.

    python main_local.py panel-hansen

Salida: datos/panel/panel_hansen.csv (+ .parquet)

    cell_id | anio | perdida_ha | bosque_base_ha | cod_dane | ...

QUE MIDE
--------
PERDIDA DE COBERTURA ARBOREA: la desaparicion del dosel en un pixel que
en el ano 2000 tenia al menos umbral_dosel por ciento de cobertura,
cualquiera sea la causa. El concepto abarca la cosecha de plantacion
forestal, el incendio y el dano natural, ademas de la conversion a otro
uso del suelo.

Sobre Colombia esta cifra equivale a entre 1,5 y 2,5 veces la
deforestacion oficial del IDEAM (panel_ideam.py), con una razon que
varia cada ano. Convertir una en otra exige, por tanto, un factor
especifico para el ano de interes.

PARA QUE SIRVE ESTA TABLA
-------------------------
1. COMPARABILIDAD INTERNACIONAL. Hansen aplica el mismo algoritmo en
   todo el planeta, de modo que permite situar a Colombia frente a
   Brasil, Peru o Indonesia con una medida homogenea. El IDEAM cubre
   solo Colombia, y las alertas de GFW varian en sensibilidad segun la
   region.

2. INDEPENDENCIA DEL ESTADO EVALUADO. Para una debida diligencia de
   importacion, una fuente ajena al gobierno del pais evaluado aporta un
   valor probatorio propio.

3. CONTROL DE ROBUSTEZ. Un municipio senalado por las tres fuentes a la
   vez constituye una senal mas solida.

Al usar el punto 3 conviene tener presente el grado de independencia
entre fuentes: el producto Hansen y el sistema GLAD provienen del mismo
laboratorio (GLAD, Universidad de Maryland) y ambos se basan en Landsat,
de modo que su coincidencia aporta evidencia limitada. Las parejas con
independencia plena son IDEAM-Hansen e IDEAM-GFW.

LOS DOS PAPELES DE HANSEN EN ESTE PROYECTO
------------------------------------------
  - Como LINEA BASE: calcular_bosque.py usa treecover2000 y lossyear
    para fijar bosque_base_ha, el denominador comun de las tres tablas.

  - Como FUENTE DE EVENTO: este modulo, que cuenta la perdida anual.

RESOLUCION TEMPORAL
-------------------
La capa lossyear codifica el ano de perdida como un entero: 1 = 2001,
2 = 2002, ..., 25 = 2025 (0 = sin perdida). Es resolucion ANUAL y un
pixel se marca una sola vez, en el ano en que se detecto la perdida. De
ahi que esta tabla sea celda x ano, y no celda x mes como la de alertas.

DE DONDE SALEN LOS DATOS
------------------------
De los mismos granulos que ya descarga "python main_local.py hansen"
para calcular el bosque base: no hace falta descargar nada nuevo.
======================================================================
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from calcular_bosque import bosque_ha_por_celda
from config_local import Config, DIR_HANSEN, DIR_PANEL, logger
from consolidar import asignar_municipio
from zonal import (bloques, cargar_grilla, contar_por_celda_y_clase,
                   indice_celdas_bloque, perfil_bloque,
                   reproyectar_sobre_bloque)

SALIDA = DIR_PANEL / "panel_hansen"

# lossyear va de 0 (sin perdida) a 25 (2025). Se reserva espacio holgado
# para que una version futura de Hansen, con un ano mas, no obligue a
# tocar esto.
N_CLASES_LOSSYEAR = 40


def perdida_anual_por_celda(cfg: Config, grilla: pd.DataFrame,
                            mapa_celda) -> np.ndarray:
    """
    Matriz (n_celdas x N_CLASES_LOSSYEAR) con hectareas de perdida por
    celda y por codigo de ano de lossyear.

    Se aplica la MISMA definicion de bosque que calcular_bosque.py
    (dosel >= umbral_dosel): un pixel que nunca fue bosque no puede
    perder cobertura, y contarlo solo agregaria ruido. Sin este filtro,
    cualquier cambio de dosel en un cultivo o en un area urbana entraria
    a la tabla.
    """
    n_celdas = len(grilla)
    total = np.zeros((n_celdas, N_CLASES_LOSSYEAR), dtype=np.float64)
    bs = bloques(cfg, grilla)

    tif_dosel = sorted(DIR_HANSEN.glob("Hansen_*_treecover2000_*.tif"))
    tif_perdida = sorted(DIR_HANSEN.glob("Hansen_*_lossyear_*.tif"))
    if not tif_dosel or not tif_perdida:
        raise FileNotFoundError(
            f"Faltan granulos de Hansen en {DIR_HANSEN}. Ejecute:\n"
            f"  python main_local.py hansen")

    logger.info("Perdida anual de Hansen sobre %d bloques...", len(bs))
    for i, (ix0, iy0, ix1, iy1) in enumerate(bs, 1):
        perfil = perfil_bloque(cfg, ix0, iy0, ix1, iy1)
        dosel = reproyectar_sobre_bloque(tif_dosel, perfil)
        perdida = reproyectar_sobre_bloque(tif_perdida, perfil)
        idx = indice_celdas_bloque(cfg, perfil, mapa_celda)

        # Solo cuenta la perdida sobre pixeles que eran bosque en 2000.
        # Se pone a 0 el resto para que contar_por_celda_y_clase() los
        # descarte igual que a los "sin dato".
        perdida = np.where(dosel >= cfg.umbral_dosel, perdida, 0)

        total += contar_por_celda_y_clase(
            perdida, idx, n_celdas, N_CLASES_LOSSYEAR) * cfg.area_px_ha

        if i % 20 == 0 or i == len(bs):
            logger.info("  [%d/%d] perdida acumulada: %.0f ha", i, len(bs), total.sum())
    return total


def construir(cfg: Config) -> pd.DataFrame:
    """Arma la tabla larga celda x ano de perdida de cobertura."""
    grilla, mapa_celda = cargar_grilla()
    logger.info("Celdas en la grilla: %d", len(grilla))

    matriz = perdida_anual_por_celda(cfg, grilla, mapa_celda)
    # bosque_base_ha sale del mismo calculo que usan las otras dos
    # tablas, asi que el denominador es identico y las tasas resultan
    # comparables entre ellas. Para ESTA tabla ademas es el denominador
    # correcto: numerador y denominador vienen del mismo producto.
    bosque = bosque_ha_por_celda(cfg, grilla, mapa_celda)

    # Solo se emiten los anos dentro de la ventana del proyecto: la serie
    # completa de Hansen arranca en 2001, pero el panel no necesita dos
    # decadas de historia previa.
    anio_ini = pd.Timestamp(cfg.fecha_inicio).year
    anio_fin = pd.Timestamp(cfg.fecha_fin).year - 1   # fecha_fin es exclusiva
    filas = []
    for anio in range(anio_ini, anio_fin + 1):
        codigo = anio - 2000
        if not (0 < codigo < N_CLASES_LOSSYEAR):
            continue
        filas.append(pd.DataFrame({
            "cell_id": grilla["cell_id"].values,
            "anio": anio,
            "perdida_ha": matriz[:, codigo],
        }))
    largo = pd.concat(filas, ignore_index=True)

    meta = grilla[["cell_id", "lon", "lat", "departamento"]].copy()
    meta["bosque_base_ha"] = bosque
    largo = largo.merge(meta, on="cell_id", how="left")

    # Mismo filtro de dominio que las otras dos tablas: una celda sin
    # bosque suficiente no puede perder cobertura, y solo aporta ceros.
    antes = largo["cell_id"].nunique()
    largo = largo[largo["bosque_base_ha"] >= cfg.bosque_minimo_ha].copy()
    logger.info("Celdas con bosque >= %.0f ha: %d de %d",
                cfg.bosque_minimo_ha, largo["cell_id"].nunique(), antes)

    # Mismo cruce municipal que las demas: las tres tablas deben poder
    # agregarse por municipio, que es la unidad del caso de uso.
    largo = asignar_municipio(largo, None, cfg)

    return largo.sort_values(["cell_id", "anio"]).reset_index(drop=True)


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

    resumen = tabla.groupby("anio")["perdida_ha"].sum()
    logger.info("=" * 62)
    logger.info("TABLA HANSEN LISTA")
    logger.info("  archivo  : %s (parquet: %s)", csv, parquet)
    logger.info("  filas    : %d  (%d celdas x %d anios)",
                len(tabla), tabla["cell_id"].nunique(), tabla["anio"].nunique())
    logger.info("  perdida de cobertura arborea por anio (ha):")
    for anio, ha in resumen.items():
        logger.info("    %d : %14s ha", anio, f"{ha:,.0f}")
    logger.info("  ---")
    logger.info("  Concepto medido: PERDIDA DE COBERTURA ARBOREA. Equivale a")
    logger.info("  1,5-2,5 veces la deforestacion oficial, segun el ano.")
    logger.info("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
