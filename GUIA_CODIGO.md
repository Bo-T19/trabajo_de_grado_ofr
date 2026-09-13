# Guía de código y reproducibilidad — Pipeline de deforestación Colombia

Este documento explica **cómo está construido el software** y **cómo
correrlo desde cero**, paso a paso, con suficiente detalle para que alguien
que no participó en escribirlo —el director de tesis, un jurado, un
colaborador futuro— pueda reproducir **las dos tablas** en su propio
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
4. [Cómo se ven las cuatro tablas](#4-cómo-se-ven-las-cuatro-tablas)
5. [Referencia de cada script](#5-referencia-de-cada-script)
6. [Cómo se calcula el bosque base, en código](#6-cómo-se-calcula-el-bosque-base-en-código)
7. [Cómo se construye el panel, en código](#7-cómo-se-construye-el-panel-en-código)
8. [El mapa interactivo (`mapa_folium.py`)](#8-el-mapa-interactivo-mapa_foliumpy)
9. [Prueba de concepto: derivar deforestación desde Landsat](#9-prueba-de-concepto-derivar-deforestación-desde-landsat)
10. [Análisis exploratorio (pendiente)](#10-análisis-exploratorio-pendiente)
11. [Estructura de `datos/`](#11-estructura-de-datos)
12. [Cómo adaptar el pipeline](#12-cómo-adaptar-el-pipeline)
13. [Solución de problemas](#13-solución-de-problemas)
14. [Glosario de código](#14-glosario-de-código)

---

## 1. Mapa del repositorio

```
trabajo_de_grado/
├── config_local.py           configuración central — todo parámetro vive aquí
├── exportar_grilla.py        genera la grilla de 5 km — una sola vez
├── zonal.py                  reparte cualquier ráster entre las celdas de la grilla
├── descargar_municipios.py   límites municipales del DANE (MGN), automático
│
│   ── LINEA BASE de bosque (Hansen) ───────────────────────────────
├── descargar_hansen.py       descarga los granulos de Hansen GFC
├── calcular_bosque.py        bosque_ha por celda — el DENOMINADOR comun
│
│   ── TABLA 1: alertas de disturbio (GFW), mensual ────────────────
├── configurar_gfw.py         registro de una sola vez en la API de GFW
├── descargar_gfw.py          descarga el evento -> datos/crudo/nacional.csv
├── consolidar.py             arma la tabla celda x mes + cruce municipal
│
│   ── TABLA 2: perdida de cobertura (Hansen), anual ───────────────
├── panel_hansen.py           celda x año, desde los granulos ya descargados
│
│   ── TABLA 3: deforestacion oficial (IDEAM), por periodo ─────────
├── descargar_ideam.py        capas de cambio de bosque del SMByC
├── panel_ideam.py            celda x periodo, con columnas de calidad
│
│   ── TABLA 4: alertas tempranas oficiales (IDEAM), trimestral ────
├── descargar_dtd.py          detecciones tempranas del SMByC (KML por trimestre)
├── panel_dtd.py              celda x trimestre, conteo de detecciones
│
├── catalogo_paneles.ipynb    describe las cuatro tablas y las mapea
├── main_local.py             orquestador de línea de comandos
│
│   ── PRUEBA DE CONCEPTO: deforestación derivada de imagen cruda ──
├── demo_landsat_caqueta.py   deriva pérdida de bosque desde Landsat
├── mapa_folium.py            mapa interactivo (Leaflet) de la tabla de alertas
│
├── requirements_local.txt    dependencias de Python (pip)
├── .dodsrc                   (sin uso en este pipeline; ver legacy/)
│
├── METODOLOGIA.md            ← el "qué y por qué" (léalo primero)
├── GUIA_CODIGO.md            ← este documento, el "cómo"
│
├── legacy/                   código archivado, fuera del pipeline activo
│                              (ver legacy/README.md)
│
└── datos/                    TODO el output cae aquí (ver sección 11)
    ├── grilla/  hansen/  gfw/  cache/  crudo/  limites/  panel/  logs/
    ├── ideam/                 capas de cambio de bosque del SMByC
    ├── dtd/                   detecciones tempranas del SMByC
    └── demo/                  salidas de la prueba de concepto
```

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
trabajo (sección 4). La cuarta se expresa en **conteos** y responde a otra
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
resultado vive en `config_local.py`, nunca hardcodeado dentro de otro
script. Si algo en las tablas se ve distinto a lo esperado, el primer
lugar a revisar es ese archivo, no el resto del código.

---

## 2. Preparar el entorno desde cero

### 2.1 Requisitos de sistema

- Python 3.10 o superior.
- **~5 GB libres en disco**, repartidos así en una corrida completa:
  gránulos de Hansen ~2,0 GB, cachés de lotes de la API de GFW ~1,0 GB,
  las cuatro tablas ~0,85 GB, capas del IDEAM ~0,25 GB, detecciones
  tempranas ~0,17 GB. Conviene dejar margen.
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
rasterio>=1.3              # lectura/reproyeccion de rasteres: Hansen GFC (calcular_bosque.py, panel_hansen.py) y capas del IDEAM (panel_ideam.py)
numpy>=1.24
pandas>=2.0
requests>=2.31             # descarga de Hansen, capas del IDEAM y llamadas a la API de GFW
pyarrow>=14.0              # motor de lectura/escritura de Parquet (todas las salidas se guardan tambien en .parquet)
geopandas>=0.14            # exportar_grilla.py (grilla local), cruce municipal del DANE, y las geometrias de celda que descargar_gfw.py manda a la API de GFW
shapely>=2.0               # se importa directamente (geometrias de celda); llega como dependencia de geopandas, pero se declara porque el codigo lo usa de forma explicita
folium>=0.15               # mapa interactivo (mapa_folium.py)
branca>=0.7                # escala de color del mapa; igual que shapely, llega con folium pero se importa directo
matplotlib>=3.7            # graficas del analisis exploratorio (pendiente de rehacer)
jupyter>=1.0               # entorno del analisis exploratorio
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

Ver la sección 7 para el detalle. Produce
`datos/panel/panel_deforestacion_colombia.csv` y `.parquet`, ahora con
la columna `cod_dane` (código DANE de municipio) incluida por defecto.

**Verificación**: el log final imprime filas, celdas, periodos, rango de
fechas, % de celda-mes con evento y hectáreas totales. Compare contra la
sección ["Cómo se ven las cuatro tablas"](#4-cómo-se-ven-las-cuatro-tablas)
más abajo.

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
python descargar_ideam.py --periodos 2018-2019 2019-2020
python descargar_ideam.py --todos
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
0,4 %. Ver METODOLOGIA.md sección 2.3 para la tabla de contraste.

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
python descargar_dtd.py --anios 2017 2018 2019
```

### Paso 10 — Tabla 4: alertas tempranas por celda y trimestre

```bash
python main_local.py panel-dtd
```

Produce `datos/panel/panel_dtd.csv` y `.parquet`, una fila por celda y
trimestre. Tarda menos de un minuto.

### Comando de estado (en cualquier momento)

```bash
python main_local.py estado
```

Resume qué hay en disco en cada etapa, sin modificar nada.

---

## 4. Cómo se ven las cuatro tablas

*(Números de la corrida de referencia.)*

Los cuatro paneles cubren exactamente las mismas **44 616 celdas**, con el
mismo `bosque_base_ha` de Hansen (77 713 177 ha) y el mismo cruce
municipal (1 114 municipios).

| Archivo en `datos/panel/` | Mide | Unidad | Filas | Cols |
|---|---|---|---|---|
| `panel_deforestacion_colombia` | Disturbio, ha (GFW) | celda × mes | 3 524 664 | 19 |
| `panel_hansen` | Pérdida de cobertura, ha (Hansen) | celda × año | 267 696 | 9 |
| `panel_ideam` | Deforestación oficial, ha (IDEAM) | celda × periodo | 223 080 | 14 |
| `panel_dtd` | Detecciones, conteo (IDEAM) | celda × trimestre | 1 115 400 | 13 |

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
| 18 | `cod_dane` | int | código DANE del municipio — **la llave para cruces** |
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
| 8-9 | `cod_dane`, `municipio` | int, texto | cruce municipal del DANE |

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

14 columnas, 44 616 celdas × 5 periodos. Guarda las **cinco clases** de
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
| 9-10 | `lon`, `lat` | float | centroide de la celda |
| 11 | `departamento` | texto | departamento del centroide |
| 12 | `bosque_base_ha` | float | línea base de Hansen, idéntica a las otras dos |
| 13-14 | `cod_dane`, `municipio` | int, texto | cruce municipal del DANE |

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

13 columnas, 44 616 celdas × 25 trimestres (2020-T1 a 2026-T1). Panel
balanceado, igual que el de alertas.

| # | Columna | Tipo | Qué es |
|---|---|---|---|
| 1 | `cell_id` | texto | id de la celda, igual que en las otras tres |
| 2 | `periodo` | fecha | primer día del trimestre, para ordenar y cruzar |
| 3 | `trimestre_txt` | texto | `"2024-T2"`, legible |
| 4-5 | `anio`, `trimestre` | int | descompuestos |
| 6 | `n_alertas` | int | **número de puntos de alerta** publicados en esa celda |
| 7 | `n_alertas_sinap` | int | cuántos de esos caen en un área protegida del SINAP |
| 8-9 | `lon`, `lat` | float | centroide de la celda |
| 10 | `departamento` | texto | departamento del centroide |
| 11 | `bosque_base_ha` | float | línea base de Hansen, idéntica a las otras |
| 12-13 | `cod_dane`, `municipio` | int, texto | cruce municipal del DANE |

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
| `gfw_dataset`, `gfw_version` | Identificador del dataset GFW en la API SQL. Cambiarlo es todo lo que hace falta para usar otra fuente de evento; el archivo lista otros datasets de alertas disponibles | METODOLOGIA §2.2 |
| `fecha_inicio`, `fecha_fin`, `frecuencia` | Ventana temporal del panel y su resolución mensual | METODOLOGIA §1.3 |
| `gfw_confianza_minima` | Niveles de confianza de GFW que cuentan como evento. Usar solo `("highest",)` aplica el criterio más estricto, a costa de un panel más disperso — ver la nota en `config_local.py` | METODOLOGIA §2.2, decisión 2 |
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

### 5.8 `consolidar.py` — Tabla 1, alertas GFW (detalle en sección 7)

### 5.9 `zonal.py` — maquinaria zonal compartida

Reparte los píxeles de **cualquier** ráster entre las celdas de la
grilla. Lo usan las dos tablas y el atributo de causas, y esa es la razón
de que exista: si cada
una implementara el reparto por su cuenta, una diferencia de medio píxel
en el borde de una celda haría que dejaran de ser comparables.

Expone `cargar_grilla()`, `bloques()`, `perfil_bloque()`,
`indice_celdas_bloque()`, `reproyectar_sobre_bloque()` y
`contar_por_celda_y_clase()`. El detalle del diseño (bloques alineados a
bordes de celda, ráster sintético en EPSG:3116, índice por aritmética
directa sin `pyproj`) está en la sección 6.

### 5.10 `panel_hansen.py` — Tabla 2, pérdida anual

Cuenta píxeles de la capa `lossyear` por celda y por año, aplicando la
misma definición de bosque que `calcular_bosque.py` (un píxel que nunca
fue bosque no puede perder cobertura). No descarga nada: reutiliza los
gránulos del Paso 2. Escribe `datos/panel/panel_hansen.*`.

Su encabezado documenta los dos papeles de Hansen en el proyecto —línea
base y fuente de evento— y la relación de su cifra con la del IDEAM:
entre 1,5 y 2,5 veces esa cifra, con una razón que varía cada año.

### 5.11 `descargar_ideam.py` — capas oficiales del SMByC

Descarga los rásteres de cambio de bosque del IDEAM a `datos/ideam/`.
El catálogo de archivos está en el diccionario `CAPAS` (el sufijo de
versión y fecha de cada capa no sigue un patrón deducible, así que se
lista explícitamente). Descarga a un `.parcial` y renombra al final, para
que una interrupción no deje un `.img` truncado que la corrida siguiente
daría por bueno.

**El servidor solo responde por HTTPS** (puerto 80 cerrado). Con `http://`
no da error: se cuelga hasta agotar el tiempo de espera.

### 5.12 `panel_ideam.py` — Tabla 3, deforestación oficial

Cuenta las cinco clases de la capa de cambio por celda y periodo. Los
cinco periodos se procesan **dentro** del recorrido de bloques, no uno
después de otro: el índice de celda depende solo de la geometría del
bloque, así que compartirlo entre periodos evita recalcularlo 780 veces
en vez de 156.

Calcula además `bosque_ideam_ha` (clase 1 + clase 2), que es el
denominador correcto para las tasas de esta tabla — ver la advertencia de
la sección 4.

### 5.13 `descargar_dtd.py` — detecciones tempranas del SMByC

Baja los puntos de alerta trimestrales a `datos/dtd/`. En vez de
construir los nombres de archivo, **lista el índice del servidor** y toma
los que encuentra: la caja de las letras no es uniforme entre años, y así
los trimestres nuevos aparecen sin tocar código. Renombra a un patrón
regular en disco (`atd_<año>_<trimestre>.kml`).

Se usan los **puntos** y no los **núcleos** porque la serie de puntos no
tiene huecos (2016-III a 2026-I), mientras la de núcleos carece del año
2024 completo en el servidor.

### 5.14 `panel_dtd.py` — Tabla 4, alertas tempranas

Reproyecta los puntos a `cfg.grid_crs` y los asigna a su celda con la
misma regla aritmética que usa `zonal.py` para los rásteres
(`floor(coord / grid_scale_m)`), de modo que un punto y un píxel en el
mismo lugar caen en la misma celda. Emite un panel balanceado.

### 5.15 `main_local.py` — orquestador

Cada subcomando (`grilla`, `hansen`, `gfw`, `municipios`, `consolidar`,
`panel-hansen`, `ideam`, `panel-ideam`, `dtd`, `panel-dtd`, `estado`)
arma la línea de comandos correcta y lanza el script correspondiente como subproceso
(`subprocess.call`), excepto `consolidar`, que importa la función
directamente. `estado` es el único que no delega: lista lo que hay en
disco en cada etapa y cuáles de las cuatro tablas ya existen.

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
cambiar una sola línea en `config_local.py`, sin tocar código.

(el operador SQL `IN` no está soportado por este endpoint — se confirmó
empíricamente que devuelve `"Unsupported filter operator: in"` — por eso
el filtro de confianza usa `OR` en vez de `IN (...)`.) Cada lote se cachea
en `datos/gfw/lote_<dataset>_NNNN.json` apenas se descarga, así que el
script es reanudable; el nombre incluye el dataset para que cambiar de
fuente no reutilice en silencio los resultados de la anterior.
`agregar_a_mensual()` junta los resultados de todos los lotes en la tabla
ancha final (`cell_id`, `d_2020_01`, ..., hasta el mes más reciente).

---

## 8. El mapa interactivo (`mapa_folium.py`)

> `atenuar_mapa_base()` es pública porque también la usa
> `catalogo_paneles.ipynb`: cualquier mapa del proyecto se ve igual.

Genera un mapa Leaflet (vía `folium`) para inspeccionar visualmente el
la tabla de alertas, sin abrir el CSV ni un SIG de escritorio:

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

## 9. Prueba de concepto: derivar deforestación desde Landsat

`demo_landsat_caqueta.py` deriva pérdida de bosque **directamente de
imágenes Landsat 8/9** sobre una zona piloto de Caquetá, y la contrasta
con las alertas GLAD-L. Es una demostración metodológica: no reemplaza a
GLAD-L como fuente del panel.

```powershell
python demo_landsat_caqueta.py
```

No hace falta instalar nada adicional ni ninguna credencial nueva: usa la
API key de GFW que el pipeline ya tiene. Tarda unos 13 minutos la primera
vez y segundos las siguientes, porque los compuestos quedan en caché.

### De dónde sale cada insumo, sin Earth Engine

| Insumo | Origen | Credencial |
|---|---|---|
| Escenas Landsat | Catálogo STAC de Microsoft Planetary Computer | Ninguna |
| Bosque base | Los gránulos de `datos/hansen/` que ya están en disco | Ninguna |
| GLAD-L | Ráster `date_conf` del data-lake de GFW | La del pipeline |

Los archivos de Landsat son **COG**, así que se lee solo el recorte de la
zona piloto: se descargan megabytes en vez de las escenas completas de
~1 GB. El módulo usa `requests` para el catálogo y `rasterio` para la
lectura, de modo que no suma dependencias.

> **Por qué no se usó Earth Engine.** El nivel gratuito de Earth Engine
> es explícitamente para uso **no comercial**, y el destino declarado de
> este trabajo incluye consultorías del Observatorio. Derivar la
> detección sin esa plataforma mantiene el proyecto entero en terreno
> utilizable, y de paso deja la demo dentro del pipeline reproducible en
> vez de convertirla en una excepción.

### El método, en tres condiciones

Un píxel cuenta como pérdida si cumple las tres:

1. **Era bosque al inicio de T1**, según Hansen GFC: dosel del año 2000
   ≥ 30 % —el mismo umbral que usa el panel nacional— y sin pérdida
   registrada antes de la ventana.
2. **Su NBR cayó más que un umbral.** Se comparan compuestos de mediana
   de la **misma temporada seca** en años consecutivos, para que la
   diferencia no recoja estacionalidad fenológica.
3. **Pertenece a un parche de al menos 1 ha**, el área mínima de la
   definición del IDEAM. A 30 m cada píxel son 0,09 ha, así que 11
   píxeles dan 0,99 ha: quedan justo por debajo. El módulo usa **12**, el
   primer entero que la alcanza.

### Por qué la ventana es 2022-2023

El ráster de GLAD-L del data-lake de GFW es un producto **rodante**: la
versión vigente arranca en enero de 2021 y no conserva los años
anteriores. Se verificó la cobertura real sobre la zona antes de fijar
las fechas. 2022 y 2023 son los dos primeros años consecutivos con
alertas confirmadas completas, y ambos tienen escenas de Landsat 8 y 9.

### Resultados de la corrida de referencia

Zona de 2968 × 2581 píxeles de 30 m, con 330 600 ha de bosque inicial.
38 escenas en T1 y 34 en T2.

| Métrica (mitad este, no vista en la calibración) | Valor |
|---|---|
| **Pearson, hectáreas por celda de 5 km** | **0,909** |
| Spearman, por celda | 0,795 |
| Precisión, a nivel de píxel | 0,549 |
| Sensibilidad, a nivel de píxel | 0,467 |
| F1, a nivel de píxel | 0,505 |

Esa diferencia entre escalas es el resultado central: **a nivel de píxel
la coincidencia es moderada, pero a la escala de 5 km del modelo la
correlación llega a 0,91**. Dos detectores pueden discrepar sobre qué
píxel exacto marcaron y aun así coincidir muy bien en cuánta pérdida hay
en cada celda, que es lo que el modelo necesita.

Matriz de acuerdo, sobre 180 450 ha de dominio: 1 251 ha detectadas por
ambos, 1 026 ha solo por el método propio, 1 430 ha solo por GLAD-L.

> **La exactitud global fue 0,9864 y no significa nada.** El bosque
> estable ocupa el 98 % del dominio, así que un detector que no marcara
> nada obtendría una cifra parecida. El módulo la reporta porque suele
> pedirse, y advierte en su propio docstring que no es informativa.

### Lo que el diagnóstico de nubes reveló

El porcentaje de bosque excluido por falta de observación fue **0,00 %**:
con tres meses de Landsat 8 y 9, todos los píxeles alcanzaron al menos
una lectura limpia en ambas ventanas.

El problema de nubosidad está en otro número. De las 38 escenas
disponibles en T1, el píxel mediano recibió **5 observaciones limpias**;
en T2, **3 de 34**. Es decir, la nubosidad descarta la gran mayoría de
las lecturas, y el compuesto descansa en muy pocas. El percentil 10 baja
a 4 y 2 respectivamente.

Por eso el diagnóstico reporta la distribución completa —mínimo,
percentil 10, mediana, máximo— y no solo el porcentaje excluido: un píxel
con una sola lectura entra al dominio, pero si esa lectura venía
contaminada y la máscara no la atrapó, su dNBR es ruido.

### Las dos decisiones que sostienen el resultado

**El dominio excluye lo que no se pudo observar.** Contar un píxel
nublado como "estable" lo convertiría en un verdadero negativo gratuito,
inflando la exactitud y escondiendo la falta de observación.

**La calibración y la validación no comparten píxeles.** El umbral de
dNBR se calibra en la mitad **oeste** y se evalúa en la mitad **este**.

### Cómo se iguala la comparación con GLAD-L

A GLAD-L se le aplica exactamente el mismo tratamiento: la misma máscara
de bosque, el mismo dominio, el mismo filtro de área mínima, y un filtro
de fecha que acota las alertas a la ventana entre ambos compuestos. Sin
esas cuatro igualaciones la comparación mediría diferencias de encuadre
en lugar de diferencias de detección.

### Salidas, en `datos/demo/`

| Archivo | Qué trae |
|---|---|
| `diagnostico_nubes.csv` | Bosque, dominio y distribución de observaciones limpias |
| `calibracion_umbral.csv` | Métricas por umbral, en la mitad oeste |
| `evaluacion_validacion.csv` | Matriz de acuerdo y métricas, en la mitad este |
| `comparacion_celdas.csv` | Hectáreas por celda de 5 km, ambas fuentes |
| `muestra_validacion_visual.csv` | 200 puntos estratificados para interpretar a mano |
| `mapa_revision.html` | Mapa con bosque, pérdida propia y pérdida GLAD-L |
| `cache_nbr_*.npz` | Compuestos guardados; borrarlo fuerza recalcular |

La muestra sigue la práctica de Olofsson et al. (2014): 50 puntos por
cada una de las cuatro combinaciones propia/GLAD, con `etiqueta_visual`
vacía para que la llene un intérprete sobre imagen de alta resolución. Es
estratificada y no aleatoria simple porque las clases de cambio ocupan
una fracción minúscula de la escena, y un muestreo simple dejaría los
desacuerdos —que son lo que hay que revisar— casi sin puntos.

### Qué reutiliza del pipeline

`zonal.reproyectar_sobre_bloque()` para llevar los gránulos de Hansen a
la rejilla de trabajo, `mapa_folium.atenuar_mapa_base()` para que el mapa
se vea igual que los demás, y el `logger` de `config_local`. La demo no
reimplementa la geometría del reparto: la hereda.

---

## 10. Análisis exploratorio (pendiente)

Para una descripción rápida de qué contiene cada tabla —dimensiones,
columnas, tipos, una muestra y un mapa en folium que compara el patrón
espacial de las cuatro fuentes— está
[`catalogo_paneles.ipynb`](catalogo_paneles.ipynb), que lee las cifras de
los propios archivos y por tanto se mantiene al día. No sustituye al
análisis exploratorio: solo describe las salidas.

El análisis exploratorio sobre las cuatro tablas está pendiente de
elaborar. Lo que debería cubrir:

- **Panel de alertas**: balance del panel (`filas = celdas × periodos`),
  desbalance de la variable `evento`, evolución temporal, estacionalidad,
  distribución de `tasa_def`, ranking departamental, concentración
  espacial y autocorrelación temporal.
- **Panel de Hansen**: serie anual de pérdida de cobertura y su relación
  con la cifra oficial, año a año.
- **Panel del IDEAM**: serie por periodo contra la cifra oficial, ranking
  municipal de deforestación, y tasas calculadas con `bosque_ideam_ha`
  (ver sección 4).
- **Comparación entre los tres**: las razones Hansen/IDEAM y GFW/IDEAM
  por año y por región, y los municipios que aparecen señalados por las
  tres fuentes a la vez.

Las dependencias para hacerlo (`matplotlib`, `jupyter`) están declaradas
en `requirements_local.txt`.

---

## 11. Estructura de `datos/`

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
| `datos/demo/` | Salidas de la prueba de concepto con Landsat | `demo_landsat_caqueta.py` |
| `datos/panel/` | **Las cuatro tablas** (`.csv` + `.parquet`) + `mapa_deforestacion.html` | `consolidar.py`, `panel_hansen.py`, `panel_ideam.py`, `panel_dtd.py`, `mapa_folium.py` |
| `datos/logs/` | `gfw_api_key.txt` | `configurar_gfw.py` |

Si algo se ve raro o hay que reconstruir desde cero, casi siempre basta con
borrar la carpeta correspondiente y volver a correr el paso que la genera
— **excepto** `datos/hansen/` (varios minutos de descarga),
`datos/ideam/` (~260 MB) y `datos/dtd/` (~167 MB), que conviene
conservar. Borrar `datos/cache/` es seguro y barato de regenerar
(se recalcula solo en la siguiente corrida de `descargar_gfw.py`). Borrar
`datos/gfw/` es igual de seguro (son solo cachés de lotes ya descargados de
la API).

---

## 12. Cómo adaptar el pipeline

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

## 13. Solución de problemas

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

---

## 14. Glosario de código

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
