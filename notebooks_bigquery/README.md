# Notebooks para BigQuery

Esta carpeta tiene todo el trabajo de grado convertido en 18 notebooks de Python para correr en **BigQuery
Studio**, en el proyecto de Google Cloud del Observatorio. Con ellos:

- **se descargan y se cargan en BigQuery** las tablas de deforestación (grilla, cuatro paneles y panel
  municipal), y se pueden **actualizar** cuando las fuentes publican datos nuevos;
- **el análisis exploratorio, la segmentación y los modelos** leen de BigQuery, tanto las tablas del
  Observatorio como las que cargan los notebooks, y dejan sus resultados en tablas.

Cada notebook trae todo su código adentro y explica en cada sección qué hace. **Lo único que hay que
cambiar en cualquiera de ellos es la celda 1.**

---

## 1. Cómo funcionan los notebooks de BigQuery

- En la consola de BigQuery (BigQuery Studio) se sube un archivo `.ipynb` o se crea uno nuevo. Se usa como
  Jupyter o Colab: celdas de código que se corren una por una o todas seguidas.
- Para correr, el notebook se conecta a una **máquina virtual** (un *runtime*) que Google prende. Esa máquina
  se cobra por hora mientras está prendida, así que **hace falta un proyecto con facturación activa**: un
  proyecto en modo Sandbox no sirve, y además en Sandbox las tablas se borran solas a los 60 días.
- Adentro, Python lee y escribe en BigQuery con la cuenta de quien lo corre. **No hace falta ninguna llave de
  cuenta de servicio.**
- Los archivos que se bajan a la máquina (los mapas de Hansen, las capas del IDEAM) son de paso: todo lo que
  importa queda en tablas.
- **Un notebook no puede ejecutar a otro.** Por eso cada uno es autocontenido y se pasan la información solo por
  tablas de BigQuery: uno escribe y el siguiente lee. De ahí que el orden importe (sección 4).
- Los notebooks se pueden **programar** para que corran solos, por ejemplo cada mes.

---

## 2. Antes de empezar: lo que tiene que estar listo en Google Cloud

| Qué | Para qué |
|---|---|
| Un proyecto de Google Cloud **con facturación** | Para prender la máquina de los notebooks y guardar las tablas sin que venzan |
| Dos datasets (o uno solo para todo): uno para las tablas de deforestación y otro para los resultados | Los notebooks los crean solos si no existen; basta con decidir el nombre |
| Permisos para quien corre los notebooks | Ver la lista de abajo |
| Una **API key de Global Forest Watch** | Solo para los notebooks 03 y 18. Es gratuita y vence al año. El anexo del notebook 03 explica cómo sacarla |

Permisos que necesita la cuenta que corre los notebooks:

- **Escribir y consultar en BigQuery:** "Editor de datos de BigQuery" (*BigQuery Data Editor*) sobre los
  datasets donde se escribe, y "Usuario de trabajos de BigQuery" (*BigQuery Job User*) en el proyecto.
- **Leer las tablas del Observatorio:** "Visualizador de datos de BigQuery" (*BigQuery Data Viewer*) sobre
  ellas.
- **Usar los notebooks:** los roles de BigQuery Studio y Colab Enterprise para crear notebooks y runtimes.
- **Recomendado:** "Usuario de sesiones de lectura de BigQuery" (*BigQuery Read Session User*). Sin ese rol los
  notebooks funcionan igual, pero leen las tablas grandes más despacio, y lo avisan.

Para correrlos programados, la cuenta de servicio con que se programan necesita los mismos permisos.

---

## 3. Cómo subir y correr un notebook

1. En BigQuery Studio, sube los archivos `.ipynb` de esta carpeta. En el panel del explorador, junto a
   "Notebooks", está la opción para subir uno desde el computador (el nombre exacto del menú puede cambiar con
   las versiones de la consola).
2. Abre el notebook y llena la **celda 1** (sección 5 de esta guía). Reemplaza cada `<<LLENAR: ...>>` por su
   valor, entre comillas.
