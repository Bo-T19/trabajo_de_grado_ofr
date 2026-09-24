"""
demo_landsat_caqueta.py
======================================================================
PRUEBA DE CONCEPTO: derivar perdida de bosque directamente de imagenes
Landsat 8/9 sobre una zona piloto de Caqueta, y contrastarla con las
alertas GLAD-L.

    python demo_landsat_caqueta.py

Salidas: datos/demo/  (ver la seccion SALIDAS mas abajo)

QUE DEMUESTRA Y QUE NO
----------------------
Demuestra que la deteccion de perdida de bosque se puede derivar desde
la imagen cruda -- compuestos, indice espectral, umbral, filtro de
parche-- y evaluarse contra un producto publicado, con separacion
honesta entre calibracion y validacion.

NO pretende reemplazar a GLAD-L como variable objetivo del modelo
nacional. Es una zona piloto, un par de fechas y un indice; el producto
de GFW integra tres sistemas, cobertura continua y una escala de
confianza validada.

SIN GOOGLE EARTH ENGINE, Y POR QUE IMPORTA
------------------------------------------
Todo el computo ocurre en este PC, igual que el resto del repositorio, y
NO hace falta ninguna credencial nueva: la unica que se usa es la API
key de Global Forest Watch que el pipeline ya tiene.

Esa decision no es de comodidad. El nivel gratuito de Earth Engine es
explicitamente para uso NO COMERCIAL, y el destino declarado de este
trabajo incluye consultorias del Observatorio Financiero Rural. Derivar
la deteccion sin depender de una plataforma con esa restriccion mantiene
al proyecto entero en terreno utilizable.

De donde sale cada insumo:

  Escenas Landsat  catalogo STAC de Microsoft Planetary Computer,
                   publico y sin credencial. Los archivos son COG, de
                   modo que se lee SOLO el recorte de la zona piloto en
                   vez de descargar escenas completas de ~1 GB.
  Bosque base      los granulos de Hansen que ya estan en datos/hansen/
                   (python main_local.py hansen). Cero descargas.
  GLAD-L           raster date_conf del data-lake de GFW, con la misma
                   API key del pipeline, leido tambien por ventana.

METODO
------
Un pixel cuenta como perdida si cumple las tres condiciones:

  1. Era bosque al inicio de T1, segun Hansen GFC: dosel del ano 2000
     >= UMBRAL_DOSEL y sin perdida registrada antes de la ventana. Si
     los granulos de datamask estan en disco se exige ademas tierra
     firme, pero el umbral de dosel ya excluye el agua.

  2. Su NBR cayo mas que un umbral. NBR = (NIR - SWIR2)/(NIR + SWIR2),
     que responde fuerte a la perdida de biomasa verde. Se comparan dos
     compuestos de MEDIANA de la MISMA temporada seca -- enero a marzo de
     dos anios consecutivos-- para que la diferencia no recoja
     estacionalidad fenologica. dNBR = NBR(T1) - NBR(T2).

  3. Pertenece a un parche de al menos 1 ha, el area minima de la
     definicion de bosque del IDEAM. Un pixel aislado que cruza el
     umbral suele ser ruido de sensor o un borde mal registrado.

POR QUE LA VENTANA ES 2022-2023
-------------------------------
El raster de GLAD-L que publica el data-lake de GFW es un producto
RODANTE: la version vigente arranca en enero de 2021 y no conserva los
anios anteriores. Se verifico la cobertura real sobre la zona piloto
antes de fijar las fechas, y 2022 y 2023 son los dos primeros anios
consecutivos con alertas confirmadas completas. De paso, ambos tienen
escenas de Landsat 8 y 9, mientras que en 2020 solo existia Landsat 8.

EL DOMINIO, Y POR QUE IMPORTA
-----------------------------
El dominio de analisis es el bosque inicial CON al menos una observacion
limpia en T1 y otra en T2. Un pixel tapado por nubes en cualquiera de
las dos ventanas no se puede evaluar, y contarlo como "estable" seria
inventar un dato: se excluye, y el porcentaje excluido se reporta como
resultado. En la Amazonia ese porcentaje es alto y es, por si mismo,
evidencia del problema de nubosidad que justifica el uso de radar en los
productos operativos.

LA COMPARACION CON GLAD-L
-------------------------
A GLAD-L se le aplica EXACTAMENTE el mismo tratamiento: la misma mascara
de bosque, el mismo dominio y el mismo filtro de area minima, filtrando
ademas por fecha de alerta dentro de la ventana T1-T2. Sin esas cuatro
igualaciones la comparacion mediria diferencias de encuadre, no de
deteccion.

CALIBRACION SEPARADA DE LA VALIDACION
-------------------------------------
El umbral de dNBR se calibra en la MITAD OESTE de la zona y se evalua en
la MITAD ESTE. Calibrar y evaluar sobre los mismos pixeles infla
cualquier metrica, y es de las primeras cosas que un jurado revisa.

SALIDAS (datos/demo/)
---------------------
  diagnostico_nubes.csv         observaciones limpias y porcentaje de
                                bosque sin datos
  calibracion_umbral.csv        metricas por umbral, en la mitad OESTE
  evaluacion_validacion.csv     matriz de acuerdo y metricas, mitad ESTE
  curva_observabilidad.csv      concordancia segun cuantas observaciones
                                limpias se exijan, con la cobertura de
                                area que queda en cada caso
  comparacion_celdas.csv        hectareas por celda de 5 km, ambas fuentes
  muestra_validacion_visual.csv muestra estratificada para interpretar a
                                mano (Olofsson et al., 2014)
  mapa_revision.html            mapa folium con todas las capas

REQUISITOS
----------
Los mismos del pipeline (requirements_local.txt). No hace falta cuenta
de Google ni instalar nada adicional.
======================================================================
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds
from scipy import ndimage

from config_local import DIR_DATOS, DIR_HANSEN, DIR_LOG, logger
from zonal import reproyectar_sobre_bloque

# =====================================================================
# CONSTANTES
# Todo parametro que afecte el resultado vive aqui, igual que en el
# resto del repositorio.
# =====================================================================

# Zona piloto: nucleo de deforestacion del arco amazonico, entre
# Cartagena del Chaira y San Vicente del Caguan (Caqueta). Se escoge
# porque concentra perdida suficiente para que las metricas tengan
# sentido; en una zona estable casi todo seria "verdadero negativo" y la
# comparacion no distinguiria nada.
BBOX = (-75.0, 0.8, -74.2, 1.5)          # lon_min, lat_min, lon_max, lat_max

# Ventanas de composicion: misma temporada seca en anios consecutivos.
# Ver "POR QUE LA VENTANA ES 2022-2023" en el encabezado.
T1_INICIO, T1_FIN = "2022-01-01", "2022-03-31"
T2_INICIO, T2_FIN = "2023-01-01", "2023-03-31"

# Ventana equivalente para GLAD-L. Un compuesto de mediana sobre
# enero-marzo representa el estado a MITAD de esa ventana, no a su
# inicio ni a su final; por eso la ventana de alertas va del punto medio
# de T1 al punto medio de T2.
GLAD_DESDE = dt.date(2022, 2, 15)
GLAD_HASTA = dt.date(2023, 2, 15)
GLAD_CONF_MIN = 3                        # 3 = alerta confirmada

# Bosque inicial. Se usan los granulos LOCALES, que el pipeline ya
# descarga; no hay que bajar nada nuevo.
UMBRAL_DOSEL = 30                        # mismo valor que config_local.py
ANIO_CORTE_PERDIDA = 21                  # lossyear <= 21 = perdida previa a 2022

# Deteccion propia. La rejilla llega hasta 0,70: con el tope en 0,35 el F1
# todavia venia subiendo en el ultimo valor probado, asi que el optimo
# quedaba fuera del rango y el umbral elegido era el borde de la busqueda.
UMBRALES_DNBR = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35,
                 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]

# Area minima de parche. A 30 m cada pixel son 900 m2 = 0,09 ha, asi que
# 11 pixeles son 0,99 ha: se quedan JUSTO por debajo de la hectarea. 12
# es el primer entero que la alcanza (1,08 ha), y es el que se usa para
# no admitir parches menores al minimo del IDEAM.
PIXELES_MIN_PARCHE = 12

ESCALA_M = 30
CRS = "EPSG:32618"                       # UTM 18N, la zona del sur de Colombia
LADO_CELDA_M = 5000                      # celda de agregacion, escala del modelo
FILAS_POR_FRANJA = 512                   # ver compuesto_nbr(): acota la memoria
PUNTOS_POR_ESTRATO = 50
SEMILLA = 42

# Catalogo STAC publico de Microsoft Planetary Computer.
STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token/landsat-c2-l2"
COLECCION_STAC = "landsat-c2-l2"
PLATAFORMAS = ["landsat-8", "landsat-9"]

# GLAD-L en el data-lake de GFW.
GFW_API = "https://data-api.globalforestwatch.org"
GLAD_DATASET = "umd_glad_landsat_alerts"
GLAD_TILE = "10N_080W"                   # tesela de 10x10 que cubre la zona
GLAD_EPOCA = dt.date(2014, 12, 31)       # origen de la codificacion de fecha

DIR_DEMO = DIR_DATOS / "demo"
TIEMPO_ESPERA = 300


# =====================================================================
# 1. REJILLA DE TRABAJO
# =====================================================================
def perfil_zona() -> dict:
    """
    Raster sintetico que cubre la zona piloto, en CRS a ESCALA_M.

    Es el mismo patron que usa zonal.perfil_bloque() para el panel
    nacional: en vez de adoptar la rejilla de alguna de las fuentes, se
    define una propia y TODAS se reproyectan sobre ella. Asi ninguna
    fuente impone su alineacion a las demas, y un pixel significa lo
    mismo en las cuatro capas.

    Los limites se redondean a multiplos de ESCALA_M para que la rejilla
    quede alineada y no aparezcan medios pixeles en los bordes.
    """
    izq, abajo, der, arriba = transform_bounds("EPSG:4326", CRS, *BBOX, densify_pts=21)
    izq, abajo = np.floor(izq / ESCALA_M) * ESCALA_M, np.floor(abajo / ESCALA_M) * ESCALA_M
    der, arriba = np.ceil(der / ESCALA_M) * ESCALA_M, np.ceil(arriba / ESCALA_M) * ESCALA_M

    ancho = int(round((der - izq) / ESCALA_M))
    alto = int(round((arriba - abajo) / ESCALA_M))
    # Affine(a, b, c, d, e, f): x = a*col + c ; y = e*fila + f.
    # e negativo porque las filas avanzan hacia abajo y la Y geografica
    # hacia arriba (convencion "north-up").
    return {"transform": Affine(ESCALA_M, 0, izq, 0, -ESCALA_M, arriba),
            "crs": CRS, "height": alto, "width": ancho,
            "bounds": (izq, abajo, der, arriba)}


def mascara_mitades(perfil: dict) -> Tuple[np.ndarray, np.ndarray]:
    """
    Divide la zona por su meridiano central: oeste calibra, este valida.

    El corte se hace sobre la rejilla proyectada, no sobre longitudes,
    para que ambas mitades tengan exactamente el mismo numero de
    columnas y ninguna quede sistematicamente mas grande.
    """
    mitad = perfil["width"] // 2
    oeste = np.zeros((perfil["height"], perfil["width"]), dtype=bool)
    oeste[:, :mitad] = True
    return oeste, ~oeste


# =====================================================================
# 2. LANDSAT: BUSQUEDA, LECTURA POR VENTANA Y COMPUESTO
# =====================================================================
def buscar_escenas(inicio: str, fin: str) -> List[dict]:
    """
    Consulta el catalogo STAC de Planetary Computer.

    Se usa requests directamente en vez de pystac-client para no sumar
    dependencias: la consulta es un unico POST con un JSON, y el
    pipeline ya trae requests.

    NO se filtra por nubosidad de escena. Una escena con 80 % de nubes
    puede tener perfectamente despejada la esquina que nos interesa, y
    descartarla reduciria observaciones justo donde mas falta hacen. El
    filtro real es por pixel, con QA_PIXEL.
    """
    q = {"collections": [COLECCION_STAC], "bbox": list(BBOX),
         "datetime": f"{inicio}/{fin}",
         "query": {"platform": {"in": PLATAFORMAS}}, "limit": 100}
    try:
        r = requests.post(STAC_URL, json=q, timeout=TIEMPO_ESPERA)
        r.raise_for_status()
        escenas = r.json().get("features", [])
    except Exception as e:
        raise SystemExit(f"No se pudo consultar el catalogo STAC:\n  {e}")

    if not escenas:
        raise SystemExit(
            f"El catalogo no devolvio escenas Landsat 8/9 entre {inicio} y {fin} "
            f"sobre la zona piloto. Revise BBOX y las fechas.")

    por_plat: Dict[str, int] = {}
    for e in escenas:
        p = e["properties"].get("platform", "?")
        por_plat[p] = por_plat.get(p, 0) + 1
    logger.info("  %s a %s: %d escenas  (%s)", inicio, fin, len(escenas),
                ", ".join(f"{k}: {v}" for k, v in sorted(por_plat.items())))
    return escenas


def token_sas() -> str:
    """
    Token de lectura anonimo para el almacenamiento de Planetary
    Computer. No exige cuenta: lo entrega el servicio a quien lo pida.
    """
    try:
        r = requests.get(SAS_URL, timeout=TIEMPO_ESPERA)
        r.raise_for_status()
        return r.json()["token"]
    except Exception as e:
        raise SystemExit(f"No se pudo obtener el token de lectura:\n  {e}")


def _leer_ventana(url: str, perfil: dict, fila0: int, n_filas: int,
                  dtype) -> Optional[np.ndarray]:
    """
    Lee de un COG remoto SOLO el rectangulo que cae sobre una franja de
    la rejilla de trabajo, y lo reproyecta sobre ella.

    Aqui esta el ahorro que hace viable trabajar sin Earth Engine: una
    escena Landsat completa pesa del orden de 1 GB, pero al ser COG el
    servidor entrega unicamente los bloques que cubren la ventana
    pedida. Se descargan megabytes, no gigabytes.

    Devuelve None si la escena no intersecta la franja.
    """
    tr = perfil["transform"]
    arriba = tr.f + tr.e * fila0
    abajo = tr.f + tr.e * (fila0 + n_filas)
    izq, der = tr.c, tr.c + tr.a * perfil["width"]

    destino = np.zeros((n_filas, perfil["width"]), dtype=dtype)
    tr_franja = Affine(tr.a, 0, izq, 0, tr.e, arriba)

    try:
        with rasterio.open(f"/vsicurl/{url}") as src:
            # Limites de la franja expresados en el CRS de la escena.
            b = transform_bounds(perfil["crs"], src.crs, izq, abajo, der, arriba,
                                 densify_pts=21)
            sb = src.bounds
            if b[2] <= sb.left or b[0] >= sb.right or b[3] <= sb.bottom or b[1] >= sb.top:
                return None                      # sin traslape

            ven = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
            # Un margen de un pixel evita perder la fila o columna del
            # borde al remuestrear.
            ven = Window(max(0, ven.col_off - 1), max(0, ven.row_off - 1),
                         min(ven.width + 2, src.width), min(ven.height + 2, src.height))
            if ven.width <= 0 or ven.height <= 0:
                return None

            datos = src.read(1, window=ven)
            reproject(source=datos, destination=destino,
                      src_transform=src.window_transform(ven), src_crs=src.crs,
                      dst_transform=tr_franja, dst_crs=perfil["crs"],
                      resampling=Resampling.nearest,
                      src_nodata=0, dst_nodata=0)
    except Exception as e:
        logger.warning("      no se pudo leer una escena (%s); se omite", e)
        return None
    return destino


def _nbr_de_escena(escena: dict, sas: str, perfil: dict,
                   fila0: int, n_filas: int) -> Optional[np.ndarray]:
    """
    NBR de una escena sobre una franja, con nubes enmascaradas.

    Bits de QA_PIXEL que se descartan:
        1  nube dilatada  (borde difuso alrededor de la nube)
        3  nube
        4  sombra de nube (tan daniana como la nube: baja la
                           reflectancia y simula perdida de biomasa)

    Los valores de Collection 2 nivel 2 vienen como enteros escalados;
    hay que aplicar la ganancia 0.0000275 y el desplazamiento -0.2 para
    volver a reflectancia fisica. Sin esa conversion el NBR sigue siendo
    un cociente normalizado y "parece" correcto, pero no lo es.

    Devuelve un array float32 con NaN donde no hay observacion valida.
    """
    a = escena["assets"]
    nir = _leer_ventana(f"{a['nir08']['href']}?{sas}", perfil, fila0, n_filas, np.uint16)
    if nir is None:
        return None
    swir = _leer_ventana(f"{a['swir22']['href']}?{sas}", perfil, fila0, n_filas, np.uint16)
    qa = _leer_ventana(f"{a['qa_pixel']['href']}?{sas}", perfil, fila0, n_filas, np.uint16)
    if swir is None or qa is None:
        return None

    limpio = ((qa & (1 << 1)) == 0) & ((qa & (1 << 3)) == 0) & ((qa & (1 << 4)) == 0)
    valido = limpio & (nir > 0) & (swir > 0) & (qa > 0)

    nir_r = nir.astype(np.float32) * 0.0000275 - 0.2
    swir_r = swir.astype(np.float32) * 0.0000275 - 0.2
    suma = nir_r + swir_r
    with np.errstate(divide="ignore", invalid="ignore"):
        nbr = (nir_r - swir_r) / suma
    nbr[~valido | (suma == 0)] = np.nan
    return nbr.astype(np.float32)


def compuesto_nbr(escenas: List[dict], sas: str, perfil: dict,
                  etiqueta: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compuesto de MEDIANA del NBR y conteo de observaciones limpias.

    Se usa mediana y no media porque es robusta a las observaciones
    residuales que la mascara de nubes deja pasar: una sola lectura
    contaminada desplaza la media, pero no la mediana.

    El trabajo va por FRANJAS horizontales para acotar la memoria.
    Apilar todas las escenas de la zona completa exigiria del orden de
    varios cientos de MB simultaneos; por franjas, el pico queda en
    decenas y el resultado es identico.
    """
    alto, ancho = perfil["height"], perfil["width"]
    nbr = np.full((alto, ancho), np.nan, dtype=np.float32)
    obs = np.zeros((alto, ancho), dtype=np.uint16)

    for fila0 in range(0, alto, FILAS_POR_FRANJA):
        n = min(FILAS_POR_FRANJA, alto - fila0)
        pila = [c for c in
                (_nbr_de_escena(e, sas, perfil, fila0, n) for e in escenas)
                if c is not None]
        if not pila:
            logger.warning("    %s franja %d-%d: sin observaciones", etiqueta,
                           fila0, fila0 + n)
            continue
        cubo = np.stack(pila)
        with warnings.catch_warnings():
            # nanmedian avisa "All-NaN slice" cuando un pixel estuvo
            # nublado en TODAS las escenas. Es el caso esperado y no un
            # fallo: ese pixel queda en NaN, no entra al dominio, y
            # termina contado en el diagnostico de nubes. Se silencia el
            # aviso para que no tape el registro util de la corrida.
            warnings.simplefilter("ignore", RuntimeWarning)
            nbr[fila0:fila0 + n] = np.nanmedian(cubo, axis=0)
        obs[fila0:fila0 + n] = np.sum(~np.isnan(cubo), axis=0).astype(np.uint16)
        logger.info("    %s franja %4d-%4d de %d  (%d escenas con datos)",
                    etiqueta, fila0, fila0 + n, alto, len(pila))
    return nbr, obs


