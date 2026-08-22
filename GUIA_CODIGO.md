# Guía de código y reproducibilidad — Pipeline de deforestación Colombia

Este documento explica **cómo está construido el software** y **cómo
correrlo desde cero**, paso a paso, con suficiente detalle para que alguien
que no participó en escribirlo —el director de tesis, un jurado, un
colaborador futuro— pueda reproducir cualquiera de los dos paneles finales
en su propio computador. El pipeline produce **dos paneles independientes,
que nunca se mezclan**: uno con NASA OPERA DIST-ALERT (2023-presente,
`fuente_dist_alert/`) y otro con el producto integrado de Global Forest
Watch (2020-presente, `fuente_gfw/`) — ver METODOLOGIA.md §2.4 y decisión
15 para el porqué.

Este documento **no** explica por qué se tomaron las decisiones de diseño
(qué fuentes de datos, qué umbrales, qué supuestos): eso está en
[METODOLOGIA.md](METODOLOGIA.md). Aquí se asume esa metodología como dada y
se explica su implementación. Los dos documentos están escritos para leerse
por separado — la metodología no requiere entender código, y esta guía no
requiere releer la justificación de cada decisión, aunque enlaza a ella donde
es relevante.

---

## Índice

1. [Mapa del repositorio](#1-mapa-del-repositorio)
2. [Preparar el entorno desde cero](#2-preparar-el-entorno-desde-cero)
3. [Orden exacto de ejecución](#3-orden-exacto-de-ejecución)
4. [Cómo se ve la base de datos final](#cómo-se-ve-la-base-de-datos-final)
5. [Referencia de cada script](#5-referencia-de-cada-script)
6. [Cómo funciona el cálculo zonal, en código](#6-cómo-funciona-el-cálculo-zonal-en-código)
7. [Cómo se construye el panel, en código](#7-cómo-se-construye-el-panel-en-código)
8. [El mapa interactivo (`mapa_folium.py`)](#8-el-mapa-interactivo-mapa_foliumpy)
9. [El notebook de EDA (`eda_deforestacion.ipynb`)](#9-el-notebook-de-eda-eda_deforestacionipynb)
10. [Estructura de `datos/`](#10-estructura-de-datos)
11. [Cómo adaptar el pipeline](#11-cómo-adaptar-el-pipeline)
12. [Solución de problemas](#12-solución-de-problemas)
13. [Glosario de código](#13-glosario-de-código)

---

## 1. Mapa del repositorio

El código está organizado por **rol**, no por orden cronológico de cuándo se
escribió: lo compartido queda en la raíz, y cada **fuente del evento**
(DIST-ALERT para 2023 en adelante, GFW integrado para 2020-presente, ver
METODOLOGIA.md §2.4 y decisión 15) vive en su propia carpeta. Las dos
fuentes producen **dos paneles finales completamente independientes**, que
nunca se fusionan: `consolidar.py` exige elegir explícitamente cuál
construir (`--fuente dist_alert` o `--fuente gfw`), nunca las dos a la vez.

```
trabajo_de_grado/
├── config_local.py         configuración central — COMPARTIDA por las dos fuentes
├── exportar_grilla.py       genera la grilla de 5 km — 1 vez, compartida (local, límites del DANE, sin Earth Engine)
├── consolidar.py            arma el panel final de UNA fuente (--fuente obligatorio)
├── main_local.py            orquestador de línea de comandos (rama DIST-ALERT + consolidar de ambas)
├── mapa_folium.py           mapa interactivo (Leaflet) de un panel final
├── eda_deforestacion.ipynb   EDA con graficas de un panel final
│
├── fuente_dist_alert/        panel 2023-presente — NASA OPERA DIST-ALERT (un solo sistema)
│   ├── descargar_dist.py     descarga Hansen GFC y DIST-ALERT (3 subcomandos)
│   ├── filtrar_tiles.py      recorta el inventario a tiles reales de Colombia
│   ├── zonal_local.py        motor de cálculo: cruza DIST-ALERT con el bosque; expone
│   │                          indice_celdas()/mascara_bosque(), reutilizadas por fuente_gfw/
│   └── diagnostico_cmr.py    herramienta puntual: valida el catálogo CMR
│
├── fuente_gfw/                panel 2020-presente — GFW integrated disturbance alerts (4 sistemas)
│   ├── configurar_gfw.py     registro de una sola vez en la API de GFW
│   └── descargar_gfw.py       consulta la API de GFW para TODA la ventana 2020-presente;
│                                calcula su propio bosque_ha (anio_mascara_gfw); escribe
│                                datos/crudo/nacional_gfw.csv -- nunca toca nacional.csv
│
├── requirements_local.txt   dependencias Python (pip)
├── .dodsrc                  le dice a GDAL/rasterio dónde están las
│                             credenciales de Earthdata (netrc, cookies)
├── cmr.txt                  salida guardada de una corrida de diagnostico_cmr.py
├── inventario_dist.json.completo   respaldo de un inventario sin filtrar
│
├── METODOLOGIA.md           ← el "qué y por qué" (léalo primero)
├── GUIA_CODIGO.md           ← este documento, el "cómo"
│
└── datos/                   TODO el output cae aquí (ver sección 10)
    ├── grilla/   hansen/   cache/   panel/   logs/     (compartidas)
    ├── dist/                                            (solo fuente_dist_alert)
    ├── gfw/                                              (solo fuente_gfw, cache de lotes API)
    └── crudo/          ← cada fuente deja su PROPIO archivo, nunca compartido:
                            nacional.csv (dist_alert) y nacional_gfw.csv (gfw).
                            consolidar.py lee SOLO el que corresponda a --fuente
                            (ver sección 7) -- jamás los dos juntos.
```

**Por qué cada script movido sigue importando `config_local` sin problema**:
los scripts dentro de `fuente_dist_alert/` y `fuente_gfw/` agregan la
carpeta raíz a `sys.path` al arrancar (ver las primeras líneas de cualquiera
de ellos), un truco liviano para no tener que invocarlos con `python -m`
ni duplicar `config_local.py` — no requiere instalar nada como paquete
Python. Se pueden seguir corriendo igual, sea directo (`python
fuente_dist_alert/zonal_local.py --tile T18NXG`) o a través de
`main_local.py`, que ya apunta a las rutas nuevas.

**Regla general del repositorio**: todo parámetro que pueda cambiar el
resultado vive en `config_local.py`, nunca hardcodeado dentro de otro script.
Si algo en el panel final se ve distinto a lo esperado, el primer lugar a
revisar es ese archivo, no el resto del código.

---

## 2. Preparar el entorno desde cero

Esta sección está pensada para alguien que recibe el repositorio sin ningún
contexto previo (p. ej. el director de tesis, en otro computador).

### 2.1 Requisitos de sistema

- **Python 3.10 o superior** (el código usa sintaxis de anotaciones de tipo
  moderna, p. ej. `str | None`, disponible desde Python 3.10).
- **Sistema operativo**: desarrollado y probado en Windows; no usa nada
  específico de Windows salvo rutas de archivo (que Python maneja de forma
  portable con `pathlib.Path`), así que debería correr igual en Linux/macOS.
- **Espacio en disco libre**: al menos **60 GB** si se va a descargar la
  ventana temporal completa con cadencia mensual (ver estimados de espacio en
  la sección 3). Verifíquelo antes de lanzar la descarga nacional.
- **Conexión a internet estable**: la descarga de DIST-ALERT puede tomar
  varias horas; el pipeline es reanudable (`Ctrl+C` y volver a correr el
  mismo comando), pero conviene no depender de una red que se cae cada pocos
  minutos.

### 2.2 Obtener el código

Copie (o clone, si se publica como repositorio git) la carpeta completa del
proyecto a la máquina destino. No hace falta nada más que los archivos `.py`,
`requirements_local.txt`, `.dodsrc` y los dos documentos `.md` — la carpeta
`datos/` se recrea sola la primera vez que se corre cualquier script (ver
`config_local.py`, que crea el árbol de carpetas al importarse).

### 2.3 Crear un entorno virtual (recomendado)

Aislar las dependencias de este proyecto evita conflictos con otras
instalaciones de Python en la misma máquina.

**Windows (PowerShell):**

```powershell
cd ruta\al\proyecto
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (cmd.exe):**

```cmd
cd ruta\al\proyecto
python -m venv .venv
.venv\Scripts\activate.bat
```

**Linux / macOS:**

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
pip install mgrs        # lo necesita filtrar_tiles.py; no está en requirements_local.txt
```

Contenido de `requirements_local.txt`, y para qué sirve cada paquete:

```
earthaccess>=0.11        # cliente de NASA CMR / LP DAAC (descarga DIST-ALERT)
rasterio>=1.3             # lectura/escritura/reproyección de rasters (GeoTIFF/COG)
pyproj>=3.6                # transformación de coordenadas entre sistemas de referencia
numpy>=1.24
pandas>=2.0
requests>=2.31              # llamadas HTTP directas a la API SQL de GFW (descargar_gfw.py)
pyarrow>=14.0              # motor de lectura/escritura de Parquet
geopandas>=0.14             # exportar_grilla.py (grilla local), cruce DANE opcional de consolidar.py, y las geometrias de celda que descargar_gfw.py manda a la API de GFW
folium>=0.15                # mapa interactivo (mapa_folium.py)
matplotlib>=3.7            # graficas de eda_deforestacion.ipynb
jupyter>=1.0                 # para abrir/correr eda_deforestacion.ipynb
```

`rasterio` en particular puede requerir GDAL como dependencia binaria del
sistema; en Windows, instalarlo con `pip` normalmente ya trae las librerías
necesarias empaquetadas (rueda binaria), sin pasos adicionales. Si falla la
instalación de `rasterio` en Linux, suele ser más simple instalar GDAL con el
gestor de paquetes del sistema primero (`apt install gdal-bin
libgdal-dev`) y después `pip install rasterio`.

### 2.5 Cuentas y credenciales necesarias

| Servicio | Para qué | Dónde crearla | Cuándo se pide |
|---|---|---|---|
| **NASA Earthdata Login** | Toda descarga de DIST-ALERT (`earthaccess`) | https://urs.earthdata.nasa.gov — registro gratuito, sin aprobación manual | La primera vez que se corre cualquier subcomando de `descargar_dist.py` que use `earthaccess` (`inventario` o `dist`); pide usuario/clave por consola |
| **GFW (Global Forest Watch)** | Panel GFW, 2020-presente (`fuente_gfw/`), independiente del panel DIST-ALERT | Self-service vía `python fuente_gfw/configurar_gfw.py signup` — ver §5.9 | Antes de correr cualquier descarga de `fuente_gfw/` |

**`exportar_grilla.py` no requiere ninguna cuenta**: construye la grilla
localmente con `geopandas`, consultando el servicio público (sin
autenticación) del DANE. Esto es un cambio deliberado — la versión anterior
de este pipeline usaba Google Earth Engine para este paso; se eliminó esa
dependencia porque su licencia gratuita prohíbe el uso en trabajo remunerado
para terceros, y este panel es insumo de consultorías comerciales del
Observatorio (ver METODOLOGIA.md, decisión 11 revisada en la bitácora de
la sección 4, con la cita textual de los términos de servicio).

**Earthdata — persistencia de credenciales**: `earthaccess.login(persist=True)`
guarda usuario/clave en `~/.netrc` (en Windows, según `.dodsrc`, en
`C:\Users\<usuario>\_netrc`) para no volver a pedirlos en corridas
posteriores. Si se reproduce el pipeline en otra cuenta de usuario del
sistema operativo, hay que volver a autenticar una vez ahí.

**Consentimiento del producto DIST-ALERT (paso que se olvida fácil)**: una
cuenta de Earthdata nueva, aunque esté correctamente autenticada, puede
devolver **cero resultados** en cualquier búsqueda de DIST-ALERT hasta que
acepte el acuerdo de licencia (EULA) del producto. Esto se resuelve una única
vez: entrar a https://search.earthdata.nasa.gov, buscar "OPERA DIST-ALERT" y
descargar manualmente un solo archivo desde ahí (alcanza con iniciar la
descarga y cancelarla). Esto es la causa más común de que
`descargar_dist.py inventario` reporte 0 gránulos en una máquina nueva — ver
también la sección 11 (solución de problemas).

### 2.6 Verificar la instalación (antes de lanzar nada largo)

```bash
python -c "import earthaccess, rasterio, pyproj, numpy, pandas, geopandas, requests, folium; print('OK')"
```

(sin `ee`: este pipeline no depende de Google Earth Engine — ver decisión 11
revisada, METODOLOGIA.md §4, y §5.2 más abajo.)

Si esto imprime `OK` sin errores, el entorno está listo. Después, un chequeo
más específico de credenciales:

```bash
python -c "import earthaccess; a = earthaccess.login(persist=True); print('Earthdata:', a.authenticated)"
```

---

## 3. Orden exacto de ejecución

Todos los comandos se corren **desde la raíz del proyecto**, con el entorno
virtual activado. El orquestador es `main_local.py`; se indica también el
comando equivalente por si se prefiere correr el script suelto (por ejemplo,
para pasarle argumentos que `main_local.py` no expone).

```
┌──────────────────────────┐
│ 0. pip install ...         │
└──────────────┬────────────┘
               ▼
┌──────────────────────────┐
│ 1. grilla  (local, DANE)   │  ~1 min · sin cuentas
└──────────────┬────────────┘
               │
     ┌─────────┴─────────┐
     ▼                   ▼
┌─────────────┐   ┌────────────────┐
│ 2. hansen     │   │ 3. inventario   │  ~5-15 min · requiere cuenta Earthdata
│  ~5 GB, ~10min│   │  sin descargar   │
└──────┬────────┘   └───────┬────────┘
       │                    ▼
       │           ┌────────────────────┐
       │           │ 4. filtrar_tiles.py  │  ~1 min
       │           └───────┬────────────┘
       │                   ▼
       │           ┌────────────────────┐
       │           │ 5. piloto (opcional) │  ~5 min, 1 tile
       │           └───────┬────────────┘
       │                   ▼
       │           ┌────────────────────┐
       │           │ 6. descargar (dist)  │  horas · decenas de GB
       │           └───────┬────────────┘
       └───────────────────┤
                            ▼
                  ┌────────────────────┐
                  │ 7. zonal              │  ~20-60 min (todo el país)
                  │    (panel DIST-ALERT) │
                  └───────┬────────────┘
                            ▼
                  ┌────────────────────┐
                  │ 8. consolidar         │  ~1-2 min
                  │    --fuente dist_alert│
                  └────────────────────┘

Rama GFW (opcional, independiente, ver Paso 7-GFW): no depende del paso 7
(zonal DIST-ALERT) ni lo modifica, pero SÍ necesita que datos/dist/ tenga
un archivo de referencia por CADA tile del país (153 en la corrida de
referencia) -- eso solo lo deja el paso 6 (descarga nacional completa),
no el paso 5 (piloto, que descarga un único tile y sirve solo para probar
que descargar_gfw.py corre sin errores, no para el panel nacional real).

        6 ──▶ 7-GFW. descargar_gfw.py  (~igual de largo que 6, vía API)
                     ▼
             8. consolidar --fuente gfw
```

Los tiempos son orden de magnitud, dependientes de la velocidad de red y del
número de núcleos/disco del computador — no son una garantía.

### Paso 0 — instalar dependencias

Ver sección 2.4.

### Paso 1 — construir la grilla (local, una sola vez)

```bash
python main_local.py grilla
# equivale a: python exportar_grilla.py
```

Corre enteramente en el computador local, sin ninguna cuenta ni
autenticación: descarga los límites departamentales del DANE (servicio
público) y construye la malla de 5 km con `geopandas`. Produce
`datos/grilla/grilla_colombia_5km.csv`. El script **verifica que la grilla
quede alineada al origen de la proyección EPSG:3116** antes de guardar
(garantizado por construcción, pero se comprueba igual como prueba de
regresión): si no lo estuviera, el indexado aritmético por píxel de
`zonal_local.py` (Paso 7) daría resultados incorrectos de forma silenciosa,
así que el script se detiene con un error explícito en vez de continuar.

**Verificación**: el archivo debe tener del orden de 45 000-46 000 filas y
las columnas `cell_id, lon, lat, x3116, y3116, ix, iy, departamento`. El log
imprime cuántas celdas y departamentos encontró — compárelo contra lo
esperado (33 unidades: los 32 departamentos más Bogotá D.C., que el DANE
trata como una unidad de nivel departamento propia; si aparecen menos,
revise que el servicio del DANE haya respondido completo — el script avisa
por consola cuántas celdas quedaron sin departamento asignado y las
descarta, normalmente un puñado de celdas costeras).

### Paso 2 — descargar Hansen GFC (no requiere Earthdata)

```bash
python main_local.py hansen
# equivale a: python fuente_dist_alert/descargar_dist.py hansen
```

Descarga HTTP directa, sin autenticación, ~5 GB en 12 archivos (6 gránulos ×
2 capas). Reanudable: una interrupción y una nueva corrida del mismo comando
saltan los archivos que ya están completos.

**Verificación**: `datos/hansen/` debe tener 12 archivos `.tif`, cada uno de
varios cientos de MB. `python main_local.py estado` reporta el conteo y el
peso total.

### Paso 3 — inventariar DIST-ALERT (sin descargar nada)

```bash
python main_local.py inventario
# equivale a: python fuente_dist_alert/descargar_dist.py inventario
```

Consulta a NASA CMR, mes por mes, dentro del `bbox` rectangular de Colombia
(que también toca países vecinos y océano — se filtra en el Paso 4). **No
descarga archivos reales**, solo construye el plan y estima el espacio en
disco. Guarda `datos/logs/inventario_dist.json`.

**Verificación**: el log final imprime "tiles MGRS distintos" y "archivos a
descargar" con una estimación en GB. Si el conteo de tiles es 0, revise la
sección 11 (probablemente falta aceptar el EULA de DIST-ALERT).

### Paso 4 — recortar el inventario al territorio real

```bash
python fuente_dist_alert/filtrar_tiles.py
```

**No** está expuesto en `main_local.py`; se corre directo. Requiere que ya
existan la grilla (Paso 1) y el inventario (Paso 3). Convierte cada celda a
su tile MGRS con la librería `mgrs` y descarta del inventario cualquier tile
sin ninguna celda colombiana — el ahorro suele ser sustancial frente al
`bbox` rectangular. Guarda un respaldo del inventario sin filtrar en
`datos/logs/inventario_dist.json.completo` antes de sobrescribir.

**Verificación**: el log reporta cuántos tiles se descartaron y el ahorro en
porcentaje. Si el mensaje de error dice que los dos conjuntos de tiles "no se
cruzan en NADA", **no** siga adelante — hay un desajuste de formato entre el
inventario y la grilla que hay que resolver primero (ver sección 11).

### Paso 5 (opcional, recomendado antes del país completo) — piloto con un tile

```bash
python main_local.py piloto --tile T18NXG
```

Descarga y procesa **un solo tile** de punta a punta (descarga + cálculo
zonal), para validar en minutos que todo el flujo funciona antes de lanzar
horas de descarga nacional. `T18NXG` cubre una zona con deforestación activa
conocida (Caquetá), buena para confirmar que el pipeline efectivamente
detecta eventos y no solo corre sin errores.

### Paso 6 — descarga nacional de DIST-ALERT

```bash
python main_local.py descargar
# equivale a: python fuente_dist_alert/descargar_dist.py dist
```

Descarga real de los `.tif` de `VEG-DIST-STATUS` y `VEG-DIST-DATE`, 6 hilos
simultáneos, con reintentos automáticos. **Reanudable** con `Ctrl+C` y
relanzando el mismo comando. Al final, si algo quedó pendiente, se escribe en
`datos/logs/fallidos_dist.txt` para poder reintentar solo eso sin repetir
todo.

**Verificación**: `python main_local.py estado` muestra cuántos tiles y
archivos hay en disco y cuántos GB pesan. Compárelo contra la estimación del
Paso 3/4.

### Paso 7 — cálculo zonal (el motor de cómputo)

```bash
python main_local.py zonal
# equivale a: python fuente_dist_alert/zonal_local.py
```

Ver la sección 6 para el detalle de implementación. Produce
`datos/crudo/nacional.csv` (formato ANCHO). Este paso reproyecta Hansen por
cada tile la primera vez (lento) y cachea el resultado en `datos/cache/`, así
que una segunda corrida (por ejemplo tras agregar más meses de DIST-ALERT) es
mucho más rápida.

**Verificación**: el log final imprime celdas con bosque, bosque total en
hectáreas y deforestación total detectada. Si "deforestación total" da 0,
algo está mal (revisar que `datos/dist/` sí tenga archivos y que
`estados_evento` en `config_local.py` no se haya cambiado por error a algo
vacío).

### Paso 7-GFW — panel alternativo 2020-presente (independiente, opcional)

**Solo si necesita datos desde 2020-01**. Este paso NO depende del Paso 7
(zonal DIST-ALERT) ni lo modifica — produce un archivo crudo completamente
aparte. Si el proyecto solo necesita 2023 en adelante, sáltese este paso y
vaya directo al Paso 8 con `--fuente dist_alert`.

**Requiere el Paso 6 completo (descarga nacional), no solo el Paso 5
(piloto)**: `descargar_gfw.py` calcula su bosque base recorriendo
`datos/dist/<tile>/` tile por tile, así que solo cubre el territorio de
los tiles que ya tengan un archivo ahí. Con solo el tile del piloto
(`T18NXG`) el script corre sin error, pero el panel resultante cubriría
únicamente ese tile, no el país — no es el resultado documentado en este
archivo (44 601 celdas). Para reproducir el mismo panel nacional que
documenta esta guía, complete el Paso 6 antes de este paso.

```bash
# una sola vez, si todavia no tiene la API key:
python fuente_gfw/configurar_gfw.py signup --nombre "Su Nombre" --email correo@ejemplo.com
python fuente_gfw/configurar_gfw.py apikey --email correo@ejemplo.com --password "la-del-correo"

# la descarga en si (cubre TODA la ventana 2020-presente, no solo un tramo):
python fuente_gfw/descargar_gfw.py
```

Ver la sección 5.10 para el detalle. Consulta la API de GFW (no descarga
rásteres) para el evento, y calcula su propio `bosque_ha` reutilizando
`indice_celdas()`/`mascara_bosque()` de `fuente_dist_alert/zonal_local.py`
con `anio_mascara_gfw = 2019`, recorriendo **todos** los tiles que
encuentre como subcarpeta de `datos/dist/` (necesita al menos un archivo
de referencia por cada uno — ver la nota del Paso 6 arriba). Escribe
`datos/crudo/nacional_gfw.csv`, un archivo **separado** de `nacional.csv`:
nunca lee ni modifica el archivo del Paso 7.

**Verificación**: el log final debe mostrar 153 tiles procesados (o el
número de tiles que tenga `datos/dist/` en su corrida), el rango de
columnas de periodo yendo de `d_2020_01` al mes más reciente disponible, y
que `datos/crudo/nacional_gfw.csv` existe como archivo aparte de
`datos/crudo/nacional.csv`. Si el log solo menciona 1 tile, el panel no
va a ser el nacional completo — revise que el Paso 6 haya terminado.

### Paso 8 — consolidar el panel final (elegir la fuente)

`--fuente` es obligatorio: no hay panel "por defecto", precisamente para
que sea imposible generar uno sin saber de qué fuente de evento salió.

```bash
# panel DIST-ALERT (2023-presente, del Paso 7):
python main_local.py consolidar --fuente dist_alert

# panel GFW (2020-presente, del Paso 7-GFW):
python main_local.py consolidar --fuente gfw

# opcionalmente, con el cruce de municipios del DANE (aplica a cualquiera de los dos):
python main_local.py consolidar --fuente dist_alert --dane ruta/al/MGN_MPIO.shp
```

Ver la sección 7 para el detalle. Cada corrida produce un par de archivos
propio: `datos/panel/panel_deforestacion_colombia_dist_alert.csv`/`.parquet`
o `datos/panel/panel_deforestacion_colombia_gfw.csv`/`.parquet` — nunca se
mezclan ni se sobrescriben entre sí.

**Verificación**: el log final imprime filas, celdas, periodos, rango de
fechas, % de celda-mes con evento y hectáreas totales. Compare contra la
sección ["Cómo se ve la base de datos final"](#cómo-se-ve-la-base-de-datos-final)
más abajo — si la corrida cubrió la misma ventana temporal, los números
deberían ser muy parecidos a los documentados ahí (esos números son del
panel DIST-ALERT).

### Comando de estado (en cualquier momento)

```bash
python main_local.py estado
```

Resume qué hay en disco en cada etapa y cuánto pesa, sin modificar nada —
útil para saber dónde iba el proceso después de una interrupción, o para que
el director de tesis confirme que una corrida en su máquina llegó tan lejos
como la original.

---

## Cómo se ve la base de datos final

*(Números de una corrida puntual de cada panel, como ejemplo — el pipeline
sigue corriendo y ambos crecen. Para las cifras y gráficas actualizadas,
correr [`eda_deforestacion.ipynb`](eda_deforestacion.ipynb), sección 8, con
`FUENTE` en el valor que interese.)*

El panel **DIST-ALERT** resultante
(`datos/panel/panel_deforestacion_colombia_dist_alert.csv`) es una
tabla de **1 917 585 filas × 17 columnas**: 44 595 celdas × 43 periodos
mensuales (2023-01 a 2026-07), 32 departamentos. Cada fila es una celda-mes.

`filas = celdas × periodos` exactamente (44 595 × 43 = 1 917 585) — es la
huella de que `balancear()` (ver sección 7) hizo su trabajo: el panel es un
rectángulo perfecto, sin huecos.

El panel **GFW** (`datos/panel/panel_deforestacion_colombia_gfw.csv`)
tiene exactamente las mismas 17 columnas (misma función `consolidar()`) —
**3 523 479 filas**: 44 601 celdas × 79 periodos mensuales (2020-01 a
2026-07), 32 departamentos (44 601 × 79 = 3 523 479, mismo chequeo de
rectángulo perfecto). No es comparable número a número con el panel
DIST-ALERT — ver METODOLOGIA.md §2.4 y decisión 15.

**Las 17 columnas**, en el orden en que aparecen en el CSV:

| # | Columna | Tipo | De dónde sale | Qué es |
|---|---|---|---|---|
| 1 | `cell_id` | texto | grilla (DANE) | id de la celda: `"{lon×1e4}_{lat×1e4}"` redondeado |
| 2 | `periodo` | fecha | `cargar_crudo` | primer día del mes, p. ej. `2023-09-01` |
| 3 | `area_def_ha` | float | `zonal_local.py` | hectáreas deforestadas **en ese mes**, en esa celda |
| 4 | `lon` | float | grilla (DANE) | longitud del centroide, EPSG:4326 |
| 5 | `lat` | float | grilla (DANE) | latitud del centroide, EPSG:4326 |
| 6 | `bosque_base_ha` | float | Hansen (`zonal_local.py`) | bosque disponible al arrancar el pipeline (dosel ≥30 %, sin pérdida antes de 2022) |
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

Si se corrió `consolidar.py --dane ...`, se agrega una columna 18,
`cod_dane` (código de municipio del DANE). La **definición matemática exacta**
de cada una de estas variables (fórmulas, no solo descripción) está en
[METODOLOGIA.md, sección 3.7](METODOLOGIA.md#37-del-bosque-base-a-las-variables-de-exposición-y-tasa).

**Una celda sin eventos** (el caso más común):

```
cell_id       , periodo    , area_def_ha, lon         , lat        , bosque_base_ha, departamento, def_acum_ha, bosque_remanente_ha, tasa_def, evento, lag_1_ha, lag_2_ha, lag_3_ha, media_movil_3, anio, mes
-668856_13524 , 2023-01-01 , 0.0        , -66.8856008 , 1.3523824  , 2411.91       , Guainia     , 0.0        , 2411.91            , 0.0     , 0     ,          ,         ,         ,              , 2023, 1
-668856_13524 , 2023-02-01 , 0.0        , -66.8856008 , 1.3523824  , 2411.91       , Guainia     , 0.0        , 2411.91            , 0.0     , 0     , 0.0      ,         ,         ,              , 2023, 2
```

(`lag_1_ha`, `lag_2_ha`, `lag_3_ha` y `media_movil_3` empiezan vacíos: en los
primeros meses de cada celda todavía no hay historia suficiente para
calcularlos.)

**La misma celda, el mes en que sí hubo evento** (septiembre de 2023: 0.18 ha
confirmadas, es decir 2 píxeles DIST-ALERT — cada píxel son 0.09 ha):

```
cell_id       , periodo    , area_def_ha, ... , def_acum_ha, bosque_remanente_ha, tasa_def   , evento, lag_1_ha, lag_2_ha, lag_3_ha, media_movil_3, anio, mes
-668856_13524 , 2023-09-01 , 0.18       , ... , 0.18       , 2411.91            , 0.0000746  , 1     , 0.0      , 0.0      , 0.0      , 0.0           , 2023, 9
```

`tasa_def` sale minúscula (0.0000746 = 0.007 %) porque el denominador es todo
el bosque remanente de la celda. Es lo esperado: la enorme mayoría de
celda-mes tienen `evento = 0` (el panel está muy desbalanceado hacia la clase
negativa — ver el análisis de esto en
[METODOLOGIA.md, sección 6](METODOLOGIA.md#6-limitaciones-conocidas)).

Para inspeccionarlo directamente en Python:

```python
import pandas as pd
df = pd.read_parquet("datos/panel/panel_deforestacion_colombia_dist_alert.parquet")
# o, para el panel GFW:
# df = pd.read_parquet("datos/panel/panel_deforestacion_colombia_gfw.parquet")
# si pyarrow no esta instalado, usar en su lugar:
# df = pd.read_csv("datos/panel/panel_deforestacion_colombia_dist_alert.csv", parse_dates=["periodo"])

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
| `dist_short_name`, `dist_version` | Identificador exacto de la colección DIST-ALERT en CMR | confirmado con `diagnostico_cmr.py`, sección 5.7 |
| `capa_estado`, `capa_fecha` | Nombres de las dos capas que se descargan de cada gránulo | METODOLOGIA §2.2 |
| `estados_evento` | Qué códigos de `VEG-DIST-STATUS` cuentan como "evento" — `(6, 8)` | METODOLOGIA §3.3, decisión 2 |
| `epoca_dist` | Fecha 0 para decodificar `VEG-DIST-DATE` | METODOLOGIA §3.4 |
| `hansen_version`, `umbral_dosel`, `anio_mascara` | Definen la máscara de bosque base **del panel DIST-ALERT** | METODOLOGIA §3.2 |
| `anio_mascara_gfw` | Corte de Hansen para la máscara de bosque **del panel GFW** (2019, no 2022) | METODOLOGIA §3.2, decisión 5 revisada |
| `fecha_inicio`, `fecha_fin`, `frecuencia` | Ventana temporal del panel y su resolución mensual | METODOLOGIA §1.3 |
| `cadencia_snapshot` | Cada cuánto se descarga una instantánea DIST-ALERT | METODOLOGIA §4, decisión 8 |
| `grid_scale_m`, `grid_crs` | Tamaño de celda (5000 m) y proyección de la grilla | METODOLOGIA §1.2, §3.6 |
| `bosque_minimo_ha` | Umbral para descartar celdas sin bosque suficiente | sección 7 de este documento |
| `bbox` | Rectángulo usado para consultar CMR y Hansen | METODOLOGIA §4, decisión 12 |
| `tiles` | Si no está vacío, restringe el pipeline a esos tiles MGRS | usado por `--tile` en varios subcomandos |
| `gfw_dataset`, `gfw_version` | Identificador del dataset GFW en la API SQL (`gfw_integrated_dist_alerts`, `latest`) | METODOLOGIA §2.4 |
| `fecha_inicio_gfw` | Inicio de la ventana del panel GFW (2020-01-01); el fin lo comparte con `fecha_fin` | METODOLOGIA §2.4 |
| `gfw_confianza_minima` | Niveles de confianza de GFW que cuentan como evento (`high`, `highest`) | METODOLOGIA §2.4, decisión 13 |
| `gfw_celdas_por_lote`, `gfw_lotes_en_paralelo` | Tamaño de lote y paralelismo de las consultas a la API de GFW | sección 5.10 de este documento |

### 5.2 `exportar_grilla.py` — grilla de 5 km (local, sin Earth Engine)

Descarga los polígonos de departamento del DANE (Marco Geoestadístico
Nacional, servicio público de ArcGIS, sin autenticación), los une en un
polígono nacional, y construye sobre él una malla de celdas cuadradas de
5 km con `geopandas`/`shapely` — cada celda como múltiplo entero exacto del
lado, así que queda alineada al origen de `EPSG:3116` por construcción, no
por casualidad. Calcula centroides en dos proyecciones (4326 para el cruce
DANE municipal posterior, 3116 para el indexado local) y asigna el
departamento por intersección espacial del centroide con los mismos
polígonos del DANE. Aun así corre la misma verificación de alineación que
la versión anterior, como prueba de regresión (ver Paso 1, sección 3). El
polígono nacional se simplifica con tolerancia de 100 m antes del filtro
espacial — el MGN del DANE es de precisión catastral completa
(~280 000 vértices sin simplificar), y sin este paso el filtro tardaba
varios minutos en vez de segundos; 100 m es irrelevante frente al lado de
celda de 5000 m, así que no cambia qué celdas quedan dentro o fuera.

### 5.3 `descargar_dist.py` — descargas (Hansen + DIST-ALERT)

Tres subcomandos (`hansen`, `inventario`, `dist`), todos comparten el mismo
patrón de descarga robusta: escribir a un archivo `.parcial`, y solo
renombrarlo al nombre final si la descarga terminó bien — así una descarga
interrumpida nunca deja un archivo a medias con el nombre "bueno" (lo que
engañaría al chequeo de "ya existe, no lo vuelvas a bajar" en la siguiente
corrida).

- `granulos_hansen()`: calcula qué gránulos de 10°×10° de Hansen intersectan
  el `bbox`, a partir de las coordenadas.
- `periodos()`: parte la ventana temporal en tramos según `cadencia_snapshot`.
- `buscar_periodo()`: para un tramo de fechas, busca en CMR y se queda con la
  instantánea **más reciente** de cada tile dentro de ese tramo.
- `cmd_inventario`: recorre todos los periodos, cuenta gránulos, no descarga.
- `cmd_dist`: reutiliza el inventario si existe, arma la lista de tareas de
  descarga y las reparte en un `ThreadPoolExecutor`.

### 5.4 `filtrar_tiles.py` — recorte al territorio real

Convierte cada celda de la grilla a su tile MGRS de 100 km con la librería
`mgrs`, y descarta del inventario cualquier tile sin ninguna celda
colombiana. Guarda respaldo del inventario sin filtrar por seguridad.

### 5.5 `zonal_local.py` — el motor de cálculo (detalle en sección 6)

Además de producir `nacional.csv`, expone dos funciones cacheadas por
tile (`indice_celdas()`, `mascara_bosque()`) que `fuente_gfw/descargar_gfw.py`
importa y reutiliza tal cual (ver 5.10) para calcular su propio bosque
base sin reimplementar la reproyección de Hansen.

### 5.6 `consolidar.py` — panel final (detalle en sección 7)

Requiere `--fuente {dist_alert,gfw}` explícito, sin default: lee
únicamente el CSV crudo de esa fuente (`ARCHIVO_CRUDO` en el módulo mapea
cada nombre de fuente a su archivo fijo) y nunca ambos a la vez. Se puede
correr como subcomando de `main_local.py` o directo:
`python consolidar.py --fuente gfw`.

### 5.7 `diagnostico_cmr.py` — herramienta de diagnóstico puntual

No forma parte de la secuencia normal de ejecución. Se usa una sola vez (o
cuando algo deja de funcionar tras un cambio en el catálogo de la NASA) para
averiguar el `short_name`/`version` exactos que reconoce CMR para DIST-ALERT,
y confirmar el formato de nombre de archivo del que depende el parseo en
`descargar_dist.py`:

```bash
python fuente_dist_alert/diagnostico_cmr.py > cmr.txt
```

El archivo `cmr.txt` en la raíz del proyecto es la salida guardada de una
corrida real — confirma que la colección correcta es
`OPERA_L3_DIST-ALERT-HLS_V1` (versión `"1"`), que un gránulo trae 19 archivos
(listados completos ahí), y que el patrón de nombre esperado
(`..._T18NWH_20240601T152659Z_..._VEG-DIST-STATUS.tif`) coincide con lo que
`RE_TILE` y el índice `[4]` de `descargar_dist.py` asumen. **Si CMR cambia el
formato del catálogo en el futuro** (nueva versión del producto, cambio de
nombre de colección), este es el primer script a correr para diagnosticar
qué cambió.

### 5.8 `main_local.py` — orquestador

Cada subcomando (`grilla`, `hansen`, `inventario`, `descargar`, `piloto`,
`zonal`, `consolidar`, `estado`) arma la línea de comandos correcta y lanza
el script correspondiente como subproceso (`subprocess.call`), excepto
`consolidar`, que importa la función directamente. `estado` es el único
subcomando que no delega: lista lo que hay en disco en cada carpeta.
`consolidar` exige `--fuente {dist_alert,gfw}`. Este orquestador cubre la
rama DIST-ALERT de punta a punta; la rama GFW se corre aparte
(`fuente_gfw/configurar_gfw.py`, `fuente_gfw/descargar_gfw.py` — mismo
patrón que `filtrar_tiles.py`, sin subcomando propio en `main_local.py`) y
solo converge aquí en el paso de `consolidar`.

### 5.9 `fuente_gfw/configurar_gfw.py` — registro en la API de GFW

No forma parte de la secuencia normal de ejecución; se corre una sola vez,
antes de que `fuente_gfw/descargar_gfw.py` pueda funcionar. Automatiza el
flujo de autenticación de la API de Global Forest Watch en tres llamadas
(`/auth/sign-up` → `/auth/token` → `/auth/apikey`), guardando la API key
resultante en `datos/logs/gfw_api_key.txt` (fuera de control de versiones,
como cualquier credencial de este proyecto):

```bash
python fuente_gfw/configurar_gfw.py signup --nombre "Su Nombre" --email correo@ejemplo.com
python fuente_gfw/configurar_gfw.py apikey --email correo@ejemplo.com --password "la-del-correo"
```

El esquema exacto de las respuestas de esos dos últimos pasos no está
documentado públicamente por la API de GFW; el script imprime la respuesta
cruda del servidor si no encuentra el campo esperado, en vez de fallar en
silencio.

### 5.10 `fuente_gfw/descargar_gfw.py` — panel GFW, 2020-presente (independiente)

**No depende de `nacional.csv`.** Este script produce su propio archivo
crudo, `datos/crudo/nacional_gfw.csv`, y nunca lee ni modifica el archivo
que produce `zonal_local.py`. El prerrequisito real tiene dos partes
distintas, que conviene no confundir:

- **Por tile, basta un solo archivo** (no el histórico completo de 43
  instantáneas), porque `bosque_ha_por_celda()` reutiliza `indice_celdas()`
  y `mascara_bosque()` de `fuente_dist_alert/zonal_local.py` (vía
  `sys.path.insert`) solo para tener la cuadrícula geométrica de ese tile
  sobre la que reproyectar Hansen — nunca lee `VEG-DIST-STATUS`/
  `VEG-DIST-DATE` de esos archivos.
- **Pero tiene que haber un archivo para CADA tile del país** (los 153 de
  la corrida de referencia), no solo para uno: el script recorre
  `datos/dist/` y calcula bosque únicamente para los tiles que encuentre
  como subcarpeta ahí. La descarga piloto del Paso 5 deja un solo tile
  (`T18NXG`) — sirve para probar que el script corre sin errores, no para
  producir el panel nacional. Para el panel completo hace falta haber
  terminado el Paso 6 (descarga nacional) primero.

La llamada usa `dataclasses.replace(cfg,
anio_mascara=cfg.anio_mascara_gfw)` (2019, no 2022) para que el corte de
bosque coincida con el inicio de la ventana de este panel (2020-01), y
las cachés de `mascara_bosque()` en `datos/cache/` ya están separadas por
`anio_mascara` (ver decisión 5 revisada, METODOLOGIA.md §4), así que
convive sin conflicto con las cachés que use `zonal_local.py`.

```bash
python fuente_gfw/descargar_gfw.py
```

A diferencia de `descargar_dist.py` (descarga archivos GeoTIFF por tile),
el evento de esta fuente se consulta vía SQL: `celdas_como_poligonos()`
convierte cada celda de la grilla a un rectángulo de 5 km en WGS84, y
`procesar_lote()` manda esas geometrías en lotes de `gfw_celdas_por_lote`
(400 por defecto, límite real de payload de la API: 256 KB) al endpoint
asíncrono `/dataset/gfw_integrated_dist_alerts/latest/query/batch`, con
esta consulta corriendo una vez por celda, para **toda** la ventana
2020-presente (no solo un tramo):

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
el filtro de confianza usa `OR` en vez de `IN (...)`.) Cada lote se
cachea en `datos/gfw/lote_NNNN.json` apenas se descarga, así que el
script es reanudable igual que `descargar_dist.py`.

**Salida propia, sin fusión.** `agregar_a_mensual()` junta los resultados
de todos los lotes en una tabla ancha (`cell_id`, `d_2020_01`, ...,
hasta el mes más reciente), y se combina con `bosque_ha_por_celda()` en
un único DataFrame que se escribe directo a `datos/crudo/nacional_gfw.csv`
— no hay ningún `merge` ni `concat` con `nacional.csv` en ningún punto de
este script (a diferencia de un diseño anterior, ya descartado — ver
decisión 15, METODOLOGIA.md §4). Las dos fuentes conviven en
`datos/crudo/` como dos archivos independientes; es `consolidar.py --fuente
{...}` el que decide, explícitamente, cuál usar (nunca este script).

**Verificación**: el log final imprime celdas con bosque, bosque total en
hectáreas, deforestación total y el archivo de salida
(`datos/crudo/nacional_gfw.csv`) — debería mostrar columnas de periodo
yendo de `d_2020_01` al mes más reciente configurado en `fecha_fin`.

---

## 6. Cómo funciona el cálculo zonal, en código

*(El razonamiento matemático completo de esta sección está en
[METODOLOGIA.md, sección 3](METODOLOGIA.md#3-marco-conceptual-de-píxeles-a-panel);
aquí se describe solo la implementación.)*

Por cada **tile MGRS**, una sola vez, cacheado en disco en `datos/cache/`:

1. **Índice de celda por píxel** (`indice_celdas`, cacheado en
   `<tile>__idx.npy`): a cada píxel del tile (en su proyección UTM nativa) se
   le calculan las coordenadas de su centro, se transforman a `EPSG:3116` con
   `pyproj.Transformer`, y se calcula `floor(coordenada / 5000)` en x e y.
   Ese par de enteros identifica la celda de 5 km. Se resuelve de forma
   vectorizada con `np.unique(..., return_inverse=True)`: solo se consulta el
   diccionario Python `mapa_celda` sobre los pares de coordenadas *únicos*
   (muchos menos que el total de píxeles, porque una celda de 5 km cubre
   miles de píxeles de 30 m), y el resultado se "reparte" de vuelta a todos
   los píxeles con `numpy` puro — evita un bucle Python por píxel, que sería
   demasiado lento con millones de píxeles por tile.

2. **Máscara de bosque** (`mascara_bosque`, cacheada en `<tile>__bosque.npy`):
   los gránulos de Hansen se reproyectan (`rasterio.warp.reproject`,
   remuestreo *nearest*) de su cuadrícula de 10°×10° a la cuadrícula exacta
   del tile DIST-ALERT. Un tile puede caer sobre el borde de dos gránulos
   Hansen; se combinan con `np.maximum` (donde un gránulo no cubre nada,
   `reproject` deja `dst_nodata=0`, así que el máximo entre gránulos siempre
   conserva el valor real donde exista).

Con esas dos cosas cacheadas, `procesar_tile()` recorre las instantáneas de
DIST-ALERT **en orden cronológico** (el nombre de archivo, que empieza con la
fecha del periodo, ya ordena cronológicamente al ordenar alfabéticamente),
manteniendo una máscara booleana acumulada `ya_contado` sobre el tile
completo. En cada instantánea:

```python
nuevo = np.isin(est, objetivo) & valido_base & ~ya_contado
```

donde `est` es el arreglo de estados de esa instantánea, `objetivo = (6, 8)`,
y `valido_base` marca los píxeles que caen dentro de la grilla y son bosque.
Los píxeles `nuevo` se decodifican con `VEG-DIST-DATE` a un índice de mes
usando `tabla_dia_a_mes()` (un vector de *lookup* precalculado una sola vez:
`tabla[dias_desde_epoca] = indice_de_mes`, mucho más rápido que convertir
cada valor con `pandas.to_datetime` uno por uno) y se suman al mes que les
corresponde con `np.bincount` sobre una clave lineal
`celda * n_meses + mes` — el equivalente vectorizado de "por cada píxel
nuevo, sumar 1 a `acum[celda, mes]`" sin un bucle Python por píxel.

`ya_contado` se actualiza con `ya_contado |= nuevo` al final de cada
instantánea, así que un píxel que sigue en estado 6/8 en instantáneas
posteriores nunca vuelve a sumarse.

Al combinar los resultados de todos los tiles procesados, `main()` usa
`np.maximum` (no suma) tanto para `bosque_total` como para `def_total`, para
no duplicar el conteo en las franjas donde dos tiles MGRS se traslapan.

Salida: `datos/crudo/nacional.csv`, formato ANCHO — una fila por celda, con
columnas `bosque_ha` y una columna `d_AAAA_MM` por cada mes del panel.

---

## 7. Cómo se construye el panel, en código

*(El razonamiento y las fórmulas exactas están en
[METODOLOGIA.md, sección 3.7](METODOLOGIA.md#37-del-bosque-base-a-las-variables-de-exposición-y-tasa);
aquí, la implementación en `consolidar.py`.)*

Cinco funciones, encadenadas por `consolidar(cfg, fuente, ...)`:

1. **`cargar_crudo`**: lee **un único** CSV crudo — `ARCHIVO_CRUDO[fuente]`
   mapea `"dist_alert"` a `datos/crudo/nacional.csv` y `"gfw"` a
   `datos/crudo/nacional_gfw.csv`, nunca los dos — y pasa la tabla ANCHA
   (una columna por mes) a LARGA (una fila por celda-mes) con
   `pandas.melt`. No hay ningún `glob`/`concat` de varios archivos: es
   deliberado, para que sea imposible mezclar las dos fuentes por
   accidente (ver decisión 15, METODOLOGIA.md §4).

2. **`filtrar_dominio`**: descarta celdas con menos de `bosque_minimo_ha`
   (50 ha por defecto) de bosque base, con un filtro simple de `pandas`.

3. **`balancear`**: construye un `pd.MultiIndex.from_product([celdas,
   periodos])` — todas las combinaciones posibles — y hace `reindex` contra
   él, rellenando con 0 las combinaciones celda-mes que no existían en los
   datos crudos (porque no hubo ningún evento ese mes en esa celda). Esto es
   lo que garantiza que el panel final sea un rectángulo perfecto (ver
   sección 4).

4. **`derivar_variables`**: usa `groupby("cell_id").cumsum()`,
   `.shift(k)` y `.rolling(3)` de `pandas`, todo ordenado cronológicamente
   por celda de antemano (`sort_values(["cell_id", "periodo"])`) — el
   `groupby` se reconstruye después de cada columna nueva, en vez de
   reutilizar un objeto `groupby` creado antes de añadir la columna, porque
   eso último es frágil en `pandas` (el objeto no siempre "ve" columnas
   agregadas después de crearlo).

5. **`asignar_municipio`** (opcional, solo si se pasa `--dane`): usa
   `geopandas.sjoin` con predicado `within` para unir cada centroide de celda
   al polígono municipal del DANE que lo contiene. Import perezoso de
   `geopandas` dentro de la función — si no está instalado, el resto del
   pipeline sigue funcionando sin esta columna.

Salida: `datos/panel/panel_deforestacion_colombia_{fuente}.csv` y
`.parquet` (este último requiere `pyarrow`; si no está instalado, se
guarda solo el CSV y se imprime una advertencia, sin detener la
ejecución). El sufijo `_dist_alert` o `_gfw` en el nombre de archivo es
deliberado: hace imposible que una corrida sobrescriba en silencio el
panel de la otra fuente.

---

## 8. El mapa interactivo (`mapa_folium.py`)

Genera un mapa Leaflet (vía `folium`) para inspeccionar visualmente el panel
final, sin abrir el CSV ni un SIG de escritorio:

```bash
python mapa_folium.py
```

Produce `datos/panel/mapa_deforestacion.html` (ábrase con doble clic en
cualquier navegador). Agrega el panel largo a una fila por celda (suma de
`area_def_ha` en toda la ventana temporal) y monta tres capas conmutables:

- **Mapa de calor** de la deforestación total — escala a las ~44 500 celdas
  sin problema, porque el peso de cada punto se codifica en un arreglo
  compacto `[lat, lon, peso]`, no un elemento por marcador.
- **Celdas con deforestación** (agrupadas en *cluster*) — limitada por
  defecto a los `--top-n 3000` focos de mayor deforestación total, porque un
  marcador con popup por cada una de las ~30 000 celdas con algún evento
  generaba un archivo HTML de más de 40 MB, lento de abrir. El mapa de calor
  ya cubre la vista completa; esta capa es para hacer clic y ver el detalle
  de los focos más importantes.
- **Bosque base** (contexto), apagada por defecto.

```bash
python mapa_folium.py --fuente gfw                  # mapa del panel GFW en vez del DIST-ALERT (default)
python mapa_folium.py --umbral-ha 1 --top-n 5000   # ajustar el filtro de marcadores
python mapa_folium.py --salida otro_nombre.html
```

Cae automáticamente al CSV si `pyarrow` no está instalado y por lo tanto no
se puede leer el `.parquet`.

---

## 9. El notebook de EDA (`eda_deforestacion.ipynb`)

Análisis exploratorio de **un** panel final (elegido con la variable
`FUENTE = "dist_alert"` o `"gfw"` en la sección 1 del notebook), con 13
secciones de gráficas (`matplotlib`, sin dependencias adicionales de
visualización). Se abre con Jupyter:

```bash
jupyter notebook eda_deforestacion.ipynb
```

o desde VS Code / cualquier editor con soporte de notebooks. Reutiliza
`cargar_panel()` de `mapa_folium.py` (mismo mecanismo de carga
parquet→csv), así que no duplica esa lógica.

**Qué cubre**: estructura y balance del panel, desbalance de la variable
`evento`, evolución temporal nacional (con el acumulado), estacionalidad,
distribución de `tasa_def`, ranking de departamentos, concentración espacial
(curva estilo Lorenz), un mapa estático de la deforestación acumulada por
celda, la relación entre bosque remanente y tasa de deforestación, y la
autocorrelación entre `area_def_ha` y sus rezagos — cerrando con un resumen
ejecutivo calculado en el momento (no copiado a mano), para que quede
actualizado si se corre contra un panel más reciente.

**Hallazgo a tener en cuenta al leerlo**: la sección 5 del notebook detecta y
explica que el **primer periodo del panel sobreestima sistemáticamente la
deforestación** de ese mes: mide el "stock" de todo lo que DIST-ALERT ya
tenía confirmado en la primera instantánea descargada de cada tile, no un
evento real concentrado en ese mes (ver METODOLOGIA.md §3.4, "Efecto de
inicio de ventana"). El notebook ya excluye ese periodo donde corresponde
(estacionalidad, resumen ejecutivo); cualquier análisis posterior sobre el
panel debería hacer lo mismo.

**Para regenerarlo con datos nuevos**: basta con reabrirlo y correr todas las
celdas (`Run All`), o desde la terminal:

```bash
jupyter nbconvert --to notebook --execute --inplace eda_deforestacion.ipynb
```

---

## 10. Estructura de `datos/`

| Carpeta | Contenido | La genera |
|---|---|---|
| `datos/grilla/` | CSV de la grilla de 5 km | `exportar_grilla.py` |
| `datos/hansen/` | Gránulos Hansen GFC (`.tif`) | `descargar_dist.py hansen` |
| `datos/dist/<tile>/` | COGs de DIST-ALERT por tile y mes (`.tif`) | `descargar_dist.py dist` |
| `datos/gfw/` | `lote_NNNN.json` — resultados crudos por lote de celdas | `descargar_gfw.py` |
| `datos/cache/` | `<tile>__idx.npy`, `<tile>__bosque_am{anio}_ud{umbral}.npy` (cachés por tile **y por combinación de parámetros** — el nombre incluye `anio_mascara`/`umbral_dosel` para que las cachés de los dos paneles nunca se pisen entre sí, ver METODOLOGIA.md decisión 5 revisada) | `zonal_local.py` (llamado directo o vía `descargar_gfw.py`) |
| `datos/crudo/` | `nacional.csv` (DIST-ALERT, 2023-presente) y `nacional_gfw.csv` (GFW, 2020-presente) — **dos archivos independientes, nunca fusionados** | `zonal_local.py` y `descargar_gfw.py`, cada uno el suyo |
| `datos/panel/` | `panel_deforestacion_colombia_dist_alert.*` y/o `panel_deforestacion_colombia_gfw.*` (formato largo), + `mapa_deforestacion.html` | `consolidar.py`, `mapa_folium.py` |
| `datos/logs/` | `inventario_dist.json` (+ `.completo`), `tiles_colombia.txt`, `fallidos_dist.txt`, `gfw_api_key.txt` | `descargar_dist.py`, `filtrar_tiles.py`, `configurar_gfw.py` |

Si algo se ve raro o hay que reconstruir desde cero, casi siempre basta con
borrar la carpeta correspondiente y volver a correr el paso que la genera —
**excepto** `datos/dist/` y `datos/hansen/`, que representan horas de
descarga y conviene conservar. Borrar `datos/cache/` es seguro y barato de
regenerar (se reconstruye solo en la siguiente corrida de `zonal_local.py`
o `descargar_gfw.py`), útil si se sospecha que una caché quedó corrupta o
desactualizada tras un cambio de parámetros — como el nombre de archivo ya
incluye `anio_mascara`/`umbral_dosel`, no hace falta borrar toda la carpeta
solo porque se corrió la otra fuente, basta con dejar que cada una use su
propia caché. Borrar `datos/gfw/` es igual de seguro: son solo cachés de
lotes ya descargados de la API de GFW, y `nacional_gfw.csv` es un archivo
aparte que no depende de que esas cachés sigan ahí una vez generado.

---

## 11. Cómo adaptar el pipeline

Situaciones típicas en que el director de tesis (o quien continúe el
trabajo) querría modificar el pipeline en vez de solo reproducirlo:

### Extender la ventana temporal (nuevos meses)

1. Cambiar `fecha_fin` en `config_local.py` (o `fecha_inicio`/`fecha_fin`
   ambas, si se quiere correr una ventana distinta).
2. Volver a correr desde el **Paso 3** (`inventario`) en adelante — no hace
   falta repetir `grilla` ni `hansen`. El caché de `datos/cache/` (índice de
   celda y máscara de bosque por tile) sigue siendo válido: no depende de la
   ventana temporal, solo de la geometría del tile y de Hansen.
3. `zonal_local.py` recalcula `meses(cfg)` con la nueva ventana y vuelve a
   procesar todas las instantáneas disponibles en `datos/dist/` — si ya
   había datos de meses previos descargados, no hace falta volver a
   descargarlos, `zonal_local.py` los reutiliza.

### Cambiar el umbral de confianza del evento

Modificar `estados_evento` en `config_local.py` (p. ej. incluir también los
estados `<50%` si se quiere una definición más laxa de disturbio). Solo hace
falta volver a correr desde el **Paso 7** (`zonal`) — no se necesita
re-descargar nada, porque los archivos `.tif` ya descargados tienen *todos*
los estados posibles; el filtro se aplica en memoria al procesar.

### Cambiar el tamaño de celda de la grilla

Modificar `grid_scale_m` en `config_local.py` y volver a correr **desde el
Paso 1** (`grilla`) — cambia la geometría de la grilla, así que todo lo que
depende de ella (índices de celda cacheados, cálculo zonal) debe rehacerse.
Conviene borrar `datos/cache/*.npy` explícitamente en este caso, porque el
nombre de archivo de la caché no incluye el tamaño de celda usado, y una
caché con el tamaño anterior sería silenciosamente incorrecta.

### Adaptar a otro país o región

1. Cambiar `bbox` en `config_local.py` al rectángulo del nuevo país/región.
2. Cambiar `DANE_MGN_DEPARTAMENTOS` en `exportar_grilla.py` por la fuente de
   límites administrativos del país nuevo, con la misma forma de salida
   (polígonos con un campo de nombre de región) — verifique primero su
   licencia con el mismo cuidado que se aplicó aquí (sección "Restricciones
   de licencia" en METODOLOGIA.md, si el uso sigue siendo comercial: NASA y
   CC BY sirven, GADM y Earth Engine gratuito no).
3. `filtrar_tiles.py` no necesita cambios: ya deriva los tiles MGRS
   necesarios directamente de la grilla exportada, sea cual sea el país.
4. Revisar si el nuevo país necesita gránulos Hansen distintos —
   `granulos_hansen()` ya calcula esto automáticamente a partir del `bbox`.

### Agregar una nueva variable derivada al panel

Se agrega como una columna nueva dentro de `derivar_variables()` en
`consolidar.py`, siguiendo el mismo patrón de las existentes (operar sobre
`df.groupby("cell_id", sort=False)`, ordenado cronológicamente). No requiere
cambios en ningún otro script, porque esta función es el único lugar que
transforma el panel balanceado en el panel final.

---

## 12. Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `descargar_dist.py inventario` reporta 0 tiles/gránulos | La cuenta Earthdata no ha aceptado el EULA de DIST-ALERT | Entrar a search.earthdata.nasa.gov, buscar "OPERA DIST-ALERT" y descargar un gránulo a mano una vez (sección 2.5) |
| `earthaccess.login()` falla o pide credenciales cada vez | El archivo `_netrc` no se está guardando o `.dodsrc` apunta a otra ruta | Revisar que `.dodsrc` exista en la raíz del proyecto y que las rutas ahí (`HTTP.NETRC`, `HTTP.COOKIEJAR`) sean válidas en la máquina actual — son rutas absolutas, hay que ajustarlas si cambia el nombre de usuario del sistema |
| `filtrar_tiles.py` dice que los conjuntos "no se cruzan en NADA" | Desajuste de formato entre el identificador de tile que produce `mgrs` y el que trae el inventario (con o sin prefijo `T`) | Revisar `_norm()` en `filtrar_tiles.py`; imprimir unos cuantos tiles de cada lado (`sorted(tiles_plan)[:5]` vs `sorted(necesarios)[:5]`) para comparar el formato a simple vista |
| `exportar_grilla.py` se detiene con "GRILLA NO ALINEADA AL ORIGEN" | No debería ocurrir con la versión actual (la alineación es por construcción, ver §5.2) — indicaría que alguien cambió `construir_grilla()` sin preservar esa propiedad | No ignorar este error — si se continúa de todas formas, el indexado de `zonal_local.py` asignaría píxeles a celdas incorrectas de forma silenciosa. Revisar que cada celda siga construyéndose como múltiplo entero exacto de `grid_scale_m` |
| `exportar_grilla.py` falla al descargar del DANE (timeout o error HTTP) | El servicio de ArcGIS del DANE puede estar temporalmente caído, o cambió de URL/item id | Reintentar en unos minutos; si persiste, buscar "Marco Geoestadístico Nacional Departamento" en el geoportal del DANE (geoportal.dane.gov.co) o en su ArcGIS Hub para encontrar la URL vigente del *Feature Service* y actualizar `DANE_MGN_DEPARTAMENTOS` en el script |
| `zonal_local.py` reporta "sin instantaneas; se salta" para muchos tiles | Ese tile no tiene ningún archivo en `datos/dist/<tile>/` | Verificar que el Paso 6 (descarga) terminó sin dejar ese tile en `fallidos_dist.txt`; si el tile nunca tuvo gránulos disponibles en CMR (nubosidad persistente), es esperado y no es un error |
| `pd.read_parquet` falla con `ImportError` | Falta `pyarrow` (o `fastparquet`) en el entorno, aunque esté listado en `requirements_local.txt` | `pip install pyarrow`, o simplemente usar el `.csv` equivalente — todos los scripts de este repositorio (`mapa_folium.py` incluido) ya caen automáticamente al CSV si el Parquet no se puede leer |
| La descarga nacional (Paso 6) es muy lenta | Límite de ancho de banda, o `hilos_descarga` muy bajo/alto para la red disponible | Ajustar `hilos_descarga` en `config_local.py` (más hilos no siempre es más rápido; LP DAAC puede limitar conexiones concurrentes por cuenta) |
| El mapa de `mapa_folium.py` pesa demasiado / tarda en abrir | Demasiados marcadores individuales en la capa de "Celdas con deforestación" | Bajar `--top-n` o subir `--umbral-ha` |
| `exportar_grilla.py` tarda varios minutos en el filtro espacial | Falta la simplificación del polígono nacional (ver §5.2) — el MGN del DANE sin simplificar tiene ~280 000 vértices | No debería pasar en la versión actual (ya incluye `pais.simplify(100, ...)`); si se quitó esa línea, restaurarla |
| `descargar_gfw.py` falla con `"Unsupported filter operator: in"` | El endpoint `/query/batch` de GFW no soporta `IN (...)` en el SQL | No debería pasar en la versión actual (`sql_lote()` ya usa `OR` encadenados, confirmado empíricamente); si se editó esa función para usar `IN`, revertir |
| `descargar_gfw.py` falla con `"extra fields not permitted"` en `feature_collection.features[i].id` | `geopandas`/`shapely` agregan un campo `"id"` a nivel de *feature* al exportar a GeoJSON, que la API de GFW rechaza | No debería pasar en la versión actual (`procesar_lote()` ya hace `feat.pop("id", None)` antes de enviar); si se quitó esa línea, restaurarla |
| `descargar_gfw.py` falla con `SystemExit` pidiendo la API key | Falta `datos/logs/gfw_api_key.txt` o la variable de entorno `GFW_API_KEY` | Correr `fuente_gfw/configurar_gfw.py` (sección 5.9) primero |
| `descargar_gfw.py` falla con `SystemExit` diciendo que no hay tiles de referencia | `datos/dist/` está vacío: nunca se corrió ni siquiera la descarga piloto de DIST-ALERT | Correr al menos el Paso 5 (piloto, `python main_local.py piloto --tile T18NXG`) antes de `descargar_gfw.py` para que el script deje de fallar — pero eso NO alcanza para el panel nacional completo, ver la fila siguiente |
| `descargar_gfw.py` corre sin error pero el panel GFW sale con muy pocas celdas (no ~44 600) | `datos/dist/` solo tiene el tile del piloto (u otro subconjunto parcial), no los 153 tiles del país — el script no avisa de esto, simplemente calcula bosque solo donde encuentra tiles | Terminar el Paso 6 (descarga nacional completa) antes de correr `descargar_gfw.py`; revisar en el log cuántos tiles procesó ("Calculando bosque base... sobre N tiles") |
| `main_local.py consolidar` falla con `argument --fuente is required` | `--fuente` no tiene default a propósito (ver sección 5.6) | Agregar `--fuente dist_alert` o `--fuente gfw` según cuál panel se quiera construir |
| `consolidar.py` falla con `FileNotFoundError` sobre `nacional.csv` o `nacional_gfw.csv` | Todavía no se corrió el paso previo de esa fuente (Paso 7 o Paso 7-GFW) | Para `--fuente dist_alert`: `python main_local.py zonal`. Para `--fuente gfw`: `python fuente_gfw/descargar_gfw.py` |
| Los dos paneles finales tienen números muy distintos para el mismo mes | Esperado: son dos metodologías de detección distintas (DIST-ALERT solo vs. cuatro sistemas integrados), no un error — ver METODOLOGIA.md §2.4 y decisión 15 | No promediarlos ni tratarlos como intercambiables; documentar cualquier comparación explícitamente si hace falta hacerla |

---

## 13. Glosario de código

| Término | Significado |
|---|---|
| **COG** | *Cloud-Optimized GeoTIFF*: el formato de archivo de DIST-ALERT, pensado para leerse por partes sin descargar el archivo completo |
| **CRS** | Sistema de referencia de coordenadas (p. ej. `EPSG:3116`, `EPSG:4326`) |
| **Gránulo** | "Un archivo/observación individual" en Hansen o en CMR — no es un tamaño espacial fijo |
| **Tile** | Una celda de la cuadrícula MGRS de 100×100 km; unidad de descarga de DIST-ALERT |
| **Panel ancho / largo** | *Ancho*: una fila por celda, una columna por periodo. *Largo*: una fila por celda-periodo. `zonal_local.py` produce ancho; `consolidar.py` lo pasa a largo |
| **Caché de tile** | Los archivos `.npy` en `datos/cache/`: resultado costoso de calcular (índice de celda, máscara de bosque) que no cambia entre corridas mientras no cambien la grilla o Hansen |
| **Reanudable** | Que se puede interrumpir (`Ctrl+C`) y relanzar sin perder el trabajo ya hecho — todas las descargas de este pipeline lo son |

Para términos conceptuales (qué es HLS, OPERA, MGRS, CMR, LP DAAC, etc.), ver
el glosario más completo en
[METODOLOGIA.md, sección 9](METODOLOGIA.md#9-glosario-técnico).

---

*Si un parámetro de `config_local.py` cambia, revise si esta guía y
[METODOLOGIA.md](METODOLOGIA.md) siguen describiendo correctamente el
comportamiento actual del pipeline — son documentación, no se actualizan
solas.*
