# Código archivado

Esta carpeta guarda una versión anterior de una parte del pipeline, que ya
no forma parte del flujo activo del proyecto. Se conserva aquí por
trazabilidad técnica, no porque siga en uso.

## Qué hay aquí

- `fuente_dist_alert/` — el código tal como quedó la última vez que se usó.
- `cmr.txt` — salida guardada de una consulta de diagnóstico contra el
  catálogo que usaba ese código.
- `METODOLOGIA_DIST_ALERT.md` — la metodología de esa fuente de datos,
  como documento independiente.
- `GUIA_CODIGO_DIST_ALERT.md` — cómo estaba construido y cómo se ejecutaba.

## Estado: congelado, no mantenido

**Este código no corre contra la versión actual de `config_local.py`.**
El pipeline activo simplificó la configuración central a los parámetros
que necesita su única fuente de datos; varios campos que estos scripts
importan (`dist_short_name`, `capa_estado`, `capa_fecha`, `estados_evento`,
`epoca_dist`, `cadencia_snapshot`, `tiles`, entre otros) ya no existen en
`config_local.py`. Para volver a correr algo de esta carpeta haría falta
restaurar esos campos o darle a estos scripts su propia configuración
aparte — no es un simple `python archivo.py`.

Lo que sí sigue vigente y es compartido con el pipeline activo:
`exportar_grilla.py` (la grilla de 5 km) y los granulos de Hansen GFC
descargados en `datos/hansen/` — ninguno de los dos es específico de lo
que hay archivado aquí.

## Por qué se archivó

El proyecto pasó a construirse sobre una sola fuente de datos, más simple
de entender y de documentar de principio a fin. Ver `METODOLOGIA.md` y
`GUIA_CODIGO.md` en la raíz del proyecto para la metodología y el código
activos.
