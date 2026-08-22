"""
zonal_local.py
======================================================================
El motor de calculo. Reemplaza a reduceRegions() de Earth Engine.

    python fuente_dist_alert/zonal_local.py

Salida: datos/crudo/nacional.csv en formato ANCHO, la misma forma que
producia GEE, para que consolidar.py lo consuma sin cambios.

    cell_id | lon | lat | departamento | bosque_ha | d_2023_01 | ...

COMO FUNCIONA
-------------
Por cada tile MGRS, una sola vez y cacheado en disco:

  a) indice de celda: se transforman los centros de pixel del tile
     (UTM) a EPSG:3116 con pyproj y se calcula floor(coord/5000).
     Da un entero por pixel que dice a que celda pertenece.

  b) mascara de bosque: Hansen se reproyecta a la grilla del tile.
     bosque = (dosel_2000 >= umbral) Y (sin perdida antes de anio_mascara)

Despues se recorren las instantaneas EN ORDEN CRONOLOGICO manteniendo
una mascara acumulada 'ya_contado'. En cada instantanea:

  nuevo = estado en (6,8) Y no contado antes Y dentro de bosque

y esos pixeles se atribuyen al mes de su VEG-DIST-DATE, no al de la
instantanea. Asi un pixel detectado en marzo que solo se confirma en
mayo cuenta en marzo, y ninguno se cuenta dos veces.

Cada pixel son exactamente 0.09 ha (30 m x 30 m), asi que el area es
un conteo multiplicado por una constante: no hay pixelArea ni sesgo
de remuestreo.
======================================================================
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.warp import Resampling, reproject

# config_local.py vive en la raiz del proyecto, un nivel arriba de
# fuente_dist_alert/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config_local import (Config, DIR_CACHE, DIR_CRUDO, DIR_DIST,
                          DIR_GRILLA, DIR_HANSEN, logger)

GRILLA_CSV = DIR_GRILLA / "grilla_colombia_5km.csv"
SALIDA = DIR_CRUDO / "nacional.csv"


# =====================================================================
# CALENDARIO
# =====================================================================
def meses(cfg: Config) -> List[pd.Timestamp]:
    """Lista de los primeros dias de cada mes del panel (una fecha = un periodo)."""
    b = pd.date_range(cfg.fecha_inicio, cfg.fecha_fin, freq=cfg.frecuencia)
    return list(b[:-1])   # se descarta el ultimo borde: fecha_fin es exclusiva


def tabla_dia_a_mes(cfg: Config) -> np.ndarray:
    """
    Vector de consulta: dado el valor crudo de VEG-DIST-DATE (dias desde
    epoca_dist), devuelve el indice del mes del panel, o -1 si cae fuera
    de la ventana.

    Idea: en vez de convertir cada valor de fecha (uno por pixel, hay
    millones) con pandas.to_datetime uno por uno -- lentisimo -- se
    construye UNA VEZ un arreglo 'tabla' donde la posicion 'd' contiene
    directamente el indice de mes al que pertenece el dia 'd' (contado
    desde epoca_dist). Despues, decodificar un pixel es solo
    tabla[dias_del_pixel], un indexado de numpy vectorizado y muy
    rapido. Es literalmente una tabla de lookup (hash por posicion).
    """
    epoca = pd.Timestamp(cfg.epoca_dist)
    ms = meses(cfg)
    fin = pd.Timestamp(cfg.fecha_fin)

    # Tamano del vector: un valor por cada dia posible entre la epoca
    # y el fin de la ventana (+2 de margen por seguridad en los bordes).
    n_dias = int((fin - epoca).days) + 2
    tabla = np.full(n_dias, -1, dtype=np.int16)   # -1 = "fuera de la ventana del panel"

    # Por cada mes k, calcula en que rango de "dias desde epoca_dist"
    # cae ese mes, y rellena ese tramo del vector con el indice k.
    for k, m in enumerate(ms):
        d0 = int((m - epoca).days)
        d1 = int(((m + pd.tseries.frequencies.to_offset(cfg.frecuencia))
                  - epoca).days)
        tabla[max(d0, 0):min(d1, n_dias)] = k

    return tabla


# =====================================================================
# CACHE POR TILE: INDICE DE CELDA
# =====================================================================
def indice_celdas(cfg: Config, tile: str, ref: Path,
                  mapa_celda: Dict[Tuple[int, int], int]) -> np.ndarray:
    """
    Array int32 del tamano del tile. Cada valor es la posicion de la
    celda en la tabla de la grilla, o -1 si el pixel cae fuera.
    """
    # Si ya se calculo antes para este tile, se reutiliza desde disco
    # en vez de recalcular (reproyectar millones de coordenadas es caro).
    cache = DIR_CACHE / f"{tile}__idx.npy"
    if cache.exists():
        return np.load(cache)

    logger.info("  [%s] construyendo indice de celdas...", tile)
    with rasterio.open(ref) as src:
        alto, ancho = src.height, src.width
        tr, crs = src.transform, src.crs   # tr = transform afin (pixel -> coordenadas del CRS del tile)

    # Coordenadas del CENTRO de cada pixel, en el CRS nativo del tile
    # (UTM). tr.c/tr.f son el origen (esquina superior-izquierda);
    # tr.a es el tamano de pixel en x (positivo), tr.e en y (negativo,
    # porque las filas del raster avanzan hacia abajo mientras Y
    # geografico avanza hacia arriba). El "+0.5" desplaza del borde del
    # pixel a su centro.
    cols = np.arange(ancho) + 0.5
    filas = np.arange(alto) + 0.5
    xs = tr.c + tr.a * cols                     # a = tamano px en x
    ys = tr.f + tr.e * filas                    # e es negativo

    # Malla 2D de coordenadas (una por pixel del tile).
    X, Y = np.meshgrid(xs, ys)
    # Transforma TODAS las coordenadas del CRS del tile (UTM) al CRS
    # de la grilla (EPSG:3116) de una sola vez -- mucho mas rapido que
    # transformar pixel por pixel.
    t = Transformer.from_crs(crs, cfg.grid_crs, always_xy=True)
    X3, Y3 = t.transform(X.ravel(), Y.ravel())

    # El mismo calculo floor(coord / lado) que usa exportar_grilla.py
    # para asignar ix, iy a cada celda: aqui se aplica a cada PIXEL
    # para saber en que celda cae.
    lado = cfg.grid_scale_m
    ix = np.floor(np.asarray(X3) / lado).astype(np.int64)
    iy = np.floor(np.asarray(Y3) / lado).astype(np.int64)

    idx = np.full(ix.shape, -1, dtype=np.int32)
    # Resolver el diccionario mapa_celda (Python puro) para CADA pixel
    # seria lentisimo con millones de pixeles. Truco: np.unique con
    # return_inverse=True encuentra los pares (ix,iy) UNICOS (muchos
    # menos que el total de pixeles, porque celdas de 5 km cubren
    # muchos pixeles de 30 m) y ademas devuelve, para cada pixel
    # original, el indice a que par unico corresponde ('inverso'). Solo
    # hace falta resolver el diccionario sobre esos pares unicos, y
    # luego "repartir" el resultado a todos los pixeles con ese indice.
    pares, inverso = np.unique(np.stack([ix, iy], 1), axis=0,
                               return_inverse=True)
    resueltos = np.array([mapa_celda.get((int(a), int(b)), -1)
                          for a, b in pares], dtype=np.int32)
    idx = resueltos[inverso]

    idx = idx.reshape(alto, ancho)
    np.save(cache, idx)
    dentro = (idx >= 0).mean() * 100
    logger.info("  [%s] indice listo | %.1f%% de pixeles dentro de la grilla",
                tile, dentro)
    return idx


# =====================================================================
# CACHE POR TILE: MASCARA DE BOSQUE
# =====================================================================
def mascara_bosque(cfg: Config, tile: str, ref: Path) -> np.ndarray:
    """
    Mascara booleana de bosque, reproyectada de Hansen a la grilla del
    tile. Se cachea porque reproyectar es lo caro y no cambia por mes.

    El nombre de la cache incluye anio_mascara y umbral_dosel a
    proposito: este pipeline calcula la mascara con DOS valores de
    anio_mascara distintos segun la fuente de evento (2022 para el
    panel DIST-ALERT, 2019 para el panel GFW -- ver config_local.py,
    seccion 3). Si el nombre de archivo no incluyera el parametro, la
    segunda fuente en correr encontraria la cache de la primera y la
    reutilizaria en silencio, produciendo una mascara de bosque
    incorrecta para esa fuente sin ningun error visible.
    """
    # Cacheado en disco: reproyectar Hansen es costoso y el resultado
    # no cambia entre corridas con los mismos parametros, asi que se
    # hace una sola vez por tile y combinacion de parametros.
    cache = DIR_CACHE / f"{tile}__bosque_am{cfg.anio_mascara}_ud{cfg.umbral_dosel}.npy"
    if cache.exists():
        return np.load(cache)

    logger.info("  [%s] reproyectando mascara de bosque...", tile)
    with rasterio.open(ref) as src:
        # 'perfil' describe la cuadricula EXACTA del tile DIST-ALERT
        # (tamano, transform, CRS): Hansen se va a remuestrear para
        # calzar pixel a pixel con esta cuadricula.
        perfil = {"height": src.height, "width": src.width,
                  "transform": src.transform, "crs": src.crs}

    def traer(capa: str) -> np.ndarray:
        """Mosaica los granulos Hansen de esa capa sobre la grilla del tile.

        Un tile DIST-ALERT (100x100 km) puede caer sobre el borde entre
        dos o mas granulos Hansen (10x10 GRADOS). Por eso se reproyecta
        cada granulo Hansen relevante a la cuadricula del tile y se
        combinan con np.maximum: donde un granulo no cubre nada,
        reproject() deja el valor dst_nodata=0, asi que el maximo entre
        granulos siempre conserva el valor real donde exista.
        """
        salida = np.zeros((perfil["height"], perfil["width"]), dtype=np.uint8)
        gs = sorted(DIR_HANSEN.glob(f"Hansen_*_{capa}_*.tif"))
        if not gs:
            raise FileNotFoundError(
                f"No hay granulos de {capa} en {DIR_HANSEN}. "
                "Ejecute: python descargar_dist.py hansen")
        for g in gs:
            with rasterio.open(g) as hsrc:
                trozo = np.zeros_like(salida)
                # reproject: remuestrea el granulo Hansen (en su CRS y
                # resolucion originales) a la cuadricula exacta del
                # tile DIST-ALERT (dst_transform/dst_crs de 'perfil').
                # Resampling.nearest: para datos categoricos/enteros
                # (dosel en %, ano de perdida) no tiene sentido
                # interpolar (promediar) valores -- se toma el pixel
                # mas cercano tal cual.
                reproject(
                    source=rasterio.band(hsrc, 1),
                    destination=trozo,
                    dst_transform=perfil["transform"],
                    dst_crs=perfil["crs"],
                    resampling=Resampling.nearest,
                    src_nodata=None, dst_nodata=0,
                )
            salida = np.maximum(salida, trozo)
        return salida

    dosel = traer("treecover2000")     # % de cobertura de dosel en el ano 2000
    perdida = traer("lossyear")        # ano de perdida (1-24 = 2001-2024), 0 = sin perdida

    # Definicion de "bosque disponible al inicio del analisis":
    #   1) tenia al menos umbral_dosel% de cobertura en el ano 2000, Y
    #   2) si perdio cobertura, la perdio EN o DESPUES de anio_mascara
    #      (perdidas mas tempranas ya no cuentan como bosque disponible).
    bosque = (dosel >= cfg.umbral_dosel)
    perdida_previa = (perdida > 0) & (perdida <= (cfg.anio_mascara - 2000))
    bosque &= ~perdida_previa

    np.save(cache, bosque)
    logger.info("  [%s] bosque: %.0f ha", tile,
                bosque.sum() * cfg.area_px_ha)
    return bosque


# =====================================================================
# PROCESAMIENTO DE UN TILE
# =====================================================================
def procesar_tile(cfg: Config, tile: str, n_celdas: int,
                  mapa_celda: Dict[Tuple[int, int], int],
                  d2m: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Devuelve (bosque_ha_por_celda, area_def_ha_por_celda_y_mes).

    La segunda tiene forma (n_celdas, n_meses).
    """
    dir_tile = DIR_DIST / tile
    # Todas las instantaneas VEG-DIST-STATUS descargadas para este
    # tile, una por periodo, ordenadas por nombre de archivo (que
    # empieza con la fecha del periodo: "2023_01_01__...", asi que el
    # orden alfabetico YA es orden cronologico).
    estados = sorted(dir_tile.glob(f"*__{cfg.capa_estado}.tif"))
    if not estados:
        logger.warning("  [%s] sin instantaneas; se salta.", tile)
        return np.zeros(n_celdas), np.zeros((n_celdas, len(meses(cfg))))

    # idx: a que celda de la grilla pertenece cada pixel (o -1 si esta
    # fuera). bosque: si ese pixel es bosque segun Hansen. Ambos se
    # calculan sobre la primera instantanea porque todas comparten la
    # misma cuadricula (mismo tile MGRS = misma resolucion y extension).
    idx = indice_celdas(cfg, tile, estados[0], mapa_celda)
    bosque = mascara_bosque(cfg, tile, estados[0])

    n_meses = len(meses(cfg))
    # .ravel(): aplana la matriz 2D (alto x ancho) a un vector 1D, para
    # poder usar bincount/indexado vectorizado sin importar la forma
    # original del raster.
    plano = idx.ravel()
    # Un pixel es "valido" para el analisis si cae dentro de alguna
    # celda de la grilla (idx >= 0) Y es bosque segun Hansen.
    valido_base = (plano >= 0) & bosque.ravel()

    # Bosque por celda (denominador de la exposicion): cuenta cuantos
    # pixeles validos caen en cada celda (bincount agrupa por el valor
    # entero de 'plano', que es justamente el indice de celda) y
    # convierte el conteo de pixeles a hectareas.
    bosque_ha = np.bincount(plano[valido_base],
                            minlength=n_celdas).astype(np.float64)
    bosque_ha = bosque_ha[:n_celdas] * cfg.area_px_ha

    # acum: matriz (celdas x meses) donde se va acumulando el conteo de
    # pixeles deforestados de cada celda en cada mes.
    acum = np.zeros((n_celdas, n_meses), dtype=np.float64)
    # ya_contado: mascara booleana, un valor por pixel del tile, que
    # marca si ese pixel YA fue atribuido a algun mes en una instantanea
    # anterior. Evita contar dos veces un pixel que sigue "confirmado"
    # (estado 6 u 8) en instantaneas sucesivas.
    ya_contado = np.zeros(plano.shape, dtype=bool)
    # Los codigos de VEG-DIST-STATUS que cuentan como evento: (6, 8).
    objetivo = np.asarray(cfg.estados_evento, dtype=np.uint8)

    # Recorre las instantaneas EN ORDEN CRONOLOGICO (clave para que
    # 'ya_contado' funcione correctamente: un pixel solo puede pasar de
    # "no contado" a "contado", nunca al reves).
    for f_estado in estados:
        # El archivo de fecha (VEG-DIST-DATE) tiene el mismo nombre que
        # el de estado, solo cambia el sufijo de capa.
        f_fecha = Path(str(f_estado).replace(cfg.capa_estado, cfg.capa_fecha))
        if not f_fecha.exists():
            logger.warning("  [%s] falta la fecha de %s", tile, f_estado.name)
            continue

        with rasterio.open(f_estado) as s:
            est = s.read(1).ravel()   # codigo de estado por pixel, esta instantanea
        with rasterio.open(f_fecha) as s:
            fec = s.read(1).ravel()   # dias desde epoca_dist, por pixel, esta instantanea

        # Pixeles que en ESTA instantanea:
        #  - tienen un estado de evento (confirmado, 6 u 8),
        #  - son bosque y caen dentro de la grilla (valido_base),
        #  - NO habian sido contados en una instantanea anterior.
        nuevo = np.isin(est, objetivo) & valido_base & ~ya_contado
        if not nuevo.any():
            continue   # nada nuevo en esta instantanea, siguiente

        # Decodifica la fecha real del evento (dias -> indice de mes)
        # SOLO para los pixeles nuevos, usando la tabla de lookup
        # precalculada d2m (ver tabla_dia_a_mes). np.clip evita que un
        # valor de fecha corrupto o fuera de rango cause un error de
        # indice fuera de limites.
        dias = fec[nuevo].astype(np.int64)
        dias = np.clip(dias, 0, len(d2m) - 1)
        mes = d2m[dias]   # -1 si la fecha decodificada cae fuera de la ventana del panel

        celdas = plano[nuevo]
        bueno = mes >= 0   # descarta eventos cuya fecha cae fuera de la ventana del panel
        if bueno.any():
            # Convierte (celda, mes) a un unico indice lineal
            # (celda * n_meses + mes) para poder usar bincount, que
            # solo trabaja con un vector de enteros. Es el equivalente
            # vectorizado de "por cada pixel nuevo, sumar 1 a
            # acum[celda, mes]", pero sin un bucle Python pixel a pixel.
            clave = celdas[bueno].astype(np.int64) * n_meses + mes[bueno]
            conteo = np.bincount(clave, minlength=n_celdas * n_meses)
            acum += conteo[:n_celdas * n_meses].reshape(n_celdas, n_meses)

        # Marca estos pixeles como ya contados para que instantaneas
        # futuras (donde seguiran apareciendo en estado 6/8) no los
        # vuelvan a sumar.
        ya_contado |= nuevo

    acum *= cfg.area_px_ha   # de conteo de pixeles a hectareas
    logger.info("  [%s] %d instantaneas | %.0f ha atribuidas | bosque %.0f ha",
                tile, len(estados), acum.sum(), bosque_ha.sum())
    return bosque_ha, acum


