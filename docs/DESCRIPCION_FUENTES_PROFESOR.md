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

|   id_credito | fecha_credito       |   cod_municipio | tipo_cartera   | tipo_intermediario   | tipo_productor         | tipo_beneficiario                   | tipo_persona   | sexo   |   cod_destino | linea_credito   | cadena     | eslabon_cadena   |   valor_credito |   valor_inversion |   plazo |   periodo_gracia |   cuotas |   cuotas_capital | tasa_indexacion   | periodicidad_tasa_indexacion   |   puntos_adicionales |   garantia_fag | nombre_programa                                      |   indicador_lec |   valor_subsidio |   nuevo | viernes    |   tasa_total | DPNOM     |   MPIO | DPMP     | PDET   | region       | ruralidad                 | Destino   | Nombre_destino                              |
|-------------:|:--------------------|----------------:|:---------------|:---------------------|:-----------------------|:------------------------------------|:---------------|:-------|--------------:|:----------------|:-----------|:-----------------|----------------:|------------------:|--------:|-----------------:|---------:|-----------------:|:------------------|:-------------------------------|---------------------:|---------------:|:-----------------------------------------------------|----------------:|-----------------:|--------:|:-----------|-------------:|:----------|-------:|:---------|:-------|:-------------|:--------------------------|:----------|:--------------------------------------------|
|   2650201395 | 2026-04-22 00:00:00 |           27493 | Redescuento    | Bancos               | Pequeño ingresos bajos | Pequeño productor de ingresos bajos | Natural        | Hombre |        141430 | Inversión       | Plátano    | Producción       |         2.6e+07 |           2.6e+07 |      84 |                2 |       14 |               12 | IBR               | Semestral                      |                6     |              1 | IBR CREDITO ORDINARIO                                |               0 |                0 |       1 | 2026-04-17 |     0.184996 |           |        |          | <NA>   |              |                           | 141430    | Plátano                                     |
|   2550212204 | 2025-05-21 00:00:00 |           27493 | Redescuento    | Bancos               | Pequeño ppib           | Pequeño productor de ingresos bajos | Natural        | Mujer  |        141430 | Inversión       | Platano    | Producción       |         2.8e+07 |           2.8e+07 |      72 |                2 |       12 |               10 | IBR               | Semestral                      |                6.7   |              1 | IBR CREDITO ORDINARIO                                |               0 |                0 |       1 | 2025-05-16 |     0.160069 |           |        |          | <NA>   |              |                           | 141430    | Plátano                                     |
|   2603133148 | 2026-05-20 00:00:00 |           05001 | Redescuento    | Bancos               | Grande                 | Grande productor                    | Jurídica       | NA     |        104009 | Inversión       | Avicultura | Producción       |         5e+08   |           5e+08   |       6 |                0 |        6 |                6 | IBR               | Mensual                        |                1.351 |              0 | 2012 IBR TRANSFORMACION PRODUCTIVA Y SOSTENIBLE 2026 |               0 |                0 |       0 | 2026-05-15 |     0.126055 | Antioquia |  05001 | Medellín | 0      | Eje cafetero | Ciudades y aglomeraciones | <NA>      |                                             |
|   2650195843 | 2026-04-16 00:00:00 |           05001 | Redescuento    | Bancos               | Pequeño ingresos bajos | Pequeño productor de ingresos bajos | Natural        | Hombre |        105002 | Inversión       | Aguacate   | Producción       |         8e+06   |           8e+06   |      60 |                2 |       10 |                8 | IBR               | Semestral                      |                6     |              1 | IBR CREDITO ORDINARIO                                |               0 |                0 |       0 | 2026-04-10 |     0.183505 | Antioquia |  05001 | Medellín | 0      | Eje cafetero | Ciudades y aglomeraciones | 105002    | Adecuación de tierras para uso Agropecuario |
|   1850460614 | 2018-11-13 00:00:00 |           05001 | Redescuento    | Bancos               | Pequeño                | Pequeño productor                   | Natural        | Mujer  |        111500 | Inversión       | Papa       | Producción       |         8e+06   |           8e+06   |      10 |                0 |        1 |                1 | DTF               |                                |                7     |              1 | CREDITO ORDINARIO                                    |               0 |                0 |       0 | 2018-11-09 |     0.119076 | Antioquia |  05001 | Medellín | 0      | Eje cafetero | Ciudades y aglomeraciones | 111500    | Papa                                        |

## SFC414 (Observatorio, solo lectura)

Tabla: `prueba-ofr.Inclusion_Financiera.SFC414_DASH`

Filas: **1,991,643** -- Columnas: **17**

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

