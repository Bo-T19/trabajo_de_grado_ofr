"""
consolidar.py
======================================================================
Convierte el CSV ANCHO que produce zonal_local.py en el panel
espacio-temporal final (formato LARGO) listo para modelar.

    ANCHO (como sale de zonal_local.py)
    cell_id | departamento | bosque_ha | d_2023_01 | d_2023_02 | ...
    A1      | Caqueta      | 2100      | 0.0       | 3.6       | ...

    LARGO (lo que necesita el modelo)
    cell_id | periodo    | area_def_ha | bosque_remanente_ha | ...
    A1      | 2023-01-01 | 0.0         | 2100.0              | ...
    A1      | 2023-02-01 | 3.6         | 2100.0              | ...

Calcula ademas las variables derivadas que requieren memoria temporal
por celda: perdida acumulada, bosque remanente y rezagos.

CAMBIO respecto a la version con Earth Engine: la columna
'departamento' ya viene en el CSV (la trae la grilla), no se deduce
del nombre del archivo.
======================================================================
"""
from __future__ import annotations

import glob
from pathlib import Path
from typing import Optional

import pandas as pd

from config_local import Config, DIR_CRUDO, DIR_PANEL, logger


# =====================================================================
# 1. LECTURA Y CAMBIO DE FORMA
# =====================================================================
def cargar_crudo(cfg: Config) -> pd.DataFrame:
    """Une los CSV de datos/crudo/ y los pasa de ancho a largo.

    En principio solo hay un archivo (nacional.csv de zonal_local.py),
    pero la funcion admite varios por si se procesaron tiles o regiones
    por separado (de ahi el glob + concat). El filtro "__p" excluye
    archivos de piezas/particiones intermedias, si las hubiera.
    """
    archivos = sorted(glob.glob(str(DIR_CRUDO / "*.csv")))
    archivos = [a for a in archivos if "__p" not in Path(a).name]
    if not archivos:
        raise FileNotFoundError(
            f"No hay CSV en {DIR_CRUDO}. Ejecute primero:\n"
            f"  python main_local.py zonal")

    logger.info("Leyendo %d archivo(s)...", len(archivos))
    piezas = []
    for a in archivos:
        df = pd.read_csv(a)
        # El pipeline local ya trae la columna; el antiguo la deducia
        # del nombre del archivo. Se respeta la que exista.
        if "departamento" not in df.columns:
            df["departamento"] = Path(a).stem.replace("_", " ")
        df["departamento"] = df["departamento"].fillna("Sin asignar")
        piezas.append(df)

    ancho = pd.concat(piezas, ignore_index=True)
    logger.info("Celdas leidas: %d", len(ancho))

    # Columnas "d_2023_01", "d_2023_02", ... son las que traen la
    # deforestacion mes a mes en formato ancho.
    cols_periodo = [c for c in ancho.columns if c.startswith("d_")]
    if not cols_periodo:
        raise ValueError("Ningun archivo tiene columnas de periodo (d_YYYY_MM).")

    # pandas.melt: convierte cada columna de periodo en filas nuevas,
    # repitiendo los metadatos de la celda (id_vars) en cada una.
    # Ejemplo: una fila con d_2023_01=0.0, d_2023_02=3.6 se vuelve dos
    # filas: (periodo=2023-01, area_def_ha=0.0) y (periodo=2023-02,
    # area_def_ha=3.6). Esta es la forma "larga" que necesita cualquier
    # modelo de panel (una observacion por fila).
    largo = ancho.melt(
        id_vars=["cell_id", "lon", "lat", "bosque_ha", "departamento"],
        value_vars=cols_periodo,
        var_name="periodo", value_name="area_def_ha",
    )
    # "d_2023_01" -> "2023_01" -> Timestamp(2023-01-01)
    largo["periodo"] = pd.to_datetime(
        largo["periodo"].str.replace("d_", "", regex=False), format="%Y_%m")
    # errors="coerce": cualquier valor no numerico se vuelve NaN, y
    # luego se rellena con 0 (sin deforestacion registrada = 0 ha).
    largo["area_def_ha"] = pd.to_numeric(
        largo["area_def_ha"], errors="coerce").fillna(0.0)

    return largo.rename(columns={"bosque_ha": "bosque_base_ha"})


