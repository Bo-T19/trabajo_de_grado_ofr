# Metodología — Panel espacio-temporal de deforestación en Colombia

Este documento explica **qué se midió, con qué datos, por qué esos datos y no
otros, qué operaciones matemáticas se les aplicaron, y qué supuestos y
limitaciones se heredan de esas decisiones**. Es la contraparte conceptual de
[GUIA_CODIGO.md](GUIA_CODIGO.md), que explica cómo correr el software que
implementa esta metodología. Este documento se puede leer sin abrir una línea
de código.

**Cómo está organizado**: primero el diseño general (sección 1), luego cada
fuente de datos en profundidad — qué es, cómo se produjo, por qué se eligió,
qué limitaciones trae (sección 2) —, después el aparato conceptual que cruza
esas fuentes píxel a píxel hasta llegar al panel final, con las fórmulas
exactas (sección 3), luego una bitácora explícita de decisiones de diseño con
sus alternativas descartadas (sección 4), los supuestos del estudio (sección
5), limitaciones conocidas (sección 6), **restricciones de licencia y uso
comercial de cada fuente** (sección 7 — relevante porque este panel es
insumo de consultorías comerciales, no solo un ejercicio académico), un
vistazo a la unidad de observación final (sección 8), glosario (sección 9)
y referencias (sección 10).

---

## 1. Diseño general

### 1.1 Pregunta que responde el panel

El pipeline no mide "cuánta deforestación tuvo Colombia" como un número único:
construye una tabla donde cada fila es **una unidad espacial, en un momento
dado**, con la deforestación ocurrida ahí y entonces. Esa estructura —panel de
datos, en el sentido econométrico: una dimensión espacial (o de sección
cruzada) cruzada con una dimensión temporal— es la que permite luego preguntas
como "¿qué características de una celda predicen que se deforeste el próximo
mes?", que es lo que un corte transversal único no puede responder.

### 1.2 Unidad de análisis: por qué una celda de 5×5 km y no el píxel nativo

Los dos productos satelitales fuente tienen resolución nativa de 30×30 m (0.09
ha por píxel). En principio, el panel podría construirse a esa resolución. No
se hizo así, por dos razones que están relacionadas:

1. **Volumen computacional.** Colombia continental tiene del orden de
   1 200 000 km² de bosque potencial, es decir del orden de 1.3×10⁹ píxeles de
   30 m. Multiplicado por 43 meses de ventana temporal, un panel a resolución
   nativa tendría más de 5×10¹⁰ filas — inviable de manipular con las
   herramientas de este pipeline (`pandas`/`numpy` en un computador personal),
   y probablemente también para cualquier modelo posterior.

2. **Señal estadística.** La probabilidad de que un píxel individual de 0.09 ha
   se deforeste en un mes dado es extremadamente baja incluso en zonas de alta
   presión: el fenómeno es de naturaleza rara y espacialmente agregada (la
   deforestación ocurre en frentes, no dispersa uniformemente). Un panel a
   resolución de píxel sería un problema de clasificación extremadamente
   desbalanceado (más aún que el ya desbalanceado panel a 5 km, ver sección
   8) y muy ruidoso: un solo píxel mal clasificado por el algoritmo fuente
   (nube, sombra, cuerpo de agua estacional) pesa igual que un evento real.

Agregar a 5×5 km (2 500 ha por celda) resuelve ambos problemas: reduce el
panel a un tamaño manejable (~44 500 celdas × 43 meses ≈ 1.9 millones de
filas, ver sección 8) y cada celda acumula suficientes píxeles como para que
un error de clasificación aislado en uno de ellos no domine la señal. El
costo es resolución espacial: dentro de una celda de 5 km no se puede ubicar
dónde exactamente ocurrió el evento, solo que ocurrió en esa celda. Se
considera un costo aceptable porque el objetivo es modelar **patrones y
predictores** de la deforestación, no cartografiarla con precisión de
parcela — para eso ya existen los productos fuente en su resolución nativa.

**Alternativa descartada**: agregar por unidad administrativa (municipio).
Se descartó porque los municipios colombianos varían enormemente en área (de
decenas a más de 10 000 km²), lo que introduce heterogeneidad artificial en
la exposición de cada unidad y complica la interpretación de una tasa. Una
grilla regular da unidades de área comparable en todo el país.

### 1.3 Ventana temporal: por qué 2023-01 en adelante, y por qué mensual

**Esta sección describe el panel DIST-ALERT** (`fuente_dist_alert/`). El
pipeline produce, aparte, un segundo panel completamente independiente con
la fuente GFW (`fuente_gfw/`), que cubre 2020-01 en adelante sobre la misma
grilla y con la misma lógica de agregación — ver sección 2.4 y decisión 15
(sección 4) para el porqué de mantener dos paneles separados en vez de
fusionarlos en uno solo.

La ventana temporal del panel DIST-ALERT (`fecha_inicio = 2023-01-01`) está
determinada por la disponibilidad real del producto DIST-ALERT sobre
Colombia — verificado empíricamente contra el catálogo real de NASA CMR:
cero gránulos en cualquier parte del mundo antes de esa fecha (decisión 1).
Quien necesite la ventana completa desde 2020 debe usar el panel GFW, no
este. La resolución mensual (`frecuencia = "MS"`) es un
punto medio entre:

- **Resolución más fina** (p. ej. semanal): daría más granularidad temporal,
  pero DIST-ALERT no garantiza una observación limpia (sin nubes) de cada
  tile cada semana, y el panel quedaría con más ceros artificiales por falta
  de datos, no por ausencia real de deforestación.
- **Resolución más gruesa** (p. ej. anual): perdería la capacidad de
  encadenar rezagos y estacionalidad de corto plazo, que es justamente lo que
  un panel mensual permite explotar (ver `lag_k_ha` y `media_movil_3` en la
  sección 3.7).

---

## 2. Fuentes de datos

Se cruzan **dos** productos satelitales independientes —cada uno responde una
pregunta distinta— más **tres** capas cartográficas auxiliares que no aportan
señal de cambio, solo estructura espacial y atributos administrativos.

### 2.1 Hansen Global Forest Change (GFC) — la línea base

**Qué es.** Producto global de cobertura y cambio de bosque a 30 m de
resolución, desarrollado por el Global Land Analysis and Discovery (GLAD) lab
de la Universidad de Maryland en colaboración con Google, publicado
originalmente en Hansen et al. (2013) y actualizado anualmente desde
entonces (ver sección 10, referencias). Es probablemente el producto de
cobertura forestal más usado en la literatura de deforestación global —entre
otras razones porque es gratuito, de cobertura mundial y homogéneo (mismo
algoritmo aplicado a todo el planeta, lo que hace comparables los resultados
entre países).

**Cómo se produce (resumen).** Hansen et al. entrenan un modelo de árboles de
decisión (con *bagging*) sobre series temporales de reflectancia Landsat para
clasificar, año a año, si un píxel sufrió una pérdida de cobertura arbórea de
tipo "reemplazo de rodal" (*stand-replacement disturbance* — el píxel deja de
tener estructura de bosque, sin importar la causa: tala, incendio, plaga,
fenómeno natural). La capa de cobertura del año 2000 (`treecover2000`) se
deriva de un modelo de regresión que relaciona reflectancia Landsat con
porcentaje de cobertura de dosel, calibrado contra datos de referencia de
alta resolución.

**Qué se usa de este producto** (dos capas, de las que trae el producto):

| Capa | Qué mide | Cómo se usa aquí |
|---|---|---|
| `treecover2000` | % de cobertura de dosel arbóreo en el año 2000, por píxel | Umbral para decidir si un píxel *era* bosque en el año base |
| `lossyear` | Año (codificado 1–24 → 2001–2024) en que el píxel perdió cobertura, si la perdió | Descuenta del bosque base los píxeles que ya se sabía que habían perdido cobertura antes del inicio de la ventana de observación con DIST-ALERT |

