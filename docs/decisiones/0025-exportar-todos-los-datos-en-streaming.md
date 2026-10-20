# 0025 — Exportar todos los datos de una cuenta, en streaming

- **Fecha:** 2026-10-20
- **Estado:** aceptada (issue [#4](https://github.com/iMiguel10/applications-tracker/issues/4))

## Contexto

La única exportación era el CSV de solicitudes (RF-70). El RGPD da a cada persona derecho a una copia de sus datos (art. 15) y a recibir los que aportó en un formato estructurado y legible por máquina (art. 20, portabilidad), y el responsable tiene un mes para responder (art. 12.3). El responsable es quien despliega la instalación. La ley no exige un botón, pero sin herramienta, cumplir era sacar los datos a mano de dos bases de datos y del disco.

## Decisión

Decisiones del usuario:

- **Dos entradas al mismo `.zip`:** el botón **Descargar todos mis datos** de Preferencias (`GET /me/export`) y el script `export_user` para quien administra la instalación, cuando se lo piden por otra vía.
- **Generado en streaming,** mientras se descarga: `AccountExportService` lee la base de datos de una vez, la suelta (commit) y arma el `.zip` con `zipfile` sobre un destino sin `seek`, de modo que cada entrada lleva su descriptor de datos al final y el fichero sale a medida que se escribe. Los PDF se copian del almacén por trozos.
- **Contenido:** un JSON por tabla con todas sus columnas, salvo las que se omiten a propósito; los PDF en `documents/`; un `README.txt` bilingüe; `format_version: 1`. **Nunca** las claves de IA (ni cifradas ni sus últimos caracteres), ni ids de SuperTokens, ni rutas del almacén. No van el registro de avisos enviados (lo hizo el sistema, no lo aportó la persona) ni los límites que fija quien administra.
- **Rate limit propio:** 5 exportaciones por hora y usuario.

## Alternativas descartadas

- **Generarlo en el `worker`, guardarlo y enviar un enlace que caduca** (lo que proponía la issue como primera opción): tabla nueva, trabajo, barrido de limpieza, aviso y una pantalla de espera. Solo compensa con exportaciones de gigas. Aquí el tamaño está acotado por el límite de almacenamiento de la cuenta (100 MB por defecto, sin "sin límite"), los JSON pesan poco y la memoria del servidor no crece con el tamaño.
- **Schemas de exportación escritos a mano por tabla:** una columna nueva se quedaría fuera sin que nadie lo notara. Se exportan todas las columnas salvo una lista de omitidas, y una prueba exige que cada tabla del modelo esté exportada o excluida con su motivo, y que toda columna binaria esté omitida.
- **Solo el script:** cumple, pero obliga a la persona a pedirlo y esperar, y a quien administra a hacer algo cada vez.
- **Ampliar el CSV:** un CSV no representa bien datos anidados (historial, logros del perfil) ni lleva ficheros.

## Consecuencias

- Una tabla nueva con datos de la cuenta obliga a decidir en `domain/account_export.py` si se exporta (`EXPORTED_TABLES`, con sus columnas omitidas) o no (`EXCLUDED_TABLES`, con el motivo); si no, falla `tests/domain/test_account_export.py`. Una columna nueva sale sola.
- Si una descarga se corta, el `.zip` queda incompleto y hay que pedirlo otra vez; no hay reanudación.
- Un PDF borrado entre la lectura de la BD y su copia se omite y lo dice el `README.txt`.
- Las lecturas no van en una transacción `REPEATABLE READ`: un cambio simultáneo de la propia persona podría verse a medias entre dos ficheros. Se acepta: es su exportación y la puede repetir.
