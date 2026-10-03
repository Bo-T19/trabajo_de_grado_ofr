# Descripcion de las fuentes del Observatorio

Generado automaticamente por `describir_fuentes_profesor.py`, usando la cuenta de servicio pipeline-satelital (la misma de describir_fuentes.py) -- ver ese script para las cuatro tablas propias. No editar a mano -- se vuelve a generar completo cada vez que se corre el script.

## FINAGRO - desembolsos de credito (Observatorio, solo lectura)

Tabla: `prueba-ofr.Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA`

Filas: **6,158,859** -- Columnas: **37**

| Columna | Tipo |
|---|---|
| id_credito | STRING |
| fecha_credito | DATETIME |
| cod_municipio | STRING |
| tipo_cartera | STRING |
| tipo_intermediario | STRING |
| tipo_productor | STRING |
| tipo_beneficiario | STRING |
| tipo_persona | STRING |
| sexo | STRING |
| cod_destino | INTEGER |
| linea_credito | STRING |
| cadena | STRING |
| eslabon_cadena | STRING |
| valor_credito | FLOAT |
| valor_inversion | FLOAT |
| plazo | INTEGER |
| periodo_gracia | INTEGER |
| cuotas | INTEGER |
| cuotas_capital | INTEGER |
| tasa_indexacion | STRING |
| periodicidad_tasa_indexacion | STRING |
| puntos_adicionales | FLOAT |
| garantia_fag | INTEGER |
| nombre_programa | STRING |
| indicador_lec | STRING |
| valor_subsidio | STRING |
| nuevo | STRING |
| viernes | DATE |
| tasa_total | FLOAT |
| DPNOM | STRING |
| MPIO | STRING |
| DPMP | STRING |
| PDET | INTEGER |
| region | STRING |
| ruralidad | STRING |
| Destino | INTEGER |
| Nombre_destino | STRING |

Muestra (primeras 5 filas):

|   id_credito | fecha_credito       |   cod_municipio | tipo_cartera   | tipo_intermediario   | tipo_productor   | tipo_beneficiario   | tipo_persona   | sexo   |   cod_destino | linea_credito   | cadena     | eslabon_cadena   |   valor_credito |   valor_inversion |   plazo |   periodo_gracia |   cuotas |   cuotas_capital | tasa_indexacion   | periodicidad_tasa_indexacion   |   puntos_adicionales |   garantia_fag | nombre_programa                                                       |   indicador_lec |   valor_subsidio |   nuevo | viernes    |   tasa_total | DPNOM     |   MPIO | DPMP     | PDET   | region       | ruralidad                 |   Destino | Nombre_destino                                      |
|-------------:|:--------------------|----------------:|:---------------|:---------------------|:-----------------|:--------------------|:---------------|:-------|--------------:|:----------------|:-----------|:-----------------|----------------:|------------------:|--------:|-----------------:|---------:|-----------------:|:------------------|:-------------------------------|---------------------:|---------------:|:----------------------------------------------------------------------|----------------:|-----------------:|--------:|:-----------|-------------:|:----------|-------:|:---------|:-------|:-------------|:--------------------------|----------:|:----------------------------------------------------|
|   2650249552 | 2026-06-11 00:00:00 |           27493 | Redescuento    | Bancos               | Pequeño          | Pequeño productor   | Natural        | Hombre |        141430 | Inversión       | Plátano    | Producción       |         3.2e+07 |           3.2e+07 |      84 |                2 |       14 |               12 | IBR               | Semestral                      |                 6.7  |              1 | IBR CREDITO ORDINARIO                                                 |               0 |                0 |       1 | 2026-06-05 |    0.194026  |           |        |          | <NA>   |              |                           |    141430 | Plátano                                             |
|   2502959549 | 2025-04-22 00:00:00 |           27493 | Redescuento    | Bancos               | Pequeño ppib     | Desplazado ppib     | Natural        | Mujer  |        253400 | Inversión       | Ganado DP  | Producción       |         2e+07   |           2e+07   |      84 |                2 |       14 |               12 | IBR               | Semestral                      |                 1.9  |              1 | IBR FINANCIACIÓN PROYECTOS EJECUTADOS POBLACIÓN EN SITUACIÓN ESPECIAL |               0 |                0 |       0 | 2025-04-18 |    0.109114  |           |        |          | <NA>   |              |                           |    253400 | Vientres bovinos y bufalinos comerciales cría y D.P |
|   2202341616 | 2022-03-30 00:00:00 |           05001 | Sustitutiva    | Bancos               | Grande           | Grande productor    | Jurídica       | NA     |        101056 | Inversión       | Flores     | Producción       |         1e+09   |           1e+09   |      18 |                0 |       18 |               18 | IBR               | Mensual                        |                 2.71 |              0 | IBR CREDITO ORDINARIO                                                 |               0 |                0 |       0 | 2022-03-25 |    0.0817737 | Antioquia |  05001 | Medellín | 0      | Eje cafetero | Ciudades y aglomeraciones |    101056 | Flores ciclo corto                                  |
|   2603061603 | 2026-01-02 00:00:00 |           05001 | Sustitutiva    | Bancos               | Grande           | Grande productor    | Jurídica       | NA     |        104008 | Inversión       | Ganado DP  | Producción       |         1.5e+09 |           1.5e+09 |      12 |                0 |       12 |               12 | IBR               | Mensual                        |                 0.72 |              0 | IBR CREDITO ORDINARIO                                                 |               0 |                0 |       0 | 2026-01-02 |    0.10023   | Antioquia |  05001 | Medellín | 0      | Eje cafetero | Ciudades y aglomeraciones |    104008 | Ganadería bovina sostenible                         |
|   2202330746 | 2022-02-16 00:00:00 |           05001 | Sustitutiva    | Bancos               | Pequeño          | Pequeño productor   | Natural        | Mujer  |        121180 | Inversión       | Hortalizas | Producción       |         1e+06   |           1e+06   |       6 |                5 |        6 |                1 | IBR               | Mensual                        |                 6.7  |              0 | IBR TARJETA AGROPECUARIA                                              |               0 |                0 |       0 | 2022-02-11 |    0.111426  | Antioquia |  05001 | Medellín | 0      | Eje cafetero | Ciudades y aglomeraciones |    121180 | Cebolla de hoja                                     |