3. Conéctalo a un runtime (el que viene por defecto sirve) y corre todas las celdas.
4. La celda 2 instala lo que le falte a la máquina; la primera vez tarda uno o dos minutos.
5. La celda 3 se conecta a BigQuery y **se detiene con un mensaje claro si quedó algo sin llenar** en la celda 1.

Cada notebook empieza con un recuadro que dice qué lee, qué escribe, qué hay que cambiar y cuánto tarda.

---

## 4. Los notebooks, en orden

### Carga y actualización de las tablas de deforestación

| # | Notebook | Qué hace | Escribe | Cuándo volver a correrlo | Tarda |
|---|---|---|---|---|---|
| 01 | `01_carga_grilla_y_municipios` | La grilla de 5 km y el municipio de cada celda (DANE) | `grilla`, `municipios_limites` | Una vez | 2 min |
| 02 | `02_carga_hansen` | Bosque base y pérdida anual de Hansen | `bosque_base`, `panel_hansen` | Una vez al año, con cada versión de Hansen | 20 min |
| 03 | `03_carga_alertas_gfw` | Alertas de GFW por celda y mes | `panel_deforestacion_colombia` | Cada mes | 10-20 min |
| 04 | `04_carga_ideam_cambio` | Deforestación oficial del IDEAM por celda y periodo | `panel_ideam` | Una vez al año, cuando el IDEAM publica | 10 min |
| 05 | `05_carga_ideam_dtd` | Detecciones tempranas del IDEAM por celda y trimestre | `panel_dtd` | Cada trimestre | 5 min |
| 06 | `06_carga_panel_municipal` | Cruza la deforestación con FINAGRO, EVA e ICA por municipio | `municipio_anio`, `municipio_mes`, `municipio_cultivo_anio` | Después de cualquier actualización | 5 min |

Las tablas van al dataset `DATASET_DEFORESTACION`. Cada carga deja además una fila en la tabla
`registro_cargas`: qué tabla, cuántas filas, de qué fuente, con qué parámetros y cuándo.

El orden importa: el 01 va primero; el 02 antes del 03, el 04 y el 05 (les da el bosque base); y el 06 al
final.

### Análisis exploratorio

| # | Notebook | Qué hace | Escribe |
|---|---|---|---|
| 07 | `07_eda_estadisticas_descriptivas` | Estadísticas descriptivas de todas las tablas | `estadisticas_descriptivas` |
| 08 | `08_eda_catalogo_paneles` | Describe y compara los cuatro paneles, con un mapa de las fuentes | — |
| 09 | `09_eda_panel_municipal` | Concentración, correlaciones y mapa del panel municipal | — |
| 10 | `10_eda_sfc414` | Exploración de la tabla SFC 414 | — |
| 11 | `11_eda_eva_ica` | Exploración de la EVA y del ICA | — |

### Segmentación y modelos

| # | Notebook | Qué hace | Necesita antes |
|---|---|---|---|
| 12 | `12_modelos_segmentacion` | Ocho segmentos de municipios rurales con K-means | 06 |
| 13 | `13_modelos_gradient_boosting` | Modelo principal: ¿deforesta? y ¿cuánto? | 06 |
| 14 | `14_modelos_random_forest` | Bosque aleatorio, con el mismo diseño | 13 |
| 15 | `15_modelos_regresion_logistica` | Regresión logística, la referencia interpretable | 13 |
| 16 | `16_modelos_comparacion` | Compara los tres modelos | 13, 14 y 15 |
| 17 | `17_modelos_segmentos_y_riesgo` | Cruza los segmentos con el riesgo | 12 y 16 |

Los resultados van al dataset `DATASET_RESULTADOS`, cada uno en una tabla con el prefijo de su notebook
(`gradient_boosting_metricas`, `segmentacion_municipios`, …). Los modelos entrenados no se guardan, porque
BigQuery guarda tablas y no archivos; correr el notebook los reconstruye iguales, porque todo lo aleatorio
parte de una semilla fija.

