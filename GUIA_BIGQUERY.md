# Guía de BigQuery — configuración y cambios del pipeline

Este documento es el compañero de `GUIA_CODIGO.md`, pero para la parte
de **nube** en vez de la parte que corre en cada PC: qué se creó en
Google Cloud, por qué, y qué cambió en el código para conectar el
pipeline local con eso. Está escrito para que cualquier persona del
equipo —no solo quien lo configuró— entienda qué existe, pueda usarlo,
y pueda reproducirlo o extenderlo si hace falta.

*(Configurado el 13-14 de septiembre de 2026. Si algo de lo descrito
aquí cambia — un rol, un dataset nuevo, la cuenta de facturación — hay
que actualizar este documento en el mismo commit que el cambio.)*

## Índice

1. [Qué existe hoy, en una tabla](#1-qué-existe-hoy-en-una-tabla)
2. [Por qué está organizado así](#2-por-qué-está-organizado-así)
3. [Paso a paso: cómo se configuró (reproducible)](#3-paso-a-paso-cómo-se-configuró-reproducible)
4. [Cambios en el código de este repositorio](#4-cambios-en-el-código-de-este-repositorio)
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
| Dataset de BigQuery | `staging` (ubicación `US`) | Una tabla por fuente, tal como la genera cada script del pipeline. Ver sección 2. |
| Dataset de BigQuery | `analitica` (ubicación `US`) | Tablas ya integradas/cruzadas (por ejemplo, deforestación + crédito agropecuario), listas para el tablero o el modelo. Todavía vacío: se llenará en una fase posterior del proyecto. |
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
cruce, sin tener que volver a tocar ni re-descargar las fuentes. Hoy
`staging` tiene las cuatro tablas del panel satelital (sección 4);
`analitica` quedará para cuando exista la tabla municipal integrada con
crédito agropecuario y producción.

**Ubicación `US` (multi-región) en ambos datasets.** Es la ubicación
por defecto más simple para el nivel gratuito de BigQuery (Sandbox) y
no tiene costo de almacenamiento en el rango que maneja este proyecto.
**Importante:** si el proyecto del profesor/Observatorio usa una
ubicación distinta, un `JOIN` directo entre sus tablas y las nuestras
puede fallar o requerir copiar datos primero — ver el pendiente en la
sección 7.

**Una cuenta de servicio (`pipeline-satelital`), no la cuenta de
Gmail del equipo.** La cuenta de Gmail es una *cuenta de usuario*: sirve
para que una persona inicie sesión desde un navegador, no para que un
script se autentique solo. Una *cuenta de servicio* es una identidad
que pertenece al proyecto, pensada exactamente para eso, y se le puede
dar el permiso mínimo que necesita (aquí, solo escribir en BigQuery y
correr jobs) sin exponer la cuenta completa del equipo. El detalle
completo de este razonamiento —y por qué el archivo `.json` de la
llave debe tratarse como una contraseña— está en `GUIA_CODIGO.md`,
sección 5.16.

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

## 4. Cambios en el código de este repositorio

Todo lo de esta sección ya está aplicado en el repositorio; se deja
registrado aquí como changelog, para que quede claro qué cambió y por
qué la próxima vez que alguien revise el historial de Git.

| Archivo | Cambio |
|---|---|
| `subir_bigquery.py` | **Nuevo.** Lee los cuatro CSV de `datos/panel/` que ya existan y los sube (modo reemplazar, `WRITE_TRUNCATE`) al dataset `staging` de `ofr-credito-deforestacion`, autenticado con la cuenta de servicio `pipeline-satelital`. Ver `GUIA_CODIGO.md` sección 5.16 para el detalle completo. |
| `main_local.py` | Nuevo subcomando `subir-bigquery` (con `--solo` y `--dataset`), agregado al docstring de uso y al despachador de subcomandos, siguiendo el mismo patrón que los demás pasos del pipeline (lanza `subir_bigquery.py` como subproceso). |
| `requirements_local.txt` | Se agregó `google-cloud-bigquery>=3.25`, la única dependencia nueva que necesita `subir_bigquery.py`. |
| `GUIA_CODIGO.md` | Nueva sección **5.16** (referencia de `subir_bigquery.py`, con la tabla de alias → archivo → tabla destino, y el apartado "¿Por qué una cuenta de servicio con `key.json`...?") y nuevo **Paso 11** en la sección 3 ("Orden exacto de ejecución"). |
| `GUIA_BIGQUERY.md` | **Nuevo** (este archivo). |

Ningún script existente (`descargar_*.py`, `panel_*.py`, `consolidar.py`,
etc.) se modificó: `subir_bigquery.py` solo **lee** los CSV que esos
scripts ya producen en `datos/panel/`, como un paso final y opcional.

## 5. Cómo lo usa cada integrante del equipo

Cada persona del equipo que quiera correr `subir-bigquery` en su propia
máquina necesita, una sola vez:

1. Tener el repositorio actualizado (`git pull`) — trae `subir_bigquery.py`
   y el `requirements_local.txt` actualizado.
2. Instalar la dependencia nueva: `pip install -r requirements_local.txt`
   (con el entorno virtual del proyecto activado, ver `GUIA_CODIGO.md`
   sección 2.3-2.4).
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

**(a) Poder correr el pipeline y subir tablas** — no requiere nada en
Google Cloud, solo el archivo `bigquery-key.json` (sección 5).

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
- **Ubicación del proyecto del profesor/Observatorio**: falta
  confirmar en qué ubicación (`US`, `EU`, una región puntual) están sus
  datasets de BigQuery. Si no coincide con `US`, un `JOIN` directo
  entre sus tablas (Finagro, UPRA, Superfinanciera) y las de este
  proyecto puede no funcionar sin copiar datos a una ubicación común —
  hay que revisarlo apenas se confirme el acceso de lectura.
- **Acceso de lectura al proyecto del profesor**: sigue pendiente de
  que lo otorgue (ver seguimiento por correo aparte). Una vez
  concedido, **no** hace falta copiar sus tablas a este proyecto: se
  pueden consultar directamente con su `proyecto.dataset.tabla`
  completo en cualquier `JOIN`, siempre que las ubicaciones coincidan
  (punto anterior).
- **Tablas de `analitica`**: todavía no existen. Se crearán cuando el
  equipo defina el cruce municipal entre el índice de deforestación
  (`staging`) y las variables financieras del Observatorio.

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
Sandbox las tablas nuevas expiran a los 60 días de inactividad por
defecto; si se necesita que una tabla de `staging`/`analitica` no
expire, hay que activar facturación (lo cual también habilita el
bucket, sección 3.6) o volver a correr `subir-bigquery` antes de que se
cumplan los 60 días.
