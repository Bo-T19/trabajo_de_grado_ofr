"""
panel_dtd.py
======================================================================
TABLA 4 de 4: alertas tempranas oficiales por celda y trimestre, segun
las Detecciones Tempranas de Deforestacion (DTD) del SMByC (IDEAM).

    python main_local.py panel-dtd

Salida: datos/panel/panel_dtd.csv (+ .parquet)

    cell_id | periodo | trimestre | n_alertas | n_alertas_sinap |
            | bosque_base_ha | cod_dane | ...

QUE MIDE
--------
El NUMERO DE PUNTOS DE ALERTA que el IDEAM publico para esa celda en ese
trimestre.

LOS DATOS SON PUNTOS, SIN SUPERFICIE ASOCIADA. Cada registro marca un
sitio donde el instituto detecto un cambio compatible con deforestacion,
y no trae extension: no hay campo de area, y el campo "count" vale
siempre 1. Se verifico en las tres distribuciones que publica el SMByC
para este producto:

    Puntos/  .kml   puntos, sin campo de area           <- lo que se usa
    Nucleos/ .kmz   una imagen superpuesta (PNG mas un
                    rectangulo), no poligonos vectoriales
    Nucleos/ .tif   raster de DENSIDAD: conteos por celda
                    de 2.500 m en EPSG:32618

Ninguna de las tres permite derivar hectareas. La magnitud en superficie
la dan panel_ideam.py (oficial, anual) y el panel de alertas de GFW
(mensual).

Por eso esta tabla se lee junto a las otras tres, y no en lugar de
ellas: aporta el POSICIONAMIENTO OFICIAL sobre donde esta ocurriendo el
fenomeno, con cadencia trimestral. La magnitud en hectareas la dan
panel_ideam.py (oficial, anual) y el panel de alertas de GFW (mensual).

QUE APORTA AL PROYECTO
----------------------
Es el unico producto OFICIAL de cadencia sub-anual disponible para
Colombia:

  panel de alertas GFW  -> mensual, no oficial
  panel_ideam           -> oficial, anual
  panel_dtd             -> oficial, trimestral

Ademas cubre las cinco regiones naturales del pais (Amazonica, Andina,
Pacifica, Orinoquia y Caribe), de modo que sirve tambien en la zona
andina, donde se producen los cultivos relevantes para la regulacion
europea de importaciones.

Cada punto trae atributos que ningun raster entrega: municipio, vereda,
corporacion autonoma regional y area protegida del SINAP. De ahi la
columna n_alertas_sinap, y la columna sinap_disponible que indica en que
trimestres ese dato viene informado (18 de 25).

LA CIFRA DE ALERTAS Y LA TASA OFICIAL SON COSAS DISTINTAS
---------------------------------------------------------
El propio IDEAM advierte que estas detecciones sirven para priorizar,
no para contabilizar; el INPE hace la misma advertencia sobre DETER en
Brasil. Para 2025, el boletin trimestral reporto 72.409 ha mientras la
capa consolidada da del orden de 119.000 ha: la brecha mide cuanto
subestima un sistema de alertas frente al conteo consolidado.

ADVERTENCIA CENTRAL: NINGUN AGREGADO DE ESTA TABLA SIRVE COMO SERIE TEMPORAL
----------------------------------------------------------------------------
Que los datos sean puntos sin superficie tiene una consecuencia directa:
el conteo depende de con cuanto detalle el IDEAM divida sus detecciones,
y ese criterio cambio a lo largo de la serie. El resultado es que las
cifras agregadas se mueven en sentido CONTRARIO a la deforestacion real.

Se probaron los tres agregados posibles contra la cifra oficial
(2021-2024), y los tres fallan:

    conteo de puntos        r = -0,669
    celdas con alerta       r = -0,994
    municipios con alerta   r = -0,978

    (referencia: alertas GFW en hectareas, r = +0,971)

El indicador de presencia, que en principio deberia ser mas robusto que
el conteo, resulta incluso peor. No hay forma de rescatar un uso temporal
de esta tabla: cualquier agregado por ano llevaria a concluir que la
deforestacion aumento en un periodo en que descendio.

La tabla sirve DENTRO de cada trimestre, para comparar unos lugares con
otros. No sirve para comparar un trimestre con otro.

PARA QUE SIRVE, ENTONCES
------------------------
1. PRIORIZACION ESPACIAL CON RESPALDO OFICIAL. Es su uso principal. El
   ranking municipal por detecciones reproduce el de la cifra oficial:

     top-10 : 10 de 10 municipios coinciden
     top-25 : 21 de 25
     top-50 : 39 de 50
     correlacion de rangos (Spearman) = 0,811

   Es decir, para responder "donde", el conteo de detecciones llega a la
   misma respuesta que la cifra oficial anual, pero con cadencia
   trimestral y meses antes de que esa cifra se publique.

   La marca discrimina con fuerza. Comparando, trimestre a trimestre,
   los municipios con deteccion DTD contra los que no la tienen:

     hectareas con alerta GFW, mediana, municipios CON deteccion : 30,6
     hectareas con alerta GFW, mediana, municipios SIN deteccion :  0,2

   Un municipio senalado por el IDEAM concentra del orden de 130 veces
   mas superficie con alerta que uno no senalado, en el mismo trimestre.

   Y dentro de un trimestre el conteo ORDENA razonablemente por
   magnitud, aunque no la cuantifique: la correlacion de rangos entre
   numero de detecciones y hectareas con alerta de GFW tiene mediana
   0,651 (rango 0,513 a 0,784 sobre los 25 trimestres). Sirve para decir
   "este municipio esta peor que aquel" dentro del trimestre; no para
   decir cuantas hectareas.

2. VALOR PROBATORIO. La afirmacion "el IDEAM detecto alertas aqui"
   proviene de la autoridad ambiental del pais. En un producto destinado
   a debida diligencia de importacion, eso pesa distinto a la salida de
   un producto global. Cada punto trae ademas municipio, vereda y
   corporacion autonoma regional: la entidad competente sobre ese
   territorio.

3. VALIDACION DEL PANEL DE ALERTAS. El 92,1% de las celda-trimestre con
   deteccion oficial tiene tambien alerta de GFW en ese mismo trimestre.
   Eso confirma, contra una fuente oficial e independiente, que el panel
   mensual senala los lugares correctos. La correlacion entre el conteo
   de detecciones y las hectareas de GFW es 0,542: coinciden en DONDE,
   no en CUANTO, que es justo lo esperado entre un conteo y una
   superficie.

4. AREAS PROTEGIDAS. El 11,1% de las detecciones cae dentro del SINAP
   (19.645 de 177.215, sobre los 18 de 25 trimestres que traen el dato).
   La deforestacion dentro de un area protegida tiene una connotacion
   legal distinta, y ninguna otra fuente del proyecto la identifica.

Para MAGNITUD estan panel_ideam (oficial, anual) y el panel de alertas
de GFW (mensual, r = +0,971 con la cifra oficial). Para TENDENCIA
temporal, esos mismos dos.

PANEL BALANCEADO
----------------
Se emite una fila por celda y trimestre, incluidos los trimestres sin
alerta (n_alertas = 0), igual que el panel de alertas de GFW. Un panel
con huecos sesgaria cualquier modelo temporal, porque los periodos sin
evento desapareceria y no se aprenderia la probabilidad base.
======================================================================
"""
from __future__ import annotations