**Por qué Hansen y no otra fuente de línea base.** Se consideraron dos
alternativas:

- **IDEAM/SMByC** (el sistema oficial colombiano de monitoreo de bosques):
  tiene la ventaja de ser la fuente "oficial" del país, pero su resolución
  temporal de publicación es más lenta y su formato/cobertura no siempre es
  directamente descargable de forma programática y reproducible fuera de
  Colombia — importante porque este pipeline está pensado para poder
  correrse por terceros (el director de tesis, un evaluador) sin gestionar
  accesos adicionales.
- **MapBiomas Colombia**: cobertura de uso del suelo multi-clase, muy rica,
  pero pensada para clasificación de coberturas, no específicamente
  optimizada para detectar el evento binario "pérdida de bosque" con la
  validación extensa que tiene Hansen GFC.

Hansen GFC se eligió por ser **gratuito, descargable por HTTP sin
autenticación, de cobertura y método homogéneos, y ampliamente validado en la
literatura** (lo que facilita comparar los resultados de esta tesis con
otros estudios que también usan Hansen como línea base).

**Limitaciones conocidas de Hansen GFC** (heredadas por este pipeline):

- No distingue la **causa** de la pérdida (tala para agricultura, incendio,
  plaga, evento natural) — es agnóstico al proceso, solo detecta el cambio
  estructural.
- Puede confundir plantaciones forestales de rotación corta (que se talan y
  vuelven a plantar cíclicamente) con deforestación real; en zonas con
  plantaciones comerciales esto puede sobreestimar el "bosque" de partida si
  las plantaciones no se filtran aparte (este pipeline no hace ese filtro).
- La capa `lossyear` tiene una resolución temporal **anual**: no permite saber
  *en qué mes* del año se perdió un píxel — otra razón por la que este
  pipeline usa Hansen solo para la línea base (dónde había bosque) y no
  para el evento que se quiere fechar mensualmente (ver sección 2.2).

### 2.2 NASA OPERA DIST-ALERT — el evento a detectar

**Qué es.** Producto de detección casi en tiempo real de disturbios de
vegetación, parte de la suite "Land Disturbance" del proyecto OPERA
(*Observational Products for End-Users from Remote Sensing Analysis*), un
proyecto de la NASA operado por el JPL que reprocesa observaciones de
satélites existentes en productos estandarizados y de fácil consumo. DIST-ALERT
se calcula sobre HLS (*Harmonized Landsat Sentinel-2*), es decir sobre
observaciones combinadas de la constelación Landsat 8/9 y Sentinel-2A/B/C
armonizadas radiométrica y geométricamente — la combinación de ambas
constelaciones es lo que le da a HLS (y por lo tanto a DIST-ALERT) una
cadencia de revisita mucho más alta (días, no semanas) que usar Landsat solo.

**Cómo se produce (resumen, con la evidencia disponible).** Cada gránulo de
DIST-ALERT trae, además de las dos capas que usa este pipeline, otras 17: entre
ellas `VEG-IND` (el valor actual de un índice de vegetación), `VEG-HIST`
(estadística histórica de referencia de ese índice para ese píxel, calculada
sobre observaciones previas) y `VEG-ANOM` (la anomalía: cuánto se desvía la
observación actual de esa referencia histórica), además de `VEG-DIST-CONF`
(confianza de la detección), `VEG-DIST-COUNT` y `VEG-DIST-DUR` (número de
observaciones y duración durante las cuales se ha visto la anomalía). Esta
estructura de bandas —confirmada directamente contra el catálogo real vía
`diagnostico_cmr.py` (ver `cmr.txt` en la raíz del proyecto)— es consistente
con el patrón estándar en la literatura de teledetección de cambios: se
mantiene una línea base histórica del índice de vegetación por píxel, se
marca una observación como "anómala" si cae por debajo de esa referencia en
una magnitud dada, y una alerta pasa de *provisional* a *confirmada* solo
cuando la anomalía se repite en observaciones sucesivas — un patrón análogo,
conceptualmente, al usado por otras alertas de disturbio casi en tiempo real
como GLAD-S2 o RADD. **Aviso metodológico**: esta descripción es una
reconstrucción razonada a partir de la estructura de bandas del producto y de
la práctica estándar del campo, no una cita textual del algoritmo interno de
OPERA. Para la tesis, si se necesita describir el algoritmo con precisión
técnica exacta (p. ej. qué índice espectral usa `VEG-IND`, o el umbral
estadístico exacto de confirmación), se debe citar el *Algorithm Theoretical
Basis Document* (ATBD) oficial del producto DIST-ALERT, disponible desde la
página del producto en Earthdata (ver sección 10).

**Las dos capas que usa este pipeline** (de 19 totales por gránulo):

| Capa | Qué es | Rol en el pipeline |
|---|---|---|
| `VEG-DIST-STATUS` | Código de estado de la alerta, por píxel (tabla completa abajo) | Define si un píxel cuenta como "evento" |
| `VEG-DIST-DATE` | Fecha real del disturbio, en días desde el 2020-12-31 | Define **a qué mes** se atribuye el evento |

**Códigos de `VEG-DIST-STATUS`** (documentación del producto):

```
0    sin perturbación
1    primera detección,  pérdida de señal <50%
2    provisional,        pérdida de señal <50%
3    confirmada,         pérdida de señal <50%
4    primera detección,  pérdida de señal ≥50%
5    provisional,        pérdida de señal ≥50%
6    confirmada,         pérdida de señal ≥50%   (disturbio EN CURSO)
7    confirmada <50%,    disturbio FINALIZADO (vegetación se recuperó o dejó de monitorearse)
8    confirmada ≥50%,    disturbio FINALIZADO
255  sin dato (nubes, sombra, fuera de cobertura)
```

Aquí "pérdida de señal" se refiere a la magnitud de la anomalía del índice de
vegetación (`VEG-ANOM`) respecto a la línea base histórica del píxel
(`VEG-HIST`) — **no** es directamente comparable al "% de cobertura de dosel"
que usa Hansen GFC; son dos variables de naturaleza distinta que casualmente
comparten la idea de un umbral al 50%, y no deben confundirse.

**Por qué DIST-ALERT y no otro producto de alertas.** Se consideraron:

- **GLAD alerts** (también de la Universidad de Maryland): basadas en Landsat
  únicamente, cadencia de revisita más baja que HLS (al no combinar
  Sentinel-2), lo que en zonas de alta nubosidad (buena parte de la Amazonía
  y el Pacífico colombianos) retrasa más la confirmación de un evento.
- **RADD alerts** (Wageningen University, basadas en radar Sentinel-1): la
  gran ventaja del radar es que atraviesa nubes, pero a costa de una
  resolución espacial menor y de un tipo de señal (retrodispersión de radar)
  con su propio conjunto de falsos positivos (lluvia intensa, inundación
  estacional) distinto al de una señal óptica; combinar dos tipos de sensor
  distintos (óptico para línea base, radar para el evento) habría complicado
  la interpretación conjunta.

DIST-ALERT se eligió por: (a) mejor cadencia temporal que Landsat-solo gracias
a HLS, (b) acceso programático estandarizado vía NASA CMR/`earthaccess`
(clave para que el pipeline sea reproducible sin descargas manuales), y (c)
ser un producto relativamente reciente y activamente mantenido por la NASA,
con expectativa de continuidad operacional a mediano plazo.

**Limitaciones conocidas de DIST-ALERT** (heredadas por este pipeline):

