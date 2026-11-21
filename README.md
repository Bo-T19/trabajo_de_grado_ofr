# Deforestación y financiamiento rural en Colombia

Trabajo de grado de la Maestría en Analítica de la Pontificia Universidad
Javeriana, con el Observatorio Financiero Rural.

El repositorio hace tres cosas:

1. **Cuatro tablas de deforestación** sobre una misma grilla de 5 × 5 km que
   cubre Colombia, a partir de fuentes satelitales públicas: alertas de
   Global Forest Watch, pérdida de cobertura de Hansen, y la deforestación
   oficial y las detecciones tempranas del IDEAM.
2. **Un panel municipal** que cruza esa deforestación con el crédito de
   FINAGRO, los cultivos de la EVA y el ganado del ICA, más un análisis
   exploratorio de ese panel.
3. **Segmentación y modelos de riesgo**:
   - una segmentación de los municipios rurales según su perfil productivo y
     financiero;
   - tres modelos que responden *¿deforesta?* y, si deforesta, *¿cuánto?*;
   - una comparación de los modelos y un cruce entre los segmentos y el
     riesgo.

## Cómo usar esta documentación

Para reproducir el trabajo se leen cuatro documentos, en este orden:

| # | Documento | Qué tiene |
|---|---|---|
| 1 | [`guias/1_FUENTES.md`](guias/1_FUENTES.md) | Qué es cada fuente de datos (las cuatro propias y las cinco del Observatorio), qué periodo cubre y cómo se accede |
| 2 | [`guias/2_DESCARGA_DE_DATOS.md`](guias/2_DESCARGA_DE_DATOS.md) | Cómo preparar el entorno y las credenciales, descargar los datos, armar las tablas y el panel municipal, y comprobar que salió bien |
| 3 | [`guias/3_NOTEBOOKS.md`](guias/3_NOTEBOOKS.md) | Cómo correr el análisis exploratorio, la segmentación y los modelos, y qué resultados esperar |
| 4 | [`guias/4_DEMO_LANDSAT.md`](guias/4_DEMO_LANDSAT.md) | La demo que replica con imágenes Landsat el cálculo de pérdida de bosque. Es opcional |

Para correr todo en BigQuery, en el proyecto del Observatorio, está
[`notebooks_bigquery/README.md`](notebooks_bigquery/README.md): los mismos pasos convertidos en 18
notebooks que cargan y actualizan las tablas en BigQuery y hacen el análisis y los modelos desde ahí.

Y tres de referencia, que no hacen falta para correr nada:

- [`guias/referencia/METODOLOGIA.md`](guias/referencia/METODOLOGIA.md): el porqué de cada decisión de diseño.
- [`guias/referencia/GUIA_CODIGO.md`](guias/referencia/GUIA_CODIGO.md): cómo está hecho el código, para quien quiera modificarlo.
- [`guias/referencia/GUIA_BIGQUERY.md`](guias/referencia/GUIA_BIGQUERY.md): la administración de Google Cloud, para el equipo.

Las columnas y una muestra de cada tabla están en
[`guias/columnas/DESCRIPCION_FUENTES.md`](guias/columnas/DESCRIPCION_FUENTES.md) y
[`guias/columnas/DESCRIPCION_FUENTES_PROFESOR.md`](guias/columnas/DESCRIPCION_FUENTES_PROFESOR.md),
que se generan solos.

## Inicio rápido

Con Python 3.10 a 3.13, desde la raíz del repositorio:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements_local.txt

python main_local.py --help     # lista de subcomandos
python main_local.py estado     # qué hay en disco y qué falta
```

Hacen falta dos credenciales (ver `guias/2_DESCARGA_DE_DATOS.md`, sección 1.5):

- **Una API key de Global Forest Watch.** Es gratuita y sirve para las
  cuatro tablas.
- **La llave de la cuenta de servicio de BigQuery.** No es pública: hay que
  pedírsela al equipo. Sin ella no se puede armar el panel municipal, y
  por lo tanto tampoco correr el análisis, la segmentación ni los modelos.

Aun sin la llave se pueden consultar los resultados de la corrida de
referencia: los notebooks están guardados con sus salidas, y las tablas de
resultados están en `modelos y clusters/resultados/` y `documento/tablas/`.

## Dónde está cada cosa

| Carpeta | Qué contiene |
|---|---|
| `main_local.py` | El único punto de entrada del pipeline: `python main_local.py <subcomando>` |
| `pipeline/` | Todo el código del pipeline: descarga de insumos, las cuatro tablas, subida a BigQuery, descripción de las fuentes y demo de Landsat |
| `procesamiento y eda/` | Notebooks del panel municipal y del análisis exploratorio |
| `modelos y clusters/` | Notebooks de la segmentación, los tres modelos de riesgo y su comparación, y el cruce entre segmentos y riesgo |
| `modelos y clusters/resultados/` | Salidas de la segmentación y de los modelos: tablas, métricas, predicciones y modelos entrenados |
| `notebooks_bigquery/` | Todo el trabajo en 18 notebooks para BigQuery Studio: carga y actualización de las tablas, análisis, segmentación, modelos y demo de Landsat |
| `guias/` | Los cuatro documentos para reproducir el trabajo, numerados en orden de lectura |
| `guias/referencia/` | Los documentos de consulta: metodología, guía del código y guía de BigQuery |
| `guias/columnas/` | Columnas y muestra de cada tabla, generadas por los scripts |
| `documento/` | Figuras (`figuras/`) y tablas (`tablas/`) exportadas para el documento del trabajo |
| `datos/` | Todo lo que se descarga y se produce al armar las tablas y el panel. No se versiona; solo se conserva la estructura de carpetas |