import re
import warnings
from typing import Tuple

import numpy as np
import pandas as pd

from calcular_bosque import bosque_ha_por_celda
from config_local import Config, DIR_DTD, DIR_PANEL, logger
from consolidar import asignar_municipio
from zonal import cargar_grilla

SALIDA = DIR_PANEL / "panel_dtd"

# Primer mes de cada trimestre, para poder expresar el periodo como
# fecha y ordenarlo/cruzarlo con los demas paneles.
MES_TRIMESTRE = {1: 1, 2: 4, 3: 7, 4: 10}


def _leer_kml(ruta):
    """Lee un KML de puntos de alerta como GeoDataFrame en EPSG:4326."""
    import geopandas as gpd
    with warnings.catch_warnings():
        # El driver KML emite avisos por campos vacios que no afectan
        # la geometria ni los atributos que se usan aqui.
        warnings.simplefilter("ignore")
        return gpd.read_file(ruta)


def _en_sinap(g) -> Tuple[np.ndarray, bool]:
    """
    Marca que puntos caen dentro de un area protegida del SINAP, y si el
    trimestre trae esa informacion.

    El campo NOM_SINAP no sigue una convencion unica en la serie:

      - en algunos trimestres la columna no existe;
      - en otros, los puntos fuera de area protegida llevan el texto
        "No Aplica" o "NO APLICA";
      - en otros, esos mismos puntos llevan el valor vacio.

    Preguntar solo por notna() contaria los "No Aplica" como si
    estuvieran dentro de un area protegida, lo que inflaba la cifra a mas
    del triple. Aqui se normaliza el texto (minusculas, sin tildes, sin
    espacios sobrantes) y se descartan tanto el vacio como las variantes
    de "no aplica".

    Devuelve (mascara, hay_dato). Cuando la columna falta, hay_dato es
    False y la columna del panel queda marcada como no disponible para
    ese trimestre, en vez de contarse como cero.
    """
    if "NOM_SINAP" not in g.columns:
        return np.zeros(len(g), dtype=bool), False
    txt = (g["NOM_SINAP"].astype("string")
           .str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii")
           .str.strip().str.lower())
    dentro = txt.notna() & (txt != "") & (~txt.str.startswith("no aplica", na=False))
    return dentro.to_numpy(dtype=bool), True