- Depende de observaciones ópticas limpias: en zonas de nubosidad persistente,
  el tiempo entre observaciones útiles crece, y por lo tanto también el
  tiempo que tarda una alerta en pasar de *provisional* a *confirmada* — esto
  no introduce un sesgo en la fecha atribuida (que viene de `VEG-DIST-DATE`,
  la fecha real del evento, no de la instantánea), pero sí implica que un
  evento reciente en una zona muy nublada puede tardar más meses en aparecer
  como "confirmado" en el panel, generando lo que en la literatura de
  vigilancia epidemiológica se llama *reporting lag*: los últimos 1-2 meses
  de la ventana temporal del panel están sistemáticamente subestimados
  porque parte de sus eventos reales aún no se han confirmado al momento de
  la descarga.
- Es agnóstico a la causa del disturbio, igual que Hansen — no distingue
  deforestación de otros tipos de disturbio de vegetación (incendios en
  pastizales, cosecha agrícola, daño por tormenta).
- El umbral de "pérdida de señal ≥50%" es una decisión de diseño **de este
  pipeline** (ver decisión 3 en la sección 4), no del producto en sí — el
  producto ofrece también los códigos <50%, que aquí se descartan
  deliberadamente.

### 2.3 Cartografía auxiliar (no aporta señal de cambio, solo estructura)

| Fuente | Uso | Por qué esta y no otra |
|---|---|---|
| DANE — Marco Geoestadístico Nacional (MGN) 2023, nivel departamento | Recorta la grilla al territorio continental de Colombia y etiqueta cada celda con su departamento | Fuente oficial colombiana, servida como *Feature Service* público de ArcGIS (sin autenticación), licencia **CC BY 4.0** (uso comercial permitido con atribución). Reemplazó a los assets de Earth Engine `USDOS/LSIB_SIMPLE/2017` y `FAO/GAUL_SIMPLIFIED_500m` — ver decisión 11 revisada en la sección 4: se abandonó Earth Engine porque su licencia gratuita prohíbe explícitamente el uso en trabajo remunerado para terceros, y este panel es insumo de consultorías comerciales del Observatorio |
| DANE — Marco Geoestadístico Nacional (MGN), municipal | Cruce **opcional** por centroide para obtener el código de municipio (`cod_dane`) | Misma fuente, mismo motivo que la fila anterior; es la fuente oficial para unir variables socioeconómicas o de crédito rural del Observatorio. Opcional porque requiere descargar el shapefile municipal aparte |

Ninguna de estas dos fuentes contribuye información temporal ni de cambio:
solo definen **dónde** está cada celda y **cómo se llama** administrativamente.
Ahora ambas vienen de la misma institución (DANE), lo que además simplifica
la atribución del panel final a una sola fuente cartográfica en vez de dos.

### 2.4 GFW Integrated Disturbance Alerts — el evento del panel GFW (2020-presente)

**Panel independiente, no un relleno.** Esta fuente no se usa para
completar un tramo faltante del panel DIST-ALERT: alimenta un **segundo
panel completo, separado, que nunca se combina con el de DIST-ALERT**
(`fuente_gfw/descargar_gfw.py` → `datos/crudo/nacional_gfw.csv` →
`panel_deforestacion_colombia_gfw.csv`). Quien necesite datos desde
2020-01 usa este panel para **toda** la ventana temporal, no solo para
2020-2022; quien solo necesite 2023 en adelante usa el panel DIST-ALERT,
que sigue siendo la opción de referencia por depender de un solo sistema
de detección en vez de cuatro integrados. Ver decisión 15 (sección 4)
para el razonamiento completo de por qué se descartó fusionar las dos
fuentes en un único panel híbrido.

**Qué es.** Producto de Global Forest Watch / World Resources Institute
(WRI) que combina, en una sola capa con una única escala de confianza,
**cuatro** sistemas independientes de alerta de disturbio: DIST-ALERT
(NASA OPERA), GLAD-L (Landsat, UMD), GLAD-S2 (Sentinel-2, UMD) y RADD
(radar Sentinel-1, Wageningen University). Metodología publicada y
revisada por pares: Pickens, Hansen, Song et al., *"Rapid monitoring of
global land change"*, Nature Communications 16, 8948 (2025).

**Por qué esta fuente para el panel 2020-presente.** DIST-ALERT no tiene
datos antes de 2023-01 (verificado empíricamente contra el catálogo real
de NASA CMR — cero gránulos en cualquier parte del mundo antes de esa
fecha, ver decisión 1), así que no puede alimentar un panel que arranque
en 2020. De las alternativas con más historia (GLAD-L, GLAD-S2, RADD por
separado), se prefirió el producto **ya integrado** en vez de que este
pipeline combinara las tres fuentes a mano: evita que la definición de
"evento" sea una decisión artesanal de esta tesis en vez de una
metodología ya publicada y validada por el equipo que produce los datos.

**Cómo se accede.** A diferencia de DIST-ALERT (archivos GeoTIFF
descargables por tile), este producto se consulta mediante una API SQL
de solo lectura (`data-api.globalforestwatch.org`) que corre la consulta
directamente sobre el dato raster, celda por celda de la grilla, y
devuelve resultados ya agregados — no hace falta descargar ni reproyectar
ningún ráster de evento para esta fuente (la línea base de bosque sí se
sigue calculando localmente con Hansen, ver más abajo). El área en
hectáreas la calcula la propia API (campo `area__ha`), no una constante
fija como en DIST-ALERT: este producto usa una cuadrícula en grados
(EPSG:4326), y el área real de un píxel de tamaño angular fijo varía con
la latitud — sumar `area__ha` directamente delega esa corrección en la
fuente, en vez de asumir un tamaño de píxel único para todo el país.

**Definición de evento — analogía con DIST-ALERT.** El producto expone
una escala de confianza de tres niveles (`nominal`, `high`, `highest`),
conceptualmente equivalente a la distinción "provisional vs. confirmada"
de DIST-ALERT. Siguiendo el mismo criterio que la decisión 2 (excluir
detecciones sin confirmar), este pipeline cuenta como evento solo
`high` y `highest`, descartando `nominal` — ver `gfw_confianza_minima`
en `config_local.py` y la decisión 13 en la bitácora (sección 4).

**Línea base de bosque propia (`anio_mascara_gfw = 2019`).** El panel GFW
calcula su propio `bosque_ha` por celda reutilizando el mismo código que
el panel DIST-ALERT (`indice_celdas()`/`mascara_bosque()` de
`zonal_local.py`), pero con el corte de Hansen un año antes (2019 en vez
de 2022), porque su ventana de eventos arranca en 2020-01, no en 2023-01
— ver decisión 5 revisada (sección 4). Esto **no** es mezclar fuentes de
evento: Hansen es, por diseño, una línea base estática compartida (sección
2.1); lo único que se reutiliza del panel DIST-ALERT es la cuadrícula
geométrica de los tiles ya descargados, nunca su contenido
`VEG-DIST-STATUS`/`VEG-DIST-DATE`.

**Limitaciones conocidas de esta fuente** (adicionales a las ya
mencionadas para DIST-ALERT, que en gran medida heredan aquí porque
DIST-ALERT es uno de los cuatro componentes integrados):

- Al combinar cuatro sistemas con metodologías de detección distintas
  (óptico de dos resoluciones + radar), la sensibilidad y el sesgo
  geográfico pueden no ser perfectamente homogéneos a lo largo de toda la
  ventana que cubre esta fuente — por ejemplo, RADD (radar) es menos
  sensible a la nubosidad que los sistemas ópticos, lo que puede hacer
  que la mezcla de fuentes que "gana" la detección varíe por región.
- El panel GFW y el panel DIST-ALERT miden el mismo fenómeno con
  metodologías distintas y **no son directamente comparables número a
  número** para el tramo en que ambos existirían (2023 en adelante,
  aunque el panel DIST-ALERT es el que se recomienda para ese tramo).
  Esta es precisamente la razón por la que no se fusionan (decisión 15):
  cualquier comparación entre los dos debe hacerse de forma explícita y
  documentada (p. ej. en `eda_deforestacion.ipynb`), nunca como una
  transición silenciosa dentro de un mismo panel.

