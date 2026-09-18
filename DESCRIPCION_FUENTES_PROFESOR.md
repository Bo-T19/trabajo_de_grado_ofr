# Descripcion de las fuentes del Observatorio (cuenta personal)

Generado automaticamente por `describir_fuentes_profesor.py`, usando la cuenta personal de Google (ADC) mientras el profesor autoriza la cuenta de servicio para estas tres tablas -- ver describir_fuentes.py para las cuatro tablas propias. No editar a mano -- se vuelve a generar completo cada vez que se corre el script.

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

|   id_credito | fecha_credito       |   cod_municipio | tipo_cartera   | tipo_intermediario   | tipo_productor   | tipo_beneficiario                   | tipo_persona   | sexo   |   cod_destino | linea_credito      | cadena                      | eslabon_cadena   |   valor_credito |   valor_inversion |   plazo |   periodo_gracia |   cuotas |   cuotas_capital | tasa_indexacion   | periodicidad_tasa_indexacion   |   puntos_adicionales |   garantia_fag | nombre_programa            |   indicador_lec |   valor_subsidio |   nuevo | viernes    |   tasa_total | DPNOM     |   MPIO | DPMP     | PDET   | region       | ruralidad                 | Destino   | Nombre_destino     |
|-------------:|:--------------------|----------------:|:---------------|:---------------------|:-----------------|:------------------------------------|:---------------|:-------|--------------:|:-------------------|:----------------------------|:-----------------|----------------:|------------------:|--------:|-----------------:|---------:|-----------------:|:------------------|:-------------------------------|---------------------:|---------------:|:---------------------------|----------------:|-----------------:|--------:|:-----------|-------------:|:----------|-------:|:---------|:-------|:-------------|:--------------------------|:----------|:-------------------|
|   2650112832 | 2026-01-19 00:00:00 |           27493 | Redescuento    | Bancos               | Pequeño ppib     | Pequeño productor de ingresos bajos | Natural        | Hombre |        141430 | Inversión          | Platano                     | Producción       |     7e+06       |       7e+06       |      84 |                2 |       14 |               12 | IBR               | Semestral                      |                 6.7  |              1 | IBR CREDITO ORDINARIO      |               0 |                0 |       1 | 2026-01-16 |    0.176032  |           |        |          | <NA>   |              |                           | 141430    | Plátano            |
|   2202401153 | 2022-07-14 00:00:00 |           05001 | Sustitutiva    | Bancos               | Grande           | Grande productor                    | Jurídica       | NA     |        101056 | Inversión          | Flores                      | Producción       |     1e+09       |       1e+09       |      12 |                0 |       12 |               12 | IBR               | Mensual                        |                 3.07 |              0 | IBR CREDITO ORDINARIO      |               0 |                0 |       0 | 2022-07-08 |    0.11447   | Antioquia |  05001 | Medellín | 0      | Eje cafetero | Ciudades y aglomeraciones | 101056    | Flores ciclo corto |
|   2402916929 | 2024-12-26 00:00:00 |           05001 | Sustitutiva    | Bancos               | Grande           | Grande productor                    | Jurídica       | NA     |        111200 | Inversión          | Arroz                       | Producción       |     2.2e+06     |       5e+07       |      36 |               35 |       36 |                1 | IBR               | Mensual                        |                 0    |              0 | IBR TARJETA AGROPECUARIA   |               0 |                0 |       0 | 2024-12-20 |    0.0937309 | Antioquia |  05001 | Medellín | 0      | Eje cafetero | Ciudades y aglomeraciones | 111200    | Arroz secano       |
|   2302738667 | 2023-12-05 00:00:00 |           05001 | Redescuento    | Bancos               | Grande           | Grande productor                    | Jurídica       | NA     |        121610 | Inversión          | Hortalizas                  | Producción       |     2.2e+08     |       2.75e+08    |      36 |                0 |       36 |               36 | IBR               | Mensual                        |                 6.9  |              0 | IBR CREDITO ORDINARIO      |               0 |                0 |       0 | 2023-12-01 |    0.209759  | Antioquia |  05001 | Medellín | 0      | Eje cafetero | Ciudades y aglomeraciones | 121610    | Champiñones        |
|   2102164306 | 2021-05-20 00:00:00 |           05001 | Sustitutiva    | Microfinancieras     | Mediano          | Mediano productor                   | Natural        | Hombre |        129978 | Capital de Trabajo | Actividades Complementarias | Producción       |     1.54811e+08 |       1.54811e+08 |       2 |                0 |        1 |                1 | IBR               | Mensual                        |                 9.5  |              0 | IBR FACTORING AGROPECUARIO |               0 |                0 |       0 | 2021-05-14 |    0.118131  | Antioquia |  05001 | Medellín | 0      | Eje cafetero | Ciudades y aglomeraciones | <NA>      |                    |

## SFC414 (Observatorio, solo lectura)

Tabla: `prueba-ofr.Inclusion_Financiera.SFC414_DASH`

Filas: **1,948,973** -- Columnas: **17**

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

| Fecha_Corte   | Tipo_de_persona   | Sexo       | Tipo_de_credito    | Tipo_de_garantia            |   Montos_desembolsados |   Numero_de_creditos_desembolsados |   Codigo_Municipio | nombre_departamento   | nombre_municipio   | region       |   fecha | ruralidad                 | Rural_Urbano   |   Tasa_efectiva_promedio_ponderada_AD |   MPIO | PDET_Nom   |
|:--------------|:------------------|:-----------|:-------------------|:----------------------------|-----------------------:|-----------------------------------:|-------------------:|:----------------------|:-------------------|:-------------|--------:|:--------------------------|:---------------|--------------------------------------:|-------:|:-----------|
| 2024-06-21    | Natural           | No binario | Crédito productivo | Sin garantia                |            8.7e+06     |                                  1 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2024 | Ciudades y aglomeraciones | Urbano         |                              36.6     |  05001 | NO PDET    |
| 2025-11-14    | Natural           | No binario | Consumo            | Garantia idónea o no idónea |            1.61e+06    |                                  2 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2025 | Ciudades y aglomeraciones | Urbano         |                              51.6142  |  05001 | NO PDET    |
| 2026-06-05    | Natural           | No binario | Consumo            | Sin garantia                |            3.48246e+06 |                                 16 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2026 | Ciudades y aglomeraciones | Urbano         |                              15.5386  |  05001 | NO PDET    |
| 2025-09-12    | Natural           | No binario | Consumo            | Sin garantia                |            4.3925e+06  |                                 24 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2025 | Ciudades y aglomeraciones | Urbano         |                               4.84747 |  05001 | NO PDET    |
| 2026-01-02    | Natural           | No binario | Consumo            | Sin garantia                |       955213           |                                  7 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2026 | Ciudades y aglomeraciones | Urbano         |                               1.52825 |  05001 | NO PDET    |

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
