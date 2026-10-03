"""
describir_fuentes_profesor.py
======================================================================
Extension de describir_fuentes.py (Paso 1 del EDA) para las tres tablas
de solo lectura del Observatorio (proyecto prueba-ofr, del profesor
Jairo):
    Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA
    Inclusion_Financiera.SFC414_DASH
    Municipios.CODIGO

Hace exactamente lo mismo que describir_fuentes.py (columnas y tipos de
dato, numero de filas, muestra de 5 filas por tabla) pero solo para
estas tres, y deja el resultado en un reporte aparte:
DESCRIPCION_FUENTES_PROFESOR.md.

Por que un script aparte, y no un modo/bandera dentro de describir_fuentes.py
--------------------------------------------------------------------------------
Hasta el 02/10/2026 el profesor solo habia autorizado estas tres tablas
para las cuentas personales de Google del equipo, no para la cuenta de
servicio "pipeline-satelital" que usa el resto del pipeline, asi que
este script usaba Application Default Credentials (ADC) en vez de la
credencial de servicio. El profesor ya confirmo el acceso de lectura
de la cuenta de servicio sobre las tres tablas (02/10/2026), asi que
este script ahora usa la MISMA credencial de servicio que
describir_fuentes.py (ver _credenciales() en ese modulo). Se mantiene
como script aparte, con su propio reporte, mientras se valida que el
acceso de la cuenta de servicio funciona igual de bien que con la
cuenta personal; una vez validado, lo natural es fusionar estas tres
tablas de vuelta a FUENTES en describir_fuentes.py y retirar este
script, para que "python main_local.py describir-fuentes" vuelva a
cubrir las siete tablas de una vez (pendiente de decision -- ver
GUIA_CODIGO.md seccion 5.18).

CREDENCIAL: cuenta de servicio "pipeline-satelital"
---------------------------------------------------
Igual que describir_fuentes.py: datos/logs/bigquery-key.json, o la
variable de entorno GOOGLE_APPLICATION_CREDENTIALS. Ver GUIA_CODIGO.md
seccion 5.16. Ya NO requiere "gcloud auth application-default login"
ni la cuenta personal de Google.

USO (desde la raiz del proyecto, normalmente via main_local.py)
------------------------------------------------------------------
    python main_local.py describir-fuentes-profesor

    (equivalente directo: python -m pipeline.entendimiento.describir_fuentes_profesor)

Vuelve a generar DESCRIPCION_FUENTES_PROFESOR.md completo cada vez que
se corre (no es incremental, igual que describir_fuentes.py).
======================================================================
"""
from __future__ import annotations

from pipeline.config_local import RAIZ, logger
from pipeline.entendimiento.describir_fuentes import _credenciales, _describir_tabla

ARCHIVO_REPORTE = RAIZ / "docs" / "DESCRIPCION_FUENTES_PROFESOR.md"

# etiqueta legible -> tabla completamente calificada (proyecto.dataset.tabla)
FUENTES = {
    "FINAGRO - desembolsos de credito (Observatorio, solo lectura)":
        "prueba-ofr.Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA",
    "SFC414 (Observatorio, solo lectura)":
        "prueba-ofr.Inclusion_Financiera.SFC414_DASH",
    "Municipios - codigo (Observatorio, solo lectura)":
        "prueba-ofr.Municipios.CODIGO",
}


def main() -> int:
    credenciales = _credenciales()
    if credenciales is None:
        return 1

    from google.cloud import bigquery

    # El proyecto que "ejecuta"/paga la consulta es siempre el nuestro;
    # las tablas de prueba-ofr se leen igual, por su nombre completo
    # (consulta cross-project -- ver GUIA_BIGQUERY.md).
    client = bigquery.Client(project="ofr-credito-deforestacion", credentials=credenciales)

    lineas = [
        "# Descripcion de las fuentes del Observatorio\n\n",
        "Generado automaticamente por `describir_fuentes_profesor.py`, "
        "usando la cuenta de servicio pipeline-satelital (la misma de "
        "describir_fuentes.py) -- ver ese script para las cuatro tablas "
        "propias. No editar a mano -- se vuelve a generar completo cada "
        "vez que se corre el script.\n",
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
    raise SystemExit(main())
