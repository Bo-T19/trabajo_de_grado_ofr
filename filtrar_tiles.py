"""
filtrar_tiles.py
======================================================================
Reduce el inventario a los tiles MGRS que REALMENTE contienen celdas
de la grilla de Colombia.

El bbox usado para consultar CMR es un rectangulo e incluye Venezuela,
Brasil, Peru, Ecuador, Panama y oceano. Este script convierte cada
celda de la grilla a su cuadricula MGRS de 100 km (que es el mismo
identificador de tile que usan HLS y DIST-ALERT) y se queda solo con
esos tiles.

    pip install mgrs
    python filtrar_tiles.py

Reescribe datos/logs/inventario_dist.json y guarda el original como
inventario_dist.json.completo por si acaso.
======================================================================
"""
from __future__ import annotations

import json
import shutil
from collections import Counter

import pandas as pd

from config_local import Config, DIR_GRILLA, DIR_LOG, logger

GRILLA_CSV = DIR_GRILLA / "grilla_colombia_5km.csv"
INVENTARIO = DIR_LOG / "inventario_dist.json"
RESPALDO = DIR_LOG / "inventario_dist.json.completo"
LISTA = DIR_LOG / "tiles_colombia.txt"


def _norm(tile: str) -> str:
    """
    Forma canonica del identificador de tile: SIN el prefijo 'T'.

    La libreria mgrs devuelve '18NWH'; los nombres de archivo de
    DIST-ALERT traen '_T18NWH_' y el parser de descargar_dist.py captura
    solo '18NWH'. Se normaliza todo a esa forma para que los conjuntos
    se puedan comparar.
    """
    t = str(tile).strip().upper()
    return t[1:] if t.startswith("T") and len(t) == 6 else t


def tiles_de_la_grilla(cfg: Config) -> Counter:
    """
    Tile MGRS de 100 km que contiene cada celda.

    Precision 0 en la libreria mgrs devuelve el identificador de la
    cuadricula de 100 km (p.ej. '18NWH'), que es exactamente el ID de
    tile de Sentinel-2 / HLS / DIST-ALERT con el prefijo 'T'.

    Recorre CADA celda de la grilla de Colombia (lat, lon) y le
    pregunta a la libreria 'mgrs' en que tile de 100x100 km cae. El
    resultado es un Counter: {tile: cuantas celdas de la grilla caen
    en ese tile}, que ademas sirve como "peso" util para priorizar
    (ver el reporte de tiles con mas celdas al final de main()).
    """
    try:
        import mgrs
    except ImportError:
        raise SystemExit(
            "Falta la libreria mgrs.\n"
            "Ejecute:  pip install mgrs")

    df = pd.read_csv(GRILLA_CSV)
    logger.info("Celdas en la grilla: %d", len(df))

    m = mgrs.MGRS()
    cuenta: Counter = Counter()
    fallos = 0

    for lat, lon in zip(df["lat"].to_numpy(), df["lon"].to_numpy()):
        try:
            # MGRSPrecision=0 -> solo la cuadricula de 100 km, sin
            # digitos de precision adicionales (que darian una
            # ubicacion exacta dentro del tile, que aqui no hace falta).
            codigo = m.toMGRS(float(lat), float(lon), MGRSPrecision=0)
        except Exception:
            fallos += 1
            continue
        cuenta[_norm(codigo)] += 1

    if fallos:
        logger.warning("Celdas sin conversion MGRS: %d", fallos)
    return cuenta


def main() -> int:
    cfg = Config()

    if not GRILLA_CSV.exists():
        logger.error("Falta %s. Ejecute: python main_local.py grilla", GRILLA_CSV)
        return 1
    if not INVENTARIO.exists():
        logger.error("Falta %s. Ejecute: python main_local.py inventario",
                     INVENTARIO)
        return 1

    # Conjunto de tiles que SI hacen falta (contienen al menos una
    # celda de la grilla de Colombia).
    cuenta = tiles_de_la_grilla(cfg)
    necesarios = set(cuenta)
    logger.info("Tiles MGRS que contienen celdas de Colombia: %d",
                len(necesarios))

    # Conjunto de tiles que aparecen en el inventario actual (calculado
    # con el bbox rectangular, asi que incluye tiles de paises vecinos
    # y oceano que no interesan).
    plan = json.loads(INVENTARIO.read_text())
    tiles_plan = {_norm(t) for periodo in plan.values() for t in periodo}
    logger.info("Tiles en el inventario actual: %d", len(tiles_plan))

    # Salvaguarda: si los dos conjuntos de tiles no comparten NADA, lo
    # mas probable es un desajuste de formato entre como 'mgrs' nombra
    # los tiles y como los nombra el inventario (por ejemplo, uno con
    # el prefijo "T" y el otro sin el). En ese caso no se modifica el
    # inventario -- mejor fallar ruidosamente que borrar datos validos.
    if not (tiles_plan & necesarios):
        logger.error("Los dos conjuntos no se cruzan en NADA.")
        logger.error("  ejemplo del inventario : %s", sorted(tiles_plan)[:3])
        logger.error("  ejemplo de la grilla   : %s", sorted(necesarios)[:3])
        logger.error("Hay un desajuste de formato. No se modifica nada.")
        return 1

    sobran = tiles_plan - necesarios   # en el inventario pero no hacen falta
    faltan = necesarios - tiles_plan   # hacen falta pero CMR no tiene datos
    logger.info("  se descartan (fuera de Colombia): %d", len(sobran))
    logger.info("  sin datos en el inventario      : %d", len(faltan))
    if faltan:
        logger.warning("  Tiles esperados sin granulos: %s",
                       sorted(faltan)[:20])
        logger.warning("  Suele ser nubosidad persistente o borde de pais.")

    antes = sum(len(p) * 2 for p in plan.values())
    # Reconstruye el plan, quedandose solo con los tiles necesarios en
    # cada periodo (el resto de la estructura -- periodos, sellos,
    # enlaces -- queda igual).
    filtrado = {clave: {t: v for t, v in periodo.items()
                        if _norm(t) in necesarios}
                for clave, periodo in plan.items()}
    despues = sum(len(p) * 2 for p in filtrado.values())

    # Respalda el inventario SIN filtrar antes de sobreescribirlo, por
    # si hace falta revertir o auditar despues. Solo la primera vez
    # (si ya existe un respaldo, no lo pisa con una version ya filtrada).
    if not RESPALDO.exists():
        shutil.copy2(INVENTARIO, RESPALDO)
        logger.info("Respaldo del inventario completo: %s", RESPALDO)

    INVENTARIO.write_text(json.dumps(filtrado, indent=1))
    LISTA.write_text("\n".join(f"{t}\t{cuenta[t]}"
                              for t in sorted(necesarios)))

    logger.info("=" * 62)
    logger.info("INVENTARIO FILTRADO")
    logger.info("  tiles      : %d  (antes %d)", len(necesarios), len(tiles_plan))
    logger.info("  archivos   : %d  (antes %d)", despues, antes)
    logger.info("  ahorro     : %.0f%%", 100 * (1 - despues / max(antes, 1)))
    logger.info("  estimado   : %.0f - %.0f GB",
                despues * 0.0015, despues * 0.005)
    logger.info("  lista      : %s", LISTA)
    logger.info("=" * 62)
    logger.info("Siguiente: python main_local.py descargar")

    top = cuenta.most_common(10)
    logger.info("Tiles con mas celdas: %s", top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
