# Guía de código archivada — rama DIST-ALERT

*(Documento histórico. Ver `../GUIA_CODIGO.md` para la guía activa. Este
archivo describe scripts que ya no forman parte del pipeline en uso — ver
`README.md` en esta misma carpeta sobre por qué no corren tal cual contra
el `config_local.py` actual.)*

## Archivos

- `fuente_dist_alert/descargar_dist.py` — descargaba Hansen GFC (esa parte
  hoy vive, ya adaptada, en `../descargar_hansen.py`) y los gránulos
  DIST-ALERT (VEG-DIST-STATUS, VEG-DIST-DATE) vía `earthaccess`/NASA CMR.
  Tres subcomandos: `hansen`, `inventario` (contaba cuánto habría que
  bajar sin descargar nada), `dist` (la descarga real, reanudable).
- `fuente_dist_alert/filtrar_tiles.py` — el `bbox` rectangular usado para
  consultar CMR incluía países vecinos y océano; este script convertía
  cada celda de la grilla a su tile MGRS (librería `mgrs`) y recortaba el
  inventario a los tiles realmente colombianos.
- `fuente_dist_alert/zonal_local.py` — el motor de cálculo: `indice_celdas()`
  y `mascara_bosque()` (por tile, cacheadas en disco) más el recorrido
  cronológico de instantáneas con la máscara `ya_contado` — ver
  `METODOLOGIA_DIST_ALERT.md` para el detalle matemático. Producía
  `datos/crudo/nacional.csv` en el mismo formato ancho que usa el
  pipeline activo.
- `fuente_dist_alert/diagnostico_cmr.py` — herramienta puntual para
  confirmar contra el catálogo real de NASA CMR el `short_name`/`version`
  exactos de la colección DIST-ALERT y el formato de nombre de archivo del
  que dependía el parseo de `descargar_dist.py`. Su salida guardada está
  en `cmr.txt`, en esta misma carpeta.

## Requisitos que ya no aplican al pipeline activo

Esta rama necesitaba una cuenta gratuita de **NASA Earthdata Login**
(`earthaccess`, con credenciales en `~/.netrc`) para autenticar contra
LP DAAC. El pipeline activo no necesita ninguna cuenta de la NASA: su
única credencial es la API key de Global Forest Watch.

## Cómo se orquestaba (para referencia)

El orden era: `grilla` → `hansen` → `inventario` (a CMR, sin descargar) →
`filtrar_tiles.py` (aparte) → `descargar` (nacional, vía `earthaccess`) →
`zonal` (el cálculo de `zonal_local.py`) → `consolidar`. Un modo "piloto"
permitía descargar y procesar un solo tile MGRS para validar el flujo
antes de lanzar el país completo.

## Caché por tile

`indice_celdas()` y `mascara_bosque()` cacheaban su resultado en
`datos/cache/<tile>__idx.npy` y `datos/cache/<tile>__bosque_am{...}_ud{...}.npy`
respectivamente — un archivo por cada uno de los ~153 tiles MGRS que
cubrían Colombia. El pipeline activo no tiene ese concepto: calcula el
bosque directamente sobre bloques de la propia grilla nacional (ver
`../calcular_bosque.py`), sin ninguna cuadrícula MGRS de por medio.
