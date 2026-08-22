"""
descargar_dist.py
======================================================================
Trae a disco lo que hace falta para el calculo zonal local:

  1. Hansen GFC: 6 granulos de 10x10 grados sobre Colombia,
     capas treecover2000 y lossyear. Descarga HTTP directa.

  2. DIST-ALERT: una instantanea por tile MGRS por periodo, solo las
     capas VEG-DIST-STATUS y VEG-DIST-DATE. Via earthaccess (CMR).

USO
---
    python fuente_dist_alert/descargar_dist.py hansen
    python fuente_dist_alert/descargar_dist.py inventario     # que hay, sin descargar
    python fuente_dist_alert/descargar_dist.py dist
    python fuente_dist_alert/descargar_dist.py dist --tile T18NXG

REANUDABLE: si un archivo ya existe con tamano plausible, se salta.
Puede interrumpir con Ctrl+C y relanzar.

REQUISITOS
----------
    pip install earthaccess rasterio pyproj pandas requests
    Cuenta gratuita en https://urs.earthdata.nasa.gov
======================================================================
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import requests

# config_local.py vive en la raiz del proyecto, un nivel arriba de
# fuente_dist_alert/. Se agrega esa carpeta a sys.path para poder
# importarlo aunque este script se corra directamente (no como paquete).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config_local import (Config, DIR_DIST, DIR_HANSEN, DIR_LOG, logger)

# URL base publica del producto Hansen Global Forest Change (GFC), alojado
# por Google en Cloud Storage. No requiere autenticacion.
HANSEN_BASE = "https://storage.googleapis.com/earthenginepartners-hansen"
# Archivo donde se guarda el "plan" de descarga de DIST-ALERT: que tile,
# que periodo, que enlaces. Lo escribe cmd_inventario() y lo reutiliza
# cmd_dist() para no tener que volver a consultar CMR cada vez.
INVENTARIO = DIR_LOG / "inventario_dist.json"

# Expresion regular para extraer el tile MGRS del nombre de archivo de
# un granulo DIST-ALERT, p.ej.:
#   OPERA_L3_DIST-ALERT-HLS_T18NXG_20230115T153259Z_..._VEG-DIST-STATUS.tif
# el grupo capturado seria "18NXG" (sin el prefijo "T").
RE_TILE = re.compile(r"_T(\d{2}[A-Z]{3})_")


# =====================================================================
# 1. HANSEN
# =====================================================================
def granulos_hansen(cfg: Config) -> List[str]:
    """Nombres de los granulos 10x10 que intersectan el bbox.

    Hansen GFC no se distribuye como un solo archivo global: viene
    partido en "granulos" de 10x10 grados (lat/lon), cada uno nombrado
    segun su esquina SUPERIOR IZQUIERDA, p.ej. "10N_080W" cubre el
    rectangulo de lat [0,10) y lon [-80,-70). Esta funcion calcula, a
    partir del bbox de Colombia, cuales de esos rectangulos hacen falta.
    """
    lon_min, lat_min, lon_max, lat_max = cfg.bbox
    nombres = []
    # rango de "techos" de latitud (multiplos de 10) que cubren el bbox,
    # de norte a sur (por eso el paso es -10). Ej: si lat_max=13.5,
    # el primer techo es 20 (redondeando hacia arriba al siguiente múltiplo de 10).
    lat_tops = range(int((lat_max // 10 + 1) * 10),
                     int(lat_min // 10 * 10), -10)
    # rango de "bordes izquierdos" de longitud (multiplos de 10), de
    # oeste a este.
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
    final (tmp.replace(destino)) si la descarga terminó bien. Asi, si
    el proceso se interrumpe a la mitad (Ctrl+C, corte de luz, error de
    red), nunca queda un archivo con el nombre "bueno" pero contenido
    incompleto -- lo que haria que una relanzada del script lo diera
    por ya-descargado sin estarlo.
    """
    # Si el archivo destino ya existe y pesa mas que el minimo esperado,
    # se asume que ya se descargo bien en una corrida anterior: se salta.
    # Esto es lo que hace que el script sea "reanudable" con Ctrl+C.
    if destino.exists() and destino.stat().st_size > minimo_bytes:
        return True

    tmp = destino.with_suffix(destino.suffix + ".parcial")
    for intento in range(1, cfg.reintentos + 1):
        try:
            # stream=True: no carga todo el archivo en memoria de una vez,
            # lo va leyendo y escribiendo por bloques de 1 MiB (1 << 20).
            with requests.get(url, stream=True, timeout=cfg.timeout_s) as r:
                r.raise_for_status()   # lanza excepcion si el HTTP status es de error (4xx/5xx)
                with tmp.open("wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
            if tmp.stat().st_size <= minimo_bytes:
                # Un archivo "exitoso" pero sospechosamente chico suele
                # ser una pagina de error HTML disfrazada de 200 OK.
                raise RuntimeError("archivo sospechosamente pequeno")
            tmp.replace(destino)   # renombrado atomico: solo aqui se considera "completo"
            return True
        except Exception as exc:
            logger.warning("  intento %d/%d fallo (%s): %s",
                           intento, cfg.reintentos, destino.name,
                           str(exc)[:120])
            tmp.unlink(missing_ok=True)   # limpia el parcial antes de reintentar
    return False


def cmd_hansen(cfg: Config) -> int:
    """Descarga todos los granulos de Hansen GFC que cubren Colombia.

    Por cada granulo espacial se bajan DOS archivos: treecover2000
    (dosel en el ano 2000) y lossyear (ano de perdida de bosque). Las
    descargas se paralelizan con un pool de hilos porque son E/S
    (red), no CPU: mientras un hilo espera datos de la red, otro puede
    avanzar.
    """
    gs = granulos_hansen(cfg)
    v = cfg.hansen_version
    logger.info("Granulos Hansen sobre Colombia: %d -> %s", len(gs), gs)

    # Arma la lista de (url_origen, ruta_destino) para las dos capas de
    # cada granulo espacial.
    tareas: List[Tuple[str, Path]] = []
    for g in gs:
        for capa in ("treecover2000", "lossyear"):
            nombre = f"Hansen_{v}_{capa}_{g}.tif"
            tareas.append((f"{HANSEN_BASE}/{v}/{nombre}",
                           DIR_HANSEN / nombre))

    fallidos = []
    # ThreadPoolExecutor: lanza hasta cfg.hilos_descarga descargas a la
    # vez. as_completed() va entregando los resultados a medida que cada
    # descarga termina (no necesariamente en el orden en que se lanzaron).
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


# =====================================================================
# 2. DIST-ALERT
# =====================================================================
def periodos(cfg: Config) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    """Bordes de cada instantanea. El fin es exclusivo.

    Genera una lista de tramos [inicio, fin) consecutivos, segun
    cfg.cadencia_snapshot (p.ej. "MS" = un tramo por mes), entre
    fecha_inicio y fecha_fin. Cada tramo define la ventana de busqueda
    de UNA instantanea de DIST-ALERT por tile (ver buscar_periodo).
    """
    b = pd.date_range(cfg.fecha_inicio, cfg.fecha_fin,
                      freq=cfg.cadencia_snapshot)
    # zip(b[:-1], b[1:]) empareja cada fecha con la siguiente:
    # [ene, feb, mar] -> [(ene,feb), (feb,mar)]
    return list(zip(b[:-1], b[1:]))


def _login():
    """Autentica contra NASA Earthdata Login usando earthaccess.

    persist=True: si ya hay credenciales guardadas (en ~/.netrc, ver
    .dodsrc), las reutiliza sin preguntar. La primera vez que se corre
    en esta maquina, earthaccess pregunta usuario/clave por consola y
    los guarda para las siguientes corridas.
    """
    import earthaccess
    auth = earthaccess.login(persist=True)
    if not auth.authenticated:
        raise RuntimeError(
            "No se pudo autenticar en Earthdata.\n"
            "Cree la cuenta en https://urs.earthdata.nasa.gov y vuelva a "
            "correr; earthaccess pedira usuario y clave una sola vez.")
    return earthaccess


def _tile_de(nombre: str) -> str | None:
    """Extrae el codigo de tile MGRS (p.ej. '18NXG') de un nombre de archivo."""
    m = RE_TILE.search(nombre)
    return m.group(1) if m else None


def buscar_periodo(ea, cfg: Config, ini: pd.Timestamp,
                   fin: pd.Timestamp) -> Dict[str, dict]:
    """
    Una instantanea por tile en el periodo: la MAS RECIENTE disponible.

    Se elige la ultima y no la primera porque a mayor acumulacion de
    observaciones, mas alertas alcanzan el estado confirmado. La
    atribucion temporal no depende de cual se elija: viene de la banda
    VEG-DIST-DATE, no de la fecha de la instantanea.
    """
    # Consulta a CMR: "dame todos los granulos de esta coleccion, dentro
    # de este rectangulo geografico, sensados entre estas dos fechas".
    # 'fin' es exclusivo en el resto del pipeline, pero CMR espera un
    # rango inclusivo, por eso se resta un dia.
    res = ea.search_data(
        short_name=cfg.dist_short_name,
        version=cfg.dist_version,
        bounding_box=cfg.bbox,
        temporal=(ini.strftime("%Y-%m-%d"), (fin - pd.Timedelta(days=1)).strftime("%Y-%m-%d")),
    )

    por_tile: Dict[str, dict] = {}
    for g in res:
        # Cada granulo 'g' trae ~19 enlaces (uno por capa); nos quedamos
        # solo con los que terminan en las dos capas que interesan.
        enlaces = [u for u in g.data_links()
                   if u.endswith((f"{cfg.capa_estado}.tif",
                                  f"{cfg.capa_fecha}.tif"))]
        if len(enlaces) < 2:
            # Granulo incompleto (falta estado o fecha): se descarta.
            continue

        tile = _tile_de(Path(enlaces[0]).name)
        if tile is None:
            continue
        # Si cfg.tiles esta definido (modo piloto / un solo tile),
        # descarta cualquier granulo que no sea de ese tile.
        if cfg.tiles and tile not in cfg.tiles:
            continue

        # La fecha de sensado va en el nombre: ..._T18NXG_20230115T153259Z_...
        # El "sello" (timestamp) esta en la posicion [4] al partir por "_".
        nombre = Path(enlaces[0]).name
        try:
            sello = nombre.split("_")[4]
        except IndexError:
            continue

        # Se compara el sello como texto (formato AAAAMMDDTHHMMSSZ, que
        # ordena lexicograficamente igual que cronologicamente) para
        # quedarse con la instantanea MAS RECIENTE de cada tile dentro
        # de este periodo, tal como explica el docstring de la funcion.
        previo = por_tile.get(tile)
        if previo is None or sello > previo["sello"]:
            por_tile[tile] = {"sello": sello, "enlaces": sorted(enlaces)}

    return por_tile


def cmd_inventario(cfg: Config) -> int:
    """Cuenta cuanto habria que bajar, sin bajar nada.

    Recorre TODOS los periodos definidos por cfg (uno por mes, tipico)
    y para cada uno consulta CMR con buscar_periodo(). El resultado es
    un diccionario anidado {periodo: {tile: {sello, enlaces}}} que se
    guarda en disco (INVENTARIO) como el "plan" de descarga. cmd_dist()
    reutiliza este archivo despues para no repetir las consultas a CMR.
    """
    ea = _login()
    ps = periodos(cfg)
    logger.info("Periodos a inventariar: %d (%s a %s, cadencia %s)",
                len(ps), cfg.fecha_inicio, cfg.fecha_fin,
                cfg.cadencia_snapshot)

    plan: Dict[str, Dict[str, dict]] = {}
    tiles_vistos = set()
    for i, (ini, fin) in enumerate(ps, 1):
        pt = buscar_periodo(ea, cfg, ini, fin)
        clave = ini.strftime("%Y_%m_%d")   # clave de texto para el JSON, p.ej. "2023_01_01"
        plan[clave] = pt
        tiles_vistos |= set(pt)
        logger.info("[%d/%d] %s -> %d tiles", i, len(ps), clave, len(pt))

    # Cada tile-periodo implica 2 archivos (estado + fecha).
    archivos = sum(len(v) * 2 for v in plan.values())
    INVENTARIO.write_text(json.dumps(plan, indent=1))

    logger.info("=" * 62)
    logger.info("INVENTARIO")
    logger.info("  tiles MGRS distintos : %d", len(tiles_vistos))
    logger.info("  archivos a descargar : %d", archivos)
    logger.info("  estimado en disco    : %.0f - %.0f GB",
                archivos * 0.0015, archivos * 0.005)
    logger.info("  plan guardado en     : %s", INVENTARIO)
    logger.info("=" * 62)
    logger.info("Tiles: %s", sorted(tiles_vistos))
    return 0


def cmd_dist(cfg: Config) -> int:
    """Descarga real de los archivos DIST-ALERT (VEG-DIST-STATUS y VEG-DIST-DATE).

    A diferencia de cmd_inventario, esta funcion SI escribe archivos
    .tif en disco. Reutiliza el inventario ya calculado si existe
    (tipicamente ya filtrado a solo tiles de Colombia por
    filtrar_tiles.py); si no existe, lo construye sobre la marcha.
    """
    ea = _login()
    # Sesion HTTP ya autenticada contra Earthdata: hace falta usar esta
    # sesion (no 'requests' a secas) porque LP DAAC exige el token/cookies
    # de la autenticacion Earthdata Login para servir los archivos.
    sesion = ea.get_requests_https_session()

    if INVENTARIO.exists():
        logger.info("Reutilizando el inventario de %s", INVENTARIO)
        plan = json.loads(INVENTARIO.read_text())
    else:
        logger.info("Sin inventario previo; se construye al vuelo.")
        plan = {}
        for ini, fin in periodos(cfg):
            plan[ini.strftime("%Y_%m_%d")] = buscar_periodo(ea, cfg, ini, fin)
        INVENTARIO.write_text(json.dumps(plan, indent=1))

    def bajar(url: str, destino: Path) -> bool:
        """Descarga atomica de un archivo, usando la sesion autenticada.

        Mismo patron 'reanudable + escritura a .parcial' que
        descargar_url() de la seccion Hansen, pero usando la sesion
        HTTPS de earthaccess en vez de 'requests' sin autenticar.
        """
        if destino.exists() and destino.stat().st_size > 1024:
            return True   # ya descargado en una corrida anterior
        destino.parent.mkdir(parents=True, exist_ok=True)
        tmp = destino.with_suffix(".parcial")
        for intento in range(1, cfg.reintentos + 1):
            try:
                with sesion.get(url, stream=True, timeout=cfg.timeout_s) as r:
                    r.raise_for_status()
                    with tmp.open("wb") as fh:
                        for chunk in r.iter_content(1 << 20):
                            fh.write(chunk)
                tmp.replace(destino)
                return True
            except Exception as exc:
                logger.warning("    intento %d/%d: %s", intento,
                               cfg.reintentos, str(exc)[:120])
                tmp.unlink(missing_ok=True)
        return False

    # Aplana el inventario (periodo -> tile -> enlaces) en una lista
    # plana de tareas (url, ruta_destino). El nombre de archivo final es
    # "<periodo>__<capa>.tif" dentro de la carpeta del tile, p.ej.
    # datos/dist/18NXG/2023_01_01__VEG-DIST-STATUS.tif
    tareas: List[Tuple[str, Path]] = []
    for clave, por_tile in plan.items():
        for tile, info in por_tile.items():
            if cfg.tiles and tile not in cfg.tiles:
                continue
            for url in info["enlaces"]:
                capa = (cfg.capa_estado if cfg.capa_estado in url
                        else cfg.capa_fecha)
                tareas.append((url, DIR_DIST / tile / f"{clave}__{capa}.tif"))

    # Descarta de la lista lo que ya esta descargado (reanudacion).
    pendientes = [t for t in tareas
                  if not (t[1].exists() and t[1].stat().st_size > 1024)]
    logger.info("Archivos totales: %d | pendientes: %d",
                len(tareas), len(pendientes))

    fallidos = []
    with ThreadPoolExecutor(max_workers=cfg.hilos_descarga) as pool:
        futs = {pool.submit(bajar, u, d): d for u, d in pendientes}
        for i, fut in enumerate(as_completed(futs), 1):
            d = futs[fut]
            if not fut.result():
                fallidos.append(str(d))
            if i % 25 == 0 or i == len(pendientes):
                logger.info("  progreso: %d/%d", i, len(pendientes))

    total_gb = sum(f.stat().st_size for f in DIR_DIST.rglob("*.tif")) / 1e9
    logger.info("=" * 62)
    logger.info("DESCARGA DIST-ALERT")
    logger.info("  en disco : %.1f GB en %s", total_gb, DIR_DIST)
    logger.info("  fallidos : %d", len(fallidos))
    logger.info("=" * 62)
    if fallidos:
        (DIR_LOG / "fallidos_dist.txt").write_text("\n".join(fallidos))
        logger.warning("Lista en %s. Relance para reintentar.",
                       DIR_LOG / "fallidos_dist.txt")
    return 0


# =====================================================================
def main() -> int:
    """Punto de entrada de linea de comandos: python descargar_dist.py <subcomando>.

    Tres subcomandos posibles: 'hansen', 'inventario', 'dist'. El
    subcomando 'dist' acepta ademas '--tile T18NXG' para restringirse
    a un solo tile (usado por el modo "piloto" de main_local.py).
    """
    p = argparse.ArgumentParser(description="Descarga local de DIST-ALERT")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hansen")
    sub.add_parser("inventario")
    pd_ = sub.add_parser("dist")
    pd_.add_argument("--tile", default=None, help="Procesar un solo tile MGRS")

    a = p.parse_args()
    cfg = Config()
    if getattr(a, "tile", None):
        # Config es frozen (inmutable): dataclasses.replace crea una
        # copia nueva con 'tiles' sobreescrito, sin tocar la original.
        from dataclasses import replace
        cfg = replace(cfg, tiles=(a.tile,))

    if a.cmd == "hansen":
        return cmd_hansen(cfg)
    if a.cmd == "inventario":
        return cmd_inventario(cfg)
    if a.cmd == "dist":
        return cmd_dist(cfg)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
