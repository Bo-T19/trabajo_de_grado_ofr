"""
descargar_ideam.py
======================================================================
Descarga las capas oficiales de CAMBIO EN LA SUPERFICIE CUBIERTA POR
BOSQUE NATURAL del SMByC (Sistema de Monitoreo de Bosques y Carbono,
IDEAM).

    python main_local.py ideam

Salida: datos/ideam/cambio_<periodo>.img

QUE SON ESTAS CAPAS
-------------------
Son el insumo espacial con que el IDEAM produce la cifra OFICIAL de
deforestacion de Colombia. A diferencia de Hansen (perdida de cobertura
arborea) y de las alertas de GFW (disturbio de la vegetacion), estas
capas miden DEFORESTACION en sentido estricto: conversion de bosque
natural a otra cobertura, con la definicion nacional de bosque.

Cada capa cubre una TRANSICION entre dos años: "cambio_2020_2021"
compara dos composiciones de imagenes, cuyas ventanas difieren del 1 de
enero al 31 de diciembre. La tabla que se construye a partir de ellas
(ver panel_ideam.py) conserva el periodo textual para reflejarlo.

Leyenda (Contenido_Cambio.txt del propio servidor del IDEAM):

    1  Bosque estable
    2  Deforestacion          <- la clase de interes
    3  Sin informacion        <- nubosidad: indicador de calidad
    4  Regeneracion
    5  No bosque estable

FORMATO Y ACCESO
----------------
Los archivos son ERDAS Imagine (.img, driver HFA de GDAL), que rasterio
abre de forma nativa -- no hay que convertirlos. Vienen ya en EPSG:3116,
la misma proyeccion de la grilla de este proyecto, a ~30 m por pixel.

Los .rrd que acompañan a cada .img en el servidor son solo piramides de
visualizacion: NO se descargan, no aportan nada al calculo y duplicarian
el peso.

IMPORTANTE -- HTTPS OBLIGATORIO: el servidor del IDEAM tiene el puerto
80 cerrado y solo responde por 443. Una URL con "http://" no da error de
protocolo: simplemente se queda esperando hasta agotar el tiempo, que es
un modo de falla dificil de diagnosticar. De ahi que BASE use https y
que no se deba "simplificar" quitandolo.
======================================================================
"""
from __future__ import annotations

import argparse
from pathlib import Path

import requests

from config_local import Config, DIR_IDEAM, logger

BASE = ("https://bart.ideam.gov.co/smbyc/"
        "Cambio%20en%20la%20superficie%20cubierta%20por%20bosque%20natural/Capas")

# Nombre exacto del archivo en el servidor para cada periodo. El sufijo
# de version y fecha (v8_220710) no sigue un patron deducible, asi que
# se lista explicitamente en vez de intentar construirlo: si el IDEAM
# republica una capa con otro sufijo, se corrige aqui y en ningun otro
# lado. Listado verificado contra el indice del servidor.
CAPAS = {
    "2015-2016": "cambio_2015-2016_v7_170629.img",
    "2016-2017": "cambio_2016-2017_v7_180612.img",
    "2017-2018": "cambio_2017-2018_v8_190616.img",
    "2018-2019": "cambio_2018_2019_v8_200707.img",
    "2019-2020": "cambio_2019-2020_v8_210702.img",
    "2020-2021": "cambio_2020_2021_v8_220710.img",
    "2021-2022": "cambio_2021_2022_v8_230705.img",
    "2022-2023": "cambio_2022_2023_V8_240703.img",
    "2023-2024": "cambio_2023_2024_v8_250721.img",
    "2024-2025": "cambio_2024_2025_v8_260729.img",
}


def ruta_local(periodo: str) -> Path:
    """Donde queda en disco la capa de un periodo."""
    return DIR_IDEAM / f"cambio_{periodo}.img"


def descargar(periodo: str, cfg: Config) -> bool:
    """
    Baja una capa si no esta ya en disco. Devuelve True si al terminar
    el archivo esta disponible.

    Se descarga a un archivo temporal (.parcial) y solo al final se
    renombra: asi una descarga interrumpida (corte de red, Ctrl+C) no
    deja un .img truncado que las corridas siguientes darian por bueno.
    """
    destino = ruta_local(periodo)
    if destino.exists() and destino.stat().st_size > 0:
        logger.info("  %s: ya esta en disco (%.0f MB)",
                    periodo, destino.stat().st_size / 1e6)
        return True

    url = f"{BASE}/{CAPAS[periodo]}"
    temporal = destino.with_suffix(".parcial")
    for intento in range(1, cfg.reintentos + 1):
        try:
            logger.info("  %s: descargando...", periodo)
            with requests.get(url, stream=True, timeout=cfg.timeout_s) as r:
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", 0))
                bajado = 0
                with open(temporal, "wb") as f:
                    for trozo in r.iter_content(chunk_size=1 << 20):
                        f.write(trozo)
                        bajado += len(trozo)
            if total and bajado != total:
                raise IOError(f"incompleto: {bajado} de {total} bytes")
            temporal.replace(destino)
            logger.info("  %s: listo (%.0f MB)", periodo, bajado / 1e6)
            return True
        except Exception as e:
            logger.warning("  %s: intento %d/%d fallo (%s)",
                           periodo, intento, cfg.reintentos, e)
            temporal.unlink(missing_ok=True)
    logger.error("  %s: no se pudo descargar", periodo)
    return False


def main() -> int:
    p = argparse.ArgumentParser(
        description="Descarga capas de cambio de bosque del SMByC (IDEAM)")
    p.add_argument("--periodos", nargs="*", default=None,
                   help=("Periodos a bajar, ej: 2020-2021 2021-2022. "
                         "Si se omite, se bajan los de config_local.py "
                         "(ideam_periodos)."))
    p.add_argument("--todos", action="store_true",
                   help="Baja las 10 capas disponibles, no solo las configuradas.")
    a = p.parse_args()
    cfg = Config()

    if a.todos:
        periodos = list(CAPAS)
    elif a.periodos:
        periodos = a.periodos
    else:
        periodos = list(cfg.ideam_periodos)

    desconocidos = [p_ for p_ in periodos if p_ not in CAPAS]
    if desconocidos:
        logger.error("Periodos no disponibles: %s", ", ".join(desconocidos))
        logger.error("Disponibles: %s", ", ".join(CAPAS))
        return 1

    logger.info("Descargando %d capas del IDEAM a %s", len(periodos), DIR_IDEAM)
    ok = sum(descargar(p_, cfg) for p_ in periodos)
    logger.info("=" * 62)
    logger.info("CAPAS IDEAM: %d de %d disponibles en disco", ok, len(periodos))
    logger.info("=" * 62)
    return 0 if ok == len(periodos) else 1


if __name__ == "__main__":
    raise SystemExit(main())
