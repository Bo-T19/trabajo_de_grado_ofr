"""
descargar_hansen.py
======================================================================
Descarga los granulos de Hansen Global Forest Change (GFC) que cubren
Colombia: dos capas por granulo espacial (treecover2000, lossyear),
alojadas por Google en Cloud Storage, sin autenticacion.

    python descargar_hansen.py

REANUDABLE: si un archivo ya existe con tamaño plausible, se salta.
Puede interrumpir con Ctrl+C y relanzar.
======================================================================
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

import requests

from config_local import Config, DIR_HANSEN, logger

# URL base publica del producto Hansen GFC. No requiere autenticacion.
HANSEN_BASE = "https://storage.googleapis.com/earthenginepartners-hansen"


def granulos_hansen(cfg: Config) -> List[str]:
    """Nombres de los granulos 10x10 grados que intersectan el bbox.

    Hansen GFC no se distribuye como un solo archivo global: viene
    partido en "granulos" de 10x10 grados (lat/lon), cada uno nombrado
    segun su esquina SUPERIOR IZQUIERDA, p.ej. "10N_080W" cubre el
    rectangulo de lat [0,10) y lon [-80,-70). Esta funcion calcula, a
    partir del bbox de Colombia, cuales de esos rectangulos hacen falta.
    """
    lon_min, lat_min, lon_max, lat_max = cfg.bbox
    nombres = []
    lat_tops = range(int((lat_max // 10 + 1) * 10),
                     int(lat_min // 10 * 10), -10)
    lon_lefts = range(int(lon_min // 10 * 10),
                      int((lon_max // 10 + 1) * 10), 10)
    for top in lat_tops:
        for left in lon_lefts:
            ns = "N" if top >= 0 else "S"
            ew = "W" if left < 0 else "E"
            nombres.append(f"{abs(top):02d}{ns}_{abs(left):03d}{ew}")
    return nombres


def descargar_url(url: str, destino: Path, cfg: Config,
                  minimo_bytes: int = 1024) -> bool:
    """GET por streaming, con reintentos. Salta si ya existe.

    Patron de descarga "atomica": el contenido se escribe primero a un
    archivo temporal '<destino>.parcial', y solo se renombra al nombre
    final si la descarga termino bien -- asi una interrupcion a la
    mitad nunca deja un archivo con el nombre "bueno" pero contenido
    incompleto.
    """
    if destino.exists() and destino.stat().st_size > minimo_bytes:
        return True

    tmp = destino.with_suffix(destino.suffix + ".parcial")
    for intento in range(1, cfg.reintentos + 1):
        try:
            with requests.get(url, stream=True, timeout=cfg.timeout_s) as r:
                r.raise_for_status()
                with tmp.open("wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
            if tmp.stat().st_size <= minimo_bytes:
                raise RuntimeError("archivo sospechosamente pequeno")
            tmp.replace(destino)
            return True
        except Exception as exc:
            logger.warning("  intento %d/%d fallo (%s): %s",
                           intento, cfg.reintentos, destino.name,
                           str(exc)[:120])
            tmp.unlink(missing_ok=True)
    return False


def main() -> int:
    cfg = Config()
    gs = granulos_hansen(cfg)
    v = cfg.hansen_version
    logger.info("Granulos Hansen sobre Colombia: %d -> %s", len(gs), gs)

    tareas: List[Tuple[str, Path]] = []
    for g in gs:
        for capa in ("treecover2000", "lossyear"):
            nombre = f"Hansen_{v}_{capa}_{g}.tif"
            tareas.append((f"{HANSEN_BASE}/{v}/{nombre}",
                           DIR_HANSEN / nombre))

    fallidos = []
    with ThreadPoolExecutor(max_workers=cfg.hilos_descarga) as pool:
        futs = {pool.submit(descargar_url, u, d, cfg, 1 << 20): d
                for u, d in tareas}
        for i, fut in enumerate(as_completed(futs), 1):
            d = futs[fut]
            ok = fut.result()
            mb = d.stat().st_size / 1e6 if d.exists() else 0
            logger.info("[%d/%d] %s %s (%.0f MB)",
                        i, len(tareas), "OK  " if ok else "FALLO", d.name, mb)
            if not ok:
                fallidos.append(d.name)

    if fallidos:
        logger.error("Granulos fallidos: %s", fallidos)
        return 1
    logger.info("Hansen completo en %s", DIR_HANSEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
