# 2. Descarga de los datos

Cómo preparar el entorno y dejar listos, desde cero, todos los datos que usa
el trabajo:

1. las **cuatro tablas de deforestación**, a partir de las fuentes
   satelitales públicas (Pasos 1 a 10);
2. si se quiere, su **subida a BigQuery** y la **descripción de las fuentes**
   (Pasos 11 a 13);
3. las **tablas del Observatorio** y el **panel municipal** (Paso 14).

Qué es cada fuente está en [`1_FUENTES.md`](1_FUENTES.md). Con los datos
listos, el análisis exploratorio, la segmentación y los modelos se corren
siguiendo [`3_NOTEBOOKS.md`](3_NOTEBOOKS.md).

## Índice

1. [Preparar el entorno y las credenciales](#1-preparar-el-entorno-y-las-credenciales)
2. [Descargar los datos y armar las tablas](#2-descargar-los-datos-y-armar-las-tablas)
3. [Cómo comprobar que salió bien](#3-cómo-comprobar-que-salió-bien)
4. [Dónde queda cada cosa](#4-dónde-queda-cada-cosa)
5. [Problemas comunes](#5-problemas-comunes)

---

## 1. Preparar el entorno y las credenciales

### 1.1 Requisitos de sistema

- Python 3.10 a 3.13. Los notebooks de la corrida de referencia se
  ejecutaron con 3.10 y 3.13, y la instalación se probó también con 3.12.
- **~5 GB libres en disco**, repartidos así en una corrida completa:
  gránulos de Hansen ~2,0 GB, cachés de lotes de la API de GFW ~1,0 GB,
  las cuatro tablas ~0,85 GB, capas del IDEAM ~0,25 GB, detecciones
  tempranas ~0,17 GB. Conviene dejar margen.
- Conexión a internet.

### 1.2 Obtener el código

```bash
git clone https://github.com/Bo-T19/trabajo_de_grado_ofr.git
cd trabajo_de_grado_ofr
```

En Windows conviene clonarlo en una ruta corta, como `C:\proyectos\`, por el
límite de largo de rutas de Windows (ver la sección 1.4).

Todos los comandos de este documento se corren desde esa carpeta, la raíz
del repositorio.

### 1.3 Crear un entorno virtual (recomendado)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux o Mac
```

Debería quedar `(.venv)` al inicio de la línea de comandos, señal de que el
entorno está activo.

### 1.4 Instalar las dependencias

```bash
pip install --upgrade pip
pip install -r requirements_local.txt
```

Un solo archivo instala todo lo que usan el pipeline y los notebooks. Cada
línea de `requirements_local.txt` dice para qué sirve el paquete; en
resumen:

| Grupo | Paquetes | Lo usan |
|---|---|---|
| Datos y geografía | `numpy`, `pandas`, `pyarrow`, `geopandas`, `shapely`, `rasterio`, `requests` | El pipeline de las cuatro tablas (etapa 1) y todos los notebooks |
| Mapas y gráficas | `folium`, `branca`, `matplotlib`, `seaborn` | El mapa interactivo y las gráficas de los notebooks |
| BigQuery | `google-cloud-bigquery`, `google-auth`, `db-dtypes`, `tabulate` | La subida a BigQuery, la descripción de las fuentes y `panel_municipal_armado.ipynb` (descarga de las tablas del Observatorio) |
| Modelos | `scipy`, `scikit-learn`, `lightgbm`, `shap`, `statsmodels`, `joblib`, `openpyxl` | La segmentación y los modelos de `modelos y clusters/` |
| Notebooks | `jupyter` | Abrir y ejecutar los notebooks, también con `jupyter nbconvert` |

La estadística descriptiva (`estadisticas_descriptivas.ipynb`) usa además R
con el paquete `psych` para comprobar sus cifras, pero es opcional: si R no
está instalado, el notebook salta esa comprobación.

`requirements_local.txt` solo fija versiones mínimas, así que `pip` instala
las más recientes. La preparación de datos de los modelos y de la
segmentación se probó con pandas 2.2 y con pandas 3.1, y da exactamente la
misma muestra. Si algún notebook falla con una versión más nueva, las de la
corrida de la segmentación fueron pandas 2.2, numpy 2.1, scikit-learn 1.6,
lightgbm 4.6, shap 0.51 y statsmodels 0.14.

En Windows, si `pip` falla con `No such file or directory` y menciona
*Long Path*, la ruta de la carpeta es demasiado larga para Windows (más de
260 caracteres en algún archivo de `jupyterlab`). Se resuelve clonando el
repositorio en una ruta corta, como `C:\proyectos\`, o activando las rutas
largas de Windows.

`rasterio` en particular puede requerir GDAL como dependencia binaria del
sistema; en Windows, instalarlo con `pip` normalmente ya trae las
librerías necesarias empaquetadas (rueda binaria), sin pasos adicionales.
Si falla la instalación de `rasterio` en Linux, suele ser más simple
instalar GDAL con el gestor de paquetes del sistema primero (`apt install
gdal-bin libgdal-dev`) y después `pip install rasterio`.

### 1.5 Credenciales necesarias

Hacen falta dos credenciales. Ninguna está en el repositorio.

| Credencial | Archivo | Para qué pasos | Cómo se consigue |
|---|---|---|---|
| API key de Global Forest Watch | `datos/logs/gfw_api_key.txt` | Las cuatro tablas (Pasos 1-10) | Es gratuita; se crea con los comandos de abajo |
| Llave de la cuenta de servicio `pipeline-satelital` | `datos/logs/bigquery-key.json` | Subida a BigQuery y descripción de las fuentes (Pasos 11-13), y **el panel municipal (Paso 14), del que dependen todos los notebooks de análisis, segmentación y modelos (Paso 14 y `3_NOTEBOOKS.md`)** | No es pública. Hay que pedírsela al equipo del trabajo de grado |

**Sin la llave de BigQuery** se pueden construir las cuatro tablas, pero no
el panel municipal, porque `panel_municipal_armado.ipynb` lo arma con las
cinco tablas del Observatorio (FINAGRO, SFC 414, la de municipios, EVA e ICA
pecuario), que solo se leen desde BigQuery. Por lo tanto tampoco se pueden volver a correr el
análisis del panel, la segmentación ni los modelos. Lo que sí se puede es
consultar la corrida de referencia: los notebooks están guardados con sus
salidas, y las tablas de resultados están en `modelos y clusters/resultados/`
y `documento/tablas/`.

#### API key de Global Forest Watch

```bash
python main_local.py configurar-gfw signup --nombre "Su Nombre" --email correo@ejemplo.com
# revise su correo: GFW manda una contraseña temporal
python main_local.py configurar-gfw apikey --email correo@ejemplo.com --password "la-del-correo"
```

La API key queda en `datos/logs/gfw_api_key.txt` (fuera de control de
versiones) o puede definirse en la variable de entorno `GFW_API_KEY`, si
se prefiere no dejarla en disco.

#### Llave de BigQuery

Cuando el equipo le entregue el archivo `.json`, cópielo a mano como
`datos/logs/bigquery-key.json`. Con esa misma llave se leen las tablas
propias en el proyecto del equipo (`ofr-credito-deforestacion`) y las cinco
tablas del Observatorio (`prueba-ofr`), a las que el profesor dio acceso de
lectura. No hace falta una cuenta personal de Google. Qué permisos tiene la
cuenta y por qué se usa una cuenta de servicio está en `referencia/GUIA_CODIGO.md`,
sección 3.16; el detalle de las tablas del Observatorio, en la 3.18.

La llave funciona como una contraseña: no se sube al repositorio ni se
comparte por chat o correo.

### 1.6 Verificar la instalación (antes de lanzar nada largo)

```bash
python -c "import rasterio, geopandas, folium, google.cloud.bigquery, sklearn, lightgbm, shap, statsmodels, openpyxl; print('OK')"
python main_local.py --help
python main_local.py estado
```

Si la primera línea imprime `OK`, están todas las librerías. La segunda
lista los subcomandos, y la tercera dice qué hay en disco y qué falta.

---

## 2. Descargar los datos y armar las tablas

Todos los comandos se corren **desde la raíz del proyecto**, con el
entorno virtual activado. El orquestador de la etapa 1 es `main_local.py`;
el Paso 14 es un notebook.

| Paso | Comando | Necesita | Tarda | Produce | ¿Hace falta para los modelos? |
|---|---|---|---|---|---|
| 0 | `pip install -r requirements_local.txt` | — | unos minutos | el entorno | Sí |
| 1 | `python main_local.py grilla` | — | ~1 min | `datos/grilla/` | Sí |
| 2 | `python main_local.py hansen` | — | ~10 min, ~2 GB | `datos/hansen/` | Sí: da el bosque base |
| 3 | `python main_local.py gfw` | API key de GFW | 10-20 min | `datos/crudo/`, `datos/gfw/`, `datos/cache/` | Sí |
| 4 | `python main_local.py municipios` | — | ~10 s | `datos/limites/` | Sí: el mapa de la segmentación |
| 5 | `python main_local.py consolidar` | Pasos 1-4 | 1-2 min | `datos/panel/panel_deforestacion_colombia` | Sí |
| 6 | `python main_local.py panel-hansen` | Pasos 1, 2 y 4 | ~3 min | `datos/panel/panel_hansen` | No (solo la estadística descriptiva) |
| 7 | `python main_local.py ideam` | — | < 1 min | `datos/ideam/` | Sí |
| 8 | `python main_local.py panel-ideam` | Pasos 1, 2, 4 y 7 | ~6 min | `datos/panel/panel_ideam` | Sí |
| 9 | `python main_local.py dtd` | — | < 1 min | `datos/dtd/` | No |
| 10 | `python main_local.py panel-dtd` | Pasos 1, 2, 4 y 9 | < 1 min | `datos/panel/panel_dtd` | No |
| 11-13 | `subir-bigquery`, `describir-fuentes`, `describir-fuentes-profesor` | Llave de BigQuery; el 12 necesita el 11 (las tablas de `staging` vencen a los 60 días) | minutos | BigQuery y `guias/columnas/DESCRIPCION_FUENTES*.md` | No (opcionales) |
| 14 | `panel_municipal_armado.ipynb` | Pasos 5 y 8, y la llave de BigQuery | ~25 min la primera vez | `datos/profesor/`, `datos/analisis/` | Sí |

**Ruta mínima hasta los modelos:** Pasos 0, 1, 2, 3, 4, 5, 7, 8 y 14. Después
vienen los notebooks de análisis y modelos, en
[`3_NOTEBOOKS.md`](3_NOTEBOOKS.md).

Los tiempos son orden de magnitud y dependen de la velocidad de la red, del
disco y del número de núcleos del computador.

### Paso 0 — instalar dependencias

Ver la sección 1.

### Paso 1 — construir la grilla (local, una sola vez)

```bash
python main_local.py grilla
# equivale a: python -m pipeline.descarga.exportar_grilla
```

Descarga los límites departamentales del DANE (Marco Geoestadístico
Nacional) y construye una malla regular de celdas de 5 km sobre el
territorio continental. Salida: `datos/grilla/grilla_colombia_5km.csv`.

**Verificación**: el log debe terminar con "Grilla alineada al origen. El
indexado local es válido." Si el script se detiene con "GRILLA NO ALINEADA
AL ORIGEN", no continúe — ver `referencia/GUIA_CODIGO.md`, sección 7.

### Paso 2 — descargar Hansen GFC

```bash
python main_local.py hansen
# equivale a: python -m pipeline.descarga.descargar_hansen
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
# equivale a: python -m pipeline.descarga.descargar_gfw
```

Este es el paso central. Hace dos cosas, en este orden:

1. Calcula `bosque_ha` por celda reproyectando Hansen directamente sobre
   la grilla nacional de 5 km, en bloques (ver `referencia/GUIA_CODIGO.md`, sección 4) — no descarga
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
revise que `gfw_confianza_minima` en `pipeline/config_local.py` no se haya cambiado
por error a algo vacío.

### Paso 4 — límites municipales del DANE (automático)

```bash
python main_local.py municipios
# equivale a: python -m pipeline.descarga.descargar_municipios
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

### Paso 5 — consolidar la Tabla 1 (alertas GFW)

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

El detalle está en `referencia/GUIA_CODIGO.md`, sección 5. Produce
`datos/panel/panel_deforestacion_colombia.csv` y `.parquet`, ahora con
la columna `cod_dane` (código DANE de municipio) incluida por defecto.

**Verificación**: el log final imprime filas, celdas, periodos, rango de
fechas, % de celda-mes con evento y hectáreas totales. Se comparan contra
la sección 3 de este documento y contra
[«Cómo se ven las cuatro tablas»](referencia/GUIA_CODIGO.md#2-cómo-se-ven-las-cuatro-tablas)
en la guía del código.

### Paso 6 — Tabla 2: pérdida anual de cobertura (Hansen)

```bash
python main_local.py panel-hansen
```

No descarga nada: reutiliza los gránulos del Paso 2. Produce
`datos/panel/panel_hansen.csv` y `.parquet`, una fila por celda y año.
Tarda unos 3 minutos.

**Qué mide**: pérdida de cobertura arbórea, cualquiera sea su causa
—incluye cosecha de plantación forestal e incendio—. **No** es
directamente comparable con la cifra oficial del IDEAM: sobre Colombia
reporta entre 1,5 y 2,5 veces esa cifra, y la razón varía por año.

### Paso 7 — capas oficiales del IDEAM

```bash
python main_local.py ideam
```

Descarga los rásteres de cambio de bosque del SMByC a `datos/ideam/`.
Son ~53 MB por periodo (5 periodos por defecto, unos 260 MB en total) y
no requieren cuenta ni credencial. Toma menos de un minuto.

Para bajar otros periodos, o el catálogo completo desde 2000:

```bash
python main_local.py ideam --periodos 2018-2019 2019-2020
python main_local.py ideam --todos
```

> **El servidor del IDEAM solo responde por HTTPS.** Tiene el puerto 80
> cerrado, y una URL con `http://` no da un error de protocolo: se queda
> esperando hasta agotar el tiempo de espera. Si alguna vez hay que
> escribir esa URL a mano, debe llevar `https://`.

### Paso 8 — Tabla 3: deforestación oficial por celda

```bash
python main_local.py panel-ideam
```

Produce `datos/panel/panel_ideam.csv` y `.parquet`, una fila por celda y
periodo. Tarda unos 6 minutos.

**Verificación**: el log imprime el total nacional de deforestación por
periodo. Debe coincidir con la cifra oficial del IDEAM del **año final**
del periodo (`cambio_2022_2023` → año 2023), con una diferencia menor al
0,4 %. Ver `referencia/METODOLOGIA.md`, sección 2.3, para la tabla de contraste.

### Paso 9 — detecciones tempranas del IDEAM

```bash
python main_local.py dtd
```

Descarga los puntos de alerta trimestrales del SMByC a `datos/dtd/`, un
KML por trimestre. Son ~167 MB para 2020-2026 y no requieren cuenta ni
credencial. Toma menos de un minuto.

El script **lee el índice del servidor** en vez de construir los nombres
de archivo, porque la caja de las letras no es uniforme
(`atd_2019_II_trim.kml` frente a `atd_2020_i_trim.kml`). Como efecto
secundario, los trimestres nuevos que publique el IDEAM aparecen solos.

Para bajar otros años:

```bash
python main_local.py dtd --anios 2017 2018 2019
```

### Paso 10 — Tabla 4: alertas tempranas por celda y trimestre

```bash
python main_local.py panel-dtd
```

Produce `datos/panel/panel_dtd.csv` y `.parquet`, una fila por celda y
trimestre. Tarda menos de un minuto.

### Paso 11 — subir las cuatro tablas a BigQuery (opcional, requiere credencial)

```bash
python main_local.py subir-bigquery
```

Sube las tablas que ya existan en `datos/panel/` al dataset `staging`
del proyecto de BigQuery del equipo. Requiere haber copiado antes la
llave de la cuenta de servicio `pipeline-satelital` en
`datos/logs/bigquery-key.json` (ver `referencia/GUIA_CODIGO.md`, sección 3.16). Se puede correr
después de cada paso anterior, tantas veces como se quiera: siempre
reemplaza la tabla completa en BigQuery, nunca duplica filas.

El proyecto está en modo Sandbox, así que las tablas de `staging` **vencen
a los 60 días**. Al 17/11/2026 ya habían vencido y el dataset estaba vacío.
Antes de usar el Paso 12 hay que correr este paso de nuevo (ver
`referencia/GUIA_BIGQUERY.md`, sección 8).

### Paso 12 — describir las cuatro tablas propias (Paso 1 del EDA, requiere credencial)

```bash
python main_local.py describir-fuentes
```

Consulta en BigQuery las cuatro tablas del panel propio, y deja
columnas, tipos de dato, número de filas y una muestra de cada una en
`guias/columnas/DESCRIPCION_FUENTES.md`. Necesita que las tablas estén en `staging`, así
que primero hay que correr el Paso 11 si pasaron más de 60 días desde la
última subida. El `guias/columnas/DESCRIPCION_FUENTES.md` que está en el repositorio se
generó el 03/10/2026, y sus filas y columnas coinciden con las de los
paneles locales actuales. Es el punto de partida del EDA (`referencia/GUIA_CODIGO.md`, sección
3.17): antes de decidir el periodo de tiempo, declarar si hace falta
limpieza o proponer KPIs, hay que revisar ese reporte para confirmar
qué columnas trae cada fuente (por ejemplo, si ya existe población o
área por municipio, o si hay que conseguirlas aparte).

### Paso 13 — describir las cinco tablas del profesor (cuenta de servicio, reporte aparte)

```bash
python main_local.py describir-fuentes-profesor
```

Igual que el paso anterior, pero para las cinco tablas de solo lectura
del Observatorio (`prueba-ofr`): las tres financieras (FINAGRO, SFC 414 y
el catálogo de municipios) y las dos de producción (EVA e ICA pecuario).
Usa la misma llave de la cuenta de servicio que el Paso 12; no hace falta
una cuenta personal de Google. Deja el resultado en
`guias/columnas/DESCRIPCION_FUENTES_PROFESOR.md`, aparte de
`guias/columnas/DESCRIPCION_FUENTES.md`. Ver `referencia/GUIA_CODIGO.md`, sección 3.18, para el
detalle. A diferencia del Paso 12, no necesita el Paso 11: las tablas del
Observatorio viven en el proyecto del profesor y no vencen.

### Paso 14 — tablas del Observatorio y panel municipal (requiere la llave de BigQuery)

```bash
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 "procesamiento y eda/panel_municipal_armado.ipynb"
```

En ese comando:

- la ruta va entre comillas porque el nombre de la carpeta tiene espacios;
- `--inplace` reemplaza las salidas guardadas en el notebook por las de su
  corrida;
- `timeout=-1` evita que `nbconvert` corte una celda larga.

También se puede abrir el notebook en Jupyter y correrlo celda por celda.

`panel_municipal_armado.ipynb` necesita los paneles del IDEAM y de GFW
(Pasos 5 y 8) y la llave de BigQuery. Hace dos cosas:

1. **Descarga las cinco tablas del Observatorio** a `datos/profesor/`. Solo
   vuelve a bajar una tabla si cambió en BigQuery. La primera vez, FINAGRO
   (6,2 millones de filas) tarda unos 25 minutos.
2. **Arma el panel municipal** en `datos/analisis/`: junta la deforestación
   del IDEAM y de GFW con el crédito, los cultivos y el ganado.

| Tabla | Unidad | Filas × columnas | Qué tiene |
|---|---|---|---|
| `municipio_anio` | municipio × año, 2020-2025 | 6.738 × 28 | IDEAM (`def_ideam_ha`, `bosque_ideam_ha`, `sin_info_ideam_ha`, `tasa_def_ideam`, `bosque_ideam_inicial_ha`); GFW (`alertas_gfw_ha`); FINAGRO (`credito_mm`, `credito_produccion_mm` y `credito_<cadena>_produccion_mm`); EVA (`area_cosechada_ha` y `cosechada_<cultivo>_ha`); ICA (`bovinos`, `fincas_bovinas`); grilla (`n_celdas`, `area_grilla_ha`) y catálogo (`nombre_departamento`, `nombre_municipio`, `region`, `ruralidad`) |
| `municipio_mes` | municipio × mes, 2020-01 a 2026-06 | 87.594 × 11 | `alertas_gfw_ha`, las siete columnas de crédito y la región |
| `municipio_cultivo_anio` | municipio × cultivo × año, 2019-2024 | 93.486 × 5 | área cosechada de cada cultivo de la EVA, con su grupo |

Lo que conviene saber al usarlas:

- **Municipios.** Son 1.123: los 1.122 del catálogo del Observatorio más el
  27493 (Nuevo Belén de Bajirá), que está en los paneles pero no en el
  catálogo. El panel es balanceado: todo municipio tiene fila en todo
  periodo.
- **Crédito.** Además del total, va el del eslabón de producción de la
  cadena (`eslabon_cadena = Producción`), de todos los tipos de productor, y
  dentro de él cinco cadenas: ganadería (toda cadena que, sin tildes, empieza
  por "ganad": doble propósito, leche y carne), palma de aceite, cacao, café
  y arroz. Está en millones de pesos corrientes.
- **Cultivos.** Se usa el área **cosechada** de la EVA, no la sembrada. Los
  semestres A y B y las variantes de un cultivo (por ejemplo, arroz riego y
  secano) se suman en el año.
- **Sin rezagos.** Todas las columnas van en su propio año; no hay columnas
  `_t1`.
- **Chequeos.** Al final de cada tabla, el notebook compara los totales con
  los de la fuente: deforestación, crédito, área cosechada y bovinos cuadran
  al 100 %.

Las decisiones detrás de estos criterios están en la bitácora de
[`referencia/METODOLOGIA.md`](referencia/METODOLOGIA.md#4-bitácora-de-decisiones-de-diseño)
(decisiones 14 a 18).

### Comando de estado (en cualquier momento)

```bash
python main_local.py estado
```

Resume qué hay en disco en cada etapa, sin modificar nada.

---

## 3. Cómo comprobar que salió bien

`python main_local.py estado` dice qué hay en disco y qué falta. Para saber
si las cifras son las correctas, estas son las de la corrida de referencia:

| Tabla | Filas | Columnas |
|---|---|---|
| `datos/panel/panel_deforestacion_colombia` | 3.524.664 | 19 |
| `datos/panel/panel_hansen` | 267.696 | 9 |
| `datos/panel/panel_ideam` | 223.080 | 15 |
| `datos/panel/panel_dtd` | 1.115.400 | 14 |
| `datos/analisis/municipio_anio` | 6.738 | 28 |
| `datos/analisis/municipio_mes` | 87.594 | 11 |
| `datos/analisis/municipio_cultivo_anio` | 93.486 | 5 |

El número de filas puede cambiar en dos casos:

- si las fuentes publicaron datos nuevos después de la corrida de referencia,
  por ejemplo un mes más de alertas de GFW o un trimestre más de detecciones
  tempranas;
- si se cambió la ventana temporal en `pipeline/config_local.py`.

Las columnas no deberían cambiar. Para contar las filas de una tabla en
Python:

```python
import pyarrow.parquet as pq
pq.read_metadata("datos/panel/panel_ideam.parquet").num_rows
```

Dos comprobaciones más de fondo:

- **La deforestación del IDEAM.** La suma de `def_ha` de `panel_ideam` en
  cada periodo queda entre el 99,65 % y el 99,84 % de la cifra oficial
  publicada por el IDEAM. La diferencia son las celdas con muy poco bosque,
  que se excluyen a propósito (ver la sección 5).
- **El panel municipal.** `panel_municipal_armado.ipynb` termina comparando
  sus totales con los de las fuentes: la deforestación, el crédito, el área
  cosechada y los bovinos deben cuadrar al 100 %.

---

## 4. Dónde queda cada cosa

| Carpeta | Contenido | La genera |
|---|---|---|
| `datos/grilla/` | CSV de la grilla de 5 km | `exportar_grilla.py` |
| `datos/hansen/` | Gránulos Hansen GFC (`.tif`) | `descargar_hansen.py` |
| `datos/gfw/` | `lote_NNNN.json` — resultados crudos por lote de celdas de la API de GFW | `descargar_gfw.py` |
| `datos/cache/` | `bosque_am{anio}_ud{umbral}_res{resolucion}.npy` — bosque_ha por celda, ya calculado | `calcular_bosque.py` |
| `datos/crudo/` | `nacional.csv`, formato ancho | `descargar_gfw.py` |
| `datos/limites/` | `municipios_dane_mgn2025.geojson` — límites municipales del DANE | `descargar_municipios.py` |
| `datos/ideam/` | `cambio_<periodo>.img` — capas de cambio del SMByC (~53 MB c/u) | `descargar_ideam.py` |
| `datos/dtd/` | `atd_<año>_<trim>.kml` — detecciones tempranas (~167 MB en total) | `descargar_dtd.py` |
| `datos/demo/` | Salidas de la réplica con Landsat | `demo_landsat_caqueta.py` |
| `datos/panel/` | **Las cuatro tablas** (`.csv` + `.parquet`) + `mapa_deforestacion.html` | `consolidar.py`, `panel_hansen.py`, `panel_ideam.py`, `panel_dtd.py`, `mapa_folium.py` |
| `datos/profesor/` | Las cinco tablas del Observatorio (`finagro/`, `sfc414/`, `municipios/`, `eva/`, `ica_pecuario/`), en partes Parquet con un `_metadatos.json`, y `CODIGO.csv` | `panel_municipal_armado.ipynb` |
| `datos/analisis/` | Panel municipal: `municipio_anio`, `municipio_mes` y `municipio_cultivo_anio` (`.parquet`). Lo leen `panel_municipal_analisis.ipynb` y todos los notebooks de `modelos y clusters/` | `panel_municipal_armado.ipynb` |
| `datos/logs/` | `gfw_api_key.txt` y `bigquery-key.json` (esta última se copia a mano) | `configurar_gfw.py` |

Si algo se ve raro o hay que reconstruir desde cero, casi siempre basta con
borrar la carpeta correspondiente y volver a correr el paso que la genera
— **excepto** `datos/hansen/` (varios minutos de descarga),
`datos/ideam/` (~260 MB), `datos/dtd/` (~167 MB) y `datos/profesor/`
(la descarga de FINAGRO tarda unos 25 minutos), que conviene conservar. Borrar `datos/cache/` es seguro y barato de regenerar
(se recalcula solo en la siguiente corrida de `descargar_gfw.py`). Borrar
`datos/gfw/` es igual de seguro (son solo cachés de lotes ya descargados de
la API).

Las salidas de la segmentación y de los modelos **no** van en `datos/`, sino
en `modelos y clusters/resultados/`, y sí se versionan: son pequeñas y
permiten consultar la corrida de referencia sin la llave de BigQuery. Lo
mismo pasa con las tablas y figuras que van al documento del trabajo, en
`documento/tablas/` y `documento/figuras/`.

---

## 5. Problemas comunes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `exportar_grilla.py` se detiene con "GRILLA NO ALINEADA AL ORIGEN" | No debería ocurrir con la versión actual (la alineación es por construcción) — indicaría que alguien cambió `construir_grilla()` sin preservar esa propiedad | No ignorar este error: revisar que cada celda siga construyéndose como múltiplo entero exacto de `grid_scale_m` |
| `exportar_grilla.py` falla al descargar del DANE (timeout o error HTTP) | El servicio de ArcGIS del DANE puede estar temporalmente caído, o cambió de URL/item id | Reintentar en unos minutos; si persiste, buscar "Marco Geoestadístico Nacional Departamento" en el geoportal del DANE o en su ArcGIS Hub para encontrar la URL vigente y actualizar `DANE_MGN_DEPARTAMENTOS` en el script |
| `exportar_grilla.py` tarda varios minutos en el filtro espacial | Falta la simplificación del polígono nacional — el MGN del DANE sin simplificar tiene ~280.000 vértices | No debería pasar en la versión actual (ya incluye `pais.simplify(100, ...)`); si se quitó esa línea, restaurarla |
| `pd.read_parquet` falla con `ImportError` | Falta `pyarrow` en el entorno, aunque esté listado en `requirements_local.txt` | `pip install pyarrow`, o usar el `.csv` equivalente — `mapa_folium.py` y el notebook ya caen automáticamente al CSV si el Parquet no se puede leer |
| La descarga de Hansen (Paso 2) es muy lenta | Límite de ancho de banda, o `hilos_descarga` muy bajo/alto para la red disponible | Ajustar `hilos_descarga` en `pipeline/config_local.py` |
| `descargar_gfw.py` falla con `SystemExit` pidiendo la API key | Falta `datos/logs/gfw_api_key.txt` o la variable de entorno `GFW_API_KEY` | Correr `configurar_gfw.py` (`referencia/GUIA_CODIGO.md`, sección 3.5) primero |
| `descargar_gfw.py` falla con `"Unsupported filter operator: in"` | El endpoint `/query/batch` de GFW no soporta `IN (...)` en el SQL | No debería pasar en la versión actual (`sql_lote()` ya usa `OR` encadenados, confirmado empíricamente); si se editó esa función para usar `IN`, revertir |
| `descargar_gfw.py` falla con `"extra fields not permitted"` en `feature_collection.features[i].id` | `geopandas`/`shapely` agregan un campo `"id"` a nivel de *feature* al exportar a GeoJSON, que la API de GFW rechaza | No debería pasar en la versión actual (`procesar_lote()` ya hace `feat.pop("id", None)` antes de enviar); si se quitó esa línea, restaurarla |
| `descargar_gfw.py` falla con `FileNotFoundError` sobre gránulos Hansen | No se corrió el Paso 2 | `python main_local.py hansen` |
| El mapa de `mapa_folium.py` pesa demasiado / tarda en abrir | Demasiados marcadores individuales en la capa de "Celdas con deforestación" | Bajar `--top-n` o subir `--umbral-ha` |
| Un cruce por `cod_dane` no encuentra los municipios de Antioquia o Atlántico | Se leyó el CSV sin declarar el tipo y `pandas` convirtió `05001` en `5001` | Leer con `dtype={"cod_dane": "string"}`, o usar el `.parquet`, que conserva el tipo |
| El mapa del cuaderno no se ve y dice "Make this Notebook Trusted" | Folium incrusta el mapa en un `<iframe srcdoc=...>` que Jupyter bloquea hasta marcar el cuaderno como confiable, y que GitHub no renderiza nunca | Abrir `datos/panel/mapa_fuentes.html`, que la propia celda guarda; o marcar el cuaderno como confiable en Jupyter |
| El mapa sale en blanco, sin fondo | El proveedor de tiles exige API key (CartoDB y Stamen hoy la piden) | La versión actual usa OpenStreetMap, que no la necesita; si se cambió con `--tiles`, volver al valor por defecto |
| `descargar_ideam.py` se queda colgado sin dar error | La URL va por `http://` y el servidor del IDEAM tiene el puerto 80 cerrado | Verificar que `BASE` en el script empiece por `https://` — no da error de protocolo, solo agota el tiempo de espera |
| El total de `panel_ideam` no coincide con la cifra oficial del IDEAM | Es esperado: queda ~0,25 % por debajo | Son celdas con menos de `bosque_minimo_ha` de bosque base, excluidas por el filtro de dominio. Si la diferencia es mucho mayor, revisar `anio_mascara` y `umbral_dosel` |
| `panel-hansen` o `panel-ideam` tardan muchísimo (más de 30 min) | El índice de celda se está calculando por el camino general en vez del separable | Ocurre solo si el ráster de destino lleva rotación. Con la configuración por defecto no pasa: son ~3 min (Hansen) y ~6 min (IDEAM) |
| Los conteos de `panel_dtd` suben mientras la deforestación baja | Comportamiento esperado del dato | La sensibilidad de detección del sistema cambió a lo largo de la serie: los conteos sirven para prioridad espacial dentro de un trimestre, no como serie temporal de magnitud (correlación −0,669 con la cifra oficial) |
| `descargar_dtd.py` no encuentra un trimestre reciente | Aún no está publicado, o cambió el nombre en el servidor | El script lee el índice del servidor, así que los nombres nuevos aparecen solos; si un año no tiene carpeta `Puntos/`, se omite con un aviso |
| La cifra de `panel_hansen` no coincide con la del IDEAM | Comportamiento esperado | Cada uno mide un concepto distinto: Hansen reporta pérdida de cobertura arbórea, que incluye plantación e incendio, y sobre Colombia da entre 1,5 y 2,5 veces la cifra oficial, con una razón que varía por año |
| Las tasas de `panel_ideam` parecen bajas | Se está usando `bosque_base_ha` (Hansen) como denominador | Para esa tabla el denominador correcto es `bosque_ideam_ha`; usar el de Hansen subestima la tasa un 30-45 % |
| `pip install` falla con `No such file or directory` y menciona *Long Path* | La ruta del entorno es demasiado larga para Windows | Clonar el repositorio en una ruta corta (por ejemplo, `C:\proyectos\`) o activar las rutas largas de Windows (ver la sección 1.4) |
| `panel_municipal_armado.ipynb` falla al conectarse a BigQuery | Falta `datos/logs/bigquery-key.json`, o la llave no tiene acceso | Ver la sección 1.5. Sin esa llave no se puede armar el panel municipal ni correr nada de lo que depende de él |
