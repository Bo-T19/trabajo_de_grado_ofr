# Metodología — Panel espacio-temporal de deforestación en Colombia

Este documento explica **qué mide el panel, de dónde sale cada dato, y por
qué se diseñó así** — el "qué y por qué". El "cómo está programado" vive en
[GUIA_CODIGO.md](GUIA_CODIGO.md).

El destino declarado de este panel no es solo académico: es insumo de
consultorías comerciales del Observatorio Financiero Rural de la Pontificia
Universidad Javeriana. Eso condiciona varias decisiones documentadas aquí,
en particular la sección 7 (licencias).

---

## Índice

1. [Diseño general](#1-diseño-general)
2. [Fuentes de datos](#2-fuentes-de-datos)
3. [Marco conceptual: de píxeles a panel](#3-marco-conceptual-de-píxeles-a-panel)
4. [Bitácora de decisiones de diseño](#4-bitácora-de-decisiones-de-diseño)
5. [Supuestos del estudio](#5-supuestos-del-estudio)
6. [Limitaciones conocidas](#6-limitaciones-conocidas)
7. [Restricciones de licencia y uso comercial](#7-restricciones-de-licencia-y-uso-comercial)
8. [Cómo se ve la unidad de observación final](#8-cómo-se-ve-la-unidad-de-observación-final)
9. [Glosario técnico](#9-glosario-técnico)
10. [Referencias](#10-referencias)

---

## 1. Diseño general

### 1.1 Pregunta que responde el panel

Para cada celda de 5×5 km del territorio continental de Colombia y cada
mes desde enero de 2020, ¿cuántas hectáreas de bosque se perdieron ese mes,
y cuánto bosque quedaba disponible para perderse al empezar ese mes? Es un
panel espacio-temporal balanceado (toda celda tiene una fila en todo
periodo), pensado como insumo para un modelo posterior de riesgo de
deforestación, no como el modelo en sí.

### 1.2 Unidad de análisis: por qué una celda de 5×5 km y no el píxel nativo

La fuente de evento (sección 2.2) detecta a nivel de píxel, pero modelar al
nivel de píxel individual no es práctico ni necesario aquí:

- **Volumen**: el territorio continental de Colombia a resolución de
  decenas de metros son cientos de millones de píxeles: inviable para
  entrenar o interpretar un modelo estadístico convencional.
- **Señal vs. ruido**: un solo píxel deforestado es una observación binaria
  casi siempre en cero; agregar a 5×5 km (2500 ha) da una magnitud continua
  (hectáreas) con varianza suficiente para modelar tasas.
- **Relevancia para el caso de uso**: el Observatorio necesita identificar
  **zonas** de riesgo para orientar consultoría y política de crédito rural,
  no el píxel exacto.

5 km es un punto medio: suficientemente fino para distinguir municipios
vecinos con dinámicas distintas, suficientemente agregado para que el
panel completo (~45 000 celdas × N meses) sea manejable.

### 1.3 Ventana temporal: 2020-01 en adelante, y por qué mensual

La ventana temporal (`fecha_inicio = 2020-01-01`) está determinada por la
disponibilidad real de la fuente de evento (sección 2.2). La resolución
mensual (`frecuencia = "MS"`) es un punto medio entre:

- **Resolución más fina** (p. ej. semanal): más granularidad, pero la
  fuente de evento no garantiza una observación limpia (sin nubes) de cada
  celda cada semana — más ceros artificiales por falta de datos, no por
  ausencia real de deforestación.
- **Resolución más gruesa** (p. ej. anual): pierde la capacidad de
  encadenar rezagos y estacionalidad de corto plazo (`lag_k_ha` y
  `media_movil_3`, sección 3.4).

---

## 2. Fuentes de datos

Se cruzan **dos** productos independientes — cada uno responde una
pregunta distinta — más una capa cartográfica auxiliar que no aporta señal
de cambio, solo estructura espacial y atributos administrativos.

### 2.1 Hansen Global Forest Change (GFC) — la línea base

**Qué es.** Producto global de cobertura y cambio de bosque a 30 m de
resolución, desarrollado por el Global Land Analysis and Discovery (GLAD)
lab de la Universidad de Maryland en colaboración con Google, publicado
originalmente en Hansen et al. (2013) y actualizado anualmente desde
entonces (sección 10). Es uno de los productos de cobertura forestal más
usados en la literatura de deforestación global: gratuito, de cobertura
mundial y homogéneo (mismo algoritmo aplicado a todo el planeta).

**Cómo se produce (resumen).** Un modelo de árboles de decisión (con
*bagging*) sobre series temporales de reflectancia Landsat clasifica, año a
año, si un píxel sufrió pérdida de cobertura arbórea de tipo "reemplazo de
rodal" (*stand-replacement disturbance*), sin importar la causa (tala,
incendio, plaga, fenómeno natural). La capa de cobertura del año 2000
(`treecover2000`) viene de un modelo de regresión que relaciona
reflectancia Landsat con % de cobertura de dosel.

**Qué se usa de este producto:**

| Capa | Qué mide | Cómo se usa aquí |
|---|---|---|
| `treecover2000` | % de cobertura de dosel arbóreo en el año 2000 | Umbral para decidir si un píxel *era* bosque en el año base |
| `lossyear` | Año (codificado 1–24 → 2001–2024) en que el píxel perdió cobertura | Descuenta del bosque base los píxeles que ya se sabía habían perdido cobertura antes del inicio de la ventana de eventos |

**Por qué Hansen y no otra fuente de línea base.** Se consideraron:

- **IDEAM/SMByC** (sistema oficial colombiano): fuente "oficial" del país,
  pero de publicación más lenta y sin un formato programáticamente
  descargable fuera de Colombia sin gestionar accesos adicionales —
  importante porque este pipeline debe poder correrlo un tercero (director
  de tesis, jurado) sin credenciales especiales.
- **MapBiomas Colombia**: clasificación multi-clase muy rica, pero pensada
  para cobertura de uso del suelo, no optimizada específicamente para el
  evento binario "pérdida de bosque" con la validación de Hansen GFC.

Se eligió Hansen GFC por ser gratuito, descargable por HTTP sin
autenticación, de cobertura y método homogéneos, y ampliamente validado en
la literatura.

**Limitaciones conocidas** (heredadas por este pipeline):

- No distingue la **causa** de la pérdida — agnóstico al proceso.
- Puede confundir plantaciones forestales de rotación corta con
  deforestación real; este pipeline no filtra ese caso aparte.
- `lossyear` tiene resolución **anual**: no dice en qué mes se perdió un
  píxel — por eso se usa solo para la línea base, no para el evento
  mensual (sección 2.2).

### 2.2 Global Forest Watch — Integrated Disturbance Alerts (el evento)

**Qué es.** Producto de Global Forest Watch / World Resources Institute
(WRI) que combina, en una sola capa con una única escala de confianza,
**cuatro** sistemas independientes de alerta de disturbio: DIST-ALERT
(NASA OPERA), GLAD-L (Landsat, UMD), GLAD-S2 (Sentinel-2, UMD) y RADD
(radar Sentinel-1, Wageningen University). Metodología publicada y
revisada por pares: Pickens, Hansen, Song et al., *"Rapid monitoring of
global land change"*, Nature Communications 16, 8948 (2025).

**Por qué esta fuente.** Se prefirió el producto **ya integrado** frente a
combinar varios sistemas de alerta a mano: evita que la definición de
"evento" sea una decisión artesanal de esta tesis en vez de una
metodología ya publicada y validada por el equipo que produce los datos.
Además cubre la ventana completa desde 2020-01, con una cadencia de
detección casi en tiempo real.

**Cómo se accede.** Se consulta mediante una API SQL de solo lectura
(`data-api.globalforestwatch.org`) que corre la consulta directamente
sobre el dato, celda por celda de la grilla, y devuelve resultados ya
agregados (fecha, confianza, hectáreas) — no hace falta descargar ni
reproyectar ningún ráster de evento. El área en hectáreas la calcula la
propia API (campo `area__ha`): este producto usa una cuadrícula en grados
(EPSG:4326), y el área real de un píxel de tamaño angular fijo varía con
la latitud — sumar `area__ha` delega esa corrección en la fuente, en vez
de asumir un tamaño de píxel fijo para todo el país.

**Definición de evento.** El producto expone una escala de confianza de
tres niveles (`nominal`, `high`, `highest`). Este pipeline cuenta como
evento solo `high` y `highest`, descartando `nominal` (la detección menos
confiable, análoga a una alerta "provisional" sin confirmar) — ver
decisión 2 en la sección 4.

**Limitaciones conocidas:**

- Al combinar cuatro sistemas con metodologías de detección distintas
  (óptico de dos resoluciones + radar), la sensibilidad y el sesgo
  geográfico pueden no ser perfectamente homogéneos a lo largo del país —
  por ejemplo, el componente de radar es menos sensible a la nubosidad que
  los sistemas ópticos, lo que puede hacer que el sistema que "gana" la
  detección varíe por región.
- Es agnóstica a la causa del disturbio, igual que Hansen — no distingue
  deforestación de otros tipos de disturbio de vegetación (incendios en
  pastizales, cosecha agrícola, daño por tormenta).
- Como cualquier sistema de alerta casi en tiempo real, tiene un rezago de
  confirmación: los últimos 1-2 meses de cualquier corrida pueden estar
  subestimados porque parte de sus eventos reales todavía no se han
  confirmado al momento de la descarga.

### 2.3 Cartografía auxiliar (DANE) — no aporta señal de cambio

| Fuente | Uso | Por qué esta y no otra |
|---|---|---|
| DANE — Marco Geoestadístico Nacional (MGN) 2023, nivel departamento | Recorta la grilla al territorio continental de Colombia y etiqueta cada celda con su departamento | Fuente oficial colombiana, servida como *Feature Service* público de ArcGIS (sin autenticación), licencia **CC BY 4.0** (uso comercial permitido con atribución) |
| DANE — MGN, nivel municipal | Cruce **opcional** por centroide para obtener el código de municipio (`cod_dane`) | Misma fuente; es la oficial para unir variables socioeconómicas o de crédito rural del Observatorio. Opcional porque requiere descargar el shapefile municipal aparte |

Ninguna de las dos aporta información temporal ni de cambio: solo definen
**dónde** está cada celda y **cómo se llama** administrativamente.

---

## 3. Marco conceptual: de píxeles a panel

*(El detalle de cómo está programado cada paso está en
[GUIA_CODIGO.md](GUIA_CODIGO.md); aquí se explica qué calcula
matemáticamente y por qué esa es la operación correcta.)*

### 3.1 Máscara de bosque — definición formal

Un píxel `p` se considera **bosque disponible al inicio del análisis** si
y solo si:

```
bosque(p) = [ treecover2000(p) ≥ 30 ]  AND  NOT ( 0 < lossyear(p) ≤ (anio_mascara − 2000) )
```

con `anio_mascara = 2019`, un año antes de que arranque la ventana de
eventos (2020-01) — el bosque base tiene que quedar definido *antes* de que
arranque la fuente de evento, para que Hansen y la fuente de evento nunca
se atribuyan la misma pérdida dos veces (ver decisión 3, sección 4). El
umbral del 30% de cobertura de dosel es uno de los de referencia usados
por la FAO para operacionalizar "bosque" de forma comparable entre países.

**Cómo se calcula sin depender de ninguna cuadrícula externa.** Hansen
viene en gránulos de 10°×10° en su propia proyección geográfica; para
convertir eso en hectáreas de bosque por celda de 5 km hace falta
reproyectarlo a algún raster de referencia. Este pipeline construye ese
raster **directamente sobre la propia grilla nacional de 5 km**, en
bloques manejables (ver `calcular_bosque.py`), en vez de apoyarse en la
cuadrícula de descarga de ningún otro producto satelital — el bosque base
es, por diseño, una capa completamente independiente de la fuente de
evento.

### 3.2 Evento de deforestación — definición formal

Para una celda `c` y un mes calendario `t`:

```
evento_ha(c, t) = Σ area__ha, sobre las filas que la API de GFW devuelve
                  para la celda c con fecha dentro de t y
                  confidence ∈ {high, highest}
```

A diferencia de una fuente que expone estados de píxel crudos (donde el
pipeline tendría que decidir cómo evitar contar dos veces una misma alerta
observada en instantáneas sucesivas), aquí la API ya devuelve una fila por
evento con su fecha real: la suma por (celda, mes) es directa, sin
necesidad de ningún acumulador de deduplicación temporal en este pipeline.

### 3.3 El problema de la doble contabilización espacial (bloques traslapados)

Al calcular el bosque base en bloques (sección 3.1), los bloques se
definen como particiones exactas de la grilla (alineadas a bordes de
celda): **no se solapan entre sí**, así que sumar sus conteos por celda es
directamente correcto — a diferencia de un esquema por tiles de un
producto satelital externo (que sí suelen solaparse en los bordes y
requerirían tomar el máximo entre piezas para no duplicar bosque).

### 3.4 Del bosque base a las variables de exposición y tasa

`consolidar.py` deriva, para cada celda-mes, en orden:

- **`def_acum_ha`**: pérdida acumulada de la celda hasta ese periodo
  inclusive (`cumsum` sobre `area_def_ha`, ordenado cronológicamente).
- **`bosque_remanente_ha`**: bosque disponible **al inicio** de ese
  periodo — `bosque_base_ha` menos la pérdida acumulada **hasta el periodo
  anterior** (`shift(1)`). Es el denominador correcto de exposición: sin
  esta variable, el modelo aprendería la trivialidad "donde hay más bosque
  hay más deforestación", y las celdas ya agotadas contaminarían la
  muestra.
- **`tasa_def`**: `area_def_ha / bosque_remanente_ha`, acotada a [0, 1] —
  target continuo, normalizado por exposición.
- **`evento`**: `1` si `area_def_ha > 0` — target binario, pensado para la
  etapa de clasificación de un modelo de dos etapas (*hurdle* /
  cero-inflado), dado el fuerte desbalance de clases (sección 6).
- **`lag_1_ha`, `lag_2_ha`, `lag_3_ha`, `media_movil_3`**: deforestación de
  la misma celda en periodos anteriores — variables predictoras simples,
  la deforestación reciente suele predecir la futura.

---

## 4. Bitácora de decisiones de diseño

| # | Decisión | Alternativas consideradas | Por qué esta opción | Riesgo/costo aceptado |
|---|---|---|---|---|
| 1 | Fuente del evento: producto integrado de GFW (`gfw_integrated_dist_alerts`) | Combinar a mano, por separado, cada uno de los sistemas de alerta que este producto ya integra (sección 2.2) | El producto integrado ya es una metodología publicada y revisada por pares (Pickens et al. 2025): evita que la fusión de sensores sea una decisión artesanal de esta tesis | Al combinar sistemas con sensibilidades distintas, la homogeneidad metodológica interna del evento es algo menor que la de un solo sensor — aceptado a cambio de cobertura temporal completa desde 2020 y de apoyarse en una fusión ya validada |
| 2 | Confianza mínima del evento: `high` + `highest`, se descarta `nominal` | Incluir también `nominal` | `nominal` es la detección menos confiable (análoga a "primera detección, sin confirmar"); incluirla infla falsos positivos | El panel mide deforestación con confianza alta/altísima, no cualquier disturbio detectado — subestima disturbios de baja confianza que luego sí podrían confirmarse |
| 3 | Máscara de bosque con corte de Hansen en `anio_mascara = 2019`, un año antes del inicio de la ventana de eventos (2020-01) | Usar Hansen `lossyear` también para 2020 en adelante | Traza una línea clara: Hansen = línea base estática (hasta el corte), la fuente de evento = único registro de pérdida dentro de su ventana. Cortar justo antes evita que una misma pérdida se atribuya dos veces | Se asume que el bosque es estático entre el corte de Hansen (2019) y el inicio de la ventana de eventos (2020-01) — un margen de días, no de años |
| 4 | Grilla regular de 5×5 km como unidad de análisis | Píxel nativo; unidad administrativa (municipio) | Balance entre volumen computacional, señal estadística y resolución espacial útil (sección 1.2) | Se pierde la ubicación exacta del evento dentro de la celda |
| 5 | Proyección `EPSG:3116` para el indexado de la grilla | UTM por zona; una proyección de área equivalente (p. ej. Albers) | Proyección oficial colombiana (MAGNA-SIRGAS), de uso común en cartografía nacional; un único sistema de indexado simplifica el código | Alguna distorsión de forma/área lejos del meridiano central — mitigado porque el área reportada no depende de esta proyección (el área de evento la calcula la API de GFW; el área de bosque es conteo de píxeles a resolución fija) |
| 6 | Bosque base calculado en bloques de la propia grilla nacional (25 m/píxel, sin ninguna cuadrícula externa) | Apoyarse en la cuadrícula de descarga de algún otro producto satelital como "molde" geométrico | Evita una dependencia innecesaria: el bosque base es, conceptualmente, independiente de cualquier fuente de evento, y no hay razón para que su cálculo dependa de descargar algo de un producto distinto a Hansen | Hubo que construir el manejo de bloques (partición de la grilla, reproyección por bloque) en vez de reutilizar una cuadrícula ya existente — más código propio, pero sin la dependencia |
| 7 | Combinar bloques con suma directa, no `max()` | Tomar el máximo entre bloques, por seguridad | Los bloques se definen como partición exacta de la grilla (alineados a bordes de celda): nunca se solapan, así que sumar es correcto y no hace falta la protección adicional que sí necesitaría un esquema con piezas traslapadas | Ninguno relevante: depende de que la partición en bloques preserve la alineación de la grilla, verificado por construcción |
| 8 | Resolución de 25 m/píxel y bloques de 20 celdas (100 km) para reproyectar Hansen | 30 m (resolución nativa aproximada de Hansen); bloques más grandes o más pequeños | 25 m divide exactamente el lado de un bloque de 20 celdas (20×5000/25 = 4000 píxeles, sin residuo), evitando cualquier redondeo en los bordes entre bloques; el tamaño de bloque mantiene el uso de memoria por iteración en un rango cómodo | Diferencia de resolución mínima frente a los ~30 m nativos de Hansen — irrelevante frente al tamaño de celda (5000 m) |
| 9 | Remuestreo *nearest neighbor* al reproyectar Hansen | Remuestreo bilinear o cúbico | `treecover2000` y `lossyear` son variables de clasificación (bosque/no bosque, año categórico); interpolar valores continuos entre categorías produciría valores sin sentido físico | Cierto error posicional de sub-píxel en los bordes de manchas de bosque, inherente a cualquier remuestreo por vecino más cercano |
| 10 | Grilla construida localmente con `geopandas` y límites del DANE (MGN) | Google Earth Engine con `coveringGrid()` y assets `USDOS/LSIB_SIMPLE`/`FAO/GAUL_SIMPLIFIED`; GADM como fuente de límites | La edición gratuita/académica de Earth Engine **prohíbe explícitamente** su uso para "actividades de pago por servicio" o para "recibir compensación de una entidad comercial por aplicaciones o datos creados usando Earth Engine" — y este panel es insumo de consultorías comerciales del Observatorio. GADM es de uso no comercial únicamente, el mismo problema. El DANE (MGN, CC BY 4.0) permite uso comercial con atribución | El MGN del DANE es de precisión catastral completa (no generalizada), así que el polígono nacional sale con ~280 000 vértices; se simplifica con tolerancia de 100 m (irrelevante frente al lado de celda de 5000 m) para que el filtro espacial corra en segundos, no minutos |
| 11 | Rectángulo (`bbox`) para seleccionar gránulos de Hansen | Enviar la geometría exacta de Colombia | Los gránulos de Hansen son de 10×10 grados: un `bbox` simple basta para identificar cuáles hacen falta, sin construir ni depurar una consulta con geometría compleja | Se descargan gránulos que cubren de más (países vecinos, océano) — costo de almacenamiento marginal, no de tiempo de cómputo relevante |

---

## 5. Supuestos del estudio

1. **El bosque es estático entre el corte de Hansen (2019) y el inicio de
   la ventana de eventos (2020-01)**: no se contempla ganancia de bosque
   (regeneración) en ese margen, ni pérdida no capturada por Hansen antes
   del corte.
2. **Un evento confirmado con confianza alta/altísima ⇒ deforestación
   real**: se confía en la calidad de detección reportada por GFW; el
   pipeline no incorpora una validación de campo local ni un cruce con
   otra fuente independiente de verdad-de-campo (*ground truth*) para
   Colombia.
3. **Un píxel pertenece a lo sumo a una celda de la grilla**: el indexado
   aritmético asume que la grilla está perfectamente alineada al origen de
   `EPSG:3116` (verificado explícitamente en `exportar_grilla.py`).
4. **La fecha que devuelve la API de GFW es confiable como fecha del
   evento real.**
5. **Los bloques en que se calcula el bosque base cubren completamente el
   territorio continental de interés**: se asume que la partición de la
   grilla en bloques (sección 3.3) no deja ninguna celda sin procesar.

## 6. Limitaciones conocidas

- **Subestimación de los últimos meses de la ventana** por el *reporting
  lag* de confirmación de alertas casi en tiempo real (sección 2.2).
- **No se distingue causa del disturbio** en ninguna de las dos fuentes:
  el panel mide pérdida de cobertura/vegetación de cualquier origen
  (antrópico o natural), no específicamente deforestación por actividad
  humana en el sentido estricto.
- **Posible confusión con plantaciones forestales de rotación corta** en
  la línea base de Hansen (sección 2.1).
- **Al combinar cuatro sistemas de detección** (sección 2.2), la
  sensibilidad no es perfectamente homogénea a lo largo del país.
- **Sin validación de campo local**: la precisión reportada de ambos
  productos proviene de sus respectivas validaciones globales/regionales,
  no de un ejercicio de verificación específico para Colombia dentro de
  esta tesis.
- **El desbalance de clases es marcado** (ver sección 8 y
  `eda_deforestacion.ipynb`): cualquier modelo posterior debe tratar esto
  explícitamente (de ahí el diseño de `evento` como variable separada,
  pensada para un enfoque de dos etapas). La proporción exacta y
  actualizada está siempre en el notebook de EDA, no hay que tomar
  cualquier cifra congelada en este documento como fija.
- **Posible efecto de arranque en el primer periodo del panel**: cualquier
  sistema de monitoreo casi en tiempo real tiene una fecha de inicio; el
  primer mes podría concentrar disturbios que ya existían pero apenas se
  estaban confirmando cuando arrancó el monitoreo. El notebook de EDA
  cuantifica esto empíricamente sobre cada corrida (sección 5 del
  notebook) — no se asume que ocurre, se verifica.

---

## 7. Restricciones de licencia y uso comercial

Esta sección existe porque el destino declarado de este panel va más allá
de lo académico: es insumo de consultorías comerciales del Observatorio
Financiero Rural de la Javeriana. Eso cambia qué licencias son aceptables
para las fuentes de datos — una fuente "gratis para investigación" no
necesariamente es gratis para vender un servicio con ella. Lo que sigue es
un resumen, **no asesoría legal**, con fuente citada para cada afirmación,
para que la oficina jurídica o de transferencia tecnológica de la
universidad lo revise antes de comercializar cualquier producto derivado
de este panel.

| Fuente | Licencia | Uso comercial | Obligación práctica |
|---|---|---|---|
| Hansen Global Forest Change | CC BY 4.0 | Permitido, incluida la reventa/redistribución | Atribución: *"Source: Hansen/UMD/Google/USGS/NASA"* + cita del paper (Hansen et al. 2013, sección 10) |
| DANE — Marco Geoestadístico Nacional | CC BY 4.0 | Permitido | Atribución, en las palabras del propio DANE: *"Departamento Administrativo Nacional de Estadística - DANE: www.dane.gov.co"* |
| GFW / GLAD-L / GLAD-S2 / RADD (evento) | CC BY 4.0 (confirmado para GFW en general y para RADD directamente desde Wageningen University; GLAD-L es muy probablemente el mismo caso — mismo laboratorio que Hansen GFC — pero no se encontró una página que lo confirme en esas palabras exactas específicamente para GLAD-L) | Permitido | Atribución por dataset; GFW advierte que "cada dataset tiene su propia licencia", así que conviene guardar un archivo de atribuciones junto al panel final |
| ~~Google Earth Engine~~ (no se usa) | Edición gratuita/académica: uso no comercial únicamente | **Prohibido explícitamente** para este caso de uso | Nunca se usó en este pipeline — ver decisión 10, sección 4, y cita textual abajo |

**Por qué no se usa Earth Engine** (cita textual de los términos de la
edición no comercial, https://earthengine.google.com/noncommercial/):
instituciones académicas que reciben Earth Engine gratis no pueden "usar
Earth Engine para actividades de pago por servicio, incluyendo cumplir un
entregable, resultado o tarea pagado por un acuerdo de pago-por-servicio
con una entidad comercial, gubernamental u otra", ni "recibir compensación
de una entidad comercial por aplicaciones o datos creados usando Earth
Engine". Ese es exactamente el modelo de negocio del Observatorio.

**Recomendación práctica**: cualquier reporte o entregable comercial que
use este panel debería incluir un bloque de atribución citando las
fuentes que efectivamente entraron en ese entregable
(Hansen/UMD/Google/USGS/NASA, DANE, y GFW/UMD/WUR), y llevar este resumen
—o uno actualizado, si las licencias cambian— a la revisión legal de la
universidad antes de la primera venta.

---

## 8. Cómo se ve la unidad de observación final

*(Los números de esta sección son de una corrida puntual, congelados como
ejemplo. El pipeline se sigue corriendo y el panel crece con cada nueva
descarga — la fuente viva y siempre actualizada de estas cifras, con
gráficas, es [`eda_deforestacion.ipynb`](eda_deforestacion.ipynb).)*

El panel resultante (`datos/panel/panel_deforestacion_colombia.csv`) es
una tabla de **3 524 664 filas × 17 columnas**: 44 616 celdas × 79 periodos
mensuales (2020-01 a 2026-07), cubriendo 32 departamentos. Cada fila es una
celda-mes. Bosque total 77 713 177 ha, deforestación total 6 444 875 ha
(38,96 % de las celda-mes con evento). La descripción completa de las 17
columnas, con ejemplos y cómo inspeccionarlas en `pandas`, está en
[GUIA_CODIGO.md, sección "Cómo se ve la base de datos final"](GUIA_CODIGO.md#cómo-se-ve-la-base-de-datos-final)
— aquí se documenta como parte de la metodología porque el diseño de cada
columna (qué mide, en qué unidades, por qué existe) es una decisión
metodológica, no solo de formato de archivo.

---

## 9. Glosario técnico

| Término | Significado |
|---|---|
| **CRS** | Sistema de referencia de coordenadas (p. ej. `EPSG:3116`, `EPSG:4326`) |
| **Panel de datos** | Estructura de datos con una dimensión de sección cruzada (aquí, la celda) y una temporal (aquí, el mes), repetida sistemáticamente |
| **Hurdle / cero-inflado** | Familia de modelos de dos etapas para variables con exceso de ceros: una etapa de clasificación (¿hubo evento?) y una de magnitud (¿cuánto, dado que hubo?) |
| **MAGNA-SIRGAS** | Marco de referencia geodésico oficial de Colombia; `EPSG:3116` es su proyección para la franja "Bogotá" |
| **DANE / MGN** | Departamento Administrativo Nacional de Estadística / Marco Geoestadístico Nacional: cartografía oficial de división político-administrativa de Colombia |
| **GLAD** | Global Land Analysis and Discovery lab, Universidad de Maryland — produce Hansen GFC y los sistemas de alerta GLAD-L/GLAD-S2 |
| **RADD** | Sistema de alerta de disturbio basado en radar Sentinel-1, Wageningen University — detecta a través de nubes |
| **Confianza (GFW)** | Escala de tres niveles (`nominal`/`high`/`highest`) que expone el producto integrado de GFW para cada alerta |

## 10. Referencias

- Hansen, M. C., Potapov, P. V., Moore, R., Hancher, M., Turubanova, S. A.,
  Tyukavina, A., Thau, D., Stehman, S. V., Goetz, S. J., Loveland, T. R.,
  Kommareddy, A., Egorov, A., Chini, L., Justice, C. O., & Townshend, J. R. G.
  (2013). High-Resolution Global Maps of 21st-Century Forest Cover Change.
  *Science*, 342(6160), 850–853. https://doi.org/10.1126/science.1244693
  — actualizaciones anuales del producto: https://glad.earthengine.app/view/global-forest-change
- Pickens, A. H., Hansen, M. C., Song, X.-P., et al. (2025). Rapid
  monitoring of global land change. *Nature Communications*, 16, 8948.
  (Verificar el DOI exacto contra la publicación antes de citar en la
  tesis — no se tiene una fuente verificada de él en este proyecto.)
- Global Forest Watch / World Resources Institute. *Integrated
  Deforestation Alerts*. https://www.globalforestwatch.org
- DANE. *Marco Geoestadístico Nacional 2023*.
  https://www.dane.gov.co
