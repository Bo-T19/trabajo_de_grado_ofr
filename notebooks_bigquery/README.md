# Notebooks para BigQuery

Esta carpeta tiene todo el trabajo de grado convertido en 18 notebooks de Python para correr en **BigQuery
Studio**, en el proyecto de Google Cloud del Observatorio. Con ellos:

- **se descargan y se cargan en BigQuery** las tablas de deforestación (grilla, cuatro paneles y panel
  municipal), y se pueden **actualizar** cuando las fuentes publican datos nuevos;
- **el análisis exploratorio, la segmentación y los modelos** leen de BigQuery, tanto las tablas del
  Observatorio como las que cargan los notebooks, y muestran sus resultados en el propio notebook.

En BigQuery solo quedan las **9 tablas de datos** (sección 7).

Cada notebook trae todo su código adentro y explica en cada sección qué hace. **La celda 1 de cada uno ya
viene llena** para el proyecto del Observatorio (`prueba-ofr`), con las tablas en el dataset
`Cambio_Climatico`. Lo único que falta poner es la API key de Global Forest Watch en el 03 y el 18.

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
  tablas de BigQuery: uno escribe y el siguiente lee. Las que solo sirven para eso se borran al terminar la
  cadena. De ahí que el orden importe (sección 4).
- Los notebooks se pueden **programar** para que corran solos, por ejemplo cada mes.

---

## 2. Antes de empezar: lo que tiene que estar listo en Google Cloud

| Qué | Para qué |
|---|---|
| El proyecto del Observatorio, Prueba-OFR (id `prueba-ofr`), **con facturación** | Para prender la máquina de los notebooks y guardar las tablas sin que venzan |
| El dataset `Cambio_Climatico` | Ahí quedan las tablas de deforestación y los resultados |
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
2. Abre el notebook. La **celda 1** ya está llena (sección 5 de esta guía). En el 03 y el 18, pega la API key
   de GFW donde dice `<<LLENAR: ...>>`, entre comillas.
3. Conéctalo a un runtime (el que viene por defecto sirve) y corre todas las celdas.
4. La celda 2 instala lo que le falte a la máquina; la primera vez tarda uno o dos minutos.
5. La celda 3 se conecta a BigQuery y **se detiene con un mensaje claro si quedó algo sin llenar** en la celda 1
   (en la práctica, la API key de GFW).

Cada notebook empieza con un recuadro que dice qué lee, qué escribe, qué hay que cambiar y cuánto tarda.

---

## 4. Los notebooks, en orden

### Carga y actualización de las tablas de deforestación

| # | Notebook | Qué hace | Escribe | Cuándo volver a correrlo | Tarda |
|---|---|---|---|---|---|
| 01 | `01_carga_grilla_y_municipios` | La grilla de 5 km y el municipio de cada celda (DANE) | `GRILLA_CELDAS_5KM` | Una vez | 2 min |
| 02 | `02_carga_hansen` | Bosque base y pérdida anual de Hansen | `BOSQUE_BASE_HANSEN_CELDA_5KM`, `PERDIDA_COBERTURA_HANSEN_CELDA_5KM_ANIO` | Una vez al año, con cada versión de Hansen | 20 min |
| 03 | `03_carga_alertas_gfw` | Alertas de GFW por celda y mes | `ALERTAS_GFW_CELDA_5KM_MES` | Cada mes | 10-20 min |
| 04 | `04_carga_ideam_cambio` | Deforestación oficial del IDEAM por celda y periodo | `DEFORESTACION_IDEAM_CELDA_5KM_PERIODO` | Una vez al año, cuando el IDEAM publica | 10 min |
| 05 | `05_carga_ideam_dtd` | Detecciones tempranas del IDEAM por celda y trimestre | `DETECCIONES_TEMPRANAS_IDEAM_CELDA_5KM_TRIMESTRE` | Cada trimestre | 5 min |
| 06 | `06_carga_panel_municipal` | Cruza la deforestación con FINAGRO, EVA e ICA por municipio | `DEFORESTACION_CREDITO_PRODUCCION_MUNICIPIO_ANIO`, `ALERTAS_GFW_CREDITO_MUNICIPIO_MES`, `AREA_COSECHADA_EVA_MUNICIPIO_CULTIVO_ANIO` | Después de cualquier actualización | 5 min |

