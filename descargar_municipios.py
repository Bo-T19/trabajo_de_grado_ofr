"""
descargar_municipios.py
======================================================================
Descarga los limites municipales de Colombia directamente del DANE,
sin descarga manual desde el navegador ni cuenta de ningun tipo --
igual que exportar_grilla.py hace con los limites departamentales.

    python descargar_municipios.py
    # equivale a: python main_local.py municipios

Salida: datos/limites/municipios_dane_mgn2025.geojson

FUENTE
------
DANE, Marco Geoestadistico Nacional 2025, nivel Municipio (version
"Grafico" -- generalizada para visualizacion, no la de precision
catastral completa "Politico"). Servida como Feature Service publico
de ArcGIS (sin autenticacion), del MISMO organismo ArcGIS del DANE
que ya usa exportar_grilla.py para los limites departamentales
(ioNRSZMYYlx0PUaB):

    https://services.arcgis.com/ioNRSZMYYlx0PUaB/arcgis/rest/services/
    MGN2025_MPIO_GRAFICO/FeatureServer/0

Por que la version "Grafico" y no "Politico": para asignar un
municipio a cada centroide de celda de la grilla (5x5 km) la precision
de la version generalizada es mas que suficiente -- su tolerancia de
simplificacion es varios ordenes de magnitud menor que el lado de la
celda, asi que no cambia a que municipio cae ningun centroide.
Documentado aqui para que quede trazable en la metodologia.

Colombia tiene 1.122 municipios, por debajo del maxRecordCount (2000)
de este servicio, asi que una sola consulta trae todos los poligonos
sin necesidad de paginar.

Licencia: igual que el resto del Marco Geoestadistico Nacional del
DANE, Creative Commons Attribution 4.0 (CC BY), uso comercial permitido
con atribucion ("Departamento Administrativo Nacional de Estadistica -
DANE: www.dane.gov.co").
======================================================================
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

from config_local import Config, DIR_LIMITES, logger

SALIDA = "municipios_dane_mgn2025.geojson"

DANE_MGN_MUNICIPIOS = (
    "https://services.arcgis.com/ioNRSZMYYlx0PUaB/arcgis/rest/services/"
    "MGN2025_MPIO_GRAFICO/FeatureServer/0/query"
)


def descargar_municipios(cfg: Config) -> dict:
    """
    Trae los poligonos municipales del MGN2025 (version Grafico) del
    servicio ArcGIS del DANE, ya en EPSG:4326 -- el mismo CRS que usa
    asignar_municipio() en consolidar.py para cruzar con los centroides
    de celda, asi que no hace falta reproyectar despues.
    """
    logger.info("Descargando limites municipales del DANE (MGN2025_MPIO_GRAFICO)...")
    r = requests.get(DANE_MGN_MUNICIPIOS, params={
        "where": "1=1",
        "outFields": "mpio_cdpmp,mpio_cnmbr,dpto_cnmbr,dpto_ccdgo",
        "outSR": "4326",
        "f": "geojson",
    }, timeout=cfg.timeout_s)
    r.raise_for_status()
    data = r.json()
    n = len(data.get("features", []))
    if n == 0:
        raise RuntimeError(
            "El servicio del DANE respondio sin features. Respuesta cruda:\n"
            + json.dumps(data, indent=2)[:500])
    logger.info("  %d municipios descargados.", n)
    return data


def ruta_cache() -> Path:
    return DIR_LIMITES / SALIDA


def main() -> int:
    cfg = Config()
    data = descargar_municipios(cfg)

    destino = ruta_cache()
    destino.write_text(json.dumps(data))

    logger.info("=" * 62)
    logger.info("MUNICIPIOS EXPORTADOS")
    logger.info("  municipios : %d", len(data["features"]))
    logger.info("  archivo    : %s", destino)
    logger.info("  fuente     : DANE, Marco Geoestadistico Nacional 2025,"
                " nivel Municipio, version Grafico (CC BY)")
    logger.info("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
