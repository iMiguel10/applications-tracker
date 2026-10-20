---
title: Copias de seguridad y restauración
sidebar_label: Copias de seguridad
---

El servicio `backup` de `compose.prod.yml` hace las copias solo: **no hay que programar nada**. Esta página explica qué copia, cómo comprobar que funciona, cómo llevarlas fuera del servidor y cómo restaurarlas.

## Qué copia

Una copia completa son **tres** piezas, en este orden:

1. La base de datos de la aplicación (`db`): `app.dump`.
2. La base de datos de SuperTokens (`supertokens-db`): `supertokens.dump`, con las cuentas y las contraseñas.
3. Los ficheros del volumen `files_data`: `files.tar.gz`.

Más un `SHA256SUMS` para comprobar al restaurar que nada se ha corrompido. Valkey no se copia: guarda la cola de tareas en espera, no datos.

El orden importa: los ficheros van **después** de las bases de datos, así que todo documento de la copia tiene su fichero (como mucho sobra alguno, y el `worker` borra cada día los que no usa ningún documento). Y SuperTokens va después de la aplicación para que una cuenta creada entre los dos volcados no deje una fila de la aplicación sin cuenta.

## Cuándo y dónde

- **Cuándo:** cada noche a las 3:00, en la zona horaria de `TZ` (`Europe/Madrid` por defecto). Se cambia con `BACKUP_SCHEDULE`, en formato cron (`0 3 * * *`). El reloj del servidor puede estar en UTC: no te sorprendas si en los registros del servidor la hora es otra.
- **Dónde:** en una carpeta **del servidor**, `BACKUP_HOST_DIR` (`/var/backups/applications-tracker` por defecto), con una subcarpeta por copia: `2026-10-19_030000/`. Es una carpeta, no un volumen de Docker, para que puedas verla, llevártela a un NAS o a un disco,.
- **Cuántas:** las `BACKUP_KEEP_DAILY` más recientes (7) y, además, la última de cada una de las `BACKUP_KEEP_WEEKLY` semanas anteriores (4). Las demás se borran. Una semana que ya tiene copias diarias no gasta un hueco semanal.

## Comprobar que se hacen

La primera copia es de esta noche; para no esperar, haz una ahora (también se puede en cualquier momento):

```bash
docker exec <contenedor-backup> backup                            # Coolify, por SSH
docker compose -f compose.prod.yml exec backup backup             # sin Coolify
```

(En Coolify también vale la terminal del servicio `backup`, ejecutando `backup`.) **Qué debe verse:** líneas que acaban en `copia 2026-10-19_153012 terminada`, y en el servidor:

```bash
ls /var/backups/applications-tracker
# 2026-10-19_153012
ls /var/backups/applications-tracker/2026-10-19_153012
# app.dump  files.tar.gz  SHA256SUMS  supertokens.dump
```

**Si una copia falla, se ve:** el servicio `backup` pasa a *unhealthy* si la última copia falló o si la última correcta tiene más de `BACKUP_MAX_AGE_HOURS` horas (26). Coolify lo muestra en el recurso. El motivo está en los logs del servicio `backup`. Tras un despliegue nuevo, el contador empieza desde cero: no sale enfermo por una copia antigua.

## Fuera del servidor