---

## 3. Marco conceptual: de píxeles a panel

Esta sección formaliza, con notación explícita, las operaciones que el código
(`zonal_local.py`, `consolidar.py`) implementa. El detalle de *cómo* está
programado cada paso está en [GUIA_CODIGO.md](GUIA_CODIGO.md); aquí se explica
*qué* calcula matemáticamente y por qué esa es la operación correcta.

### 3.1 El espacio de píxeles

Sea `p` un píxel de 30×30 m de un tile MGRS de DIST-ALERT. Cada píxel tiene
asociado:

- una posición geográfica, heredada de la cuadrícula del tile (proyección UTM
  nativa de ese tile),
- un valor de `treecover2000` y `lossyear` (de Hansen, tras reproyectarlo a
  esa misma cuadrícula — ver 3.6),
- una secuencia temporal de observaciones DIST-ALERT, una por instantánea
  descargada (aproximadamente una por mes): `estado(p, s)` y `fecha(p, s)`
  para cada instantánea `s`.

### 3.2 Máscara de bosque — definición formal

Un píxel `p` se considera **bosque disponible al inicio del análisis** si y
solo si:

```
bosque(p) = [ treecover2000(p) ≥ 30 ]  AND  NOT ( 0 < lossyear(p) ≤ (anio_mascara − 2000) )
```

con `anio_mascara = 2022` para el panel DIST-ALERT. En palabras: tenía al
menos 30% de cobertura de dosel en el año 2000, **y** si perdió esa
cobertura según Hansen, la perdió **antes** de 2023 (es decir, ya estaba
perdida antes de que arranque la ventana de observación de DIST-ALERT). Los
píxeles con `lossyear` en 2023 o después **no** se descuentan aquí — esa
pérdida es, por diseño, la que debe detectar DIST-ALERT, no Hansen (ver
decisión 5 en la sección 4, sobre por qué no se solapan Hansen y la fuente
de evento).

El panel GFW aplica exactamente la misma fórmula pero con
`anio_mascara_gfw = 2019`, un año antes de que arranque su propia ventana
de eventos (2020-01) — mismo principio, corte distinto porque cada panel
tiene su propia ventana (ver sección 2.4 y decisión 15).

El umbral del 30% de cobertura de dosel es el umbral más usado en la
literatura para operacionalizar "bosque" a partir de datos de cobertura
continua (es, entre otros, uno de los umbrales de referencia usados por la
FAO para definiciones de bosque comparables entre países), lo que facilita
comparar los resultados de esta tesis con otros estudios.

### 3.3 Evento de deforestación confirmada — definición formal

Para una instantánea `s` (aproximadamente, un mes calendario) y un píxel `p`:

```
nuevo(p, s) = [ estado(p, s) ∈ {6, 8} ]  AND  bosque(p)  AND  NOT contado_antes(p, s)
```

donde `contado_antes(p, s)` es verdadero si `p` ya fue marcado como `nuevo`
en alguna instantánea anterior a `s` (ver 3.4). Solo los píxeles con
`nuevo(p, s) = verdadero` contribuyen al conteo de deforestación.

### 3.4 El problema de la doble contabilización temporal, y cómo se resuelve

Un evento de disturbio no aparece en una sola instantánea de DIST-ALERT y
desaparece: normalmente aparece primero como *provisional* (código 1, 2, 4 o
5), y en instantáneas sucesivas —si la anomalía se sostiene— pasa a
*confirmada, en curso* (código 6), y eventualmente a *confirmada, finalizada*
(código 8). Es decir, **un mismo píxel puede aparecer en estado 6 u 8 en
varias instantáneas sucesivas.** Si simplemente se sumara el conteo de
píxeles en estado {6, 8} de cada instantánea, un solo evento real se contaría
tantas veces como instantáneas lo mostraran activo — sobreestimando
severamente la deforestación total.

La solución implementada es un **conjunto acumulado monótonamente creciente**:
sea `C_t` el conjunto de píxeles ya contados hasta la instantánea `t`
(inclusive). Se recorren las instantáneas **en orden cronológico** y en cada
paso:

```
C_t = C_(t−1) ∪ { p : nuevo(p, t) }
```

Un píxel entra a `C_t` la primera vez que se observa en estado confirmado, y
nunca vuelve a contarse en instantáneas posteriores (`contado_antes` lo
excluye). Este es exactamente el patrón de una variable de "primera
ocurrencia" en análisis de supervivencia/eventos: lo que importa es la
**primera vez** que se cruza el umbral, no cuántas veces se observa después
el estado ya cruzado.

Una vez identificado que un píxel es `nuevo` en la instantánea `t`, **no se le
atribuye el mes de `t`**: se le atribuye el mes que indica su propio valor de
`VEG-DIST-DATE`, decodificado como días desde el 2020-12-31. Esto es
importante porque la fecha de observación (`t`, cuándo se bajó la
instantánea) y la fecha del evento (`VEG-DIST-DATE`, cuándo ocurrió realmente
según el producto) pueden diferir por varios meses — un disturbio iniciado en
marzo puede no confirmarse (pasar a estado 6/8) sino hasta mayo. Atribuirlo a
marzo (la fecha real) en vez de a mayo (la fecha en que se confirmó) es lo
que permite que el panel mensual refleje *cuándo ocurrió* el fenómeno, no
*cuándo el algoritmo tuvo suficiente confianza para reportarlo* — con el
costo, ya mencionado en 2.2, de que los últimos meses de la ventana pueden
estar subestimados porque parte de sus eventos reales aún no se han
confirmado.

**Efecto de inicio de ventana (hallazgo empírico)**: por el mismo mecanismo,
el **primer periodo** de cualquier corrida del pipeline tiende a verse
anormalmente alto — en la corrida usada para este documento, cerca de 9 veces
la mediana del resto de la serie (ver el notebook `eda_deforestacion.ipynb`,
sección 5). La razón es que `C_t` arranca vacío (`C_0 = ∅`): todo píxel que
ya estaba en estado confirmado en la primera instantánea descargada de cada
tile entra de una sola vez a `C_1`, sin importar cuánto tiempo llevara
acumulándose antes de que este pipeline empezara a monitorear. El primer
periodo del panel mide entonces un **stock inicial** heredado del historial
de DIST-ALERT hasta ese punto, no un **flujo mensual** comparable al resto de
la serie. **Recomendación**: excluir el primer periodo de cualquier cálculo
de tasas promedio, estacionalidad, o entrenamiento de un modelo — no es una
observación de la misma naturaleza que las demás.

### 3.5 El problema de la doble contabilización espacial (tiles solapados)

Los tiles MGRS de 100×100 km se traslapan levemente en sus bordes (por diseño
del propio sistema de cuadrícula MGRS, para garantizar cobertura sin huecos).
Un píxel en la franja de traslape aparece en dos tiles distintos, y por lo
tanto se procesa dos veces (una por cada tile). Al combinar los resultados de
todos los tiles sobre la misma grilla de celdas, tanto el bosque base como la
deforestación de cada celda se agregan con el **máximo** entre los tiles que
la cubren, no con la suma:

```
bosque_ha(c) = max sobre todos los tiles que cubren c
área_def_ha(c, t) = max sobre todos los tiles que cubren c, en el periodo t
```

Sumar en vez de tomar el máximo duplicaría tanto el numerador como el
denominador de cualquier tasa calculada sobre las celdas de borde entre dos
tiles — un error sistemático y evitable.

### 3.6 De píxeles a celdas: la agregación zonal

