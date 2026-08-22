# Metodología archivada — NASA OPERA DIST-ALERT

*(Documento histórico. Ver `../METODOLOGIA.md` para la metodología activa
del proyecto. Este archivo describe una fuente de datos que ya no está en
uso — ver `README.md` en esta misma carpeta.)*

## Qué era

Producto de detección casi en tiempo real de disturbios de vegetación,
parte de la suite "Land Disturbance" del proyecto OPERA (*Observational
Products for End-Users from Remote Sensing Analysis*) de la NASA/JPL.
Se calculaba sobre HLS (*Harmonized Landsat Sentinel-2*): observaciones
combinadas de Landsat 8/9 y Sentinel-2A/B/C armonizadas radiométrica y
geométricamente, lo que le daba una cadencia de revisita de días, no
semanas.

Cada gránulo traía 19 capas; el pipeline archivado usaba solo dos:

| Capa | Qué es | Rol |
|---|---|---|
| `VEG-DIST-STATUS` | Código de estado de la alerta por píxel (tabla abajo) | Define si un píxel cuenta como "evento" |
| `VEG-DIST-DATE` | Fecha real del disturbio, en días desde el 2020-12-31 | Define a qué mes se atribuye el evento |

Códigos de `VEG-DIST-STATUS`:

```
0    sin perturbación
1-3  primera detección / provisional / confirmada, pérdida <50%
4-6  primera detección / provisional / confirmada, pérdida ≥50%
7    confirmada <50%, disturbio finalizado
8    confirmada ≥50%, disturbio finalizado
255  sin dato (nubes, sombra, fuera de cobertura)
```

Se contaban como evento solo los códigos **6 y 8** (confirmado, ≥50% de
pérdida de señal) — se descartaban las detecciones sin confirmar (1-5) y
las de magnitud menor (<50%).

**Por qué se había elegido esta fuente**: mejor cadencia temporal que
Landsat solo (gracias a HLS), acceso programático estandarizado vía NASA
CMR/`earthaccess`, y continuidad operacional esperada de un producto NASA
activamente mantenido.

**Limitaciones conocidas**: dependía de observaciones ópticas limpias (la
nubosidad persistente en Amazonía/Pacífico retrasaba la confirmación,
generando *reporting lag* en los últimos meses de cualquier corrida); no
distinguía causa del disturbio; el producto ofrecía también los códigos
<50%, descartados por decisión de diseño de este pipeline, no del producto.

## Ventana temporal

`fecha_inicio = 2023-01-01`: DIST-ALERT no tiene datos antes de esa fecha
(verificado empíricamente contra el catálogo real de NASA CMR — cero
gránulos en cualquier parte del mundo antes de esa fecha).

## El problema de la doble contabilización temporal

Un mismo píxel podía aparecer en estado 6 u 8 en varias instantáneas
mensuales sucesivas (una alerta pasa de *provisional* a *confirmada* y
puede seguir en estado confirmado varios meses). Sumar el conteo de cada
instantánea habría contado el mismo evento varias veces.

La solución era un conjunto acumulado monótonamente creciente: se
recorrían las instantáneas **en orden cronológico**, manteniendo una
máscara `ya_contado` (un valor por píxel del tile). En cada instantánea:

```
nuevo(p, s) = [ estado(p, s) ∈ {6, 8} ]  AND  bosque(p)  AND  NOT ya_contado(p)
ya_contado |= nuevo
```

Los píxeles `nuevo` se atribuían al mes de su **`VEG-DIST-DATE` real**, no
al de la instantánea en que se observaron confirmados — así un disturbio
iniciado en marzo pero confirmado en mayo contaba en marzo.

**Efecto de inicio de ventana**: la máscara `ya_contado` arrancaba vacía en
la primera instantánea de cada tile, así que todo lo que ya estaba
confirmado ahí entraba de una sola vez al primer mes del panel —
sobreestimando ese primer periodo (mide un *stock* inicial acumulado, no
un *flujo* mensual). Había que excluirlo de promedios y comparaciones.

## Cómo se calculaba, en código (resumen)

Por cada tile MGRS (100×100 km, el mismo sistema de cuadrícula de
Sentinel-2/HLS):

1. **Índice de celda** (`indice_celdas()`): los centros de píxel del tile
   (en su UTM nativo) se reproyectaban a EPSG:3116 con `pyproj`, y se
   calculaba `floor(coord/5000)` para asignar cada píxel a su celda de la
   grilla de 5 km.
2. **Máscara de bosque** (`mascara_bosque()`): Hansen GFC se reproyectaba
   a la cuadrícula del tile (mismo patrón de `reproject` + `np.maximum`
   entre gránulos que usa hoy `calcular_bosque.py` del pipeline activo).
3. Se recorrían las instantáneas VEG-DIST-STATUS en orden cronológico
   aplicando la lógica de `ya_contado` de arriba.

Los tiles MGRS se descargaban con `descargar_dist.py` (vía `earthaccess`,
requería una cuenta gratuita de NASA Earthdata) y se filtraban a los
realmente colombianos con `filtrar_tiles.py` (convertía cada celda de la
grilla a su tile MGRS con la librería `mgrs` y descartaba el resto).
`diagnostico_cmr.py` era una herramienta puntual para confirmar el
`short_name`/`version` exactos que reconocía el catálogo CMR.

## Restricción de licencia (para contexto)

Datos abiertos de la NASA (LP DAAC), sin restricción de uso comercial
declarada.