Las tablas van al dataset `DATASET_DEFORESTACION`.

El orden importa: el 01 va primero; el 02 antes del 03, el 04 y el 05 (les da el bosque base); y el 06 al
final.

### Análisis exploratorio

| # | Notebook | Qué hace | Escribe |
|---|---|---|---|
| 07 | `07_eda_estadisticas_descriptivas` | Estadísticas descriptivas de todas las tablas | — |
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

**En BigQuery solo quedan las tablas de datos** (las del 01 al 06). Los resultados de la segmentación, los
modelos y la comparación se ven en cada notebook y no se guardan. Como un notebook no puede llamar a otro, los de
modelos se pasan lo que necesitan por **tablas de paso** en `DATASET_RESULTADOS`: el 16 lee y borra las del 13, el
14 y el 15, y el 17 lee y borra las del 12 y el 16. Si la cadena se queda a medias, vencen solas a los 7 días.
Por eso, para volver a correr el 16 hay que correr antes el 13, el 14 y el 15; y para el 17, el 12 y el 16. Los
modelos entrenados tampoco se guardan: correr el notebook los reconstruye iguales, porque todo lo aleatorio
parte de una semilla fija.

### Demo de Landsat

| # | Notebook | Qué hace |
|---|---|---|
| 18 | `18_demo_landsat` | Replica, en una zona piloto de Caquetá, el cálculo de pérdida de bosque desde imágenes Landsat y lo compara con GLAD-L. Es entendimiento de los datos: no alimenta ninguna tabla ni ningún modelo |

---

## 5. Lo que trae la celda 1

Ya viene llena con estos valores. Solo hay que cambiarlos si las tablas se pasan a otro proyecto o dataset.

| Variable | Valor | Dónde va |
|---|---|---|
| `PROYECTO` | `prueba-ofr`: el id del proyecto Prueba-OFR | Todos |
| `DATASET_DEFORESTACION` | `Cambio_Climatico`: las tablas de deforestación | 01-09 y 12-17 |
| `DATASET_RESULTADOS` | `Cambio_Climatico`: donde van las tablas de paso entre los notebooks de modelos, que se borran al terminar. Para tenerlas aparte, se pone otro nombre en los notebooks 12 a 17, y el primero que escriba crea el dataset | 12-17 |
| `TABLA_FINAGRO` | `prueba-ofr.Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA` | 06, 07 |
| `TABLA_SFC414` | `prueba-ofr.Inclusion_Financiera.SFC414_DASH` | 07, 10 |
| `TABLA_EVA` | `prueba-ofr.Produccion.eva_full_enriquecido` | 06, 07, 11 |
| `TABLA_ICA` | `prueba-ofr.Produccion.ICA_pecuario` | 06, 07, 11 |
| `TABLA_MUNICIPIOS` | `prueba-ofr.Municipios.CODIGO` | 06, 08, 11 |
| `UBICACION` | `US`: donde se crean los datasets. Tiene que ser la misma de las tablas del Observatorio | Los que escriben |
| `RUTA_LLAVE_BIGQUERY` | Vacía. Solo se llena si el notebook se corre en un computador (sección 8) | Todos |
| `CARPETA_DESCARGAS` | Vacía: los archivos se bajan a una carpeta temporal | 02-05, 18 |
| `ANIO_INICIO`, `ANIO_PRUEBA` (13-17) y `ANIO_INICIO`, `ANIO_FIN` (12) | Los años de los modelos y de la segmentación (sección 6) | 12-17 |

La única que falta es `GFW_API_KEY`, la API key de Global Forest Watch, en el 03 y el 18.

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