def compuestos_con_cache(perfil: dict):
    """
    Compuestos de T1 y T2, reutilizando el resultado si ya se calculo.

    Componer las dos ventanas exige leer del orden de 70 escenas por
    HTTP y toma varios minutos. Ese resultado depende UNICAMENTE de la
    zona, las fechas y la rejilla, no de los umbrales de deteccion, asi
    que se guarda en disco: ajustar UMBRALES_DNBR o PIXELES_MIN_PARCHE y
    volver a correr pasa a costar segundos.

    La clave del archivo incluye los parametros que SI cambian el
    contenido -- zona, fechas y forma de la rejilla-- para que un cambio
    en cualquiera de ellos invalide el cache en vez de devolver
    calladamente un compuesto de otra corrida. Es el mismo cuidado que
    calcular_bosque.py tiene con su propio cache.
    """
    clave = (f"nbr_{BBOX[0]}_{BBOX[1]}_{BBOX[2]}_{BBOX[3]}"
             f"_{T1_INICIO}_{T1_FIN}_{T2_INICIO}_{T2_FIN}"
             f"_{perfil['width']}x{perfil['height']}").replace("-", "")
    archivo = DIR_DEMO / f"cache_{clave}.npz"

    if archivo.exists():
        logger.info("  reutilizando compuestos en cache (%s)", archivo.name)
        d = np.load(archivo)
        return d["nbr_t1"], d["obs_t1"], d["nbr_t2"], d["obs_t2"]

    e_t1 = buscar_escenas(T1_INICIO, T1_FIN)
    e_t2 = buscar_escenas(T2_INICIO, T2_FIN)
    sas = token_sas()
    logger.info("  componiendo T1...")
    nbr_t1, obs_t1 = compuesto_nbr(e_t1, sas, perfil, "T1")
    logger.info("  componiendo T2...")
    nbr_t2, obs_t2 = compuesto_nbr(e_t2, sas, perfil, "T2")

    np.savez_compressed(archivo, nbr_t1=nbr_t1, obs_t1=obs_t1,
                        nbr_t2=nbr_t2, obs_t2=obs_t2)
    logger.info("  compuestos guardados en %s", archivo.name)
    return nbr_t1, obs_t1, nbr_t2, obs_t2


