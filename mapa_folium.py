"""
mapa_folium.py
======================================================================
Mapa interactivo (Leaflet, via folium) para darle un vistazo rapido al
panel final de deforestacion, sin abrir el CSV ni QGIS.

    python mapa_folium.py

Salida: datos/panel/mapa_deforestacion.html — se abre con doble click
en cualquier navegador, no necesita servidor ni internet para verse
(solo los tiles del mapa base piden internet la primera vez).

QUE MUESTRA
-----------
Agrega el panel LARGO (una fila por celda-mes) a UNA fila por celda,
sumando toda la ventana temporal, y monta tres capas sobre un mapa de
Colombia, todas encendibles/apagables desde el control de capas:

  1. "Deforestacion (mapa de calor)"   — vista general, rapida, hasta
     con las 44 mil celdas.
  2. "Celdas con deforestacion"        — un marcador por celda con
     evento, agrupados (cluster) para no saturar el navegador; al dar
     click muestra departamento, hectareas totales y meses con evento.
  3. "Bosque base (contexto)"          — donde habia bosque para
     empezar, apagada por defecto.

REQUISITOS
----------
    pip install folium
(branca viene incluido con folium; ya se usa para la escala de color).
======================================================================
"""
from __future__ import annotations

import argparse

import branca.colormap as cm
import folium
import numpy as np
import pandas as pd
from folium.plugins import Fullscreen, HeatMap, MarkerCluster, MiniMap

from config_local import DIR_PANEL, logger

PARQUET = DIR_PANEL / "panel_deforestacion_colombia.parquet"
CSV = DIR_PANEL / "panel_deforestacion_colombia.csv"
SALIDA = DIR_PANEL / "mapa_deforestacion.html"

# Centro y zoom inicial: encuadran Colombia continental completa.
CENTRO_COLOMBIA = (4.2, -73.5)
ZOOM_INICIAL = 6


# =====================================================================
# 1. CARGA Y AGREGACION
# =====================================================================
def cargar_panel() -> pd.DataFrame:
    """Lee el panel largo (una fila por celda-mes). Prefiere Parquet
    (mas rapido y con tipos correctos); cae a CSV si no existe."""
    if PARQUET.exists():
        try:
            logger.info("Leyendo %s", PARQUET)
            return pd.read_parquet(PARQUET)
        except ImportError:
            # Falta pyarrow/fastparquet en este entorno: se cae al CSV
            # en vez de obligar a instalar un motor de Parquet solo
            # para ver el mapa.
            logger.warning("pyarrow no disponible; se usa el CSV en su lugar.")
    if CSV.exists():
        logger.info("Leyendo %s", CSV)
        df = pd.read_csv(CSV)
        df["periodo"] = pd.to_datetime(df["periodo"])
        return df
    raise FileNotFoundError(
        f"No hay panel en {DIR_PANEL}. Ejecute primero:\n"
        f"  python main_local.py consolidar")


def agregar_por_celda(df: pd.DataFrame) -> pd.DataFrame:
    """Colapsa el panel largo a UNA fila por celda, resumiendo toda la
    ventana temporal. Es lo que se necesita para pintar un punto por
    celda en el mapa (el mapa no anima el tiempo, solo lo resume).
    """
    # Metadatos que no cambian mes a mes: basta con tomar el primero.
    base = df.groupby("cell_id", sort=False)[
        ["lon", "lat", "departamento", "bosque_base_ha"]].first()

    # Hectareas deforestadas en TODA la ventana temporal (no solo el
    # ultimo mes): es la magnitud mas util para un primer vistazo.
    resumen = df.groupby("cell_id", sort=False).agg(
        area_def_total_ha=("area_def_ha", "sum"),
        meses_con_evento=("evento", "sum"),
    )

    # Mes mas reciente con evento confirmado, por celda (NaT si nunca
    # tuvo ninguno). Se calcula solo sobre las filas con evento=1 para
    # no arrastrar meses sin deforestacion en el maximo.
    con_evento = df.loc[df["evento"] == 1, ["cell_id", "periodo"]]
    ultimo = (con_evento.groupby("cell_id")["periodo"].max()
              .rename("ultimo_evento"))

    celdas = base.join(resumen).join(ultimo).reset_index()
    celdas["tasa_total"] = (celdas["area_def_total_ha"]
                            / celdas["bosque_base_ha"].replace(0, np.nan))
    logger.info("Celdas agregadas: %d | con deforestacion: %d",
                len(celdas), (celdas["area_def_total_ha"] > 0).sum())
    return celdas


# =====================================================================
# 2. CAPAS DEL MAPA
# =====================================================================
def capa_calor(celdas: pd.DataFrame) -> HeatMap:
    """Mapa de calor de la deforestacion total: la vista mas rapida de
    leer para todo el pais de una sola vez, y la que mejor escala con
    muchas celdas (no crea un elemento HTML por celda, como si hacen
    los marcadores)."""
    con_def = celdas[celdas["area_def_total_ha"] > 0]
    # Peso normalizado a [0,1]: HeatMap interpreta el peso como
    # intensidad relativa, no como hectareas absolutas.
    pico = con_def["area_def_total_ha"].max()
    datos = list(zip(con_def["lat"], con_def["lon"],
                     con_def["area_def_total_ha"] / pico))
    return HeatMap(datos, name="Deforestacion (mapa de calor)",
                   radius=11, blur=16, max_zoom=9, min_opacity=.25)


