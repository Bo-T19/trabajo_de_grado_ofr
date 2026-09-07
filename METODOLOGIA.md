# Metodología — Panel espacio-temporal de deforestación en Colombia

Este documento explica **qué mide el panel, de dónde sale cada dato, y por
qué se diseñó así** — el "qué y por qué". El "cómo está programado" vive en
[GUIA_CODIGO.md](GUIA_CODIGO.md).

El destino declarado de este panel abarca, además del uso académico, su
empleo como insumo de consultorías comerciales del Observatorio Financiero
Rural de la Pontificia Universidad Javeriana. Eso condiciona varias
decisiones documentadas aquí, en particular la sección 7 (licencias).

---

## Índice

1. [Diseño general](#1-diseño-general)
   - [1.2 Para qué sirve cada fuente](#12-para-qué-sirve-cada-fuente)
2. [Fuentes de datos](#2-fuentes-de-datos)
3. [Marco conceptual: de píxeles a panel](#3-marco-conceptual-de-píxeles-a-panel)
4. [Bitácora de decisiones de diseño](#4-bitácora-de-decisiones-de-diseño)
5. [Supuestos del estudio](#5-supuestos-del-estudio)
6. [Limitaciones conocidas](#6-limitaciones-conocidas)
7. [Restricciones de licencia y uso comercial](#7-restricciones-de-licencia-y-uso-comercial)
8. [Cómo se ven las unidades de observación finales](#8-cómo-se-ven-las-unidades-de-observación-finales)
9. [Glosario técnico](#9-glosario-técnico)
10. [Referencias](#10-referencias)

---

## 1. Diseño general

### 1.1 Pregunta que responde el panel

Para cada celda de 5×5 km del territorio continental de Colombia,
¿cuánto bosque se perdió, cuándo, y cuánto bosque quedaba disponible para
perderse?

La pregunta se responde con **cuatro paneles** sobre la misma grilla,
porque **no existe una sola fuente** que sea a la vez oportuna,
homogénea a escala global y oficialmente válida. Cada una renuncia a algo:

| Panel | Fuente | Qué mide exactamente | Unidad | Su ventaja | Lo que sacrifica |
|---|---|---|---|---|---|
| **1. Alertas** | GFW `gfw_integrated_alerts` | *Disturbio* de la vegetación, en ha | celda × **mes** | Máxima resolución temporal; detección casi en tiempo real | No distingue causa; las alertas son provisionales y pueden reclasificarse |
| **2. Pérdida** | Hansen GFC | *Pérdida de cobertura arbórea*, en ha | celda × **año** | Mismo algoritmo en todo el planeta: permite comparar países | Incluye cosecha de plantación e incendio; anual y estático |
| **3. Oficial** | IDEAM / SMByC | *Deforestación* de bosque natural, en ha | celda × **periodo** | Es la cifra que Colombia reporta; definición nacional de bosque | Rezago de publicación; solo cubre Colombia |
| **4. Detecciones** | IDEAM / SMByC (DTD) | *Detecciones* de alerta, en número de puntos | celda × **trimestre** | Único producto oficial de cadencia sub-anual; cobertura nacional | Mide conteos, no superficie; los conteos no son comparables entre años |

**Los cuatro miden cosas distintas y por eso nunca se suman entre sí.**
Lo que comparten —y lo que los hace comparables— es la grilla de 5 km, la
línea base de bosque calculada una sola vez, y el cruce municipal.

Los tres primeros expresan **hectáreas** y son comparables en magnitud
entre sí. El cuarto expresa **conteos** y responde a otra pregunta: dónde
situó el IDEAM el fenómeno ese trimestre.

La sección 1.2 desarrolla, con la evidencia de la corrida, para qué
sirve cada uno y qué no puede hacer.

El panel de alertas es además espacio-temporal **balanceado** (toda celda
tiene una fila en todo periodo), pensado como insumo para un modelo
posterior de riesgo de deforestación.

#### Advertencia sobre la independencia de las fuentes

Al argumentar convergencia hay que declarar una asimetría: **Hansen y las
alertas de GFW no son independientes entre sí.** El producto Hansen y el
sistema GLAD provienen del mismo laboratorio (GLAD, Universidad de
Maryland) y ambos se basan en imágenes Landsat, de modo que su
coincidencia aporta menos evidencia de lo que aparenta. Las parejas
genuinamente independientes son IDEAM–Hansen e IDEAM–GFW; dentro de las
alertas, RADD (radar Sentinel-1, Wageningen) sí es independiente de la
familia Landsat.

#### El doble papel de Hansen

Hansen aparece dos veces en el diseño y conviene no confundir los papeles:

- **Como línea base** (§2.1): define `bosque_base_ha`, el denominador
  común de los cuatro paneles. Este papel es estructural y ninguna otra
  fuente lo cubre.
- **Como fuente de evento** (panel 2): la pérdida anual de cobertura.

### 1.2 Para qué sirve cada fuente

Cada panel responde una pregunta que los otros no pueden responder. Lo
que sigue lo sustenta con cifras de la propia corrida, verificables
contra las salidas del pipeline.

#### Panel 1 — Alertas de GFW: **cuándo**

Es el de mayor resolución temporal del proyecto: mensual, con detección
casi en tiempo real. Sirve para saber qué está ocurriendo ahora y para
modelar la dinámica del fenómeno, que es el destino previsto de este
panel.

Su serie sigue de cerca la magnitud oficial: la correlación anual entre
las hectáreas con alerta y la cifra del IDEAM es **+0,971**. Reporta
entre 1,13 y 1,55 veces esa cifra según el año, porque una alerta señala
disturbio de la vegetación y no toda alteración del dosel es conversión
del uso del suelo.

#### Panel 2 — Hansen: **comparación con otros países**

Aplica el mismo algoritmo en todo el planeta, lo que permite situar a
Colombia frente a Brasil, Perú o Indonesia con una medida homogénea. El
IDEAM cubre solo Colombia, y las alertas de GFW varían en sensibilidad
según la región.

Cumple además otras dos funciones: aporta la **línea base de bosque**
(`bosque_base_ha`) que los cuatro paneles usan como denominador, y
constituye una fuente **independiente del Estado evaluado**, lo que le da
valor probatorio en una debida diligencia de importación.

Reporta entre 1,53 y 2,50 veces la cifra oficial, porque contabiliza toda
pérdida de cobertura arbórea: cosecha de plantación, incendio y daño
natural, además de la deforestación.

#### Panel 3 — IDEAM, capas de cambio: **cuánto**

Es la cifra oficial de Colombia y la única que mide deforestación de
bosque natural con la definición nacional. Funciona como referente de
validez de todo el trabajo: la agregación zonal de este proyecto
reproduce el dato publicado entre el **99,65 % y el 99,84 %**, lo que
verifica el procedimiento contra una fuente externa.

Aporta también el denominador correcto para sus propias tasas
(`bosque_ideam_ha`) y las columnas de calidad por nubosidad
(`sin_info_ha`).

#### Panel 4 — IDEAM, detecciones tempranas: **dónde, con respaldo oficial**

Es el único producto **oficial de cadencia sub-anual** disponible para
Colombia, y ese es exactamente el espacio que ocupa:

| Producto | Oficial | Cadencia | Unidad |
|---|---|---|---|
| Alertas GFW | No | Mensual | Hectáreas |
| Capas de cambio del IDEAM | Sí | Anual | Hectáreas |
| **Detecciones tempranas (DTD)** | **Sí** | **Trimestral** | **Conteo de puntos** |

Sus cuatro usos, cada uno verificado:

**1. Priorización espacial.** El ranking municipal por detecciones llega
a la misma respuesta que la cifra oficial anual, con meses de
anticipación:

| Coincidencia | Resultado |
|---|---|
| Top-10 municipios | **10 de 10** |
| Top-25 municipios | 21 de 25 |
| Top-50 municipios | 39 de 50 |
| Correlación de rangos (Spearman) | **0,811** |

La marca discrimina con fuerza. Comparando, trimestre a trimestre, los
municipios con detección contra los que no la tienen:

| Municipios en el trimestre | Hectáreas con alerta GFW (mediana) |
|---|---|
| **Con** detección del IDEAM | **30,6** |
| **Sin** detección del IDEAM | 0,2 |

Un municipio señalado concentra del orden de **130 veces** más superficie
con alerta que uno no señalado. Y dentro del trimestre el conteo ordena
razonablemente por magnitud, aunque no la cuantifique: la correlación de
rangos entre número de detecciones y hectáreas de GFW tiene mediana
**0,651** (rango 0,513 a 0,784 sobre los 25 trimestres).

**2. Valor probatorio.** La afirmación "el IDEAM detectó alertas aquí"
proviene de la autoridad ambiental del país. Cada punto identifica
además el municipio, la vereda y la corporación autónoma regional
competente sobre ese territorio.

**3. Validación del panel mensual.** El **92,1 %** de las celda-trimestre
con detección oficial tiene también alerta de GFW en ese mismo trimestre.
Eso confirma, contra una fuente oficial e independiente, que el panel de
alertas señala los lugares correctos. La correlación entre el conteo de
detecciones y las hectáreas de GFW es 0,542: coinciden en *dónde*, no en
*cuánto*, que es lo esperable entre un conteo y una superficie.

**4. Áreas protegidas.** El 11,1 % de las detecciones cae dentro del
SINAP. La deforestación dentro de un área protegida tiene una
connotación legal distinta, y ninguna otra fuente del proyecto la
identifica.

**Lo que este panel no puede hacer.** Sus datos son **puntos sin
superficie asociada**: no hay campo de área, y el campo `count` vale
siempre 1. Se verificó en las tres distribuciones que publica el SMByC
—los puntos en KML, los "núcleos" en KMZ (que resultan ser una imagen
superpuesta, no polígonos) y el ráster TIF (una superficie de densidad a
2 500 m)—: ninguna permite derivar hectáreas.

De ahí se sigue la limitación temporal. Sin extensión asociada, el conteo
depende de con cuánto detalle el instituto divida sus detecciones, y ese
criterio cambió a lo largo de la serie. Se probaron los tres agregados
posibles contra la cifra oficial (2021-2024), y los tres se mueven en
sentido contrario a la deforestación real:

| Agregado del panel DTD | Correlación con la cifra oficial |
|---|---|
| Conteo de puntos | −0,669 |
| Celdas con alerta | **−0,994** |
| Municipios con alerta | −0,978 |
| *(referencia: alertas GFW en hectáreas)* | *+0,971* |

El indicador de presencia, que en principio debería ser más robusto que
el conteo, resulta incluso peor. **La tabla sirve dentro de cada
trimestre, para comparar unos lugares con otros; no para comparar un
trimestre con otro.** Para magnitud y para tendencia temporal están los
paneles 1 y 3.

#### Resumen

| Pregunta | Panel |
|---|---|
| ¿Cuándo está ocurriendo? | 1 — Alertas GFW (mensual) |
| ¿Cuánto fue, oficialmente? | 3 — IDEAM, capas de cambio |
| ¿Cómo se compara con otros países? | 2 — Hansen |
| ¿Dónde, y lo respalda la autoridad? | 4 — IDEAM, detecciones tempranas |
| ¿Cuánto bosque había disponible? | Línea base de Hansen, común a los cuatro |

---

### 1.3 Unidad de análisis: por qué una celda de 5×5 km y no el píxel nativo

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

### 1.4 Ventana temporal: 2020-01 en adelante, y por qué mensual

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

Se usan **tres** productos de observación de la Tierra —uno de ellos en
dos presentaciones distintas—, más una capa cartográfica auxiliar que no
aporta señal de cambio sino estructura espacial y atributos
administrativos.

| Fuente | Papel en este trabajo | Salida |
|---|---|---|
| Hansen GFC (§2.1) | **Línea base** de bosque **y** fuente de evento anual | `bosque_base_ha` + Panel 2 |
| GFW `gfw_integrated_alerts` (§2.2) | Fuente de evento mensual | Panel 1 |
| IDEAM / SMByC — capas de cambio (§2.3) | Fuente de evento oficial, anual | Panel 3 |
| IDEAM / SMByC — detecciones tempranas (§2.4) | Ubicación oficial, trimestral | Panel 4 |
| DANE — MGN (§2.5) | Estructura espacial y `cod_dane` | Columnas de todos |

Cada subsección describe qué es el producto, cómo se genera, qué se usa
de él y cuáles son sus límites conocidos. La comparación entre las tres
fuentes de evento constituye uno de los **resultados** del trabajo:
cuantifica, celda a celda y año a año, la relación entre una alerta de
disturbio, una hectárea de cobertura perdida y una hectárea oficialmente
deforestada (sección 8).

### 2.1 Hansen Global Forest Change — línea base y pérdida de cobertura

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

### 2.2 Global Forest Watch — alertas de disturbio (mensual)

**Qué es.** Producto de Global Forest Watch / World Resources Institute
(WRI), identificado en su API como `gfw_integrated_alerts`, que combina en
una sola capa con una única escala de confianza **tres** sistemas
independientes de alerta de deforestación:

| Sistema | Sensor | Productor |
|---|---|---|
| GLAD-L | Landsat (óptico, 30 m) | GLAD lab, Universidad de Maryland |
| GLAD-S2 | Sentinel-2 (óptico, 10 m) | GLAD lab, Universidad de Maryland |
| RADD | Sentinel-1 (radar, 10 m) | Wageningen University & Research |

Las alertas de Landsat se remuestrean a 10 m para calzar con las de
Sentinel, lo que evita el doble conteo de alertas superpuestas: cuando dos
sistemas independientes detectan el mismo evento, en vez de sumarse, la
alerta sube de nivel de confianza. La combinación de óptico y radar es
deliberada: el radar atraviesa nubes, lo que reduce el vacío de detección
en las regiones de nubosidad persistente (Amazonía, Pacífico).

**Por qué esta fuente.** Se prefirió un producto **ya integrado** frente a
combinar varios sistemas de alerta a mano: evita que la definición de
"evento" sea una decisión artesanal de esta tesis en vez de una
metodología ya publicada por el equipo que produce los datos.

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

- Al combinar tres sistemas con metodologías de detección distintas
  (óptico de dos resoluciones + radar), la sensibilidad y el sesgo
  geográfico pueden no ser perfectamente homogéneos a lo largo del país —
  por ejemplo, el componente de radar es menos sensible a la nubosidad que
  los sistemas ópticos, lo que puede hacer que el sistema que "gana" la
  detección varíe por región.
- Es agnóstica a la causa del disturbio, igual que Hansen — no distingue
  deforestación de otros tipos de disturbio de vegetación (incendios,
  cosecha agrícola, daño por tormenta).
- Como cualquier sistema de alerta casi en tiempo real, tiene un rezago de
  confirmación: los últimos 1-2 meses de cualquier corrida pueden estar
  subestimados porque parte de sus eventos reales todavía no se han
  confirmado al momento de la descarga.

### 2.3 IDEAM / SMByC — deforestación oficial

**Qué es.** Las capas de *Cambio en la superficie cubierta por bosque
natural* del Sistema de Monitoreo de Bosques y Carbono (SMByC) del IDEAM
son el insumo espacial con que Colombia produce su **cifra oficial de
deforestación**. Se publican como rásteres anuales de ~30 m, en acceso
abierto y sin credencial.

**Por qué importa que esté aquí.** Es la única fuente del proyecto que
mide *deforestación* en sentido estricto —conversión de bosque natural a
otra cobertura, con la definición nacional de bosque— y no un proxy más
amplio. Hansen mide pérdida de cobertura arbórea (incluye cosecha de
plantación e incendio); las alertas de GFW miden disturbio de la
vegetación. Tener la fuente oficial en la misma grilla permite expresar
las otras dos en términos de ella.

**Leyenda de las capas** (según `Contenido_Cambio.txt` del propio
servidor del SMByC):

| Código | Clase |
|---|---|
| 1 | Bosque estable |
| **2** | **Deforestación** — la clase de interés |
| 3 | Sin información (nubosidad) |
| 4 | Regeneración |
| 5 | No bosque estable |

**Periodos, no años calendario.** Cada capa cubre una transición entre
dos composiciones anuales de imágenes (`cambio_2022_2023`), cuya ventana
no coincide con el 1 de enero al 31 de diciembre. La tabla conserva el
periodo como texto en vez de reducirlo a un año: hacerlo afirmaría una
equivalencia temporal que el dato no respalda. La correspondencia con el
año de referencia se verificó empíricamente (ver abajo): `cambio_YYYY_ZZZZ`
corresponde al año **ZZZZ**.

**Validación contra la cifra publicada.** El total nacional de la clase 2
en cada capa se contrastó con la cifra oficial del año correspondiente:

| Capa | Calculado (ha) | Oficial IDEAM (ha) | Razón |
|---|---|---|---|
| `cambio_2020_2021` | 174.100 | 174.103 (2021) | 1,000 |
| `cambio_2021_2022` | 123.515 | 123.517 (2022) | 1,000 |
| `cambio_2022_2023` | 79.255 | 79.256 (2023) | 1,000 |
| `cambio_2023_2024` | 113.606 | 113.608 (2024) | 1,000 |

La diferencia es de 2 a 3 hectáreas sobre totales de 79.000 a 174.000, es
decir 0,002%, atribuible al redondeo del área de píxel. Esto confirma dos
cosas: la convención de nombres de las capas, y que el procedimiento de
agregación de este trabajo reproduce el dato oficial.

**Cobertura de nubes, muy desigual entre periodos.** La superficie
clasificada como "sin información" cae de forma abrupta en la serie:
116.461 ha en 2020-2021 y 148.472 ha en 2021-2022, frente a 648 ha en
2022-2023 y 377 ha en 2023-2024. Los dos primeros periodos tienen, por
tanto, más incertidumbre por vacíos de observación que los siguientes.
Por eso la tabla conserva `sin_info_ha` como columna: permite filtrar o
ponderar las celdas afectadas, dado que un vacío de observación y una
ausencia real de deforestación se registrarían de otro modo igual.

**Qué se usa de este producto:** la clase 2 (deforestación) como variable
principal, y las clases 1, 3, 4 y 5 como contexto y control de calidad.

---

### 2.4 IDEAM / SMByC — detecciones tempranas (DTD)

**Qué es.** Además de las capas anuales consolidadas (§2.3), el SMByC
publica cada trimestre un boletín de **Detecciones Tempranas de
Deforestación** que identifica los núcleos activos del país. Junto al
boletín en PDF distribuye dos capas espaciales: los **puntos** de alerta
individuales y los **polígonos** de los núcleos.

**Qué se usa y por qué.** Los puntos, porque su serie es continua del III
trimestre de 2016 al I de 2026, mientras la de núcleos carece del año
2024 completo en el servidor. Cada punto trae municipio, vereda,
corporación autónoma regional y, cuando aplica, el área protegida del
SINAP donde cae.

**Qué aporta.** Es el único producto **oficial de cadencia sub-anual**
disponible para Colombia:

| Producto | Oficial | Cadencia |
|---|---|---|
| Alertas GFW | No | Mensual |
| Capas de cambio del IDEAM | Sí | Anual |
| **Detecciones tempranas (DTD)** | **Sí** | **Trimestral** |

Su cobertura alcanza las cinco regiones naturales del país (Amazónica,
Andina, Pacífica, Orinoquía y Caribe) y 1 114 municipios, de modo que
resulta utilizable también en la zona andina.

**Unidad de medida.** El conteo de detecciones, no la hectárea. Cada
punto marca un sitio donde el instituto detectó un cambio compatible con
deforestación, sin cuantificar su extensión.

**Limitación principal: los conteos no son comparables entre años.** El
número de puntos publicados crece de forma sostenida mientras la
deforestación oficial disminuye, y la correlación entre ambas series
resulta **negativa**:

| Serie (2021-2024) | Correlación con la cifra oficial |
|---|---|
| Conteo de detecciones DTD | **−0,669** |
| Alertas GFW, en hectáreas | +0,971 |

La sensibilidad de detección del sistema cambió a lo largo de la serie,
de manera que un punto de 2020 y uno de 2025 no representan la misma
cantidad de deforestación. Leer esta columna como serie temporal de
magnitud llevaría a concluir que la deforestación aumentó en un periodo
en que descendió.

**Los usos que el dato sí sostiene:**

1. **Prioridad espacial dentro de un trimestre**: qué municipios y celdas
   concentran las detecciones que el IDEAM publicó ese periodo.
2. **Respaldo institucional**: la afirmación "el IDEAM detectó alertas
   aquí" tiene un peso distinto al de una alerta de un producto global,
   lo que importa en un producto destinado a debida diligencia.
3. **Cruce con áreas protegidas**: el 11,1 % de las detecciones cae
   dentro del SINAP (19 645 de 177 215, sobre los 18 de 25 trimestres
   que traen ese dato informado).

**Alertas y tasa oficial son cifras distintas.** El propio IDEAM advierte
que estas detecciones sirven para priorizar; el INPE hace la misma
advertencia sobre DETER en Brasil. Para 2025, el boletín trimestral
reportó 72 409 ha mientras la capa consolidada arroja del orden de
119 000 ha: la brecha mide cuánto subestima un sistema de alertas frente
al conteo consolidado.

---

### 2.5 Cartografía auxiliar (DANE) — no aporta señal de cambio

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
| 0 | **Cuatro paneles separados** (alertas GFW, pérdida Hansen, deforestación IDEAM, detecciones tempranas IDEAM) sobre la misma grilla, en vez de una sola tabla con las fuentes como columnas | Una tabla única con todas las fuentes; quedarse con una sola y descartar las demás | Miden conceptos distintos (*disturbio* / *pérdida de cobertura* / *deforestación* / *detecciones*) y tienen unidades temporales distintas (mes / año calendario / transición entre composiciones de imágenes / trimestre). Ponerlas en una misma fila bajo una columna "año" afirmaría una equivalencia temporal que el dato no respalda. Y descartar fuentes perdería capacidades que solo una tiene: cadencia mensual (GFW), comparabilidad internacional (Hansen), validez oficial de la magnitud (capas de cambio del IDEAM) y respaldo oficial sub-anual de la ubicación (detecciones tempranas) | Toda comparación entre paneles exige un `join` explícito y declarar el desfase temporal. Se acepta a cambio de no falsear la alineación de periodos |
| 0b | **El denominador de cada panel corresponde a su propio numerador** | Un único denominador para todo (el de Hansen, o el del IDEAM) | El denominador debe **contener** al numerador. Verificado empíricamente: con el bosque del IDEAM como denominador de las alertas, 843 celdas darían tasas superiores al 100 % (máximo 130,3), porque las alertas se disparan también fuera del bosque natural; con el de Hansen, ninguna. A la inversa, dividir la deforestación oficial entre el bosque de Hansen —que incluye plantaciones— subestima la tasa entre un 30 % y un 45 % | El panel del IDEAM lleva dos columnas de bosque y hay que elegir bien cuál usar. Se documenta de forma explícita en la propia tabla, en la guía y en la sección 8 |
| 1 | Fuente del evento: producto integrado de GFW (`gfw_integrated_alerts`) | Combinar a mano, por separado, cada uno de los sistemas de alerta que este producto ya integra (sección 2.2); usar un producto de un solo sensor; usar Hansen anual | El producto integrado ya es una metodología publicada por el equipo que produce los datos: evita que la fusión de sensores sea una decisión artesanal de esta tesis. Cubre la ventana completa 2020-presente con cadencia casi en tiempo real, algo que un producto anual no permite | Al combinar sistemas con sensibilidades distintas, la homogeneidad metodológica interna del evento es algo menor que la de un solo sensor — aceptado a cambio de mejor cobertura de detección (el radar complementa al óptico bajo nubes) |
| 1b | Fuente oficial: capas rásteres de cambio del SMByC, agregadas por celda | Usar solo la cifra nacional o departamental publicada en los informes del IDEAM; prescindir del IDEAM | Las capas rásteres permiten llevar el dato oficial a la misma celda de 5 km que las otras dos fuentes, en vez de quedarse en un agregado nacional. La agregación se validó contra la cifra publicada y la reproduce al 99,75 % (sección 8), lo que confirma de paso la convención de nombres de las capas | Los periodos son transiciones entre composiciones de imágenes, no años calendario, y hay que declararlo en todo cruce. Además el dato llega con rezago de publicación |
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
  humana en el sentido estricto. Lo que registra `area_def_ha` es, con
  precisión, *área con alerta de disturbio de alta confianza*.
- **Posible confusión con plantaciones forestales de rotación corta** en
  la línea base de Hansen (sección 2.1).
- **Al combinar tres sistemas de detección** (sección 2.2), la
  sensibilidad no es perfectamente homogénea a lo largo del país.
- **Sin validación de campo local**: la precisión reportada de ambos
  productos proviene de sus respectivas validaciones globales/regionales,
  no de un ejercicio de verificación específico para Colombia dentro de
  esta tesis.
- **El desbalance de clases es marcado** (ver sección 8 y
  en el análisis exploratorio): cualquier modelo posterior debe tratar esto
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
| IDEAM — capas de cambio de bosque (SMByC) | Datos abiertos del Estado colombiano, publicados bajo el marco de la Ley 1712 de 2014 (transparencia y acceso a la información pública). El propio marco define los datos abiertos como información *"bajo licencia abierta y sin restricciones legales para su aprovechamiento"*. **No se encontró una licencia con nombre propio (tipo CC BY) declarada específicamente para estas capas rásteres**, a diferencia de Hansen o el DANE | Muy probablemente permitido, por el marco de datos abiertos — **confirmar con el IDEAM antes de comercializar** | Atribución al IDEAM / Sistema de Monitoreo de Bosques y Carbono, citando el año de la capa. Dado que es la fuente oficial del país, conviene además dejar claro en cualquier producto derivado que el IDEAM no avala ni valida el análisis propio |
| DANE — Marco Geoestadístico Nacional | CC BY 4.0 | Permitido | Atribución, en las palabras del propio DANE: *"Departamento Administrativo Nacional de Estadística - DANE: www.dane.gov.co"* |
| GFW / GLAD-L / GLAD-S2 / RADD (evento) | CC BY 4.0 (confirmado para GFW en general y para RADD directamente desde Wageningen University; GLAD-L es muy probablemente el mismo caso — mismo laboratorio que Hansen GFC — pero no se encontró una página que lo confirme en esas palabras exactas específicamente para GLAD-L) | Permitido | Atribución por dataset; GFW advierte que "cada dataset tiene su propia licencia", así que conviene guardar un archivo de atribuciones junto a las tablas publicadas |
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

## 8. Cómo se ven las unidades de observación finales

*(Números de la corrida de referencia.)*

El pipeline produce **cuatro paneles** en `datos/panel/`, cada uno en
`.csv` y `.parquet`. Los cuatro cubren exactamente las mismas **44 616
celdas** (32 departamentos, 1 114 municipios), con la misma línea base de
bosque —**77 713 177 ha** según Hansen— y el mismo cruce municipal. Esa
coincidencia se sigue del diseño: los cuatro usan el mismo cálculo de
bosque base y el mismo indexado de píxel a celda, y es lo que los hace
comparables.

| Panel | Unidad de observación | Filas | Columnas |
|---|---|---|---|
| `panel_deforestacion_colombia` | celda × mes (79 periodos, 2020-01 a 2026-07) | 3 524 664 | 19 |
| `panel_hansen` | celda × año (6 años, 2020-2025) | 267 696 | 9 |
| `panel_ideam` | celda × periodo (5 transiciones, 2020-2021 a 2024-2025) | 223 080 | 14 |
| `panel_dtd` | celda × trimestre (25 trimestres, 2020-T1 a 2026-T1) | 1 115 400 | 13 |

En el panel de alertas, `filas = celdas × periodos` exactamente: es un
rectángulo perfecto, sin huecos, que es la condición para modelar. Área
con alerta 1 085 131 ha, 28,01 % de las celda-mes con evento.

### Qué reporta cada fuente, lado a lado

| Año | GFW alerta (ha) | Hansen pérdida (ha) | IDEAM def. (ha) | Oficial IDEAM (ha) | Hansen/IDEAM | GFW/IDEAM |
|---|---|---|---|---|---|---|
| 2021 | 195 833 | 265 200 | 173 663 | 174 103 | 1,53 | 1,13 |
| 2022 | 172 082 | 266 168 | 123 204 | 123 517 | 2,16 | 1,40 |
| 2023 | 122 362 | 197 246 | 78 982 | 79 256 | 2,50 | 1,55 |
| 2024 | 156 640 | 213 785 | 113 423 | 113 608 | 1,88 | 1,38 |
| 2025 | 144 843 | 186 697 | 119 282 | *(sin publicar)* | 1,57 | 1,21 |

El panel del IDEAM recupera entre el **99,65 % y el 99,84 %** de la cifra
oficial publicada; lo que falta son celdas por debajo de
`bosque_minimo_ha`, excluidas por el filtro de dominio que los cuatro
paneles aplican por igual. Esta correspondencia **valida el procedimiento
de agregación zonal** contra una cifra externa: no se asume que reproduce
el dato oficial, se comprueba.

### Cómo leer las razones entre fuentes

Cada razón **mide la distancia entre un proxy y el concepto oficial**:

- **Hansen/IDEAM (1,53 a 2,50)**: Hansen cuenta pérdida de cobertura
  arbórea, que incluye cosecha de plantación forestal, incendio y daño
  natural, ninguno de los cuales es deforestación en sentido estricto.
- **GFW/IDEAM (1,13 a 1,55)**: las alertas señalan disturbio, que además
  incluye eventos que no llegan a ser conversión de uso del suelo.

**Ambas razones varían año a año.** La implicación metodológica es
directa: **la conversión entre fuentes exige un factor específico para
cada año**, y aplicar un coeficiente constante produciría errores de
decenas de miles de hectáreas. Mantener los paneles sobre la misma
grilla permite estimar esa relación empíricamente en lugar de suponerla.

### Dos definiciones de bosque, y cuál usar en cada caso

El panel del IDEAM lleva **dos** columnas de bosque disponible, y no son
intercambiables:

| Columna | Definición | Total nacional |
|---|---|---|
| `bosque_base_ha` | Hansen: dosel ≥ `umbral_dosel`, plantaciones incluidas | 77 713 177 ha |
| `bosque_ideam_ha` | IDEAM: bosque natural, definición nacional | 59 294 546 ha |

**El mismo territorio, el mismo año, una diferencia del 31 %.** La brecha
proviene de la definición de la palabra "bosque": Hansen cuenta como
bosque cualquier píxel con dosel suficiente, incluidas plantaciones
forestales y rastrojo alto, mientras la definición nacional de bosque
natural los excluye.

La regla, formalizada en la decisión 0b de la sección 4, es que **el
denominador debe contener al numerador**:

| Panel | Denominador correcto | Por qué |
|---|---|---|
| Alertas GFW | `bosque_base_ha` | Las alertas se disparan también fuera del bosque natural. Con el denominador del IDEAM, **843 celdas darían tasas superiores al 100 %** (máximo observado 130,3); con el de Hansen, ninguna |
| Hansen | `bosque_base_ha` | Numerador y denominador salen del mismo producto: son internamente consistentes |
| IDEAM | `bosque_ideam_ha` | `def_ha` cuenta solo bosque natural destruido. Dividirlo entre el bosque de Hansen mezcla definiciones y **subestima la tasa entre un 30 % y un 45 %** |

`bosque_base_ha` se conserva en los cuatro paneles pese a lo anterior,
porque es lo que garantiza que cubran el mismo conjunto de celdas y
permite compararlos sobre un denominador común.

La descripción columna por columna de los cuatro paneles, con ejemplos de
cómo inspeccionarlos en `pandas`, está en
[GUIA_CODIGO.md, sección 4](GUIA_CODIGO.md#4-cómo-se-ven-las-cuatro-tablas).

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
- Global Forest Watch / World Resources Institute. *Integrated
  Deforestation Alerts* (`gfw_integrated_alerts`) — integra GLAD-L,
  GLAD-S2 y RADD. https://www.globalforestwatch.org — ficha técnica y
  metadatos consultables vía
  `https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts`
- Reiche, J., et al. *RADD — Radar for Detecting Deforestation*,
  Wageningen University & Research. (Verificar la cita exacta del paper
  antes de usarla en la tesis.)
- IDEAM. *Sistema de Monitoreo de Bosques y Carbono (SMByC) — Cambio en
  la superficie cubierta por bosque natural*. Capas rásteres anuales en
  acceso abierto:
  https://bart.ideam.gov.co/smbyc/ — la leyenda de clases está en el
  archivo `Contenido_Cambio.txt` del propio directorio de capas.
  Cifras oficiales de deforestación por año en los comunicados del
  SMByC (verificar el comunicado del año que se cite).
- DANE. *Marco Geoestadístico Nacional*.
  https://www.dane.gov.co