def alertas_por_celda(cfg: Config, grilla: pd.DataFrame) -> pd.DataFrame:
    """
    Conteo de puntos de alerta por celda y trimestre.

    Los puntos vienen en EPSG:4326 y la grilla vive en cfg.grid_crs, asi
    que hay que reproyectar antes de indexar. Una vez en la proyeccion
    de la grilla, la celda de cada punto es aritmetica directa
    (floor(coord / grid_scale_m)), la misma regla que usa zonal.py para
    los rasteres: eso garantiza que un punto y un pixel que caen en el
    mismo lugar terminen en la misma celda.
    """
    archivos = sorted(DIR_DTD.glob("atd_*.kml"))
    if not archivos:
        raise FileNotFoundError(
            f"No hay archivos DTD en {DIR_DTD}. Ejecute primero:\n"
            f"  python main_local.py dtd")

    # (ix, iy) -> cell_id, para traducir la posicion del punto.
    llave = {(int(r.ix), int(r.iy)): r.cell_id for r in grilla.itertuples()}
    lado = cfg.grid_scale_m
    filas = []

    logger.info("Leyendo %d trimestres de alertas tempranas...", len(archivos))
    for ruta in archivos:
        m = re.match(r"atd_(\d{4})_(\d)", ruta.stem)
        if not m:
            logger.warning("  %s: nombre inesperado, se omite", ruta.name)
            continue
        anio, trim = int(m.group(1)), int(m.group(2))

        g = _leer_kml(ruta)
        if g.empty:
            logger.warning("  %d-T%d: sin registros", anio, trim)
            continue
        g = g.to_crs(cfg.grid_crs)

        ix = np.floor(g.geometry.x.to_numpy() / lado).astype(np.int64)
        iy = np.floor(g.geometry.y.to_numpy() / lado).astype(np.int64)
        cell = [llave.get((a, b)) for a, b in zip(ix, iy)]

        sinap, hay_sinap = _en_sinap(g)

        d = pd.DataFrame({"cell_id": cell, "en_sinap": sinap}).dropna(subset=["cell_id"])
        fuera = len(g) - len(d)
        agg = (d.groupby("cell_id")
                .agg(n_alertas=("en_sinap", "size"),
                     n_alertas_sinap=("en_sinap", "sum"))
                .reset_index())
        agg["anio"], agg["trimestre"] = anio, trim
        agg["sinap_disponible"] = hay_sinap
        filas.append(agg)
        logger.info("  %d-T%d: %5d alertas en %4d celdas | SINAP: %s%s",
                    anio, trim, len(g), len(agg),
                    f"{int(sinap.sum()):,} ({100*sinap.mean():.1f}%)"
                    if hay_sinap else "sin dato",
                    f"  ({fuera} fuera de la grilla)" if fuera else "")

    return pd.concat(filas, ignore_index=True)


