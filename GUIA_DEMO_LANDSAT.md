# Cómo se deriva deforestación desde Landsat, paso a paso

Recorrido completo de [`demo_landsat_caqueta.py`](demo_landsat_caqueta.py):
qué hace cada bloque de código, por qué está escrito así, y qué significa
cada número del resultado.

**Qué papel cumple en la tesis.** Esta demo es parte del entendimiento de
los datos. El panel usa cifras que calcularon otros —GLAD-L, Hansen, el
IDEAM—, y la demo replica en una zona piloto el tipo de cálculo con que
se obtienen, para entenderlo bien y no tomarlo como dado. Ver la
sección 1.

Este documento asume que ya leyó [`METODOLOGIA.md`](METODOLOGIA.md)
sección 1.2, donde se explica qué mide cada fuente del proyecto.

---

## Índice

1. [Para qué sirve esta demo](#1-para-qué-sirve-esta-demo)
2. [Con qué se compara, y una precisión necesaria](#2-con-qué-se-compara-y-una-precisión-necesaria)
3. [La idea física: por qué el NBR detecta tala](#3-la-idea-física-por-qué-el-nbr-detecta-tala)
4. [Los parámetros, uno por uno](#4-los-parámetros-uno-por-uno)
5. [Paso 1 — La rejilla de trabajo](#paso-1--la-rejilla-de-trabajo)
6. [Paso 2 — Encontrar las escenas](#paso-2--encontrar-las-escenas)
7. [Paso 3 — Leer solo el recorte](#paso-3--leer-solo-el-recorte)
8. [Paso 4 — De reflectancia a NBR](#paso-4--de-reflectancia-a-nbr)
9. [Paso 5 — El compuesto de mediana](#paso-5--el-compuesto-de-mediana)
10. [Paso 6 — El bosque inicial](#paso-6--el-bosque-inicial)
11. [Paso 7 — El dominio](#paso-7--el-dominio)
12. [Paso 8 — Traer GLAD-L](#paso-8--traer-glad-l)
13. [Paso 9 — Del dNBR a la detección](#paso-9--del-dnbr-a-la-detección)
14. [Paso 10 — Calibrar sin hacer trampa](#paso-10--calibrar-sin-hacer-trampa)
15. [Paso 11 — Las métricas](#paso-11--las-métricas)
16. [La curva de observabilidad](#la-curva-de-observabilidad)
17. [Paso 12 — La comparación por celda](#paso-12--la-comparación-por-celda)
18. [Paso 13 — La muestra para validación visual](#paso-13--la-muestra-para-validación-visual)
19. [Los resultados, interpretados](#los-resultados-interpretados)
20. [Por qué los resultados son como son](#por-qué-los-resultados-son-como-son)
21. [¿Es bueno un F1 de 0,505?](#es-bueno-un-f1-de-0505)
22. [Dónde se ubica este método](#dónde-se-ubica-este-método)
23. [Límites de la demo](#límites-de-la-demo)
24. [Preguntas para más adelante](#preguntas-para-más-adelante)

---

## 1. Para qué sirve esta demo

El panel del proyecto usa productos ya procesados: alertas de GFW,
pérdida de Hansen, capas del IDEAM. Ninguno de los integrantes de este
trabajo es experto en detección de deforestación, y proponer un indicador
propio frente a productos hechos por equipos especializados sería
pretencioso. Lo que sí está a nuestro alcance, y aporta, es entender bien
cómo calcularon ellos sus datos.

La demo hace eso en una zona piloto de Caquetá:

1. Toma **imágenes crudas de satélite** y replica el tipo de cálculo con
   que se detecta pérdida de bosque: compuestos sin nubes, un índice
   espectral, un umbral y un filtro de área mínima.
2. Se **ajusta lo más posible a un producto publicado**, GLAD-L: el
   umbral se calibra para acercarse a sus valores.
3. Mide **cuánto se acerca y por qué se aparta**, y compara esa distancia
   con la que hay entre los propios productos profesionales.

Por decisión tomada con el profesor, la demo queda como **parte del
entendimiento de los datos**: explica de dónde vienen las cifras y cómo
se calcularon. No alimenta ningún panel ni el modelo. Si más adelante
hace falta responder preguntas que los productos publicados no
contestan, este es el punto de partida (ver
[Preguntas para más adelante](#preguntas-para-más-adelante)).

Todo corre en el PC, sin Google Earth Engine y sin credenciales nuevas.
El nivel gratuito de Earth Engine está limitado a uso **no comercial**, y
este trabajo alimenta consultorías del Observatorio.

---

## 2. Con qué se compara, y una precisión necesaria

La demo se compara contra **GLAD-L**, no contra el dato oficial.

| | Qué es | ¿Oficial? |
|---|---|---|
| **GLAD-L** | Alertas de la Universidad de Maryland, sobre Landsat | No |
| **IDEAM / SMByC** | La cifra que reporta Colombia | Sí |

GLAD-L se escogió porque es **comparable en naturaleza**: también deriva
de Landsat, también detecta a nivel de píxel, y también cubre la ventana
de fechas. El IDEAM publica una capa anual por transición de año, que no
se alinea con dos compuestos de enero-marzo.

Cuando el código dice "referencia" se refiere al producto contra el que
se contrasta. Está escrito así en el docstring de `metricas()`:

> *"Referencia" tampoco significa "verdad": GLAD-L tiene sus propios
> errores. Lo que miden estas cifras es CONCORDANCIA con un producto
> publicado, no exactitud contra el terreno.*

Para exactitud contra el terreno está la muestra de validación visual
del paso 13.

> **El IDEAM entra en la comparación de otra forma.** En
> [¿Es bueno un F1 de 0,505?](#es-bueno-un-f1-de-0505) se mide cuánto
> concuerdan entre sí GLAD-L, Hansen y el IDEAM en 2022, para tener un
> punto de referencia. La detección propia no se compara directamente con
> el IDEAM porque el año del IDEAM va de enero a diciembre y el de la
> demo de febrero a febrero.

---

## 3. La idea física: por qué el NBR detecta tala

El **NBR** (Normalized Burn Ratio) combina dos bandas:

```
NBR = (NIR - SWIR2) / (NIR + SWIR2)
```

- **NIR** (infrarrojo cercano, banda 5): la vegetación sana lo refleja
  con fuerza. Las hojas son casi espejos en esa longitud de onda.
- **SWIR2** (infrarrojo de onda corta, banda 7): el agua dentro de las
  hojas lo absorbe. Vegetación viva, poca reflectancia.

Un bosque en pie tiene entonces **NIR alto y SWIR2 bajo**, lo que da un
NBR alto. Cuando se tumba, queda suelo y madera seca: el NIR baja y el
SWIR2 sube, así que el NBR **cae**.

De ahí la resta:

```
dNBR = NBR(antes) - NBR(después)
```

Un dNBR grande y positivo significa "aquí había vegetación y dejó de
haberla". El umbral decide cuán grande tiene que ser.

---

## 4. Los parámetros, uno por uno

Todos viven al inicio del archivo, como en el resto del repositorio.

```python
BBOX = (-75.0, 0.8, -74.2, 1.5)
```

Zona piloto entre Cartagena del Chairá y San Vicente del Caguán. Se
escogió porque **concentra pérdida suficiente**: en una zona estable casi
todo sería verdadero negativo y las métricas no distinguirían nada.

```python
T1_INICIO, T1_FIN = "2022-01-01", "2022-03-31"
T2_INICIO, T2_FIN = "2023-01-01", "2023-03-31"
```

**La misma temporada seca en años consecutivos.** Comparando enero
contra julio, el dNBR recogería el ciclo fenológico: la vegetación cambia
sola entre estaciones y no se sabría qué parte del cambio es tala.

¿Por qué 2022-2023 y no 2020-2021? Porque el ráster de GLAD-L que publica
GFW es **rodante**: la versión vigente arranca en enero de 2021 y no
conserva los años previos. Se verificó la cobertura real antes de fijar
las fechas. Como efecto secundario, ambos años tienen Landsat 8 **y** 9,
mientras que en 2020 solo existía Landsat 8.

```python
GLAD_DESDE = dt.date(2022, 2, 15)
GLAD_HASTA = dt.date(2023, 2, 15)
```

La ventana equivalente para las alertas, del centro de T1 al centro de
T2. Un compuesto de mediana sobre enero-marzo representa, en promedio,
algo cercano a la mitad de la ventana. La fecha que representa de verdad
cada píxel se mide en cada corrida; ver el paso 5.

```python
UMBRAL_DOSEL = 30
ANIO_CORTE_PERDIDA = 21
```

El 30 % es el mismo umbral que usa el panel nacional
(`config_local.umbral_dosel`), para que la demo hable de "bosque" en los
mismos términos. El 21 corresponde a `lossyear <= 21` = pérdida ocurrida
antes de 2022.

```python
UMBRALES_DNBR = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35,
                 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
```

Los candidatos que prueba la calibración. La rejilla llega hasta 0,70
para que el óptimo quede **dentro** del rango y no en su borde. Ver el
paso 10.

```python
PIXELES_MIN_PARCHE = 12
```

A 30 m, cada píxel son 900 m² = **0,09 ha**. Entonces:

| Píxeles | Hectáreas |
|---|---|
| 11 | 0,99 — **no alcanza** |
| **12** | **1,08 — primer entero que llega a 1 ha** |

La hectárea es el área mínima de la definición de bosque del IDEAM.

```python
FILAS_POR_FRANJA = 512
```

El procesamiento va por franjas horizontales. Ver paso 5.

---

## Paso 1 — La rejilla de trabajo

```python
def perfil_zona() -> dict:
    izq, abajo, der, arriba = transform_bounds("EPSG:4326", CRS, *BBOX, densify_pts=21)
    izq, abajo = np.floor(izq / ESCALA_M) * ESCALA_M, np.floor(abajo / ESCALA_M) * ESCALA_M
    der, arriba = np.ceil(der / ESCALA_M) * ESCALA_M, np.ceil(arriba / ESCALA_M) * ESCALA_M
    ...
    return {"transform": Affine(ESCALA_M, 0, izq, 0, -ESCALA_M, arriba), ...}
```

**Qué hace.** Convierte el `BBOX` de longitud/latitud a metros UTM y
define un ráster sintético de 30 m que cubre la zona.

**Por qué.** Las cuatro fuentes llegan en proyecciones distintas: Landsat
en UTM, Hansen y GLAD-L en coordenadas geográficas. En vez de adoptar la
rejilla de alguna de ellas, se define **una propia** y todas se
reproyectan encima. Así ninguna fuente le impone su alineación a las
demás, y un píxel significa lo mismo en todas las capas.

Es el mismo patrón que usa `zonal.perfil_bloque()` para el panel
nacional. La demo hereda esa geometría del repositorio.

**El detalle del redondeo.** `np.floor` y `np.ceil` fuerzan los límites a
múltiplos exactos de 30 m. Sin eso, la rejilla quedaría desfasada medio
píxel y los bordes tendrían fracciones.

**`densify_pts=21`** agrega puntos intermedios al reproyectar el
rectángulo. En UTM los bordes de un bbox de lon/lat se curvan, así que
transformar solo las cuatro esquinas subestimaría la extensión.

El resultado para esta zona: **2968 × 2581 píxeles**.

```python
def mascara_mitades(perfil: dict) -> Tuple[np.ndarray, np.ndarray]:
    mitad = perfil["width"] // 2
    oeste = np.zeros((perfil["height"], perfil["width"]), dtype=bool)
    oeste[:, :mitad] = True
    return oeste, ~oeste
```

Parte la zona en dos por el medio. El corte se hace sobre **columnas de
la rejilla**, no sobre longitudes, para que ambas mitades tengan
exactamente el mismo ancho.

---

## Paso 2 — Encontrar las escenas

```python
q = {"collections": [COLECCION_STAC], "bbox": list(BBOX),
     "datetime": f"{inicio}/{fin}",
     "query": {"platform": {"in": PLATAFORMAS}}, "limit": 100}
r = requests.post(STAC_URL, json=q, timeout=TIEMPO_ESPERA)
```

**Qué hace.** Le pregunta al catálogo de Microsoft Planetary Computer qué
escenas Landsat 8/9 hay sobre la zona en esas fechas. Es un único POST
con un JSON.

**Se usa `requests` y no `pystac-client`** para no sumar una
dependencia. La consulta es sencilla y el pipeline ya trae `requests`.

**Lo que el código evita a propósito:**

```python
    # NO se filtra por nubosidad de escena. Una escena con 80 % de nubes
    # puede tener perfectamente despejada la esquina que nos interesa, y
    # descartarla reduciria observaciones justo donde mas falta hacen. El
    # filtro real es por pixel, con QA_PIXEL.
```

Es un error común filtrar escenas por su porcentaje global de nubes. Ese
porcentaje se calcula sobre la escena completa, de 185 × 180 km, y no
dice nada sobre el recorte de 80 km que interesa aquí.

Resultado: **38 escenas en T1** (20 de Landsat 8, 18 de Landsat 9) y
**34 en T2**.

```python
def token_sas() -> str:
    r = requests.get(SAS_URL, timeout=TIEMPO_ESPERA)
    return r.json()["token"]
```

Los archivos viven en almacenamiento de Azure, que exige una firma. El
servicio la entrega **a quien la pida**, sin cuenta. Eso es lo que
permite prescindir de credenciales.

---

## Paso 3 — Leer solo el recorte

Esta es la función que hace viable todo el enfoque.

```python
def _leer_ventana(url: str, perfil: dict, fila0: int, n_filas: int,
                  dtype) -> Optional[np.ndarray]:
    tr = perfil["transform"]
    arriba = tr.f + tr.e * fila0
    abajo = tr.f + tr.e * (fila0 + n_filas)
    izq, der = tr.c, tr.c + tr.a * perfil["width"]
```

Calcula los límites de la franja en coordenadas del terreno. Recuerde que
`tr.e` es **negativo** (las filas bajan, la Y sube), así que `arriba`
corresponde a la fila menor.

```python
    with rasterio.open(f"/vsicurl/{url}") as src:
        b = transform_bounds(perfil["crs"], src.crs, izq, abajo, der, arriba,
                             densify_pts=21)
```

**`/vsicurl/` es lo que hace viable el enfoque.** Es un controlador de
GDAL que abre un archivo remoto por HTTP **sin descargarlo**: lee solo
los bytes que uno le pida.

Luego traduce los límites de la franja al sistema de coordenadas de la
escena, para saber qué pedazo pedir.

```python
        sb = src.bounds
        if b[2] <= sb.left or b[0] >= sb.right or b[3] <= sb.bottom or b[1] >= sb.top:
            return None                      # sin traslape
```

Si la escena no toca la franja, se devuelve `None` de inmediato. Sin este
corte se harían peticiones HTTP inútiles por cada combinación de escena y
franja.

```python
        ven = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
        ven = Window(max(0, ven.col_off - 1), max(0, ven.row_off - 1),
                     min(ven.width + 2, src.width), min(ven.height + 2, src.height))
```

Convierte los límites a una ventana en píxeles de la escena, y le agrega
**un píxel de margen**. Sin ese margen, el remuestreo perdería la fila y
la columna del borde, porque necesita vecinos para interpolar.

```python
        datos = src.read(1, window=ven)
        reproject(source=datos, destination=destino,
                  src_transform=src.window_transform(ven), src_crs=src.crs,
                  dst_transform=tr_franja, dst_crs=perfil["crs"],
                  resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
```

Lee el recorte y lo reproyecta sobre la franja de la rejilla de trabajo.

**El remuestreo es `nearest`** porque la banda `QA_PIXEL` guarda bits de
calidad. Promediar el valor 22280 con el 21824 da un número sin sentido.
Y si se usara una interpolación para las bandas y otra para su máscara,
quedarían desalineadas.

**El ahorro.** Una escena Landsat completa pesa del orden de 1 GB. Como
los archivos son **COG** (Cloud Optimized GeoTIFF), el servidor entrega
solo los bloques que cubren la ventana. Se descargan megabytes.

El registro de la corrida lo confirma: las tres primeras franjas leen 19
escenas y las tres últimas 38. Esa duplicación es el traslape entre
órbitas de Landsat en el sur de la zona. Trayendo escenas completas el
número sería igual en todas.

---

## Paso 4 — De reflectancia a NBR

```python
    limpio = ((qa & (1 << 1)) == 0) & ((qa & (1 << 3)) == 0) & ((qa & (1 << 4)) == 0)
```

`QA_PIXEL` empaqueta varios indicadores de calidad, uno por bit. El
operador `&` con `1 << n` prueba el bit `n`:

| Bit | Qué marca | Por qué se descarta |
|---|---|---|
| 1 | Nube dilatada | El borde difuso de una nube contamina igual |
| 3 | Nube | Evidente |
| 4 | **Sombra de nube** | Tan dañina como la nube: baja la reflectancia y **simula pérdida de biomasa** |

La sombra es la trampa menos obvia. Una sombra sobre bosque intacto se ve
espectralmente parecida a un claro recién abierto, y sin este filtro
generaría falsos positivos.

```python
    nir_r = nir.astype(np.float32) * 0.0000275 - 0.2
    swir_r = swir.astype(np.float32) * 0.0000275 - 0.2
```

Los valores de Collection 2 nivel 2 vienen como **enteros escalados**
para ahorrar espacio. Hay que aplicar la ganancia y el desplazamiento
para recuperar reflectancia física.

**Es fácil de omitir y difícil de detectar.** El NBR es un cociente
normalizado, así que sin la conversión sigue dando valores entre −1 y 1 y
parece correcto. El desplazamiento de −0,2 no es lineal respecto al
cociente, así que el resultado sale distinto.

```python
    nbr[~valido | (suma == 0)] = np.nan
```

Donde no hay observación válida se pone **NaN**. Un cero sería un valor
de NBR legítimo y se confundiría con un dato real; NaN marca la ausencia.

---

## Paso 5 — El compuesto de mediana

```python
    for fila0 in range(0, alto, FILAS_POR_FRANJA):
        n = min(FILAS_POR_FRANJA, alto - fila0)
        pila, dias = [], []
        for e in escenas:
            c = _nbr_de_escena(e, sas, perfil, fila0, n)
            if c is not None:
                pila.append(c)
                dias.append((_fecha_escena(e) - referencia).days)
        cubo = np.stack(pila)
        limpio = ~np.isnan(cubo)
        fechas = np.where(limpio, np.array(dias, np.float32)[:, None, None],
                          np.nan)
        nbr[fila0:fila0 + n] = np.nanmedian(cubo, axis=0)
        desfase[fila0:fila0 + n] = np.nanmedian(fechas, axis=0)
        obs[fila0:fila0 + n] = limpio.sum(axis=0).astype(np.uint16)
```

Para cada píxel salen tres cosas:

- **`nbr`**: la mediana de todas sus lecturas limpias de la ventana.
- **`obs`**: cuántas lecturas limpias tuvo. Con eso se construye el
  dominio.
- **`desfase`**: la fecha mediana de esas lecturas, en días respecto del
  centro de la ventana. Dice qué momento representa en realidad el
  compuesto. Ver más abajo.

**Se usa la mediana** porque la máscara de nubes deja pasar
observaciones residuales. Una lectura contaminada desplaza la media, y a
la mediana casi no la mueve. Con 5 observaciones eso se nota bastante.

**Se trabaja por franjas** porque apilar las 38 escenas de la zona
completa pediría unos 600 MB al tiempo. Con franjas de 512 filas el pico
baja a decenas de MB. El resultado es idéntico, porque la mediana se
calcula por píxel y partir el trabajo por filas no la altera.

```python
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            nbr[fila0:fila0 + n] = np.nanmedian(cubo, axis=0)
```

`nanmedian` avisa cuando un píxel estuvo nublado en **todas** las
escenas. Ese caso está previsto: el píxel queda en NaN, no entra al
dominio y aparece contado en el diagnóstico. El aviso se silencia para
que no tape el registro útil.

### Cómo se llega al dato anual

No se suman meses. Se arman dos "fotos" del bosque, una alrededor de
febrero de 2022 y otra alrededor de febrero de 2023, y la resta de las
dos da lo que se perdió en ese año.

Cada foto se arma con todas las lecturas sin nube de enero a marzo,
porque una sola fecha casi siempre sale nublada: de 38 escenas, el píxel
típico tiene 5 limpias. No se usa la serie completa del año; solo esas
dos ventanas de tres meses.

### Todas las lecturas pesan igual

Dentro de cada ventana, una lectura del 7 de enero pesa lo mismo que una
del 15 de febrero. Eso tiene una consecuencia: si en un píxel las
lecturas limpias de 2022 cayeron en enero y las de 2023 en marzo, su
dNBR mide unos 14 meses, no 12.

La alternativa natural es darles más peso a las lecturas cercanas al
centro de la ventana. Se probaron cuatro formas, con el mismo dominio,
la misma calibración en la mitad oeste y la misma validación en la mitad
este:

| Cómo se arma cada foto | Umbral | F1 | Pearson por celda | Área de GLAD-L encontrada |
|---|---|---|---|---|
| **Todas las lecturas, mismo peso (el módulo)** | 0,35 | **0,505** | **0,909** | **62 %** |
| Más peso a las cercanas, suave (σ = 30 días) | 0,35 | 0,497 | 0,909 | 60 % |
| Más peso a las cercanas, fuerte (σ = 15 días) | 0,45 | 0,470 | 0,896 | 53 % |
| Solo las 3 lecturas más cercanas | 0,35 | 0,479 | 0,907 | 58 % |
| Solo la lectura más cercana | 0,50 | 0,455 | 0,886 | 51 % |

Mientras más se concentra la foto en una fecha, peor sale.

La razón es la misma que explica casi todo en esta demo: el error
dominante son las **lecturas contaminadas por nube**, no la fecha. Armar
la foto con menos lecturas gana precisión de fecha y pierde la
protección de la mediana contra una lectura sucia. Se nota en el umbral:
las variantes más concentradas necesitaron subir la raya a 0,45 y 0,50
para no llenarse de falsos positivos, y con eso dejaron de ver tala real.

Por eso el módulo deja el mismo peso para todas.

> Esta comparación se hizo una vez, fuera del módulo, releyendo las
> escenas con su fecha. El módulo conserva solo la variante elegida.

### Qué fecha representa cada compuesto

Con el mismo peso para todas, la fecha de cada foto depende de cuándo
cayeron las lecturas limpias de ese píxel. `fecha_efectiva.csv` lo mide
en cada corrida:

| | Fecha efectiva mediana | 90 % de los píxeles entre |
|---|---|---|
| Foto 2022 | **1 de febrero** (14 días antes del centro) | 23 de enero y 17 de febrero |
| Foto 2023 | **19 de febrero** (4 días después del centro) | 27 de enero y 7 de marzo |

Y con eso, el intervalo que mide el dNBR:

| Intervalo T1 → T2 | Días |
|---|---|
| Mediana | **376** |
| 90 % de los píxeles entre | 360 y 400 |
| Se aparta del año más de 30 días | 8,2 % de los píxeles |
| Se aparta del año más de 45 días | 0,3 % de los píxeles |

El dato "anual" de la demo mide entonces unos **12 meses y medio**, y el
92 % de los píxeles queda a menos de un mes del año exacto.

La foto de 2022 sale corrida hacia enero porque ese año las lecturas
limpias se concentraron en la primera parte de la ventana. No falta
información cerca del centro: en el mismo diagnóstico de arriba, la
mediana de la distancia entre el 15 de febrero y la lectura limpia más
cercana fue de 1 día en 2022 y de 4 en 2023.

### La ventana de GLAD-L se deja fija

Las alertas de GLAD-L se cuentan del 15 de febrero de 2022 al 15 de
febrero de 2023, para todos los píxeles. Se probó darle a cada píxel su
propia ventana, de su fecha efectiva de 2022 a la de 2023, y el F1 bajó
de 0,505 a 0,491. El desfase de fechas no explica los desacuerdos con
GLAD-L; los explican los bordes, las nubes y los claros pequeños (ver
[Por qué los resultados son como son](#por-qué-los-resultados-son-como-son)).

### El caché

```python
    clave = (f"nbr_{BBOX[0]}_..._{T1_INICIO}_..._{perfil['width']}x{perfil['height']}")
    archivo = DIR_DEMO / f"cache_{clave}.npz"
```

Componer las dos ventanas toma unos 13 minutos de lecturas HTTP, y ese
resultado **no depende de los umbrales**. Se guarda en disco, así que
probar otro umbral cuesta segundos.

**La clave incluye zona, fechas y forma de la rejilla**, que es todo lo
que cambia el contenido. Si usted cambia el `BBOX` y vuelve a correr, el
caché se invalida y se recalcula. Sin eso le devolvería calladamente el
compuesto de otra corrida. `calcular_bosque.py` toma la misma
precaución con su propio caché.

El caché guarda también la fecha efectiva. Un caché de una versión
anterior del módulo, que no la trae, se descarta y se recalcula solo.

---

## Paso 6 — El bosque inicial

```python
    dosel = reproyectar_sobre_bloque(granulos("treecover2000"), perfil)
    perdida = reproyectar_sobre_bloque(granulos("lossyear"), perfil)
    previa = (perdida >= 1) & (perdida <= ANIO_CORTE_PERDIDA)
    bosque = (dosel >= UMBRAL_DOSEL) & ~previa
```

**Dos condiciones:**

1. **Tenía dosel suficiente en 2000** (≥ 30 %).
2. **No se había deforestado antes de T1.** Esto es lo que evita contar
   como hallazgo un claro que existe desde hace años. Sin este filtro, un
   potrero abierto en 2015 aparecería como "bosque" solo porque tenía
   árboles en 2000.

`reproyectar_sobre_bloque()` viene de `zonal.py`, el mismo módulo que
usa el panel nacional.

```python
    g_dm = granulos("datamask", obligatoria=False)
    if g_dm:
        bosque &= reproyectar_sobre_bloque(g_dm, perfil) == 1
    else:
        logger.info("  datamask no esta en disco; se omite...")
```

La capa `datamask` distingue tierra firme de agua permanente. El pipeline
solo descarga `treecover2000` y `lossyear`, así que suele no estar.

Se dejó **opcional** para no exigir otro gigabyte de descarga. El umbral
de dosel ya hace ese trabajo: un cuerpo de agua tiene 0 % de cobertura
arbórea en 2000 y no pasa el primer filtro.

---

## Paso 7 — El dominio

Es la decisión metodológica más importante del módulo.

```python
def construir_dominio(bosque, obs_t1, obs_t2) -> np.ndarray:
    return bosque & (obs_t1 >= 1) & (obs_t2 >= 1)
```

Tres líneas que deciden la validez de todo lo demás.

Un píxel de bosque tapado por nubes en T1 o en T2 **no se puede
evaluar**: no sabemos si cambió.

Lo que pasa si uno no lo piensa es que ese píxel queda contado como "sin
pérdida", y se vuelve un verdadero negativo regalado. Como el bosque
estable ya domina la escena, agregar miles de negativos así **infla la
exactitud global** y **esconde la falta de observación**, que es el
problema de fondo.

Por eso se excluye del análisis, y el porcentaje excluido se reporta
entre los resultados.

### Lo que reveló el diagnóstico

```
sin_datos_pct : 0.00
```

**Cero.** Con tres meses de Landsat 8 y 9, todos los píxeles alcanzaron
al menos una lectura limpia en ambas ventanas.

Eso debilita el argumento de "las nubes nos dejaron sin datos". El
número que sí importa es otro:

| | T1 | T2 |
|---|---|---|
| Escenas disponibles | 38 | 34 |
| Observaciones limpias, **mínimo** | 1 | 1 |
| Observaciones limpias, **percentil 10** | 4 | 2 |
| Observaciones limpias, **mediana** | **5** | **3** |
| Observaciones limpias, **máximo** | 19 | 14 |

De 38 escenas, el píxel mediano recibió **5 lecturas limpias**. La
nubosidad descarta la gran mayoría; acumulando tres meses alcanza a
quedar alguna.

Así que lo que conviene decir es que **las nubes redujeron 38
observaciones a 5**. Es más preciso y se defiende mejor.

El diagnóstico reporta la distribución completa por esto: un píxel con
una sola lectura entra al dominio, pero si esa lectura venía contaminada
y la máscara no la atrapó, su dNBR es ruido. Quedó en ese caso el **0,38 %**
del bosque.

---

## Paso 8 — Traer GLAD-L

```python
    r = requests.get(u, headers={"x-api-key": clave}, allow_redirects=False, ...)
    if r.status_code != 307 or "Location" not in r.headers:
        raise SystemExit(...)
    return r.headers["Location"]
```

El bucket de GFW es **"Requester Pays"**: una descarga anónima falla. Hay
que pasar por el endpoint de la API con la key, que responde **307** con
una redirección hacia una URL de S3 ya firmada.

`allow_redirects=False` captura esa URL sin descargar el cuerpo, para
después pasársela a GDAL y leer por ventana.

### La decodificación, y por qué se verifica

```python
    conf = (destino // 10000).astype(np.uint8)
    dias = (destino % 10000).astype(np.int32)
```

La banda `date_conf` empaqueta **dos cosas en un entero**:
`confianza × 10000 + días desde 2014-12-31`.

```python
    logger.info("  codigos de confianza observados: %s", ...)
    logger.info("  rango de fechas: %s a %s", ...)
```

**La codificación se verifica contra los datos, no se da por supuesta.**
Si estuviera mal, el módulo no fallaría: devolvería un resultado vacío,
que es el error más difícil de notar.

Esa verificación descubrió que el ráster es **rodante** (solo tiene
alertas desde 2021), y por eso hubo que mover la ventana del análisis.

```python
    if d_max < i_desde or d_min > i_hasta:
        raise SystemExit(
            f"Las alertas disponibles ({GLAD_EPOCA + dt.timedelta(days=d_min)} a "
```

Si la ventana pedida cae fuera del rango disponible, el módulo se
detiene con un mensaje claro. Devolver cero alertas sería peor.

El ráster se lee una sola vez por corrida, con `leer_glad()`, y
`alertas_glad()` lo filtra para cada ventana que haga falta: la de la
demo y, en la referencia entre productos, el año calendario 2022.

### Cuando la API responde a medias

Antes de bajar el ráster hay que preguntarle a GFW cuál es la versión
vigente del dataset. Esa consulta puede responder **200 con el cuerpo
incompleto**, sin el campo `data`, mientras GFW está publicando una
versión nueva.

Nos pasó: la corrida murió con `KeyError: 'data'` y, al repetirla un
minuto después, funcionó. GFW estaba publicando `v20260923` justo en ese
momento.

`_version_glad()` separa las fallas que se arreglan reintentando de las
que no:

| Qué responde el servidor | Qué hace |
|---|---|
| 200 con `data.version` | Sigue |
| **200 sin `data`** | Reintenta, hasta 3 veces cada 10 s |
| 500 u otro error del servidor | Reintenta |
| Sin respuesta (red caída) | Reintenta |
| **401 o 403** | **Se detiene de una** y dice cómo renovar la key |

Una key vencida no mejora por insistir, así que ese caso corta de
inmediato y nombra el comando que la renueva. Los demás esperan, porque
suelen resolverse solos.

Si se agotan los intentos, el mensaje dice cuál fue el último motivo y
sugiere volver a correr más tarde cuando la causa fue una respuesta
incompleta.

---

## Paso 9 — Del dNBR a la detección

```python
def perdida_propia(dnbr, dominio, umbral: float) -> np.ndarray:
    cruda = (dnbr > umbral) & dominio
    return filtrar_parches(cruda)
```

Dos condiciones: el dNBR supera el umbral **y** el píxel está en el
dominio.

```python
def filtrar_parches(binaria: np.ndarray) -> np.ndarray:
    estructura = np.ones((3, 3), dtype=bool)          # 8 vecinos
    etiquetas, n = ndimage.label(binaria, structure=estructura)
    tam = np.bincount(etiquetas.ravel())
    tam[0] = 0                                        # el fondo no cuenta
    return np.isin(etiquetas, np.flatnonzero(tam >= PIXELES_MIN_PARCHE))
```

`ndimage.label` agrupa los píxeles marcados en **componentes conexas** y
le da un número a cada grupo. `np.bincount` cuenta cuántos píxeles tiene
cada grupo. Se conservan solo los grupos de 12 o más.

**`tam[0] = 0`** hace falta porque la etiqueta 0 es el fondo, o sea todo
lo no marcado, y sería con mucho el grupo más grande.

**La vecindad es de 8 y no de 4.** Con vecindad de 4, un claro alargado
en diagonal —una vía de extracción, por ejemplo— se partiría en
fragmentos sueltos y el filtro lo eliminaría entero.

### El mismo trato para GLAD-L

```python
def perdida_glad(glad, dominio) -> np.ndarray:
    return filtrar_parches(glad & dominio)
```

A GLAD-L se le aplica **el mismo tratamiento**: misma máscara de bosque y
mismo dominio (ambos van dentro de `dominio`), y el mismo filtro de área
mínima. El filtro de fecha ya se aplicó al leer.

Esas igualaciones son las que hacen comparable el resultado. Un ejemplo:
GLAD-L alerta también fuera del bosque definido por Hansen. Sin la
máscara común, eso saldría como "detección adicional de GLAD" cuando en
realidad es terreno donde el método propio nunca pudo buscar.

---

## Paso 10 — Calibrar sin hacer trampa

```python
def calibrar_umbral(dnbr, dominio, glad_p, oeste) -> pd.DataFrame:
    for u in UMBRALES_DNBR:
        p = perdida_propia(dnbr, dominio, u)
        m = matriz_acuerdo(p, glad_p, dominio, oeste)
```

Prueba cada umbral candidato **solo en la mitad oeste**. Después:

```python
    mejor = float(cal.loc[cal.f1.idxmax(), "umbral_dnbr"])
    propia = perdida_propia(dnbr, dominio, mejor)
    m = matriz_acuerdo(propia, glad_p, dominio, este)
```

El umbral elegido se aplica sobre la mitad **este**, que el procedimiento
no ha visto.

**Por qué importa.** Calibrando y evaluando sobre los mismos píxeles, el
umbral se ajusta al ruido de esos píxeles y la métrica sale inflada. Es
de las primeras cosas que un jurado revisa.

### El barrido completo

Se prueban trece umbrales, de 0,10 a 0,70:

| Umbral | Precisión | Sensibilidad | F1 |
|---|---|---|---|
| 0,10 | 0,057 | 0,613 | 0,105 |
| 0,15 | 0,107 | 0,560 | 0,180 |
| 0,20 | 0,160 | 0,505 | 0,242 |
| 0,25 | 0,199 | 0,447 | 0,276 |
| 0,30 | 0,243 | 0,418 | 0,307 |
| **0,35** | 0,279 | 0,377 | **0,321** |
| 0,40 | 0,299 | 0,331 | 0,314 |
| 0,45 | 0,317 | 0,267 | 0,290 |
| 0,50 | 0,355 | 0,213 | 0,266 |
| 0,55 | 0,420 | 0,184 | 0,256 |
| 0,60 | 0,444 | 0,155 | 0,230 |
| 0,65 | 0,478 | 0,115 | 0,186 |
| 0,70 | 0,431 | 0,074 | 0,126 |

**El F1 hace pico en 0,35 y baja.** Pasado ese punto la precisión sigue
mejorando, de 0,28 a 0,48, pero la sensibilidad se cae de 0,38 a 0,12: se
marcan cada vez menos píxeles, los que quedan son más confiables, y se
pierde la mayor parte de la tala. El F1 castiga ese desbalance.

Que la curva suba, haga pico y baje es lo que permite afirmar que 0,35 es
el óptimo. Un máximo en el último valor probado no diría nada, porque el
verdadero óptimo podría estar más allá del rango.

> La primera versión del módulo probaba solo hasta 0,35 y por eso el
> umbral elegido caía en el borde de la búsqueda. Extender la rejilla
> hasta 0,70 no cambió el valor elegido, y sí volvió defendible la
> elección.

---

## Paso 11 — Las métricas

```python
    vp, fp, fn, vn = (m["ambos_ha"], m["solo_propia_ha"],
                      m["solo_glad_ha"], m["ninguno_ha"])
    prec = vp / (vp + fp)
    sens = vp / (vp + fn)
    f1 = 2 * prec * sens / (prec + sens)
```

Tomando GLAD-L como referencia:

- **Precisión**: de todo lo que marqué, ¿cuánto también marcó GLAD-L?
- **Sensibilidad**: de todo lo que marcó GLAD-L, ¿cuánto encontré?
- **F1**: media armónica de las dos.

```python
    "exactitud_global_no_informativa": round((vp + vn) / tot, 4)
```

El nombre de la clave lleva la advertencia incorporada. La exactitud
global dio **0,9864** y no dice nada útil: el bosque estable ocupa el
98 % del dominio, así que un detector que no marcara nada sacaría una
cifra parecida.

Se reporta porque suele pedirse, con ese nombre para que nadie la cite
por descuido.

---

### La curva de observabilidad

Un solo F1 esconde de qué depende el resultado. El dominio exige al menos
una observación limpia; si se sube esa barra, la concordancia mejora:

| Obs. mínimas | Cobertura | En el norte | Precisión | Sensibilidad | F1 |
|---|---|---|---|---|---|
| **1** (el dominio actual) | 100 % | 36,4 % | 0,549 | 0,467 | **0,505** |
| 2 | 99,5 % | 36,1 % | 0,550 | 0,467 | 0,505 |
| 3 | 95,9 % | 34,4 % | 0,556 | 0,464 | 0,506 |
| 4 | 71,7 % | 29,2 % | 0,570 | 0,489 | 0,526 |
| **6** | 43,4 % | 26,9 % | 0,590 | 0,537 | **0,562** |
| 8 | 15,9 % | 5,3 % | 0,635 | 0,650 | 0,642 |
| 10 | 4,1 % | **0,0 %** | 0,682 | 0,703 | **0,693** |

Se lee así: sobre el área completa el F1 es 0,505, y sobre el 43 % mejor
observado sube a 0,562. El método rinde donde tiene datos suficientes,
y el promedio general lo arrastran las 44 000 ha que solo alcanzaron tres
lecturas limpias.

El filtro es por **observabilidad** —cuántas veces se pudo ver el píxel—
y nunca por resultado. Filtrar por resultado sería quedarse con los
aciertos, que es otra cosa.

**La columna "en el norte" es la advertencia.** El número de
observaciones lo manda la geometría orbital: en el sur de la zona se
traslapan dos órbitas de Landsat y llegan 38 escenas, contra 19 en el
norte. Por eso, al exigir 10 observaciones, la proporción de área en el
norte cae a **cero**: esa fila ya no describe la zona, describe el tercio
sur.

Hasta 6 observaciones el área sigue repartida entre norte y sur, así que
el 0,562 se puede citar. El 0,693 solo se puede citar diciendo de qué
región se está hablando.

### Por qué la ventana se queda en tres meses

Más observaciones se consiguen componiendo más meses, y eso tiene un
costo: la pérdida que ocurre **dentro** de la ventana se promedia con el
estado anterior, y el dNBR sale intermedio.

Según las fechas de GLAD en esta zona, la pérdida de 2022-2023 se reparte
así: enero-marzo concentra el **13,6 %** del año, y enero-junio el
**29,8 %**. Pasar de tres a seis meses duplicaría la fracción de eventos
que se difuminan.

El intervalo entre compuestos no cambia —sigue siendo de doce meses,
porque ambos se corren igual— pero cada extremo pierde definición.

Este es un límite propio de los sensores ópticos en el trópico húmedo:
para ver hay que acumular meses, y acumular meses difumina el cuándo. Es
la razón por la que los sistemas operativos suman radar: Sentinel-1
atraviesa la nube, así que RADD no necesita componer medio año para
conseguir una lectura limpia.

---

## Paso 12 — La comparación por celda

```python
    px_celda = LADO_CELDA_M // ESCALA_M
    filas = np.arange(perfil["height"])[:, None] // px_celda
    cols = np.arange(perfil["width"])[None, :] // px_celda
    idx = (filas * (perfil["width"] // px_celda + 1) + cols).astype(np.int64)
    cuenta = lambda m: np.bincount(idx[m], minlength=n) * ha
```

Agrupa los píxeles en celdas de 5 × 5 km y suma hectáreas por celda, para
cada fuente. El índice de celda sale de dividir la coordenada de píxel
entre el lado de la celda, igual que en `zonal.py`.

**Por qué esta es la comparación relevante.** El modelo predictivo del
proyecto trabaja a escala de celda de 5 km. Dos productos
pueden discrepar píxel a píxel por medio píxel de desplazamiento y aun
así coincidir muy bien en **cuánta pérdida hay en cada celda**, que es lo
que el modelo necesita.

```python
    df = df[df.dominio_ha > 0].copy()
```

Las celdas sin dominio se descartan. En ellas no había dónde mirar, así
que incluirlas inflaría la correlación.

### Dos formas de medir si coinciden: Pearson y Lin

Para cada celda hay dos números: las hectáreas que marca GLAD-L y las que
marca la demo. Algunas celdas de la mitad este:

| Celda | GLAD-L | Demo |
|---|---|---|
| 212 | 224 ha | 303 ha |
| 229 | 167 ha | 198 ha |
| 211 | 149 ha | 163 ha |
| 230 | 149 ha | 103 ha |
| 213 | 34 ha | 23 ha |
| 124 | 13 ha | 12 ha |
| 87 | 6 ha | 9 ha |
| 15 | 0 ha | 0 ha |

**El Pearson mide si las dos columnas suben y bajan juntas.** Donde GLAD-L
marca mucho, ¿la demo también? Donde marca poco, ¿la demo también? Va de
−1 a 1: 1 es que siempre suben y bajan juntas, 0 que no tienen relación,
−1 que van al revés. Con las 160 celdas da **0,909**. Si se barajan las
celdas al azar, cae a casi cero.

**El Pearson no mira la cantidad.** Si la demo reportara el doble en todas
las celdas, el Pearson seguiría en 0,909, porque las columnas seguirían
subiendo y bajando juntas.

**La concordancia de Lin mide lo mismo y además exige que los números sean
iguales.** Se lee igual, de −1 a 1, pero castiga que una fuente reporte
más que la otra:

| | Pearson | Lin |
|---|---|---|
| Demo vs GLAD-L, tal como está | 0,909 | **0,902** |
| Si la demo reportara el doble | 0,909 | **0,668** |

```python
    cov = float(((x - x.mean()) * (y - y.mean())).mean())
    den = float(x.var() + y.var() + (x.mean() - y.mean()) ** 2)
    return 2 * cov / den if den else float("nan")
```

El denominador suma la diferencia de medias al cuadrado: si una fuente
reporta en promedio más que la otra, el coeficiente baja. Lin nunca
supera al Pearson, y solo lo iguala cuando las dos series tienen la misma
media y la misma dispersión.

Por eso **Lin es la medida que conviene poner como titular**: responde la
pregunta del panel, si una fuente dice lo mismo que la otra en cada celda,
en dónde y en cuánto. El Pearson se sigue reportando porque es el que la
mayoría conoce, y la distancia entre los dos dice cuánto pesa la
diferencia de cantidad.

> Lin, L. I-K. (1989). A concordance correlation coefficient to evaluate
> reproducibility. *Biometrics*, 45(1), 255–268.

---

## Paso 13 — La muestra para validación visual

```python
    estratos = {
        "ambos": d & propia & glad,
        "solo_propia": d & propia & ~glad,
        "solo_glad": d & ~propia & glad,
        "ninguno": d & ~propia & ~glad,
    }
    sel = rng.choice(len(f), size=k, replace=False)
```

Cincuenta puntos por cada una de las cuatro combinaciones, siguiendo la
práctica recomendada para estimación de área y exactitud (Olofsson et
al., 2014).

**La muestra es estratificada.** Las clases de cambio ocupan una
fracción minúscula de la escena: `ambos` es el 0,7 % del dominio. Una
muestra aleatoria simple de 200 puntos caería casi entera en bosque
estable, y los desacuerdos, que son lo que hay que revisar, quedarían con
uno o dos puntos.

```python
        filas.append(pd.DataFrame({..., "etiqueta_visual": ""}))
```

La columna sale vacía a propósito. La llena un humano mirando imagen de
alta resolución, y de ahí salen los errores de omisión y comisión que
permiten corregir el área estimada.

**Este paso está pendiente.** El CSV está generado con sus 200 puntos,
pero nadie los ha interpretado todavía. Hasta que eso ocurra, la demo
mide **concordancia con GLAD-L**, no exactitud.

---

## Los resultados, interpretados

Sobre la mitad este, que la calibración nunca vio. Para saber si estas
cifras son buenas o malas, ver
[¿Es bueno un F1 de 0,505?](#es-bueno-un-f1-de-0505), que las compara con
cuánto concuerdan entre sí los productos profesionales.

| Métrica | Valor |
|---|---|
| **Concordancia de Lin, hectáreas por celda de 5 km** | **0,902** |
| Pearson, por celda | 0,909 |
| Spearman, por celda | 0,795 |
| Precisión, a nivel de píxel | 0,549 |
| Sensibilidad, a nivel de píxel | 0,467 |
| F1, a nivel de píxel | 0,505 |

Matriz de acuerdo, sobre 180 450 ha de dominio:

| | Hectáreas |
|---|---|
| Detectado por ambos | 1 251 |
| Solo por el método propio | 1 026 |
| Solo por GLAD-L | 1 430 |
| Por ninguno | 176 743 |

### La lectura central

**A nivel de píxel la coincidencia es moderada; a la escala de 5 km sube
a 0,91.**

Esa brecha entre escalas es el hallazgo principal. Los dos métodos
discrepan sobre qué píxel exacto marcar, y coinciden bien sobre dónde
está ocurriendo la pérdida y cuánta hay. Lo segundo es lo que el modelo
necesita.

La explicación es geométrica: un claro de 3 ha detectado por ambos puede
tener los bordes desplazados uno o dos píxeles, lo que castiga la
precisión por píxel sin afectar el total por celda.

### Qué dicen los desacuerdos

Las 1 026 ha "solo propia" y las 1 430 ha "solo GLAD" pueden venir de
varias cosas:

- Diferencias de fecha: el compuesto ve el estado a mitad de la ventana,
  GLAD-L alerta en el momento de la detección.
- Diferencias de sensibilidad: dNBR detecta cambios graduales que GLAD-L
  clasifica como no confirmados.
- Errores genuinos de cualquiera de los dos.

Para distinguir cuál es cuál hace falta la validación visual del paso 13.

---

## Por qué los resultados son como son

El F1 por píxel es 0,505 y la correlación por celda de 5 km es 0,909. Esa
diferencia no es un accidente de las cifras: tiene causas concretas, y
tres de ellas se pueden medir.

### El fondo del asunto

El método le pide a un solo número —el dNBR— que conteste una pregunta de
sí o no. Eso funcionaría si el bosque diera valores bajos y la tala
valores altos, con un hueco en el medio donde poner la raya.

No pasa eso. Hay bosque intacto con dNBR alto y hay tala real con dNBR
bajo. Los dos grupos **se traslapan**, y dentro del traslape cualquier
umbral se equivoca. Lo que sigue explica de dónde sale ese traslape.

### Causa 1 — Los bordes de un claro son mitad y mitad

Cada píxel es un cuadro de 30 × 30 m, y el satélite entrega **un solo
valor por cuadro**: el promedio de todo lo que hay dentro.

Cuando se tumba monte, el claro no queda alineado con la cuadrícula. Su
orilla parte varios píxeles por la mitad, y esos píxeles quedan con mitad
árboles y mitad suelo desnudo.

Con cifras redondas: si un píxel de puro bosque marca 0,85 y uno de puro
claro marca 0,15, entonces tumbar el píxel completo lo hace caer 0,70 —
muy por encima de la raya de 0,35. Pero un píxel partido por la mitad cae
aproximadamente la mitad: **0,35 justo**.

Ahí no hay respuesta correcta. Contarlo entero sobreestima el área;
descartarlo la subestima. El umbral tiene que elegir una de las dos.

Como esos píxeles de orilla caen justo por encima de la raya, el método
los cuenta, y **cada claro sale con un anillo de más**. GLAD-L no los
cuenta, porque exige confirmación en varias fechas y la orilla es
dudosa.

### Causa 2 — La mediana de tres lecturas no es confiable

De las 38 escenas del trimestre, el píxel mediano tuvo **5 observaciones
limpias en T1 y 3 en T2**: la nubosidad descartó el 85 %.

Sacar la mediana de tres valores es frágil. Si uno de los tres traía nube
residual que la máscara no atrapó, el dNBR de ese píxel es ruido, y nada
lo delata.

Esto es lo que más pesa, y se mide en `curva_observabilidad.csv`, que
trae la misma cuenta leída de dos formas.

**Por tramo exacto**, o sea mirando solo los píxeles que tuvieron
exactamente ese número de lecturas:

| Observaciones | Cobertura | F1 |
|---|---|---|
| 3 | 24,2 % | **0,285** |
| 4–5 | 28,3 % | 0,362 |
| 6–9 | 39,3 % | 0,529 |
| 10 o más | 4,1 % | **0,693** |

Mismo método, mismo umbral, misma zona. Lo único que cambia es cuántas
veces se pudo ver el píxel, y el F1 se multiplica por dos y medio. Las
44 000 ha que solo alcanzaron tres lecturas son las que arrastran el
promedio general hacia 0,505.

**Por tramo acumulado**, o sea qué pasaría si el dominio subiera su barra:

| Exige al menos | Cobertura | F1 |
|---|---|---|
| 1 (el dominio actual) | 100 % | 0,505 |
| 4 | 71,7 % | 0,526 |
| 6 | 43,4 % | **0,562** |
| 10 | 4,1 % | 0,693 |

> **Las filas exactas de pocas observaciones hay que leerlas con
> cuidado.** Recortar el dominio a esos píxeles los deja dispersos, y el
> filtro de parche exige 12 píxeles conexos *dentro* del dominio. Con una
> sola observación no se forma ningún parche y el F1 sale 0,000 por
> construcción, no porque el método falle ahí. El efecto se diluye a
> medida que el tramo cubre más área, así que las filas de 4 en adelante
> son las fiables.

### Causa 3 — Un solo umbral para toda la zona

El 0,35 se aplica igual en los 7,6 millones de píxeles. Pero tumbar
bosque tupido produce una caída grande, y tumbar bosque ya degradado
produce una caída pequeña.

Un umbral único no puede servir para los dos casos: el que funciona en el
bosque denso deja pasar la tala en el degradado, y al revés. Un
clasificador entrenado sobre varias variables sí podría distinguirlos,
pero para eso hacen falta etiquetas (ver el paso 13).

### Y una causa que no es del método

GLAD-L tampoco acierta siempre. Parte de lo que aquí se cuenta como error
propio es error suyo. Cuáles son cuáles no se sabe sin interpretar las
imágenes a mano.

---

### Comprobación 1: las capas no están corridas

La explicación fácil sería un desajuste geométrico entre las fuentes. Se
descarta desplazando la capa propia y midiendo el F1 en cada posición:

| | −2 | −1 | **0** | +1 | +2 |
|---|---|---|---|---|---|
| **−2** | 0,398 | 0,424 | 0,440 | 0,436 | 0,416 |
| **−1** | 0,421 | 0,456 | 0,479 | 0,477 | 0,450 |
| **0** | 0,433 | 0,475 | **0,505** | 0,503 | 0,469 |
| **+1** | 0,427 | 0,467 | 0,498 | 0,496 | 0,465 |
| **+2** | 0,409 | 0,443 | 0,465 | 0,465 | 0,443 |

El máximo está exactamente en (0, 0) y cae en todas direcciones. Con un
corrimiento de un píxel, el pico aparecería desplazado. **No hay
desajuste de alineación**, y la reproyección común sobre la rejilla de
trabajo está haciendo su trabajo.

### Comprobación 2: los dos tipos de error tienen forma distinta

Midiendo a qué distancia está cada píxel en desacuerdo del píxel de
acuerdo más cercano:

| Distancia al acuerdo más cercano | Solo propia | Solo GLAD-L |
|---|---|---|
| Pegado (1 px) | 399,5 ha | 162,7 ha |
| 2–3 px | 116,9 ha | 71,9 ha |
| 3–6 px | 95,3 ha | 84,7 ha |
| 6–16 px | 113,0 ha | 211,7 ha |
| Más de 16 px | 301,6 ha | **899,3 ha** |
| **En el borde (≤ 3 px)** | **50 %** | **16 %** |

Los dos errores son cosas diferentes:

- **Lo que marco de más está pegado a claros reales.** La mitad, a tres
  píxeles o menos de un acuerdo. Es la causa 1: el anillo de orilla.
- **Lo que se me escapa son claros enteros.** 899 ha —el 63 %— a más de
  medio kilómetro de cualquier acuerdo. No son bordes mal cortados: son
  eventos que no vi, en su mayoría por la causa 2.

### Comprobación 3: a 5 km los errores se cancelan

| | Hectáreas |
|---|---|
| Desacuerdo bruto (solo propia + solo GLAD) | 2 457 |
| Error neto por celda (\|mi total − total GLAD\|) | 1 222 |
| **Se cancela dentro de las celdas** | **50 %** |

Por celda con desacuerdo, la mediana del desacuerdo bruto es 14,3 ha y la
del error neto 7,4 ha.

Ahí está la explicación de la brecha entre escalas. Sobredetecto 1 026 ha
y subdetecto 1 430 ha; dentro de una celda de 2 500 ha esas dos cosas se
compensan, y el anillo que le sobro a un claro tapa el claro vecino que
se me escapó. A nivel de píxel esa compensación no existe: un píxel está
bien o está mal.

> **Esa cancelación es una propiedad de esta zona, no una virtud del
> método.** Funciona porque los dos tipos de error andan parecidos en
> magnitud. En una región donde la sobredetección dominara, el total por
> celda se iría hacia arriba y la correlación caería aunque el F1 por
> píxel fuera el mismo. Lo defendible es decir que *en esta zona los
> errores se compensan y el agregado por celda queda bien*.

### Cuántos claros se detectan, no cuántos píxeles

El F1 por píxel castiga igual dos errores que no son iguales: inventarse
un claro donde no lo hay, y encontrar el claro correcto con el contorno
un poco ancho. Para un panel que tamiza municipios, lo segundo importa
poco — lo que se necesita saber es si el evento quedó señalado.

`deteccion_por_parche.csv` mide eso: agrupa cada capa en claros y cuenta
cuántos de una son tocados por al menos un píxel de la otra, sin exigir
que coincida el contorno.

**De los claros que reporta GLAD-L, cuántos encuentra la demo:**

| Tamaño del claro | Claros | Encontrados | % | % del área |
|---|---|---|---|---|
| 1–3 ha | 292 | 66 | **23 %** | 25 % |
| 3–10 ha | 164 | 71 | 43 % | 46 % |
| 10–30 ha | 48 | 37 | **77 %** | 80 % |
| Más de 30 ha | 8 | 7 | **88 %** | 94 % |
| **Todos** | **512** | **181** | **35 %** | **62 %** |

**De los claros que reporta la demo, cuántos confirma GLAD-L:**

| Tamaño del claro | Claros | Confirmados | % | % del área |
|---|---|---|---|---|
| 1–3 ha | 108 | 49 | 45 % | 49 % |
| 3–10 ha | 81 | 56 | 69 % | 70 % |
| 10–30 ha | 48 | 41 | 85 % | 86 % |
| Más de 30 ha | 15 | 15 | **100 %** | 100 % |
| **Todos** | **252** | **161** | **64 %** | **86 %** |

### Cómo se leen esas tablas

**Los claros grandes se detectan de forma confiable.** 7 de los 8 claros
de más de 30 ha, y 37 de los 48 de 10 a 30 ha. En la otra dirección, los
15 claros propios de más de 30 ha están todos confirmados.

**Los pequeños se escapan.** De 292 claros de 1 a 3 ha, la demo encuentra
66. Esos claros miden entre 12 y 33 píxeles: es justo el tamaño donde
tres observaciones limpias no bastan para separar la señal del ruido.

**Los dos totales dicen cosas distintas y los dos son ciertos.** El
conteo simple da 35 % porque trata igual un claro de 1 ha y uno de 100, y
los pequeños son mayoría en número. El ponderado por área da 62 % porque
los pequeños aportan poca hectárea. Citar uno sin el otro engaña.

### Qué corrige esto sobre el F1

**El F1 es injustamente duro en un aspecto.** El anillo de orilla lo
cuenta como claro inventado, cuando es un claro real con el contorno
ancho. Por eso el 86 % del área que marca la demo queda confirmada por
GLAD-L: casi todo lo que señala corresponde a algo que existe.

**Y es justo en el otro.** La demo no vio 331 de los 512 claros, y 319 de
esos son menores de 10 ha. Son omisiones reales, y ahí el F1 tiene razón
en castigar.

La forma correcta de enunciar el resultado, entonces, no es que el F1 sea
mejor de lo que parece, sino esto:

> La demo **encuentra los claros grandes de forma confiable** —88 % de
> los de más de 30 ha, 77 % de los de 10 a 30 ha— y **se le escapan los
> pequeños**, porque con tres observaciones limpias no hay señal
> suficiente para distinguirlos del ruido. Por área captura el 62 % de la
> pérdida que reporta GLAD-L, y el 86 % de lo que detecta queda
> confirmado.

Para un panel cuya unidad es la celda de 5 km, eso alcanza: lo que mueve
una cifra agregada son los claros grandes, no los de hectárea y media.

---
### Qué se puede arreglar

| Causa | ¿Arreglable? | Cómo |
|---|---|---|
| Bordes mitad y mitad | No del todo | Es el tamaño del píxel. Se reduce con sensores de 10 m (Sentinel-2) |
| Pocas lecturas limpias | Sí, con costo | Componer más meses difumina el cuándo; el radar lo resuelve sin ese costo |
| Umbral único | Sí | Un clasificador sobre varias variables, una vez haya etiquetas |
| Errores de GLAD-L | No aplica | Solo se separan con interpretación visual |

La causa 2 es la que más pesa y la que explica por qué los sistemas
operativos integran radar: Sentinel-1 atraviesa la nube, así que RADD no
necesita acumular meses para conseguir una lectura limpia.

---

## ¿Es bueno un F1 de 0,505?

A simple vista parece bajo. Pero un F1 suelto no dice si un resultado es
bueno o malo. Para leerlo hacen falta tres cosas: saber qué castiga,
compararlo con cuánto concuerdan entre sí los productos profesionales, y
ponerlo al lado de medidas a la escala en que se usa el dato. Esta
sección hace las tres.

### Qué castiga el F1 por píxel

Exige que las dos capas marquen **exactamente el mismo cuadro de 30 m**.
Castiga por igual cuatro situaciones:

1. Marcar un claro que la otra capa no tiene.
2. No ver un claro que la otra capa sí tiene.
3. Ver el claro correcto, pero con el borde uno o dos píxeles más afuera.
4. Reportar más o menos área total que la otra capa.

Solo las dos primeras son fallas de detección. La tercera es el anillo de
orilla explicado en
[Por qué los resultados son como son](#por-qué-los-resultados-son-como-son),
y la cuarta depende de cómo define cada producto qué cuenta como
pérdida. En esta demo las dos últimas pesan bastante.

### El punto de referencia: cuánto concuerdan los productos profesionales

La pregunta útil es: si se miden con la misma vara, ¿cuánto concuerdan
entre sí productos hechos por equipos profesionales?

`referencia_entre_productos.csv` lo mide en cada corrida, en la mitad
este, con el mismo dominio de bosque y el mismo filtro de parche que la
demo. Los productos se comparan en el año calendario 2022:

- **GLAD-L**: las alertas confirmadas de la Universidad de Maryland.
- **Hansen**: la pérdida anual de cobertura arbórea, también de Maryland,
  producida con el año ya cerrado.
- **IDEAM**: la capa oficial de cambio de bosque de Colombia. Se excluyen
  los píxeles que el IDEAM marca sin información.

| Par | F1 por píxel | Pearson por celda | Lin por celda |
|---|---|---|---|
| **Demo vs GLAD-L** | **0,505** | **0,909** | **0,902** |
| Hansen vs GLAD-L | 0,436 | 0,889 | 0,472 |
| IDEAM vs GLAD-L | 0,460 | 0,904 | 0,757 |
| IDEAM vs Hansen | 0,611 | 0,939 | 0,763 |

**Tres productos profesionales concuerdan entre sí, por píxel, entre 0,44
y 0,61.** El 0,505 de la demo cae en ese rango. Y en la escala del panel,
la celda de 5 km, su Pearson de 0,909 también: los productos van de
0,889 a 0,939.

El F1 por píxel es bajo para todos. Es una vara muy exigente, y dos
mapas de deforestación rara vez coinciden cuadro por cuadro aunque los
hagan equipos expertos.

La columna de Lin muestra lo que el Pearson esconde. Hansen y GLAD-L
coinciden bien en **dónde** hay pérdida (Pearson 0,889), pero Hansen
reporta 3,5 veces más área, y Lin cae a 0,472. Los productos difieren en
cantidad porque miden cosas distintas: alertas confirmadas, pérdida de
cobertura arbórea y deforestación según la definición oficial de bosque.

### Por qué esa tabla no permite decir que la demo es mejor

La demo supera en F1 a dos de los tres pares de productos. Eso no
significa que detecte mejor que ellos, por una razón concreta: **las
capas no reportan la misma cantidad de área**.

| Par | Área de la primera | Área de la segunda | Razón |
|---|---|---|---|
| Demo vs GLAD-L | 2 277 ha | 2 681 ha | 0,85 |
| Hansen vs GLAD-L | 11 860 ha | 3 329 ha | **3,56** |
| IDEAM vs GLAD-L | 6 548 ha | 3 329 ha | 1,97 |
| IDEAM vs Hansen | 6 548 ha | 11 859 ha | 0,55 |

Cuando dos capas difieren en área, el F1 tiene un **techo** aunque la
chica esté completamente dentro de la grande:

```
techo del F1 = 2 × área menor / (área mayor + área menor)
```

Un ejemplo: si una capa marca 100 ha y la otra 300, y las 100 están
todas dentro de las 300, el F1 no puede pasar de 2 × 100 / 400 = 0,50.

| Par | F1 | Techo | Parte del techo alcanzada |
|---|---|---|---|
| Demo vs GLAD-L | 0,505 | 0,919 | 55 % |
| Hansen vs GLAD-L | 0,436 | 0,438 | **99 %** |
| IDEAM vs GLAD-L | 0,460 | 0,674 | 68 % |
| IDEAM vs Hansen | 0,611 | 0,711 | 86 % |

Hansen contra GLAD-L está en su techo: prácticamente todo lo que marca
GLAD-L está dentro de lo que marca Hansen, que encuentra el 100 % del
área de GLAD-L. Su F1 es bajo porque Hansen reporta el triple de área, no
porque pongan la pérdida en lugares distintos. Las alertas confirmadas
de GLAD-L son conservadoras frente al producto anual de Hansen.

La demo está en el otro extremo. Su umbral se calibró contra GLAD-L, así
que reporta casi la misma área y su techo es alto. Lo que le baja el F1
es **dónde** pone la pérdida.

Entonces: **los productos discrepan entre sí sobre todo en cuánto; la
demo discrepa con GLAD-L sobre todo en dónde.** Son desacuerdos de
distinta naturaleza y no se pueden ordenar de mejor a peor. Lo que sí se
puede afirmar es que la concordancia de la demo con GLAD-L está en el
mismo rango que la de los productos profesionales entre sí.

Lo mismo vale para Lin. La demo saca 0,902 y los productos entre 0,47 y
0,76 porque el umbral de la demo se calibró contra GLAD-L, y eso la lleva
a reportar casi la misma cantidad. Ese 0,902 dice que la réplica quedó
cerca de GLAD-L, que era su propósito; no dice que mida mejor que Hansen o
el IDEAM.

### Qué pasa si se perdona el borde

`f1_con_tolerancia()` cuenta como acierto todo píxel que tenga uno de la
otra capa a 1 o 2 píxeles de distancia. Así se aparta el error de
contorno:

| Par | F1 exacto | Tolerancia 1 píxel (30 m) | Tolerancia 2 píxeles (60 m) |
|---|---|---|---|
| Demo vs GLAD-L | 0,505 | 0,615 | 0,646 |
| Hansen vs GLAD-L | 0,436 | 0,624 | 0,686 |
| IDEAM vs GLAD-L | 0,460 | 0,630 | 0,694 |
| IDEAM vs Hansen | 0,611 | 0,734 | 0,779 |

Aceptando 30 m de corrimiento, la demo sube de 0,505 a 0,615. Los
productos suben más, y con tolerancia la demo queda en el extremo bajo
del rango. Eso es coherente con lo que ya se sabía: además del borde, la
demo tiene un error propio, los claros pequeños que no ve.

### Una medida para cada pregunta

Ninguna medida sola describe la concordancia. Cada una contesta una
pregunta distinta:

| Pregunta | Medida | Demo vs GLAD-L | Entre productos |
|---|---|---|---|
| ¿Dice lo mismo en cada celda, en dónde y en cuánto? | Concordancia de Lin por celda de 5 km | **0,902** | de 0,47 a 0,76 |
| ¿Coincide en qué celdas pierden más, sin mirar cuánto? | Pearson por celda de 5 km | 0,909 | de 0,89 a 0,94 |
| ¿Reporta la misma cantidad de área? | Razón de áreas | 0,85 | de 0,55 a 3,56 |
| ¿Marca exactamente los mismos píxeles? | F1 por píxel | 0,505 | de 0,44 a 0,61 |
| ¿Los mismos, perdonando 30 m de borde? | F1 con tolerancia de 1 píxel | 0,615 | de 0,62 a 0,73 |
| ¿Ve la pérdida que marca la referencia? | % del área de la referencia hallada | 62 % | de 81 % a 100 % |
| ¿Lo que marca existe en la referencia? | % del área propia confirmada | 86 % | de 73 % a 98 % |

El "% hallado" de los productos sale alto en parte porque varios
reportan mucha más área que GLAD-L: con el triple de área es fácil tocar
todo lo que marca la otra capa.

### Entonces, ¿los datos son buenos o malos?

**Son buenos para:**

- Saber **dónde y cuánta** pérdida hay a escala de 5 km. La concordancia
  de Lin por celda es 0,902, y la correlación de Pearson, 0,909, está en
  el rango de los productos profesionales entre sí.
- Los **claros grandes**: encuentra el 88 % de los de más de 30 ha y el
  77 % de los de 10 a 30 ha.
- Confiar en lo que marca: el **86 %** del área que señala la demo
  también la señala GLAD-L.

**Son malos para:**

- Los **claros pequeños**: encuentra el 23 % de los de 1 a 3 ha.
- **Dibujar el contorno exacto** de cada claro: el anillo de orilla lo
  engorda.
- Las zonas con **pocas lecturas limpias**: con tres observaciones el F1
  cae a 0,285.
- El **área total**: queda un 15 % por debajo de GLAD-L.

Y todo lo anterior es concordancia con GLAD-L, no exactitud contra el
terreno. Para eso hace falta la validación visual del paso 13.

### Cómo reportarlo

No conviene citar el F1 solo. El orden recomendado es este:

1. **Como titular, la concordancia de Lin por celda de 5 km (0,902).** Es
   la escala del panel, y junta en un número el dónde y el cuánto.
2. **Al lado, la razón de áreas (0,85) y la detección por tamaño de
   claro** (88 % de los mayores de 30 ha, 23 % de los de 1 a 3 ha).
3. **El F1 por píxel (0,505), siempre con el rango de los productos entre
   sí** (0,44 a 0,61). Sin esa referencia cualquiera lo lee como malo, y
   un jurado lo va a pedir.

Al citar el Lin hay que decir que el umbral se calibró contra GLAD-L:
parte de que la demo reporte casi lo mismo viene de esa calibración. Una
forma de decirlo:

> A la escala de celda de 5 km, la réplica concuerda con GLAD-L con un
> coeficiente de Lin de 0,902, con el umbral calibrado contra GLAD-L en
> otra mitad de la zona; en total reporta un 15 % menos de área. A nivel
> de píxel el F1 es 0,505, en el rango en que concuerdan entre sí GLAD-L,
> Hansen y el IDEAM medidos con la misma vara (0,44 a 0,61). El método
> encuentra los claros grandes de forma confiable y pierde la mayoría de
> los menores de 3 ha.

---

## Dónde se ubica este método

Hay muchas formas de detectar pérdida de bosque con satélite. Conviene
verlas como un espectro, con dos extremos:

| | Regla simple sobre un índice | Modelo entrenado |
|---|---|---|
| **Ejemplo** | Esta demo: NBR con un umbral | GLAD-L: árboles de decisión |
| **Qué usa por píxel** | Un número (el dNBR) | Muchas variables espectrales y temporales |
| **Qué aprende** | Un parámetro: dónde va la raya | Cientos de reglas combinadas |
| **Con qué aprende** | Comparando contra un producto publicado | Muestras interpretadas a mano |
| **Fechas que mira** | Dos compuestos, uno por año | La serie de tiempo completa |

Entre los dos extremos, y a los lados, hay otros enfoques: modelos de
serie temporal que ajustan la trayectoria completa de cada píxel
(LandTrendr, CCDC, BFAST), detección con radar que atraviesa la nube
(RADD) y redes neuronales entrenadas sobre imágenes. Esta demo está en el
extremo más simple.

### Las dos diferencias con GLAD-L

**El tipo de modelo.** La demo decide con una sola raya sobre un solo
número. GLAD-L combina muchas variables con árboles de decisión. Un
umbral sobre el dNBR equivale a un árbol de un solo nodo: es el miembro
más simple de la misma familia.

**Las fechas.** La demo compara dos compuestos. GLAD-L sigue cada píxel en
todas las pasadas del satélite y confirma cada alerta con varias
observaciones.

La segunda diferencia pesa tanto como la primera. El problema principal
de la demo resultó ser la falta de observaciones limpias (ver
[Por qué los resultados son como son](#por-qué-los-resultados-son-como-son)),
y eso GLAD-L lo resuelve con la serie temporal, no con los árboles.

### Qué cuesta cada extremo

En tiempo de computador, casi nada en ambos casos. Entrenar un bosque
aleatorio de 300 árboles sobre 2 000 puntos toma 0,4 segundos, y
aplicarlo a los 7,6 millones de píxeles de la zona toma unos 11 segundos.
La demo ya gasta 13 minutos descargando imágenes.

El costo del modelo entrenado son **las etiquetas**: alguien tiene que
mirar imagen de alta resolución y decidir, píxel por píxel, si hubo tala.
Para 200 puntos son unas horas. Para un producto como GLAD-L, que cubre
todo el trópico húmedo y se mantiene durante años, es el trabajo de un
equipo.

Esta demo no usa etiquetas propias, pero tampoco trabaja sin referencia:
el umbral de 0,35 se calibró contra GLAD-L en la mitad oeste. Tiene un
solo parámetro, y ese parámetro se ajustó con datos.

### Por qué el extremo simple sirve para entender

Para el propósito de esta demo, el extremo simple tiene una ventaja
concreta: cada paso se puede leer, explicar y cambiar. Se ve qué índice
se usa, dónde queda la raya y qué pasa con cada píxel. Un clasificador
con cientos de reglas se acercaría más a GLAD-L, pero explicaría menos
por qué.

### Por qué no se entrenó un modelo con GLAD-L como etiqueta

Sería circular. El modelo aprendería a reproducir GLAD-L, y después
compararlo contra GLAD-L no mediría nada.

Con un solo parámetro esa circularidad queda acotada: la partición
este/oeste evita el sobreajuste, y lo que se mide es cuánto se acerca un
método de un parámetro a un clasificador operativo. Con cientos de
parámetros, el modelo simplemente copiaría.

El camino limpio es etiquetar a mano la muestra de `muestra_validacion_visual.csv`
y entrenar sobre esas etiquetas. Así el modelo nunca ve a GLAD-L, y la
comparación vuelve a significar algo.

### En resumen

> Hay un espectro de métodos. En un extremo está una regla simple sobre
> un índice espectral; en el otro, modelos entrenados con muestras
> etiquetadas a mano y con la serie temporal completa, como GLAD-L. Esta
> demo usa el extremo simple: el NBR con un umbral calibrado contra
> GLAD-L. No requiere etiquetas, y el precio es que pierde los claros
> pequeños y depende mucho de cuántas imágenes sin nube haya. Donde hubo
> suficientes observaciones, el desempeño mejora bastante.

---

## Límites de la demo

Conviene tenerlos claros antes de presentarla:

**No es un indicador propio.** Es una réplica en una zona piloto de
89 × 77 km, con un par de fechas y un solo índice, hecha para entender el
cálculo. El producto de GFW integra tres sistemas, cobertura continua y
una escala de confianza validada.

**Mide concordancia, no exactitud.** Sin la interpretación visual de los
200 puntos no hay verdad de campo contra la cual medirse.

**La detección propia no se comparó directamente con el dato oficial.**
El IDEAM entra en la referencia entre productos, pero la demo solo se
contrasta con GLAD-L, cuya ventana de fechas coincide con la suya.
Compararla con el IDEAM exigiría mover las fechas objetivo al año
calendario.

**Un umbral único para toda la zona.** El 0,35 se aplica igual en los
2968 × 2581 píxeles. Un bosque más seco o con otra estructura responde
distinto, así que el valor que sirve aquí no necesariamente sirve en otra
región del país.

**El año que mide va de febrero a febrero.** El IDEAM reporta del 1 de
enero al 31 de diciembre; esta demo mide entre dos compuestos centrados
cerca del 1 de febrero de 2022 y del 19 de febrero de 2023. Las fechas
objetivo se pueden mover, porque el método mide la pérdida entre dos
fechas cualesquiera, pero tienen que caer en meses secos: son los únicos
con suficientes lecturas limpias.

**Un solo índice y una sola fecha por año.** Los productos operativos
usan series temporales completas y varios índices. Esta demo usa dos
compuestos y el NBR.

---

## Preguntas para más adelante

Entender cómo se calculan los datos deja preguntas que los productos
publicados no contestan. Esta demo es el lugar al que habría que volver
para responderlas, porque aquí cada paso del cálculo está a la vista y
se puede cambiar.

### ¿Cómo se sabe cuánto se deforestó en un departamento?

Hoy la respuesta tiene dos pasos, y cada uno lleva una decisión.

**Del píxel a hectáreas.** GLAD-L, Hansen, el IDEAM y esta demo cuentan
cada píxel marcado con su área completa: 0,09 ha a 30 m. La magnitud del
cambio espectral solo decide si el píxel se marca o no. Un píxel donde el
NBR cayó 0,36 y otro donde cayó 0,90 suman lo mismo.

**De hectáreas a departamento.** El panel suma por celdas de 5 km, y
cada celda se asigna completa al departamento donde cae su centroide
(`exportar_grilla.py`). Una celda partida por un límite departamental
cuenta entera para un solo lado.

De ahí salen tres preguntas abiertas:

- **¿Debe pesar igual todo píxel marcado?** El anillo de orilla (ver
  [Por qué los resultados son como son](#por-qué-los-resultados-son-como-son))
  muestra lo que cuesta no ponderar: los píxeles que el borde de un claro
  parte por la mitad cuentan enteros. Una alternativa sería estimar qué
  fracción de cada píxel se perdió a partir de cuánto cayó el índice, y
  sumar fracciones en lugar de píxeles enteros. La demo ya tiene el dNBR
  de cada píxel, así que esa prueba se puede hacer aquí.
- **¿Qué magnitud de cambio cuenta como deforestación?** Hoy la decide un
  umbral calibrado contra GLAD-L. Otra referencia, u otro uso del dato,
  podría justificar otro umbral.
- **¿Cómo se reparten las celdas de frontera?** En un departamento grande
  el efecto es pequeño; en un municipio pequeño, cubierto por pocas
  celdas, puede no serlo. La alternativa es repartir cada celda según la
  fracción de su área que cae en cada unidad.

### Cómo se abordarían

Con el mismo camino que siguió esta demo: primero replicar lo que hacen
los productos publicados, y después cambiar una decisión a la vez y ver
cuánto se mueve la cifra agregada. La vara para juzgar cada cambio sería
el dato oficial agregado, porque el IDEAM reporta también por
departamento y la agregación de sus capas en este proyecto ya reproduce
su cifra nacional (ver `METODOLOGIA.md`, sección 8).

---

## Cómo volver a correrlo

```powershell
python demo_landsat_caqueta.py
```

La primera vez toma unos 13 minutos. Las siguientes, segundos, porque los
compuestos quedan en `datos/demo/cache_nbr_*.npz`.

Para forzar el recálculo, por ejemplo tras cambiar las fechas, basta
borrar ese archivo. Si cambia el `BBOX` o la rejilla, el caché se
invalida solo, porque la clave del archivo los incluye.
