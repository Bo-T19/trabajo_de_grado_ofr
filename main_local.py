"""
main_local.py
======================================================================
Punto de entrada del pipeline (Global Forest Watch, 2020-presente).

USO — en este orden
-------------------
    python main_local.py grilla
        Construye la grilla de 5 km localmente (limites del DANE).
        ~1 minuto.

    python main_local.py hansen
        Baja los granulos de Hansen GFC sobre Colombia (~5 GB).
        No requiere ninguna cuenta.

    python main_local.py gfw
        Calcula el bosque base y descarga el evento desde la API de
        GFW. Produce datos/crudo/nacional.csv. Requiere una API key
        de GFW (ver configurar_gfw.py). Del orden de 10-20 minutos.

    python main_local.py municipios
        Descarga los limites municipales del DANE (MGN2025, nivel
        Municipio), sin cuenta ni descarga manual. ~10 segundos.

    python main_local.py consolidar
        Construye el panel final en datos/panel/, con cruce municipal
        automatico (descarga los limites si aun no estan en disco).

    python main_local.py consolidar --dane ruta/al/otro_archivo.shp
        Igual, pero usando un shapefile/geojson municipal distinto en
        vez del descargado automaticamente del DANE.

    python main_local.py estado
        Que hay en disco y que falta.
======================================================================
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from config_local import (Config, DIR_CRUDO, DIR_GRILLA, DIR_HANSEN,
                          DIR_LIMITES, DIR_PANEL, logger)

AQUI = Path(__file__).resolve().parent


def _correr(script: str, *args: str) -> int:
    """Lanza otro script del pipeline como subproceso.

    main_local.py no reimplementa la logica de cada etapa: solo arma
    la linea de comandos correcta ("python <script> <args>") y la
    ejecuta como un proceso hijo, propagando su codigo de salida.
    """
    cmd = [sys.executable, str(AQUI / script), *args]
    logger.info("-> %s", " ".join(cmd[1:]))
    return subprocess.call(cmd)


def cmd_estado(cfg: Config) -> int:
    """Resume que hay en disco en cada etapa del pipeline, sin modificar nada."""
    grilla = DIR_GRILLA / "grilla_colombia_5km.csv"
    hansen = list(DIR_HANSEN.glob("*.tif"))
    crudo = DIR_CRUDO / "nacional.csv"
    municipios = DIR_LIMITES / "municipios_dane_mgn2025.geojson"
    panel = DIR_PANEL / "panel_deforestacion_colombia.csv"
    gb_h = sum(f.stat().st_size for f in hansen) / 1e9

    def _ok(p: Path) -> str:
        return "OK" if p.exists() else "falta"

    logger.info("=" * 62)
    logger.info("ESTADO DEL PIPELINE")
    logger.info("  1. grilla     : %s",
                "OK" if grilla.exists() else "FALTA (python main_local.py grilla)")
    logger.info("  2. hansen     : %d archivos, %.1f GB", len(hansen), gb_h)
    logger.info("  3. gfw        : %s (%s)", _ok(crudo), crudo.name)
    logger.info("  4. municipios : %s (%s) [opcional, se auto-descarga en consolidar]",
                _ok(municipios), municipios.name)
    logger.info("  5. panel      : %s (%s)", _ok(panel), panel.name)
    logger.info("=" * 62)
    return 0


def main() -> int:
    """Punto de entrada: python main_local.py <subcomando> [opciones].

    Ver el docstring del inicio del archivo para el orden recomendado
    de subcomandos, y GUIA_CODIGO.md para la explicacion completa de
    cada paso.
    """
    p = argparse.ArgumentParser(
        description="Panel de deforestacion de Colombia (Global Forest Watch)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("grilla")
    sub.add_parser("hansen")
    sub.add_parser("gfw")
    sub.add_parser("municipios")
    sub.add_parser("estado")

    pc = sub.add_parser("consolidar")
    pc.add_argument("--dane", default=None,
                    help=("Ruta a un shapefile/geojson municipal alterno. "
                          "Si se omite, se usa (descargandolo si hace falta) "
                          "el de datos/limites/, ver municipios."))

    a = p.parse_args()
    cfg = Config()

    if a.cmd == "estado":
        return cmd_estado(cfg)

    if a.cmd == "grilla":
        return _correr("exportar_grilla.py")

    if a.cmd == "hansen":
        return _correr("descargar_hansen.py")

    if a.cmd == "gfw":
        return _correr("descargar_gfw.py")

    if a.cmd == "municipios":
        return _correr("descargar_municipios.py")

    if a.cmd == "consolidar":
        # A diferencia de los demas subcomandos, este SI importa la
        # funcion directamente en vez de lanzar un subproceso.
        from consolidar import consolidar
        consolidar(cfg, a.dane)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
