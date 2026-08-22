"""
main_local.py
======================================================================
Punto de entrada del pipeline local (DIST-ALERT via LP DAAC).

USO — en este orden
-------------------
    python main_local.py grilla
        Construye la grilla de 5 km localmente (limites del DANE, sin
        Earth Engine ni ninguna cuenta de Google). ~1 minuto.

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
        Produce datos/crudo/nacional.csv (fuente DIST-ALERT, 2023-presente).

    python main_local.py consolidar --fuente dist_alert
        Construye el panel final en datos/panel/ a partir de
        nacional.csv (DIST-ALERT, 2023-presente).

    python main_local.py consolidar --fuente gfw
        Igual, pero a partir de datos/crudo/nacional_gfw.csv (Global
        Forest Watch, 2020-presente -- generado aparte con
        "python fuente_gfw/descargar_gfw.py").

    python main_local.py consolidar --fuente dist_alert --dane ruta/al/MGN_MPIO.shp
        Igual, mas el cruce con codigos DANE.

    --fuente es obligatorio: DIST-ALERT y GFW son dos paneles
    INDEPENDIENTES que nunca se mezclan (ver METODOLOGIA.md decision
    15). Este main_local.py orquesta la rama DIST-ALERT de punta a
    punta (grilla -> hansen -> descargar -> zonal); la rama GFW se
    corre aparte con fuente_gfw/configurar_gfw.py y
    fuente_gfw/descargar_gfw.py, y solo se une aqui en el paso final
    de consolidar.

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
    """Resume que hay en disco en cada etapa del pipeline, sin modificar nada.

    Reporta cada fuente por separado (nunca un conteo combinado): las dos
    ramas (DIST-ALERT y GFW) producen archivos independientes que nunca se
    mezclan (ver METODOLOGIA.md decision 15), asi que agregar sus conteos
    en una sola cifra escondería cual de las dos falta.
    """
    grilla = DIR_GRILLA / "grilla_colombia_5km.csv"
    hansen = list(DIR_HANSEN.glob("*.tif"))
    tiles = [d for d in DIR_DIST.iterdir() if d.is_dir()] if DIR_DIST.exists() else []
    cogs = list(DIR_DIST.rglob("*.tif"))
    crudo_dist = DIR_CRUDO / "nacional.csv"
    crudo_gfw = DIR_CRUDO / "nacional_gfw.csv"
    panel_dist = DIR_PANEL / "panel_deforestacion_colombia_dist_alert.csv"
    panel_gfw = DIR_PANEL / "panel_deforestacion_colombia_gfw.csv"

    gb = sum(f.stat().st_size for f in cogs) / 1e9
    gb_h = sum(f.stat().st_size for f in hansen) / 1e9

    def _ok(p: Path) -> str:
        return "OK" if p.exists() else "falta"

    logger.info("=" * 62)
    logger.info("ESTADO DEL PIPELINE")
    logger.info("  1. grilla            : %s",
                "OK" if grilla.exists() else "FALTA (python main_local.py grilla)")
    logger.info("  2. hansen (compartido): %d archivos, %.1f GB", len(hansen), gb_h)
    logger.info("  3. dist-alert (tiles) : %d tiles, %d archivos, %.1f GB",
                len(tiles), len(cogs), gb)
    logger.info("  4a. zonal  dist_alert : %s (%s)", _ok(crudo_dist), crudo_dist.name)
    logger.info("  4b. zonal  gfw        : %s (%s)", _ok(crudo_gfw), crudo_gfw.name)
    logger.info("  5a. panel  dist_alert : %s (%s)", _ok(panel_dist), panel_dist.name)
    logger.info("  5b. panel  gfw        : %s (%s)", _ok(panel_gfw), panel_gfw.name)
    logger.info("=" * 62)
    return 0


def main() -> int:
    """Punto de entrada: python main_local.py <subcomando> [opciones].

    Ver el docstring del inicio del archivo para el orden recomendado
    de subcomandos (grilla -> hansen -> inventario ->
    [fuente_dist_alert/filtrar_tiles.py aparte] -> descargar -> zonal ->
    consolidar), y GUIA_CODIGO.md para la explicacion completa de cada paso.
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
    pc.add_argument("--fuente", required=True, choices=["dist_alert", "gfw"],
                    help="dist_alert = 2023-presente. gfw = 2020-presente. "
                         "Obligatorio: las dos fuentes nunca se mezclan.")
    pc.add_argument("--dane", default=None,
                    help="Ruta al shapefile municipal del DANE (MGN)")

    a = p.parse_args()
    cfg = Config()

    if a.cmd == "estado":
        return cmd_estado(cfg)

    if a.cmd == "grilla":
        return _correr("exportar_grilla.py")

    if a.cmd == "hansen":
        return _correr("fuente_dist_alert/descargar_dist.py", "hansen")

    if a.cmd == "inventario":
        return _correr("fuente_dist_alert/descargar_dist.py", "inventario")

    if a.cmd == "descargar":
        return _correr("fuente_dist_alert/descargar_dist.py", "dist")

    if a.cmd == "piloto":
        # Encadena dos subprocesos: primero descarga solo ese tile,
        # y solo si la descarga fue exitosa (r == 0) corre el calculo
        # zonal sobre el mismo tile.
        r = _correr("fuente_dist_alert/descargar_dist.py", "dist", "--tile", a.tile)
        if r != 0:
            return r
        return _correr("fuente_dist_alert/zonal_local.py", "--tile", a.tile)

    if a.cmd == "zonal":
        args = ["--tile", a.tile] if a.tile else []
        return _correr("fuente_dist_alert/zonal_local.py", *args)

    if a.cmd == "consolidar":
        # A diferencia de los demas subcomandos, este SI importa la
        # funcion directamente en vez de lanzar un subproceso (no hay
        # una razon tecnica fuerte para la diferencia; simplemente asi
        # quedo implementado).
        from consolidar import consolidar
        consolidar(cfg, a.fuente, a.dane)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