| Fecha_Corte   | Tipo_de_persona   | Sexo       | Tipo_de_credito   | Tipo_de_garantia   |   Montos_desembolsados |   Numero_de_creditos_desembolsados |   Codigo_Municipio | nombre_departamento   | nombre_municipio   | region       |   fecha | ruralidad                 | Rural_Urbano   |   Tasa_efectiva_promedio_ponderada_AD |   MPIO | PDET_Nom   |
|:--------------|:------------------|:-----------|:------------------|:-------------------|-----------------------:|-----------------------------------:|-------------------:|:----------------------|:-------------------|:-------------|--------:|:--------------------------|:---------------|--------------------------------------:|-------:|:-----------|
| 2025-08-01    | Natural           | No binario | Consumo           | Sin garantia       |            5.24785e+06 |                                 25 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2025 | Ciudades y aglomeraciones | Urbano         |                               2.92536 |  05001 | NO PDET    |
| 2025-03-07    | Natural           | No binario | Consumo           | Sin garantia       |       343050           |                                  4 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2025 | Ciudades y aglomeraciones | Urbano         |                              16.6603  |  05001 | NO PDET    |
| 2026-03-27    | Natural           | No binario | Consumo           | Sin garantia       |            2.71811e+06 |                                 24 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2026 | Ciudades y aglomeraciones | Urbano         |                               0       |  05001 | NO PDET    |
| 2024-12-13    | Natural           | Trans      | Consumo           | Sin garantia       |            2.35029e+06 |                                  8 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2024 | Ciudades y aglomeraciones | Urbano         |                              26.31    |  05001 | NO PDET    |
| 2025-05-16    | Natural           | Trans      | Consumo           | Sin garantia       |            5.85818e+06 |                                 15 |              05001 | Antioquia             | Medellín           | Eje cafetero |    2025 | Ciudades y aglomeraciones | Urbano         |                               2.17323 |  05001 | NO PDET    |

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

## EVA - produccion agropecuaria enriquecida (Observatorio, solo lectura)

Tabla: `prueba-ofr.Produccion.eva_full_enriquecido`

Filas: **347,141** -- Columnas: **23**

| Columna | Tipo |
|---|---|
| Cod_dep | STRING |
| Departamento | STRING |
| Cod_mun | STRING |
| Municipio | STRING |
| Grupo_cultivo | STRING |
| Subgrupo | STRING |
| Cultivo | STRING |
| Desagregacion | STRING |
| Year | DATE |
| Periodo | STRING |
| Sembrada | FLOAT |
| Cosechada | FLOAT |
| Produccion | FLOAT |
| Rendimiento | FLOAT |
| Estado | STRING |
| Nombre_cultivo | STRING |
| Ciclo | STRING |
| Cod_cultivo | STRING |
| Como_aparece_eva | STRING |
| Como_aparece_finagro | STRING |
| Como_pega | STRING |
| Nombre_perfecto | STRING |
| Tipo_match | STRING |

Muestra (primeras 5 filas):

|   Cod_dep | Departamento   |   Cod_mun | Municipio     | Grupo_cultivo                                    | Subgrupo            | Cultivo   | Desagregacion   | Year       | Periodo   |   Sembrada |   Cosechada |   Produccion |   Rendimiento | Estado      | Nombre_cultivo    | Ciclo       | Cod_cultivo   | Como_aparece_eva    | Como_aparece_finagro               | Como_pega                          | Nombre_perfecto     | Tipo_match      |
|----------:|:---------------|----------:|:--------------|:-------------------------------------------------|:--------------------|:----------|:----------------|:-----------|:----------|-----------:|------------:|-------------:|--------------:|:------------|:------------------|:------------|:--------------|:--------------------|:-----------------------------------|:-----------------------------------|:--------------------|:----------------|
|        91 | AMAZONAS       |     91540 | PUERTO NARIÑO | PLANTAS AROMATICAS, CONDIMENTARIAS Y MEDICINALES | PLANTAS MEDICINALES | ACHICORIA | ACHICORIA       | 2008-01-01 | 2008B     |          6 |           6 |            6 |             1 | HOJA FRESCA | CICHORIUM INTYBUS | TRANSITORIO |               | PLANTAS MEDICINALES | plantas medicinales y ornamentales | plantas medicinales y ornamentales | Plantas medicinales | destino-cultivo |
|        91 | AMAZONAS       |     91001 | LETICIA       | PLANTAS AROMATICAS, CONDIMENTARIAS Y MEDICINALES | PLANTAS MEDICINALES | ACHICORIA | ACHICORIA       | 2008-01-01 | 2008A     |          3 |           3 |            3 |             1 | HOJA FRESCA | CICHORIUM INTYBUS | TRANSITORIO |               | PLANTAS MEDICINALES | plantas medicinales y ornamentales | plantas medicinales y ornamentales | Plantas medicinales | destino-cultivo |
|        91 | AMAZONAS       |     91540 | PUERTO NARIÑO | PLANTAS AROMATICAS, CONDIMENTARIAS Y MEDICINALES | PLANTAS MEDICINALES | ACHICORIA | ACHICORIA       | 2007-01-01 | 2007B     |          4 |           4 |            4 |             1 | HOJA FRESCA | CICHORIUM INTYBUS | TRANSITORIO |               | PLANTAS MEDICINALES | plantas medicinales y ornamentales | plantas medicinales y ornamentales | Plantas medicinales | destino-cultivo |
|        91 | AMAZONAS       |     91001 | LETICIA       | PLANTAS AROMATICAS, CONDIMENTARIAS Y MEDICINALES | PLANTAS MEDICINALES | ACHICORIA | ACHICORIA       | 2008-01-01 | 2008B     |          3 |           3 |            3 |             1 | HOJA FRESCA | CICHORIUM INTYBUS | TRANSITORIO |               | PLANTAS MEDICINALES | plantas medicinales y ornamentales | plantas medicinales y ornamentales | Plantas medicinales | destino-cultivo |
|        91 | AMAZONAS       |     91001 | LETICIA       | PLANTAS AROMATICAS, CONDIMENTARIAS Y MEDICINALES | PLANTAS MEDICINALES | ACHICORIA | ACHICORIA       | 2007-01-01 | 2007B     |          2 |           2 |            2 |             1 | HOJA FRESCA | CICHORIUM INTYBUS | TRANSITORIO |               | PLANTAS MEDICINALES | plantas medicinales y ornamentales | plantas medicinales y ornamentales | Plantas medicinales | destino-cultivo |