Cada celda `c` de la grilla de 5 km es, por diseño, la unión de un número
entero de píxeles de 30 m (aproximadamente `(5000/30)² ≈ 27 778` píxeles por
celda, si la celda cae enteramente dentro de un tile). La asignación de cada
píxel a su celda se hace por indexado aritmético, no por intersección
geométrica de polígonos (mucho más rápido):

```
ix(p) = floor( x₃₁₁₆(p) / 5000 )
iy(p) = floor( y₃₁₁₆(p) / 5000 )
```

donde `x₃₁₁₆(p)`, `y₃₁₁₆(p)` son las coordenadas del centro del píxel `p`,
transformadas de la proyección UTM nativa del tile a `EPSG:3116` (la
proyección de la grilla). El par `(ix, iy)` identifica unívocamente la celda,
siempre que la grilla esté alineada al origen de `EPSG:3116` —
`exportar_grilla.py` construye cada celda directamente como múltiplo entero
del lado (5000 m), así que esa alineación queda **garantizada por
construcción**, no solo verificada después. El script igual corre la misma
comprobación explícita antes de guardar la grilla, como prueba de regresión
(si algún día cambiara la forma de construir la grilla y algo quedara mal
alineado, este indexado aritmético asignaría píxeles a la celda equivocada
de forma silenciosa; por eso el script se detiene con error en ese caso en
vez de continuar).

**Nota importante sobre el área**: aunque la asignación de píxeles a celdas
usa la proyección `EPSG:3116` (que, como toda proyección cartográfica,
distorsiona algo el área lejos de su meridiano central — Colombia
oficialmente se divide en tres franjas MAGNA-SIRGAS, y aquí se usa solo la
franja "Bogotá" para todo el país, por simplicidad de tener un único sistema
de indexado nacional), **el área en hectáreas no se calcula en esa
proyección**. Se calcula como un conteo de píxeles multiplicado por el área
fija de un píxel DIST-ALERT en su propia cuadrícula UTM nativa
(`30 m × 30 m = 900 m² = 0.09 ha`, constante en toda observación, sin
reproyección de área de por medio). Es decir: `EPSG:3116` decide **a qué
celda** pertenece un píxel; la cuadrícula UTM nativa del tile decide **cuánta
área** representa ese píxel. Esto evita que la distorsión de la proyección de
indexado se filtre a las hectáreas reportadas.

La agregación zonal para la celda `c` y el mes `t` es entonces:

```
bosque_ha(c)      = 0.09 × |{ p : ix(p)=ix(c), iy(p)=iy(c), bosque(p) }|
área_def_ha(c, t)  = 0.09 × |{ p : ix(p)=ix(c), iy(p)=iy(c), nuevo(p, t') para algún t' con mes(VEG-DIST-DATE(p)) = t }|
```

donde `|·|` denota cardinalidad (conteo) del conjunto.

### 3.7 Del bosque base a las variables de exposición y tasa

Con la tabla ancha `(celda, bosque_ha, área_def_ha por mes)` como insumo,
`consolidar.py` deriva, para cada celda `c` y periodo `t` (en orden
cronológico dentro de cada celda):

**Pérdida acumulada** — suma corrida de la deforestación observada hasta e
incluyendo `t`:

```
def_acum_ha(c, t) = Σ_{τ ≤ t} área_def_ha(c, τ)
```

**Bosque remanente al inicio del periodo** — el bosque base menos lo ya
perdido *antes* de `t` (nótese `τ < t`, estrictamente anterior, no `τ ≤ t`):

```
bosque_remanente_ha(c, t) = max( bosque_ha(c) − Σ_{τ < t} área_def_ha(c, τ),  0 )
```

Este es el denominador correcto de cualquier tasa: usar `bosque_ha(c)` (el
bosque original, sin descontar lo ya perdido) inflaría artificialmente el
denominador en periodos avanzados de celdas que ya perdieron buena parte de
su bosque, sesgando la tasa hacia abajo justo donde más habría que
observarla. El `max(..., 0)` es una salvaguarda numérica (redondeo) — el
resultado nunca debería ser negativo por construcción.

**Tasa de deforestación** — el target continuo, normalizado por la
exposición real de esa celda en ese periodo:

```
tasa_def(c, t) = área_def_ha(c, t) / bosque_remanente_ha(c, t),  acotada a [0, 1]
```

(si `bosque_remanente_ha(c, t) = 0`, se define `tasa_def(c, t) = 0` por
convención, no indeterminado — una celda sin bosque remanente no puede
deforestarse más, así que la tasa observada es trivialmente cero).

**Evento binario** — el target discreto, pensado para la primera etapa de un
modelo de dos partes (tipo *hurdle* o cero-inflado, apropiado dado el fuerte
desbalance hacia el cero que se documenta en la sección 8):

```
evento(c, t) = 1 [ área_def_ha(c, t) > 0 ]
```

**Rezagos y memoria de corto plazo** — para capturar dependencia temporal
(autocorrelación) dentro de cada celda:

```
lag_k_ha(c, t) = área_def_ha(c, t − k),   k = 1, 2, 3
media_movil_3(c, t) = promedio( área_def_ha(c, t−1), área_def_ha(c, t−2), área_def_ha(c, t−3) )
```

(el promedio móvil excluye deliberadamente el propio periodo `t`, para no
usar información del periodo que se busca explicar/predecir).

---

## 4. Bitácora de decisiones de diseño

Cada fila es un punto donde el pipeline pudo haberse construido distinto, qué
se decidió, por qué, y qué riesgo o costo se acepta a cambio.

