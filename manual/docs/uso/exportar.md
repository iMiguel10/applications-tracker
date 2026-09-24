---
title: Exportar tus solicitudes
sidebar_label: Exportar a CSV
---

En **Solicitudes**, pulsa **Exportar CSV**. Se descarga un fichero con **todas** tus solicitudes, archivadas incluidas, sin importar los filtros que tengas puestos.

Cada fila es una solicitud, con estas columnas:

`position_title`, `company`, `status`, `applied_at`, `work_mode`, `source`, `origin`, `location`, `job_url`, `salary_min`, `salary_max`, `salary_currency`, `notes`, `archived_at`, `created_at`, `updated_at`

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

El CSV no incluye el historial de estados, las entrevistas ni los recordatorios.
