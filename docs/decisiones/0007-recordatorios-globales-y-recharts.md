# 0007 — F5 cierra el alcance de recordatorios y añade `recharts`

- **Fecha:** 2026-09-23
- **Estado:** aceptada

## Contexto

La decisión [0005](0005-recordatorios-sin-pagina-global-en-f4.md) dejó pendiente para F5 la página global de recordatorios (`/reminders`) y, con ella, la posibilidad de crear un recordatorio sin partir del detalle de una solicitud (RF-50). El dashboard de F5 (RF-60…66) necesita además dibujar un desglose de solicitudes por estado y una serie de envíos por semana.

## Decisión

`ReminderFormDialog` pasa de exigir siempre un `applicationId` fijo a aceptarlo como opcional: si se omite (el caso del listado global en `/reminders`), el formulario ofrece un `FormAsyncCombobox` para buscar y ligar una solicitud, o dejar el recordatorio sin ligar. `reminderSchema` gana el campo `application_id` (`""` = sin solicitud, se convierte a `null` al enviar).

Para los gráficos del dashboard (`StatusBreakdownCard`, `WeeklyApplicationsChart`) se añade `recharts` como dependencia nueva del frontend.

## Alternativas descartadas

No aplica: ambos cambios ejecutan lo que ya anticipaban la especificación (RF-50, RF-60, RF-61) y la decisión 0005, sin alternativas que evaluar.

## Consecuencias

- Cierra el punto que la decisión 0005 dejó explícitamente pendiente para F5.
- `recharts` es la primera dependencia de gráficos del proyecto; un gráfico futuro debería reutilizarla en vez de introducir una segunda biblioteca.
