"""
describir_fuentes.py
======================================================================
Paso 1 del EDA (segun lo pedido por el tutor): antes de poder decir si
hace falta limpieza, definir el periodo de tiempo o proponer KPIs, hay
que saber con certeza que tiene cada una de las siete fuentes que se
van a cruzar -- hoy eso no esta documentado en ningun lado del codigo.

Este script consulta BigQuery directamente y para cada tabla obtiene:
columnas y tipos de dato, numero de filas, y una muestra de 5 filas.
Deja todo consolidado en DESCRIPCION_FUENTES.md, en la raiz del
repositorio, para poder revisarlo y decidir sobre eso (llaves de cruce
municipal, columnas de fecha, si falta poblacion/area para los KPIs,
etc.) sin tener que volver a entrar a la consola de BigQuery.

Fuentes cubiertas
------------------
Panel satelital propio (proyecto ofr-credito-deforestacion, dataset
staging -- ver GUIA_BIGQUERY.md):
    stg_gfw_alertas, stg_hansen_perdida, stg_ideam_deforestacion,
    stg_dtd_alertas

Datos del Observatorio (proyecto prueba-ofr, del profesor Jairo --
acceso de SOLO LECTURA a estas tres tablas puntuales, otorgado el
14/09/2026):
    Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA
    Inclusion_Financiera.SFC414_DASH
    Municipios.CODIGO

Por que una sola consulta por tabla, y no client.get_table()
--------------------------------------------------------------
Las tres tablas del profesor solo tienen permiso de lectura a nivel de
ESA tabla puntual, no del dataset. Pedir metadatos del dataset
(listar tablas, INFORMATION_SCHEMA.COLUMNS) da "Access Denied" con ese
permiso (ver GUIA_BIGQUERY.md), aunque correr una consulta normal
sobre la tabla si funciona. Por eso aqui el esquema, el conteo de
filas y la muestra se obtienen todos corriendo consultas (SELECT...),
nunca pidiendo metadatos aparte -- asi el mismo script sirve igual
para las tablas propias y para las del profesor.

CREDENCIAL
----------
Por defecto usa la misma llave que subir_bigquery.py:
datos/logs/bigquery-key.json (o la variable de entorno
GOOGLE_APPLICATION_CREDENTIALS). Ver GUIA_CODIGO.md seccion 5.16.

Solucion temporal mientras el profesor le da acceso a la cuenta de
servicio sobre las tres tablas de prueba-ofr: --credenciales personal
usa tu propia cuenta de Google (Application Default Credentials) en vez
de la cuenta de servicio. Sirve porque el profesor SI le dio acceso a
tu cuenta personal desde el principio -- asi describir_fuentes.py puede
leer las 7 fuentes de una vez, sin esperar. Requiere haber corrido antes
"gcloud auth application-default login" (una sola vez por maquina) e
iniciar sesion ahi con la MISMA cuenta de Google que el profesor
autorizo. Ver GUIA_CODIGO.md seccion 5.17 para el detalle. Cuando el
profesor confirme el acceso de la cuenta de servicio, se vuelve a correr
sin la bandera (--credenciales servicio, el default) y no hay que tocar
nada mas: FUENTES y el resto del script son identicos en ambos modos.

USO (desde la raiz del proyecto, normalmente via main_local.py)
------------------------------------------------------------------
    python main_local.py describir-fuentes
    python main_local.py describir-fuentes --credenciales personal

    (equivalente directo: python describir_fuentes.py [--credenciales ...])

Vuelve a generar DESCRIPCION_FUENTES.md completo cada vez que se
corre (no es incremental) -- correrlo de nuevo cuando cambien las
tablas de origen es la forma de mantener el reporte al dia.
======================================================================
"""
from __future__ import annotations

import os
from pathlib import Path

from config_local import DIR_LOG, logger

AQUI = Path(__file__).resolve().parent

# Ruta esperada de la llave de la cuenta de servicio "pipeline-satelital".
# Ver GUIA_CODIGO.md seccion 5.16.
ARCHIVO_KEY = DIR_LOG / "bigquery-key.json"

ARCHIVO_REPORTE = AQUI / "DESCRIPCION_FUENTES.md"

# etiqueta legible -> tabla completamente calificada (proyecto.dataset.tabla)
FUENTES = {
    "GFW - alertas de disturbio (staging propio)":
        "ofr-credito-deforestacion.staging.stg_gfw_alertas",
    "Hansen - perdida de cobertura arborea (staging propio)":
        "ofr-credito-deforestacion.staging.stg_hansen_perdida",
    "IDEAM - deforestacion oficial (staging propio)":
        "ofr-credito-deforestacion.staging.stg_ideam_deforestacion",
    "DTD - alertas tempranas oficiales (staging propio)":
        "ofr-credito-deforestacion.staging.stg_dtd_alertas",
    "FINAGRO - desembolsos de credito (Observatorio, solo lectura)":
        "prueba-ofr.Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA",
    "SFC414 (Observatorio, solo lectura)":
        "prueba-ofr.Inclusion_Financiera.SFC414_DASH",
    "Municipios - codigo (Observatorio, solo lectura)":
        "prueba-ofr.Municipios.CODIGO",
}