## ICA pecuario - inventario pecuario (Observatorio, solo lectura; aun se esta arreglando, puede tener inconsistencias)

Tabla: `prueba-ofr.Produccion.ICA_pecuario`

Filas: **8,976** -- Columnas: **142**

| Columna | Tipo |
|---|---|
| anio | INTEGER |
| codigo_municipio | STRING |
| departamento | STRING |
| municipio | STRING |
| total_aves_capacidad_instalada_engorde | FLOAT |
| total_aves_capacidad_ocupada_engorde | FLOAT |
| aves_no_de_predios_engorde | FLOAT |
| total_aves_capacidad_instalada_levante | FLOAT |
| total_aves_capacidad_ocupada_levante | FLOAT |
| aves_no_de_predios_levante | FLOAT |
| total_aves_capacidad_instalada_postura | FLOAT |
| total_aves_capacidad_ocupada_postura | FLOAT |
| aves_no_de_predios_postura | FLOAT |
| total_aves_capacidad_instalada_material_genetico_o_reproductoras | FLOAT |
| total_aves_capacidad_ocupada_material_genetico_o_reproductoras | FLOAT |
| aves_no_de_predios_material_genetico_o_reproductoras | FLOAT |
| aves_capacidad_instalada_total | FLOAT |
| aves_capacidad_ocupada_total | FLOAT |
| aves_total_predios_avicolas | FLOAT |
| aves_traspatio_total | FLOAT |
| total_predios_aves_traspatio | FLOAT |
| total_aves | FLOAT |
| aves_total_predios_avicolas_mas_predios_traspatio | FLOAT |
| bovinos_terneras_menor_1_ano | FLOAT |
| bovinos_terneros_menor_1_ano | FLOAT |
| bovinos_hembras_1_2_anos | FLOAT |
| bovinos_machos_1_2_anos | FLOAT |
| bovinos_hembras_2_3_anos | FLOAT |
| bovinos_machos_2_3_anos | FLOAT |
| bovinos_hembras_mayor_3_anos | FLOAT |
| bovinos_machos_mayor_3_anos | FLOAT |
| total_bovinos | FLOAT |
| bovinos_no_de_fincas_1_a_50 | FLOAT |
| bovinos_no_de_fincas_51_a_100 | FLOAT |
| bovinos_no_de_fincas_101_a_500 | FLOAT |
| bovinos_no_de_fincas_501_o_mas | FLOAT |
| total_fincas_con_bovinos | FLOAT |
| bovinos_justificacion_variacion_20_o_dif_0 | FLOAT |
| bufalos_bucerras_menor_1_ano | FLOAT |
| bufalos_bucerros_menor_1_ano | FLOAT |
| bufalos_hembras_1_2_anos | FLOAT |
| bufalos_machos_1_2_anos | FLOAT |
| bufalos_hembras_2_3_anos | FLOAT |
| bufalos_machos_2_3_anos | FLOAT |
| bufalos_hembras_mayor_3_anos | FLOAT |
| bufalos_machos_mayor_3_anos | FLOAT |
| total_bufalos | FLOAT |
| bufalos_no_de_fincas_1_a_50 | FLOAT |
| bufalos_no_de_fincas_51_a_100 | FLOAT |
| bufalos_no_de_fincas_101_a_500 | FLOAT |
| bufalos_no_de_fincas_501_o_mas | FLOAT |
| total_fincas_con_bufalos | FLOAT |
| total_equinos | FLOAT |
| total_caprinos | FLOAT |
| total_ovinos | FLOAT |
| porcinos_hembras_cria_traspatio | FLOAT |
| porcinos_hembras_reemplazo_traspatio | FLOAT |
| porcinos_machos_reproductores_traspatio | FLOAT |
| porcinos_levante_ceba_traspatio | FLOAT |
| porcinos_traspatio_total | FLOAT |
| porcinos_total_predios_traspatio | FLOAT |
| porcinos_hembras_cria_comercial_familiar | FLOAT |
| porcinos_hembras_reemplazo_comercial_familiar | FLOAT |
| porcinos_machos_reproductores_comercial_familiar | FLOAT |
| porcinos_levante_ceba_comercial_familiar | FLOAT |
| total_porcinos_comercial_familiar | FLOAT |
| total_predios_porcinos_comercial_familiar | FLOAT |
| porcinos_hembras_cria_comercial_industrial | FLOAT |
| porcinos_hembras_reemplazo_comercial_industrial | FLOAT |
| porcinos_machos_reproductores_comercial_industrial | FLOAT |
| porcinos_levante_ceba_comercial_industrial | FLOAT |
| total_porcinos_comercial_industrial | FLOAT |
| total_predios_porcinos_comercial_industrial | FLOAT |
| porcinos_hembras_cria_tecnificada | FLOAT |
| porcinos_hembras_reemplazo_tecnificada | FLOAT |
| porcinos_machos_reproductores_tecnificada | FLOAT |
| porcinos_levante_ceba_tecnificada | FLOAT |
| porcinos_tecnificada_total | FLOAT |
| porcinos_total_granjas_porcinas_tecnificadas | FLOAT |
| porcinos_total_hembras_cria | FLOAT |
| porcinos_total_hembras_reemplazo | FLOAT |
| porcinos_total_machos_reproductores | FLOAT |
| porcinos_total_levante_ceba | FLOAT |
| total_porcinos | FLOAT |
| porcinos_total_predios_porcicolas | FLOAT |
| aves_no_de_predios_traspatio | FLOAT |
| aves_total_predios_traspatio | FLOAT |
| aves_observaciones | FLOAT |
| bovinos_no_de_fincas_1_a_50_bov | FLOAT |
| predios_con_bufalos | FLOAT |
| total_caprinos_hembras | FLOAT |
| total_caprinos_machos | FLOAT |
| total_ovinos_hembras | FLOAT |
| total_ovinos_machos | FLOAT |
| caprinos_hembras | FLOAT |
| caprinos_machos | FLOAT |
| ovinos_hembras | FLOAT |
| ovinos_machos | FLOAT |
| total_equinos_hembras | FLOAT |
| total_equinos_machos | FLOAT |
| porcinos_lechones_1_60_dias | FLOAT |
| porcinos_levante_61_120_dias | FLOAT |
| porcinos_ceba_121_180_dias | FLOAT |
| porcinos_hembras_reemplazo_120_240_dias | FLOAT |
| porcinos_hembras_cria_mayor_240_dias | FLOAT |
| porcinos_machos_reproductores_reemplazo_mayor_180_dias | FLOAT |
| porcinos_numero_de_granjas_porcinas_tecnificadas_10_hembras | FLOAT |
| porcinos_numero_de_granjas_porcinas_tecnificadas_11_30_hembras | FLOAT |
| porcinos_numero_de_granjas_porcinas_tecnificadas_31_100_hembras | FLOAT |
| porcinos_numero_de_granjas_porcinas_tecnificadas_mayor_101_hembras | FLOAT |
| porcinos_numero_de_granjas_porcinas_tecnificadas_levante_y_ceba | FLOAT |
| porcinos_numero_de_granjas_porcinas_tecnificadas_de_ciclo_completo | FLOAT |
| total_predios_porcinos | FLOAT |
| porcinos_granjas_porcinas_tecnificadas_10_hembras | FLOAT |
| porcinos_granjas_porcinas_tecnificadas_11_30_hembras | FLOAT |
| porcinos_granjas_porcinas_tecnificadas_31_100_hembras | FLOAT |
| porcinos_granjas_porcinas_tecnificadas_mayor_101_hembras | FLOAT |
| porcinos_granjas_porcinas_tecnificadas_levante_y_ceba | FLOAT |
| porcinos_granjas_porcinas_tecnificadas_de_ciclo_completo | FLOAT |
| porcinos_lactantes_comercial_familiar | FLOAT |
| porcinos_precebo_comercial_familiar | FLOAT |
| porcinos_levante_comercial_familiar | FLOAT |
| porcinos_ceba_comercial_familiar | FLOAT |
| porcinos_lactantes_comercial_industrial | FLOAT |
| porcinos_precebo_comercial_industrial | FLOAT |
| porcinos_levante_comercial_industrial | FLOAT |
| porcinos_ceba_comercial_industrial | FLOAT |
| porcinos_hembras_cria_produccion_tecnificada | FLOAT |
| porcinos_hembras_reemplazo_produccion_tecnificada | FLOAT |
| porcinos_machos_reproductores_produccion_tecnificada | FLOAT |
| porcinos_lactantes_produccion_tecnificada | FLOAT |
| porcinos_precebo_produccion_tecnificada | FLOAT |
| porcinos_levante_produccion_tecnificada | FLOAT |
| porcinos_ceba_produccion_tecnificada | FLOAT |
| total_porcinos_produccion_tecnificada | FLOAT |
| total_porcinos_produccion_comercial_y_tecnificada | FLOAT |
| porcinos_total_granjas_porcinas_comerciales_y_tecnificadas | FLOAT |
| porcinos_lactantes_traspatio | FLOAT |
| porcinos_precebo_traspatio | FLOAT |
| porcinos_levante_traspatio | FLOAT |
| porcinos_ceba_traspatio | FLOAT |
| porcinos_total_predios_produccion_tecnificada_traspatio | FLOAT |