### Demo de Landsat

| # | Notebook | Qué hace |
|---|---|---|
| 18 | `18_demo_landsat` | Replica, en una zona piloto de Caquetá, el cálculo de pérdida de bosque desde imágenes Landsat y lo compara con GLAD-L. Es entendimiento de los datos: no alimenta ninguna tabla ni ningún modelo |

---

## 5. Qué llenar en la celda 1

| Variable | Qué poner | Dónde va |
|---|---|---|
| `PROYECTO` | El id del proyecto de Google Cloud. Aparece arriba a la izquierda en la consola | Todos |
| `DATASET_DEFORESTACION` | El dataset de las tablas de deforestación, p. ej. `"deforestacion"` | 01-09 y 12-17 |
| `DATASET_RESULTADOS` | El dataset de los resultados, p. ej. `"deforestacion_resultados"`. Puede ser el mismo de arriba | 07 y 12-18 |
| `TABLA_FINAGRO` | Tabla de desembolsos de FINAGRO. En el trabajo: `prueba-ofr.Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA` | 06, 07 |
| `TABLA_SFC414` | Tabla del formato 414. En el trabajo: `prueba-ofr.Inclusion_Financiera.SFC414_DASH` | 07, 10 |
| `TABLA_EVA` | EVA. En el trabajo: `prueba-ofr.Produccion.eva_full_enriquecido` | 06, 07, 11 |
| `TABLA_ICA` | Inventario pecuario del ICA. En el trabajo: `prueba-ofr.Produccion.ICA_pecuario` | 06, 07, 11 |
| `TABLA_MUNICIPIOS` | Catálogo de municipios. En el trabajo: `prueba-ofr.Municipios.CODIGO` | 06, 08, 11 |
| `GFW_API_KEY` | La API key de Global Forest Watch | 03, 18 |

Ya vienen llenas y normalmente no se tocan:

| Variable | Qué es |
|---|---|
| `UBICACION` | Dónde se crean los datasets. Viene en `"US"`, la de las tablas del Observatorio; tiene que ser la misma de ellas |
| `RUTA_LLAVE_BIGQUERY` | Vacía en BigQuery. Solo se llena si el notebook se corre en un computador (sección 8) |
| `CARPETA_DESCARGAS` | Vacía: los archivos se bajan a una carpeta temporal |
| `ANIO_INICIO`, `ANIO_PRUEBA` (13-17) y `ANIO_INICIO`, `ANIO_FIN` (12) | Los años de los modelos y de la segmentación (sección 6) |

> **Sobre la llave de GFW.** Los notebooks 03 y 18 quedan guardados en BigQuery con la llave adentro. No los
> compartas fuera del equipo. En el repositorio de GitHub, que es público, van siempre con el
> `<<LLENAR: ...>>`.

---

## 6. Cómo actualizar

| Fuente | Cada cuánto publica | Qué hacer |
|---|---|---|
| Alertas de GFW | Continuamente | Correr el 03 cada mes. No hay que cambiar nada: por defecto llega hasta el último mes completo. Cada corrida vuelve a bajar todo el periodo, porque GFW confirma alertas con semanas de retraso |
| Detecciones tempranas del IDEAM | Cada trimestre | Correr el 05. Los trimestres nuevos aparecen solos; cuando empieza un año, se agrega a `DTD_ANIOS` |
| Capas de cambio del IDEAM | Una vez al año | En el 04, agregar el periodo nuevo a `IDEAM_PERIODOS` y su nombre de archivo a `CAPAS_IDEAM` (el notebook dice dónde buscarlo) |
| Hansen | Una vez al año | En el 02, cambiar `HANSEN_VERSION` (p. ej. a `GFC-2026-v1.14`) y volver a correr el 02 y luego el 03, el 04 y el 05 |
| Tablas del Observatorio | Las actualiza el Observatorio | Volver a correr el 06 |

Después de actualizar cualquier fuente, se vuelve a correr el **06** y, si se quiere, el análisis y los
modelos.

