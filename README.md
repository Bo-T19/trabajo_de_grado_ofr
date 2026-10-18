# Deforestación y financiamiento rural en Colombia

Trabajo de grado de la Maestría en Analítica de la Pontificia Universidad
Javeriana, con el Observatorio Financiero Rural.

El repositorio hace dos cosas.

**1. Cuatro tablas de deforestación** sobre una misma grilla de 5 × 5 km que
cubre Colombia, a partir de fuentes satelitales públicas:

| Tabla | Fuente | Qué mide | Unidad |
|---|---|---|---|
| `panel_deforestacion_colombia` | Global Forest Watch | Alertas de disturbio | celda × mes |
| `panel_hansen` | Hansen GFC | Pérdida de cobertura arbórea | celda × año |
| `panel_ideam` | IDEAM / SMByC | Deforestación oficial | celda × periodo |
| `panel_dtd` | IDEAM / SMByC | Detecciones tempranas | celda × trimestre |

Cada una mide un concepto distinto, así que sus cifras no se suman entre
sí. El porqué está en [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md).

**2. Un panel municipal** que cruza la deforestación del IDEAM y de GFW con
las tablas que compartió el Observatorio (crédito de FINAGRO, cultivos de la
EVA y ganado del ICA), y un análisis de ese panel en los municipios rurales y
rurales dispersos:

| Tabla (en `datos/analisis/`) | Unidad | Qué tiene |
|---|---|---|
| `municipio_anio` | municipio × año, 2020-2025 | Deforestación del IDEAM y alertas de GFW; crédito de FINAGRO, total y del eslabón de producción (total y por cadena); área cosechada de la EVA; bovinos y fincas del ICA; atributos del municipio |
| `municipio_mes` | municipio × mes, 2020-01 a 2026-06 | Alertas de GFW y crédito |
| `municipio_cultivo_anio` | municipio × cultivo × año, 2019-2024 | Área cosechada de cada cultivo de la EVA |

Los notebooks del panel municipal se corren en este orden:

1. [`panel_municipal_armado.ipynb`](notebooks/panel_municipal_armado.ipynb):
   descarga las tablas del Observatorio y arma las tres tablas.
2. [`panel_municipal_analisis.ipynb`](notebooks/panel_municipal_analisis.ipynb):
   índice de cambio, concentración (Lorenz y Pareto), cultivos y ganado de
   los 10 municipios que más deforestan, correlaciones y mapa.
3. [`estadisticas_descriptivas.ipynb`](notebooks/estadisticas_descriptivas.ipynb):
   estadística descriptiva de todas las tablas, que se exporta a
   `docs/figuras/` y `docs/tablas/`.

## Cómo empezar

Todo se corre desde esta carpeta, con un solo punto de entrada:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements_local.txt

python main_local.py --help     # lista de subcomandos
python main_local.py estado     # qué hay en disco y qué falta
```

El orden completo de ejecución, paso por paso, está en
[`docs/GUIA_CODIGO.md`](docs/GUIA_CODIGO.md), sección 3. Las cuatro tablas de
deforestación solo necesitan una API key gratuita de Global Forest Watch
(`python main_local.py configurar-gfw`). El panel municipal necesita además
la llave de la cuenta de servicio de BigQuery, para leer las tablas del
Observatorio (sección 2.5 de la guía). Las dos credenciales quedan en
`datos/logs/` y nunca se suben al repositorio.

## Dónde está cada cosa

| Carpeta | Qué contiene |
|---|---|
| `main_local.py` | El único punto de entrada: `python main_local.py <subcomando>` |
| `pipeline/` | Todo el código. En la raíz del paquete, las piezas compartidas (configuración, reparto zonal, bosque base, mapa) |
| `pipeline/descarga/` | Etapa 1: grilla e insumos (Hansen, GFW, límites del DANE, capas y detecciones del IDEAM) |
| `pipeline/paneles/` | Etapa 2: las cuatro tablas |
| `pipeline/bigquery/` | Etapa 3: subida de las tablas a BigQuery |
| `pipeline/entendimiento/` | Descripción de las fuentes y réplica del cálculo con imágenes Landsat |
| `notebooks/` | Catálogo de las tablas, exploración de las tablas del Observatorio, panel municipal y estadísticas descriptivas |
| `docs/` | Metodología, guías y descripción de las fuentes |
| `docs/figuras/`, `docs/tablas/` | Figuras y tablas exportadas para el documento del trabajo |
| `datos/` | Todo lo que se descarga y se produce. No se versiona; solo se conserva la estructura de carpetas |
| `legacy/` | Código archivado, fuera del pipeline activo |

## Documentación

- [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md): qué mide cada fuente y por qué se tomó cada decisión. Es el documento para leer primero.
- [`docs/GUIA_CODIGO.md`](docs/GUIA_CODIGO.md): cómo está construido el código y cómo correrlo desde cero.
- [`docs/GUIA_DEMO_LANDSAT.md`](docs/GUIA_DEMO_LANDSAT.md): recorrido de la réplica del cálculo con Landsat.
- [`docs/GUIA_BIGQUERY.md`](docs/GUIA_BIGQUERY.md): acceso y arquitectura de BigQuery.
- [`docs/DESCRIPCION_FUENTES.md`](docs/DESCRIPCION_FUENTES.md) y [`docs/DESCRIPCION_FUENTES_PROFESOR.md`](docs/DESCRIPCION_FUENTES_PROFESOR.md): columnas, tipos y una muestra de las cuatro tablas propias y de las cinco del Observatorio. Se generan con `describir-fuentes` y `describir-fuentes-profesor`.