## SFC414 (Observatorio, solo lectura)

Tabla: `prueba-ofr.Inclusion_Financiera.SFC414_DASH`

Filas: **1,977,282** -- Columnas: **17**

| Columna | Tipo |
|---|---|
| Fecha_Corte | DATE |
| Tipo_de_persona | STRING |
| Sexo | STRING |
| Tipo_de_credito | STRING |
| Tipo_de_garantia | STRING |
| Montos_desembolsados | FLOAT |
| Numero_de_creditos_desembolsados | INTEGER |
| Codigo_Municipio | STRING |
| nombre_departamento | STRING |
| nombre_municipio | STRING |
| region | STRING |
| fecha | INTEGER |
| ruralidad | STRING |
| Rural_Urbano | STRING |
| Tasa_efectiva_promedio_ponderada_AD | FLOAT |
| MPIO | STRING |
| PDET_Nom | STRING |

Muestra (primeras 5 filas):

| Fecha_Corte   | Tipo_de_persona   | Sexo       | Tipo_de_credito   | Tipo_de_garantia            |   Montos_desembolsados |   Numero_de_creditos_desembolsados |   Codigo_Municipio | nombre_departamento   | nombre_municipio   | region       |   fecha | ruralidad                 | Rural_Urbano   |   Tasa_efectiva_promedio_ponderada_AD |   MPIO | PDET_Nom   |
|:--------------|:------------------|:-----------|:------------------|:----------------------------|-----------------------:|-----------------------------------:|-------------------:|:----------------------|:-------------------|:-------------|--------:|:--------------------------|:---------------|--------------------------------------:|-------:|:-----------|
| 2025-04-25    | Natural           | Trans      | Consumo           | Garantia idónea o no idónea |            1.13918e+07 |                                  5 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2025 | Ciudades y aglomeraciones | Urbano         |                               25.52   |  05001 | NO PDET    |
| 2025-04-18    | Natural           | No binario | Consumo           | Sin garantia                |       250000           |                                  2 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2025 | Ciudades y aglomeraciones | Urbano         |                               20.464  |  05001 | NO PDET    |
| 2025-07-04    | Natural           | No binario | Consumo           | Garantia idónea o no idónea |            3.85e+06    |                                  3 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2025 | Ciudades y aglomeraciones | Urbano         |                               43.3219 |  05001 | NO PDET    |
| 2025-03-28    | Natural           | No binario | Consumo           | Sin garantia                |        90207           |                                  2 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2025 | Ciudades y aglomeraciones | Urbano         |                                0      |  05001 | NO PDET    |
| 2026-08-07    | Natural           | No binario | Consumo           | Garantia idónea o no idónea |            1.83294e+08 |                                642 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2026 | Ciudades y aglomeraciones | Urbano         |                               24.8356 |  05001 | NO PDET    |

## Municipios - codigo (Observatorio, solo lectura)

Tabla: `prueba-ofr.Municipios.CODIGO`

Filas: **20,196** -- Columnas: **6**

| Columna | Tipo |
|---|---|
| cod_dane | STRING |
| nombre_departamento | STRING |
| nombre_municipio | STRING |
| region | STRING |
| fecha | INTEGER |
| ruralidad | STRING |

Muestra (primeras 5 filas):

|   cod_dane | nombre_departamento   | nombre_municipio   | region   |   fecha | ruralidad   |
|-----------:|:----------------------|:-------------------|:---------|--------:|:------------|
|      13490 | Bolívar               | Norosí             | Caribe   |    2005 |             |
|      19300 | Cauca                 | Guachené           | Pacífico |    2005 |             |
|      23682 | Córdoba               | San José de Uré    | Caribe   |    2005 |             |
|      23815 | Córdoba               | Tuchín             | Caribe   |    2005 |             |
|      23815 | Córdoba               | Tuchín             | Caribe   |    2010 |             |