**Los años de los modelos.** Por defecto, los notebooks 12 a 17 usan los del trabajo de grado: perfil y
entrenamiento de 2021 a 2024, prueba con 2025. Para mover los modelos hacia adelante (por ejemplo, probar con
2026 cuando el panel municipal tenga ese año completo), se cambia `ANIO_PRUEBA` en los notebooks 13 a 17 y
`ANIO_FIN` en el 12, todos al mismo valor. Las tablas, gráficas y frases que calculan los notebooks se
actualizan solas; los textos escritos a mano describen la corrida del trabajo de grado y no cambian.

En el 06, `ANIO_FIN` y `MES_FIN` dicen hasta dónde llega el panel municipal; se mueven cuando las fuentes
tengan el año o el mes completo.

**Programar las corridas.** En BigQuery Studio, un notebook se puede programar desde su barra de herramientas.
Como un notebook no llama a otro, se programa cada uno por separado, dejando tiempo entre ellos: por ejemplo,
el 03 el día 1 de cada mes y el 06 el día 2.

---

## 7. Las tablas que quedan

En `DATASET_DEFORESTACION`:

| Tabla | Una fila es | Qué trae |
|---|---|---|
| `grilla` | una celda de 5 km | Identificador, centro, departamento y municipio |
| `municipios_limites` | un municipio | Su polígono (texto WKT), para los mapas |
| `bosque_base` | una celda | Bosque al empezar el análisis, según Hansen |
| `panel_deforestacion_colombia` | una celda en un mes | Alertas de GFW, bosque remanente, tasa, rezagos |
| `panel_hansen` | una celda en un año | Pérdida de cobertura arbórea de Hansen |
| `panel_ideam` | una celda en un periodo | Deforestación oficial y demás clases de cambio del IDEAM |
| `panel_dtd` | una celda en un trimestre | Detecciones tempranas del IDEAM |
| `municipio_anio` | un municipio en un año | Deforestación, crédito, cultivos, ganado y atributos |
| `municipio_mes` | un municipio en un mes | Alertas de GFW y crédito |
| `municipio_cultivo_anio` | un municipio, cultivo y año | Hectáreas cosechadas según la EVA |
| `registro_cargas` | una carga | Qué se cargó, de dónde, con qué parámetros y cuándo |

En `DATASET_RESULTADOS`, las salidas de los notebooks 07 y 12 a 18, con el prefijo de cada uno.

Cada tabla y cada columna tienen una descripción, que se ve en BigQuery en la pestaña de esquema. Dos cosas
de cómo se guardan:

- **`orden_fila`.** Todas las tablas que escriben los notebooks tienen esta columna, con la posición de cada
  fila. BigQuery no guarda el orden de las filas, y algunos cálculos dependen de él (el muestreo del random
  forest, por ejemplo). Los notebooks leen las tablas ordenadas por esa columna; en SQL, `ORDER BY orden_fila`.
- **Nombres de columna.** Las tablas de resultados tenían columnas con tildes, espacios o paréntesis
  ("deforestación IDEAM 2021-2025 (ha)"). En BigQuery se guardan con un nombre simple
  (`deforestacion_ideam_2021_2025_ha`) y el nombre original queda en la descripción de la columna; los
  notebooks lo recuperan al leer.

---

## 8. Correr un notebook en un computador

Los notebooks también corren fuera de BigQuery, con el entorno del repositorio (`requirements_local.txt`):

1. En la celda 1, `RUTA_LLAVE_BIGQUERY` = la ruta al `.json` de una cuenta de servicio con acceso a las tablas.
2. La celda 2 (instalar paquetes) se puede saltar.
3. Si ya tienes los archivos de Hansen, el IDEAM o las detecciones tempranas en tu computador, apunta
   `CARPETA_DESCARGAS` a esa carpeta y no se vuelven a bajar.

---

## 9. Qué se comprobó

Los notebooks se corrieron contra un dataset de prueba en BigQuery y sus tablas se compararon con las del
trabajo de grado:

