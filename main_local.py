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
        Construye la TABLA 1 (alertas GFW, celda x mes) en datos/panel/,
        con cruce municipal automatico (descarga los limites si aun no
        estan en disco).

    python main_local.py ideam
        Descarga las capas oficiales de cambio de bosque del SMByC
        (IDEAM). ~53 MB por periodo, sin cuenta ni credencial.

    python main_local.py panel-hansen
        TABLA 2: perdida anual de cobertura arborea por celda (Hansen).
        No descarga nada: usa los granulos que ya bajo "hansen".

    python main_local.py panel-ideam
        TABLA 3: deforestacion oficial por celda y periodo (IDEAM).

    python main_local.py dtd
        Descarga las detecciones tempranas de deforestacion del SMByC
        (IDEAM), un archivo por trimestre. Sin cuenta ni credencial.

    python main_local.py panel-dtd
        TABLA 4: alertas tempranas oficiales por celda y trimestre.

    Las tres tablas miden conceptos DISTINTOS sobre el mismo territorio
    -- disturbio (GFW), perdida de cobertura arborea (Hansen) y
    deforestacion de bosque natural (IDEAM) -- y por eso NUNCA se suman
    entre si. Comparten grilla, bosque base y cruce municipal, que es lo
    que las hace comparables. Ver METODOLOGIA.md seccion 2.

    python main_local.py consolidar --dane ruta/al/otro_archivo.shp
        Igual, pero usando un shapefile/geojson municipal distinto en
        vez del descargado automaticamente del DANE.

    python main_local.py estado
        Que hay en disco y que falta.

    python main_local.py subir-bigquery
        Sube las tablas del panel que ya existan en datos/panel/ al
        dataset "staging" del proyecto de BigQuery del equipo
        (ofr-credito-deforestacion). Requiere la llave de la cuenta de
        servicio "pipeline-satelital" en datos/logs/bigquery-key.json
        (o en la variable de entorno GOOGLE_APPLICATION_CREDENTIALS).
        Ver subir_bigquery.py y GUIA_CODIGO.md seccion 5.16.

    python main_local.py describir-fuentes
        Paso 1 del EDA: describe las cuatro tablas del panel propio en
        BigQuery -- columnas, tipos de dato, numero de filas y una
        muestra de 5 filas por tabla. Requiere la misma credencial que
        subir-bigquery. Genera/actualiza DESCRIPCION_FUENTES.md en la
        raiz del repositorio. Ver describir_fuentes.py.

    python main_local.py describir-fuentes-profesor
        Igual, pero para las tres tablas de solo lectura del
        Observatorio en prueba-ofr, usando tu cuenta personal de
        Google (ADC) en vez de la cuenta de servicio -- solucion
        temporal mientras el profesor le da acceso a la cuenta de
        servicio sobre esas tres tablas. Requiere "gcloud auth
        application-default login" una vez, iniciando sesion con la
        cuenta que el profesor autorizo. Genera
        DESCRIPCION_FUENTES_PROFESOR.md aparte. Cuando el profesor
        confirme el acceso de la cuenta de servicio, este comando deja
        de ser necesario. Ver describir_fuentes_profesor.py.
======================================================================
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from config_local import (Config, DIR_CRUDO, DIR_DTD, DIR_GRILLA,
                          DIR_HANSEN, DIR_IDEAM, DIR_LIMITES, DIR_PANEL,
                          logger)

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
    p_hansen = DIR_PANEL / "panel_hansen.csv"
    p_ideam = DIR_PANEL / "panel_ideam.csv"
    p_dtd = DIR_PANEL / "panel_dtd.csv"
    capas_ideam = list(DIR_IDEAM.glob("cambio_*.img"))
    capas_dtd = list(DIR_DTD.glob("atd_*.kml"))
    gb_h = sum(f.stat().st_size for f in hansen) / 1e9
    gb_i = sum(f.stat().st_size for f in capas_ideam) / 1e9

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
    logger.info("  5. capas IDEAM: %d archivos, %.1f GB", len(capas_ideam), gb_i)
    logger.info("  6. DTD trimest: %d archivos", len(capas_dtd))
    logger.info("  --- tablas de salida ---")
    logger.info("  T1 GFW alertas: %s (%s)", _ok(panel), panel.name)
    logger.info("  T2 Hansen     : %s (%s)", _ok(p_hansen), p_hansen.name)
    logger.info("  T3 IDEAM      : %s (%s)", _ok(p_ideam), p_ideam.name)
    logger.info("  T4 DTD alertas: %s (%s)", _ok(p_dtd), p_dtd.name)
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
    sub.add_parser("ideam")
    sub.add_parser("panel-hansen")
    sub.add_parser("panel-ideam")
    sub.add_parser("dtd")
    sub.add_parser("panel-dtd")
    sub.add_parser("estado")

    pb = sub.add_parser("subir-bigquery")
    pb.add_argument("--solo", default=None,
                    help="Lista separada por comas: gfw,hansen,ideam,dtd (default: todas).")
    pb.add_argument("--dataset", default=None,
                    help="Dataset de BigQuery destino (default: staging, ver subir_bigquery.py).")

    sub.add_parser("describir-fuentes")
    sub.add_parser("describir-fuentes-profesor")

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

    if a.cmd == "ideam":
        return _correr("descargar_ideam.py")

    if a.cmd == "panel-hansen":
        return _correr("panel_hansen.py")

    if a.cmd == "panel-ideam":
        return _correr("panel_ideam.py")

    if a.cmd == "dtd":
        return _correr("descargar_dtd.py")

    if a.cmd == "panel-dtd":
        return _correr("panel_dtd.py")

    if a.cmd == "subir-bigquery":
        args = []
        if a.solo:
            args += ["--solo", a.solo]
        if a.dataset:
            args += ["--dataset", a.dataset]
        return _correr("subir_bigquery.py", *args)

    if a.cmd == "describir-fuentes":
        return _correr("describir_fuentes.py")

    if a.cmd == "describir-fuentes-profesor":
        return _correr("describir_fuentes_profesor.py")

    if a.cmd == "consolidar":
        # A diferencia de los demas subcomandos, este SI importa la
        # funcion directamente en vez de lanzar un subproceso.
        from consolidar import consolidar
        consolidar(cfg, a.dane)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