def _credenciales(modo: str):
    """Localiza y carga las credenciales de BigQuery segun `modo`.

    Import diferido de las librerias de Google (aqui y en el resto del
    modulo): asi el resto del pipeline, que no las necesita para nada,
    sigue funcionando aunque no esten instaladas todavia.

    modo="servicio" (default): la cuenta de servicio "pipeline-satelital"
    (ARCHIVO_KEY). El modo normal del pipeline -- no depende de que una
    persona puntual tenga la sesion iniciada.

    modo="personal": tu propia cuenta de Google, via Application Default
    Credentials (ADC). Solucion temporal mientras el profesor le da
    acceso a la cuenta de servicio (ver el docstring del modulo).
    """
    if modo == "personal":
        import google.auth

        try:
            credenciales, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/bigquery"])
        except Exception as e:  # noqa: BLE001 -- mensaje claro en vez del traceback de google-auth
            logger.error(
                "No se encontraron credenciales personales (ADC). Corre "
                "'gcloud auth application-default login' e inicia sesion "
                "con la cuenta de Google que autorizo el profesor, y "
                "vuelve a intentar. Detalle: %s", e)
            return None
        return credenciales

    from google.oauth2 import service_account

    ruta = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    ruta = Path(ruta) if ruta else ARCHIVO_KEY
    if not ruta.exists():
        logger.error(
            "No se encontro la credencial de BigQuery en %s. Ver "
            "subir_bigquery.py y GUIA_CODIGO.md seccion 5.16.", ruta)
        return None
    return service_account.Credentials.from_service_account_file(str(ruta))


def _describir_tabla(client, tabla: str) -> dict:
    """Corre dos consultas sobre `tabla` y devuelve columnas/tipos,
    numero de filas y una muestra de 5 filas -- o el error, si la
    tabla no existe o no hay permiso para leerla.
    """
    resultado = {"columnas": [], "filas": None, "muestra": None, "error": None}
    try:
        muestra = client.query(f"SELECT * FROM `{tabla}` LIMIT 5").result()
        resultado["columnas"] = [(c.name, c.field_type) for c in muestra.schema]
        resultado["muestra"] = muestra.to_dataframe()

        fila_conteo = list(client.query(f"SELECT COUNT(*) AS n FROM `{tabla}`").result())
        resultado["filas"] = fila_conteo[0]["n"]
    except Exception as e:  # noqa: BLE001 -- una tabla con error no debe tumbar el resto
        resultado["error"] = str(e)
    return resultado


def main(modo: str = "servicio") -> int:
    credenciales = _credenciales(modo)
    if credenciales is None:
        return 1

    from google.cloud import bigquery

    # El proyecto que "ejecuta"/paga la consulta es siempre el nuestro;
    # las tablas de prueba-ofr se leen igual, por su nombre completo
    # (consulta cross-project -- ver GUIA_BIGQUERY.md).
    client = bigquery.Client(project="ofr-credito-deforestacion", credentials=credenciales)

    lineas = [
        "# Descripcion de las fuentes de datos\n\n",
        "Generado automaticamente por `describir_fuentes.py` "
        "(Paso 1 del EDA: inventario y descripcion inicial de datos). "
        "No editar a mano -- se vuelve a generar completo cada vez que "
        "se corre el script.\n",
    ]

    ok, con_error = 0, 0
    for etiqueta, tabla in FUENTES.items():
        logger.info("Describiendo %s (%s) ...", etiqueta, tabla)
        info = _describir_tabla(client, tabla)
        lineas.append(f"\n## {etiqueta}\n\n")
        lineas.append(f"Tabla: `{tabla}`\n")

        if info["error"]:
            con_error += 1
            logger.warning("  No se pudo describir: %s", info["error"])
            lineas.append(f"\n**No se pudo leer esta tabla:** {info['error']}\n")
            continue

        ok += 1
        logger.info("  %s filas, %d columnas", f"{info['filas']:,}", len(info["columnas"]))
        lineas.append(f"\nFilas: **{info['filas']:,}** -- Columnas: **{len(info['columnas'])}**\n")
        lineas.append("\n| Columna | Tipo |\n|---|---|\n")
        for nombre, tipo in info["columnas"]:
            lineas.append(f"| {nombre} | {tipo} |\n")
        lineas.append("\nMuestra (primeras 5 filas):\n\n")
        lineas.append(info["muestra"].to_markdown(index=False))
        lineas.append("\n")

    ARCHIVO_REPORTE.write_text("".join(lineas), encoding="utf-8")
    logger.info("Listo: %d/%d tabla(s) descritas correctamente. Reporte en %s.",
                ok, len(FUENTES), ARCHIVO_REPORTE)
    return 0 if con_error == 0 else 1


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument(
        "--credenciales", choices=["servicio", "personal"], default="servicio",
        help=("'servicio' (default): cuenta de servicio pipeline-satelital. "
              "'personal': tu cuenta de Google via ADC -- solucion temporal "
              "mientras el profesor autoriza la cuenta de servicio, ver "
              "docstring del modulo."))
    a = p.parse_args()
    raise SystemExit(main(a.credenciales))
