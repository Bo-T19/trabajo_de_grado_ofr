"""
descargar_gfw.py
======================================================================
Construye el panel de deforestacion 2020-presente usando UNICAMENTE el
producto integrado de Global Forest Watch (gfw_integrated_dist_alerts:
DIST-ALERT + GLAD-L + GLAD-S2 + RADD en una sola escala de confianza),
sin mezclarlo con la fuente DIST-ALERT pura de fuente_dist_alert/.

    python fuente_gfw/descargar_gfw.py

Salida: datos/crudo/nacional_gfw.csv -- un archivo COMPLETAMENTE
INDEPENDIENTE de datos/crudo/nacional.csv (el de fuente_dist_alert/).
Los dos NUNCA se fusionan ni se concatenan: consolidar.py pide
explicitamente cual de los dos usar (--fuente dist_alert | gfw) y lee
solo ese archivo. Ver METODOLOGIA.md, decision 15 revisada, para el
porque de mantener dos paneles separados en vez de uno combinado.

CUANDO USAR ESTE SCRIPT EN VEZ DE fuente_dist_alert/
------------------------------------------------------
- Si el analisis necesita la ventana completa desde 2020-01: use esta
  fuente (GFW) para TODO el panel, de 2020 al mes mas reciente.
- Si solo hace falta 2023-01 en adelante: use fuente_dist_alert/ (el
  producto oficial de la NASA, con documentacion metodologica mas
  completa -- ver METODOLOGIA.md seccion 2.4).
No se recomienda usar ambas fuentes para construir un solo panel
combinado: mezclarlas introduce un salto metodologico no controlado en
el limite entre las dos (distintas definiciones de "confianza",
distinta sensibilidad por combinar radar+optico vs. optico solo).

COMO FUNCIONA
-------------
1. BOSQUE BASE (bosque_ha por celda): se reutilizan, tal cual,
   indice_celdas() y mascara_bosque() de fuente_dist_alert/zonal_local.py
   -- el mismo codigo ya probado que usa el panel DIST-ALERT -- pero
   con anio_mascara_gfw (2019) en vez de anio_mascara (2022), porque
   este panel arranca en 2020-01, no en 2023-01 (ver METODOLOGIA.md,
   decision 5 revisada). Importante: esto NO es mezclar fuentes de
   EVENTO. Hansen (el insumo de la mascara de bosque) es una fuente
   estatica compartida por diseño, independiente de cual fuente de
   evento se use despues (ver METODOLOGIA.md seccion 2.1). Lo unico
   que se reutiliza de fuente_dist_alert/ es la CUADRICULA (transform,
   CRS, forma) de los archivos ya descargados en datos/dist/, como
   andamio geometrico para reproyectar Hansen -- nunca su contenido
   VEG-DIST-STATUS/VEG-DIST-DATE. mascara_bosque() ya cachea por
   separado segun anio_mascara (ver su docstring), asi que esta
   corrida no pisa la cache del panel DIST-ALERT.

2. EVENTO: se consulta por lotes de ~400 celdas la API SQL de GFW
   (data-api.globalforestwatch.org), endpoint asincrono /query/batch,
   con esta consulta corriendo una vez por celda:

       SELECT confidence, date, SUM(area__ha) AS ha
       FROM data
       WHERE date >= fecha_inicio_gfw AND date < fecha_fin
         AND (confidence = 'high' OR confidence = 'highest')
       GROUP BY confidence, date

   (el operador SQL "IN" no esta soportado por este endpoint -- se
   confirmo empiricamente que devuelve "Unsupported filter operator:
   in" -- por eso el filtro de confianza usa OR encadenados). El campo
   `area__ha` lo calcula la propia API: este producto usa una
   cuadricula en grados (EPSG:4326), y el area real de un pixel de
   tamano angular fijo varia con la latitud -- sumar `area__ha`
   evita asumir un tamano de pixel fijo para todo el pais.

REANUDABLE: cada lote se cachea en datos/gfw/lote_XXXX.json apenas se
descarga.

REQUISITOS
----------
    pip install geopandas requests
    Una API key de GFW en datos/logs/gfw_api_key.txt (ver
    fuente_gfw/configurar_gfw.py) o en la variable de entorno GFW_API_KEY.
    Al menos un archivo de referencia por tile en datos/dist/<tile>/
    (basta uno solo, no hace falta el archivo historico completo --
    ver GUIA_CODIGO.md si se quiere evitar descargar DIST-ALERT del
    todo).
======================================================================
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely.geometry as sg

# config_local.py vive en la raiz del proyecto, un nivel arriba de
# fuente_gfw/; las funciones de mascara de bosque viven en
# fuente_dist_alert/, hermana de esta carpeta.
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "fuente_dist_alert"))
from config_local import Config, DIR_CRUDO, DIR_DIST, DIR_GFW, DIR_GRILLA, DIR_LOG, logger
from zonal_local import indice_celdas, mascara_bosque   # reutilizados tal cual

GRILLA_CSV = DIR_GRILLA / "grilla_colombia_5km.csv"
SALIDA = DIR_CRUDO / "nacional_gfw.csv"
BASE = "https://data-api.globalforestwatch.org"
ARCHIVO_KEY = DIR_LOG / "gfw_api_key.txt"


# =====================================================================
# CREDENCIALES
# =====================================================================
def _api_key() -> str:
    key = os.environ.get("GFW_API_KEY")
    if key:
        return key.strip()
    if ARCHIVO_KEY.exists():
        return ARCHIVO_KEY.read_text().strip()
    raise SystemExit(
        "Falta la API key de GFW. Corra primero:\n"
        "  python fuente_gfw/configurar_gfw.py signup --nombre ... --email ...\n"
        "  python fuente_gfw/configurar_gfw.py apikey --email ... --password ...\n"
        "O defina la variable de entorno GFW_API_KEY.")


# =====================================================================
# BOSQUE BASE -- reutiliza el mismo codigo que fuente_dist_alert/,
# con anio_mascara_gfw en vez de anio_mascara.
# =====================================================================
def bosque_ha_por_celda(cfg: Config, grilla: pd.DataFrame,
                        mapa_celda: Dict[Tuple[int, int], int]) -> np.ndarray:
    """
    Devuelve un array de hectareas de bosque por celda (misma logica y
    mismos cachés que procesar_tile() en zonal_local.py, pero solo la
    parte del bosque -- este script no necesita el resto porque el
    evento lo trae GFW, no DIST-ALERT).
    """
    cfg_gfw = replace(cfg, anio_mascara=cfg.anio_mascara_gfw)
    n_celdas = len(grilla)
    bosque_total = np.zeros(n_celdas)

    tiles = sorted(d.name for d in DIR_DIST.iterdir() if d.is_dir()) if DIR_DIST.exists() else []
    if not tiles:
        raise SystemExit(
            f"No hay tiles de referencia en {DIR_DIST}. Se necesita al menos\n"
            "un archivo por tile (no hace falta el historico completo) para\n"
            "tener la cuadricula sobre la que reproyectar Hansen. Corra\n"
            "primero, aunque sea para un solo tile:\n"
            "  python fuente_dist_alert/descargar_dist.py dist --tile T18NXG")

    logger.info("Calculando bosque base (anio_mascara=%d) sobre %d tiles...",
               cfg_gfw.anio_mascara, len(tiles))
    for i, tile in enumerate(tiles, 1):
        dir_tile = DIR_DIST / tile
        referencias = sorted(dir_tile.glob(f"*__{cfg.capa_estado}.tif"))
        if not referencias:
            logger.warning("  [%d/%d] %s: sin archivo de referencia, se salta", i, len(tiles), tile)
            continue
        ref = referencias[0]

        idx = indice_celdas(cfg_gfw, tile, ref, mapa_celda)
        bosque = mascara_bosque(cfg_gfw, tile, ref)

        plano = idx.ravel()
        valido = (plano >= 0) & bosque.ravel()
        conteo = np.bincount(plano[valido], minlength=n_celdas).astype(np.float64)
        ha_tile = conteo[:n_celdas] * cfg.area_px_ha

        # Los tiles MGRS se traslapan: maximo, no suma (misma razon
        # que en zonal_local.py -- evitar duplicar bosque en los bordes).
        bosque_total = np.maximum(bosque_total, ha_tile)
        if i % 20 == 0 or i == len(tiles):
            logger.info("  [%d/%d] bosque acumulado: %.0f ha", i, len(tiles), bosque_total.sum())

    return bosque_total


# =====================================================================
# CALENDARIO Y SQL
# =====================================================================
def meses_gfw(cfg: Config) -> List[pd.Timestamp]:
    b = pd.date_range(cfg.fecha_inicio_gfw, cfg.fecha_fin, freq="MS")
    return list(b[:-1])


def sql_lote(cfg: Config) -> str:
    """
    La API de este endpoint NO soporta el operador SQL "IN" (se
    confirmo empiricamente: devuelve "Unsupported filter operator: in"),
    asi que el filtro de confianza se arma con OR encadenados.
    """
    condiciones = " OR ".join(
        f"gfw_integrated_dist_alerts__confidence = '{c}'"
        for c in cfg.gfw_confianza_minima)
    fin_excl = pd.Timestamp(cfg.fecha_fin).strftime("%Y-%m-%d")
    return f"""