def construir(cfg: Config) -> pd.DataFrame:
    grilla, _ = cargar_grilla()
    logger.info("Celdas en la grilla: %d", len(grilla))
    conteo = alertas_por_celda(cfg, grilla)

    # --- Panel balanceado: toda celda en todo trimestre --------------
    periodos = (conteo[["anio", "trimestre"]].drop_duplicates()
                      .sort_values(["anio", "trimestre"]))
    idx = pd.MultiIndex.from_product(
        [grilla["cell_id"].values,
         [tuple(x) for x in periodos.to_numpy()]],
        names=["cell_id", "_per"])
    largo = pd.DataFrame(index=idx).reset_index()
    largo[["anio", "trimestre"]] = pd.DataFrame(
        largo["_per"].tolist(), index=largo.index)
    largo = largo.drop(columns="_per")

    largo = largo.merge(conteo, on=["cell_id", "anio", "trimestre"], how="left")
    largo[["n_alertas", "n_alertas_sinap"]] = (
        largo[["n_alertas", "n_alertas_sinap"]].fillna(0).astype(int))
    # sinap_disponible es una propiedad del TRIMESTRE, no de la celda:
    # se propaga a las celdas sin alerta, que en el merge quedaron NaN.
    disp = (conteo.groupby(["anio", "trimestre"])["sinap_disponible"]
                  .first().rename("disp"))
    largo = largo.merge(disp, on=["anio", "trimestre"], how="left")
    largo["sinap_disponible"] = largo.pop("disp").fillna(False).astype(bool)
    # Donde el trimestre no trae el dato, el conteo se anula: un vacio
    # de informacion y una ausencia de alertas en area protegida son
    # cosas distintas.
    largo.loc[~largo.sinap_disponible, "n_alertas_sinap"] = pd.NA

    # periodo como fecha (primer dia del trimestre) para ordenar y
    # cruzar con los demas paneles; trimestre legible como texto.
    largo["periodo"] = pd.to_datetime(dict(
        year=largo.anio, month=largo.trimestre.map(MES_TRIMESTRE), day=1))
    largo["trimestre_txt"] = (largo.anio.astype(str) + "-T"
                              + largo.trimestre.astype(str))

    # --- Metadatos y filtro de dominio, iguales a los demas paneles ---
    bosque = bosque_ha_por_celda(cfg, grilla,
                                 {(int(r.ix), int(r.iy)): i
                                  for i, r in enumerate(grilla.itertuples())})
    meta = grilla[["cell_id", "lon", "lat", "departamento"]].copy()
    meta["bosque_base_ha"] = bosque
    largo = largo.merge(meta, on="cell_id", how="left")

    antes = largo["cell_id"].nunique()
    largo = largo[largo["bosque_base_ha"] >= cfg.bosque_minimo_ha].copy()
    logger.info("Celdas con bosque >= %.0f ha: %d de %d",
                cfg.bosque_minimo_ha, largo["cell_id"].nunique(), antes)

    largo = asignar_municipio(largo, None, cfg)

    cols = ["cell_id", "periodo", "trimestre_txt", "anio", "trimestre",
            "n_alertas", "n_alertas_sinap", "sinap_disponible",
            "lon", "lat", "departamento",
            "bosque_base_ha", "cod_dane", "municipio"]
    return (largo[cols].sort_values(["cell_id", "periodo"])
                       .reset_index(drop=True))


def main() -> int:
    cfg = Config()
    tabla = construir(cfg)

    csv = SALIDA.with_suffix(".csv")
    tabla.to_csv(csv, index=False)
    try:
        tabla.to_parquet(SALIDA.with_suffix(".parquet"), index=False)
        parquet = "si"
    except Exception as e:                      # pyarrow ausente: no es fatal
        logger.warning("No se pudo escribir el .parquet (%s)", e)
        parquet = "no"

    por_anio = tabla.groupby("anio")["n_alertas"].sum()
    logger.info("=" * 62)
    logger.info("TABLA DTD LISTA")
    logger.info("  archivo   : %s (parquet: %s)", csv, parquet)
    logger.info("  filas     : %d  (%d celdas x %d trimestres)",
                len(tabla), tabla["cell_id"].nunique(),
                tabla["trimestre_txt"].nunique())
    logger.info("  celdas con alguna alerta: %d (%.1f%%)",
                tabla[tabla.n_alertas > 0].cell_id.nunique(),
                100 * tabla[tabla.n_alertas > 0].cell_id.nunique()
                / tabla.cell_id.nunique())
    logger.info("  puntos de alerta por anio:")
    for anio, n in por_anio.items():
        logger.info("    %d : %8s alertas", anio, f"{n:,}")
    con = tabla[tabla.sinap_disponible]
    if len(con):
        tot_c, sp_c = con.n_alertas.sum(), int(con.n_alertas_sinap.sum())
        logger.info("  areas protegidas (SINAP), solo trimestres con el dato:")
        logger.info("    %s de %s detecciones (%.1f%%) en %d de %d trimestres",
                    f"{sp_c:,}", f"{tot_c:,}", 100 * sp_c / max(tot_c, 1),
                    con.trimestre_txt.nunique(), tabla.trimestre_txt.nunique())
    logger.info("  ---")
    logger.info("  Unidad: NUMERO de detecciones. Sirve para prioridad espacial")
    logger.info("  dentro de cada trimestre. Los conteos NO son comparables")
    logger.info("  entre anios (r = -0,669 con la cifra oficial): ver el")
    logger.info("  encabezado del modulo. La magnitud la da panel_ideam.")
    logger.info("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