Una copia en el mismo disco no te protege si el disco falla. Con `BACKUP_RCLONE_REMOTE`, cada copia nueva se envía a otro sitio con [rclone](https://rclone.org), que habla con S3 y compatibles, SFTP, SMB y muchos más. El valor es una cadena de conexión de rclone con el destino:

```text
# S3 o compatible (aquí, Cloudflare R2)
BACKUP_RCLONE_REMOTE=:s3,provider=Cloudflare,access_key_id=<id>,secret_access_key=<secreto>,endpoint=https://<cuenta>.r2.cloudflarestorage.com:bucket/applications-tracker

# SFTP (un NAS u otro servidor)
BACKUP_RCLONE_REMOTE=:sftp,host=nas.local,user=backup,pass=<contraseña ofuscada>:/volume1/backups/applications-tracker
```

Las contraseñas de SFTP o SMB van **ofuscadas** con `rclone obscure <contraseña>` (no cifra: solo evita que se lea a simple vista). Vacía, no se envía nada.

- **Nunca se borra nada allí.** La aplicación solo copia (`rclone copy`, no `sync`): si alguien borra las copias del servidor, las de fuera siguen. Por eso la retención de allí la pones tú, con las reglas del propio almacén (por ejemplo, el ciclo de vida de un bucket).
- Si el envío falla, la copia falla (aunque la local sí esté) y el servicio sale *unhealthy*.
- Las claves del almacén van en una variable de entorno: trátala como un secreto.

### Cifrar las copias de fuera

Las copias llevan **todos los datos de tus usuarios** en claro. Si salen del servidor a un almacén que no controlas del todo (un S3, un NAS compartido), **cífralas**: como [responsable](obligaciones.md), es lo que se espera de ti, y si alguien accede a ese almacén no podrá leerlas. rclone cifra con un destino `crypt` que envuelve al de siempre: cifra el contenido y los nombres de los ficheros antes de enviarlos.

1. **Genera dos contraseñas** largas y aleatorias (la segunda es la *sal*) y guárdalas en tu gestor de contraseñas: **sin ellas, las copias de fuera no se pueden recuperar**.
2. **Ofúscalas** para la variable, con la imagen del servicio `backup` (lleva rclone):

    ```bash
    docker exec <contenedor-backup> rclone obscure '<contraseña>'
    docker exec <contenedor-backup> rclone obscure '<sal>'
    ```

3. **Envuelve el destino** en `BACKUP_RCLONE_REMOTE`: el de antes va entre comillas simples en `remote`, y `password` y `password2` llevan las dos ofuscadas:

    ```text
    # S3 o compatible, cifrado
    BACKUP_RCLONE_REMOTE=:crypt,remote=':s3,provider=Cloudflare,access_key_id=<id>,secret_access_key=<secreto>,endpoint=https://<cuenta>.r2.cloudflarestorage.com:bucket/applications-tracker',password=<contraseña ofuscada>,password2=<sal ofuscada>:

    # SFTP, cifrado
    BACKUP_RCLONE_REMOTE=:crypt,remote=':sftp,host=nas.local,user=backup,pass=<contraseña ofuscada>:/volume1/backups/applications-tracker',password=<contraseña ofuscada>,password2=<sal ofuscada>:
    ```

4. **Vuelve a desplegar** y lanza una copia (`docker exec <contenedor-backup> backup`).

**Qué debe verse:** en el almacén, la carpeta de cada copia y sus ficheros tienen nombres ilegibles (`le237ndr70jg…`) y su contenido no se puede abrir; la copia local del servidor sigue en claro. Cómo traerla de vuelta, en [Restaurar](#restaurar).

`rclone obscure` no cifra (cualquiera con rclone deshace la ofuscación): lo que protege las copias es que la variable, y las contraseñas, solo estén en el servidor y en tu gestor de contraseñas.

#### Que las puedas recuperar sin el servidor

Las copias de fuera son para cuando pierdes el servidor, y con él se pierde la variable: Coolify la guarda en su propia base de datos, en ese mismo servidor. Si las contraseñas solo estaban ahí, **las copias cifradas no se pueden recuperar**; rclone no tiene ninguna puerta trasera.

- **Guarda en tu gestor de contraseñas** las dos contraseñas en claro y el valor entero de `BACKUP_RCLONE_REMOTE` (lleva también las claves del almacén). Si solo tienes las ofuscadas, `docker exec <contenedor-backup> rclone reveal '<valor ofuscado>'` devuelve cada una en claro mientras tengas el servidor.
- **Pruébalo una vez desde otra máquina**, con rclone y solo lo que hay en el gestor: `rclone copy "<valor de BACKUP_RCLONE_REMOTE>/<copia>" ./prueba` y, dentro de la carpeta, `sha256sum -c SHA256SUMS`. Si todo da `OK`, no dependes del servidor para recuperarlas.

#### Las copias del servidor van en claro

Solo se cifra lo que sale con `BACKUP_RCLONE_REMOTE`. Las copias de `/var/backups/applications-tracker` van **en claro a propósito**: están en el mismo disco que las bases de datos en uso, que tampoco van cifradas, así que quien pueda leer esa carpeta ya puede leer los datos; y cifrarlas haría más lenta y delicada la restauración, que es para lo que están.

- **Si el servidor está en un sitio al que otros tienen acceso físico** (en casa, en una oficina), lo que protege los datos y las copias a la vez es **cifrar el disco entero** (LUKS en Linux), normalmente al instalar el sistema.
- **No saques las copias a mano tal cual** a un NAS o un disco externo: saldrían en claro. Configura ese destino como `BACKUP_RCLONE_REMOTE` con `crypt` y cada copia nueva sale cifrada sola.

## Secretos que hay que guardar aparte

Las copias **no incluyen**, a propósito, estos valores. Guárdalos en un gestor de contraseñas, **fuera del servidor y de las copias**:

| Secreto | Si lo pierdes |
|---|---|
| `AI_KEYS_ENCRYPTION_KEYS` | Las claves de IA que guardaron los usuarios son ilegibles: tendrán que volver a introducirlas |
| `APP_SECRET` | Los enlaces de baja de los emails ya enviados dejan de valer |
| `POSTGRES_PASSWORD`, `SUPERTOKENS_DB_PASSWORD`, `SUPERTOKENS_API_KEY` | Sin ellas no puedes reconstruir la instalación con las mismas bases de datos |
| `BACKUP_RCLONE_REMOTE` (sus claves) | No puedes recuperar las copias de fuera |
| Las dos contraseñas del cifrado (`crypt`), en claro | Las copias de fuera cifradas **no se pueden descifrar**: nadie, tampoco tú |

## Restaurar

:::danger
Restaurar **sustituye** las dos bases de datos y los ficheros actuales por los de la copia.
:::

La restauración exige que **nadie esté escribiendo**: tienen que estar parados `api`, `worker` y `supertokens`. Si queda alguna conexión a las bases de datos, `restore` se niega a empezar y no toca nada. Tampoco toca nada si la copia está dañada (los `SHA256SUMS` no coinciden).

1. **Elige la copia.** Mira las que hay en la carpeta del servidor (`ls /var/backups/applications-tracker`). Una copia traída de fuera (NAS, S3) se deja antes en esa carpeta, con su carpeta de fecha. Si está fuera (también si está cifrada), tráela con el propio servicio `backup`, que la descifra con `BACKUP_RCLONE_REMOTE`:

    ```bash
    docker exec <contenedor-backup> sh -c 'rclone copy "$BACKUP_RCLONE_REMOTE/2026-10-19_030000" /backups/2026-10-19_030000'
    ```

    `restore` comprueba después los `SHA256SUMS`: si el descifrado o la descarga hubieran fallado, no toca nada.

2. **Para `api`, `worker` y `supertokens`.** Con Coolify, por SSH (el nombre de los contenedores, con `docker ps`):

    ```bash
    docker stop <contenedor-worker> <contenedor-api> <contenedor-supertokens>
    ```

    Sin Coolify:

    ```bash
    docker compose -f compose.prod.yml stop worker api supertokens
    ```

3. **Restaura.**

    ```bash
    docker exec <contenedor-backup> restore 2026-10-19_030000 --yes            # Coolify
    docker compose -f compose.prod.yml run --rm backup restore 2026-10-19_030000 --yes   # sin Coolify
    ```

    **Qué debe verse:** la comprobación de `SHA256SUMS`, la restauración de cada base de datos y de los ficheros, y una última línea `copia … restaurada: arranca de nuevo el stack`. Sin `--yes`, se niega y te recuerda qué sustituiría.

4. **Arranca de nuevo**, en este orden:

    ```bash
    docker start <contenedor-supertokens> <contenedor-api> <contenedor-worker>
    ```

    (sin Coolify, `docker compose -f compose.prod.yml up -d`). Si la copia era de una versión anterior de la aplicación, `api` aplica al arrancar las migraciones que falten.

5. **Comprueba** que `https://tracker.example.com/api/v1/health` responde `ok` y que puedes iniciar sesión.

Las contraseñas y las claves tienen que ser las mismas con las que se hizo la copia (las de [arriba](#secretos-que-hay-que-guardar-aparte)): si restauras en una instalación nueva, ponlas antes de desplegar.