| # | Decisión | Alternativas consideradas | Por qué esta opción | Riesgo/costo aceptado |
|---|---|---|---|---|
| 1 | Fuente del evento: NASA OPERA DIST-ALERT | GLAD alerts (Landsat), RADD alerts (radar Sentinel-1) | Mejor cadencia temporal que Landsat-solo (HLS combina Landsat+Sentinel-2); acceso programático estandarizado vía CMR | Producto relativamente nuevo, con menos años de historial de validación en la literatura que GLAD |
| 2 | Definición de evento: estados `(6, 8)` | `(4, 8)` (versión anterior del pipeline); incluir también `<50%` (estados 1-3, 7) | Excluye detecciones sin confirmar (código 4 = primera detección, alto riesgo de falso positivo por nube/sombra); incluye el 6 (confirmada, aún en curso) para no perder eventos activos al cierre de la ventana | Se descarta toda pérdida de vegetación con magnitud <50%, es decir se mide deforestación "severa" confirmada, no cualquier alteración de la vegetación — el panel subestima disturbios parciales o degradación leve |
| 3 | Umbral de magnitud ≥50% de pérdida de señal | Incluir también <50% como "evento menor" | Mantener una única definición binaria simple, con la señal de mayor confianza del producto | Ya cubierto en la fila anterior: no se mide degradación parcial |
| 4 | Atribución temporal por `VEG-DIST-DATE`, no por la fecha de la instantánea | Atribuir al mes de la instantánea en que se observó confirmado | Refleja cuándo ocurrió el evento en el terreno, no cuándo el algoritmo tuvo suficiente confianza para reportarlo | Los últimos 1-2 meses de la ventana temporal pueden estar subestimados (eventos reales aún no confirmados al momento de la descarga) |
| 5 | Máscara de bosque con corte de Hansen **por panel**: `anio_mascara = 2022` para DIST-ALERT, `anio_mascara_gfw = 2019` para GFW — **decisión revisada dos veces**: primero para agregar GFW como relleno 2020-2022 (corte único 2019 compartido), y de nuevo al pasar a dos paneles independientes (decisión 15), donde cada panel necesita su propio corte porque ya no comparten una sola ventana de eventos | Un único `anio_mascara` global para ambos paneles (como en la revisión anterior) | Cada panel necesita su bosque base cortado justo antes de que arranque *su propia* ventana de eventos: 2022 para DIST-ALERT (arranca 2023-01), 2019 para GFW (arranca 2020-01). Usar el mismo corte para los dos sería incorrecto para el que no arranca ese año — p. ej. cortar en 2019 el panel DIST-ALERT le añadiría de vuelta al "bosque disponible" pérdidas de 2019-2022 que DIST-ALERT nunca observa, porque ese producto no cubre esos años. `mascara_bosque()` en `zonal_local.py` cachea por separado según `anio_mascara`, así que las dos máscaras nunca se pisan entre sí (ver su docstring) | Cada panel asume que el bosque es estático entre su propio corte de Hansen y el inicio de su propia ventana de eventos (un margen de días, no de años, en ambos casos) |
| 6 | Grilla regular de 5×5 km como unidad de análisis | Píxel nativo (30 m); unidad administrativa (municipio) | Balance entre volumen computacional, señal estadística y resolución espacial útil (ver sección 1.2) | Se pierde la ubicación exacta del evento dentro de la celda; una celda de 2 500 ha puede mezclar zonas con presión de deforestación muy distinta |
| 7 | Proyección `EPSG:3116` para el indexado de la grilla | UTM por zona (múltiples zonas para cubrir Colombia); una proyección de área equivalente (p. ej. Albers) | Proyección oficial colombiana (MAGNA-SIRGAS), de uso común en cartografía nacional; un único sistema de indexado simplifica el código frente a manejar varias zonas UTM | Alguna distorsión de forma/área lejos del meridiano central de la franja Bogotá — mitigado porque el área reportada no se calcula en esta proyección (ver 3.6) |
| 8 | Cadencia de descarga mensual de instantáneas DIST-ALERT | Quincenal (`SMS`) | ~40 GB en vez de ~80 GB de descarga y almacenamiento; suficiente para la resolución mensual del panel final | Si el ciclo completo de una alerta (de primera detección a confirmada) ocurriera y se "reiniciara" por completo entre dos instantáneas separadas por un mes, podría perderse — riesgo mitigado en parte porque el estado 6 (confirmada, en curso) también se captura, no solo el 8 (finalizada) |
| 9 | Combinar tiles solapados con `max()`, no con suma | Sumar y luego deduplicar por geometría exacta | Mucho más simple y rápido de calcular; correcto porque el traslape entre tiles MGRS es por diseño del sistema de cuadrícula, no señal real duplicada | Ninguno relevante: `max()` es la operación correcta para este caso, no un compromiso |
| 10 | Remuestreo *nearest neighbor* al reproyectar Hansen a la grilla del tile | Remuestreo bilinear o cúbico | `treecover2000` y `lossyear` son, en el uso que se les da aquí, variables de clasificación (bosque/no bosque, año categórico) — interpolar valores continuos entre categorías produciría valores sin sentido físico | Cierto error posicional de sub-píxel en los bordes de manchas de bosque, inherente a cualquier remuestreo por vecino más cercano |
| 11 | Grilla construida localmente con `geopandas` y límites del DANE (MGN) — **decisión revisada**, ver nota abajo | (i) Google Earth Engine con `coveringGrid()` y los assets `USDOS/LSIB_SIMPLE`/`FAO/GAUL_SIMPLIFIED` — el diseño original; (ii) GADM como fuente de límites | Frente a (i): la edición gratuita/académica de Earth Engine **prohíbe explícitamente** su uso para "actividades de pago por servicio" o para "recibir compensación de una entidad comercial por aplicaciones o datos creados usando Earth Engine" — y este panel es insumo de consultorías comerciales del Observatorio, así que seguir con Earth Engine habría violado esos términos. Frente a (ii): GADM es de uso no comercial únicamente, el mismo problema que se está evitando. El DANE (MGN, CC BY 4.0) permite uso comercial con atribución y es además la fuente que el pipeline ya usaba opcionalmente para el cruce municipal — ahora es una sola fuente cartográfica, no dos | El MGN del DANE es de precisión catastral completa (no generalizada como GAUL_SIMPLIFIED), así que el polígono nacional sale con ~280 000 vértices; hubo que agregar una simplificación geométrica (tolerancia 100 m, irrelevante frente al lado de celda de 5000 m) para que el filtro espacial corriera en segundos y no en minutos |
| 12 | Filtrado de tiles en dos pasos (`bbox` rectangular a CMR, luego recorte por MGRS real) | Enviar a CMR la geometría exacta de Colombia | La API de búsqueda de CMR admite un `bounding_box` simple de forma directa; construir y depurar una consulta con geometría compleja habría sido más frágil | Se consulta (y luego se descarta) un excedente de gránulos de países vecinos y océano durante el inventario — costo de tiempo de consulta, no de almacenamiento (el filtro ocurre antes de descargar los archivos reales) |
| 13 | Panel GFW (2020-presente): confianza `high`+`highest` como evento, se descarta `nominal` | Incluir también `nominal`; usar un producto de un solo sistema (p. ej. solo RADD) en vez del integrado | Misma lógica que la decisión 2 para DIST-ALERT: `nominal` es la detección menos confiable (análoga a "primera detección, sin confirmar"), incluirla infla falsos positivos. El producto integrado se prefirió sobre un solo sistema porque ya es una metodología publicada (Pickens et al. 2025), no una combinación artesanal de esta tesis | La escala de confianza de GFW (3 niveles: nominal/high/highest) no es literalmente la misma variable que los 9 códigos de `VEG-DIST-STATUS` de DIST-ALERT — son dos productos distintos con dos definiciones de "confianza" no idénticas, aunque conceptualmente análogas. Esto es una limitación interna del panel GFW (mezcla de cuatro sistemas con sensibilidades distintas dentro de una sola escala de confianza), documentada en la sección 2.4 — no debe confundirse con el empalme entre los dos paneles (DIST-ALERT/GFW), que ya no existe porque no se fusionan (decisión 15) |
| 14 | ~~Fusión de las dos fuentes en `datos/crudo/nacional.csv` por `merge`~~ — **SUPERADA por la decisión 15**: el pipeline ya no fusiona las fuentes en absoluto, ni por `merge` ni por `concat` | (histórico) Concatenar el CSV de GFW y el de DIST-ALERT, dejando que `consolidar.py` los una | (histórico) Se mantiene esta fila por trazabilidad del diseño, pero el diseño que describe ya no existe en el código — ver decisión 15 | — |
| 15 | Dos paneles completamente independientes (`nacional.csv`/`panel_..._dist_alert.csv` y `nacional_gfw.csv`/`panel_..._gfw.csv`), **nunca fusionados ni concatenados**; el usuario elige explícitamente cuál construir (`consolidar.py --fuente {dist_alert,gfw}`, obligatorio, sin default) | Panel único e híbrido: GFW rellena 2020-2022, se fusiona por `merge` en `cell_id` con DIST-ALERT (2023-presente) en un solo archivo continuo — el diseño de la decisión 14, ya implementado y luego revertido | Un panel híbrido introduce, dentro de una sola serie temporal por celda, un cambio de metodología de detección no controlado en el límite 2022-12/2023-01 (de cuatro sistemas integrados a uno solo) sin ninguna señal en los datos que lo marque — cualquier salto real de la tasa de deforestación alrededor de ese mes sería indistinguible de un artefacto del empalme. Mantener los paneles separados traslada esa decisión al usuario del panel (¿necesito la serie larga y menos homogénea, o la corta y más homogénea?) en vez de resolverla en silencio dentro del pipeline. Requirió además separar el corte de Hansen por panel (decisión 5 revisada) y el nombre de cache de `mascara_bosque()` (`{tile}__bosque_am{anio_mascara}_ud{umbral}.npy`) para que las dos máscaras de bosque nunca se contaminen entre sí | Quien quiera una serie 2020-presente pierde la posibilidad de "aprovechar" DIST-ALERT (el sistema único, mejor documentado) para el tramo 2023 en adelante: el panel GFW usa el producto integrado para *toda* su ventana, no solo para 2020-2022, así que sacrifica algo de homogeneidad metodológica interna a cambio de nunca mezclar dos definiciones de "evento" dentro de un mismo panel |