En BigQuery quedan solo estas 9 tablas, en `DATASET_DEFORESTACION`:

| Tabla | Una fila es | Qué trae |
|---|---|---|
| `GRILLA_CELDAS_5KM` | una celda de 5 km | Identificador, centro, departamento y municipio |
| `BOSQUE_BASE_HANSEN_CELDA_5KM` | una celda | Bosque al empezar el análisis, según Hansen |
| `ALERTAS_GFW_CELDA_5KM_MES` | una celda en un mes | Alertas de GFW, bosque remanente, tasa, rezagos |
| `PERDIDA_COBERTURA_HANSEN_CELDA_5KM_ANIO` | una celda en un año | Pérdida de cobertura arbórea de Hansen |
| `DEFORESTACION_IDEAM_CELDA_5KM_PERIODO` | una celda en un periodo | Deforestación oficial y demás clases de cambio del IDEAM |
| `DETECCIONES_TEMPRANAS_IDEAM_CELDA_5KM_TRIMESTRE` | una celda en un trimestre | Detecciones tempranas del IDEAM |
| `DEFORESTACION_CREDITO_PRODUCCION_MUNICIPIO_ANIO` | un municipio en un año | Deforestación, crédito, cultivos, ganado y atributos |
| `ALERTAS_GFW_CREDITO_MUNICIPIO_MES` | un municipio en un mes | Alertas de GFW y crédito |
| `AREA_COSECHADA_EVA_MUNICIPIO_CULTIVO_ANIO` | un municipio, cultivo y año | Hectáreas cosechadas según la EVA |

Nada más queda en BigQuery: los notebooks 07 a 18 muestran sus resultados y no los guardan. Las tablas de paso
entre los notebooks de modelos se borran al terminar la cadena (sección 4).

Los límites de los municipios no se guardan en BigQuery, porque el Observatorio ya los tiene. El 01 los
descarga del DANE para asignar el municipio de cada celda, y el 09 y el 12 los vuelven a descargar para sus
mapas. Si quedó una tabla `MUNICIPIOS_LIMITES` de una versión anterior, el 01 la borra.

Los nombres de las tablas van en mayúscula. En BigQuery importan las mayúsculas, así que en SQL hay que
escribirlos igual (`DEFORESTACION_IDEAM_CELDA_5KM_PERIODO`, no `deforestacion_ideam_celda_5km_periodo`). Cada tabla y cada columna tienen una descripción, que
se ve en BigQuery en la pestaña de esquema. Dos cosas de cómo se guardan:

- **`orden_fila`.** Todas las tablas que escriben los notebooks tienen esta columna, con la posición de cada
  fila. BigQuery no guarda el orden de las filas, y algunos cálculos dependen de él (el muestreo del random
  forest, por ejemplo). Los notebooks leen las tablas ordenadas por esa columna; en SQL, `ORDER BY orden_fila`.

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
| 01 | `GRILLA_CELDAS_5KM` idéntica: las mismas 45.621 celdas, en el mismo orden, con el mismo departamento y municipio |
| 02 | `BOSQUE_BASE_HANSEN_CELDA_5KM` y `PERDIDA_COBERTURA_HANSEN_CELDA_5KM_ANIO` idénticos |
| 03 | `ALERTAS_GFW_CELDA_5KM_MES` idéntico (3.524.664 filas), con las respuestas de la API de agosto de 2026. Una consulta nueva a la API también funcionó |
| 04 | `DEFORESTACION_IDEAM_CELDA_5KM_PERIODO` idéntico |
| 05 | `DETECCIONES_TEMPRANAS_IDEAM_CELDA_5KM_TRIMESTRE` idéntico en los 25 trimestres del trabajo; el IDEAM ya publicó uno más, que entra solo |
| 06 | `DEFORESTACION_CREDITO_PRODUCCION_MUNICIPIO_ANIO` y `ALERTAS_GFW_CREDITO_MUNICIPIO_MES` idénticos, también con las tablas actuales del Observatorio |
| 07 a 11 | Corren de principio a fin sin errores |
| 12 a 17 | Los resultados de la segmentación, los tres modelos, la comparación y el cruce con riesgo salen idénticos a los de la corrida del 20 de noviembre de 2026 (los archivos de `modelos y clusters/resultados/`): métricas, predicciones, importancias, odds y la asignación de los 640 municipios a su segmento. Solo cambia la forma de algunas tablas: hiperparámetros guardados como texto, encabezados de dos niveles que quedan en uno, y la frase de reproducibilidad de la síntesis, que ya no habla de rutas ni de archivos |
| 18 | La demo corre de principio a fin, bajando de nuevo Hansen, el IDEAM, las escenas Landsat y GLAD-L |

