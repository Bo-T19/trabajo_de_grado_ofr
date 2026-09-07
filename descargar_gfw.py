"""
descargar_gfw.py
======================================================================
Construye el panel de deforestacion de Colombia usando el producto
integrado de alertas de Global Forest Watch. Cual producto exactamente
lo decide config_local.py (gfw_dataset); por defecto
"gfw_integrated_alerts", que integra GLAD-L, GLAD-S2 y RADD.

    python descargar_gfw.py

Salida: datos/crudo/nacional.csv, formato ANCHO:

    cell_id | lon | lat | departamento | bosque_ha | d_2020_01 | ...

COMO FUNCIONA
-------------
1. BOSQUE BASE (bosque_ha por celda): se calcula con
   calcular_bosque.bosque_ha_por_celda(), que reproyecta Hansen Global
   Forest Change directamente sobre la grilla nacional de 5 km (sin
   depender de ninguna cuadricula externa) y aplica el umbral de dosel
   y el corte temporal de anio_mascara -- ver ese modulo para el detalle.

2. EVENTO: se consulta por lotes de ~400 celdas la API SQL de GFW
   (data-api.globalforestwatch.org), endpoint asincrono /query/batch,
   con esta consulta corriendo una vez por celda:

       SELECT confidence, date, SUM(area__ha) AS ha
       FROM data
       WHERE date >= fecha_inicio AND date < fecha_fin
         AND (confidence = 'high' OR confidence = 'highest')
       GROUP BY confidence, date

   (el operador SQL "IN" no esta soportado por este endpoint -- se
   confirmo empiricamente que devuelve "Unsupported filter operator:
   in" -- por eso el filtro de confianza usa OR encadenados). El campo
   `area__ha` lo calcula la propia API: este producto usa una
   cuadricula en grados (EPSG:4326), y el area real de un pixel de
   tamano angular fijo varia con la latitud -- sumar `area__ha`
   evita asumir un tamano de pixel fijo para todo el pais.

REANUDABLE: cada lote se cachea en datos/gfw/lote_<dataset>_XXXX.json
apenas se descarga. El nombre incluye el dataset para que cambiar de
fuente en config_local.py nunca reutilice en silencio resultados de la
fuente anterior.

REQUISITOS
----------
    pip install geopandas requests
    Una API key de GFW en datos/logs/gfw_api_key.txt (ver
    configurar_gfw.py) o en la variable de entorno GFW_API_KEY.
    Los granulos de Hansen ya descargados (python main_local.py hansen).
======================================================================
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely.geometry as sg

from calcular_bosque import bosque_ha_por_celda
from config_local import Config, DIR_CRUDO, DIR_GFW, DIR_GRILLA, DIR_LOG, logger

GRILLA_CSV = DIR_GRILLA / "grilla_colombia_5km.csv"
SALIDA = DIR_CRUDO / "nacional.csv"
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
        "  python configurar_gfw.py signup --nombre ... --email ...\n"
        "  python configurar_gfw.py apikey --email ... --password ...\n"
        "O defina la variable de entorno GFW_API_KEY.")


# =====================================================================
# CALENDARIO Y SQL
# =====================================================================
def meses(cfg: Config) -> List[pd.Timestamp]:
    b = pd.date_range(cfg.fecha_inicio, cfg.fecha_fin, freq="MS")
    return list(b[:-1])


def sql_lote(cfg: Config) -> str:
    """
    La API de este endpoint NO soporta el operador SQL "IN" (se
    confirmo empiricamente: devuelve "Unsupported filter operator: in"),
    asi que el filtro de confianza se arma con OR encadenados.

    El prefijo de los campos (confidence/date) es igual al nombre del
    dataset (cfg.gfw_dataset) en todos los datasets de alertas de GFW
    verificados hasta ahora (gfw_integrated_dist_alerts,
    umd_glad_landsat_alerts, umd_glad_sentinel2_alerts) -- por eso se
    arma dinamicamente en vez de escribirlo a mano, para que cambiar de
    fuente sea solo cambiar cfg.gfw_dataset, sin tocar este archivo.
    """
    prefijo = cfg.gfw_dataset
    condiciones = " OR ".join(
        f"{prefijo}__confidence = '{c}'"
        for c in cfg.gfw_confianza_minima)
    fin_excl = pd.Timestamp(cfg.fecha_fin).strftime("%Y-%m-%d")
    return f"""
SELECT {prefijo}__confidence,
       {prefijo}__date,
       SUM(area__ha) AS ha
FROM data
WHERE {prefijo}__date >= '{cfg.fecha_inicio}'
  AND {prefijo}__date < '{fin_excl}'
  AND ({condiciones})
GROUP BY {prefijo}__confidence, {prefijo}__date
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
    # El nombre de la cache incluye cfg.gfw_dataset a proposito: si no
    # lo incluyera, cambiar de fuente (p.ej. del producto integrado a
    # GLAD-L solo) reutilizaria en silencio los resultados del dataset
    # anterior, sin ningun error visible -- mismo riesgo que ya se
    # corrigio antes para la cache de bosque en calcular_bosque.py.
    cache = DIR_GFW / f"lote_{cfg.gfw_dataset}_{indice:04d}.json"
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
def agregar_a_mensual(cfg: Config, resultados_por_lote: List[List[dict]],
                      ms: List[pd.Timestamp]) -> pd.DataFrame:
    campo_fecha = f"{cfg.gfw_dataset}__date"
    columnas = {f"d_{m.strftime('%Y_%m')}": {} for m in ms}
    todas_las_celdas = set()

    for lote in resultados_por_lote:
        for item in lote:
            cell_id = item.get("cell_id")
            if cell_id is None:
                continue
            todas_las_celdas.add(cell_id)
            for fila in item.get("result", []):
                fecha = fila.get(campo_fecha)
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
    p = argparse.ArgumentParser(description="Panel de deforestacion de Colombia (GFW)")
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

    ms = meses(cfg)
    logger.info("Periodos: %d (%s a %s)", len(ms), ms[0].date(), ms[-1].date())

    # --- 1. Bosque base ---
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

    mensual = agregar_a_mensual(cfg, [r for r in resultados if r], ms)
    logger.info("Celdas con al menos una alerta: %d", len(mensual))

    # --- 3. Ensamblar el archivo ancho ---
    salida = grilla[["cell_id", "lon", "lat", "departamento"]].copy()
    salida["bosque_ha"] = bosque_total
    salida = salida.merge(mensual, on="cell_id", how="left")
    cols_periodo = [f"d_{m.strftime('%Y_%m')}" for m in ms]
    salida[cols_periodo] = salida[cols_periodo].fillna(0.0)

    antes = len(salida)
    salida = salida[salida["bosque_ha"] > 0].copy()
    salida.to_csv(SALIDA, index=False)

    logger.info("=" * 62)
    logger.info("PANEL COMPLETO")
    logger.info("  celdas con bosque : %d de %d", len(salida), antes)
    logger.info("  bosque total      : %.0f ha", salida["bosque_ha"].sum())
    logger.info("  deforestacion     : %.0f ha", salida[cols_periodo].sum().sum())
    logger.info("  archivo           : %s", SALIDA)
    logger.info("=" * 62)
    logger.info("Siguiente: python main_local.py consolidar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
