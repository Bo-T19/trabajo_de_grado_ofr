"""
config_local.py
======================================================================
Configuracion central del pipeline LOCAL (DIST-ALERT via LP DAAC).

Reemplaza a config.py. Earth Engine solo se usa una vez, para exportar
la grilla (exportar_grilla.py); todo lo demas corre en su PC.

TODO parametro que afecte el resultado vive aqui.
======================================================================
"""
from __future__ import annotations

import logging
import os
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

# Cada carpeta corresponde a UNA etapa del pipeline. Ver GUIA_PIPELINE.md
# seccion 9 para el detalle de que genera cada script y que contiene cada una.
DIR_GRILLA = DIR_DATOS / "grilla"      # CSV exportado de GEE (una vez)
DIR_DIST = DIR_DATOS / "dist"          # COGs de DIST-ALERT, por tile
DIR_HANSEN = DIR_DATOS / "hansen"      # granulos 10x10 de Hansen GFC
DIR_CACHE = DIR_DATOS / "cache"        # indices celda y mascaras por tile
DIR_CRUDO = DIR_DATOS / "crudo"        # salida ancha (la come consolidar.py)
DIR_PANEL = DIR_DATOS / "panel"        # panel final
DIR_LOG = DIR_DATOS / "logs"

# Se crean automaticamente al importar este modulo (osea, la primera vez
# que se corre CUALQUIER script del pipeline, porque todos hacen
# "from config_local import ..."). exist_ok=True: si ya existen, no falla.
for _d in (DIR_GRILLA, DIR_DIST, DIR_HANSEN, DIR_CACHE,
           DIR_CRUDO, DIR_PANEL, DIR_LOG):
    _d.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Config:
    """Parametros del diseno. Modifique aqui, nunca en el codigo.

    frozen=True: una vez creada una instancia de Config no se puede
    modificar (Config().bbox = ... lanzaria un error). Esto evita que
    algun script cambie un parametro "de paso" y contamine el resto
    de la corrida. Si un script necesita una variante puntual (por
    ejemplo, restringir a un solo tile), usa
    dataclasses.replace(cfg, tiles=(...)) para crear una copia nueva
    en vez de mutar la existente (ver main_local.py de descargar_dist.py).
    """

    # =================================================================
    # 1. CREDENCIALES
    # =================================================================
    # Earth Engine: solo para exportar_grilla.py (assets publicos).
    # Se puede sobreescribir con la variable de entorno EE_PROJECT;
    # si no esta definida, usa el proyecto de Cloud por defecto.
    ee_project: str = os.environ.get("EE_PROJECT", "trabajodegrado-505814")

    # Earthdata Login: https://urs.earthdata.nasa.gov (gratis).
    # earthaccess lee ~/.netrc o pregunta interactivamente la primera vez.
    # No ponga la contrasena aqui.

    # =================================================================
    # 2. FUENTE UNICA DEL TARGET
    # =================================================================
    # OPERA DIST-ALERT v1, COG por capa, 30 m.
    # Estos dos valores (short_name + version) son el identificador
    # exacto que entiende el catalogo CMR de la NASA. No son un nombre
    # "bonito": hay que confirmarlos contra el catalogo real, porque
    # CMR es estricto con el formato de 'version' (por eso existe
    # diagnostico_cmr.py, que probo varias combinaciones y encontro
    # que la que funciona es esta, con version="1").
    dist_short_name: str = "OPERA_L3_DIST-ALERT-HLS_V1"
    dist_version: str = "1"

    # Cada granulo de DIST-ALERT trae 19 capas distintas (indices de
    # vegetacion, anomalias, historial, etc.). Para este pipeline solo
    # hacen falta estas dos: el estado de la alerta y la fecha del
    # evento. Descargar solo estas dos ahorra muchisimo espacio en disco.
    capa_estado: str = "VEG-DIST-STATUS"
    capa_fecha: str = "VEG-DIST-DATE"

    # Definicion operativa del evento sobre VEG-DIST-STATUS.
    # Codificacion oficial del producto:
    #   0 sin perturbacion    1 primera <50%     2 provisional <50%
    #   3 confirmada <50%     4 primera >50%     5 provisional >50%
    #   6 confirmada >50%     7 confirmada <50% finalizada
    #   8 confirmada >50% finalizada             255 sin dato
    #
    # ATENCION: la version anterior usaba (4, 8). El 4 es PRIMERA
    # deteccion, sin confirmar, y faltaba el 6 (confirmada en curso).
    # (6, 8) = confirmada con perdida >= 50%. Reportar esto en la tesis.
    #
    # En criollo: un pixel "cuenta" como deforestado solo cuando el
    # algoritmo de DIST-ALERT ya CONFIRMO el disturbio (no basta con
    # la primera sospecha, que puede ser una nube o sombra) y cuando
    # la perdida de senal vegetal fue de al menos el 50%. Este filtro
    # se aplica en zonal_local.py, linea por linea de cada instantanea.
    estados_evento: Tuple[int, ...] = (6, 8)

    # VEG-DIST-DATE no trae una fecha en formato AAAA-MM-DD: trae un
    # numero entero que cuenta los dias transcurridos desde esta fecha
    # de referencia (la "epoca" del producto). zonal_local.py hace la
    # conversion inversa (dias -> mes del panel) con tabla_dia_a_mes().
    epoca_dist: str = "2020-12-31"

    # =================================================================
    # 3. DOMINIO DE ANALISIS (mascara de bosque)
    # =================================================================
    # Version del producto Hansen Global Forest Change a descargar.
    # Cambia cada año con nuevos datos; v1.12 correspondia a 2024.
    hansen_version: str = "GFC-2025-v1.13"   # v1.12 era 2024; documentar
    # Un pixel se considera "bosque en el año 2000" si su cobertura de
    # dosel arboreo (capa treecover2000, en %) es mayor o igual a esto.
    umbral_dosel: int = 30                   # % dosel en 2000
    # Ano de corte para la mascara de bosque remanente: un pixel que
    # tuvo bosque en 2000 pero lo perdio (lossyear) ANTES de este ano
    # ya no cuenta como bosque disponible al arrancar el analisis.
    # Perdidas ocurridas EN o DESPUES de este ano son las que el
    # pipeline intenta detectar via DIST-ALERT, no via Hansen.
    anio_mascara: int = 2022                 # bosque remanente al inicio

    # =================================================================
    # 4. VENTANA TEMPORAL
    # =================================================================
    fecha_inicio: str = "2023-01-01"
    fecha_fin: str = "2026-08-01"    # exclusivo
    # Resolucion temporal del panel final (no de la descarga): "MS"
    # = un periodo por mes ("Month Start", codigo de pandas.date_range).
    frecuencia: str = "MS"           # MS = mensual

    # Cadencia de instantaneas de DIST-ALERT a DESCARGAR (independiente
    # de 'frecuencia', que es la resolucion del panel de salida).
    # "MS" = una por mes (~40 GB en total para Colombia).
    # "SMS" = quincenal: duplica el disco pero reduce el riesgo de que
    # una alerta se reinicie entre instantaneas. Con 915 GB es viable.
    cadencia_snapshot: str = "MS"

    # =================================================================
    # 5. DISENO ESPACIAL
    # =================================================================
    grid_scale_m: int = 5_000        # lado de la celda, en metros (5 km)
    grid_crs: str = "EPSG:3116"      # MAGNA-SIRGAS / Colombia Bogota
    px_dist_m: int = 30              # resolucion nativa de DIST-ALERT, en metros
    # Celdas de la grilla con menos hectareas de bosque base que esto
    # se descartan en consolidar.py: una celda de paramo o sabana no
    # se puede deforestar, e incluirla solo ensucia el panel con ceros.
    bosque_minimo_ha: float = 50.0   # celdas con menos bosque se descartan

    # =================================================================
    # 6. EJECUCION
    # =================================================================
    # Rectangulo (lon_min, lat_min, lon_max, lat_max) que cubre Colombia
    # con margen. Se usa para consultar CMR (DIST-ALERT) y para calcular
    # que granulos de Hansen hacen falta. Como es un rectangulo, tambien
    # toca paises vecinos y oceano: por eso existe filtrar_tiles.py, que
    # recorta el inventario resultante a los tiles que si son de Colombia.
    bbox: Tuple[float, float, float, float] = (-79.2, -4.4, -66.7, 13.5)

    reintentos: int = 3              # reintentos por archivo antes de darlo por fallido
    timeout_s: int = 300             # segundos de espera por solicitud HTTP
    hilos_descarga: int = 6          # descargas simultaneas a LP DAAC

    # Tiles MGRS a procesar. Vacio (tupla vacia) = todos los que cubran
    # el bbox. Se usa para restringir el pipeline a un solo tile en modo
    # "piloto" (ver main_local.py) o para depurar un tile especifico.
    tiles: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def area_px_ha(self) -> float:
        """Hectareas por pixel de DIST-ALERT. A 30 m son exactamente 0.09.

        Como todos los pixeles de DIST-ALERT miden exactamente
        30 x 30 m = 900 m^2 = 0.09 ha, convertir un conteo de pixeles
        a hectareas es tan simple como multiplicar por esta constante
        (no hace falta calcular area por reproyeccion pixel a pixel).
        """
        return (self.px_dist_m ** 2) / 10_000.0