# =====================================================================
# 3. BOSQUE INICIAL, DESDE LOS GRANULOS LOCALES
# =====================================================================
def mascara_bosque(perfil: dict) -> np.ndarray:
    """
    Bosque existente al inicio de T1, segun Hansen GFC.

    Tres condiciones:

      dosel >= UMBRAL_DOSEL  cobertura arborea suficiente en 2000. Es el
                             mismo umbral que usa el panel nacional
                             (config_local.umbral_dosel), para que la
                             demo hable de "bosque" en los mismos
                             terminos.
      sin perdida previa     si ya se habia deforestado antes de la
                             ventana, no puede volver a perderse dentro
                             de ella. Sin esto la demo contaria como
                             hallazgo un claro que existe hace anios.
      datamask == 1          tierra firme, OPCIONAL. El pipeline solo
                             descarga treecover2000 y lossyear, asi que
                             esta capa suele no estar en disco. Su papel
                             es descartar agua permanente, y el umbral
                             de dosel ya lo hace: un cuerpo de agua
                             tiene 0 % de cobertura arborea en 2000 y no
                             pasa el primer filtro. Se aplica si los
                             granulos estan, y si no, se avisa y se
                             sigue.

    Se reutiliza zonal.reproyectar_sobre_bloque(), la misma funcion que
    usa el panel nacional: la demo no reimplementa la geometria del
    reparto, la hereda.
    """
    def granulos(capa: str, obligatoria: bool = True) -> List[Path]:
        g = sorted(DIR_HANSEN.glob(f"Hansen_*_{capa}_*.tif"))
        if not g and obligatoria:
            raise SystemExit(
                f"No hay granulos de {capa} en {DIR_HANSEN}.\n"
                f"  python main_local.py hansen")
        return g

    dosel = reproyectar_sobre_bloque(granulos("treecover2000"), perfil)
    perdida = reproyectar_sobre_bloque(granulos("lossyear"), perfil)
    previa = (perdida >= 1) & (perdida <= ANIO_CORTE_PERDIDA)
    bosque = (dosel >= UMBRAL_DOSEL) & ~previa

    g_dm = granulos("datamask", obligatoria=False)
    if g_dm:
        bosque &= reproyectar_sobre_bloque(g_dm, perfil) == 1
        logger.info("  datamask aplicado")
    else:
        logger.info("  datamask no esta en disco; se omite. El umbral de dosel "
                    "ya excluye el agua permanente (0 %% de cobertura en 2000).")
    return bosque


