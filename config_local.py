"""
config_local.py
======================================================================
Configuracion central del pipeline. Todo corre en su PC: no hay
dependencia de Google Earth Engine ni de ninguna cuenta de la NASA --
la unica credencial que hace falta es una API key gratuita de Global
Forest Watch (ver configurar_gfw.py).

TODO parametro que afecte el resultado vive aqui.
======================================================================
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

# Configura el logging global: todo el pipeline (los demas scripts hacen
# "from config_local import logger") escribe con este mismo formato,
# asi que basta con importar 'logger' en cualquier script para que los
# mensajes salgan consistentes: hora | nivel (INFO/WARNING/ERROR) | mensaje.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


# ---------------------------------------------------------------------
# RUTAS
# ---------------------------------------------------------------------
# RAIZ = la carpeta donde vive este archivo (la raiz del proyecto),
# calculada de forma robusta sin depender de cual sea el directorio
# de trabajo desde donde se lanzo python.
RAIZ = Path(__file__).resolve().parent
DIR_DATOS = RAIZ / "datos"

# Cada carpeta corresponde a UNA etapa del pipeline. Ver GUIA_CODIGO.md
# seccion 10 para el detalle de que genera cada script y que contiene cada una.
DIR_GRILLA = DIR_DATOS / "grilla"      # CSV de la grilla, generado localmente (una vez)
DIR_GFW = DIR_DATOS / "gfw"            # cache de lotes de la API de GFW
DIR_HANSEN = DIR_DATOS / "hansen"      # granulos 10x10 de Hansen GFC
DIR_CACHE = DIR_DATOS / "cache"        # bosque_ha por celda, ya calculado
DIR_CRUDO = DIR_DATOS / "crudo"        # salida ancha de calcular_bosque.py + descargar_gfw.py
DIR_PANEL = DIR_DATOS / "panel"        # panel final
DIR_LIMITES = DIR_DATOS / "limites"    # limites municipales del DANE (MGN), para el cruce municipal
DIR_LOG = DIR_DATOS / "logs"

# Se crean automaticamente al importar este modulo (osea, la primera vez
# que se corre CUALQUIER script del pipeline, porque todos hacen
# "from config_local import ..."). exist_ok=True: si ya existen, no falla.
for _d in (DIR_GRILLA, DIR_GFW, DIR_HANSEN, DIR_CACHE,
           DIR_CRUDO, DIR_PANEL, DIR_LIMITES, DIR_LOG):
    _d.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Config:
    """Parametros del diseno. Modifique aqui, nunca en el codigo.

    frozen=True: una vez creada una instancia de Config no se puede
    modificar (Config().bbox = ... lanzaria un error). Esto evita que
    algun script cambie un parametro "de paso" y contamine el resto
    de la corrida.
    """

    # =================================================================
    # 1. DOMINIO ESPACIAL (bosque base, con Hansen GFC)
    # =================================================================
    # Version del producto Hansen Global Forest Change a descargar.
    # Cambia cada año con nuevos datos; v1.12 correspondia a 2024.
    hansen_version: str = "GFC-2025-v1.13"

    # Un pixel se considera "bosque en el año 2000" si su cobertura de
    # dosel arboreo (capa treecover2000, en %) es mayor o igual a esto.
    # 30% es el umbral mas usado en la literatura para operacionalizar
    # "bosque" a partir de cobertura continua (entre otros, uno de los
    # de referencia de la FAO), lo que facilita comparar con otros
    # estudios.
    umbral_dosel: int = 30

    # Ano de corte para la mascara de bosque remanente: un pixel que
    # tuvo bosque en 2000 pero lo perdio (lossyear) ANTES de este ano ya
    # no cuenta como bosque disponible al arrancar el analisis. Un año
    # antes del inicio de la ventana de eventos (fecha_inicio, seccion
    # 3): el bosque base tiene que quedar definido justo antes de que
    # arranque la fuente de evento, para que Hansen y GFW nunca se
    # atribuyan la misma perdida dos veces.
    anio_mascara: int = 2019

    # Resolucion (metros/pixel) y tamano de bloque (en celdas de la
    # grilla) con que calcular_bosque.py reproyecta Hansen sobre la
    # grilla nacional -- ver ese modulo para el detalle. 25 m divide
    # exactamente el lado de un bloque de 20 celdas (20*5000/25=4000
    # pixeles, sin residuo), evitando cualquier redondeo en los bordes
    # entre bloques.
    bosque_resolucion_m: int = 25
    bosque_bloque_celdas: int = 20

    # =================================================================
    # 2. DISENO ESPACIAL DE LA GRILLA
    # =================================================================
    grid_scale_m: int = 5_000        # lado de la celda, en metros (5 km)
    grid_crs: str = "EPSG:3116"      # MAGNA-SIRGAS / Colombia Bogota
    # Celdas de la grilla con menos hectareas de bosque base que esto
    # se descartan en consolidar.py: una celda de paramo o sabana no
    # se puede deforestar, e incluirla solo ensucia el panel con ceros.
    bosque_minimo_ha: float = 50.0

    # Rectangulo (lon_min, lat_min, lon_max, lat_max) que cubre Colombia
    # con margen, usado para saber que granulos de Hansen hacen falta.
    bbox: Tuple[float, float, float, float] = (-79.2, -4.4, -66.7, 13.5)

    # =================================================================
    # 3. VENTANA TEMPORAL Y FUENTE DEL EVENTO (Global Forest Watch)
    # =================================================================
    # Producto integrado de Global Forest Watch / World Resources
    # Institute: combina DIST-ALERT (NASA OPERA), GLAD-L (Landsat, UMD),
    # GLAD-S2 (Sentinel-2, UMD) y RADD (radar Sentinel-1, Wageningen
    # University) en una sola capa con una unica escala de confianza.
    # Metodologia publicada y revisada por pares: Pickens, Hansen, Song
    # et al., "Rapid monitoring of global land change", Nature
    # Communications 16, 8948 (2025). Se consulta via su API SQL
    # (ver descargar_gfw.py), no se descarga ningun raster de evento.
    gfw_dataset: str = "gfw_integrated_dist_alerts"
    gfw_version: str = "latest"

    fecha_inicio: str = "2020-01-01"
    fecha_fin: str = "2026-08-01"    # exclusivo
    # Resolucion temporal del panel final: "MS" = un periodo por mes
    # ("Month Start", codigo de pandas.date_range).
    frecuencia: str = "MS"

    # Confianza minima para contar como "evento". El producto expone
    # tres niveles (nominal/high/highest); se excluye 'nominal' (la
    # deteccion menos confiable, equivalente a una alerta "provisional"
    # sin confirmar) y se incluyen 'high' y 'highest'.
    gfw_confianza_minima: Tuple[str, ...] = ("high", "highest")

    # Cuantas celdas de la grilla se mandan por lote a la API de GFW.
    # El limite duro del servicio es 256 KB por payload; 400 celdas
    # (rectangulos de 5 km) quedan con margen de sobra y tardan del
    # orden de 30-50 s por lote en la practica.
    gfw_celdas_por_lote: int = 400
    gfw_lotes_en_paralelo: int = 6

    # =================================================================
    # 4. EJECUCION
    # =================================================================
    reintentos: int = 3              # reintentos por archivo antes de darlo por fallido
    timeout_s: int = 300             # segundos de espera por solicitud HTTP
    hilos_descarga: int = 6          # descargas simultaneas (Hansen)

    @property
    def area_px_ha(self) -> float:
        """Hectareas por pixel de la reproyeccion de Hansen (ver calcular_bosque.py)."""
        return (self.bosque_resolucion_m ** 2) / 10_000.0
