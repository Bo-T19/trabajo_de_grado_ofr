# Descripcion de las fuentes de datos

Generado automaticamente por `describir_fuentes.py` (Paso 1 del EDA: inventario y descripcion inicial de datos). No editar a mano -- se vuelve a generar completo cada vez que se corre el script.

## GFW - alertas de disturbio (staging propio)

Tabla: `ofr-credito-deforestacion.staging.stg_gfw_alertas`

Filas: **3,524,664** -- Columnas: **19**

| Columna | Tipo |
|---|---|
| cell_id | STRING |
| periodo | STRING |
| area_def_ha | FLOAT |
| lon | FLOAT |
| lat | FLOAT |
| bosque_base_ha | FLOAT |
| departamento | STRING |
| def_acum_ha | FLOAT |
| bosque_remanente_ha | FLOAT |
| tasa_def | FLOAT |
| evento | INTEGER |
| lag_1_ha | FLOAT |
| lag_2_ha | FLOAT |
| lag_3_ha | FLOAT |
| media_movil_3 | FLOAT |
| anio | INTEGER |
| mes | INTEGER |
| cod_dane | INTEGER |
| municipio | STRING |

Muestra (primeras 5 filas):

|       cell_id | periodo    |   area_def_ha |      lon |     lat |   bosque_base_ha | departamento   |   def_acum_ha |   bosque_remanente_ha |    tasa_def |   evento |   lag_1_ha |   lag_2_ha |   lag_3_ha |   media_movil_3 |   anio |   mes |   cod_dane | municipio    |
|--------------:|:-----------|--------------:|---------:|--------:|-----------------:|:---------------|--------------:|----------------------:|------------:|---------:|-----------:|-----------:|-----------:|----------------:|-------:|------:|-----------:|:-------------|
| -668855_13972 | 2020-01-01 |       1.10757 | -66.8855 | 1.39724 |          1802.56 | Guainía        |       1.10757 |               1802.56 | 0.000614442 |        1 |  nan       |  nan       |  nan       |      nan        |   2020 |     1 |      94885 | La Guadalupe |
| -668855_13972 | 2020-02-01 |       1.32906 | -66.8855 | 1.39724 |          1802.56 | Guainía        |       2.43663 |               1801.45 | 0.00073777  |        1 |    1.10757 |  nan       |  nan       |      nan        |   2020 |     2 |      94885 | La Guadalupe |
| -668855_13972 | 2020-03-01 |       0.04924 | -66.8855 | 1.39724 |          1802.56 | Guainía        |       2.48587 |               1800.13 | 2.73536e-05 |        1 |    1.32906 |    1.10757 |  nan       |      nan        |   2020 |     3 |      94885 | La Guadalupe |
| -668855_13972 | 2020-04-01 |       0.02462 | -66.8855 | 1.39724 |          1802.56 | Guainía        |       2.51049 |               1800.08 | 1.36772e-05 |        1 |    0.04924 |    1.32906 |    1.10757 |        0.828623 |   2020 |     4 |      94885 | La Guadalupe |
| -668855_13972 | 2020-05-01 |       0       | -66.8855 | 1.39724 |          1802.56 | Guainía        |       2.51049 |               1800.05 | 0           |        0 |    0.02462 |    0.04924 |    1.32906 |        0.46764  |   2020 |     5 |      94885 | La Guadalupe |

## Hansen - perdida de cobertura arborea (staging propio)

Tabla: `ofr-credito-deforestacion.staging.stg_hansen_perdida`

Filas: **267,696** -- Columnas: **9**

| Columna | Tipo |
|---|---|
| cell_id | STRING |
| anio | INTEGER |
| perdida_ha | FLOAT |
| lon | FLOAT |
| lat | FLOAT |
| departamento | STRING |
| bosque_base_ha | FLOAT |
| cod_dane | INTEGER |
| municipio | STRING |

Muestra (primeras 5 filas):