**Nota sobre la decisión 11**: es la única fila de esta bitácora que se
revisó después de implementada. El diseño original (documentado en
versiones previas de este documento) usaba Google Earth Engine porque, para
una grilla generada una sola vez con datos públicos, parecía la opción más
simple. Esa evaluación no consideró el uso comercial previsto del panel; al
aparecer ese requisito, se verificaron los términos de servicio de Earth
Engine y se encontró el conflicto directo descrito arriba, así que se
reimplementó `exportar_grilla.py` localmente. El resultado (45 621 celdas,
33 departamentos) es muy cercano al de la versión con Earth Engine (44 530
celdas) — la diferencia es esperable y viene de usar un límite
administrativo más preciso (DANE MGN) en vez de uno generalizado (GAUL
simplificado a 500 m), no de un error de construcción.

---

## 5. Supuestos del estudio

1. **El bosque es estático entre el corte de Hansen y el inicio de la
   ventana de eventos de cada panel** (2022→2023-01 para DIST-ALERT,
   2019→2020-01 para GFW): no se contempla ganancia de bosque
   (regeneración) en ese margen, ni pérdida no capturada por Hansen antes
   del corte.
2. **DIST-ALERT confirmado + pérdida de señal ≥50% ⇒ deforestación real**: se
   confía en la calidad de detección reportada por el producto OPERA; el
   pipeline no incorpora una validación de campo local ni un cruce con otra
   fuente independiente de verdad-de-campo (*ground truth*) para Colombia.
3. **Un pixel puede pertenecer a lo sumo a una celda de la grilla**: el
   indexado aritmético asume que la grilla está perfectamente alineada al
   origen de `EPSG:3116` (verificado explícitamente en `exportar_grilla.py`).
4. **La fecha de `VEG-DIST-DATE` es confiable como fecha del evento real**,
   incluso cuando la confirmación (cambio de estado a 6/8) ocurre varios
   meses después.
5. **El área de un píxel DIST-ALERT es exactamente 900 m² en cualquier
   ubicación de Colombia** (constante, sin corrección por proyección) — válido
   porque la cuadrícula nativa de cada tile ya es una proyección de baja
   distorsión de área a esa escala.
6. **Los tiles MGRS descargados cubren completamente el territorio
   continental de interés**: se asume que `filtrar_tiles.py` identificó
   correctamente todos los tiles con celdas colombianas; tiles sin ningún
   gránulo disponible en CMR (nubosidad persistente, borde de cobertura)
   quedan con datos faltantes, no con ceros (ver limitaciones).

## 6. Limitaciones conocidas

- **Subestimación de los últimos meses de la ventana** por el *reporting lag*
  de confirmación de DIST-ALERT (sección 2.2 y decisión 4).
- **No se distingue causa del disturbio** en ninguna de las dos fuentes: el
  panel mide pérdida de cobertura/vegetación de cualquier origen (antrópico o
  natural), no específicamente deforestación por actividad humana en el
  sentido estricto.
- **Posible confusión con plantaciones forestales de rotación corta** en la
  línea base de Hansen (sección 2.1).
- **Nubosidad persistente** (Amazonía, Pacífico) reduce la frecuencia de
  observaciones limpias, lo que puede retrasar (no eliminar) la detección de
  eventos reales en esas regiones.
- **Sin validación de campo local**: la precisión reportada de ambos
  productos proviene de sus respectivas validaciones globales/regionales, no
  de un ejercicio de verificación específico para Colombia dentro de esta
  tesis.
- **El desbalance de clases es marcado** (ver sección 8 y
  `eda_deforestacion.ipynb`): en la corrida usada para este documento, cerca
  del 77% de las celda-mes del panel tienen `evento = 0`; cualquier modelo
  posterior debe tratar esto explícitamente (de ahí el diseño de `evento`
  como variable separada, pensada para un enfoque de dos etapas). Esta
  proporción puede variar entre corridas (más celdas o más meses cambian el
  denominador) — el número exacto y actualizado está siempre en la sección
  4 del notebook de EDA, no hay que tomar esta cifra como fija.
- **Efecto de inicio de ventana** (ver sección 3.4): el primer periodo de
  cualquier corrida sobreestima la deforestación "de ese mes" porque mide un
  stock inicial acumulado, no un flujo mensual — excluirlo de promedios y
  modelos. Como ahora hay dos paneles con ventanas distintas, este efecto
  aparece **dos veces por separado**: en 2023-01 para el panel DIST-ALERT y
  en 2020-01 para el panel GFW — cada uno debe tratarse independientemente
  al analizar o modelar ese panel.
- **Los dos paneles no son comparables número a número** (ver sección 2.4 y
  decisión 15): tienen metodologías de detección distintas y ventanas de
  ambos empiezan en años distintos. No están pensados para promediarse,
  restarse ni concatenarse fuera de este pipeline tampoco.

---

## 7. Restricciones de licencia y uso comercial

Esta sección existe porque el destino declarado de este panel va más allá de
lo académico: es insumo de consultorías comerciales del Observatorio
Financiero Rural de la Javeriana. Eso cambia qué licencias son aceptables
para las fuentes de datos — una fuente "gratis para investigación" no
necesariamente es gratis para vender un servicio con ella. Lo que sigue es
un resumen, **no asesoría legal**, con fuente citada para cada afirmación,
para que la oficina
jurídica o de transferencia tecnológica de la universidad lo revise antes de
comercializar cualquier producto derivado de este panel.

| Fuente | Licencia | Uso comercial | Obligación práctica |
|---|---|---|---|
| NASA OPERA DIST-ALERT (LP DAAC) | Datos abiertos de la NASA, sin restricción declarada | Permitido explícitamente, sin costo | Ninguna obligatoria; se recomienda citar la fuente y no dar a entender que la NASA respalda el producto comercial |
| Hansen Global Forest Change | CC BY 4.0 | Permitido, incluida la reventa/redistribución | Atribución: *"Source: Hansen/UMD/Google/USGS/NASA"* + cita del paper (Hansen et al. 2013, sección 10) |
| DANE — Marco Geoestadístico Nacional | CC BY 4.0 | Permitido | Atribución, en las palabras del propio DANE: *"Departamento Administrativo Nacional de Estadística - DANE: www.dane.gov.co"* |
| GFW / GLAD-L / GLAD-S2 / RADD (panel GFW, 2020-presente, independiente del panel DIST-ALERT — sección 2.4) | CC BY 4.0 (confirmado para GFW en general y para RADD directamente desde Wageningen University; GLAD-L es muy probablemente el mismo caso — mismo laboratorio que Hansen GFC — pero no se encontró una página que lo confirme en esas palabras exactas específicamente para GLAD-L) | Permitido | Atribución por dataset; GFW advierte que "cada dataset tiene su propia licencia", así que conviene guardar un archivo de atribuciones junto al panel GFW final |
| ~~Google Earth Engine~~ (ya no se usa) | Edición gratuita/académica: uso no comercial únicamente | **Prohibido explícitamente** para este caso de uso | Se eliminó la dependencia (decisión 11 revisada, sección 4); ver cita textual abajo |