# =====================================================================
# 4. GLAD-L, DESDE EL DATA-LAKE DE GFW
# =====================================================================
def _api_key() -> str:
    """La misma credencial que usa descargar_gfw.py."""
    k = os.environ.get("GFW_API_KEY")
    if k:
        return k.strip()
    archivo = DIR_LOG / "gfw_api_key.txt"
    if archivo.exists():
        return archivo.read_text().strip()
    raise SystemExit(
        "Falta la API key de GFW.\n"
        "  python configurar_gfw.py signup --nombre \"...\" --email ...\n"
        "  python configurar_gfw.py apikey --email ... --password ...")


def _version_glad(clave: str, intentos: int = 3, espera_s: int = 10) -> str:
    """
    Version vigente de GLAD-L, reintentando ante respuestas incompletas.

    El endpoint /latest puede responder 200 con un cuerpo sin el campo
    "data" mientras GFW publica una version nueva del dataset. Dura poco
    y se resuelve solo, pero antes reventaba con un KeyError sin
    explicacion. Aqui se separa ese caso de los que NO se arreglan
    reintentando -- una key invalida, por ejemplo -- y solo se reintenta
    cuando tiene sentido hacerlo.
    """
    u = f"{GFW_API}/dataset/{GLAD_DATASET}/latest"
    motivo = "sin intentos"
    for intento in range(1, intentos + 1):
        try:
            r = requests.get(u, headers={"x-api-key": clave},
                             timeout=TIEMPO_ESPERA)
        except requests.RequestException as e:
            motivo = f"no hubo respuesta del servidor ({e})"
        else:
            if r.status_code in (401, 403):
                raise SystemExit(
                    f"GFW rechazo la API key (HTTP {r.status_code}).\n"
                    "  Renuevela con:\n"
                    "  python configurar_gfw.py apikey "
                    "--email ... --password ...")
            if r.status_code != 200:
                motivo = f"HTTP {r.status_code}"
            else:
                try:
                    return r.json()["data"]["version"]
                except (ValueError, KeyError, TypeError):
                    motivo = ("respuesta 200 sin el campo data.version; "
                              "GFW suele estar publicando una version nueva")

        if intento < intentos:
            logger.warning("  no se pudo resolver la version (%s); "
                           "reintento %d de %d en %d s",
                           motivo, intento, intentos - 1, espera_s)
            time.sleep(espera_s)

    raise SystemExit(
        f"No se pudo resolver la version de {GLAD_DATASET} tras "
        f"{intentos} intentos.\n"
        f"  Ultimo motivo: {motivo}\n"
        "  Si fue una respuesta incompleta, suele bastar con volver a "
        "correr en unos minutos.")


def _url_glad(clave: str) -> str:
    """
    URL firmada del raster date_conf de GLAD-L.

    El bucket de GFW es "Requester Pays": una descarga anonima falla con
    AccessDenied. Hay que pasar por el endpoint de la API con la key,
    que responde 307 hacia una URL de S3 ya firmada.
    """
    v = _version_glad(clave)

    u = (f"{GFW_API}/dataset/{GLAD_DATASET}/{v}/download/geotiff"
         f"?grid=10/100000&tile_id={GLAD_TILE}&pixel_meaning=date_conf")
    r = requests.get(u, headers={"x-api-key": clave},
                     allow_redirects=False, timeout=TIEMPO_ESPERA)
    if r.status_code != 307 or "Location" not in r.headers:
        raise SystemExit(
            f"El endpoint de descarga de GLAD-L respondio {r.status_code}, "
            f"se esperaba 307 con redireccion.\n  {r.text[:200]}")
    logger.info("  GLAD-L version %s, tesela %s", v, GLAD_TILE)
    return r.headers["Location"]