|       cell_id |   anio |   perdida_ha |      lon |     lat | departamento   |   bosque_base_ha |   cod_dane | municipio    |
|--------------:|-------:|-------------:|---------:|--------:|:---------------|-----------------:|-----------:|:-------------|
| -668855_13972 |   2020 |       4.3125 | -66.8855 | 1.39724 | Guainía        |          1802.56 |      94885 | La Guadalupe |
| -668855_13972 |   2021 |       3.125  | -66.8855 | 1.39724 | Guainía        |          1802.56 |      94885 | La Guadalupe |
| -668855_13972 |   2022 |       5.5    | -66.8855 | 1.39724 | Guainía        |          1802.56 |      94885 | La Guadalupe |
| -668855_13972 |   2023 |       5.6875 | -66.8855 | 1.39724 | Guainía        |          1802.56 |      94885 | La Guadalupe |
| -668855_13972 |   2024 |       5.3125 | -66.8855 | 1.39724 | Guainía        |          1802.56 |      94885 | La Guadalupe |

## IDEAM - deforestacion oficial (staging propio)

Tabla: `ofr-credito-deforestacion.staging.stg_ideam_deforestacion`

Filas: **223,080** -- Columnas: **15**

| Columna | Tipo |
|---|---|
| cell_id | STRING |
| periodo | STRING |
| bosque_estable_ha | FLOAT |
| def_ha | FLOAT |
| sin_info_ha | FLOAT |
| regeneracion_ha | FLOAT |
| no_bosque_ha | FLOAT |
| bosque_ideam_ha | FLOAT |
| bosque_ideam_fin_ha | FLOAT |
| lon | FLOAT |
| lat | FLOAT |
| departamento | STRING |
| bosque_base_ha | FLOAT |
| cod_dane | INTEGER |
| municipio | STRING |

Muestra (primeras 5 filas):

|       cell_id | periodo   |   bosque_estable_ha |   def_ha |   sin_info_ha |   regeneracion_ha |   no_bosque_ha |   bosque_ideam_ha |   bosque_ideam_fin_ha |      lon |     lat | departamento   |   bosque_base_ha |   cod_dane | municipio    |
|--------------:|:----------|--------------------:|---------:|--------------:|------------------:|---------------:|------------------:|----------------------:|---------:|--------:|:---------------|-----------------:|-----------:|:-------------|
| -668855_13972 | 2020-2021 |             1004.69 |        0 |        0.25   |                 0 |        490.625 |           1004.69 |               1004.69 | -66.8855 | 1.39724 | Guainía        |          1802.56 |      94885 | La Guadalupe |
| -668855_13972 | 2021-2022 |             1008.31 |        0 |        0.125  |                 0 |        487.125 |           1008.31 |               1008.31 | -66.8855 | 1.39724 | Guainía        |          1802.56 |      94885 | La Guadalupe |
| -668855_13972 | 2022-2023 |             1008.56 |        0 |        0.4375 |                 0 |        489.688 |           1008.56 |               1008.56 | -66.8855 | 1.39724 | Guainía        |          1802.56 |      94885 | La Guadalupe |
| -668855_13972 | 2023-2024 |             1008.56 |        0 |        0      |                 0 |        489.688 |           1008.56 |               1008.56 | -66.8855 | 1.39724 | Guainía        |          1802.56 |      94885 | La Guadalupe |
| -668855_13972 | 2024-2025 |             1008.56 |        0 |        0.4375 |                 0 |        489.688 |           1008.56 |               1008.56 | -66.8855 | 1.39724 | Guainía        |          1802.56 |      94885 | La Guadalupe |

## DTD - alertas tempranas oficiales (staging propio)

Tabla: `ofr-credito-deforestacion.staging.stg_dtd_alertas`

Filas: **1,115,400** -- Columnas: **14**

