"""
main_local.py
======================================================================
Punto de entrada del pipeline local (DIST-ALERT via LP DAAC).

USO — en este orden
-------------------
    python main_local.py grilla
        Exporta la grilla de 5 km desde Earth Engine. Unica vez que se
        usa GEE, y solo con assets publicos. ~1 minuto.

    python main_local.py hansen
        Baja los 12 granulos de Hansen sobre Colombia. ~5 GB.

    python main_local.py inventario
        Consulta a NASA CMR cuantos archivos y GB implica la descarga.
        NO descarga nada. Hagalo antes de comprometer horas.

    python main_local.py piloto --tile T18NXG
        Descarga y procesa un solo tile MGRS. Valida el flujo completo
        en minutos antes de lanzar el pais.

    python main_local.py descargar
        Descarga nacional. Varias horas, reanudable con Ctrl+C.

    python main_local.py zonal
        Calculo zonal local. Reemplaza a reduceRegions de GEE.

    python main_local.py consolidar
        Construye el panel final en datos/panel/.

    python main_local.py consolidar --dane ruta/al/MGN_MPIO.shp
        Igual, mas el cruce con codigos DANE.

    python main_local.py estado
        Que hay en disco y que falta.
======================================================================
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from config_local import (Config, DIR_CRUDO, DIR_DIST, DIR_GRILLA,
                          DIR_HANSEN, DIR_PANEL, logger)

AQUI = Path(__file__).resolve().parent


def _correr(script: str, *args: str) -> int:
    """Lanza otro script del pipeline como subproceso.

    main_local.py no reimplementa la logica de cada etapa: solo arma
    la linea de comandos correcta ("python <script> <args>") y la
    ejecuta como un proceso hijo, propagando su codigo de salida.
    sys.executable asegura que se use el mismo interprete de Python
    (y el mismo entorno virtual) con el que se corrio main_local.py.
    """
    cmd = [sys.executable, str(AQUI / script), *args]
    logger.info("-> %s", " ".join(cmd[1:]))
    return subprocess.call(cmd)


def cmd_estado(cfg: Config) -> int:
    """Resume que hay en disco en cada etapa del pipeline, sin modificar nada."""
    grilla = DIR_GRILLA / "grilla_colombia_5km.csv"
    hansen = list(DIR_HANSEN.glob("*.tif"))
    tiles = [d for d in DIR_DIST.iterdir() if d.is_dir()] if DIR_DIST.exists() else []
    cogs = list(DIR_DIST.rglob("*.tif"))
    crudo = list(DIR_CRUDO.glob("*.csv"))
    panel = list(DIR_PANEL.glob("*.csv"))

    gb = sum(f.stat().st_size for f in cogs) / 1e9
    gb_h = sum(f.stat().st_size for f in hansen) / 1e9

    logger.info("=" * 62)
    logger.info("ESTADO DEL PIPELINE")
    logger.info("  1. grilla      : %s",
                "OK" if grilla.exists() else "FALTA (python main_local.py grilla)")
    logger.info("  2. hansen      : %d archivos, %.1f GB", len(hansen), gb_h)
    logger.info("  3. dist-alert  : %d tiles, %d archivos, %.1f GB",
                len(tiles), len(cogs), gb)
    logger.info("  4. zonal       : %d CSV en crudo/", len(crudo))
    logger.info("  5. panel       : %d CSV en panel/", len(panel))
    logger.info("=" * 62)
    return 0


def main() -> int:
    """Punto de entrada: python main_local.py <subcomando> [opciones].

    Ver el docstring del inicio del archivo para el orden recomendado
    de subcomandos (grilla -> hansen -> inventario -> [filtrar_tiles.py
    aparte] -> descargar -> zonal -> consolidar), y GUIA_PIPELINE.md
    para la explicacion completa de cada paso.
    """
    p = argparse.ArgumentParser(
        description="Panel de deforestacion de Colombia (DIST-ALERT local)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("grilla")
    sub.add_parser("hansen")
    sub.add_parser("inventario")
    sub.add_parser("descargar")
    sub.add_parser("estado")

    # "piloto": descarga + calculo zonal de UN SOLO tile, para validar
    # el flujo completo en minutos antes de lanzar el pais entero.
    pp = sub.add_parser("piloto")
    pp.add_argument("--tile", default="T18NXG")

    # "zonal": --tile es opcional; si no se pasa, procesa todos los
    # tiles que ya esten descargados en datos/dist/.
    pz = sub.add_parser("zonal")
    pz.add_argument("--tile", default=None)

    pc = sub.add_parser("consolidar")
    pc.add_argument("--dane", default=None,
                    help="Ruta al shapefile municipal del DANE (MGN)")

    a = p.parse_args()
    cfg = Config()

    if a.cmd == "estado":
        return cmd_estado(cfg)

    if a.cmd == "grilla":
        return _correr("exportar_grilla.py")

    if a.cmd == "hansen":
        return _correr("descargar_dist.py", "hansen")

    if a.cmd == "inventario":
        return _correr("descargar_dist.py", "inventario")

    if a.cmd == "descargar":
        return _correr("descargar_dist.py", "dist")

    if a.cmd == "piloto":
        # Encadena dos subprocesos: primero descarga solo ese tile,
        # y solo si la descarga fue exitosa (r == 0) corre el calculo
        # zonal sobre el mismo tile.
        r = _correr("descargar_dist.py", "dist", "--tile", a.tile)
        if r != 0:
            return r
        return _correr("zonal_local.py", "--tile", a.tile)

    if a.cmd == "zonal":
        args = ["--tile", a.tile] if a.tile else []
        return _correr("zonal_local.py", *args)

    if a.cmd == "consolidar":
        # A diferencia de los demas subcomandos, este SI importa la
        # funcion directamente en vez de lanzar un subproceso (no hay
        # una razon tecnica fuerte para la diferencia; simplemente asi
        # quedo implementado).
        from consolidar import consolidar
        consolidar(cfg, a.dane)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
