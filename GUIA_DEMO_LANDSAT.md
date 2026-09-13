# Cómo se deriva deforestación desde Landsat, paso a paso

Recorrido completo de [`demo_landsat_caqueta.py`](demo_landsat_caqueta.py):
qué hace cada bloque de código, por qué está escrito así, y qué significa
cada número del resultado.

Este documento asume que ya leyó [`METODOLOGIA.md`](METODOLOGIA.md)
sección 1.2, donde se explica qué mide cada fuente del proyecto.

---

## Índice

1. [Qué problema resuelve](#1-qué-problema-resuelve)
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
15. [Paso 11 — Las métricas, y cuál mentiría](#paso-11--las-métricas-y-cuál-mentiría)
16. [Paso 12 — La comparación que de verdad importa](#paso-12--la-comparación-que-de-verdad-importa)
17. [Paso 13 — La muestra para validación visual](#paso-13--la-muestra-para-validación-visual)
18. [Los resultados, interpretados](#los-resultados-interpretados)
19. [Lo que esta demo no demuestra](#lo-que-esta-demo-no-demuestra)

---

## 1. Qué problema resuelve

El panel del proyecto usa productos ya procesados: alertas de GFW,
pérdida de Hansen, capas del IDEAM. Alguien puede preguntar, con razón,
si el trabajo consiste solo en descargar y agregar tablas ajenas.

Esta demo responde que no: toma **imágenes crudas de satélite** y deriva
de ellas una detección de pérdida de bosque propia, con su propio
umbral calibrado, y la contrasta contra un producto publicado.

Todo corre en el PC, sin Google Earth Engine y sin ninguna credencial
nueva. Eso no es comodidad: el nivel gratuito de Earth Engine es
explícitamente para uso **no comercial**, y el destino de este trabajo
incluye consultorías del Observatorio.

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

Por eso, cuando el código dice "referencia", significa **producto de
contraste**, no verdad de campo. Está escrito así en el docstring de
`metricas()`:

> *"Referencia" tampoco significa "verdad": GLAD-L tiene sus propios
> errores. Lo que miden estas cifras es CONCORDANCIA con un producto
> publicado, no exactitud contra el terreno.*

Para exactitud contra el terreno está la muestra de validación visual
del paso 13.

> **Una comparación contra el IDEAM sí es posible** y sería un buen
> siguiente paso: la capa `cambio_2022-2023` del panel cubre la misma
> ventana y la misma zona. Quedaría como contraste anual, no por píxel.

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

**La misma temporada seca en años consecutivos.** Si se comparara enero
contra julio, el dNBR recogería el ciclo fenológico —la vegetación cambia
sola entre estaciones— y no se sabría qué parte del cambio es tala.

¿Por qué 2022-2023 y no 2020-2021? Porque el ráster de GLAD-L que publica
GFW es **rodante**: la versión vigente arranca en enero de 2021 y no
conserva los años previos. Se verificó la cobertura real antes de fijar
las fechas. Como efecto secundario, ambos años tienen Landsat 8 **y** 9,
mientras que en 2020 solo existía Landsat 8.

```python
GLAD_DESDE = dt.date(2022, 2, 15)
GLAD_HASTA = dt.date(2023, 2, 15)
```

La ventana equivalente para las alertas. Un compuesto de mediana sobre
enero-marzo representa el estado a **mitad** de esa ventana, no a su
inicio ni a su final. Por eso va de punto medio a punto medio.

```python
UMBRAL_DOSEL = 30
ANIO_CORTE_PERDIDA = 21
```

El 30 % es el mismo umbral que usa el panel nacional
(`config_local.umbral_dosel`), para que la demo hable de "bosque" en los
mismos términos. El 21 corresponde a `lossyear <= 21` = pérdida ocurrida
antes de 2022.

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
nacional: la demo no inventa una geometría nueva, hereda la del
repositorio.

**El detalle del redondeo.** `np.floor` y `np.ceil` fuerzan los límites a
múltiplos exactos de 30 m. Sin eso, la rejilla quedaría desfasada medio
píxel y los bordes tendrían fracciones.

**`densify_pts=21`** agrega puntos intermedios al reproyectar el
rectángulo. Un bbox en lon/lat no es un rectángulo en UTM —sus bordes se
curvan— así que transformar solo las cuatro esquinas subestimaría la
extensión.

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

**Por qué `requests` y no `pystac-client`.** Para no sumar una
dependencia: la consulta es trivial y el pipeline ya trae `requests`.

**Lo que NO hace, y es deliberado:**

```python
    # NO se filtra por nubosidad de escena. Una escena con 80 % de nubes
    # puede tener perfectamente despejada la esquina que nos interesa, y
    # descartarla reduciria observaciones justo donde mas falta hacen. El
    # filtro real es por pixel, con QA_PIXEL.
```

Es un error común filtrar escenas por su porcentaje global de nubes. Ese
porcentaje se calcula sobre la escena completa —185 × 180 km— y no dice
nada sobre el recorte de 80 km que nos interesa.

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

**`/vsicurl/` es la clave.** Es un controlador de GDAL que abre un
archivo remoto por HTTP **sin descargarlo**. Lee solo los bytes que le
pida.

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

**`Resampling.nearest` y no bilineal**, por una razón importante: la
banda `QA_PIXEL` es un campo de **bits**, no un número continuo.
Promediar el valor 22280 con el 21824 produce un valor que no significa
nada. Y aplicar interpolaciones distintas a las bandas y a su máscara las
desalinearía.

**El ahorro.** Una escena Landsat completa pesa del orden de 1 GB. Como
los archivos son **COG** (Cloud Optimized GeoTIFF), el servidor entrega
solo los bloques que cubren la ventana. Se descargan megabytes.

Que esto funciona se comprueba en el registro de la corrida: las tres
primeras franjas leen 19 escenas y las tres últimas 38. Esa duplicación
es el traslape entre órbitas de Landsat en el sur de la zona. Si
estuviera trayendo escenas completas, el número sería idéntico en todas.

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

**Esto es fácil de omitir y difícil de detectar.** El NBR es un cociente
normalizado, así que sin la conversión sigue dando valores entre −1 y 1 y
*parece* correcto. Pero no lo es: el desplazamiento de −0,2 no es lineal
respecto al cociente, y el resultado difiere.

```python
    nbr[~valido | (suma == 0)] = np.nan
```

Donde no hay observación válida se pone **NaN**, no cero. Un cero sería
un valor de NBR legítimo; NaN dice "aquí no hay dato", que es distinto.

---

## Paso 5 — El compuesto de mediana

```python
    for fila0 in range(0, alto, FILAS_POR_FRANJA):
        n = min(FILAS_POR_FRANJA, alto - fila0)
        pila = [c for c in (_nbr_de_escena(e, sas, perfil, fila0, n) for e in escenas)
                if c is not None]
        cubo = np.stack(pila)
        nbr[fila0:fila0 + n] = np.nanmedian(cubo, axis=0)
        obs[fila0:fila0 + n] = np.sum(~np.isnan(cubo), axis=0).astype(np.uint16)
```

**Por qué mediana y no media.** La máscara de nubes no es perfecta; deja
pasar observaciones residuales. Una sola lectura contaminada desplaza la
media, pero **no la mediana**. Con 5 observaciones, una mala cambia la
media notablemente y la mediana casi nada.

**Por qué franjas.** Apilar las 38 escenas de la zona completa exigiría
del orden de 600 MB simultáneos. Por franjas de 512 filas el pico baja a
decenas de MB, y el resultado es **idéntico**: la mediana se calcula por
píxel, así que partir el trabajo por filas no la altera.

**`obs` es tan importante como `nbr`.** Cuenta cuántas observaciones
limpias tuvo cada píxel, y es lo que permite construir el dominio.

```python
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            nbr[fila0:fila0 + n] = np.nanmedian(cubo, axis=0)
```

`nanmedian` avisa cuando un píxel estuvo nublado en **todas** las
escenas. Ese caso es esperado, no un fallo: el píxel queda en NaN, no
entra al dominio, y termina contado en el diagnóstico. El aviso se
silencia para que no tape el registro útil.

### El caché

```python
    clave = (f"nbr_{BBOX[0]}_..._{T1_INICIO}_..._{perfil['width']}x{perfil['height']}")
    archivo = DIR_DEMO / f"cache_{clave}.npz"
```

Componer las dos ventanas toma unos 13 minutos de lecturas HTTP, y ese
resultado **no depende de los umbrales**. Se guarda en disco, así que
probar otro umbral cuesta segundos.

**La clave incluye zona, fechas y forma de la rejilla** — todo lo que
cambia el contenido. Si usted cambia el `BBOX` y vuelve a correr, el
caché se invalida en vez de devolverle calladamente el compuesto de otra
corrida. Es la misma precaución que toma `calcular_bosque.py` con su
propio caché.

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

`reproyectar_sobre_bloque()` viene de `zonal.py`, el módulo que usa el
panel nacional. La demo **no reimplementa la geometría del reparto**: la
hereda.

```python
    g_dm = granulos("datamask", obligatoria=False)
    if g_dm:
        bosque &= reproyectar_sobre_bloque(g_dm, perfil) == 1
    else:
        logger.info("  datamask no esta en disco; se omite...")
```

La capa `datamask` distingue tierra firme de agua permanente. El pipeline
solo descarga `treecover2000` y `lossyear`, así que suele no estar.

Se hizo **opcional** en vez de exigir otro gigabyte de descarga, porque
el umbral de dosel ya hace ese trabajo: un cuerpo de agua tiene 0 % de
cobertura arbórea en 2000 y no pasa el primer filtro.

---

## Paso 7 — El dominio

Esta es **la decisión metodológica más importante del módulo**.

```python
def construir_dominio(bosque, obs_t1, obs_t2) -> np.ndarray:
    return bosque & (obs_t1 >= 1) & (obs_t2 >= 1)
```

Tres líneas que deciden la validez de todo lo demás.

**El problema.** Un píxel de bosque tapado por nubes en T1 o en T2 **no
se puede evaluar**: no sabemos si cambió.

**La tentación.** Contarlo como "sin pérdida". Es lo que pasa por
omisión si uno no piensa en ello.

**Por qué está mal.** Ese píxel se convertiría en un verdadero negativo
gratuito. Como el bosque estable ya domina la escena, agregar miles de
negativos falsos **infla la exactitud global** y, peor, **esconde el
problema real**, que es la falta de observación.

**La solución.** Se excluye del análisis, y el porcentaje excluido se
reporta como **resultado**, no como nota al pie.

### Lo que reveló el diagnóstico, y que no esperábamos

```
sin_datos_pct : 0.00
```

**Cero.** Con tres meses de Landsat 8 y 9, todos los píxeles alcanzaron
al menos una lectura limpia en ambas ventanas.

Eso desarma parcialmente el argumento de "las nubes nos dejaron sin
datos". Pero la historia real está en otro número:

| | T1 | T2 |
|---|---|---|
| Escenas disponibles | 38 | 34 |
| Observaciones limpias, **mínimo** | 1 | 1 |
| Observaciones limpias, **percentil 10** | 4 | 2 |
| Observaciones limpias, **mediana** | **5** | **3** |
| Observaciones limpias, **máximo** | 19 | 14 |

De 38 escenas, el píxel mediano recibió **5 lecturas limpias**. La
nubosidad descarta la gran mayoría — solo que acumulando tres meses
alcanza a quedar alguna.

**La afirmación correcta no es** *"las nubes nos dejaron sin datos"*
**sino** *"las nubes redujeron 38 observaciones a 5"*. Es más defendible
y más interesante.

Por eso el diagnóstico reporta la distribución completa: un píxel con una
sola lectura entra al dominio, pero si esa lectura venía contaminada y la
máscara no la atrapó, su dNBR es ruido. Solo el **0,38 %** del bosque
quedó en ese caso.

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

**Se verifica empíricamente en vez de darla por supuesta.** Un desajuste
en la codificación no produciría un error: produciría un resultado
**vacío**, que es el modo de falla más difícil de detectar.

Esa verificación fue la que descubrió que el ráster es **rodante** —solo
tiene alertas desde 2021— y obligó a mover toda la ventana del análisis.

```python
    if d_max < desde or d_min > hasta:
        raise SystemExit(f"Las alertas disponibles (...) no cubren la ventana pedida ...")
```

Y si la ventana pedida cae fuera del rango disponible, el módulo se
detiene con un mensaje claro en vez de devolver cero alertas.

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

**`tam[0] = 0`** es necesario porque la etiqueta 0 es el fondo —todo lo
no marcado— y sería con mucho el grupo más grande.

**La vecindad de 8 y no de 4** importa más de lo que parece: un claro
alargado en diagonal, como una vía de extracción, se partiría en
fragmentos sueltos con vecindad de 4 y se perdería entero al filtrar.

### El mismo trato para GLAD-L

```python
def perdida_glad(glad, dominio) -> np.ndarray:
    return filtrar_parches(glad & dominio)
```

A GLAD-L se le aplica **exactamente el mismo tratamiento**: misma máscara
de bosque y mismo dominio (ambos van dentro de `dominio`), y el mismo
filtro de área mínima. El filtro de fecha ya se aplicó al leer.

**Sin esas igualaciones la comparación mediría diferencias de encuadre,
no de detección.** Un ejemplo concreto: GLAD-L alerta también fuera del
bosque definido por Hansen. Sin la máscara común, eso aparecería como
"detección adicional de GLAD" cuando en realidad es terreno donde el
método propio nunca pudo haber buscado.

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

**Por qué importa.** Si se calibra y se evalúa sobre los mismos píxeles,
el umbral se ajusta al ruido de esos píxeles y la métrica resultante está
inflada. Es de las primeras cosas que un jurado revisa.

### Un problema real en el resultado

| Umbral | Precisión | Sensibilidad | F1 |
|---|---|---|---|
| 0,10 | 0,057 | 0,613 | 0,105 |
| 0,20 | 0,160 | 0,505 | 0,242 |
| 0,30 | 0,243 | 0,418 | 0,307 |
| **0,35** | 0,279 | 0,377 | **0,321** |

El F1 **seguía subiendo** al llegar a 0,35, que es el último valor
probado. Eso significa que el óptimo probablemente está más allá y que la
grilla de búsqueda era estrecha.

Conviene extender `UMBRALES_DNBR` hacia 0,40-0,50 y volver a correr —
ahora cuesta segundos gracias al caché.

---

## Paso 11 — Las métricas, y cuál mentiría

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

**El nombre de la clave es la advertencia.** La exactitud global dio
**0,9864**, y no significa nada: el bosque estable ocupa el 98 % del
dominio, así que un detector que no marcara **nada** obtendría una cifra
parecida.

Se reporta porque suele pedirse, con el nombre puesto para que nadie la
cite sin darse cuenta.

---

## Paso 12 — La comparación que de verdad importa

```python
    px_celda = LADO_CELDA_M // ESCALA_M
    filas = np.arange(perfil["height"])[:, None] // px_celda
    cols = np.arange(perfil["width"])[None, :] // px_celda
    idx = (filas * (perfil["width"] // px_celda + 1) + cols).astype(np.int64)
    cuenta = lambda m: np.bincount(idx[m], minlength=n) * ha
```

Agrupa los píxeles en celdas de 5 × 5 km y suma hectáreas por celda, para
cada fuente. El índice de celda sale por **aritmética directa** —dividir
la coordenada de píxel entre el lado de la celda— igual que en
`zonal.py`.

**Por qué esta es la comparación relevante.** El modelo predictivo del
proyecto trabaja a escala de celda de 5 km, no de píxel. Dos productos
pueden discrepar píxel a píxel por medio píxel de desplazamiento y aun
así coincidir muy bien en **cuánta pérdida hay en cada celda**, que es lo
que el modelo necesita.

```python
    df = df[df.dominio_ha > 0].copy()
```

Las celdas sin dominio se descartan. No es que coincidan en cero: es que
no había dónde mirar. Incluirlas inflaría artificialmente la correlación.

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

**Por qué estratificado y no aleatorio simple.** Las clases de cambio
ocupan una fracción minúscula de la escena: `ambos` es el 0,7 % del
dominio. Una muestra aleatoria simple de 200 puntos caería casi entera en
bosque estable y dejaría los desacuerdos —que son **justo lo que hay que
revisar**— con uno o dos puntos, o ninguno.

```python
        filas.append(pd.DataFrame({..., "etiqueta_visual": ""}))
```

La columna sale **vacía a propósito**. La llena un humano mirando imagen
de alta resolución, y de ahí salen los errores de omisión y comisión que
permiten corregir el área estimada.

**Este paso está pendiente.** El CSV está generado con sus 200 puntos,
pero nadie los ha interpretado todavía. Hasta que eso ocurra, la demo
mide **concordancia con GLAD-L**, no exactitud.

---

## Los resultados, interpretados

Sobre la mitad este, que la calibración nunca vio:

| Métrica | Valor |
|---|---|
| **Pearson, hectáreas por celda de 5 km** | **0,909** |
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

**A nivel de píxel la coincidencia es moderada; a la escala de 5 km es de
0,91.**

Esa brecha entre escalas no es un defecto, es el hallazgo. Significa que
los dos métodos **no coinciden sobre qué píxel exacto marcar**, pero sí
sobre **dónde está ocurriendo y cuánto**. Y lo segundo es lo que el
modelo necesita.

La explicación es geométrica: un claro de 3 ha detectado por ambos puede
tener bordes desplazados uno o dos píxeles, lo que castiga la precisión
por píxel sin afectar el total por celda.

### Qué dicen los desacuerdos

Que haya 1 026 ha "solo propia" y 1 430 ha "solo GLAD" no significa que
unas sean falsos positivos y otras falsos negativos. Puede ser:

- Diferencias de fecha: el compuesto ve el estado a mitad de la ventana,
  GLAD-L alerta en el momento de la detección.
- Diferencias de sensibilidad: dNBR detecta cambios graduales que GLAD-L
  clasifica como no confirmados.
- Errores genuinos de cualquiera de los dos.

**Solo la validación visual del paso 13 puede distinguir cuál es cuál.**

---

## Lo que esta demo no demuestra

Conviene tenerlo claro antes de presentarla:

**No reemplaza a GLAD-L.** Es una zona piloto de 80 × 77 km, un par de
fechas y un solo índice. El producto de GFW integra tres sistemas,
cobertura continua y una escala de confianza validada.

**No mide exactitud, mide concordancia.** Sin la interpretación visual de
los 200 puntos, no hay verdad de campo contra la cual medirse.

**No se comparó con el dato oficial.** GLAD-L no es el IDEAM. Una
comparación contra la capa `cambio_2022-2023` del panel sería un buen
siguiente paso, aunque sería anual y no por píxel.

**El umbral óptimo quedó en el borde de la grilla.** Hay que ampliar la
búsqueda antes de reportar el 0,35 como valor elegido.

**Un solo índice y una sola fecha por año.** Los productos operativos
usan series temporales completas y varios índices. Esta demo usa dos
compuestos y el NBR.

---

## Cómo volver a correrlo

```powershell
python demo_landsat_caqueta.py
```

La primera vez toma unos 13 minutos. Las siguientes, segundos, porque los
compuestos quedan en `datos/demo/cache_nbr_*.npz`.

Para forzar el recálculo —por ejemplo tras cambiar las fechas— basta
borrar ese archivo. Si cambia el `BBOX` o la rejilla, el caché se
invalida solo, porque la clave del archivo los incluye.