# =====================================================================
# 2. FILTRO DE DOMINIO
# =====================================================================
def filtrar_dominio(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """
    Elimina las celdas sin bosque suficiente.

    Una celda de paramo o sabana no puede deforestarse. Incluirla aporta
    un cero estructural que infla el desbalance de clases y degrada las
    metricas del modelo sin aportar informacion.
    """
    antes = df["cell_id"].nunique()
    df = df[df["bosque_base_ha"] >= cfg.bosque_minimo_ha].copy()
    logger.info("Celdas con bosque >= %.0f ha: %d de %d",
                cfg.bosque_minimo_ha, df["cell_id"].nunique(), antes)
    return df


# =====================================================================
# 3. BALANCEO DEL PANEL
# =====================================================================
def balancear(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garantiza que toda celda tenga una fila en TODO periodo.

    Un panel desbalanceado sesga cualquier modelo temporal: los meses
    sin alerta desaparecerian y el modelo no aprenderia la probabilidad
    base del evento.
    """
    # Metadatos fijos por celda (no cambian mes a mes): se guardan
    # aparte para poder re-unirlos despues de reindexar.
    llaves = df.groupby("cell_id")[
        ["lon", "lat", "bosque_base_ha", "departamento"]].first()
    # Todas las combinaciones posibles de (celda, periodo), aunque esa
    # combinacion no exista todavia en 'df'.
    idx = pd.MultiIndex.from_product(
        [sorted(df["cell_id"].unique()), sorted(df["periodo"].unique())],
        names=["cell_id", "periodo"])

    # reindex(idx): expande el DataFrame a TODAS las combinaciones de
    # 'idx'; las que no existian quedan con area_def_ha = NaN, que se
    # rellena con 0.0 (mes sin evento registrado). Luego se reincorporan
    # los metadatos de la celda (join) que se habian guardado aparte.
    out = (df.set_index(["cell_id", "periodo"])[["area_def_ha"]]
             .reindex(idx)
             .fillna({"area_def_ha": 0.0})
             .join(llaves, on="cell_id")
             .reset_index()
             .sort_values(["cell_id", "periodo"]))
    logger.info("Panel balanceado: %d filas", len(out))
    return out


# =====================================================================
# 4. VARIABLES DERIVADAS
# =====================================================================
def derivar_variables(df: pd.DataFrame, n_rezagos: int = 3) -> pd.DataFrame:
    """
    Calcula exposicion, targets y rezagos.

    bosque_remanente_ha
        Bosque disponible AL INICIO del periodo. Es el denominador
        correcto. Sin esta variable el modelo aprende la trivialidad
        "donde hay mas bosque hay mas deforestacion" y las celdas ya
        agotadas contaminan la muestra.

    tasa_def   target continuo, normalizado por exposicion.
    evento     target binario, para la etapa de clasificacion de un
               modelo hurdle / zero-inflated.
    lag_k      deforestacion k periodos atras en la misma celda.
    """
    # Orden cronologico por celda: obligatorio antes de cualquier
    # cumsum/shift/rolling, porque esas operaciones asumen que las
    # filas ya estan en el orden temporal correcto.
    df = df.sort_values(["cell_id", "periodo"]).copy()

    # El groupby se reconstruye despues de cada columna nueva: depender
    # de un objeto groupby creado antes de anadir la columna es fragil.
    # def_acum_ha: suma acumulada de deforestacion, celda por celda,
    # mes a mes (cumsum reinicia en cada grupo/celda).
    df["def_acum_ha"] = df.groupby("cell_id", sort=False)["area_def_ha"].cumsum()

    # 'previo' = la perdida acumulada HASTA EL PERIODO ANTERIOR (shift
    # 1 posicion hacia adelante = "un mes atras"). El primer mes de cada
    # celda no tiene anterior, por eso fillna(0).
    previo = df.groupby("cell_id", sort=False)["def_acum_ha"].shift(1).fillna(0)
    # bosque_remanente_ha = bosque original menos lo ya perdido antes de
    # este periodo. clip(lower=0): nunca puede ser negativo (protege
    # contra redondeos o inconsistencias minimas de los datos).
    df["bosque_remanente_ha"] = (df["bosque_base_ha"] - previo).clip(lower=0)

    # tasa_def: deforestacion de este mes, como fraccion del bosque
    # que quedaba disponible al empezar el mes. replace(0, pd.NA) evita
    # dividir por cero (celda sin bosque remanente): esos casos
    # terminan en NaN y luego se fuerzan a 0 con fillna. clip(upper=1)
    # acota la tasa a maximo 100%, por seguridad numerica.
    df["tasa_def"] = (df["area_def_ha"]
                      / df["bosque_remanente_ha"].replace(0, pd.NA))
    df["tasa_def"] = df["tasa_def"].fillna(0).clip(upper=1)
    # evento: target binario (1 si hubo algo de deforestacion, 0 si no).
    df["evento"] = (df["area_def_ha"] > 0).astype("int8")

    # Rezagos (lag_1_ha, lag_2_ha, lag_3_ha): deforestacion de k meses
    # atras, en la MISMA celda. Sirven como variables predictoras: la
    # deforestacion reciente suele ser buen predictor de la futura.
    g = df.groupby("cell_id", sort=False)["area_def_ha"]
    for k in range(1, n_rezagos + 1):
        df[f"lag_{k}_ha"] = g.shift(k)
    # Promedio movil de los 3 meses ANTERIORES (shift(1) excluye el mes
    # actual, para no usar informacion del propio periodo que se quiere
    # predecir/explicar).
    df["media_movil_3"] = g.transform(lambda s: s.shift(1).rolling(3).mean())

    df["anio"] = df["periodo"].dt.year
    df["mes"] = df["periodo"].dt.month
    return df


# =====================================================================
# 5. CRUCE CON LA CARTOGRAFIA DANE (opcional)
# =====================================================================
def asignar_municipio(df: pd.DataFrame, ruta_shp: Optional[str]) -> pd.DataFrame:
    """
    Asigna codigo DANE de municipio a cada celda mediante su centroide.

    Requiere el Marco Geoestadistico Nacional (MGN) del DANE, que trae
    el campo MPIO_CDPMP: la llave para unir variables socioeconomicas
    y de credito rural del Observatorio.

    Solo este paso necesita geopandas. Es opcional: sin shapefile el
    panel se construye igual, sin la columna cod_dane.
    """
    if not ruta_shp:
        logger.info("Sin shapefile DANE; se omite la asignacion municipal.")
        return df
    try:
        import geopandas as gpd
    except ImportError:
        logger.warning("geopandas no esta instalado; se omite el cruce DANE.")
        return df

    mgn = gpd.read_file(ruta_shp).to_crs("EPSG:4326")
    celdas = df[["cell_id", "lon", "lat"]].drop_duplicates("cell_id")
    pts = gpd.GeoDataFrame(
        celdas, geometry=gpd.points_from_xy(celdas.lon, celdas.lat),
        crs="EPSG:4326")

    campo = next((c for c in ("MPIO_CDPMP", "MPIO_CCNCT", "mpio_cdpmp")
                  if c in mgn.columns), None)
    if campo is None:
        logger.warning("No se hallo el campo de codigo DANE en el shapefile.")
        return df

    unido = gpd.sjoin(pts, mgn[[campo, "geometry"]],
                      how="left", predicate="within")
    mapa = unido.set_index("cell_id")[campo].rename("cod_dane")
    logger.info("Municipio asignado a %d celdas.", mapa.notna().sum())
    return df.merge(mapa, on="cell_id", how="left")


# =====================================================================
# 6. PIPELINE COMPLETO
# =====================================================================
def consolidar(cfg: Config, ruta_shp_dane: Optional[str] = None) -> pd.DataFrame:
    """Ejecuta las cinco etapas y guarda el panel en disco.

    Orden importa: cada etapa depende de que la anterior ya se haya
    aplicado (cargar -> filtrar -> balancear -> derivar -> asignar
    municipio). Ver las secciones 1-5 de este archivo para el detalle
    de cada una.
    """
    df = cargar_crudo(cfg)
    df = filtrar_dominio(df, cfg)
    df = balancear(df)
    df = derivar_variables(df)
    df = asignar_municipio(df, ruta_shp_dane)

    csv = DIR_PANEL / "panel_deforestacion_colombia.csv"
    parquet = DIR_PANEL / "panel_deforestacion_colombia.parquet"
    df.to_csv(csv, index=False)
    try:
        # Parquet es opcional (requiere pyarrow, que si esta en
        # requirements_local.txt): mas liviano que CSV y preserva
        # tipos de dato exactos (fechas, enteros vs. flotantes), util
        # si el analisis posterior sigue en pandas/Python.
        df.to_parquet(parquet, index=False)
    except Exception as exc:
        logger.warning("No se pudo escribir Parquet (%s).", exc)

    logger.info("=" * 62)
    logger.info("PANEL FINAL")
    logger.info("  filas          : %d", len(df))
    logger.info("  celdas         : %d", df["cell_id"].nunique())
    logger.info("  periodos       : %d", df["periodo"].nunique())
    logger.info("  rango          : %s a %s",
                df["periodo"].min().date(), df["periodo"].max().date())
    logger.info("  %% con evento    : %.3f%%", 100 * df["evento"].mean())
    logger.info("  bosque total   : %.0f ha",
                df.groupby("cell_id")["bosque_base_ha"].first().sum())
    logger.info("  deforestacion  : %.0f ha", df["area_def_ha"].sum())
    logger.info("  archivo        : %s", csv)
    logger.info("=" * 62)
    return df