def alertas_glad(perfil: dict, clave: str) -> np.ndarray:
    """
    Alertas GLAD-L confirmadas dentro de la ventana T1-T2, sobre la
    rejilla de trabajo.

    CODIFICACION de la banda date_conf: el valor empaqueta dos cosas,
    confianza y fecha, como conf * 10000 + dias desde GLAD_EPOCA. Se
    verifica empiricamente al leer -- se imprimen los codigos de
    confianza y el rango de fechas observados-- en vez de darla por
    supuesta: un desajuste aqui produciria un resultado vacio, que es el
    modo de falla mas dificil de detectar.
    """
    url = _url_glad(clave)
    os.environ["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY_DIR"

    tr = perfil["transform"]
    izq, arriba = tr.c, tr.f
    der = izq + tr.a * perfil["width"]
    abajo = arriba + tr.e * perfil["height"]
    destino = np.zeros((perfil["height"], perfil["width"]), dtype=np.uint16)

    try:
        with rasterio.open(f"/vsicurl/{url}") as src:
            b = transform_bounds(perfil["crs"], src.crs, izq, abajo, der, arriba,
                                 densify_pts=21)
            ven = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
            datos = src.read(1, window=ven)
            reproject(source=datos, destination=destino,
                      src_transform=src.window_transform(ven), src_crs=src.crs,
                      dst_transform=tr, dst_crs=perfil["crs"],
                      resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
    except Exception as e:
        raise SystemExit(f"No se pudo leer el raster de GLAD-L:\n  {e}")

    con_dato = destino > 0
    if not con_dato.any():
        raise SystemExit(
            "El raster de GLAD-L no trae ninguna alerta sobre la zona piloto. "
            "Revise GLAD_TILE y BBOX.")

    conf = (destino // 10000).astype(np.uint8)
    dias = (destino % 10000).astype(np.int32)
    d_min, d_max = int(dias[con_dato].min()), int(dias[con_dato].max())
    logger.info("  codigos de confianza observados: %s",
                sorted(np.unique(conf[con_dato]).tolist()))
    logger.info("  rango de fechas: %s a %s",
                GLAD_EPOCA + dt.timedelta(days=d_min),
                GLAD_EPOCA + dt.timedelta(days=d_max))

    desde = (GLAD_DESDE - GLAD_EPOCA).days
    hasta = (GLAD_HASTA - GLAD_EPOCA).days
    if d_max < desde or d_min > hasta:
        raise SystemExit(
            f"Las alertas disponibles ({GLAD_EPOCA + dt.timedelta(days=d_min)} a "
            f"{GLAD_EPOCA + dt.timedelta(days=d_max)}) no cubren la ventana pedida "
            f"({GLAD_DESDE} a {GLAD_HASTA}). Ajuste T1/T2 o GLAD_DESDE/GLAD_HASTA.")

    return con_dato & (conf >= GLAD_CONF_MIN) & (dias >= desde) & (dias <= hasta)


# =====================================================================
# 5. DOMINIO
# =====================================================================
def construir_dominio(bosque, obs_t1, obs_t2) -> np.ndarray:
    """
    Dominio = bosque inicial CON al menos una observacion limpia en cada
    ventana.

    Es la decision metodologica mas importante del modulo. Un pixel de
    bosque tapado por nubes en T1 o en T2 no se puede evaluar: no se
    sabe si cambio. Tratarlo como "sin perdida" lo convertiria en un
    verdadero negativo gratuito, inflando la exactitud global y
    escondiendo el problema real, que es la falta de observacion.

    Al excluirlos, la metrica describe solo el terreno donde de verdad
    hubo con que mirar, y el porcentaje excluido pasa a ser un resultado
    que se reporta.
    """
    return bosque & (obs_t1 >= 1) & (obs_t2 >= 1)


def diagnostico_nubes(bosque, dominio, obs_t1, obs_t2) -> pd.DataFrame:
    """
    Cuanto bosque quedo observable, y con cuantas observaciones limpias.

    Se reportan DOS cosas distintas, y conviene no confundirlas:

      sin_datos_pct   bosque que quedo FUERA del dominio por no tener
                      ninguna observacion limpia en alguna de las dos
                      ventanas. Con tres meses de Landsat 8 y 9 este
                      numero suele ser cero, porque basta UNA observacion
                      para entrar.

      obs_p10 / mediana   cuantas observaciones limpias tuvo de verdad
                      cada pixel. Aqui es donde se ve el problema de
                      nubosidad: que la mediana sea de apenas unas pocas
                      escenas -- de las decenas disponibles-- significa
                      que la mayoria se descarto por nubes, y que el
                      compuesto descansa en muy pocas lecturas.

    Un pixel con una sola observacion limpia entra al dominio, pero su
    mediana es esa unica lectura: si venia contaminada y la mascara no la
    atrapo, el dNBR de ese pixel es ruido. Por eso el percentil 10 dice
    mas sobre la calidad del compuesto que el porcentaje excluido.
    """
    ha = (ESCALA_M ** 2) / 10_000.0
    b, d = int(bosque.sum()), int(dominio.sum())
    o1, o2 = obs_t1[bosque], obs_t2[bosque]
    return pd.DataFrame([{
        "bosque_inicial_ha": round(b * ha, 1),
        "con_obs_t1_ha": round(int((bosque & (obs_t1 >= 1)).sum()) * ha, 1),
        "con_obs_t2_ha": round(int((bosque & (obs_t2 >= 1)).sum()) * ha, 1),
        "dominio_ha": round(d * ha, 1),
        "sin_datos_ha": round((b - d) * ha, 1),
        "sin_datos_pct": round(100 * (b - d) / b, 2) if b else None,
        "obs_min_t1": int(o1.min()) if b else 0,
        "obs_p10_t1": int(np.percentile(o1, 10)) if b else 0,
        "obs_mediana_t1": int(np.median(o1)) if b else 0,
        "obs_max_t1": int(o1.max()) if b else 0,
        "obs_min_t2": int(o2.min()) if b else 0,
        "obs_p10_t2": int(np.percentile(o2, 10)) if b else 0,
        "obs_mediana_t2": int(np.median(o2)) if b else 0,
        "obs_max_t2": int(o2.max()) if b else 0,
        "pct_bosque_con_1_sola_obs": round(
            100 * float(((o1 == 1) | (o2 == 1)).mean()), 2) if b else None,
    }])


# =====================================================================
# 6. DETECCION Y FILTRO DE PARCHE
# =====================================================================
def filtrar_parches(binaria: np.ndarray) -> np.ndarray:
    """
    Conserva solo los pixeles que pertenecen a un parche de al menos
    PIXELES_MIN_PARCHE pixeles conectados, con vecindad de 8.

    La vecindad de 8 (y no de 4) importa: un claro alargado en diagonal
    -- una via de extraccion, por ejemplo-- se partiria en fragmentos
    sueltos con vecindad de 4 y se perderia entero al filtrar.
    """
    estructura = np.ones((3, 3), dtype=bool)          # 8 vecinos
    etiquetas, n = ndimage.label(binaria, structure=estructura)
    if n == 0:
        return np.zeros_like(binaria, dtype=bool)
    tam = np.bincount(etiquetas.ravel())
    tam[0] = 0                                        # el fondo no cuenta
    return np.isin(etiquetas, np.flatnonzero(tam >= PIXELES_MIN_PARCHE))


def perdida_propia(dnbr, dominio, umbral: float) -> np.ndarray:
    """Perdida derivada del dNBR: umbral, dominio y filtro de parche."""
    with np.errstate(invalid="ignore"):
        cruda = (dnbr > umbral) & dominio
    return filtrar_parches(cruda)


def perdida_glad(glad, dominio) -> np.ndarray:
    """
    Perdida segun GLAD-L, con EXACTAMENTE el mismo tratamiento que la
    propia: misma mascara de bosque y mismo dominio (ambos vienen dentro
    de 'dominio'), y el mismo filtro de area minima. El filtro de fecha
    ya se aplico al leer el raster.

    Sin esas igualaciones la comparacion mediria diferencias de encuadre.
    Un ejemplo concreto: GLAD-L alerta tambien fuera del bosque definido
    por Hansen, de modo que sin la mascara comun apareceria como
    "deteccion adicional" algo que la propia nunca pudo haber encontrado.
    """
    return filtrar_parches(glad & dominio)


# =====================================================================
# 7. METRICAS
# =====================================================================
def matriz_acuerdo(propia, glad, dominio, region) -> dict:
    """Hectareas en las cuatro combinaciones propia/GLAD dentro del dominio."""
    ha = (ESCALA_M ** 2) / 10_000.0
    d = dominio & region
    return {
        "ambos_ha": round(int((d & propia & glad).sum()) * ha, 1),
        "solo_propia_ha": round(int((d & propia & ~glad).sum()) * ha, 1),
        "solo_glad_ha": round(int((d & ~propia & glad).sum()) * ha, 1),
        "ninguno_ha": round(int((d & ~propia & ~glad).sum()) * ha, 1),
    }


def metricas(m: dict) -> dict:
    """
    Precision, sensibilidad y F1 tomando GLAD-L como referencia.

    ADVERTENCIA sobre la exactitud global: se incluye porque suele
    pedirse, pero NO es informativa aqui. El bosque estable domina la
    escena -- suele ser mas del 95 % del dominio--, asi que un detector
    que no marcara nada obtendria una exactitud altisima. Las metricas
    que si dicen algo son las tres primeras.

    "Referencia" tampoco significa "verdad": GLAD-L tiene sus propios
    errores. Lo que miden estas cifras es CONCORDANCIA con un producto
    publicado, no exactitud contra el terreno. Para eso esta la muestra
    de validacion visual.
    """
    vp, fp, fn, vn = (m["ambos_ha"], m["solo_propia_ha"],
                      m["solo_glad_ha"], m["ninguno_ha"])
    prec = vp / (vp + fp) if (vp + fp) else 0.0
    sens = vp / (vp + fn) if (vp + fn) else 0.0
    f1 = 2 * prec * sens / (prec + sens) if (prec + sens) else 0.0
    tot = vp + fp + fn + vn
    return {"precision": round(prec, 4), "sensibilidad": round(sens, 4),
            "f1": round(f1, 4),
            "exactitud_global_no_informativa": round((vp + vn) / tot, 4) if tot else 0.0}


def calibrar_umbral(dnbr, dominio, glad_p, oeste) -> pd.DataFrame:
    """
    Recorre los umbrales candidatos en la MITAD OESTE.

    La mitad oeste no vuelve a tocarse despues: el umbral elegido aqui
    se aplica tal cual sobre la mitad este, que el procedimiento no ha
    visto.
    """
    filas = []
    for u in UMBRALES_DNBR:
        p = perdida_propia(dnbr, dominio, u)
        m = matriz_acuerdo(p, glad_p, dominio, oeste)
        fila = {"umbral_dnbr": u, **m, **metricas(m)}
        filas.append(fila)
        logger.info("  umbral %.2f -> precision %.3f | sensibilidad %.3f | F1 %.3f",
                    u, fila["precision"], fila["sensibilidad"], fila["f1"])
    return pd.DataFrame(filas)


# =====================================================================
# 8. AGREGACION A CELDAS DE 5 KM
# =====================================================================
def curva_observabilidad(propia_fn, glad_raw, bosque, obs_t1, obs_t2,
                         region, umbral: float,
                         minimos=(1, 2, 3, 4, 6, 8, 10)) -> pd.DataFrame:
    """
    Concordancia contra GLAD-L segun cuantas observaciones limpias exija
    el dominio.

    El dominio de la demo pide al menos UNA observacion limpia en cada
    ventana. Subir esa barra deja fuera los pixeles peor observados, y
    la concordancia mejora: con 3 observaciones el F1 ronda 0,29 y con
    10 o mas llega a 0,69. Reportar un solo numero esconde eso.

    La curva se reporta entera porque el valor util depende de para que
    se use: quien necesite cobertura completa lee la primera fila, quien
    pueda restringirse a zonas bien observadas lee las de abajo.

    Se filtra por OBSERVABILIDAD (cuantas veces se pudo ver el pixel),
    nunca por resultado. Filtrar por resultado seria elegir los aciertos.

    Cuidado al leer las filas exigentes: el numero de observaciones lo
    manda la geometria orbital, y en esta zona el traslape entre orbitas
    cae en el sur. Pedir 10 observaciones equivale a quedarse con el
    tercio sur, asi que esa fila describe una region, no la zona. La
    columna cobertura_pct dice cuanta area queda, y reparto_ns cuan
    repartida esta entre el norte y el sur.
    """
    nobs = np.minimum(obs_t1, obs_t2)
    alto = bosque.shape[0]
    norte = np.zeros_like(bosque)
    norte[:alto // 2] = True
    ha = (ESCALA_M ** 2) / 10_000.0
    base = float((bosque & (nobs >= 1) & region).sum()) * ha

    filas = []
    for k in minimos:
        dom = bosque & (nobs >= k)
        gp = perdida_glad(glad_raw, dom)
        pp = propia_fn(dom, umbral)
        m = matriz_acuerdo(pp, gp, dom, region)
        sel = dom & region
        area = float(sel.sum()) * ha
        en_norte = float((sel & norte).sum()) * ha
        filas.append({
            "obs_minimas": k,
            "dominio_ha": round(area, 1),
            "cobertura_pct": round(100 * area / base, 1) if base else 0.0,
            "reparto_ns": round(100 * en_norte / area, 1) if area else 0.0,
            **m, **metricas(m),
        })
    return pd.DataFrame(filas)


def comparar_celdas(propia, glad, dominio, region, perfil) -> pd.DataFrame:
    """
    Hectareas perdidas por celda de 5 x 5 km, segun cada fuente.

    Es la comparacion mas relevante para este proyecto: el modelo
    predictivo trabaja a esa escala, no a nivel de pixel. Dos productos
    pueden discrepar pixel a pixel por medio pixel de desplazamiento y
    aun asi coincidir muy bien en cuanta perdida hay en cada celda, que
    es lo que el modelo necesita.

    El indice de celda sale por aritmetica directa sobre la rejilla
    proyectada -- floor(coord / LADO_CELDA_M)-- igual que en zonal.py.
    """
    tr = perfil["transform"]
    px_celda = LADO_CELDA_M // ESCALA_M
    filas = np.arange(perfil["height"])[:, None] // px_celda
    cols = np.arange(perfil["width"])[None, :] // px_celda
    idx = (filas * (perfil["width"] // px_celda + 1) + cols).astype(np.int64)

    ha = (ESCALA_M ** 2) / 10_000.0
    d = dominio & region
    n = idx.max() + 1
    cuenta = lambda m: np.bincount(idx[m], minlength=n) * ha    # noqa: E731

    df = pd.DataFrame({
        "celda": np.arange(n),
        "propia_ha": cuenta(d & propia),
        "glad_ha": cuenta(d & glad),
        "dominio_ha": cuenta(d),
    })
    # Centro de cada celda, en la rejilla proyectada y en lon/lat.
    f_c = (df.celda // (perfil["width"] // px_celda + 1)) * px_celda + px_celda / 2
    c_c = (df.celda % (perfil["width"] // px_celda + 1)) * px_celda + px_celda / 2
    x = tr.c + tr.a * c_c
    y = tr.f + tr.e * f_c
    lon, lat = rasterio.warp.transform(perfil["crs"], "EPSG:4326",
                                       x.tolist(), y.tolist())
    df["lon_centro"] = np.round(lon, 5)
    df["lat_centro"] = np.round(lat, 5)

    # Celdas sin dominio no aportan informacion: no es que coincidan en
    # cero, es que no habia donde mirar.
    df = df[df.dominio_ha > 0].copy()
    for c in ("propia_ha", "glad_ha", "dominio_ha"):
        df[c] = df[c].round(3)
    return df[["celda", "lon_centro", "lat_centro",
               "propia_ha", "glad_ha", "dominio_ha"]].reset_index(drop=True)


# =====================================================================
# 9. MUESTRA PARA VALIDACION VISUAL
# =====================================================================
def muestra_estratificada(propia, glad, dominio, region, perfil) -> pd.DataFrame:
    """
    Muestra estratificada sobre las cuatro combinaciones propia/GLAD,
    siguiendo la practica recomendada para estimacion de area y
    exactitud (Olofsson et al., 2014).

    El muestreo es ESTRATIFICADO y no aleatorio simple por una razon
    concreta: las clases de cambio ocupan una fraccion minuscula de la
    escena, asi que una muestra aleatoria simple caeria casi entera en
    bosque estable y dejaria los desacuerdos -- que son justo lo que hay
    que revisar-- con un punado de puntos o ninguno.

    La columna etiqueta_visual sale vacia a proposito: la interpreta un
    humano sobre imagen de alta resolucion, y de ahi salen los errores
    de omision y comision que permiten corregir el area estimada.
    """
    rng = np.random.default_rng(SEMILLA)
    d = dominio & region
    estratos = {
        "ambos": d & propia & glad,
        "solo_propia": d & propia & ~glad,
        "solo_glad": d & ~propia & glad,
        "ninguno": d & ~propia & ~glad,
    }
    tr = perfil["transform"]
    filas = []
    for nombre, m in estratos.items():
        f, c = np.nonzero(m)
        if len(f) == 0:
            logger.warning("  estrato '%s' vacio: no se puede muestrear", nombre)
            continue
        k = min(PUNTOS_POR_ESTRATO, len(f))
        if k < PUNTOS_POR_ESTRATO:
            logger.warning("  estrato '%s': solo %d pixeles disponibles", nombre, k)
        sel = rng.choice(len(f), size=k, replace=False)
        # Centro del pixel, no su esquina.
        x = tr.c + tr.a * (c[sel] + 0.5)
        y = tr.f + tr.e * (f[sel] + 0.5)
        lon, lat = rasterio.warp.transform(perfil["crs"], "EPSG:4326",
                                           x.tolist(), y.tolist())
        filas.append(pd.DataFrame({"lon": np.round(lon, 6),
                                   "lat": np.round(lat, 6),
                                   "estrato": nombre,
                                   "etiqueta_visual": ""}))
    return pd.concat(filas, ignore_index=True) if filas else pd.DataFrame()


# =====================================================================
# 10. MAPA DE REVISION
# =====================================================================
def _png(ruta: Path, rgb: np.ndarray) -> None:
    """Guarda un array RGBA como PNG, sin dependencias nuevas."""
    import matplotlib.pyplot as plt
    plt.imsave(str(ruta), rgb)


def mapa_revision(capas: Dict[str, np.ndarray], perfil: dict,
                  destino: Path) -> bool:
    """
    Mapa interactivo con las capas que permiten revisar visualmente cada
    deteccion.

    Se usa folium y no geemap porque el resto del repositorio ya lo usa
    (mapa_folium.py) y porque no exige Earth Engine. Las capas raster se
    superponen como PNG georreferenciados, que es lo que folium admite
    sin un servidor de teselas detras.
    """
    try:
        import folium
        from folium.plugins import Fullscreen
        from mapa_folium import TILES_DEFECTO, atenuar_mapa_base
    except ImportError as e:
        logger.warning("No se pudo armar el mapa (%s); se omite.", e)
        return False

    izq, abajo, der, arriba = perfil["bounds"]
    o, s, e, n = transform_bounds(perfil["crs"], "EPSG:4326",
                                  izq, abajo, der, arriba, densify_pts=21)
    limites = [[s, o], [n, e]]

    m = folium.Map(location=[(s + n) / 2, (o + e) / 2], zoom_start=10,
                   tiles=TILES_DEFECTO, control_scale=True)
    atenuar_mapa_base(m)

    dir_png = destino.parent
    colores = {
        "bosque": (30, 107, 69),        # verde bosque
        "sin_datos": (154, 165, 160),   # gris
        "glad": (59, 53, 166),          # indigo, igual que en el catalogo
        "propia": (184, 86, 45),        # naranja
    }
    encendida = {"propia": True, "glad": True}
    for nombre, color in colores.items():
        m_ = capas[nombre]
        if not m_.any():
            continue
        rgba = np.zeros((*m_.shape, 4), dtype=np.uint8)
        rgba[m_, :3] = color
        rgba[m_, 3] = 200
        ruta = dir_png / f"capa_{nombre}.png"
        _png(ruta, rgba)
        # Se pasa la ruta COMPLETA, no el nombre: folium abre el archivo
        # para incrustarlo en base64 dentro del HTML, y con el nombre
        # suelto lo buscaria en el directorio de trabajo. El HTML queda
        # autonomo, y los PNG sirven ademas para abrirlos en un SIG.
        folium.raster_layers.ImageOverlay(
            image=str(ruta), bounds=limites, opacity=0.75,
            name={"bosque": "Bosque inicial", "sin_datos": "Sin datos (nubes)",
                  "glad": "Perdida GLAD-L", "propia": "Perdida propia"}[nombre],
            show=encendida.get(nombre, False)).add_to(m)

    folium.Rectangle(limites, color="#16211C", weight=2, fill=False,
                     name="Zona piloto").add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    Fullscreen(position="topleft").add_to(m)
    m.save(str(destino))
    return True


# =====================================================================
# 11. ORQUESTADOR
# =====================================================================
def main() -> int:
    """
    Corre la demo completa y escribe las salidas en datos/demo/.

    El orden no es arbitrario: primero se resuelven los insumos -- bosque,
    escenas, GLAD-L-- porque cualquiera de los tres puede faltar y
    descubrirlo al final costaria toda la corrida. Despues el
    diagnostico de nubes, que define el dominio sobre el que todo lo
    demas se mide. Y solo entonces calibracion, validacion y muestreo.
    """
    DIR_DEMO.mkdir(parents=True, exist_ok=True)
    try:
        perfil = perfil_zona()
        oeste, este = mascara_mitades(perfil)
        logger.info("=" * 62)
        logger.info("ZONA PILOTO")
        logger.info("  bbox    : %s", BBOX)
        logger.info("  rejilla : %d x %d px de %d m (%s)",
                    perfil["width"], perfil["height"], ESCALA_M, CRS)

        # --- bosque inicial ---------------------------------------------
        logger.info("=" * 62)
        logger.info("BOSQUE INICIAL (granulos locales de Hansen)")
        bosque = mascara_bosque(perfil)
        ha = (ESCALA_M ** 2) / 10_000.0
        logger.info("  %d px = %.1f ha", int(bosque.sum()), bosque.sum() * ha)

        # --- Landsat -----------------------------------------------------
        logger.info("=" * 62)
        logger.info("ESCENAS LANDSAT (catalogo STAC, lectura por ventana)")
        nbr_t1, obs_t1, nbr_t2, obs_t2 = compuestos_con_cache(perfil)
        dnbr = nbr_t1 - nbr_t2

        # --- dominio ------------------------------------------------------
        dominio = construir_dominio(bosque, obs_t1, obs_t2)
        logger.info("=" * 62)
        logger.info("DIAGNOSTICO DE NUBES")
        diag = diagnostico_nubes(bosque, dominio, obs_t1, obs_t2)
        diag.to_csv(DIR_DEMO / "diagnostico_nubes.csv", index=False)
        f = diag.iloc[0]
        logger.info("  bosque inicial : %10.1f ha", f.bosque_inicial_ha)
        logger.info("  dominio        : %10.1f ha", f.dominio_ha)
        logger.info("  sin datos      : %10.1f ha  (%.2f %% del bosque)",
                    f.sin_datos_ha, f.sin_datos_pct)
        logger.info("  observaciones limpias por pixel (mediana): T1=%d, T2=%d",
                    f.obs_mediana_t1, f.obs_mediana_t2)
        if dominio.sum() == 0:
            raise SystemExit("El dominio quedo vacio: no hay bosque con "
                             "observaciones limpias en ambas ventanas.")

        # --- GLAD-L -------------------------------------------------------
        logger.info("=" * 62)
        logger.info("ALERTAS GLAD-L (data-lake de GFW)")
        glad_bruta = alertas_glad(perfil, _api_key())
        glad_p = perdida_glad(glad_bruta, dominio)
        logger.info("  en ventana y dominio: %.1f ha", glad_p.sum() * ha)

        # --- calibracion --------------------------------------------------
        logger.info("=" * 62)
        logger.info("CALIBRACION DEL UMBRAL (mitad OESTE)")
        cal = calibrar_umbral(dnbr, dominio, glad_p, oeste)
        cal.to_csv(DIR_DEMO / "calibracion_umbral.csv", index=False)
        mejor = float(cal.loc[cal.f1.idxmax(), "umbral_dnbr"])
        logger.info("  umbral elegido por F1: %.2f", mejor)

        # --- validacion ---------------------------------------------------
        logger.info("=" * 62)
        logger.info("VALIDACION (mitad ESTE, no vista en la calibracion)")
        propia = perdida_propia(dnbr, dominio, mejor)
        m = matriz_acuerdo(propia, glad_p, dominio, este)
        ev = pd.DataFrame([{"umbral_dnbr": mejor, **m, **metricas(m)}])
        ev.to_csv(DIR_DEMO / "evaluacion_validacion.csv", index=False)
        e = ev.iloc[0]
        logger.info("  ambos        : %9.1f ha", e.ambos_ha)
        logger.info("  solo propia  : %9.1f ha", e.solo_propia_ha)
        logger.info("  solo GLAD-L  : %9.1f ha", e.solo_glad_ha)
        logger.info("  ninguno      : %9.1f ha", e.ninguno_ha)
        logger.info("  precision %.3f | sensibilidad %.3f | F1 %.3f",
                    e.precision, e.sensibilidad, e.f1)
        logger.info("  (exactitud global %.4f -- no informativa, ver docstring)",
                    e.exactitud_global_no_informativa)

        # --- curva de observabilidad ---------------------------------------
        logger.info("=" * 62)
        logger.info("CONCORDANCIA SEGUN OBSERVACIONES EXIGIDAS (mitad ESTE)")
        curva = curva_observabilidad(
            lambda dom, u: perdida_propia(dnbr, dom, u),
            glad_bruta, bosque, obs_t1, obs_t2, este, mejor)
        curva.to_csv(DIR_DEMO / "curva_observabilidad.csv", index=False)
        logger.info("  obs  cobertura   norte   precision  sensib      F1")
        for _, f in curva.iterrows():
            logger.info("  %3d %8.1f%% %6.1f%% %10.3f %7.3f %7.3f",
                        f.obs_minimas, f.cobertura_pct, f.reparto_ns,
                        f.precision, f.sensibilidad, f.f1)

        # --- celdas de 5 km ------------------------------------------------
        logger.info("=" * 62)
        logger.info("COMPARACION POR CELDA DE 5 KM (mitad ESTE)")
        celdas = comparar_celdas(propia, glad_p, dominio, este, perfil)
        celdas.to_csv(DIR_DEMO / "comparacion_celdas.csv", index=False)
        if len(celdas) >= 3:
            rp = celdas.propia_ha.corr(celdas.glad_ha, method="pearson")
            rs = celdas.propia_ha.corr(celdas.glad_ha, method="spearman")
            logger.info("  celdas con dominio: %d", len(celdas))
            logger.info("  Pearson  r = %.3f", rp)
            logger.info("  Spearman r = %.3f", rs)
        else:
            logger.warning("  muy pocas celdas (%d) para correlacionar", len(celdas))

        # --- muestra --------------------------------------------------------
        logger.info("=" * 62)
        logger.info("MUESTRA PARA VALIDACION VISUAL")
        muestra = muestra_estratificada(propia, glad_p, dominio, este, perfil)
        muestra.to_csv(DIR_DEMO / "muestra_validacion_visual.csv", index=False)
        logger.info("  %d puntos", len(muestra))
        for k, v in muestra.estrato.value_counts().items():
            logger.info("    %-12s %3d", k, v)

        # --- mapa -----------------------------------------------------------
        logger.info("=" * 62)
        logger.info("MAPA DE REVISION")
        destino = DIR_DEMO / "mapa_revision.html"
        if mapa_revision({"bosque": bosque, "sin_datos": bosque & ~dominio,
                          "propia": propia, "glad": glad_p}, perfil, destino):
            logger.info("  %s", destino)

        logger.info("=" * 62)
        logger.info("DEMO COMPLETA. Salidas en %s", DIR_DEMO)
        logger.info("=" * 62)
        return 0

    except SystemExit:
        raise
    except MemoryError:
        logger.error("Sin memoria. Reduzca BBOX o FILAS_POR_FRANJA.")
        return 1
    except Exception as e:
        logger.error("Fallo la demo (%s): %s", type(e).__name__, e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
