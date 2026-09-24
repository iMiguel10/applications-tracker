---
title: Copias de seguridad y restauración
sidebar_label: Copias de seguridad
---

Una copia completa son **tres** piezas:

1. La base de datos de la aplicación (`db`).
2. La base de datos de SuperTokens (`supertokens-db`): cuentas y contraseñas.
3. Los ficheros del volumen `files_data`.

Valkey no necesita copia: guarda la cola de tareas en espera, no datos.

:::warning El orden importa
Copia **primero las bases de datos y después los ficheros**. Así, un fichero subido entre los dos pasos, como mucho, queda en la copia sin que nada lo use: sobra, pero no rompe nada. En el orden contrario, podrías restaurar una base de datos que apunta a un fichero que no está en la copia.
:::

## Hacer la copia

Desde la carpeta del proyecto, con los contenedores en marcha:

```bash
mkdir -p backup

# 1. Base de datos de la aplicación
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backup/app.dump

# 2. Base de datos de SuperTokens
docker compose exec -T supertokens-db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backup/supertokens.dump

# 3. Ficheros, siempre después de las bases de datos
docker compose exec -T api tar -czf - -C /data/files . > backup/files.tar.gz
```

Para comprobar que la copia es válida, lista su contenido. Debe mostrar las tablas, sin errores:

```bash
docker compose exec -T db pg_restore --list < backup/app.dump | head
```

Guarda las copias **fuera del servidor**. Una copia en el mismo disco no te protege si el disco falla.

## Restaurar

:::danger
Restaurar **sustituye** los datos actuales por los de la copia.
:::

1. Para la API y el worker, para que nadie escriba mientras restauras:

    ```bash
    docker compose stop api worker
    ```

2. Restaura las dos bases de datos:

    ```bash
    docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < backup/app.dump
    docker compose exec -T supertokens-db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < backup/supertokens.dump
    ```

3. Restaura los ficheros:

    ```bash
    docker compose run --rm --no-deps -T --entrypoint sh api -c 'rm -rf /data/files/* && tar -xzf - -C /data/files' < backup/files.tar.gz
    ```

4. Arranca de nuevo:

    ```bash
    docker compose up -d
    ```

Si la copia era de una versión anterior de la aplicación, la API aplica al arrancar las migraciones que falten.
