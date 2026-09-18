"""
subir_bigquery.py
======================================================================
Sube las tablas del panel (datos/panel/*.csv) al dataset "staging" del
proyecto de BigQuery del equipo (ofr-credito-deforestacion), para que
dejen de vivir solo en el disco local y puedan cruzarse alla con los
datos financieros que comparta el profesor (Finagro, UPRA, Superfinan-
ciera) una vez el Observatorio otorgue el acceso de lectura.

Cada tabla LOCAL se sube COMPLETA (WRITE_TRUNCATE, "reemplazar"): como
cada corrida de consolidar.py / panel_hansen.py / panel_ideam.py /
panel_dtd.py reconstruye el CSV entero desde cero, subir en modo
"reemplazar" mantiene BigQuery igual de sincronizado que el disco local
sin duplicar filas. No es un append incremental.

CREDENCIAL
----------
Usa la cuenta de servicio "pipeline-satelital" (creada en el proyecto
ofr-credito-deforestacion, con permisos BigQuery Data Editor + BigQuery
Job User: puede leer/escribir tablas y correr jobs, nada mas). Se
espera la llave .json en:

    datos/logs/bigquery-key.json   (fuera del control de versiones,
                                     igual que gfw_api_key.txt -- ver
                                     .gitignore y configurar_gfw.py)

o, si se prefiere no dejarla en disco del proyecto, en la variable de
entorno GOOGLE_APPLICATION_CREDENTIALS (ruta absoluta al .json).

USO (desde la raiz del proyecto, normalmente via main_local.py)
------------------------------------------------------------------
    python main_local.py subir-bigquery
        Sube las tablas que ya existan en datos/panel/ (avisa y omite
        las que aun no se hayan generado).

    python main_local.py subir-bigquery --solo gfw,hansen
        Sube solo las tablas indicadas. Alias validos: gfw, hansen,
        ideam, dtd (ver TABLAS mas abajo).

    python main_local.py subir-bigquery --dataset analitica
        Sube al dataset "analitica" en vez de "staging" (por defecto
        las cuatro fuentes van a "staging"; "analitica" se reserva
        para las tablas ya integradas con los datos financieros).

    (equivalente directo: python subir_bigquery.py [--solo ...] [--dataset ...])
======================================================================
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from config_local import DIR_LOG, DIR_PANEL, logger

PROYECTO = "ofr-credito-deforestacion"
DATASET_DEFAULT = "staging"

# Ruta esperada de la llave de la cuenta de servicio "pipeline-satelital".
# Ver GUIA_CODIGO.md seccion 5.16.
ARCHIVO_KEY = DIR_LOG / "bigquery-key.json"

# alias en linea de comandos -> (archivo local generado por el pipeline, tabla destino en BigQuery)
TABLAS = {
    "gfw":    (DIR_PANEL / "panel_deforestacion_colombia.csv", "stg_gfw_alertas"),
    "hansen": (DIR_PANEL / "panel_hansen.csv",                 "stg_hansen_perdida"),
    "ideam":  (DIR_PANEL / "panel_ideam.csv",                  "stg_ideam_deforestacion"),
    "dtd":    (DIR_PANEL / "panel_dtd.csv",                    "stg_dtd_alertas"),
}


def _credenciales():
    """Localiza y carga la credencial de la cuenta de servicio.

    Prioridad: variable de entorno GOOGLE_APPLICATION_CREDENTIALS (si
    esta definida) y, si no, el archivo por defecto en datos/logs/.

    Import diferido de las librerias de Google (aqui y en el resto del
    modulo): asi el resto del pipeline, que no las necesita para nada,
    sigue funcionando aunque no esten instaladas todavia.
    """
    from google.oauth2 import service_account

    ruta = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    ruta = Path(ruta) if ruta else ARCHIVO_KEY
    if not ruta.exists():
        logger.error(
            "No se encontro la credencial de BigQuery en %s. Copie ahi el "
            "archivo .json de la cuenta de servicio 'pipeline-satelital' "
            "(el que se descargo desde la consola de Google Cloud al crearla), "
            "o defina la variable de entorno GOOGLE_APPLICATION_CREDENTIALS "
            "con la ruta donde la haya guardado.", ruta,
        )
        return None
    return service_account.Credentials.from_service_account_file(str(ruta))


def _subir_tabla(client, dataset: str, archivo: Path, tabla: str) -> bool:
    from google.cloud import bigquery

    if not archivo.exists():
        logger.warning(
            "%s no existe todavia (falta correr el paso del pipeline que la genera) -- se omite.",
            archivo.name)
        return False

    # cod_dane hay que leerlo como texto: los codigos DANE llevan cero a
    # la izquierda en Antioquia (05001) y Atlantico (08001), y si pandas
    # lo infiere como entero (lo hace por defecto, porque el texto del
    # CSV "parece" numerico) ese cero desaparece -- y luego autodetect=True
    # de BigQuery hereda ese tipo INTEGER al crear/reemplazar la tabla.
    # Mismo criterio que cargar() en catalogo_paneles.ipynb.
    df = pd.read_csv(archivo, dtype={"cod_dane": "string"})
    destino = f"{PROYECTO}.{dataset}.{tabla}"
    job_config = bigquery.LoadJobConfig(
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    logger.info("Subiendo %s (%d filas) -> %s ...", archivo.name, len(df), destino)
    job = client.load_table_from_dataframe(df, destino, job_config=job_config)
    job.result()  # bloquea hasta que el job de carga termine (o falle)
    logger.info("OK: %s quedo con %d fila(s) en BigQuery.", tabla, job.output_rows)
    return True


def main() -> int:
    p = argparse.ArgumentParser(
        description="Sube las tablas del panel local al proyecto de BigQuery del equipo.")
    p.add_argument("--solo", default=None,
                   help=f"Lista separada por comas de {{{', '.join(TABLAS)}}} (default: todas).")
    p.add_argument("--dataset", default=DATASET_DEFAULT,
                   help=f"Dataset de BigQuery destino (default: {DATASET_DEFAULT}).")
    a = p.parse_args()

    credenciales = _credenciales()
    if credenciales is None:
        return 1

    from google.cloud import bigquery
    client = bigquery.Client(project=PROYECTO, credentials=credenciales)

    alias = [s.strip() for s in a.solo.split(",")] if a.solo else list(TABLAS)
    invalidos = [s for s in alias if s not in TABLAS]
    if invalidos:
        logger.error("Alias desconocido(s): %s (validos: %s)", invalidos, list(TABLAS))
        return 1

    subidas = 0
    for s in alias:
        archivo, tabla = TABLAS[s]
        if _subir_tabla(client, a.dataset, archivo, tabla):
            subidas += 1

    logger.info("Listo: %d/%d tabla(s) subida(s) al dataset '%s' de %s.",
                subidas, len(alias), a.dataset, PROYECTO)
    return 0 if subidas > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
