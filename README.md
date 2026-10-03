# Panel de deforestación de Colombia

Trabajo de grado de la Maestría en Analítica de la Pontificia Universidad
Javeriana, con el Observatorio Financiero Rural.

El repositorio construye cuatro tablas de deforestación sobre una misma
grilla de 5 × 5 km que cubre Colombia, a partir de fuentes satelitales
públicas:

| Tabla | Fuente | Qué mide | Unidad |
|---|---|---|---|
| `panel_deforestacion_colombia` | Global Forest Watch | Alertas de disturbio | celda × mes |
| `panel_hansen` | Hansen GFC | Pérdida de cobertura arbórea | celda × año |
| `panel_ideam` | IDEAM / SMByC | Deforestación oficial | celda × periodo |
| `panel_dtd` | IDEAM / SMByC | Detecciones tempranas | celda × trimestre |

Cada una mide un concepto distinto, así que sus cifras no se suman entre
sí. El porqué está en [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md).

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
[`docs/GUIA_CODIGO.md`](docs/GUIA_CODIGO.md), sección 3. La única
credencial obligatoria es una API key gratuita de Global Forest Watch
(`python main_local.py configurar-gfw`), que queda en `datos/logs/` y
nunca se sube al repositorio.

## Dónde está cada cosa

| Carpeta | Qué contiene |
|---|---|
| `main_local.py` | El único punto de entrada: `python main_local.py <subcomando>` |
| `pipeline/` | Todo el código. En la raíz del paquete, las piezas compartidas (configuración, reparto zonal, bosque base, mapa) |
| `pipeline/descarga/` | Etapa 1: grilla e insumos (Hansen, GFW, límites del DANE, capas y detecciones del IDEAM) |
| `pipeline/paneles/` | Etapa 2: las cuatro tablas |
| `pipeline/bigquery/` | Etapa 3: subida de las tablas a BigQuery |
| `pipeline/entendimiento/` | Descripción de las fuentes y réplica del cálculo con imágenes Landsat |
| `notebooks/` | Catálogo de las tablas y exploración de las tablas del Observatorio |
| `docs/` | Metodología y guías |
| `datos/` | Todo lo que se descarga y se produce. No se versiona; solo se conserva la estructura de carpetas |
| `legacy/` | Código archivado, fuera del pipeline activo |

## Documentación

- [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md): qué mide cada fuente y por qué se tomó cada decisión. Es el documento para leer primero.
- [`docs/GUIA_CODIGO.md`](docs/GUIA_CODIGO.md): cómo está construido el código y cómo correrlo desde cero.
- [`docs/GUIA_DEMO_LANDSAT.md`](docs/GUIA_DEMO_LANDSAT.md): recorrido de la réplica del cálculo con Landsat.
- [`docs/GUIA_BIGQUERY.md`](docs/GUIA_BIGQUERY.md): acceso y arquitectura de BigQuery.
