# Guía de BigQuery — administración de Google Cloud

Documento **para el equipo**: qué se creó en Google Cloud, por qué, cómo se
da acceso a alguien nuevo y qué está pendiente. Para reproducir el trabajo
no hace falta leerlo: lo necesario sobre la llave de BigQuery está en
[`2_DESCARGA_DE_DATOS.md`](../2_DESCARGA_DE_DATOS.md), sección 1.5.

*(Configurado el 13-14 de septiembre de 2026. Si algo de lo descrito
aquí cambia — un rol, un dataset nuevo, la cuenta de facturación — hay
que actualizar este documento en el mismo commit que el cambio.)*

## Índice

1. [Qué existe hoy, en una tabla](#1-qué-existe-hoy-en-una-tabla)
2. [Por qué está organizado así](#2-por-qué-está-organizado-así)
3. [Paso a paso: cómo se configuró (reproducible)](#3-paso-a-paso-cómo-se-configuró-reproducible)
4. [Qué usa esta configuración](#4-qué-usa-esta-configuración)
5. [Cómo lo usa cada integrante del equipo](#5-cómo-lo-usa-cada-integrante-del-equipo)
6. [Cómo agregar a alguien nuevo al equipo](#6-cómo-agregar-a-alguien-nuevo-al-equipo)
7. [Pendientes y cosas por verificar](#7-pendientes-y-cosas-por-verificar)
8. [Solución de problemas](#8-solución-de-problemas)

---

## 1. Qué existe hoy, en una tabla

| Recurso | Nombre / ID | Para qué |
|---|---|---|
| Proyecto de Google Cloud | `ofr-credito-deforestacion` | Contenedor de todo lo de abajo. Es un proyecto **propio del equipo**, distinto del proyecto de BigQuery del profesor/Observatorio (ver sección 7). |
| Cuenta dueña del proyecto | `trabajodegrado139@gmail.com` | Cuenta de Gmail creada para el equipo; es la que tiene rol *Owner* y con la que se entra a la consola por navegador. |
| Dataset de BigQuery | `staging` (ubicación `US`) | Una tabla por fuente, tal como la genera cada script del pipeline. Ver sección 2. **Las tablas vencen a los 60 días** (modo Sandbox, sección 8): al 17/11/2026 el dataset está vacío, y hay que volver a subirlas con `subir-bigquery` antes de consultarlas. |
| Dataset de BigQuery | `analitica` (ubicación `US`) | Pensado para tablas ya integradas/cruzadas (por ejemplo, deforestación + crédito agropecuario). Está vacío: el panel municipal que cruza esas fuentes se arma en local (`datos/analisis/`) y no se sube. |
| Cuenta de servicio | `pipeline-satelital@ofr-credito-deforestacion.iam.gserviceaccount.com` | Identidad que usa el **código** (no una persona) para escribir en BigQuery. Ver sección 2 para por qué existe una cuenta aparte. |
| Roles de esa cuenta | `BigQuery Data Editor` + `BigQuery Job User` (a nivel de proyecto) | Puede crear/reemplazar tablas en cualquier dataset del proyecto y correr los jobs de carga. No puede tocar facturación, borrar el proyecto, ni administrar permisos. |
| Llave de la cuenta de servicio | archivo `.json`, tipo `TYPE_GOOGLE_CREDENTIALS_FILE` | Credencial que usa `subir_bigquery.py` para autenticarse como `pipeline-satelital` sin intervención humana. Cada integrante la guarda localmente en `datos/logs/bigquery-key.json` (ver sección 5). |
| Bucket de Cloud Storage | *(no creado todavía)* | Bloqueado: Cloud Storage exige una cuenta de facturación activa (aunque sea la prueba gratis de USD 300) antes de crear el primer bucket. Ver sección 7. |

## 2. Por qué está organizado así

**Un proyecto nuevo, no el `Prueba-OFR` que ya existía.** Se decidió
crear `ofr-credito-deforestacion` como proyecto definitivo (en vez de
seguir usando el de pruebas) para que el entregable final quede en un
proyecto con nombre claro y estable, sin mezclar experimentos.

**Dos datasets (`staging` / `analitica`), no uno solo.** La regla
práctica: si algo se va a consultar, cruzar o agregar con SQL, es una
tabla de BigQuery; si es un archivo que solo hay que conservar tal cual
llegó (crudo, no tabular), va a un bucket de Cloud Storage (pendiente,
sección 7). Dentro de BigQuery, separar **staging** (una tabla limpia
por fuente, sin cruzar) de **analitica** (tablas ya integradas) permite
reconstruir la capa final desde cero si cambia la metodología del
cruce, sin tener que volver a tocar ni re-descargar las fuentes.
`staging` recibe las cuatro tablas del panel satelital cuando se corre
`subir-bigquery` (sección 4), y en modo Sandbox vencen a los 60 días
(sección 8).
`analitica` sigue vacío: el cruce con el crédito y la producción, el panel
municipal, se terminó haciendo en local con
`procesamiento y eda/panel_municipal_armado.ipynb`, que lee las tablas del
Observatorio desde BigQuery y guarda el resultado en `datos/analisis/`.

**Ubicación `US` (multi-región) en ambos datasets.** Es la ubicación
por defecto más simple para el nivel gratuito de BigQuery (Sandbox) y
no tiene costo de almacenamiento en el rango que maneja este proyecto.
**Importante:** el proyecto del profesor/Observatorio (`prueba-ofr`)
resultó compatible -- las consultas cross-project ya corren sin error
de ubicación (ver sección 7).

**Una cuenta de servicio (`pipeline-satelital`), no la cuenta de
Gmail del equipo.** La cuenta de Gmail es una *cuenta de usuario*: sirve
para que una persona inicie sesión desde un navegador, no para que un
script se autentique solo. Una *cuenta de servicio* es una identidad
que pertenece al proyecto, pensada exactamente para eso, y se le puede
dar el permiso mínimo que necesita (aquí, solo escribir en BigQuery y
correr jobs) sin exponer la cuenta completa del equipo. El detalle
completo de este razonamiento —y por qué el archivo `.json` de la
llave debe tratarse como una contraseña— está en `GUIA_CODIGO.md`,
sección 3.16.

## 3. Paso a paso: cómo se configuró (reproducible)

Esto sirve para dos cosas: entender qué se hizo, y poder reproducirlo
si algún día hay que montar el mismo proyecto en otra cuenta (por
ejemplo, si la Javeriana da una cuenta institucional más adelante).

### 3.1 Crear el proyecto

1. En [console.cloud.google.com](https://console.cloud.google.com), con
   la cuenta `trabajodegrado139@gmail.com` iniciada, ir a **"New
   project"** (o `console.cloud.google.com/projectcreate`).
2. **Project name**: `ofr-credito-deforestacion`.
3. Clic en **"Edit"** junto al Project ID (autogenerado) y escribir el
   mismo texto, `ofr-credito-deforestacion`, como ID definitivo — el ID
   **no se puede cambiar después**, a diferencia del nombre.
4. **Create**. Tarda unos segundos; queda seleccionable desde el
   selector de proyectos arriba a la izquierda.

### 3.2 Crear los datasets de BigQuery

Con el proyecto `ofr-credito-deforestacion` seleccionado:

1. Ir a **BigQuery → Explorer** (icono de brújula en el panel
   izquierdo).
2. Clic en los tres puntos junto al nombre del proyecto → **"Create
   dataset"**.
3. **Dataset ID**: `staging`. **Data location**: `US (multiple regions
   in the United States)`. **Create data set**.
4. Repetir para **Dataset ID**: `analitica`, misma ubicación `US`.

No hace falta cuenta de facturación para este paso: BigQuery funciona
en modo **Sandbox** (gratis, con algunas limitaciones — ver sección 8)
mientras no se active facturación en el proyecto.

### 3.3 Crear la cuenta de servicio

1. **IAM y administración → Cuentas de servicio → Crear cuenta de
   servicio** (o `console.cloud.google.com/iam-admin/serviceaccounts/create`).
2. **Nombre**: `pipeline-satelital`. **Descripción**: algo como "Cuenta
   de servicio para el pipeline de descarga y carga de datos
   satelitales de deforestación a BigQuery/Cloud Storage."
3. **Crear y continuar**.

### 3.4 Darle permisos (IAM)

1. **IAM y administración → IAM → Grant access** (o, desde la propia
   cuenta de servicio, la pestaña "Permissions").
2. **Nuevos principales**: `pipeline-satelital@ofr-credito-deforestacion.iam.gserviceaccount.com`.
3. **Rol 1**: `BigQuery Data Editor`. **Add another role → Rol 2**:
   `BigQuery Job User`.
4. **Save**.

Con esto la cuenta puede escribir tablas y correr jobs de carga en
**cualquier** dataset del proyecto (hoy son solo `staging` y
`analitica`), pero nada más — no puede, por ejemplo, borrar datasets
ajenos ni tocar la facturación.

### 3.5 Generar y descargar la llave

1. Entrar a la cuenta de servicio → pestaña **Keys** → **Add key →
   Create new key**.
2. Tipo **JSON** (viene marcado por defecto, "Recommended"). **Create**.
3. El navegador descarga automáticamente un archivo tipo
   `ofr-credito-deforestacion-xxxxxxxx.json`. Ese archivo es la
   credencial completa: guardarlo de inmediato como
   `datos/logs/bigquery-key.json` dentro del repositorio local (esa
   carpeta ya está excluida de Git, ver `.gitignore`) y **no**
   compartirlo por chat, correo ni subirlo a ningún repositorio.

### 3.6 (Pendiente) Bucket de Cloud Storage

Requiere activar facturación en el proyecto primero (tarjeta propia o
cuenta institucional) — ver sección 7. Una vez activa:

1. **Cloud Storage → Buckets → Create**.
2. Elegir un nombre único globalmente (por ejemplo
   `ofr-credito-deforestacion-crudos`), la misma región/ubicación que
   los datasets de BigQuery (`US`) para evitar costos de transferencia
   entre regiones, y clase de almacenamiento *Standard*.
3. Dar a `pipeline-satelital` el rol `Storage Object Admin` **sobre
   ese bucket específico** (no a nivel de proyecto), para que el
   código pueda subir y reemplazar archivos crudos ahí.

## 4. Qué usa esta configuración

La llave de la cuenta de servicio se usa para cuatro cosas:

| Qué | Para qué la usa |
|---|---|
| `python main_local.py subir-bigquery` (Paso 11) | Escribir las cuatro tablas en `staging` |
| `python main_local.py describir-fuentes` (Paso 12) | Leer las cuatro tablas de `staging` |
| `python main_local.py describir-fuentes-profesor` (Paso 13) | Leer las cinco tablas del Observatorio en `prueba-ofr` |
| `procesamiento y eda/panel_municipal_armado.ipynb` (Paso 14) | Descargar las cinco tablas del Observatorio y armar el panel municipal, del que dependen el análisis, la segmentación y los modelos |

También la usan cuatro notebooks exploratorios que leen directo las tablas
del Observatorio (ver `3_NOTEBOOKS.md`, sección 2).

Sin la llave no se puede hacer nada de esto. Alguien de fuera del equipo
que quiera reproducir el trabajo tiene que pedírsela al equipo.

## 5. Cómo lo usa cada integrante del equipo

Cada persona que vaya a usarla en su propia máquina necesita, una sola vez:

1. Tener el repositorio actualizado (`git pull`).
2. Instalar las dependencias: `pip install -r requirements_local.txt`
   (con el entorno virtual del proyecto activado, ver
   `2_DESCARGA_DE_DATOS.md`, secciones 1.3 y 1.4).
3. Conseguir el archivo `bigquery-key.json` (quien lo generó lo
   comparte por un canal seguro — **nunca** por chat/correo en texto
   plano ni por Git; ver sección 6 para la alternativa de generar una
   llave propia) y copiarlo en `datos/logs/bigquery-key.json`.

Después de eso, en cualquier momento:

```bash
python main_local.py subir-bigquery              # sube las cuatro tablas que existan
python main_local.py subir-bigquery --solo gfw   # sube solo una
```

No hace falta que la persona tenga una cuenta de Google con acceso a la
consola para esto — la llave de la cuenta de servicio es suficiente.
Acceso a la **consola** (para ver las tablas en el navegador, correr
consultas SQL a mano, etc.) es un permiso aparte, ver sección 6.

## 6. Cómo agregar a alguien nuevo al equipo

Hay dos accesos distintos y es fácil confundirlos:

**(a) Poder correr el pipeline, subir tablas y leer las del
Observatorio** — no requiere nada en Google Cloud, solo el archivo
`bigquery-key.json` (sección 5).

**(b) Poder entrar a la consola de Google Cloud** (para explorar las
tablas visualmente, correr SQL desde el navegador, revisar permisos,
etc.) — esto sí requiere que alguien con acceso de administración
(hoy, quien tenga la contraseña de `trabajodegrado139@gmail.com`, que
es *Owner*) agregue a la persona:

1. **IAM y administración → IAM → Grant access.**
2. **Nuevos principales**: la cuenta de Gmail personal de esa persona.
3. **Rol**: `BigQuery Data Viewer` si solo necesita consultar, o
   `BigQuery Data Editor` si también va a crear/modificar tablas a mano
   desde la consola. Evitar dar `Owner` o `Editor` de proyecto a menos
   de que sea realmente necesario.

**Sobre compartir vs. regenerar la llave de servicio:** para un equipo
pequeño de trabajo de grado, compartir el mismo `bigquery-key.json`
entre todos (por un canal seguro, una sola vez) es razonable y más
simple. Si más adelante se quiere poder revocar el acceso de una sola
persona sin afectar a las demás, la alternativa es generar una llave
adicional para esa persona desde la misma cuenta de servicio (**Keys →
Add key**, sección 3.5) — una cuenta de servicio puede tener varias
llaves activas a la vez, cada una revocable por separado.

## 7. Pendientes y cosas por verificar

- **Bucket de Cloud Storage**: bloqueado hasta activar una cuenta de
  facturación (tarjeta propia o institucional de la Javeriana). Ver
  sección 3.6 para los pasos una vez esté disponible.
- ~~Ubicación del proyecto del profesor/Observatorio~~ — **resuelto**:
  las consultas cross-project contra `prueba-ofr` (`describir_fuentes_profesor.py`,
  GUIA_CODIGO.md sección 3.18) corren sin error de ubicación, así que
  las regiones son compatibles y no hace falta copiar datos primero.
- ~~Acceso de la cuenta de servicio al proyecto del profesor~~ —
  **resuelto**: el profesor le dio acceso de lectura a las tres tablas
  financieras puntuales (`FINAGRO_Desembolsos_EFECTIVA`, `SFC414_DASH`,
  `Municipios.CODIGO`) primero a las cuentas personales del equipo
  (14/09/2026) y luego, el 02/10/2026, también a la **cuenta de
  servicio** `pipeline-satelital`. Ya verificado y en uso:
  `describir_fuentes_profesor.py` usa esa cuenta de servicio (la misma
  de `describir_fuentes.py`), no la cuenta personal vía ADC -- ver
  GUIA_CODIGO.md sección 3.18. El 09/10/2026 el profesor compartió dos
  tablas más, de producción agropecuaria (`Produccion.eva_full_enriquecido`
  y `Produccion.ICA_pecuario`, esta última "aún se está arreglando" según
  su propio correo), esta vez directo a la cuenta de servicio -- sin pasar
  primero por las cuentas personales. En total son cinco tablas de solo
  lectura del Observatorio. No hace falta copiar ninguna al proyecto
  propio: se consultan directamente con su `proyecto.dataset.tabla`
  completo en cualquier `JOIN`.
- **Tablas de `staging` vencidas**: en modo Sandbox las tablas vencen a
  los 60 días, y al 17/11/2026 las cuatro ya habían vencido. Mientras no
  se active facturación, hay que volver a correr `subir-bigquery` antes
  de usar `describir-fuentes`.
- **Tablas de `analitica`**: no existen. El cruce municipal entre la
  deforestación y las variables financieras y de producción del
  Observatorio se hizo en local (`panel_municipal_armado.ipynb`, que deja
  el panel en `datos/analisis/`), sin subirlo a BigQuery. Subirlo a
  `analitica` queda como opción. La compatibilidad de la llave municipal (`cod_dane`) ya se
  verificó por separado -- ver `catalogo_paneles.ipynb` sección 6 y
  3_NOTEBOOKS.md, sección 2: 99.9% de match tratando `cod_dane` como
  texto de 5 caracteres con cero a la izquierda. La tabla `staging.*` de
  este proyecto guardaba `cod_dane` como INTEGER (perdía el cero) hasta
  que se corrigió en `subir_bigquery.py` el 17/09/2026 (forzando
  `dtype={"cod_dane": "string"}` al leer el CSV) -- tras volver a subir
  las cuatro tablas, ya quedan como STRING también en BigQuery, así que
  un `JOIN` directo ahí con las tablas del profesor ya no necesita
  `LPAD` primero.

## 8. Solución de problemas

**"Sign up for the cost-free trial to start using Cloud Storage"** al
intentar crear un bucket → falta activar facturación en el proyecto
(sección 3.6); BigQuery no lo necesita, Cloud Storage sí.

**El script `subir_bigquery.py` dice que no encuentra la credencial**
→ revisar que el archivo esté exactamente en `datos/logs/bigquery-key.json`
(mayúsculas/minúsculas y nombre exactos), o definir la variable de
entorno `GOOGLE_APPLICATION_CREDENTIALS` con la ruta completa al
`.json`.

**Tablas con menos de 10 GB / consultas con poco volumen y sin
facturación activa** → es normal, es el modo Sandbox de BigQuery. Con
Sandbox cada tabla vence 60 días después de creada: los dos datasets
tienen ese vencimiento por defecto (5.184.000.000 ms). Si se necesita que
una tabla de `staging`/`analitica` no venza, hay que activar facturación
(lo cual también habilita el bucket, sección 3.6). Si ya venció,
`subir-bigquery` la vuelve a crear.

**`describir-fuentes` falla con "Not found: Table"** → las tablas de
`staging` vencieron (ver el punto anterior). Correr primero
`python main_local.py subir-bigquery`, que las vuelve a crear desde
`datos/panel/`, y después `describir-fuentes`. Las tablas del Observatorio
(`prueba-ofr`) no vencen por esto, porque viven en el proyecto del
profesor.