def capa_contexto(celdas: pd.DataFrame) -> HeatMap:
    """Mapa de calor del bosque base: da contexto de donde habia
    bosque para empezar, independientemente de si se deforesto o no.
    Apagada por defecto (show=False) para no tapar la capa principal.
    """
    pico = celdas["bosque_base_ha"].max()
    datos = list(zip(celdas["lat"], celdas["lon"],
                     celdas["bosque_base_ha"] / pico))
    capa = HeatMap(datos, name="Bosque base (contexto)",
                   radius=9, blur=14, max_zoom=9, min_opacity=.15,
                   gradient={0.2: "#2A3327", 0.6: "#4C5A4E", 1.0: "#1E6B45"})
    return capa


def capa_marcadores(celdas: pd.DataFrame, umbral_ha: float, top_n: int,
                    escala: cm.LinearColormap) -> MarkerCluster:
    """Un marcador por celda CON deforestacion (>= umbral_ha), coloreado
    segun cuanto perdio en total, agrupados en racimos (cluster) para
    que el navegador no tenga que dibujar miles de elementos sueltos.
    Al hacer zoom, el cluster se abre solo.

    Cada marcador con su popup pesa bastante en el HTML final (a
    diferencia del mapa de calor, que es solo un array compacto de
    [lat, lon, peso]). Con las ~30 mil celdas que SI tienen algo de
    deforestacion en Colombia, dibujar un marcador por cada una genera
    un archivo de decenas de MB, lento de abrir. Por eso esta capa se
    limita a los 'top_n' focos mas grandes: para ver el pais completo
    ya esta el mapa de calor, esta capa es para "hacer click y ver el
    detalle" de los casos que mas importan.
    """
    cluster = MarkerCluster(name="Celdas con deforestacion (mayores focos)")
    con_def = (celdas[celdas["area_def_total_ha"] >= umbral_ha]
              .sort_values("area_def_total_ha", ascending=False))

    if len(con_def) > top_n:
        logger.info("  marcadores: mostrando los %d focos mayores de %d que "
                    "superan el umbral (use --top-n para ajustar)",
                    top_n, len(con_def))
        con_def = con_def.head(top_n)

    for f in con_def.itertuples():
        color = escala(np.log1p(f.area_def_total_ha))
        radio = float(np.clip(3 + np.sqrt(f.area_def_total_ha) * 1.4, 3, 16))
        ultimo = (f.ultimo_evento.strftime("%Y-%m")
                  if pd.notna(f.ultimo_evento) else "—")
        popup = folium.Popup(html=(
            f"<b>{f.cell_id}</b> · {f.departamento}<br>"
            f"Bosque base: {f.bosque_base_ha:,.0f} ha<br>"
            f"Deforestado (total): <b>{f.area_def_total_ha:,.2f} ha</b> "
            f"({f.tasa_total * 100:.2f}% del bosque base)<br>"
            f"Meses con evento: {int(f.meses_con_evento)}<br>"
            f"Ultimo evento: {ultimo}"
        ), max_width=260)
        folium.CircleMarker(
            location=(f.lat, f.lon), radius=radio,
            color=color, fill=True, fill_color=color, fill_opacity=.85,
            weight=1, popup=popup,
        ).add_to(cluster)

    return cluster


# =====================================================================
# 3. ENSAMBLAJE
# =====================================================================
def construir_mapa(celdas: pd.DataFrame, umbral_ha: float, top_n: int) -> folium.Map:
    # prefer_canvas: Leaflet dibuja los CircleMarker en un <canvas> en
    # vez de un elemento SVG por marcador -- mucho mas liviano para el
    # navegador cuando hay miles de puntos.
    mapa = folium.Map(location=CENTRO_COLOMBIA, zoom_start=ZOOM_INICIAL,
                      tiles="CartoDB positron", control_scale=True,
                      prefer_canvas=True)

    capa_contexto(celdas).add_to(mapa)
    capa_calor(celdas).add_to(mapa)

    con_def = celdas[celdas["area_def_total_ha"] > 0]
    escala = cm.LinearColormap(
        colors=["#FBE3CE", "#E2905A", "#B8562D", "#7A3319"],
        vmin=float(np.log1p(con_def["area_def_total_ha"].min())),
        vmax=float(np.log1p(con_def["area_def_total_ha"].max())),
    )
    escala.caption = "Deforestacion acumulada por celda, ha (escala logaritmica)"
    mapa.add_child(escala)

    capa_marcadores(celdas, umbral_ha, top_n, escala).add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)
    Fullscreen(position="topleft").add_to(mapa)
    MiniMap(toggle_display=True).add_to(mapa)
    return mapa


# =====================================================================
def main() -> int:
    p = argparse.ArgumentParser(description="Mapa folium del panel de deforestacion")
    p.add_argument("--umbral-ha", type=float, default=0.09,
                   help="Hectareas totales minimas para mostrar el marcador "
                        "de una celda (0.09 ha = 1 pixel DIST-ALERT). Default: 0.09")
    p.add_argument("--top-n", type=int, default=3000,
                   help="Maximo de marcadores a dibujar (los de mayor "
                        "deforestacion total primero). El mapa de calor "
                        "siempre muestra todas las celdas. Default: 3000")
    p.add_argument("--salida", type=str, default=str(SALIDA),
                   help="Ruta del HTML de salida")
    a = p.parse_args()

    df = cargar_panel()
    celdas = agregar_por_celda(df)
    mapa = construir_mapa(celdas, a.umbral_ha, a.top_n)

    destino = a.salida
    mapa.save(destino)
    logger.info("=" * 62)
    logger.info("MAPA GENERADO")
    logger.info("  archivo : %s", destino)
    logger.info("  abralo con doble click, o: start %s (Windows)", destino)
    logger.info("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
