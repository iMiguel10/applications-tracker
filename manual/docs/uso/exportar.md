---
title: Exportar tus datos
sidebar_label: Exportar
---

Hay dos exportaciones: **todos tus datos**, para llevártelos o guardarlos, y tus **solicitudes en CSV**, para trabajar con ellas en una hoja de cálculo.

## Descargar todos tus datos

En **Preferencias**, en la tarjeta **Tus datos**, pulsa **Descargar todos mis datos**. Mientras se prepara, el botón dice **Preparando la descarga…**; después se descarga `applications-tracker-export-<fecha>.zip`.

El `.zip` lleva todo lo que tienes en la aplicación:

- `account.json`: tu email, tus preferencias (idioma, zona horaria, avisos) y la fecha de alta.
- Un fichero JSON por tipo de dato: empresas, solicitudes, historial de estados, entrevistas, recordatorios, documentos, tu perfil (experiencia, formación, proyectos, certificaciones, logros, habilidades e idiomas), propuestas de IA y consentimientos. Cada fichero lleva el nombre de su tipo en inglés (`applications.json`, `interviews.json`…).
- `documents/`: todos tus PDF, subidos y generados.
- `README.txt`: qué es cada fichero, en español y en inglés.

Los datos van con sus códigos y sus ids, como en el CSV: cada entrevista dice a qué solicitud pertenece con `application_id`, y las fechas van en ISO 8601, en UTC. Es un formato pensado para que lo lea otro programa.

**Nunca incluye tus claves de IA**, ni siquiera cifradas: solo qué proveedor y modelo usabas.

Puedes descargarlo **5 veces por hora**. Si la descarga se corta, vuelve a pulsar el botón.

:::tip Si ya no puedes entrar
Pide tus datos a quien administra la instalación: puede generar el mismo `.zip` sin tu contraseña.
:::

## Exportar tus solicitudes a CSV

En **Solicitudes**, pulsa **Exportar CSV**. Se descarga un fichero con **todas** tus solicitudes, archivadas incluidas, sin importar los filtros que tengas puestos.

Cada fila es una solicitud, con estas columnas:

`position_title`, `company`, `status`, `applied_at`, `work_mode`, `source`, `origin`, `location`, `job_url`, `salary_min`, `salary_max`, `salary_currency`, `notes`, `job_description`, `cv_document`, `cover_letter_document`, `archived_at`, `created_at`, `updated_at`

`cv_document` y `cover_letter_document` llevan el **nombre** del CV y de la carta enviados; los PDF no van en el CSV.

Los estados, modalidades y fuentes van con su **código**, no con la etiqueta de la pantalla: `applied` en lugar de "Enviada", `remote` en lugar de "Remoto". Así el fichero es el mismo sea cual sea el idioma de la interfaz y se puede procesar con cualquier herramienta.

| Código | Estado |
|---|---|
| `saved` | Guardada |
| `applied` | Enviada |
| `screening` | En revisión |
| `interviewing` | Entrevistas |
| `offer` | Oferta |
| `accepted` | Aceptada |
| `rejected` | Descartada |
| `withdrawn` | Retirada |

El CSV no incluye el historial de estados, las entrevistas ni los recordatorios: para eso, [descarga todos tus datos](#descargar-todos-tus-datos).