| Notebook | Resultado |
|---|---|
| 01 | `grilla` idéntica: las mismas 45.621 celdas, en el mismo orden, con el mismo departamento y municipio |
| 02 | `bosque_base` y `panel_hansen` idénticos |
| 03 | `panel_deforestacion_colombia` idéntico (3.524.664 filas), con las respuestas de la API de agosto de 2026. Una consulta nueva a la API también funcionó |
| 04 | `panel_ideam` idéntico |
| 05 | `panel_dtd` idéntico en los 25 trimestres del trabajo; el IDEAM ya publicó uno más, que entra solo |
| 06 | `municipio_anio` y `municipio_mes` idénticos, también con las tablas actuales del Observatorio |
| 07 a 11 | Corren de principio a fin sin errores |
| 12 | Segmentación idéntica: los 640 municipios quedan en el mismo segmento |
| 13 | Métricas, hiperparámetros, importancias y lista de riesgo idénticos a los del trabajo |
| 14 a 17 | Corren de principio a fin sin errores |
| 18 | La demo corre de principio a fin, bajando de nuevo Hansen, el IDEAM, las escenas Landsat y GLAD-L |

Sobre el 14 y el 15: los archivos de resultados guardados en el repositorio (`modelos y clusters/resultados/`)
son de una corrida anterior y no coinciden del todo con lo que dan hoy los notebooks originales. Se corrieron
los dos originales de nuevo y los notebooks 14 y 15 dan **exactamente lo mismo** que ellos: métricas,
predicciones, importancias y lista de riesgo. Las diferencias con los archivos guardados son pequeñas (por
ejemplo, en la regresión logística con departamentos por fuera, exactitud balanceada de 0,8248 frente a 0,8242;
en el random forest, AUC de 0,92950 frente a 0,92947).

Con otros años (prueba con 2024 en lugar de 2025, entrenando con 2021-2023) la segmentación y toda la cadena
de modelos (12 a 17) corren de principio a fin, así que los años funcionan como parámetro. No se pudo probar
desde fuera lo que solo existe dentro de BigQuery Studio: la instalación de paquetes en el runtime y la
programación de corridas.

Los notebooks de modelos de esta carpeta se adaptaron de las versiones de "modelos y clusters/" anteriores al
commit `8a1f855` (20 de noviembre de 2026), que trajo versiones nuevas de esos notebooks. Esas versiones nuevas
todavía no están pasadas a BigQuery.

---

## 10. Problemas comunes

| Lo que pasa | Por qué | Qué hacer |
|---|---|---|
| La celda 3 dice "Falta llenar en la celda 1: …" | Quedó algún `<<LLENAR ...>>` | Llenar las variables que nombra |
| "Aviso: la lectura rápida de BigQuery no está disponible" | Falta el rol *BigQuery Read Session User* | Nada: el notebook sigue con la lectura normal, más lenta en tablas grandes. Para que sea más rápido, pedir ese rol |
| El 03 dice que GFW rechazó la API key | La llave venció (duran un año) | Sacar una nueva con el anexo del notebook 03 |
| El 03 dice que fallaron algunos lotes | La API de GFW no respondió a tiempo | Volver a correr la celda: los lotes que llegaron no se vuelven a pedir. El notebook nunca rellena con ceros un lote que falló |
| Una descarga del IDEAM se queda esperando | El servidor del IDEAM está lento o caído | Volver a correr la celda más tarde |
| El 04 dice que falta el nombre de un periodo | Se agregó un periodo a `IDEAM_PERIODOS` sin su archivo | Agregar el nombre del archivo a `CAPAS_IDEAM` |
| El 14 o el 15 dicen que la muestra no coincide con la del gradient boosting | Se corrieron con años o datos distintos | Correr el 13 y luego el 14 y el 15 con los mismos años |
| El 16 o el 17 dicen que faltan tablas | No se han corrido los notebooks anteriores | Correr los que nombra el mensaje |
