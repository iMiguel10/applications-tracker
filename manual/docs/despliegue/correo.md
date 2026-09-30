---
title: Configurar el correo
sidebar_label: Correo
---

La aplicación envía el correo a través de un servidor **SMTP** que eliges tú: el de tu proveedor de correo o un servicio de envío (Brevo, Amazon SES, Mailgun, Gmail con contraseña de aplicación…). No depende de ninguno en concreto.

## Qué emails envía

| Email | Cuándo |
|---|---|
| Confirmar el email | Al crear la cuenta, y cuando el usuario pulsa **Reenviar enlace** |
| Recuperar o cambiar la contraseña | Lo pide el usuario desde el inicio de sesión o desde Preferencias |
| Avisos (recordatorio vencido, entrevista próxima, resumen semanal, solicitudes sin actividad) | Según las preferencias de cada usuario, solo a emails verificados. Los decide el `worker` con tareas programadas |

Salen en el idioma de la cuenta (o, si no lo ha fijado, en el que ve en pantalla), en español o en inglés.

- **Los envía el servicio `worker`**, no la API: si el `worker` está parado, los emails se quedan en cola y salen cuando arranca. En sus registros (`docker compose logs worker`) queda cada envío y cada fallo, con el id del usuario y sin la dirección.
- **Los enlaces de los emails usan `WEBSITE_DOMAIN`.** Si se queda con el valor de desarrollo (`http://localhost:5173`), los emails llegan bien, pero su enlace no lleva a ninguna parte. Ver [Variables](variables.md).
- **Los avisos los programa el `worker`.** Cada minuto, cada 5 minutos o cada hora, según el aviso, mira qué toca enviar. Si el `worker` estuvo parado, los avisos que vencieron hace más de 24 horas no se envían al volver (para no inundar la bandeja) y el resumen semanal de un lunes en que estuvo parado todo el día se pierde. Un aviso nunca sale dos veces por el mismo motivo, y si un envío falla sin saber si el servidor llegó a aceptarlo, no se repite.
- **Sin SMTP la aplicación funciona igual:** no ofrece recuperar ni cambiar la contraseña, lo dice en pantalla, y no pide confirmar el email. Tampoco se programa ningún aviso: la tarjeta **Avisos por email** de Preferencias dice que la instalación no envía emails.

## Variables

| Variable | Valor | Notas |
|---|---|---|
| `SMTP_HOST` | Servidor, por ejemplo `smtp-relay.brevo.com` | **Sin ella no se envía nada**, y la aplicación funciona igual |
| `SMTP_PORT` | Puerto | Normalmente `587` con `starttls` o `465` con `tls` |
| `SMTP_SECURITY` | `starttls`, `tls` o `none` | Ver la tabla de abajo |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | Credenciales del servidor | Vacías si el servidor no pide inicio de sesión |
| `EMAIL_FROM` | Remitente, por ejemplo `Applications Tracker <no-reply@tudominio.com>` | **Obligatoria si hay `SMTP_HOST`**: sin ella, la API no arranca |
| `SMTP_TIMEOUT_SECONDS` | Segundos de espera (30 por defecto) | Opcional |

| `SMTP_SECURITY` | Cuándo |
|---|---|
| `starttls` (por defecto) | Puerto 587: la conexión empieza sin cifrar y se cifra antes de enviar nada |
| `tls` | Puerto 465: cifrada desde el principio |
| `none` | Solo para un servidor de pruebas en la misma máquina. **Nunca con un servidor real**: la contraseña viajaría sin cifrar |

Con `starttls` o `tls`, si el servidor no ofrece cifrado, la aplicación **no envía** el email en claro: lo da por fallido.

## Comprobar que funciona

Con los contenedores en marcha:

```bash
docker compose exec api python -m app.scripts.send_test_email tu@email.com
```

| Lo que ves | Qué significa |
|---|---|
| `Aceptado por <servidor>:<puerto> (<cifrado>) para tu@email.com.` | El servidor aceptó el email. Mira tu bandeja, y también la de spam |
| `SMTP sin configurar: define SMTP_HOST y EMAIL_FROM.` | Falta la configuración, o el contenedor no se recreó tras cambiar el `.env` |
| `No se envió (es seguro reintentar): …` | El servidor no lo aceptó: dirección o puerto equivocados, credenciales rechazadas, cifrado no disponible… El mensaje dice el motivo |
| `Resultado desconocido, puede que haya salido: …` | La conexión se cortó mientras se enviaba. Comprueba la bandeja antes de repetir |

## Problemas habituales

- **El servidor no permite enviar SMTP.** Muchos proveedores de servidores bloquean por defecto el puerto 25, y algunos también el 465 y el 587, en cuentas nuevas. Si la prueba se queda esperando hasta el timeout, pide al proveedor que desbloquee el puerto o usa un servicio de envío que admita el 587 o el 2525.
- **El remitente no está autorizado.** Muchos servicios solo dejan enviar desde direcciones o dominios que hayas verificado con ellos. Si `EMAIL_FROM` no coincide, rechazan el email.
- **Los emails llegan a spam.** Configura **SPF**, **DKIM** y **DMARC** del dominio de `EMAIL_FROM` siguiendo las instrucciones de tu servicio de envío. Sin ellos, muchos servidores desconfían aunque todo funcione.
- **No aparece el botón de baja de Gmail u Outlook en los avisos.** Cada aviso lleva las cabeceras de baja con un clic (`List-Unsubscribe`), pero Gmail y Yahoo solo muestran el botón si el email va firmado con **DKIM**. El enlace de baja del pie del email funciona igual.
