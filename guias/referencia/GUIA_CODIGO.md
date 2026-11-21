# Guía del código: cómo está hecho el pipeline

Referencia para quien quiera **entender o modificar** el código: cómo está
organizado el repositorio, cómo se ven las cuatro tablas, qué hace cada
script y cómo se calculan el bosque base y el panel.

Para **correr** el trabajo no hace falta leer esta guía:

- [`2_DESCARGA_DE_DATOS.md`](../2_DESCARGA_DE_DATOS.md): entorno, credenciales,
  descarga y armado de los datos. Los «Pasos» que se citan aquí son los de
  ese documento.
- [`3_NOTEBOOKS.md`](../3_NOTEBOOKS.md): el análisis exploratorio, la
  segmentación y los modelos.

El porqué de cada decisión de diseño está en
[`METODOLOGIA.md`](METODOLOGIA.md); aquí se explica cómo está implementada.

---

## Índice

1. [Mapa del repositorio](#1-mapa-del-repositorio)
2. [Cómo se ven las cuatro tablas](#2-cómo-se-ven-las-cuatro-tablas)
3. [Referencia de cada script](#3-referencia-de-cada-script)
4. [Cómo se calcula el bosque base, en código](#4-cómo-se-calcula-el-bosque-base-en-código)
5. [Cómo se construye el panel, en código](#5-cómo-se-construye-el-panel-en-código)
6. [El mapa interactivo (`mapa_folium.py`)](#6-el-mapa-interactivo-mapa_foliumpy)
7. [Cómo adaptar el pipeline](#7-cómo-adaptar-el-pipeline)
8. [Glosario de código](#8-glosario-de-código)

---

## 1. Mapa del repositorio

```
trabajo_de_grado_ofr/
├── main_local.py             ÚNICO punto de entrada: python main_local.py <subcomando>
├── requirements_local.txt    dependencias de Python (pip)
├── README.md                 presentación corta y por dónde empezar
│
├── pipeline/                 todo el código, como paquete de Python
│   ├── config_local.py       configuración central — todo parámetro vive aquí
│   ├── zonal.py              reparte cualquier ráster entre las celdas de la grilla
│   ├── calcular_bosque.py    bosque_ha por celda — el DENOMINADOR común
│   ├── mapa_folium.py        mapa interactivo (Leaflet) de la Tabla 1
│   │
│   ├── descarga/             ── ETAPA 1: grilla e insumos ─────────────────
│   │   ├── exportar_grilla.py        grilla de 5 km — una sola vez
│   │   ├── descargar_hansen.py       gránulos de Hansen GFC
│   │   ├── configurar_gfw.py         registro de una sola vez en la API de GFW
│   │   ├── descargar_gfw.py          bosque base + alertas -> datos/crudo/nacional.csv
│   │   ├── descargar_municipios.py   límites municipales del DANE (MGN)
│   │   ├── descargar_ideam.py        capas de cambio de bosque del SMByC
│   │   └── descargar_dtd.py          detecciones tempranas del SMByC (KML por trimestre)
│   │
│   ├── paneles/              ── ETAPA 2: las cuatro tablas ────────────────
│   │   ├── consolidar.py             TABLA 1: alertas GFW, celda × mes + cruce municipal
│   │   ├── panel_hansen.py           TABLA 2: pérdida de cobertura, celda × año
│   │   ├── panel_ideam.py            TABLA 3: deforestación oficial, celda × periodo
│   │   └── panel_dtd.py              TABLA 4: alertas tempranas, celda × trimestre
│   │
│   ├── bigquery/             ── ETAPA 3: publicación ──────────────────────
│   │   └── subir_bigquery.py         sube las tablas del panel a BigQuery (opcional)
│   │
│   └── entendimiento/        ── ENTENDIMIENTO DE LOS DATOS ────────────────
│       ├── describir_fuentes.py           Paso 1 del EDA: las 4 tablas propias
│       ├── describir_fuentes_profesor.py  igual, para las 5 tablas del profesor
│       └── demo_landsat_caqueta.py        réplica del cálculo de pérdida desde Landsat
│
├── procesamiento y eda/
│   ├── catalogo_paneles.ipynb                 describe las cuatro tablas propias y las mapea
│   ├── consultar_tablas_profesor.ipynb        consulta de las tablas del profesor
│   ├── exploratorio_sfc414.ipynb              análisis exploratorio de SFC 414
│   ├── exploratorio_eva_ica_pecuario.ipynb    análisis exploratorio de EVA e ICA pecuario
│   ├── investigacion_municipio_27493.ipynb    el municipio 27493 en los catálogos del Observatorio
│   ├── panel_municipal_armado.ipynb           arma el panel municipal: municipio × año, × mes y × cultivo
│   ├── panel_municipal_analisis.ipynb         análisis de los municipios rurales sobre ese panel
│   └── estadisticas_descriptivas.ipynb        estadística descriptiva de todas las tablas
│
├── modelos y clusters/
│   ├── segmentacion_municipios.ipynb          segmentación de los municipios rurales con K-means
│   ├── gradient_boosting.ipynb                modelo principal: ¿deforesta? y ¿cuánto?
│   ├── random_forest.ipynb                    random forest, con el mismo diseño
│   ├── regresion_logistica.ipynb              regresión logística, la referencia interpretable
│   ├── comparacion_modelos.ipynb              compara los tres modelos
│   ├── segmentos_y_riesgo.ipynb               cruza los segmentos con el riesgo de los modelos
│   └── resultados/                            salidas de los notebooks oficiales (tablas, métricas, modelos .joblib)
│
├── notebooks_bigquery/       todo el trabajo en 18 notebooks para BigQuery Studio (ver su README.md)
│
├── guias/                    la documentación
│   ├── 1_FUENTES.md                      ← qué es cada fuente de datos
│   ├── 2_DESCARGA_DE_DATOS.md            ← entorno, credenciales, descarga y armado de los datos
│   ├── 3_NOTEBOOKS.md                    ← cómo correr el EDA, la segmentación y los modelos
│   ├── 4_DEMO_LANDSAT.md                 ← la réplica del cálculo con Landsat
│   ├── referencia/                       de consulta; no hacen falta para correr nada
│   │   ├── METODOLOGIA.md                el porqué de cada decisión
│   │   ├── GUIA_CODIGO.md                este documento: cómo está hecho el código
│   │   └── GUIA_BIGQUERY.md              administración de Google Cloud (para el equipo)
│   └── columnas/                         columnas y muestra de cada tabla; los generan los Pasos 12 y 13
│       ├── DESCRIPCION_FUENTES.md
│       └── DESCRIPCION_FUENTES_PROFESOR.md
│
├── documento/                figuras y tablas exportadas para el documento del trabajo
│   ├── figuras/                          estadísticas descriptivas y segmentos y riesgo (los generan los notebooks);
│   │                                     fuentes_deforestacion (diagrama de las fuentes, hecho aparte)
│   └── tablas/                           estadísticas descriptivas y segmentación (.xlsx)
│
└── datos/                    todo lo que se descarga y se produce (ver 2_DESCARGA_DE_DATOS.md, sección 4)
    ├── grilla/  hansen/  gfw/  cache/  crudo/  limites/  panel/  logs/
    ├── ideam/                 capas de cambio de bosque del SMByC
    ├── dtd/                   detecciones tempranas del SMByC
    ├── demo/                  salidas de la réplica con Landsat
    ├── profesor/              tablas del Observatorio descargadas de BigQuery
    └── analisis/              panel municipal (municipio × año, × mes y × cultivo)
```

### Cómo se corre

**Todo se corre desde la raíz del repositorio**, con
`python main_local.py <subcomando>`. Cada subcomando lanza un módulo del
paquete `pipeline/`, y las opciones que vienen después del subcomando se
le pasan a ese módulo:

```powershell
python main_local.py ideam --todos         # opciones de descargar_ideam.py
python main_local.py mapa --umbral-ha 1    # opciones de mapa_folium.py
python main_local.py ideam --help          # ayuda del módulo
python main_local.py --help                # lista de subcomandos
```

El equivalente directo de cada subcomando es `python -m` con la ruta del
módulo, también desde la raíz. Por ejemplo,
`python main_local.py demo-landsat` equivale a
`python -m pipeline.entendimiento.demo_landsat_caqueta`. Se usa `-m`, y
no la ruta del archivo, para que el módulo pueda importar el resto del
paquete.

Los notebooks se pueden abrir desde `procesamiento y eda/` o desde
`modelos y clusters/`: su primera celda de código busca la raíz del
repositorio y trabaja desde ahí, así que las rutas `datos/...` y los
imports de `pipeline` funcionan igual.

### Las cuatro tablas

El repositorio produce cuatro paneles sobre una misma grilla de 5 km.
Cada uno mide un concepto distinto, y por eso **sus cifras nunca se suman
entre sí**:

| Tabla | Fuente | Qué mide | Unidad | Responde a |
|---|---|---|---|---|
| `panel_deforestacion_colombia` | GFW | *Disturbio* de la vegetación, en hectáreas | celda × **mes** | **¿Cuándo?** Es el de mayor resolución temporal |
| `panel_hansen` | Hansen GFC | *Pérdida de cobertura arbórea*, en hectáreas | celda × **año** | **¿Cómo se compara con otros países?** Mismo algoritmo en todo el planeta |
| `panel_ideam` | IDEAM / SMByC | *Deforestación* de bosque natural, en hectáreas | celda × **periodo** | **¿Cuánto, oficialmente?** Definición nacional de bosque |
| `panel_dtd` | IDEAM / SMByC | *Detecciones* de alerta, en número de puntos | celda × **trimestre** | **¿Dónde, según la autoridad?** Único producto oficial sub-anual |

El alcance de cada una es específico. Una alerta de GFW indica que el
dosel cambió. Hansen contabiliza toda pérdida de cobertura arbórea,
incluidas la cosecha de plantación y el incendio. Las capas de cambio del
IDEAM aplican la definición nacional de bosque, con cadencia anual y
rezago de publicación. Las detecciones tempranas ubican el fenómeno cada
trimestre, en número de puntos y sin cuantificar superficie.

Las tres primeras se expresan en **hectáreas** y son comparables en
magnitud entre sí; comparar sus cifras es uno de los **resultados** del
trabajo (sección 2). La cuarta se expresa en **conteos** y responde a otra
pregunta.

Los cuatro comparten la grilla, el `bosque_base_ha` de Hansen (calculado
una sola vez en `calcular_bosque.py`), el mismo indexado de píxel a celda
(`zonal.py`) y el mismo cruce municipal. Esa base común es lo que los
hace comparables entre sí.

> **Hansen cumple dos papeles distintos.** Como **línea base** define
> `bosque_base_ha`, el denominador común de los cuatro paneles; ese
> cálculo vive en `calcular_bosque.py`. Como **fuente de evento** produce
> la Tabla 2, en `panel_hansen.py`. Conviene no confundirlos al leer el
> código.

**Regla general del repositorio**: todo parámetro que pueda cambiar el
resultado vive en `pipeline/config_local.py`, nunca hardcodeado dentro de otro
script. Si algo en las tablas se ve distinto a lo esperado, el primer
lugar a revisar es ese archivo, no el resto del código.

---

## 2. Cómo se ven las cuatro tablas

*(Números de la corrida de referencia.)*

Los cuatro paneles cubren exactamente las mismas **44 616 celdas**, con el
mismo `bosque_base_ha` de Hansen (77 713 177 ha) y el mismo cruce
municipal (1 114 municipios).

| Archivo en `datos/panel/` | Mide | Unidad | Filas | Cols |
|---|---|---|---|---|
| `panel_deforestacion_colombia` | Disturbio, ha (GFW) | celda × mes | 3 524 664 | 19 |
| `panel_hansen` | Pérdida de cobertura, ha (Hansen) | celda × año | 267 696 | 9 |
| `panel_ideam` | Deforestación oficial, ha (IDEAM) | celda × periodo | 223 080 | 15 |
| `panel_dtd` | Detecciones, conteo (IDEAM) | celda × trimestre | 1 115 400 | 14 |

Cada uno en `.csv` y `.parquet`.

### Qué reporta cada fuente, lado a lado

| Año | GFW alerta | Hansen pérdida | IDEAM def. | Oficial IDEAM | Hansen/IDEAM | GFW/IDEAM |
|---|---|---|---|---|---|---|
| 2021 | 195 833 | 265 200 | 173 663 | 174 103 | 1,53 | 1,13 |
| 2022 | 172 082 | 266 168 | 123 204 | 123 517 | 2,16 | 1,40 |
| 2023 | 122 362 | 197 246 | 78 982 | 79 256 | 2,50 | 1,55 |
| 2024 | 156 640 | 213 785 | 113 423 | 113 608 | 1,88 | 1,38 |
| 2025 | 144 843 | 186 697 | 119 282 | 119 483 | 1,57 | 1,21 |

La tabla del IDEAM recupera entre el **99,65 % y el 99,84 %** de la cifra
oficial publicada; lo que falta son celdas por debajo de
`bosque_minimo_ha`, excluidas por el filtro de dominio. Eso **valida el
procedimiento de agregación zonal** contra un dato externo.

Las dos últimas columnas miden **cuánto se aparta cada proxy del concepto
oficial**, y varían año a año: Hansen entre 1,53 y 2,50, GFW entre 1,13 y
1,55. Convertir alertas o pérdida de cobertura en hectáreas deforestadas
requiere, por tanto, **un factor específico para cada año**.

### Tabla 1 — `panel_deforestacion_colombia` (alertas GFW, mensual)

19 columnas, 44 616 celdas × 79 periodos (2020-01 a 2026-07).
`filas = celdas × periodos` exactamente: el panel es un rectángulo
perfecto, sin huecos, que es la condición para modelar. Área con alerta
1 085 131 ha; 28,01 % de las celda-mes con evento.

| # | Columna | Tipo | Qué es |
|---|---|---|---|
| 1 | `cell_id` | texto | id de la celda: `"{lon×1e4}_{lat×1e4}"` redondeado |
| 2 | `periodo` | fecha | primer día del mes, p. ej. `2023-09-01` |
| 3 | `area_def_ha` | float | hectáreas **con alerta** ese mes en esa celda |
| 4-5 | `lon`, `lat` | float | centroide de la celda, EPSG:4326 |
| 6 | `bosque_base_ha` | float | bosque al arrancar (Hansen: dosel ≥ `umbral_dosel`) |
| 7 | `departamento` | texto | departamento del centroide |
| 8 | `def_acum_ha` | float | pérdida acumulada hasta este periodo inclusive |
| 9 | `bosque_remanente_ha` | float | bosque disponible **al inicio** del periodo |
| 10 | `tasa_def` | float | `area_def_ha / bosque_remanente_ha`, en [0, 1] — target continuo |
| 11 | `evento` | int (0/1) | 1 si hubo alerta ese mes — target binario |
| 12-14 | `lag_1_ha`…`lag_3_ha` | float | `area_def_ha` de la celda, 1-3 meses atrás |
| 15 | `media_movil_3` | float | promedio de `area_def_ha` de los 3 meses previos |
| 16-17 | `anio`, `mes` | int | descompuestos de `periodo` |
| 18 | `cod_dane` | texto (5 dígitos) | código DANE del municipio — **la llave para cruces**; conserva el cero a la izquierda (`05001`) |
| 19 | `municipio` | texto | nombre, solo para lectura humana |

Definición matemática de las variables derivadas en
[METODOLOGIA.md §3.4](METODOLOGIA.md#34-del-bosque-base-a-las-variables-de-exposición-y-tasa).

### Tabla 2 — `panel_hansen` (pérdida de cobertura, anual)

9 columnas, 44 616 celdas × 6 años (2020-2025).

| # | Columna | Tipo | Qué es |
|---|---|---|---|
| 1 | `cell_id` | texto | id de la celda, igual que en las otras dos |
| 2 | `anio` | int | año calendario de la pérdida (capa `lossyear`) |
| 3 | `perdida_ha` | float | hectáreas que perdieron cobertura arbórea ese año |
| 4-5 | `lon`, `lat` | float | centroide de la celda |
| 6 | `departamento` | texto | departamento del centroide |
| 7 | `bosque_base_ha` | float | **idéntico** al de las otras dos tablas |
| 8-9 | `cod_dane`, `municipio` | texto (5 dígitos), texto | cruce municipal del DANE |

> **Para qué sirve esta tabla.** Habilita tres usos concretos:
>
> 1. **Comparación internacional.** Hansen aplica el mismo algoritmo en
>    todo el planeta, de modo que permite situar a Colombia frente a
>    Brasil, Perú o Indonesia con una medida homogénea. El IDEAM cubre
>    solo Colombia, y las alertas de GFW varían en sensibilidad según la
>    región.
> 2. **Fuente independiente del Estado evaluado**, lo que aporta valor
>    probatorio en una debida diligencia de importación.
> 3. **Control de robustez**: un municipio señalado por las tres fuentes
>    a la vez constituye una señal más sólida.

> **Al argumentar convergencia entre fuentes, tener presente su
> independencia.** El producto Hansen y el sistema GLAD provienen del
> mismo laboratorio (UMD) y ambos se basan en Landsat, de modo que su
> coincidencia aporta evidencia limitada. Las parejas con independencia
> plena son IDEAM–Hansen e IDEAM–GFW.

### Tabla 3 — `panel_ideam` (deforestación oficial, por periodo)

15 columnas, 44 616 celdas × 5 periodos. Guarda las **cinco clases** de
la capa de cambio, no solo la deforestación.

| # | Columna | Tipo | Qué es |
|---|---|---|---|
| 1 | `cell_id` | texto | id de la celda, igual que en las otras dos |
| 2 | `periodo` | texto | `"2022-2023"` — transición, **no año calendario** |
| 3 | `bosque_estable_ha` | float | clase 1 — bosque que siguió siendo bosque |
| 4 | `def_ha` | float | clase 2 — **deforestación**, la variable principal |
| 5 | `sin_info_ha` | float | clase 3 — nubosidad: **indicador de calidad** |
| 6 | `regeneracion_ha` | float | clase 4 — recuperación de bosque |
| 7 | `no_bosque_ha` | float | clase 5 — no bosque que siguió siendo no bosque |
| 8 | `bosque_ideam_ha` | float | clase 1 + clase 2 = **bosque natural al inicio del periodo** |
| 9 | `bosque_ideam_fin_ha` | float | clase 1 + clase 4 = bosque natural al final del periodo |
| 10-11 | `lon`, `lat` | float | centroide de la celda |
| 12 | `departamento` | texto | departamento del centroide |
| 13 | `bosque_base_ha` | float | línea base de Hansen, idéntica a las otras dos |
| 14-15 | `cod_dane`, `municipio` | texto (5 dígitos), texto | cruce municipal del DANE |

> **`periodo` designa una transición entre dos composiciones anuales de
> imágenes**, cuya ventana difiere del año calendario. Su cifra
> corresponde al **año final**: `2022-2023` produce el dato oficial de
> **2023**, verificado contra la cifra publicada.

> **`sin_info_ha` mide la superficie que las nubes impidieron observar**,
> y sirve como control de calidad. Cae de 116 400 ha en 2020-2021 a
> 566 ha en 2022-2023: los primeros periodos arrastran mucha más
> incertidumbre por vacíos de observación, y conviene ponderar o filtrar
> las celdas afectadas.

### Tabla 4 — `panel_dtd` (alertas tempranas oficiales, trimestral)

14 columnas, 44 616 celdas × 25 trimestres (2020-T1 a 2026-T1). Panel
balanceado, igual que el de alertas.

| # | Columna | Tipo | Qué es |
|---|---|---|---|
| 1 | `cell_id` | texto | id de la celda, igual que en las otras tres |
| 2 | `periodo` | fecha | primer día del trimestre, para ordenar y cruzar |
| 3 | `trimestre_txt` | texto | `"2024-T2"`, legible |
| 4-5 | `anio`, `trimestre` | int | descompuestos |
| 6 | `n_alertas` | int | **número de puntos de alerta** publicados en esa celda |
| 7 | `n_alertas_sinap` | int | cuántos de esos caen en un área protegida del SINAP |
| 8 | `sinap_disponible` | bool | si ese trimestre trae el dato de área protegida (18 de los 25) |
| 9-10 | `lon`, `lat` | float | centroide de la celda |
| 11 | `departamento` | texto | departamento del centroide |
| 12 | `bosque_base_ha` | float | línea base de Hansen, idéntica a las otras |
| 13-14 | `cod_dane`, `municipio` | texto (5 dígitos), texto | cruce municipal del DANE |

> **Los datos son puntos, sin superficie asociada.** Cada registro marca
> un sitio donde el IDEAM detectó un cambio compatible con deforestación,
> y no trae extensión: no hay campo de área y el campo `count` vale
> siempre 1. Se verificó en las tres distribuciones del SMByC:
>
> | Capa | Qué contiene |
> |---|---|
> | `Puntos/` `.kml` | Puntos, sin campo de área — **lo que se usa** |
> | `Nucleos/` `.kmz` | Una imagen superpuesta (PNG y un rectángulo), no polígonos |
> | `Nucleos/` `.tif` | Ráster de **densidad**: conteos por celda de 2 500 m |
>
> Ninguna permite derivar hectáreas. La magnitud en superficie la dan las
> Tablas 1 a 3.

> **Ningún agregado de esta tabla sirve como serie temporal.** Que los
> datos sean puntos sin superficie tiene una consecuencia directa: el
> conteo depende de con cuánto detalle el IDEAM divida sus detecciones, y
> ese criterio cambió a lo largo de la serie. Se probaron los tres
> agregados posibles contra la cifra oficial (2021-2024) y los tres
> fallan:
>
> | Agregado | Correlación con la cifra oficial |
> |---|---|
> | Conteo de puntos | −0,669 |
> | Celdas con alerta | **−0,994** |
> | Municipios con alerta | −0,978 |
> | *(referencia: alertas GFW en ha)* | *+0,971* |
>
> El indicador de presencia, que en principio debería ser más robusto que
> el conteo, resulta incluso peor. Cualquier agregado por año llevaría a
> concluir que la deforestación aumentó en un periodo en que descendió.
>
> **La tabla sirve dentro de cada trimestre, para comparar unos lugares
> con otros. No sirve para comparar un trimestre con otro.**
>
> Los usos que el dato sí sostiene: **prioridad espacial dentro de un
> trimestre**, **respaldo institucional** (el IDEAM detectó alertas aquí)
> y **cruce con áreas protegidas** — el 11,1 % de las detecciones cae
> dentro del SINAP.

> **Cobertura nacional.** Las detecciones alcanzan las cinco regiones
> naturales (Amazónica, Andina, Pacífica, Orinoquía y Caribe) y 1 114
> municipios, lo que la hace utilizable también en la zona andina.

### Qué denominador usar en cada tabla

Esto importa y es fácil equivocarse. La regla es que el denominador debe
**contener** al numerador:

| Tabla | Denominador correcto | Por qué |
|---|---|---|
| Alertas GFW | `bosque_base_ha` | Las alertas se disparan también fuera del bosque natural. Con el denominador del IDEAM, 843 celdas darían tasas > 100 % |
| Hansen | `bosque_base_ha` | Numerador y denominador salen del mismo producto |
| IDEAM | **`bosque_ideam_ha`** | `def_ha` cuenta solo bosque natural. Usar el de Hansen **subestima la tasa un 30-45 %** |

La brecha entre ambas definiciones es grande: Hansen ve 77 713 177 ha de
bosque y el IDEAM 59 294 546 ha, sobre el mismo territorio y el mismo
año. La diferencia proviene de la definición de la palabra "bosque":
Hansen incluye las plantaciones forestales, el IDEAM las excluye.

### Inspeccionarlas en Python

> **Al leer los CSV, `cod_dane` debe forzarse a texto.** Los códigos DANE
> llevan cero a la izquierda en Antioquia (`05001`) y Atlántico (`08001`).
> Si `pandas` los infiere, los convierte a entero y el cero desaparece
> (`5001`), lo que rompe cualquier cruce con otra fuente del DANE. Los
> `.parquet` conservan el tipo; los `.csv` no lo declaran.

```python
import pandas as pd

# Con Parquet el tipo viene conservado:
gfw    = pd.read_parquet("datos/panel/panel_deforestacion_colombia.parquet")
hansen = pd.read_parquet("datos/panel/panel_hansen.parquet")
ideam  = pd.read_parquet("datos/panel/panel_ideam.parquet")

# Sin pyarrow instalado, usar los CSV -- declarando el tipo de cod_dane:
# gfw = pd.read_csv("datos/panel/panel_deforestacion_colombia.csv",
#                   parse_dates=["periodo"], dtype={"cod_dane": "string"})

# --- Ranking municipal segun la fuente OFICIAL ---
(ideam.groupby(["cod_dane", "municipio"])["def_ha"].sum()
      .sort_values(ascending=False).head(15))

# --- Tasa oficial con el denominador correcto ---
ideam["tasa_oficial"] = ideam.def_ha / ideam.bosque_ideam_ha.replace(0, pd.NA)

# --- Las tres fuentes en un mismo municipio ---
COD = 18150   # Cartagena del Chaira, Caqueta
print("GFW   :", gfw[gfw.cod_dane == COD]["area_def_ha"].sum())
print("Hansen:", hansen[hansen.cod_dane == COD]["perdida_ha"].sum())
print("IDEAM :", ideam[ideam.cod_dane == COD]["def_ha"].sum())

# --- Municipios senalados por las TRES fuentes (convergencia) ---
top = lambda t, c: set(t.groupby("cod_dane")[c].sum().nlargest(50).index)
convergen = top(gfw, "area_def_ha") & top(hansen, "perdida_ha") & top(ideam, "def_ha")
print(f"{len(convergen)} municipios en el top-50 de las tres fuentes")
```

---

## 3. Referencia de cada script

### 3.1 `pipeline/config_local.py` — configuración central

Todos los parámetros que afectan el resultado viven en un `dataclass`
congelado (`frozen=True`, no se puede mutar por accidente). También crea
automáticamente el árbol de carpetas bajo `datos/` la primera vez que se
importa cualquier script del pipeline.

| Parámetro | Significado | Ver también |
|---|---|---|
| `hansen_version`, `umbral_dosel`, `anio_mascara` | Definen la máscara de bosque base | METODOLOGIA §3.1 |
| `bosque_resolucion_m`, `bosque_bloque_celdas` | Resolución (m/píxel) y tamaño de bloque (celdas/lado) con que se reproyecta Hansen sobre la grilla nacional | sección 4 de este documento |
| `grid_scale_m`, `grid_crs` | Tamaño de celda (5000 m) y proyección de la grilla | METODOLOGIA §1.2 |
| `bosque_minimo_ha` | Umbral para descartar celdas sin bosque suficiente | sección 5 de este documento |
| `bbox` | Rectángulo usado para seleccionar gránulos de Hansen | METODOLOGIA §4, decisión 11 |
| `gfw_dataset`, `gfw_version` | Identificador del dataset GFW en la API SQL. Cambiarlo es todo lo que hace falta para usar otra fuente de evento; el archivo lista otros datasets de alertas disponibles | METODOLOGIA §2.2 |
| `fecha_inicio`, `fecha_fin`, `frecuencia` | Ventana temporal del panel y su resolución mensual | METODOLOGIA §1.3 |
| `gfw_confianza_minima` | Niveles de confianza de GFW que cuentan como evento. Usar solo `("highest",)` aplica el criterio más estricto, a costa de un panel más disperso — ver la nota en `pipeline/config_local.py` | METODOLOGIA §2.2, decisión 2 |
| `gfw_celdas_por_lote`, `gfw_lotes_en_paralelo` | Tamaño de lote y paralelismo de las consultas a la API de GFW | sección 5 |
| `reintentos`, `timeout_s`, `hilos_descarga` | Robustez de red para las descargas de Hansen | — |

### 3.2 `pipeline/descarga/exportar_grilla.py` — grilla de 5 km

Genera la grilla localmente con `geopandas` y los límites del DANE (Marco
Geoestadístico Nacional), sin ninguna cuenta de Google ni de la NASA.
Construye una malla regular de celdas alineadas al origen de EPSG:3116
(cada celda es literalmente `[ix*5000, (ix+1)*5000) x [iy*5000, (iy+1)*5000)`
para algún par de enteros `ix, iy` — alineación garantizada por
construcción, no por verificación posterior) y descarta las que no tocan
el territorio continental.

### 3.3 `pipeline/descarga/descargar_hansen.py` — descarga de Hansen GFC

Calcula qué gránulos de 10°×10° intersectan el `bbox` de Colombia y los
descarga de un bucket público (sin autenticación), con el patrón de
descarga atómica de siempre (escribe a `.parcial`, solo renombra al
nombre final si terminó bien) y en paralelo con un `ThreadPoolExecutor`.

### 3.4 `pipeline/calcular_bosque.py` — bosque base (detalle en sección 4)

### 3.5 `pipeline/descarga/configurar_gfw.py` — registro en la API de GFW

Automatiza el flujo de autenticación de la API de GFW en tres llamadas
(`/auth/sign-up` → `/auth/token` → `/auth/apikey`), guardando la API key
resultante en `datos/logs/gfw_api_key.txt`. El esquema exacto de las
respuestas no está documentado públicamente por la API; el script imprime
la respuesta cruda del servidor si no encuentra el campo esperado, en vez
de fallar en silencio.

### 3.6 `pipeline/descarga/descargar_gfw.py` — bosque + evento (detalle en sección 4)

### 3.7 `pipeline/descarga/descargar_municipios.py` — límites municipales del DANE

Trae los 1.122 polígonos municipales del Marco Geoestadístico Nacional
2025 (nivel Municipio, capa "Gráfico") del mismo servicio ArcGIS público
del DANE que usa `exportar_grilla.py` para los departamentos —sin
cuenta, sin descarga manual desde el navegador—, y los guarda en
`datos/limites/municipios_dane_mgn2025.geojson`. `consolidar.py` lo
invoca automáticamente si ese archivo todavía no existe.

### 3.8 `pipeline/paneles/consolidar.py` — Tabla 1, alertas GFW (detalle en sección 5)

### 3.9 `pipeline/zonal.py` — maquinaria zonal compartida

Reparte los píxeles de **cualquier** ráster entre las celdas de la
grilla. Lo usan las dos tablas y el atributo de causas, y esa es la razón
de que exista: si cada
una implementara el reparto por su cuenta, una diferencia de medio píxel
en el borde de una celda haría que dejaran de ser comparables.

Expone `cargar_grilla()`, `bloques()`, `perfil_bloque()`,
`indice_celdas_bloque()`, `reproyectar_sobre_bloque()` y
`contar_por_celda_y_clase()`. El detalle del diseño (bloques alineados a
bordes de celda, ráster sintético en EPSG:3116, índice por aritmética
directa sin `pyproj`) está en la sección 4.

### 3.10 `pipeline/paneles/panel_hansen.py` — Tabla 2, pérdida anual

Cuenta píxeles de la capa `lossyear` por celda y por año, aplicando la
misma definición de bosque que `calcular_bosque.py` (un píxel que nunca
fue bosque no puede perder cobertura). No descarga nada: reutiliza los
gránulos del Paso 2. Escribe `datos/panel/panel_hansen.*`.

Su encabezado documenta los dos papeles de Hansen en el proyecto —línea
base y fuente de evento— y la relación de su cifra con la del IDEAM:
entre 1,5 y 2,5 veces esa cifra, con una razón que varía cada año.

### 3.11 `pipeline/descarga/descargar_ideam.py` — capas oficiales del SMByC

Descarga los rásteres de cambio de bosque del IDEAM a `datos/ideam/`.
El catálogo de archivos está en el diccionario `CAPAS` (el sufijo de
versión y fecha de cada capa no sigue un patrón deducible, así que se
lista explícitamente). Descarga a un `.parcial` y renombra al final, para
que una interrupción no deje un `.img` truncado que la corrida siguiente
daría por bueno.

**El servidor solo responde por HTTPS** (puerto 80 cerrado). Con `http://`
no da error: se cuelga hasta agotar el tiempo de espera.

### 3.12 `pipeline/paneles/panel_ideam.py` — Tabla 3, deforestación oficial

Cuenta las cinco clases de la capa de cambio por celda y periodo. Los
cinco periodos se procesan **dentro** del recorrido de bloques, no uno
después de otro: el índice de celda depende solo de la geometría del
bloque, así que compartirlo entre periodos evita recalcularlo 780 veces
en vez de 156.

Calcula además `bosque_ideam_ha` (clase 1 + clase 2), que es el
denominador correcto para las tasas de esta tabla — ver la advertencia de
la sección 2.

### 3.13 `pipeline/descarga/descargar_dtd.py` — detecciones tempranas del SMByC

Baja los puntos de alerta trimestrales a `datos/dtd/`. En vez de
construir los nombres de archivo, **lista el índice del servidor** y toma
los que encuentra: la caja de las letras no es uniforme entre años, y así
los trimestres nuevos aparecen sin tocar código. Renombra a un patrón
regular en disco (`atd_<año>_<trimestre>.kml`).

Se usan los **puntos** y no los **núcleos** porque la serie de puntos no
tiene huecos (2016-III a 2026-I), mientras la de núcleos carece del año
2024 completo en el servidor.

### 3.14 `pipeline/paneles/panel_dtd.py` — Tabla 4, alertas tempranas

Reproyecta los puntos a `cfg.grid_crs` y los asigna a su celda con la
misma regla aritmética que usa `zonal.py` para los rásteres
(`floor(coord / grid_scale_m)`), de modo que un punto y un píxel en el
mismo lugar caen en la misma celda. Emite un panel balanceado.

### 3.15 `main_local.py` — orquestador

Es el único punto de entrada. Vive en la raíz; todo lo demás está en
`pipeline/`.

Cada subcomando (`grilla`, `hansen`, `configurar-gfw`, `gfw`,
`municipios`, `consolidar`, `panel-hansen`, `ideam`, `panel-ideam`,
`dtd`, `panel-dtd`, `mapa`, `subir-bigquery`, `describir-fuentes`,
`describir-fuentes-profesor`, `demo-landsat`, `estado`) arma la línea de
comandos correcta y lanza el módulo correspondiente como subproceso, con
`python -m pipeline.<carpeta>.<módulo>` desde la raíz. La tabla `ETAPAS`
del archivo dice qué módulo corre cada subcomando.

Las opciones que siguen al subcomando se reenvían al módulo, así que
`python main_local.py ideam --todos` llega a `descargar_ideam.py` como
`--todos`, y `--help` después del subcomando muestra la ayuda del
módulo.

Hay dos excepciones. `consolidar` importa la función directamente en vez
de lanzar un subproceso, y `estado` no delega: lista lo que hay en disco
en cada etapa y cuáles de las cuatro tablas ya existen.

### 3.16 `pipeline/bigquery/subir_bigquery.py` — subir las cuatro tablas a BigQuery

Sube cada tabla de `datos/panel/*.csv` que ya exista al dataset
`staging` del proyecto de BigQuery del equipo (`ofr-credito-deforestacion`),
en modo "reemplazar" (`WRITE_TRUNCATE`): como cada corrida de
`consolidar.py`/`panel_hansen.py`/`panel_ideam.py`/`panel_dtd.py`
reconstruye el CSV completo, subir en modo reemplazar mantiene
BigQuery igual de sincronizado que el disco sin duplicar filas.

Se autentica con la cuenta de servicio `pipeline-satelital` (permisos
BigQuery Data Editor + BigQuery Job User, nada más), cuya llave `.json`
se espera en `datos/logs/bigquery-key.json` (fuera del control de
versiones, igual que `gfw_api_key.txt`) o en la variable de entorno
`GOOGLE_APPLICATION_CREDENTIALS`. El esquema de cada tabla se detecta
automáticamente a partir del CSV (`autodetect=True`), así que no hace
falta declararlo a mano ni mantenerlo sincronizado con los cambios en
las columnas del panel.

#### ¿Por qué una cuenta de servicio con `key.json`, y no la cuenta de Gmail del equipo?

La cuenta de Gmail (`trabajodegrado139@gmail.com`) es una **cuenta de
usuario**: sirve para que una persona inicie sesión en la consola de
Google Cloud desde un navegador (con su propio flujo de login, y
verificación en dos pasos si está activada). No está pensada para que
un script se autentique solo, sin nadie sentado frente al navegador
cada vez que corre `subir_bigquery.py`.

Una **cuenta de servicio** es distinta: es una identidad que pertenece
al *proyecto* de Google Cloud, no a una persona, y existe justo para
que código (scripts, notebooks, jobs programados) se autentique de
forma automática. `pipeline-satelital` es una de esas identidades,
creada solo para este pipeline, con exactamente dos permisos —cargar
tablas en BigQuery y correr los jobs de carga— y ningún otro (no puede,
por ejemplo, borrar el proyecto, tocar la facturación ni ver el bucket
de Cloud Storage). Aunque la llave se filtrara, el daño posible queda
acotado a esos dos permisos sobre este proyecto puntual.

El archivo `bigquery-key.json` es la credencial que le permite al
script "iniciar sesión" como esa cuenta de servicio sin pasar por un
navegador ni una contraseña: contiene una llave privada que firma cada
solicitud a la API de Google en nombre de `pipeline-satelital`. Por
eso funciona exactamente como una contraseña —quien tenga el archivo
puede actuar con esos permisos— y por eso vive en `datos/logs/`, fuera
del control de versiones, siguiendo el mismo criterio que ya se usa
con `gfw_api_key.txt` (sección 3.5): la credencial nunca se sube al
repositorio ni se comparte por chat o correo, cada quien la copia una
sola vez en su propia máquina.

Tablas destino (todas en el dataset `staging`):

| Alias    | Archivo local                          | Tabla en BigQuery          |
|----------|------------------------------------------|-----------------------------|
| `gfw`    | `panel_deforestacion_colombia.csv`        | `stg_gfw_alertas`           |
| `hansen` | `panel_hansen.csv`                        | `stg_hansen_perdida`        |
| `ideam`  | `panel_ideam.csv`                         | `stg_ideam_deforestacion`   |
| `dtd`    | `panel_dtd.csv`                           | `stg_dtd_alertas`           |

Uso: `python main_local.py subir-bigquery` (o `--solo gfw,hansen` para
subir solo algunas). Ver el docstring del propio script para el detalle.

### 3.17 `pipeline/entendimiento/describir_fuentes.py` — Paso 1 del EDA: describir las cuatro tablas propias

Corresponde al primer paso del EDA acordado con el tutor ("organizar
la información: extracción" y "analizar datos y declarar si se
necesita limpieza"): antes de poder decidir el periodo de tiempo,
proponer KPIs o cruzar las tablas, hay que saber con certeza qué tiene
cada una.

Consulta directamente en BigQuery las cuatro tablas del panel propio
(`staging`, sección 3.16) y para cada una obtiene columnas y tipos de
dato, número de filas, y una muestra de 5 filas. Todo se obtiene
corriendo consultas normales (`SELECT ...`), nunca pidiendo metadatos
del dataset (`INFORMATION_SCHEMA`, listar tablas) -- ver el porqué en
`describir_fuentes_profesor.py` (sección 3.18), que reutiliza esta
misma lógica (`_describir_tabla()`) para las tablas del profesor, cuyo
permiso sí depende de eso.

Usa la misma credencial que `subir-bigquery` (`datos/logs/bigquery-key.json`).
Deja el resultado en `guias/columnas/DESCRIPCION_FUENTES.md` (no en `datos/`, para
que quede versionado y visible para todos). Se regenera completo cada vez
que se corre —no es incremental—, así que basta con volver a correrlo
cuando cambien las tablas de origen.

Las cinco tablas de solo lectura del Observatorio (`prueba-ofr`) no están
en este script: se describen aparte, con su propio reporte, en
`describir_fuentes_profesor.py` (sección 3.18), que usa la misma cuenta de
servicio.

Uso: `python main_local.py describir-fuentes`.

### 3.18 `pipeline/entendimiento/describir_fuentes_profesor.py` — Paso 1 del EDA: las cinco tablas del profesor

Hace exactamente lo mismo que `describir_fuentes.py` (columnas y tipos
de dato, número de filas, muestra de 5 filas) pero solo para las cinco
tablas de solo lectura del Observatorio: las tres financieras
(`prueba-ofr.Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA`,
`prueba-ofr.Inclusion_Financiera.SFC414_DASH`, `prueba-ofr.Municipios.CODIGO`)
y las dos de producción agropecuaria
(`prueba-ofr.Produccion.eva_full_enriquecido` y
`prueba-ofr.Produccion.ICA_pecuario`; el Observatorio advirtió que esta
última puede tener inconsistencias). El resultado queda en un reporte
aparte: `guias/columnas/DESCRIPCION_FUENTES_PROFESOR.md`. Reutiliza `_describir_tabla()` y
`_credenciales()` de `describir_fuentes.py` (mismo import), así que
tanto la lógica de consulta -- siempre `SELECT`, nunca metadatos del
dataset, porque el permiso del profesor es solo a nivel de tabla
puntual (ver `GUIA_BIGQUERY.md`) -- como la credencial son una sola,
compartida entre los dos scripts.

Es un script aparte, y no una opción dentro de `describir_fuentes.py`,
para que las tablas del Observatorio tengan su propio reporte, separado
del de las tablas propias.

**Requiere:** la misma llave de la cuenta de servicio que
`describir-fuentes` y `subir-bigquery` (`datos/logs/bigquery-key.json`,
o la variable de entorno `GOOGLE_APPLICATION_CREDENTIALS` -- ver
sección 3.16). No requiere el Google Cloud CLI ni una cuenta personal de
Google.

Uso: `python main_local.py describir-fuentes-profesor`.

---

## 4. Cómo se calcula el bosque base, en código

*(El razonamiento completo está en
[METODOLOGIA.md, sección 3.1](METODOLOGIA.md#31-máscara-de-bosque--definición-formal);
aquí la implementación en `calcular_bosque.py`.)*

`bosque_ha_por_celda(cfg, grilla, mapa_celda)` es la única función pública
del módulo, y la usa `descargar_gfw.py` antes de consultar el evento.

1. **Bloques** (`_bloques`): se toma el rango de `ix`/`iy` (índices
   enteros de celda) de `grilla_colombia_5km.csv` y se agrupa en bloques
   cuadrados de `bosque_bloque_celdas` celdas de lado (20 por defecto,
   100 km), alineados a múltiplos de ese tamaño **desde el origen** — no
   desde el mínimo de la grilla, para que el mismo bloque quede definido
   igual sin importar qué subconjunto de celdas se procese. Solo se
   generan los bloques que de verdad contienen alguna celda (Colombia no
   es un rectángulo).

2. **Perfil sintético del bloque** (`_perfil_bloque`): un `transform`
   afín construido directamente en `EPSG:3116` a resolución
   `bosque_resolucion_m` (25 m por defecto) — el raster de referencia
   "vive" ya en la proyección de la grilla, así que no hace falta ningún
   `pyproj.Transformer` para saber a qué celda pertenece cada píxel: es
   aritmética directa (`floor(coordenada / 5000)`), igual que hace
   `construir_grilla()` en `exportar_grilla.py`.

3. **Máscara de bosque del bloque** (`_mascara_bosque_bloque`): reproyecta
   cada gránulo Hansen que trae datos sobre ese bloque
   (`rasterio.warp.reproject`, remuestreo *nearest neighbor* porque son
   variables categóricas, combinando gránulos con `np.maximum` — donde
   uno no cubre nada, `reproject` deja `dst_nodata=0`) y aplica el umbral
   de dosel + corte de `anio_mascara`.

4. **Índice de celda del bloque** (`_indice_celdas_bloque`): mismo truco
   de `np.unique(..., return_inverse=True)` que cualquier otro indexado de
   celda de este proyecto — resolver el diccionario `mapa_celda` solo
   sobre los pares `(ix, iy)` únicos y repartir el resultado a todos los
   píxeles.

5. **Acumulación nacional**: por cada bloque, se cuenta con `np.bincount`
   cuántos píxeles de bosque caen en cada celda y se **suma** al array
   nacional — los bloques nunca se solapan (están alineados a bordes de
   celda), así que sumar es correcto directamente, sin necesitar el
   `max()` que sí hace falta cuando la cuadrícula de referencia viene en
   piezas traslapadas.

Se cachea un solo array nacional (`datos/cache/bosque_am{anio_mascara}
_ud{umbral_dosel}_res{resolucion}.npy`), no uno por bloque: el resultado
final es pequeño (un valor por celda), así que no hace falta un esquema de
caché más fino.

---

## 5. Cómo se construye el panel, en código

*(El razonamiento y las fórmulas exactas están en
[METODOLOGIA.md, sección 3.4](METODOLOGIA.md#34-del-bosque-base-a-las-variables-de-exposición-y-tasa);
aquí, la implementación en `consolidar.py`.)*

Cinco funciones, encadenadas por `consolidar()`:

1. **`cargar_crudo`**: lee `datos/crudo/nacional.csv` y pasa la tabla
   ANCHA (una columna por mes) a LARGA (una fila por celda-mes) con
   `pandas.melt`.

2. **`filtrar_dominio`**: descarta celdas con menos de `bosque_minimo_ha`
   (50 ha por defecto) de bosque base, con un filtro simple de `pandas`.

3. **`balancear`**: construye un `pd.MultiIndex.from_product([celdas,
   periodos])` — todas las combinaciones posibles — y hace `reindex`
   contra él, rellenando con 0 las combinaciones celda-mes que no existían
   en los datos crudos. Esto es lo que garantiza que el panel final sea un
   rectángulo perfecto.

4. **`derivar_variables`**: usa `groupby("cell_id").cumsum()`,
   `.shift(k)` y `.rolling(3)` de `pandas`, todo ordenado cronológicamente
   por celda de antemano.

5. **`asignar_municipio`** (automático): si no se pasa `--dane`, descarga
   primero los límites municipales del DANE (`descargar_municipios.py`,
   cacheados en `datos/limites/`) y luego usa `geopandas.sjoin` con
   predicado `within` para unir cada centroide de celda al polígono
   municipal que lo contiene. Import perezoso de `geopandas` dentro de
   la función — si no está instalado, el resto del pipeline sigue
   funcionando, solo sin la columna `cod_dane`.

Salida: `datos/panel/panel_deforestacion_colombia.csv` y `.parquet` (este
último requiere `pyarrow`; si no está instalado, se guarda solo el CSV y
se imprime una advertencia, sin detener la ejecución).

Cómo se consulta la API de GFW (en `descargar_gfw.py`, no en
`consolidar.py`): `celdas_como_poligonos()` convierte cada celda de la
grilla a un rectángulo de 5 km en WGS84, y `procesar_lote()` manda esas
geometrías en lotes de `gfw_celdas_por_lote` (400 por defecto, límite real
de payload de la API: 256 KB) al endpoint asíncrono
`/dataset/{gfw_dataset}/latest/query/batch`, con esta consulta corriendo
una vez por celda (con el default `gfw_dataset = "gfw_integrated_alerts"`):

```sql
SELECT gfw_integrated_alerts__confidence,
       gfw_integrated_alerts__date,
       SUM(area__ha) AS ha
FROM data
WHERE gfw_integrated_alerts__date >= '2020-01-01'
  AND gfw_integrated_alerts__date < '{fecha_fin}'
  AND (gfw_integrated_alerts__confidence = 'high'
       OR gfw_integrated_alerts__confidence = 'highest')
GROUP BY gfw_integrated_alerts__confidence, gfw_integrated_alerts__date
```

**El prefijo de los campos se arma dinámicamente** a partir de
`cfg.gfw_dataset` (ver `sql_lote()`): en todos los datasets de alertas de
GFW verificados, los campos se llaman `<nombre_del_dataset>__confidence` y
`<nombre_del_dataset>__date`. Por eso cambiar de fuente de evento es
cambiar una sola línea en `pipeline/config_local.py`, sin tocar código.

(el operador SQL `IN` no está soportado por este endpoint — se confirmó
empíricamente que devuelve `"Unsupported filter operator: in"` — por eso
el filtro de confianza usa `OR` en vez de `IN (...)`.) Cada lote se cachea
en `datos/gfw/lote_<dataset>_NNNN.json` apenas se descarga, así que el
script es reanudable; el nombre incluye el dataset para que cambiar de
fuente no reutilice en silencio los resultados de la anterior.
`agregar_a_mensual()` junta los resultados de todos los lotes en la tabla
ancha final (`cell_id`, `d_2020_01`, ..., hasta el mes más reciente).

---

## 6. El mapa interactivo (`mapa_folium.py`)

> `atenuar_mapa_base()` es pública porque también la usa
> `catalogo_paneles.ipynb`: cualquier mapa del proyecto se ve igual.

Genera un mapa Leaflet (vía `folium`) para inspeccionar visualmente el
la tabla de alertas, sin abrir el CSV ni un SIG de escritorio:

```bash
python main_local.py mapa
```

Produce `datos/panel/mapa_deforestacion.html` (ábrase con doble clic en
cualquier navegador). Agrega el panel largo a una fila por celda (suma de
`area_def_ha` en toda la ventana temporal) y monta tres capas conmutables:

- **Mapa de calor** de la deforestación total — escala sin problema a
  todas las celdas, porque el peso de cada punto se codifica en un
  arreglo compacto `[lat, lon, peso]`, no un elemento por marcador.
- **Celdas con deforestación** (agrupadas en *cluster*) — limitada por
  defecto a los `--top-n 3000` focos de mayor deforestación total, porque
  un marcador con popup por cada celda con algún evento genera un archivo
  HTML lento de abrir. El mapa de calor ya cubre la vista completa; esta
  capa es para hacer clic y ver el detalle de los focos más importantes.
- **Bosque base** (contexto), apagada por defecto.

```bash
python main_local.py mapa --umbral-ha 1 --top-n 5000   # ajustar el filtro de marcadores
python main_local.py mapa --salida otro_nombre.html
```

Cae automáticamente al CSV si `pyarrow` no está instalado y por lo tanto no
se puede leer el `.parquet`.

---

## 7. Cómo adaptar el pipeline

### Extender la ventana temporal (nuevos meses)

Cambiar `fecha_fin` en `pipeline/config_local.py` y volver a correr
`python main_local.py gfw` — la API de GFW se consulta de nuevo con la
ventana ampliada (los lotes ya cacheados con la fecha vieja no sirven para
el rango nuevo, así que sí vuelve a consultar la API; el cálculo de bosque
sí se reutiliza de caché, porque no depende de la ventana temporal).

### Cambiar el umbral de confianza del evento

Modificar `gfw_confianza_minima` en `pipeline/config_local.py` (p. ej. incluir
también `nominal` si se quiere una definición más laxa de disturbio) y
volver a correr `python main_local.py gfw` — cambia la consulta SQL que se
manda a la API.

### Cambiar el tamaño de celda de la grilla

Modificar `grid_scale_m` en `pipeline/config_local.py` y volver a correr **desde el
Paso 1** (`grilla`) — cambia la geometría de la grilla, así que todo lo que
depende de ella debe rehacerse. Conviene borrar `datos/cache/*.npy`
explícitamente en este caso.

### Adaptar a otro país o región

Cambiar `bbox` en `pipeline/config_local.py` y reescribir `exportar_grilla.py` para
usar la fuente de límites administrativos apropiada para ese país (el
DANE es específico de Colombia).

### Agregar una nueva variable derivada al panel

Se agrega como una columna nueva dentro de `derivar_variables()` en
`consolidar.py`, siguiendo el mismo patrón de las existentes (operar sobre
`df.groupby("cell_id", sort=False)`, ordenado cronológicamente).

---

## 8. Glosario de código

| Término | Significado |
|---|---|
| **CRS** | Sistema de referencia de coordenadas (p. ej. `EPSG:3116`, `EPSG:4326`) |
| **Gránulo** | "Un archivo/observación individual" en Hansen — no es un tamaño espacial fijo |
| **Bloque** | Agrupación cuadrada de celdas de la grilla nacional (ver sección 4), usada para reproyectar Hansen en piezas manejables |
| **Panel ancho / largo** | *Ancho*: una fila por celda, una columna por periodo. *Largo*: una fila por celda-periodo. `descargar_gfw.py` produce ancho; `consolidar.py` lo pasa a largo |
| **Caché de bosque** | El archivo `.npy` en `datos/cache/`: resultado costoso de calcular (bosque_ha por celda) que no cambia entre corridas mientras no cambien la grilla, Hansen o los parámetros de máscara |
| **Reanudable** | Que se puede interrumpir (`Ctrl+C`) y relanzar sin perder el trabajo ya hecho — todas las descargas de este pipeline lo son |

Para términos conceptuales (qué es GLAD, RADD, MAGNA-SIRGAS, etc.), ver el
glosario más completo en
[METODOLOGIA.md, sección 9](METODOLOGIA.md#9-glosario-técnico).

---

*Si un parámetro de `config_local.py` cambia, revise si esta guía y
[METODOLOGIA.md](METODOLOGIA.md) siguen describiendo correctamente el
comportamiento actual del pipeline — son documentación, no se actualizan
solas.*
