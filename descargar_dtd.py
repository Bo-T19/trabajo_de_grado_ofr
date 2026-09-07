"""
descargar_dtd.py
======================================================================
Descarga las DETECCIONES TEMPRANAS DE DEFORESTACION (DTD) del SMByC
(IDEAM): los puntos de alerta que el instituto publica cada trimestre.

    python main_local.py dtd

Salida: datos/dtd/atd_<anio>_<trimestre>.kml

QUE SON
-------
El SMByC publica cada trimestre, desde 2016, un boletin de alertas
tempranas que identifica los NUCLEOS ACTIVOS de deforestacion del pais.
Junto al boletin en PDF publica dos capas espaciales:

  Puntos/   puntos de alerta individuales (.kml)  <- lo que se usa aqui
  Nucleos/  poligonos de los nucleos activos (.kmz)

Se usan los PUNTOS porque su serie no tiene huecos: van del III trimestre
de 2016 al I de 2026 de forma continua, mientras que los nucleos carecen
del ano 2024 completo en el servidor.

QUE APORTAN AL PROYECTO
-----------------------
Son el unico producto OFICIAL de cadencia sub-anual para Colombia. El
panel de alertas de GFW es mensual pero no oficial; las capas de cambio
del IDEAM son oficiales pero anuales. Los DTD ocupan ese espacio: los
publica el mismo instituto que produce la cifra oficial, cada trimestre,
con cobertura nacional (las cinco regiones naturales).

Cada punto trae ademas atributos que ningun raster entrega: municipio,
vereda, corporacion autonoma regional y, cuando aplica, el area protegida
del SINAP donde cae la alerta.

USO PREVISTO: validacion y contexto. La cifra de alertas NO es la tasa
oficial de deforestacion -- el propio IDEAM lo advierte, igual que el
INPE con DETER en Brasil. Para 2025 el boletin trimestral reporto 72.409
ha mientras la capa consolidada da del orden de 119.000: la diferencia
mide cuanto subestima un sistema de alertas frente al conteo consolidado.

NOMBRES DE ARCHIVO
------------------
El patron es atd_<anio>_<trimestre>_trim.kml, pero la caja de las letras
no es consistente en el servidor (atd_2019_II_trim.kml y
atd_2020_I_trim.kml usan mayuscula; el resto, minuscula). En vez de
adivinar, este modulo LISTA el directorio del servidor y toma los
nombres tal como estan. Asi ademas aparecen solos los trimestres nuevos
que el IDEAM publique, sin tocar codigo.

IMPORTANTE -- HTTPS OBLIGATORIO: el servidor del IDEAM tiene el puerto
80 cerrado. Una URL con "http://" se queda esperando hasta agotar el
tiempo de espera, sin devolver un error de protocolo.
======================================================================
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple

import requests

from config_local import Config, DIR_DTD, logger

BASE = ("https://bart.ideam.gov.co/smbyc/"
        "Boletines%20Detecciones%20Tempranas%20de%20Deforestacion")

# Los trimestres se nombran con numeracion romana en el servidor.
ROMANOS = {"i": 1, "ii": 2, "iii": 3, "iv": 4}


def catalogo(anios: Tuple[int, ...]) -> Dict[Tuple[int, int], str]:
    """
    {(anio, trimestre): nombre_de_archivo} leyendo el indice del
    servidor, en vez de construir los nombres a mano.

    El listado de Apache se parsea con una expresion regular simple; si
    algun ano no tiene carpeta de Puntos (paso con 2015), se omite con
    un aviso en vez de fallar.
    """
    encontrado: Dict[Tuple[int, int], str] = {}
    for anio in anios:
        url = f"{BASE}/{anio}/Puntos/"
        try:
            r = requests.get(url, timeout=60)
        except Exception as e:
            logger.warning("  %d: no se pudo listar (%s)", anio, e)
            continue
        if r.status_code != 200:
            logger.warning("  %d: sin carpeta de Puntos (HTTP %d)", anio, r.status_code)
            continue
        for nombre in re.findall(r'href="([^"?/]+\.kml)"', r.text, re.I):
            m = re.search(rf"atd_{anio}_(i{{1,3}}|iv)_trim", nombre, re.I)
            if m:
                encontrado[(anio, ROMANOS[m.group(1).lower()])] = nombre
    return dict(sorted(encontrado.items()))


def ruta_local(anio: int, trimestre: int) -> Path:
    """Nombre normalizado en disco, sin la irregularidad del servidor."""
    return DIR_DTD / f"atd_{anio}_{trimestre}.kml"


def descargar(anio: int, trimestre: int, nombre: str, cfg: Config) -> bool:
    """Baja un trimestre si no esta en disco. True si queda disponible."""
    destino = ruta_local(anio, trimestre)
    if destino.exists() and destino.stat().st_size > 0:
        logger.info("  %d-T%d: ya esta en disco (%.1f MB)",
                    anio, trimestre, destino.stat().st_size / 1e6)
        return True

    url = f"{BASE}/{anio}/Puntos/{nombre}"
    temporal = destino.with_suffix(".parcial")
    for intento in range(1, cfg.reintentos + 1):
        try:
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
            logger.info("  %d-T%d: listo (%.1f MB)", anio, trimestre, bajado / 1e6)
            return True
        except Exception as e:
            logger.warning("  %d-T%d: intento %d/%d fallo (%s)",
                           anio, trimestre, intento, cfg.reintentos, e)
            temporal.unlink(missing_ok=True)
    logger.error("  %d-T%d: no se pudo descargar", anio, trimestre)
    return False


def main() -> int:
    p = argparse.ArgumentParser(
        description="Descarga las detecciones tempranas de deforestacion (IDEAM)")
    p.add_argument("--anios", nargs="*", type=int, default=None,
                   help="Anios a bajar. Por defecto, los de config_local.py "
                        "(dtd_anios).")
    a = p.parse_args()
    cfg = Config()
    anios = tuple(a.anios) if a.anios else cfg.dtd_anios

    logger.info("Consultando el catalogo del SMByC para %d anios...", len(anios))
    cat = catalogo(anios)
    if not cat:
        logger.error("No se encontro ningun trimestre publicado.")
        return 1

    logger.info("Descargando %d trimestres a %s", len(cat), DIR_DTD)
    ok = sum(descargar(y, t, n, cfg) for (y, t), n in cat.items())
    logger.info("=" * 62)
    logger.info("DTD: %d de %d trimestres disponibles en disco", ok, len(cat))
    logger.info("=" * 62)
    return 0 if ok == len(cat) else 1


if __name__ == "__main__":
    raise SystemExit(main())
