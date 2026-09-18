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
El profesor le dio acceso de lectura a estas tres tablas a las cuentas
personales de Google del equipo desde el 14/09/2026, pero todavia NO a
la cuenta de servicio "pipeline-satelital" que usa el resto del
pipeline (correo enviado, pendiente de respuesta). Este script por eso
usa SIEMPRE la cuenta personal (Application Default Credentials / ADC)
-- no tiene modo "servicio" ni bandera que elegir, para no repetir la
confusion de tener dos flujos de credenciales mezclados en el mismo
comando. Cuando el profesor autorice la cuenta de servicio, este script
deja de ser necesario: esas tres tablas se agregan de vuelta a FUENTES
en describir_fuentes.py y "python main_local.py describir-fuentes"
vuelve a cubrir las siete de una vez.

CREDENCIAL: tu cuenta personal de Google, via ADC
---------------------------------------------------
Requiere haber corrido, una sola vez en esta maquina:

    gcloud auth application-default login

e iniciar sesion en el navegador con la MISMA cuenta de Google que el
profesor autorizo para las tres tablas (no la cuenta de servicio, no
necesariamente la cuenta con la que usas Windows -- si tu navegador
por defecto no es donde tienes esa cuenta iniciada, copia la URL que
imprime el comando y pegala en el navegador correcto).

Si no se han configurado las credenciales, el script lo dice claro y
no hace nada mas (no intenta usar la cuenta de servicio como respaldo).

USO (desde la raiz del proyecto, normalmente via main_local.py)
------------------------------------------------------------------
    python main_local.py describir-fuentes-profesor

    (equivalente directo: python describir_fuentes_profesor.py)

Vuelve a generar DESCRIPCION_FUENTES_PROFESOR.md completo cada vez que
se corre (no es incremental, igual que describir_fuentes.py).
======================================================================
"""
from __future__ import annotations

from pathlib import Path

from config_local import logger
from describir_fuentes import _describir_tabla

AQUI = Path(__file__).resolve().parent

ARCHIVO_REPORTE = AQUI / "DESCRIPCION_FUENTES_PROFESOR.md"

# etiqueta legible -> tabla completamente calificada (proyecto.dataset.tabla)
FUENTES = {
    "FINAGRO - desembolsos de credito (Observatorio, solo lectura)":
        "prueba-ofr.Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA",
    "SFC414 (Observatorio, solo lectura)":
        "prueba-ofr.Inclusion_Financiera.SFC414_DASH",
    "Municipios - codigo (Observatorio, solo lectura)":
        "prueba-ofr.Municipios.CODIGO",
}


def _credenciales_personales():
    """Carga la cuenta personal de Google via Application Default
    Credentials (ADC). Import diferido: el resto del pipeline no
    necesita google-auth para nada.
    """
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


def main() -> int:
    credenciales = _credenciales_personales()
    if credenciales is None:
        return 1

    from google.cloud import bigquery

    # El proyecto que "ejecuta"/paga la consulta es siempre el nuestro;
    # las tablas de prueba-ofr se leen igual, por su nombre completo
    # (consulta cross-project -- ver GUIA_BIGQUERY.md).
    client = bigquery.Client(project="ofr-credito-deforestacion", credentials=credenciales)

    lineas = [
        "# Descripcion de las fuentes del Observatorio (cuenta personal)\n\n",
        "Generado automaticamente por `describir_fuentes_profesor.py`, "
        "usando la cuenta personal de Google (ADC) mientras el profesor "
        "autoriza la cuenta de servicio para estas tres tablas -- ver "
        "describir_fuentes.py para las cuatro tablas propias. "
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
    raise SystemExit(main())