# =====================================================================
# ORQUESTADOR
# =====================================================================
def main() -> int:
    p = argparse.ArgumentParser(description="Calculo zonal local")
    p.add_argument("--tile", default=None, help="Procesar un solo tile")
    a = p.parse_args()

    cfg = Config()

    if not GRILLA_CSV.exists():
        logger.error("Falta %s. Ejecute: python exportar_grilla.py", GRILLA_CSV)
        return 1

    grilla = pd.read_csv(GRILLA_CSV).reset_index(drop=True)
    n_celdas = len(grilla)
    # Diccionario (ix, iy) -> posicion de fila en la tabla 'grilla'.
    # Es el mapa que usa indice_celdas() para resolver, por cada pixel,
    # a que fila del CSV de la grilla corresponde.
    mapa_celda = {(int(r.ix), int(r.iy)): i
                  for i, r in enumerate(grilla.itertuples())}
    logger.info("Grilla: %d celdas", n_celdas)

    ms = meses(cfg)
    d2m = tabla_dia_a_mes(cfg)
    logger.info("Periodos del panel: %d (%s a %s)",
                len(ms), ms[0].date(), ms[-1].date())

    # Si se paso --tile, procesa solo ese; si no, todos los tiles que
    # tengan una carpeta con datos descargados en datos/dist/.
    tiles = ([a.tile] if a.tile
             else sorted(d.name for d in DIR_DIST.iterdir() if d.is_dir()))
    if not tiles:
        logger.error("No hay tiles en %s. Ejecute: python descargar_dist.py dist",
                     DIR_DIST)
        return 1
    logger.info("Tiles a procesar: %d", len(tiles))

    bosque_total = np.zeros(n_celdas)
    def_total = np.zeros((n_celdas, len(ms)))

    for i, tile in enumerate(tiles, 1):
        logger.info("[%d/%d] %s", i, len(tiles), tile)
        b, d = procesar_tile(cfg, tile, n_celdas, mapa_celda, d2m)
        # Los tiles MGRS se traslapan: para el bosque se toma el maximo,
        # no la suma, o se duplicaria el denominador en los bordes.
        bosque_total = np.maximum(bosque_total, b)
        def_total = np.maximum(def_total, d)

    # Arma la tabla ANCHA final: metadatos de la celda + bosque_ha +
    # una columna por cada mes del panel (d_2023_01, d_2023_02, ...).
    salida = grilla[["cell_id", "lon", "lat", "departamento"]].copy()
    salida["bosque_ha"] = bosque_total
    for k, m in enumerate(ms):
        salida[f"d_{m.strftime('%Y_%m')}"] = def_total[:, k]

    # Descarta celdas sin nada de bosque: no aportan al analisis y
    # consolidar.py las filtraria de todas formas por bosque_minimo_ha.
    antes = len(salida)
    salida = salida[salida["bosque_ha"] > 0].copy()
    salida.to_csv(SALIDA, index=False)

    logger.info("=" * 62)
    logger.info("CALCULO ZONAL COMPLETO")
    logger.info("  celdas con bosque : %d de %d", len(salida), antes)
    logger.info("  bosque total      : %.0f ha", salida["bosque_ha"].sum())
    logger.info("  deforestacion     : %.0f ha", def_total.sum())
    logger.info("  archivo           : %s", SALIDA)
    logger.info("=" * 62)
    logger.info("Siguiente: python main_local.py consolidar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