Los notebooks 12 a 17 están adaptados de las versiones de "modelos y clusters/" del commit `8a1f855`
(20 de noviembre de 2026).

Con otros años (prueba con 2024 en lugar de 2025, entrenando con 2021-2023) la segmentación y toda la cadena
de modelos corren de principio a fin, así que los años funcionan como parámetro.

Después de pasar los nombres de las tablas a mayúscula y de dejar de guardar los límites municipales, se
volvieron a correr el 01, el 06 a 09, y el 12, 13, 16 y 17: `GRILLA_CELDAS_5KM` y las tablas municipales siguen
idénticas, y el resto corre sin errores.

Al dejar en BigQuery solo las tablas de datos se volvieron a correr el 16 y el 17, que son los que borran: el 16 guardó sus dos tablas de paso y borró las 22 del 13, el 14 y el 15, y el 17 borró las tres que usó.

No se pudo probar desde
fuera lo que solo existe dentro de BigQuery Studio: la instalación de paquetes en el runtime y la
programación de corridas.

---

## 10. Problemas comunes

| Lo que pasa | Por qué | Qué hacer |
|---|---|---|
| Conectar al entorno de ejecución tarda varios minutos | Google está prendiendo la máquina: pasa la primera vez y cada vez que se apagó por estar inactiva | Esperar unos minutos. Si pasa de un cuarto de hora, revisar en Colab Enterprise → Entornos de ejecución si la máquina quedó con error, borrarla y conectar de nuevo |
| La celda 3 dice "Falta llenar en la celda 1: GFW_API_KEY" | No se pegó la API key de GFW (03 y 18) | Pegarla en la celda 1 |
| El 03 muestra errores 404 mientras espera un lote | La API de GFW a veces no encuentra un lote recién pedido | Nada: el notebook lo vuelve a intentar solo |
| "Aviso: la lectura rápida de BigQuery no está disponible" | Falta el rol *BigQuery Read Session User* | Nada: el notebook sigue con la lectura normal, más lenta en tablas grandes. Para que sea más rápido, pedir ese rol |
| El 03 dice que GFW rechazó la API key | La llave venció (duran un año) | Sacar una nueva con el anexo del notebook 03 |
| El 03 dice que fallaron algunos lotes | La API de GFW no respondió a tiempo | Volver a correr la celda: los lotes que llegaron no se vuelven a pedir. El notebook nunca rellena con ceros un lote que falló |
| Una descarga del IDEAM se queda esperando | El servidor del IDEAM está lento o caído | Volver a correr la celda más tarde |
| El 04 dice que falta el nombre de un periodo | Se agregó un periodo a `IDEAM_PERIODOS` sin su archivo | Agregar el nombre del archivo a `CAPAS_IDEAM` |
| El 14 o el 15 dicen que la muestra no coincide con la del gradient boosting | Se corrieron con años o datos distintos | Correr el 13 y luego el 14 y el 15 con los mismos años |
| El 16 o el 17 dicen que faltan tablas | No se han corrido los notebooks anteriores, o ya se borraron: el 16 y el 17 borran las tablas de paso al terminar | Correr de nuevo los que nombra el mensaje y después el 16 o el 17 |