Muestra (primeras 5 filas):

|   anio |   codigo_municipio | departamento   | municipio   |   total_aves_capacidad_instalada_engorde |   total_aves_capacidad_ocupada_engorde |   aves_no_de_predios_engorde |   total_aves_capacidad_instalada_levante |   total_aves_capacidad_ocupada_levante |   aves_no_de_predios_levante |   total_aves_capacidad_instalada_postura |   total_aves_capacidad_ocupada_postura |   aves_no_de_predios_postura |   total_aves_capacidad_instalada_material_genetico_o_reproductoras |   total_aves_capacidad_ocupada_material_genetico_o_reproductoras |   aves_no_de_predios_material_genetico_o_reproductoras |   aves_capacidad_instalada_total |   aves_capacidad_ocupada_total |   aves_total_predios_avicolas |   aves_traspatio_total |   total_predios_aves_traspatio |   total_aves |   aves_total_predios_avicolas_mas_predios_traspatio |   bovinos_terneras_menor_1_ano |   bovinos_terneros_menor_1_ano |   bovinos_hembras_1_2_anos |   bovinos_machos_1_2_anos |   bovinos_hembras_2_3_anos |   bovinos_machos_2_3_anos |   bovinos_hembras_mayor_3_anos |   bovinos_machos_mayor_3_anos |   total_bovinos |   bovinos_no_de_fincas_1_a_50 |   bovinos_no_de_fincas_51_a_100 |   bovinos_no_de_fincas_101_a_500 |   bovinos_no_de_fincas_501_o_mas |   total_fincas_con_bovinos |   bovinos_justificacion_variacion_20_o_dif_0 |   bufalos_bucerras_menor_1_ano |   bufalos_bucerros_menor_1_ano |   bufalos_hembras_1_2_anos |   bufalos_machos_1_2_anos |   bufalos_hembras_2_3_anos |   bufalos_machos_2_3_anos |   bufalos_hembras_mayor_3_anos |   bufalos_machos_mayor_3_anos |   total_bufalos |   bufalos_no_de_fincas_1_a_50 |   bufalos_no_de_fincas_51_a_100 |   bufalos_no_de_fincas_101_a_500 |   bufalos_no_de_fincas_501_o_mas |   total_fincas_con_bufalos |   total_equinos |   total_caprinos |   total_ovinos |   porcinos_hembras_cria_traspatio |   porcinos_hembras_reemplazo_traspatio |   porcinos_machos_reproductores_traspatio |   porcinos_levante_ceba_traspatio |   porcinos_traspatio_total |   porcinos_total_predios_traspatio |   porcinos_hembras_cria_comercial_familiar |   porcinos_hembras_reemplazo_comercial_familiar |   porcinos_machos_reproductores_comercial_familiar |   porcinos_levante_ceba_comercial_familiar |   total_porcinos_comercial_familiar |   total_predios_porcinos_comercial_familiar |   porcinos_hembras_cria_comercial_industrial |   porcinos_hembras_reemplazo_comercial_industrial |   porcinos_machos_reproductores_comercial_industrial |   porcinos_levante_ceba_comercial_industrial |   total_porcinos_comercial_industrial |   total_predios_porcinos_comercial_industrial |   porcinos_hembras_cria_tecnificada |   porcinos_hembras_reemplazo_tecnificada |   porcinos_machos_reproductores_tecnificada |   porcinos_levante_ceba_tecnificada |   porcinos_tecnificada_total |   porcinos_total_granjas_porcinas_tecnificadas |   porcinos_total_hembras_cria |   porcinos_total_hembras_reemplazo |   porcinos_total_machos_reproductores |   porcinos_total_levante_ceba |   total_porcinos |   porcinos_total_predios_porcicolas |   aves_no_de_predios_traspatio |   aves_total_predios_traspatio |   aves_observaciones |   bovinos_no_de_fincas_1_a_50_bov |   predios_con_bufalos |   total_caprinos_hembras |   total_caprinos_machos |   total_ovinos_hembras |   total_ovinos_machos |   caprinos_hembras |   caprinos_machos |   ovinos_hembras |   ovinos_machos |   total_equinos_hembras |   total_equinos_machos |   porcinos_lechones_1_60_dias |   porcinos_levante_61_120_dias |   porcinos_ceba_121_180_dias |   porcinos_hembras_reemplazo_120_240_dias |   porcinos_hembras_cria_mayor_240_dias |   porcinos_machos_reproductores_reemplazo_mayor_180_dias |   porcinos_numero_de_granjas_porcinas_tecnificadas_10_hembras |   porcinos_numero_de_granjas_porcinas_tecnificadas_11_30_hembras |   porcinos_numero_de_granjas_porcinas_tecnificadas_31_100_hembras |   porcinos_numero_de_granjas_porcinas_tecnificadas_mayor_101_hembras |   porcinos_numero_de_granjas_porcinas_tecnificadas_levante_y_ceba |   porcinos_numero_de_granjas_porcinas_tecnificadas_de_ciclo_completo |   total_predios_porcinos |   porcinos_granjas_porcinas_tecnificadas_10_hembras |   porcinos_granjas_porcinas_tecnificadas_11_30_hembras |   porcinos_granjas_porcinas_tecnificadas_31_100_hembras |   porcinos_granjas_porcinas_tecnificadas_mayor_101_hembras |   porcinos_granjas_porcinas_tecnificadas_levante_y_ceba |   porcinos_granjas_porcinas_tecnificadas_de_ciclo_completo |   porcinos_lactantes_comercial_familiar |   porcinos_precebo_comercial_familiar |   porcinos_levante_comercial_familiar |   porcinos_ceba_comercial_familiar |   porcinos_lactantes_comercial_industrial |   porcinos_precebo_comercial_industrial |   porcinos_levante_comercial_industrial |   porcinos_ceba_comercial_industrial |   porcinos_hembras_cria_produccion_tecnificada |   porcinos_hembras_reemplazo_produccion_tecnificada |   porcinos_machos_reproductores_produccion_tecnificada |   porcinos_lactantes_produccion_tecnificada |   porcinos_precebo_produccion_tecnificada |   porcinos_levante_produccion_tecnificada |   porcinos_ceba_produccion_tecnificada |   total_porcinos_produccion_tecnificada |   total_porcinos_produccion_comercial_y_tecnificada |   porcinos_total_granjas_porcinas_comerciales_y_tecnificadas |   porcinos_lactantes_traspatio |   porcinos_precebo_traspatio |   porcinos_levante_traspatio |   porcinos_ceba_traspatio |   porcinos_total_predios_produccion_tecnificada_traspatio |
|-------:|-------------------:|:---------------|:------------|-----------------------------------------:|---------------------------------------:|-----------------------------:|-----------------------------------------:|---------------------------------------:|-----------------------------:|-----------------------------------------:|---------------------------------------:|-----------------------------:|-------------------------------------------------------------------:|-----------------------------------------------------------------:|-------------------------------------------------------:|---------------------------------:|-------------------------------:|------------------------------:|-----------------------:|-------------------------------:|-------------:|----------------------------------------------------:|-------------------------------:|-------------------------------:|---------------------------:|--------------------------:|---------------------------:|--------------------------:|-------------------------------:|------------------------------:|----------------:|------------------------------:|--------------------------------:|---------------------------------:|---------------------------------:|---------------------------:|---------------------------------------------:|-------------------------------:|-------------------------------:|---------------------------:|--------------------------:|---------------------------:|--------------------------:|-------------------------------:|------------------------------:|----------------:|------------------------------:|--------------------------------:|---------------------------------:|---------------------------------:|---------------------------:|----------------:|-----------------:|---------------:|----------------------------------:|---------------------------------------:|------------------------------------------:|----------------------------------:|---------------------------:|-----------------------------------:|-------------------------------------------:|------------------------------------------------:|---------------------------------------------------:|-------------------------------------------:|------------------------------------:|--------------------------------------------:|---------------------------------------------:|--------------------------------------------------:|-----------------------------------------------------:|---------------------------------------------:|--------------------------------------:|----------------------------------------------:|------------------------------------:|-----------------------------------------:|--------------------------------------------:|------------------------------------:|-----------------------------:|-----------------------------------------------:|------------------------------:|-----------------------------------:|--------------------------------------:|------------------------------:|-----------------:|------------------------------------:|-------------------------------:|-------------------------------:|---------------------:|----------------------------------:|----------------------:|-------------------------:|------------------------:|-----------------------:|----------------------:|-------------------:|------------------:|-----------------:|----------------:|------------------------:|-----------------------:|------------------------------:|-------------------------------:|-----------------------------:|------------------------------------------:|---------------------------------------:|---------------------------------------------------------:|--------------------------------------------------------------:|-----------------------------------------------------------------:|------------------------------------------------------------------:|---------------------------------------------------------------------:|------------------------------------------------------------------:|---------------------------------------------------------------------:|-------------------------:|----------------------------------------------------:|-------------------------------------------------------:|--------------------------------------------------------:|-----------------------------------------------------------:|--------------------------------------------------------:|-----------------------------------------------------------:|----------------------------------------:|--------------------------------------:|--------------------------------------:|-----------------------------------:|------------------------------------------:|----------------------------------------:|----------------------------------------:|-------------------------------------:|-----------------------------------------------:|----------------------------------------------------:|-------------------------------------------------------:|--------------------------------------------:|------------------------------------------:|------------------------------------------:|---------------------------------------:|----------------------------------------:|----------------------------------------------------:|-------------------------------------------------------------:|-------------------------------:|-----------------------------:|-----------------------------:|--------------------------:|----------------------------------------------------------:|
|   2018 |              05001 | ANTIOQUIA      | MEDELLIN    |                                   850000 |                                 820000 |                           16 |                                    12000 |                                   9500 |                            2 |                                    76700 |                                  74525 |                            6 |                                                                  0 |                                                                0 |                                                      0 |                                0 |                         904025 |                            24 |                   7798 |                              0 |       911823 |                                                 989 |                           2155 |                            751 |                       2495 |                      1394 |                       2147 |                      1026 |                           3342 |                           148 |           13458 |                           580 |                              40 |                               18 |                                1 |                        639 |                                            0 |                              0 |                              0 |                          0 |                         0 |                          0 |                         0 |                              0 |                             0 |               4 |                             0 |                               0 |                                0 |                                0 |                          0 |             709 |              188 |            145 |                                 0 |                                      0 |                                         0 |                                 0 |                       5421 |                                461 |                                          0 |                                               0 |                                                  0 |                                          0 |                                   0 |                                           0 |                                            0 |                                                 0 |                                                    0 |                                            0 |                                     0 |                                             0 |                                   0 |                                        0 |                                           0 |                                   0 |                       158273 |                                             82 |                             0 |                                  0 |                                     0 |                             0 |           163694 |                                   0 |                            965 |                              0 |                    0 |                                 0 |                     1 |                        0 |                       0 |                      0 |                     0 |                  0 |                 0 |                0 |               0 |                       0 |                      0 |                         60782 |                          45215 |                        41723 |                                      2321 |                                   7623 |                                                      609 |                                                            19 |                                                                6 |                                                                 4 |                                                                    7 |                                                                21 |                                                                   25 |                      543 |                                                   0 |                                                      0 |                                                       0 |                                                          0 |                                                       0 |                                                          0 |                                       0 |                                     0 |                                     0 |                                  0 |                                         0 |                                       0 |                                       0 |                                    0 |                                              0 |                                                   0 |                                                      0 |                                           0 |                                         0 |                                         0 |                                      0 |                                       0 |                                                   0 |                                                            0 |                              0 |                            0 |                            0 |                         0 |                                                         0 |
|   2018 |              05002 | ANTIOQUIA      | ABEJORRAL   |                                        0 |                                      0 |                            0 |                                        0 |                                      0 |                            0 |                                        0 |                                      0 |                            0 |                                                                  0 |                                                                0 |                                                      0 |                                0 |                              0 |                             0 |                    386 |                              0 |          386 |                                                  15 |                           3405 |                           1908 |                       4742 |                      2949 |                       2760 |                      1704 |                           9560 |                           559 |           27587 |                          1141 |                              74 |                               29 |                                0 |                       1244 |                                            0 |                              0 |                              0 |                          0 |                         0 |                          0 |                         0 |                              0 |                             0 |               0 |                             0 |                               0 |                                0 |                                0 |                          0 |            1290 |               19 |              2 |                                 0 |                                      0 |                                         0 |                                 0 |                        300 |                                 50 |                                          0 |                                               0 |                                                  0 |                                          0 |                                   0 |                                           0 |                                            0 |                                                 0 |                                                    0 |                                            0 |                                     0 |                                             0 |                                   0 |                                        0 |                                           0 |                                   0 |                         1339 |                                             12 |                             0 |                                  0 |                                     0 |                             0 |             1639 |                                   0 |                             15 |                              0 |                    0 |                                 0 |                     0 |                        0 |                       0 |                      0 |                     0 |                  0 |                 0 |                0 |               0 |                       0 |                      0 |                           220 |                            374 |                          600 |                                        35 |                                    100 |                                                       10 |                                                             4 |                                                                1 |                                                                 0 |                                                                    0 |                                                                 5 |                                                                    2 |                       62 |                                                   0 |                                                      0 |                                                       0 |                                                          0 |                                                       0 |                                                          0 |                                       0 |                                     0 |                                     0 |                                  0 |                                         0 |                                       0 |                                       0 |                                    0 |                                              0 |                                                   0 |                                                      0 |                                           0 |                                         0 |                                         0 |                                      0 |                                       0 |                                                   0 |                                                            0 |                              0 |                            0 |                            0 |                         0 |                                                         0 |
|   2018 |              05004 | ANTIOQUIA      | ABRIAQUI    |                                        0 |                                      0 |                            0 |                                        0 |                                      0 |                            0 |                                        0 |                                      0 |                            0 |                                                                  0 |                                                                0 |                                                      0 |                                0 |                              0 |                             0 |                    586 |                              0 |          586 |                                                  35 |                           1146 |                            891 |                       1058 |                      1370 |                       1014 |                       451 |                           3045 |                           109 |            9084 |                           257 |                              33 |                               10 |                                0 |                        300 |                                            0 |                              0 |                              0 |                          0 |                         0 |                          0 |                         0 |                              0 |                             0 |               0 |                             0 |                               0 |                                0 |                                0 |                          0 |             708 |                7 |             28 |                                 0 |                                      0 |                                         0 |                                 0 |                        310 |                                 15 |                                          0 |                                               0 |                                                  0 |                                          0 |                                   0 |                                           0 |                                            0 |                                                 0 |                                                    0 |                                            0 |                                     0 |                                             0 |                                   0 |                                        0 |                                           0 |                                   0 |                            0 |                                              0 |                             0 |                                  0 |                                     0 |                             0 |              310 |                                   0 |                             35 |                              0 |                    0 |                                 0 |                     0 |                        0 |                       0 |                      0 |                     0 |                  0 |                 0 |                0 |               0 |                       0 |                      0 |                             0 |                              0 |                            0 |                                         0 |                                      0 |                                                        0 |                                                             0 |                                                                0 |                                                                 0 |                                                                    0 |                                                                 0 |                                                                    0 |                       15 |                                                   0 |                                                      0 |                                                       0 |                                                          0 |                                                       0 |                                                          0 |                                       0 |                                     0 |                                     0 |                                  0 |                                         0 |                                       0 |                                       0 |                                    0 |                                              0 |                                                   0 |                                                      0 |                                           0 |                                         0 |                                         0 |                                      0 |                                       0 |                                                   0 |                                                            0 |                              0 |                            0 |                            0 |                         0 |                                                         0 |
|   2018 |              05021 | ANTIOQUIA      | ALEJANDRIA  |                                        0 |                                      0 |                            0 |                                        0 |                                      0 |                            0 |                                        0 |                                      0 |                            0 |                                                                  0 |                                                                0 |                                                      0 |                                0 |                              0 |                             0 |                    330 |                              0 |          330 |                                                  50 |                            323 |                            219 |                        417 |                       216 |                        572 |                        95 |                           1512 |                           161 |            3515 |                           225 |                               6 |                                4 |                                0 |                        235 |                                            0 |                              0 |                              0 |                          0 |                         0 |                          0 |                         0 |                              0 |                             0 |               0 |                             0 |                               0 |                                0 |                                0 |                          0 |             420 |                0 |              0 |                                 0 |                                      0 |                                         0 |                                 0 |                        250 |                                 30 |                                          0 |                                               0 |                                                  0 |                                          0 |                                   0 |                                           0 |                                            0 |                                                 0 |                                                    0 |                                            0 |                                     0 |                                             0 |                                   0 |                                        0 |                                           0 |                                   0 |                            0 |                                              0 |                             0 |                                  0 |                                     0 |                             0 |              250 |                                   0 |                             50 |                              0 |                    0 |                                 0 |                     0 |                        0 |                       0 |                      0 |                     0 |                  0 |                 0 |                0 |               0 |                       0 |                      0 |                             0 |                              0 |                            0 |                                         0 |                                      0 |                                                        0 |                                                             0 |                                                                0 |                                                                 0 |                                                                    0 |                                                                 0 |                                                                    0 |                       30 |                                                   0 |                                                      0 |                                                       0 |                                                          0 |                                                       0 |                                                          0 |                                       0 |                                     0 |                                     0 |                                  0 |                                         0 |                                       0 |                                       0 |                                    0 |                                              0 |                                                   0 |                                                      0 |                                           0 |                                         0 |                                         0 |                                      0 |                                       0 |                                                   0 |                                                            0 |                              0 |                            0 |                            0 |                         0 |                                                         0 |
|   2018 |              05030 | ANTIOQUIA      | AMAGA       |                                   915000 |                                 895000 |                           16 |                                    32000 |                                  27800 |                            1 |                                    12000 |                                  11800 |                            1 |                                                                  0 |                                                                0 |                                                      0 |                                0 |                         934600 |                            18 |                    470 |                              0 |       935070 |                                                  93 |                            412 |                            416 |                        564 |                       951 |                        950 |                       629 |                            925 |                            52 |            4899 |                           230 |                              11 |                                9 |                                0 |                        250 |                                            0 |                              0 |                              0 |                          0 |                         0 |                          0 |                         0 |                              0 |                             0 |               2 |                             0 |                               0 |                                0 |                                0 |                          0 |             630 |                0 |              0 |                                 0 |                                      0 |                                         0 |                                 0 |                        753 |                                120 |                                          0 |                                               0 |                                                  0 |                                          0 |                                   0 |                                           0 |                                            0 |                                                 0 |                                                    0 |                                            0 |                                     0 |                                             0 |                                   0 |                                        0 |                                           0 |                                   0 |                        18009 |                                             33 |                             0 |                                  0 |                                     0 |                             0 |            18762 |                                   0 |                             75 |                              0 |                    0 |                                 0 |                     1 |                        0 |                       0 |                      0 |                     0 |                  0 |                 0 |                0 |               0 |                       0 |                      0 |                          6278 |                           5132 |                         4214 |                                       834 |                                   1435 |                                                      116 |                                                             7 |                                                                8 |                                                                 1 |                                                                    1 |                                                                 9 |                                                                    7 |                      153 |                                                   0 |                                                      0 |                                                       0 |                                                          0 |                                                       0 |                                                          0 |                                       0 |                                     0 |                                     0 |                                  0 |                                         0 |                                       0 |                                       0 |                                    0 |                                              0 |                                                   0 |                                                      0 |                                           0 |                                         0 |                                         0 |                                      0 |                                       0 |                                                   0 |                                                            0 |                              0 |                            0 |                            0 |                         0 |                                                         0 |