**Por qué se eliminó Earth Engine** (cita textual de los términos de la
edición no comercial, https://earthengine.google.com/noncommercial/):
instituciones académicas que reciben Earth Engine gratis no pueden "usar
Earth Engine para actividades de pago por servicio, incluyendo cumplir un
entregable, resultado o tarea pagado por un acuerdo de pago-por-servicio con
una entidad comercial, gubernamental u otra", ni "recibir compensación de
una entidad comercial por aplicaciones o datos creados usando Earth Engine".
Ese es exactamente el modelo de negocio del Observatorio. La alternativa
habría sido una licencia comercial de Earth Engine (precio no público, bajo
consulta con el equipo de ventas de Google Cloud) — se descartó porque
Earth Engine solo se usaba para un paso trivial de reimplementar localmente
(la grilla, ver decisión 11 revisada), sin ninguna razón para pagar por él.

**Recomendación práctica**: cualquier reporte o entregable comercial que use
uno de estos paneles debería incluir un bloque de atribución citando las
fuentes que efectivamente entraron en ese entregable (siempre
Hansen/UMD/Google/USGS/NASA y DANE; además NASA OPERA DIST-ALERT si el
entregable usa el panel DIST-ALERT, o GFW/UMD/WUR si usa el panel GFW —
nunca ambas listas de fuentes de evento a la vez para un mismo entregable,
ya que los dos paneles no se combinan), y llevar este resumen —o uno
actualizado, si las licencias cambian— a la revisión legal de la
universidad antes de la primera venta.

---

## 8. Cómo se ve la unidad de observación final

*(Los números de esta sección son de una corrida puntual del panel
DIST-ALERT, congelados como ejemplo. El pipeline se sigue corriendo y el
panel crece con cada nueva descarga — la fuente viva y siempre actualizada
de estas cifras, con gráficas, es
[`eda_deforestacion.ipynb`](eda_deforestacion.ipynb); ver también su
"efecto de inicio de ventana", documentado en la sección 3.4. El panel GFW
(`panel_deforestacion_colombia_gfw.csv`) tiene exactamente la misma forma
de columnas — es la misma función `consolidar()` la que produce los
dos — pero su propio rango temporal y sus propios números: de la misma
corrida puntual, **3 523 479 filas × 17 columnas** — 44 601 celdas × 79
periodos mensuales (2020-01 a 2026-07), 32 departamentos, 6 444 367 ha de
deforestación total (bosque base 77 468 340 ha). No son comparables número
a número con el panel DIST-ALERT — ver sección 2.4.)*

El panel DIST-ALERT resultante
(`datos/panel/panel_deforestacion_colombia_dist_alert.csv`) es una
tabla de **1 917 585 filas × 17 columnas**: 44 595 celdas × 43 periodos
mensuales (2023-01 a 2026-07), cubriendo 32 departamentos. Cada fila es una
celda-mes. Dos ejemplos reales:

**Una celda sin evento ese mes** (el caso ampliamente dominante):

```
cell_id: -668856_13524   periodo: 2023-01-01   area_def_ha: 0.0
bosque_remanente_ha: 2411.91   tasa_def: 0.0   evento: 0
```

**La misma celda, el mes en que sí hubo evento** (2 píxeles DIST-ALERT
confirmados, 0.18 ha):

```
cell_id: -668856_13524   periodo: 2023-09-01   area_def_ha: 0.18
bosque_remanente_ha: 2411.91   tasa_def: 0.0000746   evento: 1
```

La descripción completa de las 17 columnas, con ejemplos adicionales y cómo
inspeccionarlas en `pandas`, está en
[GUIA_CODIGO.md, sección "Cómo se ve la base de datos final"](GUIA_CODIGO.md#cómo-se-ve-la-base-de-datos-final)
— aquí se documenta como parte de la metodología porque el diseño de cada
columna (qué mide, en qué unidades, por qué existe) es una decisión
metodológica, no solo de formato de archivo.

---

## 9. Glosario técnico

| Término | Significado |
|---|---|
| **HLS** | *Harmonized Landsat Sentinel-2*: observaciones de Landsat 8/9 y Sentinel-2 armonizadas radiométrica y geométricamente en un único producto, insumo de OPERA DIST-ALERT |
| **OPERA** | *Observational Products for End-Users from Remote Sensing Analysis*: proyecto de la NASA/JPL que reprocesa observaciones satelitales existentes en productos estandarizados |
| **MGRS** | *Military Grid Reference System*: sistema de cuadrículas de 100×100 km usado por Sentinel-2, HLS y por lo tanto DIST-ALERT |
| **COG** | *Cloud-Optimized GeoTIFF*, el formato de archivo de DIST-ALERT |
| **CRS** | Sistema de referencia de coordenadas (p. ej. `EPSG:3116`, `EPSG:4326`) |
| **CMR** | *Common Metadata Repository*, el catálogo de la NASA para localizar gránulos |
| **Anomalía (VEG-ANOM)** | Desviación de una observación respecto a la línea base histórica del píxel (`VEG-HIST`) |
| **Censura (por la derecha)** | En este contexto: eventos que están en curso (no finalizados) al cierre de la ventana temporal de observación — el estado 6 los captura en vez de perderlos |
| **Panel de datos** | Estructura de datos con una dimensión de sección cruzada (aquí, la celda) y una temporal (aquí, el mes), repetida sistemáticamente |
| **Hurdle / cero-inflado** | Familia de modelos de dos etapas para variables con exceso de ceros: una etapa de clasificación (¿hubo evento?) y una de magnitud (¿cuánto, dado que hubo?) |
| **MAGNA-SIRGAS** | Marco de referencia geodésico oficial de Colombia; `EPSG:3116` es su proyección para la franja "Bogotá" |
| **DANE / MGN** | Departamento Administrativo Nacional de Estadística / Marco Geoestadístico Nacional: cartografía oficial de división político-administrativa de Colombia |

---

## 10. Referencias

- Hansen, M. C., Potapov, P. V., Moore, R., Hancher, M., Turubanova, S. A.,
  Tyukavina, A., Thau, D., Stehman, S. V., Goetz, S. J., Loveland, T. R.,
  Kommareddy, A., Egorov, A., Chini, L., Justice, C. O., & Townshend, J. R. G.
  (2013). High-Resolution Global Maps of 21st-Century Forest Cover Change.
  *Science*, 342(6160), 850–853. https://doi.org/10.1126/science.1244693
  — actualizaciones anuales del producto: https://glad.earthengine.app/view/global-forest-change
- NASA OPERA Project — Land Disturbance product suite (DIST-ALERT). Página del
  producto y documentación técnica (ATBD, User Guide) en NASA Earthdata:
  https://www.earthdata.nasa.gov (buscar "OPERA DIST-ALERT"). Se recomienda
  citar la versión exacta del ATBD consultada, dado que el producto se
  actualiza.
- earthaccess (cliente Python para NASA CMR/Earthdata):
  https://earthaccess.readthedocs.io
- DANE — Marco Geoestadístico Nacional (MGN) 2023, nivel departamento,
  licencia CC BY 4.0: https://www.dane.gov.co (Feature Service público:
  `MarcoGeoestadisticoNacional2023_NivelDepartamento`, servido vía ArcGIS).
  Fuente de los límites del país y de la asignación de departamento a cada
  celda de la grilla (ver METODOLOGIA §2.3 y decisión 11 revisada, §4).
- IGAC — MAGNA-SIRGAS, marco de referencia geodésico de Colombia
  (`EPSG:3116` y franjas asociadas).
- Google Earth Engine — Términos de servicio, edición no comercial:
  https://earthengine.google.com/noncommercial/ — citada como justificación
  de la decisión 11 revisada (§4): el pipeline dejó de depender de Earth
  Engine porque esos términos prohíben su uso en trabajo remunerado para
  terceros, y este panel es insumo de consultorías comerciales.

---

*Documento vivo: si cambian parámetros de diseño en `config_local.py`
(umbral de dosel, códigos de evento, año de corte, etc.), esta metodología
debe actualizarse en paralelo — son la misma decisión descrita dos veces, en
prosa aquí y en código allá.*
