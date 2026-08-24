# Guía de código y reproducibilidad — Pipeline de deforestación Colombia

Este documento explica **cómo está construido el software** y **cómo
correrlo desde cero**, paso a paso, con suficiente detalle para que alguien
que no participó en escribirlo —el director de tesis, un jurado, un
colaborador futuro— pueda reproducir el panel final en su propio
computador.

Este documento **no** explica por qué se tomaron las decisiones de diseño
(qué fuentes de datos, qué umbrales, qué supuestos): eso está en
[METODOLOGIA.md](METODOLOGIA.md). Aquí se asume esa metodología como dada y
se explica su implementación.

---

## Índice

1. [Mapa del repositorio](#1-mapa-del-repositorio)
2. [Preparar el entorno desde cero](#2-preparar-el-entorno-desde-cero)
3. [Orden exacto de ejecución](#3-orden-exacto-de-ejecución)
4. [Cómo se ve la base de datos final](#cómo-se-ve-la-base-de-datos-final)
5. [Referencia de cada script](#5-referencia-de-cada-script)
6. [Cómo se calcula el bosque base, en código](#6-cómo-se-calcula-el-bosque-base-en-código)
7. [Cómo se construye el panel, en código](#7-cómo-se-construye-el-panel-en-código)
8. [El mapa interactivo (`mapa_folium.py`)](#8-el-mapa-interactivo-mapa_foliumpy)
9. [El notebook de EDA (`eda_deforestacion.ipynb`)](#9-el-notebook-de-eda-eda_deforestacionipynb)
10. [Estructura de `datos/`](#10-estructura-de-datos)
11. [Cómo adaptar el pipeline](#11-cómo-adaptar-el-pipeline)
12. [Solución de problemas](#12-solución-de-problemas)
13. [Glosario de código](#13-glosario-de-código)

---

## 1. Mapa del repositorio

```
trabajo_de_grado/
├── config_local.py          configuración central — todo parámetro vive aquí
├── exportar_grilla.py        genera la grilla de 5 km — 1 vez (limites del DANE)
├── descargar_hansen.py       descarga los granulos de Hansen GFC (linea base)
├── calcular_bosque.py        bosque_ha por celda, reproyectando Hansen sobre la grilla nacional
├── configurar_gfw.py         registro de una sola vez en la API de GFW
├── descargar_gfw.py          calcula bosque_ha + descarga el evento -> datos/crudo/nacional.csv
├── descargar_municipios.py   limites municipales del DANE (MGN) -- automatico, sin cuenta
├── consolidar.py             arma el panel final (formato largo) + cruce municipal
├── main_local.py             orquestador de línea de comandos
├── mapa_folium.py            mapa interactivo (Leaflet) del panel final
├── eda_deforestacion.ipynb   EDA con graficas del panel final
│
├── requirements_local.txt   dependencias Python (pip)
├── .dodsrc                  (sin uso en este pipeline; ver legacy/)
│
├── METODOLOGIA.md           ← el "qué y por qué" (léalo primero)
├── GUIA_CODIGO.md           ← este documento, el "cómo"
│
├── legacy/                   código archivado, ya no forma parte del pipeline
│                              activo (ver legacy/README.md)
│
└── datos/                   TODO el output cae aquí (ver sección 10)
    ├── grilla/   hansen/   gfw/   cache/   crudo/   limites/   panel/   logs/
```

**Regla general del repositorio**: todo parámetro que pueda cambiar el
resultado vive en `config_local.py`, nunca hardcodeado dentro de otro
script. Si algo en el panel final se ve distinto a lo esperado, el primer
lugar a revisar es ese archivo, no el resto del código.

---

## 2. Preparar el entorno desde cero

### 2.1 Requisitos de sistema

- Python 3.10 o superior.
- ~10 GB libres en disco (sobre todo para los granulos de Hansen y la
  cache de bosque; el panel final pesa unas pocas centenas de MB).
- Conexión a internet.

### 2.2 Obtener el código

```bash
git clone <url-del-repositorio>
cd trabajo_de_grado
```

### 2.3 Crear un entorno virtual (recomendado)

```bash
cd ruta/al/proyecto
python3 -m venv .venv
source .venv/bin/activate
```

Debería quedar `(.venv)` al inicio de la línea de comandos, señal de que el
entorno está activo.

### 2.4 Instalar las dependencias

```bash
pip install --upgrade pip
pip install -r requirements_local.txt
```

Contenido de `requirements_local.txt`, y para qué sirve cada paquete:

```
rasterio>=1.3              # lectura/reproyeccion de Hansen GFC (calcular_bosque.py)
numpy>=1.24
pandas>=2.0
requests>=2.31              # descarga de Hansen y llamadas a la API de GFW
pyarrow>=14.0              # motor de lectura/escritura de Parquet
geopandas>=0.14             # exportar_grilla.py (grilla local), cruce DANE opcional de consolidar.py, y las geometrias de celda que descargar_gfw.py manda a la API de GFW
folium>=0.15                # mapa interactivo (mapa_folium.py)
matplotlib>=3.7            # graficas de eda_deforestacion.ipynb
jupyter>=1.0                 # para abrir/correr eda_deforestacion.ipynb
```

`rasterio` en particular puede requerir GDAL como dependencia binaria del
sistema; en Windows, instalarlo con `pip` normalmente ya trae las
librerías necesarias empaquetadas (rueda binaria), sin pasos adicionales.
Si falla la instalación de `rasterio` en Linux, suele ser más simple
instalar GDAL con el gestor de paquetes del sistema primero (`apt install
gdal-bin libgdal-dev`) y después `pip install rasterio`.

### 2.5 Cuenta y credencial necesaria

Este pipeline necesita **una sola** credencial: una API key gratuita de
Global Forest Watch.

```bash
python configurar_gfw.py signup --nombre "Su Nombre" --email correo@ejemplo.com
# revise su correo: GFW manda una contraseña temporal
python configurar_gfw.py apikey --email correo@ejemplo.com --password "la-del-correo"
```

La API key queda en `datos/logs/gfw_api_key.txt` (fuera de control de
versiones) o puede definirse en la variable de entorno `GFW_API_KEY`, si
se prefiere no dejarla en disco.

### 2.6 Verificar la instalación (antes de lanzar nada largo)

```bash
python -c "import rasterio, numpy, pandas, requests, geopandas, folium; print('OK')"
```

---

## 3. Orden exacto de ejecución

Todos los comandos se corren **desde la raíz del proyecto**, con el
entorno virtual activado. El orquestador es `main_local.py`.

```
┌──────────────────────────┐
│ 0. pip install ...          │
└──────────────┬────────────┘
               ▼
┌──────────────────────────┐
│ 1. grilla  (local, DANE)   │  ~1 min · sin cuentas
└──────────────┬────────────┘
               ▼
┌──────────────────────────┐
│ 2. hansen                   │  ~5 GB, ~10 min · sin cuentas
└──────────────┬────────────┘
               ▼
┌──────────────────────────┐
│ 3. gfw                      │  ~10-20 min · requiere API key de GFW
│    (calcula bosque + evento)│
└──────────────┬────────────┘
               ▼
┌──────────────────────────┐
│ 4. municipios (local, DANE) │  ~10 s · sin cuentas · opcional a mano
│    (auto en el paso 5)      │    (consolidar la descarga si falta)
└──────────────┬────────────┘
               ▼
┌──────────────────────────┐
│ 5. consolidar                │  ~1-2 min
└──────────────────────────┘
```

Los tiempos son orden de magnitud, dependientes de la velocidad de red y
del número de núcleos/disco del computador.

### Paso 0 — instalar dependencias

Ver sección 2.

### Paso 1 — construir la grilla (local, una sola vez)

```bash
python main_local.py grilla
# equivale a: python exportar_grilla.py
```

Descarga los límites departamentales del DANE (Marco Geoestadístico
Nacional) y construye una malla regular de celdas de 5 km sobre el
territorio continental. Salida: `datos/grilla/grilla_colombia_5km.csv`.

**Verificación**: el log debe terminar con "Grilla alineada al origen. El
indexado local es válido." Si el script se detiene con "GRILLA NO ALINEADA
AL ORIGEN", no continúe — ver sección 12.

### Paso 2 — descargar Hansen GFC

```bash
python main_local.py hansen
# equivale a: python descargar_hansen.py
```

Descarga los granulos de 10°×10° de Hansen Global Forest Change que cubren
Colombia (dos capas por gránulo: `treecover2000`, `lossyear`), de un bucket
público de Google Cloud Storage, sin autenticación. Reanudable con
Ctrl+C.

**Verificación**: `datos/hansen/` debe tener 2 archivos `.tif` por cada
gránulo espacial listado en el log ("Granulos Hansen sobre Colombia: N ->
[...]").

### Paso 3 — bosque base + evento (API de GFW)

```bash
python main_local.py gfw
# equivale a: python descargar_gfw.py
```

Este es el paso central. Hace dos cosas, en este orden:

1. Calcula `bosque_ha` por celda reproyectando Hansen directamente sobre
   la grilla nacional de 5 km, en bloques (ver sección 6) — no descarga
   nada nuevo para esto, usa lo que ya bajó el Paso 2.
2. Consulta la API SQL de GFW por lotes de celdas para obtener el evento
   (hectáreas deforestadas por celda y mes, con confianza `high`/
   `highest`) desde 2020-01 hasta el mes más reciente configurado.

Produce `datos/crudo/nacional.csv`, formato ANCHO:

```
cell_id | lon | lat | departamento | bosque_ha | d_2020_01 | d_2020_02 | ...
```

Reanudable: cada lote de la API se cachea en `datos/gfw/lote_NNNN.json`
apenas se descarga, y el cálculo de bosque se cachea completo en
`datos/cache/`.

**Verificación**: el log final imprime celdas con bosque, bosque total en
hectáreas y deforestación total detectada. Si "deforestación total" da 0,
revise que `gfw_confianza_minima` en `config_local.py` no se haya cambiado
por error a algo vacío.

### Paso 4 — límites municipales del DANE (automático)

```bash
python main_local.py municipios
# equivale a: python descargar_municipios.py
```

Descarga los polígonos de los 1.122 municipios del Marco Geoestadístico
Nacional del DANE (versión MGN2025, nivel Municipio, capa "Gráfico"),
del mismo servicio ArcGIS público (sin cuenta) que ya usa el Paso 1 para
los límites departamentales. Salida:
`datos/limites/municipios_dane_mgn2025.geojson`.

Este paso es **opcional correrlo a mano**: si no existe el archivo,
`consolidar` (Paso 5) lo descarga automáticamente antes de hacer el
cruce. Se documenta como paso aparte solo para que quede claro en la
trazabilidad de dónde sale cada dato.

**Por qué la versión "Gráfico" y no "Político"**: para asignar un
municipio al centroide de una celda de 5×5 km, la generalización de la
versión "Gráfico" es irrelevante frente al tamaño de la celda — no
cambia a qué municipio cae ningún centroide, y es la misma fuente
(IGAC, vía DANE) que exige el documento de entendimiento del negocio
para el análisis a nivel municipal.

### Paso 5 — consolidar el panel final

```bash
python main_local.py consolidar
```

El cruce municipal ya es automático: si `datos/limites/` está vacío,
`consolidar` descarga los límites del DANE por su cuenta (ver Paso 4)
antes de asignar `cod_dane` a cada celda. Para usar un archivo municipal
distinto en vez del descargado automáticamente:

```bash
python main_local.py consolidar --dane ruta/al/otro_archivo.shp
```

Ver la sección 7 para el detalle. Produce
`datos/panel/panel_deforestacion_colombia.csv` y `.parquet`, ahora con
la columna `cod_dane` (código DANE de municipio) incluida por defecto.

**Verificación**: el log final imprime filas, celdas, periodos, rango de
fechas, % de celda-mes con evento y hectáreas totales. Compare contra la
sección ["Cómo se ve la base de datos final"](#cómo-se-ve-la-base-de-datos-final)
más abajo.

### Comando de estado (en cualquier momento)

```bash
python main_local.py estado
```

Resume qué hay en disco en cada etapa, sin modificar nada.

---

## Cómo se ve la base de datos final

*(Números de una corrida puntual, como ejemplo — el pipeline sigue
corriendo y el panel crece. Para las cifras y gráficas actualizadas, correr
[`eda_deforestacion.ipynb`](eda_deforestacion.ipynb).)*

El panel resultante (`datos/panel/panel_deforestacion_colombia.csv`) es
una tabla de **3 524 664 filas × 17 columnas**: 44 616 celdas × 79 periodos
mensuales (2020-01 a 2026-07), 32 departamentos. Cada fila es una
celda-mes (`filas = celdas × periodos` exactamente — es la huella de que
`balancear()`, sección 7, hizo su trabajo: el panel es un rectángulo
perfecto, sin huecos).

**Las 17 columnas**, en el orden en que aparecen en el CSV:

| # | Columna | Tipo | De dónde sale | Qué es |
|---|---|---|---|---|
| 1 | `cell_id` | texto | grilla (DANE) | id de la celda: `"{lon×1e4}_{lat×1e4}"` redondeado |
| 2 | `periodo` | fecha | `cargar_crudo` | primer día del mes, p. ej. `2023-09-01` |
| 3 | `area_def_ha` | float | `descargar_gfw.py` | hectáreas deforestadas **en ese mes**, en esa celda |
| 4 | `lon` | float | grilla (DANE) | longitud del centroide, EPSG:4326 |
| 5 | `lat` | float | grilla (DANE) | latitud del centroide, EPSG:4326 |
| 6 | `bosque_base_ha` | float | Hansen (`calcular_bosque.py`) | bosque disponible al arrancar el pipeline (dosel ≥30 %, sin pérdida antes de 2019) |
| 7 | `departamento` | texto | grilla (DANE) | departamento del centroide |
| 8 | `def_acum_ha` | float | `derivar_variables` | pérdida acumulada de la celda hasta este periodo inclusive |
| 9 | `bosque_remanente_ha` | float | `derivar_variables` | bosque que quedaba disponible **al inicio** de este periodo |
| 10 | `tasa_def` | float | `derivar_variables` | `area_def_ha / bosque_remanente_ha`, acotada a [0, 1] — target continuo |
| 11 | `evento` | int (0/1) | `derivar_variables` | 1 si hubo algo de deforestación este mes — target binario |
| 12 | `lag_1_ha` | float | `derivar_variables` | `area_def_ha` de la misma celda, 1 mes atrás |
| 13 | `lag_2_ha` | float | `derivar_variables` | ídem, 2 meses atrás |
| 14 | `lag_3_ha` | float | `derivar_variables` | ídem, 3 meses atrás |
| 15 | `media_movil_3` | float | `derivar_variables` | promedio de `area_def_ha` de los 3 meses anteriores |
| 16 | `anio` | int | `derivar_variables` | año de `periodo` |
| 17 | `mes` | int | `derivar_variables` | mes de `periodo` (1-12) |

Desde que el cruce municipal quedó automático (ver Paso 5), se agrega
además una columna 18, `cod_dane` (código de municipio del DANE) — la
tabla de ejemplo de arriba es de una corrida anterior a ese cambio, por
eso muestra 17. La **definición matemática exacta** de cada una de estas
variables está en
[METODOLOGIA.md, sección 3.4](METODOLOGIA.md#34-del-bosque-base-a-las-variables-de-exposición-y-tasa).

Para inspeccionarlo directamente en Python:

```python
import pandas as pd
df = pd.read_parquet("datos/panel/panel_deforestacion_colombia.parquet")
# si pyarrow no esta instalado, usar en su lugar:
# df = pd.read_csv("datos/panel/panel_deforestacion_colombia.csv", parse_dates=["periodo"])

df.head()
df[df["evento"] == 1].sample(10)      # ejemplos con deforestacion real
df.groupby("anio")["evento"].mean()   # tasa de celda-mes con evento, por anio
df.groupby("departamento")["area_def_ha"].sum().sort_values(ascending=False)
```

---

## 5. Referencia de cada script

### 5.1 `config_local.py` — configuración central

Todos los parámetros que afectan el resultado viven en un `dataclass`
congelado (`frozen=True`, no se puede mutar por accidente). También crea
automáticamente el árbol de carpetas bajo `datos/` la primera vez que se
importa cualquier script del pipeline.

| Parámetro | Significado | Ver también |
|---|---|---|
| `hansen_version`, `umbral_dosel`, `anio_mascara` | Definen la máscara de bosque base | METODOLOGIA §3.1 |
| `bosque_resolucion_m`, `bosque_bloque_celdas` | Resolución (m/píxel) y tamaño de bloque (celdas/lado) con que se reproyecta Hansen sobre la grilla nacional | sección 6 de este documento |
| `grid_scale_m`, `grid_crs` | Tamaño de celda (5000 m) y proyección de la grilla | METODOLOGIA §1.2 |
| `bosque_minimo_ha` | Umbral para descartar celdas sin bosque suficiente | sección 7 de este documento |
| `bbox` | Rectángulo usado para seleccionar gránulos de Hansen | METODOLOGIA §4, decisión 11 |
| `gfw_dataset`, `gfw_version` | Identificador del dataset GFW en la API SQL | METODOLOGIA §2.2 |
| `fecha_inicio`, `fecha_fin`, `frecuencia` | Ventana temporal del panel y su resolución mensual | METODOLOGIA §1.3 |
| `gfw_confianza_minima` | Niveles de confianza de GFW que cuentan como evento | METODOLOGIA §2.2, decisión 2 |
| `gfw_celdas_por_lote`, `gfw_lotes_en_paralelo` | Tamaño de lote y paralelismo de las consultas a la API de GFW | sección 7 |
| `reintentos`, `timeout_s`, `hilos_descarga` | Robustez de red para las descargas de Hansen | — |

### 5.2 `exportar_grilla.py` — grilla de 5 km

Genera la grilla localmente con `geopandas` y los límites del DANE (Marco
Geoestadístico Nacional), sin ninguna cuenta de Google ni de la NASA.
Construye una malla regular de celdas alineadas al origen de EPSG:3116
(cada celda es literalmente `[ix*5000, (ix+1)*5000) x [iy*5000, (iy+1)*5000)`
para algún par de enteros `ix, iy` — alineación garantizada por
construcción, no por verificación posterior) y descarta las que no tocan
el territorio continental.

### 5.3 `descargar_hansen.py` — descarga de Hansen GFC

Calcula qué gránulos de 10°×10° intersectan el `bbox` de Colombia y los
descarga de un bucket público (sin autenticación), con el patrón de
descarga atómica de siempre (escribe a `.parcial`, solo renombra al
nombre final si terminó bien) y en paralelo con un `ThreadPoolExecutor`.

### 5.4 `calcular_bosque.py` — bosque base (detalle en sección 6)

### 5.5 `configurar_gfw.py` — registro en la API de GFW

Automatiza el flujo de autenticación de la API de GFW en tres llamadas
(`/auth/sign-up` → `/auth/token` → `/auth/apikey`), guardando la API key
resultante en `datos/logs/gfw_api_key.txt`. El esquema exacto de las
respuestas no está documentado públicamente por la API; el script imprime
la respuesta cruda del servidor si no encuentra el campo esperado, en vez
de fallar en silencio.

### 5.6 `descargar_gfw.py` — bosque + evento (detalle en sección 6)

### 5.7 `descargar_municipios.py` — límites municipales del DANE

Trae los 1.122 polígonos municipales del Marco Geoestadístico Nacional
2025 (nivel Municipio, capa "Gráfico") del mismo servicio ArcGIS público
del DANE que usa `exportar_grilla.py` para los departamentos —sin
cuenta, sin descarga manual desde el navegador—, y los guarda en
`datos/limites/municipios_dane_mgn2025.geojson`. `consolidar.py` lo
invoca automáticamente si ese archivo todavía no existe.

### 5.8 `consolidar.py` — panel final (detalle en sección 7)

### 5.9 `main_local.py` — orquestador

Cada subcomando (`grilla`, `hansen`, `gfw`, `municipios`, `consolidar`,
`estado`) arma la línea de comandos correcta y lanza el script
correspondiente como subproceso (`subprocess.call`), excepto
`consolidar`, que importa la función directamente. `estado` es el único
subcomando que no delega: lista lo que hay en disco en cada carpeta.

---

## 6. Cómo se calcula el bosque base, en código

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

## 7. Cómo se construye el panel, en código

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
`/dataset/gfw_integrated_dist_alerts/latest/query/batch`, con esta
consulta corriendo una vez por celda:

```sql
SELECT gfw_integrated_dist_alerts__confidence,
       gfw_integrated_dist_alerts__date,
       SUM(area__ha) AS ha
FROM data
WHERE gfw_integrated_dist_alerts__date >= '2020-01-01'
  AND gfw_integrated_dist_alerts__date < '{fecha_fin}'
  AND (gfw_integrated_dist_alerts__confidence = 'high'
       OR gfw_integrated_dist_alerts__confidence = 'highest')
GROUP BY gfw_integrated_dist_alerts__confidence, gfw_integrated_dist_alerts__date
```

(el operador SQL `IN` no está soportado por este endpoint — se confirmó
empíricamente que devuelve `"Unsupported filter operator: in"` — por eso
el filtro de confianza usa `OR` en vez de `IN (...)`.) Cada lote se cachea
en `datos/gfw/lote_NNNN.json` apenas se descarga, así que el script es
reanudable. `agregar_a_mensual()` junta los resultados de todos los lotes
en la tabla ancha final (`cell_id`, `d_2020_01`, ..., hasta el mes más
reciente).

---

## 8. El mapa interactivo (`mapa_folium.py`)

Genera un mapa Leaflet (vía `folium`) para inspeccionar visualmente el
panel final, sin abrir el CSV ni un SIG de escritorio:

```bash
python mapa_folium.py
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
python mapa_folium.py --umbral-ha 1 --top-n 5000   # ajustar el filtro de marcadores
python mapa_folium.py --salida otro_nombre.html
```

Cae automáticamente al CSV si `pyarrow` no está instalado y por lo tanto no
se puede leer el `.parquet`.

---

## 9. El notebook de EDA (`eda_deforestacion.ipynb`)

Análisis exploratorio del panel final, con 13 secciones de gráficas
(`matplotlib`, sin dependencias adicionales de visualización). Se abre con
Jupyter:

```bash
jupyter notebook eda_deforestacion.ipynb
```

o desde VS Code / cualquier editor con soporte de notebooks. Reutiliza
`cargar_panel()` de `mapa_folium.py` (mismo mecanismo de carga
parquet→csv), así que no duplica esa lógica.

**Qué cubre**: estructura y balance del panel, desbalance de la variable
`evento`, evolución temporal nacional (con el acumulado), estacionalidad,
distribución de `tasa_def`, ranking de departamentos, concentración
espacial (curva estilo Lorenz), un mapa estático de la deforestación
acumulada por celda, la relación entre bosque remanente y tasa de
deforestación, autocorrelación entre `area_def_ha` y sus rezagos —
cerrando con un resumen ejecutivo calculado en el momento (no copiado a
mano), para que quede actualizado si se corre contra un panel más
reciente.

**Hallazgo a verificar al leerlo**: la sección 5 del notebook cuantifica
empíricamente si el primer periodo del panel se ve anormalmente alto
respecto al resto de la serie — un posible efecto de arranque del
monitoreo (ver METODOLOGIA.md, sección 6), no necesariamente un evento
real concentrado ahí. Si la razón resulta marcadamente alta, el notebook
ya excluye ese periodo donde corresponde (estacionalidad, resumen
ejecutivo).

**Para regenerarlo con datos nuevos**: basta con reabrirlo y correr todas
las celdas (`Run All`), o desde la terminal:

```bash
jupyter nbconvert --to notebook --execute --inplace eda_deforestacion.ipynb
```

---

## 10. Estructura de `datos/`

| Carpeta | Contenido | La genera |
|---|---|---|
| `datos/grilla/` | CSV de la grilla de 5 km | `exportar_grilla.py` |
| `datos/hansen/` | Gránulos Hansen GFC (`.tif`) | `descargar_hansen.py` |
| `datos/gfw/` | `lote_NNNN.json` — resultados crudos por lote de celdas de la API de GFW | `descargar_gfw.py` |
| `datos/cache/` | `bosque_am{anio}_ud{umbral}_res{resolucion}.npy` — bosque_ha por celda, ya calculado | `calcular_bosque.py` |
| `datos/crudo/` | `nacional.csv`, formato ancho | `descargar_gfw.py` |
| `datos/limites/` | `municipios_dane_mgn2025.geojson` — límites municipales del DANE | `descargar_municipios.py` |
| `datos/panel/` | Panel final, formato largo, + `mapa_deforestacion.html` | `consolidar.py`, `mapa_folium.py` |
| `datos/logs/` | `gfw_api_key.txt` | `configurar_gfw.py` |

Si algo se ve raro o hay que reconstruir desde cero, casi siempre basta con
borrar la carpeta correspondiente y volver a correr el paso que la genera
— **excepto** `datos/hansen/`, que representa varios minutos de descarga y
conviene conservar. Borrar `datos/cache/` es seguro y barato de regenerar
(se recalcula solo en la siguiente corrida de `descargar_gfw.py`). Borrar
`datos/gfw/` es igual de seguro (son solo cachés de lotes ya descargados de
la API).

---

## 11. Cómo adaptar el pipeline

### Extender la ventana temporal (nuevos meses)

Cambiar `fecha_fin` en `config_local.py` y volver a correr
`python main_local.py gfw` — la API de GFW se consulta de nuevo con la
ventana ampliada (los lotes ya cacheados con la fecha vieja no sirven para
el rango nuevo, así que sí vuelve a consultar la API; el cálculo de bosque
sí se reutiliza de caché, porque no depende de la ventana temporal).

### Cambiar el umbral de confianza del evento

Modificar `gfw_confianza_minima` en `config_local.py` (p. ej. incluir
también `nominal` si se quiere una definición más laxa de disturbio) y
volver a correr `python main_local.py gfw` — cambia la consulta SQL que se
manda a la API.

### Cambiar el tamaño de celda de la grilla

Modificar `grid_scale_m` en `config_local.py` y volver a correr **desde el
Paso 1** (`grilla`) — cambia la geometría de la grilla, así que todo lo que
depende de ella debe rehacerse. Conviene borrar `datos/cache/*.npy`
explícitamente en este caso.

### Adaptar a otro país o región

Cambiar `bbox` en `config_local.py` y reescribir `exportar_grilla.py` para
usar la fuente de límites administrativos apropiada para ese país (el
DANE es específico de Colombia).

### Agregar una nueva variable derivada al panel

Se agrega como una columna nueva dentro de `derivar_variables()` en
`consolidar.py`, siguiendo el mismo patrón de las existentes (operar sobre
`df.groupby("cell_id", sort=False)`, ordenado cronológicamente).

---

## 12. Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `exportar_grilla.py` se detiene con "GRILLA NO ALINEADA AL ORIGEN" | No debería ocurrir con la versión actual (la alineación es por construcción) — indicaría que alguien cambió `construir_grilla()` sin preservar esa propiedad | No ignorar este error: revisar que cada celda siga construyéndose como múltiplo entero exacto de `grid_scale_m` |
| `exportar_grilla.py` falla al descargar del DANE (timeout o error HTTP) | El servicio de ArcGIS del DANE puede estar temporalmente caído, o cambió de URL/item id | Reintentar en unos minutos; si persiste, buscar "Marco Geoestadístico Nacional Departamento" en el geoportal del DANE o en su ArcGIS Hub para encontrar la URL vigente y actualizar `DANE_MGN_DEPARTAMENTOS` en el script |
| `exportar_grilla.py` tarda varios minutos en el filtro espacial | Falta la simplificación del polígono nacional — el MGN del DANE sin simplificar tiene ~280 000 vértices | No debería pasar en la versión actual (ya incluye `pais.simplify(100, ...)`); si se quitó esa línea, restaurarla |
| `pd.read_parquet` falla con `ImportError` | Falta `pyarrow` en el entorno, aunque esté listado en `requirements_local.txt` | `pip install pyarrow`, o usar el `.csv` equivalente — `mapa_folium.py` y el notebook ya caen automáticamente al CSV si el Parquet no se puede leer |
| La descarga de Hansen (Paso 2) es muy lenta | Límite de ancho de banda, o `hilos_descarga` muy bajo/alto para la red disponible | Ajustar `hilos_descarga` en `config_local.py` |
| `descargar_gfw.py` falla con `SystemExit` pidiendo la API key | Falta `datos/logs/gfw_api_key.txt` o la variable de entorno `GFW_API_KEY` | Correr `configurar_gfw.py` (sección 5.5) primero |
| `descargar_gfw.py` falla con `"Unsupported filter operator: in"` | El endpoint `/query/batch` de GFW no soporta `IN (...)` en el SQL | No debería pasar en la versión actual (`sql_lote()` ya usa `OR` encadenados, confirmado empíricamente); si se editó esa función para usar `IN`, revertir |
| `descargar_gfw.py` falla con `"extra fields not permitted"` en `feature_collection.features[i].id` | `geopandas`/`shapely` agregan un campo `"id"` a nivel de *feature* al exportar a GeoJSON, que la API de GFW rechaza | No debería pasar en la versión actual (`procesar_lote()` ya hace `feat.pop("id", None)` antes de enviar); si se quitó esa línea, restaurarla |
| `descargar_gfw.py` falla con `FileNotFoundError` sobre gránulos Hansen | No se corrió el Paso 2 | `python main_local.py hansen` |
| El mapa de `mapa_folium.py` pesa demasiado / tarda en abrir | Demasiados marcadores individuales en la capa de "Celdas con deforestación" | Bajar `--top-n` o subir `--umbral-ha` |

---

## 13. Glosario de código

| Término | Significado |
|---|---|
| **CRS** | Sistema de referencia de coordenadas (p. ej. `EPSG:3116`, `EPSG:4326`) |
| **Gránulo** | "Un archivo/observación individual" en Hansen — no es un tamaño espacial fijo |
| **Bloque** | Agrupación cuadrada de celdas de la grilla nacional (ver sección 6), usada para reproyectar Hansen en piezas manejables |
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
