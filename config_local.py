"""
config_local.py
======================================================================
Configuracion central del pipeline LOCAL. Todo corre en su PC: no hay
ninguna dependencia de Google Earth Engine (ver exportar_grilla.py para
el porque).

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
DIR_DIST = DIR_DATOS / "dist"          # COGs de DIST-ALERT, por tile (fuente_dist_alert/)
DIR_GFW = DIR_DATOS / "gfw"            # descargas del producto integrado GFW (fuente_gfw/)
DIR_HANSEN = DIR_DATOS / "hansen"      # granulos 10x10 de Hansen GFC (compartida)
DIR_CACHE = DIR_DATOS / "cache"        # indices celda y mascaras por tile (compartida)
DIR_CRUDO = DIR_DATOS / "crudo"        # salida ancha de CADA fuente (consolidar.py las une)
DIR_PANEL = DIR_DATOS / "panel"        # panel final
DIR_LOG = DIR_DATOS / "logs"

# Se crean automaticamente al importar este modulo (osea, la primera vez
# que se corre CUALQUIER script del pipeline, porque todos hacen
# "from config_local import ..."). exist_ok=True: si ya existen, no falla.
for _d in (DIR_GRILLA, DIR_DIST, DIR_GFW, DIR_HANSEN, DIR_CACHE,
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
    # Earthdata Login: https://urs.earthdata.nasa.gov (gratis).
    # earthaccess lee ~/.netrc o pregunta interactivamente la primera vez.
    # No ponga la contrasena aqui.
    #
    # (Ya no hace falta credencial de Google Earth Engine: exportar_grilla.py
    # construye la grilla localmente con geopandas + limites del DANE.
    # Ver el docstring de ese archivo para el porque del cambio.)

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
    # Perdidas ocurridas EN o DESPUES de este ano son las que la fuente
    # de evento debe detectar -- no Hansen.
    #
    # IMPORTANTE: este pipeline produce DOS paneles independientes que
    # NUNCA se mezclan (fuente_dist_alert/, solo 2023+; fuente_gfw/,
    # solo 2020+ -- ver METODOLOGIA.md decision 15). Cada uno necesita
    # su bosque base cortado justo ANTES de que arranque SU PROPIA
    # ventana de eventos, no la del otro:
    #   - Panel DIST-ALERT (arranca 2023-01): anio_mascara = 2022
    #   - Panel GFW         (arranca 2020-01): anio_mascara = 2019
    # Este valor por defecto (2022) es el que usa fuente_dist_alert/
    # zonal_local.py. fuente_gfw/descargar_gfw.py NO usa este default:
    # pide su propia mascara con anio_mascara=2019 explicito (ver
    # ANIO_MASCARA_GFW mas abajo). mascara_bosque() en zonal_local.py
    # incluye anio_mascara en el nombre de la cache precisamente para
    # que las dos mascaras nunca se pisen entre si.
    anio_mascara: int = 2022                 # bosque remanente al inicio de la ventana DIST-ALERT

    # Corte de mascara para el panel GFW (ver nota arriba). Vive como
    # constante aparte, no como default de la clase, para que sea
    # imposible confundirlo con anio_mascara al llamar mascara_bosque()
    # sin pasar el argumento explicito.
    anio_mascara_gfw: int = 2019             # bosque remanente al inicio de la ventana GFW

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

    # =================================================================
    # 7. FUENTE GFW (evento 2020-presente, fuente_gfw/, panel INDEPENDIENTE)
    # =================================================================
    # DIST-ALERT no tiene datos antes de 2023-01 (verificado contra CMR,
    # ver METODOLOGIA.md decision 1 y su nota de revision). Para tener
    # un panel que arranque en 2020, fuente_gfw/descargar_gfw.py usa el
    # producto integrado de Global Forest Watch (DIST-ALERT + GLAD-L +
    # GLAD-S2 + RADD en una sola escala de confianza) para TODA la
    # ventana 2020-presente, consultado via su API SQL -- no solo para
    # rellenar 2020-2022. Este panel NUNCA se mezcla ni se concatena
    # con el panel DIST-ALERT: son dos productos independientes que el
    # usuario elige segun necesite (ver METODOLOGIA.md decision 15).
    gfw_dataset: str = "gfw_integrated_dist_alerts"
    gfw_version: str = "latest"

    # Inicio de la ventana de este panel. El fin lo marca fecha_fin
    # (arriba, seccion 4) -- el mismo limite que usa el panel DIST-ALERT,
    # asi los dos llegan hasta el mismo mes mas reciente aunque nunca se
    # combinen.
    fecha_inicio_gfw: str = "2020-01-01"

    # Confianza minima para contar como "evento", analogo a
    # estados_evento=(6,8) de DIST-ALERT: se excluye 'nominal' (la
    # deteccion menos confiable, equivalente a una alerta "provisional"
    # sin confirmar) y se incluyen 'high' y 'highest'.
    gfw_confianza_minima: Tuple[str, ...] = ("high", "highest")

    # Cuantas celdas de la grilla se mandan por lote a la API de GFW.
    # El limite duro del servicio es 256 KB por payload; 400 celdas
    # (rectangulos de 5 km) quedan con margen de sobra y tardan del
    # orden de 30-50 s por lote en la practica.
    gfw_celdas_por_lote: int = 400
    gfw_lotes_en_paralelo: int = 6

    @property
    def area_px_ha(self) -> float:
        """Hectareas por pixel de DIST-ALERT. A 30 m son exactamente 0.09.

        Como todos los pixeles de DIST-ALERT miden exactamente
        30 x 30 m = 900 m^2 = 0.09 ha, convertir un conteo de pixeles
        a hectareas es tan simple como multiplicar por esta constante
        (no hace falta calcular area por reproyeccion pixel a pixel).
        """
        return (self.px_dist_m ** 2) / 10_000.0
