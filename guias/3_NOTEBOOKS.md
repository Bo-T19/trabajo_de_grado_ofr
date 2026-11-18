# 3. Notebooks: análisis exploratorio, segmentación y modelos

Cómo correr los notebooks del trabajo y qué produce cada uno. Antes hay que
tener los datos listos, siguiendo
[`2_DESCARGA_DE_DATOS.md`](2_DESCARGA_DE_DATOS.md) hasta el Paso 14: los
notebooks leen las cuatro tablas de `datos/panel/` y el panel municipal de
`datos/analisis/`.

Los notebooks están guardados con las salidas de la corrida de referencia,
así que también se pueden leer sin correrlos.

## Índice

1. [Cómo se corren](#1-cómo-se-corren)
2. [Análisis exploratorio](#2-análisis-exploratorio-procesamiento-y-eda)
3. [Segmentación y modelos](#3-segmentación-y-modelos-modelos-y-clusters)
4. [Resultados esperados](#4-resultados-esperados)
5. [Problemas comunes](#5-problemas-comunes)

---

## 1. Cómo se corren

Hay dos formas:

- **Celda por celda, en Jupyter.** Se abre con `jupyter lab` desde la raíz
  del repositorio y se elige el notebook.
- **Completo, desde la terminal**, con `nbconvert`:

```bash
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 "modelos y clusters/segmentacion_municipios.ipynb"
```

En ese comando:

- la ruta va entre comillas porque los nombres de las carpetas tienen
  espacios;
- `--inplace` reemplaza las salidas guardadas en el notebook por las de la
  nueva corrida;
- `timeout=-1` evita que `nbconvert` corte una celda larga.

Todos los notebooks buscan solos la raíz del repositorio, así que las rutas
`datos/...` funcionan sin importar desde dónde se abran.

---

## 2. Análisis exploratorio (`procesamiento y eda/`)

Además de `panel_municipal_armado.ipynb`, que es parte de la descarga (Paso
14), la carpeta tiene siete notebooks. Son exploratorios: los notebooks de
`modelos y clusters/` no usan nada de lo que producen. Se pueden correr en
cualquier orden, y solo los que interesen.

| Notebook | Qué hace | Necesita | Guarda |
|---|---|---|---|
| `panel_municipal_analisis.ipynb` | Analiza el panel municipal en los municipios rurales | El panel municipal (Paso 14) y `datos/limites/` (Paso 4) | Nada: solo muestra resultados |
| `estadisticas_descriptivas.ipynb` | Estadística descriptiva de nueve tablas | Las cuatro tablas (Pasos 1-10) y `datos/profesor/` (Paso 14) | Figuras en `documento/figuras/` y `documento/tablas/estadisticas_descriptivas.xlsx` |
| `catalogo_paneles.ipynb` | Catálogo y análisis exploratorio de las cuatro tablas propias | Las cuatro tablas; la llave de BigQuery para la sección 6 del notebook | `datos/panel/mapa_fuentes.html` |
| `exploratorio_sfc414.ipynb` | Análisis exploratorio de SFC 414 | `datos/profesor/sfc414/` (Paso 14) | Nada |
| `exploratorio_eva_ica_pecuario.ipynb` | Análisis exploratorio de EVA e ICA pecuario | La llave de BigQuery: descarga sus tablas si no están en `datos/profesor/` | Nada |
| `consultar_tablas_profesor.ipynb` | Primeras filas de FINAGRO, SFC 414 y municipios, y exploración de FINAGRO | La llave de BigQuery y `datos/profesor/finagro/` (Paso 14) | Nada |
| `investigacion_municipio_27493.ipynb` | Por qué el municipio 27493 no está en el catálogo de municipios | La llave de BigQuery | Nada |

Los dos principales se corren así:

```bash
jupyter nbconvert --to notebook --execute --inplace "procesamiento y eda/panel_municipal_analisis.ipynb"
jupyter nbconvert --to notebook --execute --inplace "procesamiento y eda/estadisticas_descriptivas.ipynb"
```

Los demás se corren igual, cambiando el nombre del notebook.

### Panel municipal: análisis (`panel_municipal_analisis.ipynb`)

Trabaja solo con los **642 municipios rurales y rurales dispersos** (según la
clasificación más reciente de la tabla de municipios), en 2021-2025, sin
filtro de bosque. Tiene una sección de datos y filtros y cinco análisis:

1. **Índice 2021 = 100** de la deforestación, el crédito, el ganado y los
   cultivos.
2. **Concentración**: curvas de Lorenz, Gini, regla 80-20 y Pareto de la
   deforestación.
3. **Los 10 municipios que más deforestan**: sus cultivos (área cosechada
   por grupo y por cultivo) y su ganadería.
4. **Correlaciones de Spearman**, con una fila por municipio (promedio
   2021-2025) y las variables en intensidad: cada variable frente a la
   deforestación, con intervalos por bootstrap (4.1); la matriz entre todas
   las variables (4.2), y las mismas correlaciones dentro de cinco grupos de
   municipios de tamaño parecido (quintiles de área), con una revisión con 3
   y 10 grupos (4.3). La deforestación se mide como tasa y como hectáreas
   por 100 km².
5. **Mapa** de la deforestación de todos los municipios del país, con los
   límites del MGN 2025.

El notebook solo explica qué se hace y cómo leer cada gráfico; la
interpretación de los resultados va en el documento del trabajo. Dos
advertencias para leerlo: los intervalos por bootstrap remuestrean
municipios y son optimistas, porque los municipios vecinos se parecen; y en
2025 el ICA reasigna bovinos entre municipios vecinos (más de 100 municipios
cambian más de 50 % frente a 2024), así que las cifras municipales de ganado
de ese año deben leerse con cuidado.

### Estadísticas descriptivas (`estadisticas_descriptivas.ipynb`)

Calcula, para las variables numéricas principales de nueve tablas (la grilla,
los cuatro paneles, FINAGRO, SFC 414, EVA e ICA pecuario), las estadísticas
de `summary()` y `psych::describe()` de R: n, faltantes, % de ceros, media,
desviación estándar, mínimo, cuartiles, máximo, asimetría y curtosis. Cada
tabla se describe tal como está, sin limpiar; por eso aparecen, por ejemplo,
las tasas negativas de FINAGRO. Los montos van en millones de pesos.

Exporta la tabla completa y una por grupo a `documento/figuras/` (PNG) y los
valores sin redondear a `documento/tablas/estadisticas_descriptivas.xlsx`. La
última sección toma una muestra de tres variables y comprueba con R que las
cifras coinciden; en la corrida de referencia, la diferencia máxima fue de
2 × 10⁻¹¹.

### Catálogo de las cuatro tablas (`catalogo_paneles.ipynb`)

Describe las cuatro tablas propias de deforestación (GFW, Hansen, IDEAM y
detecciones tempranas) leyendo las cifras de los propios archivos, así que
se mantiene al día. Tiene:

- dimensiones, columnas, tipos y una muestra de cada tabla;
- un mapa en folium que compara el patrón espacial de las cuatro fuentes;
- la **distribución** de cada fuente: % de ceros, histogramas y dispersión
  por departamento. El sesgo que se ve es propio del fenómeno, no un
  problema de calidad;
- el **cruce con el catálogo de municipios** del Observatorio: 1.113 de
  1.114 municipios cruzan bien tratando `cod_dane` como texto de 5
  caracteres con cero a la izquierda. El único que no cruza es el 27493;
- la **correlación entre fuentes**, en el tiempo y en el espacio. GFW, Hansen
  e IDEAM concuerdan; las detecciones tempranas concuerdan en el espacio,
  pero no en el tiempo, porque dependen del esfuerzo de monitoreo;
- la **calidad de datos**: los faltantes son estructurales, no hay
  duplicados, y los valores extremos se concentran en los mismos municipios
  en las cuatro fuentes. Es el arco de deforestación, no un error.

### Tablas del Observatorio

- **`exploratorio_sfc414.ipynb`**: análisis exploratorio de SFC 414. Esta
  tabla no entra en el panel municipal porque su serie empieza en
  septiembre de 2023.
- **`exploratorio_eva_ica_pecuario.ipynb`**: describe, explora y revisa la
  calidad de EVA e ICA pecuario antes de usarlas. Incluye:
  - un diccionario de sus variables;
  - el cruce de `cod_dane` con el catálogo de municipios;
  - diagnósticos propios de estas tablas: valores negativos, área
    cosechada mayor que la sembrada, y totales de bovinos que no cuadran
    con la suma por edad y sexo.

  Sus secciones 4 a 6 no están ejecutadas en la versión guardada (5 de sus
  19 celdas de código), así que no muestran resultados hasta que se corra
  el notebook completo.
- **`consultar_tablas_profesor.ipynb`**: muestra las primeras filas de
  FINAGRO, SFC 414 y el catálogo de municipios sin ejecutar SQL (no genera
  costo en BigQuery), y explora FINAGRO a partir de la copia en
  `datos/profesor/`.
- **`investigacion_municipio_27493.ipynb`**: el 27493 (Nuevo Belén de
  Bajirá, Chocó) es el municipio más nuevo de Colombia. Tiene datos en EVA,
  FINAGRO y SFC 414, pero no está en el catálogo de municipios del
  Observatorio, así que le faltan la región, la ruralidad y el indicador
  PDET. Se trata como un faltante documentado, sin imputar.

---

## 3. Segmentación y modelos (`modelos y clusters/`)

Seis notebooks oficiales. Necesitan el panel municipal (Paso 14 de
`2_DESCARGA_DE_DATOS.md`) y no dependen de los notebooks exploratorios de la
sección 2.

### Orden y comandos

```bash
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 "modelos y clusters/segmentacion_municipios.ipynb"
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 "modelos y clusters/gradient_boosting.ipynb"
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 "modelos y clusters/random_forest.ipynb"
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 "modelos y clusters/regresion_logistica.ipynb"
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 "modelos y clusters/comparacion_modelos.ipynb"
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 "modelos y clusters/segmentos_y_riesgo.ipynb"
```

Todos necesitan `datos/analisis/municipio_anio.parquet` (Paso 14 de
`2_DESCARGA_DE_DATOS.md`) y guardan sus salidas en
`modelos y clusters/resultados/`, con el nombre del notebook como prefijo.
Qué lee y qué guarda cada uno:

| # | Notebook | Lee, además del panel | Guarda |
|---|---|---|---|
| 1 | `segmentacion_municipios.ipynb` | `datos/limites/` (Paso 4 de `2_DESCARGA_DE_DATOS.md`), para el mapa | `segmentacion_municipios_clusters.xlsx` (un municipio por fila, con su cluster) y `documento/tablas/segmentacion_municipios.xlsx` (el detalle) |
| 2 | `gradient_boosting.ipynb` | — | Los dos modelos entrenados (`.joblib`), métricas, hiperparámetros, importancia por permutación y la lista de municipios de mayor riesgo |
| 3 | `random_forest.ipynb` | Las celdas de preparación de datos de `gradient_boosting.ipynb` | Lo mismo que el 2, más las predicciones de 2025 y de departamentos fuera, la importancia por bloques y la síntesis por objetivo |
| 4 | `regresion_logistica.ipynb` | Las celdas de preparación de datos de `gradient_boosting.ipynb` | Lo mismo que el 3, más coeficientes con errores robustos, efectos marginales, pruebas de Wald y el VIF |
| 5 | `comparacion_modelos.ipynb` | Las salidas de 2, 3 y 4, y las celdas de preparación de `gradient_boosting.ipynb` | Métricas comparadas, probabilidades de 2025 de los tres modelos y la síntesis por objetivo |
| 6 | `segmentos_y_riesgo.ipynb` | `documento/tablas/segmentacion_municipios.xlsx` (de 1) y las probabilidades y la síntesis de 5 | El cruce de segmentos y riesgo, y tres figuras en `documento/figuras/` |

Sobre el orden:

- **1 a 4 se pueden correr en cualquier orden entre sí.** El random forest
  y la regresión logística no usan los resultados del gradient boosting:
  ejecutan sus celdas de preparación de datos directamente desde el archivo
  `gradient_boosting.ipynb`, para que los tres modelos usen exactamente la
  misma muestra y las mismas variables. Por eso ese archivo tiene que estar
  en la carpeta, y si se cambia cómo arma las variables, hay que volver a
  correr los tres.
- **5 va después de 2, 3 y 4.** Si le falta algún archivo, se detiene y dice
  cuál notebook correr. Además vuelve a cargar los modelos del gradient
  boosting (`.joblib`), así que conviene correr los tres modelos en el mismo
  entorno antes de compararlos.
- **6 va al final**, después de 1 y 5.

**Cuánto tarda.** La segmentación tarda unos 5 minutos, casi todos en las
pruebas de estabilidad, que vuelven a entrenar K-means cientos de veces. En
el random forest, la búsqueda de hiperparámetros tardó unos 9 minutos en la
corrida de referencia, según su propia salida. Los demás notebooks no
registran su tiempo. Todos los comandos llevan `timeout=-1` para que
`nbconvert` no corte una celda larga.

### Segmentación de los municipios (`segmentacion_municipios.ipynb`)

Agrupa con K-means a los 640 municipios rurales y rurales dispersos que
tienen celdas en la grilla. Los agrupa según su perfil productivo y
financiero, con diez variables relativas promediadas en 2021-2024:

- el bosque;
- los bovinos por km² y por finca;
- el área cosechada y la participación de palma, cacao, café y arroz;
- el crédito de producción por km² y la parte que va a la ganadería.

La deforestación no entra en la segmentación: se usa después para comparar
los segmentos.

El notebook sigue este orden:

1. **Preprocesamiento** en un `Pipeline` de scikit-learn: imputación con la
   mediana, `log(1 + x)` a las intensidades y estandarización.
2. **Elección de k** con el codo, la silueta y la estabilidad por
   bootstrap. La silueta se compara con la de datos sin estructura, que son
   las mismas variables barajadas por separado.
3. **Robustez**: la estabilidad de cada segmento, medida con el Jaccard
   medio en 200 remuestreos bootstrap.
4. **Perfiles**: centros, medianas y componentes principales.
5. **Deforestación de cada segmento** y el mapa.

A diferencia de `panel_municipal_analisis.ipynb`, este notebook sí trae la
interpretación de los resultados. Todo lo aleatorio parte de una semilla
fija, así que los textos coinciden con las cifras mientras los datos no
cambien. Si se vuelve a armar el panel, hay que releer los textos.

### Modelos de riesgo: diseño común

Los tres modelos (`gradient_boosting.ipynb`, `random_forest.ipynb` y
`regresion_logistica.ipynb`) comparten el mismo diseño, para que sus
cifras se puedan poner una al lado de la otra:

| Elemento | Cómo es |
|---|---|
| Unidad | Municipio × año |
| Muestra | 3.195 municipios-año de 2021 a 2025: municipios rurales y rurales dispersos que tienen bosque |
| Preguntas | **¿Deforesta?** (tasa del IDEAM > 0), una clasificación con todas las filas; y **si deforesta, ¿cuánto?** (la tasa, % del bosque), una regresión solo con las filas que deforestan |
| Variables | 15 explicativas del **mismo año**, sin rezago, como intensidades: crédito de producción (total y por cadena) por km²; bovinos y fincas ganaderas por km²; área cosechada (total y de palma, cacao, café y arroz) y bosque como % del municipio; y el área del municipio. La EVA no tiene 2025, así que los cultivos de 2025 repiten los de 2024 |
| Partición | Entrena con 2021-2024 y prueba con 2025 (639 municipios) |
| Validación | `GroupKFold` por departamento, con 5 pliegues: en la búsqueda de hiperparámetros y en una evaluación con departamentos completos por fuera |
| Selección de hiperparámetros | Exactitud balanceada para *¿deforesta?* y R² para *¿cuánto?* |
| Umbral de clasificación | 0,5 |

Las preparaciones de datos de `random_forest.ipynb` y
`regresion_logistica.ipynb` no repiten el código: ejecutan las celdas de
`gradient_boosting.ipynb` y verifican, fila por fila, que la muestra sea la
misma.

### Gradient boosting (`gradient_boosting.ipynb`)

Es el modelo principal. Usa LightGBM, que maneja los valores vacíos sin
imputarlos. Busca los hiperparámetros de la Tabla 26 del documento:
`learning_rate`, `max_depth` y `min_child_samples`, con hasta 1.000
árboles y parada temprana. Después evalúa el modelo en 2025 y con
departamentos por fuera, mide la importancia de las variables por
permutación, da la dirección de cada efecto con SHAP y arma la lista de
municipios de mayor riesgo.

LightGBM corre en un solo hilo y en modo determinista, para que la búsqueda
dé el mismo resultado en cualquier computador.

### Random forest (`random_forest.ipynb`)

El bosque aleatorio de scikit-learn, con la misma estructura y las mismas
secciones que el gradient boosting. Busca los hiperparámetros de la Tabla
27. Agrega cuatro lecturas que vienen de su versión anterior:

- la búsqueda agrupando por municipio frente a por departamento;
- qué aportan el crédito y la producción más allá del bosque y el área;
- la importancia por bloques y por actividad productiva;
- la dependencia parcial.

### Regresión logística (`regresion_logistica.ipynb`)

Es la referencia interpretable: si los ensambles no le ganan, su
complejidad no se justifica. Tiene tres cosas propias:

- **Antes de entrenar**: transforma las variables y quita las muy
  correlacionadas con un VIF iterativo. Las dos cosas se aprenden solo con
  los datos de entrenamiento.
- **Inferencia**: odds ratios con errores estándar agrupados por
  departamento y corrección de Holm, efectos marginales y pruebas de Wald
  por actividad.
- **¿Cuánto?**: lo responde con una regresión Gamma con enlace logarítmico,
  así que sus coeficientes se leen como efectos multiplicativos sobre la
  tasa.

Igual que el random forest, rescata lecturas de su versión anterior.

### Comparación de modelos (`comparacion_modelos.ipynb`)

No entrena nada. Lee lo que guardaron los tres modelos y recalcula de la
misma forma todas sus métricas a partir de las probabilidades de 2025. Las
del gradient boosting se calculan aquí mismo, cargando su `.joblib`, porque
ese notebook no las guarda.

Antes de comparar, se verifica a sí mismo:

- que los tres evalúan las mismas 639 filas;
- que el resultado real es idéntico;
- que usan las mismas 15 variables;
- que lo recalculado coincide con lo que reportó cada notebook.

Después compara:

- las métricas y las curvas;
- las matrices de confusión;
- si los modelos coinciden en qué municipios son riesgosos;
- la regresión de *¿cuánto?*;
- la importancia de las variables;
- dónde coinciden alto crédito y alto riesgo.

Cierra con ventajas y desventajas, un veredicto y una síntesis por objetivo
del documento. Todas las frases de resultados se generan con los números de
la corrida: no hay cifras escritas a mano.

### Segmentos y riesgo (`segmentos_y_riesgo.ipynb`)

Cruza los dos resultados del modelado: el segmento de cada municipio (qué
tipo de municipio es) y la probabilidad de deforestar en 2025 que le dan los
tres modelos (cuánto riesgo tiene). Responde cuatro preguntas:

1. ¿Qué perfiles concentran el riesgo?
2. Dentro de un mismo perfil, ¿los modelos saben cuáles municipios
   deforestan?
3. ¿Con qué municipios conviene empezar? Responde con una lista de
   prioridad.
4. ¿Dónde coinciden alto riesgo y alto crédito, y de qué perfil son esos
   municipios?

Tampoco entrena nada, y sus frases también se calculan con los números de la
corrida. El segmento resume el promedio 2021-2024, y el riesgo es el de
2025.

### Versiones anteriores

Las versiones anteriores del random forest y de la regresión logística ya
no están en la carpeta. Los notebooks las citan como "la versión anterior"
para explicar de dónde salen algunas lecturas, pero no las necesitan para
correr.

Se pueden recuperar del historial de git, en el commit `4793898`. Ahí, las
versiones anteriores son `random_forest.ipynb`, `random_forest_2.ipynb`,
`regresion_logistica.ipynb` y `regresion_logistica_2.ipynb`; los notebooks
actuales son los que en ese commit se llaman `random_forest_3.ipynb` y
`regresion_logistica_3.ipynb`. Por ejemplo:

```bash
git show 4793898:"modelos y clusters/random_forest_2.ipynb" > random_forest_2.ipynb
```

---

## 4. Resultados esperados

Todo lo aleatorio de los notebooks parte de una semilla fija. Con los mismos
datos, las cifras deberían coincidir con las de la corrida de referencia:

| Notebook | Cifra de control | Corrida de referencia |
|---|---|---|
| `panel_municipal_analisis.ipynb` | Municipios rurales y rurales dispersos | 642 |
| `segmentacion_municipios.ipynb` | Municipios segmentados | 640: los 642 menos dos que no tienen celdas en la grilla |
| `segmentacion_municipios.ipynb` | Segmentos | 8, de 64, 86, 47, 123, 142, 42, 101 y 35 municipios |
| `segmentacion_municipios.ipynb` | Silueta con 8 segmentos | 0,26 |
| Los tres modelos | Muestra | 3.195 municipios-año: 2.556 para entrenar (2021-2024) y 639 para probar (2025) |
| `comparacion_modelos.ipynb` | Verificación | Las cuatro comprobaciones de su sección 1 salen bien |

Métricas en la prueba de 2025:

| Métrica | Gradient boosting | Random forest | Regresión logística |
|---|---|---|---|
| ¿Deforesta? — exactitud balanceada | 0,830 | 0,854 | 0,826 |
| ¿Deforesta? — AUC | 0,928 | 0,929 | 0,906 |
| ¿Cuánto? — R² | 0,059 | 0,062 | 0,013 |
| ¿Cuánto? — R² sin Pedraza | 0,354 | 0,369 | 0,112 |

El R² de *¿cuánto?* es muy bajo porque un solo municipio, Pedraza, pesa
demasiado en la prueba. Sin él sube a 0,35-0,37 en los dos ensambles. Cada
notebook lo explica en su sección 5.3. Todas las métricas están en
`modelos y clusters/resultados/comparacion_modelos_metricas.csv`.

Si las fuentes se actualizaron después de la corrida de referencia, las
cifras cambian:

- en `comparacion_modelos.ipynb` y `segmentos_y_riesgo.ipynb` los textos se
  generan con los números de cada corrida, así que se actualizan solos;
- en `segmentacion_municipios.ipynb` los textos están escritos a mano, y hay
  que releerlos.

---

## 5. Problemas comunes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `jupyter nbconvert` dice que no encuentra el notebook | La ruta tiene espacios (`procesamiento y eda/`, `modelos y clusters/`) y no va entre comillas | Escribir la ruta entre comillas, como en la sección 1 |
| `nbconvert` corta un notebook con `CellTimeoutError` | Hay un límite de tiempo por celda, puesto en la configuración de Jupyter o en el comando | Agregar `--ExecutePreprocessor.timeout=-1`, como en la sección 1, que quita el límite |
| Un notebook de `modelos y clusters/` no encuentra `datos/analisis/municipio_anio.parquet` | No se ha armado el panel municipal | Correr primero `panel_municipal_armado.ipynb` (Paso 14 de [`2_DESCARGA_DE_DATOS.md`](2_DESCARGA_DE_DATOS.md)) |
| `comparacion_modelos.ipynb` se detiene con "Faltan archivos en modelos y clusters/resultados/" | No se han corrido los tres modelos | Correr el notebook que nombra el mensaje (`gradient_boosting.ipynb`, `random_forest.ipynb` o `regresion_logistica.ipynb`) y volver a correr la comparación |
| `comparacion_modelos.ipynb` dice que las filas de 2025 no coinciden entre modelos | Los modelos se corrieron con versiones distintas del panel municipal | Volver a correr los tres modelos con el mismo panel, y después la comparación |
| Advertencias o errores al cargar un `.joblib` | El modelo se entrenó con otra versión de `lightgbm` o `scikit-learn` | Volver a correr el notebook que lo entrenó en el entorno actual |
| `segmentos_y_riesgo.ipynb` se detiene porque faltan archivos | No se han corrido la segmentación o la comparación | Correr `segmentacion_municipios.ipynb` y `comparacion_modelos.ipynb` (que necesita los tres modelos) |