| Columna | Tipo |
|---|---|
| cell_id | STRING |
| periodo | STRING |
| trimestre_txt | STRING |
| anio | INTEGER |
| trimestre | INTEGER |
| n_alertas | INTEGER |
| n_alertas_sinap | FLOAT |
| sinap_disponible | BOOLEAN |
| lon | FLOAT |
| lat | FLOAT |
| departamento | STRING |
| bosque_base_ha | FLOAT |
| cod_dane | INTEGER |
| municipio | STRING |

Muestra (primeras 5 filas):

|       cell_id | periodo    | trimestre_txt   |   anio |   trimestre |   n_alertas |   n_alertas_sinap | sinap_disponible   |      lon |     lat | departamento   |   bosque_base_ha |   cod_dane | municipio    |
|--------------:|:-----------|:----------------|-------:|------------:|------------:|------------------:|:-------------------|---------:|--------:|:---------------|-----------------:|-----------:|:-------------|
| -668855_13972 | 2020-01-01 | 2020-T1         |   2020 |           1 |           0 |                 0 | True               | -66.8855 | 1.39724 | Guainía        |          1802.56 |      94885 | La Guadalupe |
| -668856_13524 | 2020-01-01 | 2020-T1         |   2020 |           1 |           0 |                 0 | True               | -66.8856 | 1.35238 | Guainía        |          2432.12 |      94885 | La Guadalupe |
| -668857_13075 | 2020-01-01 | 2020-T1         |   2020 |           1 |           0 |                 0 | True               | -66.8857 | 1.30752 | Guainía        |          2111.56 |      94885 | La Guadalupe |
| -668859_12627 | 2020-01-01 | 2020-T1         |   2020 |           1 |           0 |                 0 | True               | -66.8859 | 1.26266 | Guainía        |          2016.19 |      94885 | La Guadalupe |
| -669296_15320 | 2020-01-01 | 2020-T1         |   2020 |           1 |           0 |                 0 | True               | -66.9296 | 1.53197 | Guainía        |          1928.25 |      94885 | La Guadalupe |

## FINAGRO - desembolsos de credito (Observatorio, solo lectura)

Tabla: `prueba-ofr.Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA`

**No se pudo leer esta tabla:** 403 Access Denied: Table prueba-ofr:Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA: User does not have permission to query table prueba-ofr:Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA, or perhaps it does not exist.; reason: accessDenied, message: Access Denied: Table prueba-ofr:Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA: User does not have permission to query table prueba-ofr:Inclusion_Financiera.FINAGRO_Desembolsos_EFECTIVA, or perhaps it does not exist.

Location: US
Job ID: 09634ac1-7dfa-4503-b6c2-79297ac45ddc


## SFC414 (Observatorio, solo lectura)

Tabla: `prueba-ofr.Inclusion_Financiera.SFC414_DASH`

**No se pudo leer esta tabla:** 403 Access Denied: Table prueba-ofr:Inclusion_Financiera.SFC414_DASH: User does not have permission to query table prueba-ofr:Inclusion_Financiera.SFC414_DASH, or perhaps it does not exist.; reason: accessDenied, message: Access Denied: Table prueba-ofr:Inclusion_Financiera.SFC414_DASH: User does not have permission to query table prueba-ofr:Inclusion_Financiera.SFC414_DASH, or perhaps it does not exist.

Location: US
Job ID: e325c006-d3f7-4d03-ac46-5378104c8207


## Municipios - codigo (Observatorio, solo lectura)

Tabla: `prueba-ofr.Municipios.CODIGO`

**No se pudo leer esta tabla:** 403 Access Denied: Table prueba-ofr:Municipios.CODIGO: User does not have permission to query table prueba-ofr:Municipios.CODIGO, or perhaps it does not exist.; reason: accessDenied, message: Access Denied: Table prueba-ofr:Municipios.CODIGO: User does not have permission to query table prueba-ofr:Municipios.CODIGO, or perhaps it does not exist.

Location: US
Job ID: ac18f538-0617-426e-96ec-f55f9d124962