SELECT gfw_integrated_dist_alerts__confidence,
       gfw_integrated_dist_alerts__date,
       SUM(area__ha) AS ha
FROM data
WHERE gfw_integrated_dist_alerts__date >= '{cfg.fecha_inicio_gfw}'
  AND gfw_integrated_dist_alerts__date < '{fin_excl}'
  AND ({condiciones})
GROUP BY gfw_integrated_dist_alerts__confidence, gfw_integrated_dist_alerts__date
"""


# =====================================================================
# GEOMETRIA: celdas de la grilla como poligonos WGS84
# =====================================================================
def celdas_como_poligonos(cfg: Config, grilla: pd.DataFrame) -> gpd.GeoDataFrame:
    lado = cfg.grid_scale_m
    cajas = [sg.box(r.ix * lado, r.iy * lado, (r.ix + 1) * lado, (r.iy + 1) * lado)
             for r in grilla.itertuples()]
    gdf = gpd.GeoDataFrame({"cell_id": grilla["cell_id"].values},
                           geometry=cajas, crs=cfg.grid_crs)
    return gdf.to_crs("EPSG:4326")


# =====================================================================
# UN LOTE: enviar, esperar, descargar
# =====================================================================
def procesar_lote(cfg: Config, key: str, indice: int,
                  lote: gpd.GeoDataFrame) -> List[dict]:
    cache = DIR_GFW / f"lote_{indice:04d}.json"
    if cache.exists():
        return json.loads(cache.read_text())

    fc = json.loads(lote.to_json())
    for feat in fc["features"]:
        feat.pop("id", None)   # la API rechaza el campo "id" a nivel de feature

    body = {"feature_collection": fc, "id_field": "cell_id", "sql": sql_lote(cfg)}
    headers = {"x-api-key": key}

    for intento in range(1, cfg.reintentos + 1):
        try:
            r = requests.post(
                f"{BASE}/dataset/{cfg.gfw_dataset}/{cfg.gfw_version}/query/batch",
                json=body, headers=headers, timeout=60)
            r.raise_for_status()
            job_id = r.json()["data"]["job_id"]

            for _ in range(180):   # hasta 15 min por lote
                time.sleep(5)
                jr = requests.get(f"{BASE}/job/{job_id}", headers=headers, timeout=30)
                jr.raise_for_status()
                jd = jr.json()["data"]
                estado = jd.get("status")
                if estado == "success":
                    resultado = requests.get(jd["download_link"], timeout=120).json()
                    cache.write_text(json.dumps(resultado))
                    return resultado
                if estado in ("failed", "error", "partial_success"):
                    logger.warning("  lote %d: job %s -> %s", indice, estado, str(jd)[:200])
                    resultado = []
                    if jd.get("download_link"):
                        resultado = requests.get(jd["download_link"], timeout=120).json()
                    cache.write_text(json.dumps(resultado))
                    return resultado
            raise TimeoutError("el job no termino en 15 minutos")
        except Exception as exc:
            logger.warning("  lote %d intento %d/%d fallo: %s",
                           indice, intento, cfg.reintentos, str(exc)[:150])
    logger.error("  lote %d: se agotaron los reintentos, se deja vacio", indice)
    return []


# =====================================================================
# AGREGACION: de filas diarias por celda a columnas d_AAAA_MM
# =====================================================================
def agregar_a_mensual(resultados_por_lote: List[List[dict]],
                      meses: List[pd.Timestamp]) -> pd.DataFrame:
    columnas = {f"d_{m.strftime('%Y_%m')}": {} for m in meses}
    todas_las_celdas = set()

    for lote in resultados_por_lote:
        for item in lote:
            cell_id = item.get("cell_id")
            if cell_id is None:
                continue
            todas_las_celdas.add(cell_id)
            for fila in item.get("result", []):
                fecha = fila.get("gfw_integrated_dist_alerts__date")
                ha = fila.get("ha") or 0.0
                if not fecha:
                    continue
                clave = f"d_{fecha[:7].replace('-', '_')}"
                if clave not in columnas:
                    continue
                columnas[clave][cell_id] = columnas[clave].get(cell_id, 0.0) + ha

    out = pd.DataFrame({"cell_id": sorted(todas_las_celdas)})
    for col, valores in columnas.items():
        out[col] = out["cell_id"].map(valores).fillna(0.0)
    return out


# =====================================================================
def main() -> int:
    p = argparse.ArgumentParser(description="Panel de deforestacion 2020-presente, solo GFW")
    p.add_argument("--limite-celdas", type=int, default=None,
                   help="Procesar solo las primeras N celdas (para pruebas)")
    a = p.parse_args()

    cfg = Config()
    key = _api_key()

    if not GRILLA_CSV.exists():
        logger.error("Falta %s. Ejecute: python main_local.py grilla", GRILLA_CSV)
        return 1

    grilla = pd.read_csv(GRILLA_CSV).reset_index(drop=True)
    if a.limite_celdas:
        grilla = grilla.head(a.limite_celdas).reset_index(drop=True)
    n_celdas = len(grilla)
    mapa_celda = {(int(r.ix), int(r.iy)): i for i, r in enumerate(grilla.itertuples())}
    logger.info("Celdas a consultar: %d", n_celdas)

    meses = meses_gfw(cfg)
    logger.info("Periodos GFW: %d (%s a %s)", len(meses), meses[0].date(), meses[-1].date())

    # --- 1. Bosque base (propio de este panel, anio_mascara_gfw) ---
    bosque_total = bosque_ha_por_celda(cfg, grilla, mapa_celda)

    # --- 2. Evento (API de GFW, por lotes) ---
    poligonos = celdas_como_poligonos(cfg, grilla)
    lotes = [poligonos.iloc[i:i + cfg.gfw_celdas_por_lote]
             for i in range(0, len(poligonos), cfg.gfw_celdas_por_lote)]
    logger.info("Lotes: %d (de hasta %d celdas c/u)", len(lotes), cfg.gfw_celdas_por_lote)

    resultados: List[List[dict]] = [None] * len(lotes)
    with ThreadPoolExecutor(max_workers=cfg.gfw_lotes_en_paralelo) as pool:
        futs = {pool.submit(procesar_lote, cfg, key, i, lote): i
                for i, lote in enumerate(lotes)}
        for j, fut in enumerate(as_completed(futs), 1):
            i = futs[fut]
            resultados[i] = fut.result()
            logger.info("  progreso: %d/%d lotes (lote %d: %d celdas con resultado)",
                        j, len(lotes), i, len(resultados[i]))

    mensual = agregar_a_mensual([r for r in resultados if r], meses)
    logger.info("Celdas con al menos una alerta GFW: %d", len(mensual))

    # --- 3. Ensamblar el archivo ancho, igual forma que nacional.csv ---
    salida = grilla[["cell_id", "lon", "lat", "departamento"]].copy()
    salida["bosque_ha"] = bosque_total
    salida = salida.merge(mensual, on="cell_id", how="left")
    cols_periodo = [f"d_{m.strftime('%Y_%m')}" for m in meses]
    salida[cols_periodo] = salida[cols_periodo].fillna(0.0)

    antes = len(salida)
    salida = salida[salida["bosque_ha"] > 0].copy()
    salida.to_csv(SALIDA, index=False)

    logger.info("=" * 62)
    logger.info("PANEL GFW (2020-presente) COMPLETO")
    logger.info("  celdas con bosque : %d de %d", len(salida), antes)
    logger.info("  bosque total      : %.0f ha", salida["bosque_ha"].sum())
    logger.info("  deforestacion     : %.0f ha", salida[cols_periodo].sum().sum())
    logger.info("  archivo           : %s", SALIDA)
    logger.info("=" * 62)
    logger.info("Siguiente: python main_local.py consolidar --fuente gfw")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
