# 0024 — Cambiar la contraseña con la actual

- **Fecha:** 2026-10-20
- **Estado:** aceptada (issue [#2](https://github.com/iMiguel10/applications-tracker/issues/2))

## Contexto

Al construir F11 se decidió que, con sesión iniciada, la contraseña se cambiara **solo** con el enlace de recuperación enviado al correo de la cuenta (RF-03). El motivo era que cambiarla exigiera acceso al correo, no solo una sesión abierta (que podría ser robada), sin una segunda vía que mantener.

Con F7 apareció el caso que esa decisión no cubría: una instalación **sin correo** (RNF-34), como la de producción del usuario. Ahí la tarjeta **Contraseña** solo decía que se pidiera ayuda a quien administra. Nadie podía cambiar su contraseña desde la aplicación, ni siquiera la elegida con el enlace de `create_user` (0022).

## Decisión

Decisión del usuario:

- **La contraseña se cambia con la actual y la nueva**, en `POST /api/v1/me/password`, con o sin correo. Pedir la actual cumple el mismo papel que pedía el correo: alguien con una sesión abierta ajena no puede cambiarla sin conocerla.
- La política de contraseñas la aplica SuperTokens (`update_email_or_password` con `apply_password_policy`). Sigue viviendo solo en el backend (invariante 7).
- Al cambiarla **se cierran las demás sesiones** de la cuenta y la de la petición sigue abierta, porque demostró conocer la anterior. La recuperación por email, en cambio, las cierra todas.
- **Rate limit propio:** 5 intentos cada 15 minutos por usuario, contando también los correctos. Sin él, una sesión abierta serviría para adivinar la contraseña actual.
- **Con correo:**
  - el enlace de recuperación sigue en la misma tarjeta, para quien haya olvidado la actual;
  - **llega un aviso** de que la contraseña cambió, con la hora en la zona de la cuenta. Si no fue la persona de la cuenta, se entera y la recupera desde su correo, que sigue siendo suyo. El aviso no lleva un enlace con token, sino a la página para pedirlo: llega sin haberlo pedido.

## Alternativas descartadas

- **Mantener solo el enlace:** deja sin forma de cambiar la contraseña a cualquier instalación sin correo.
- **Ofrecer el formulario solo cuando no hay correo:** dos caminos según la configuración para la misma tarea, y la persona que sí tiene correo tendría que salir a su bandeja para algo que puede hacer en un paso. El formulario con la actual es la práctica habitual (OWASP ASVS: cambiar la contraseña exige la actual).
- **Cerrar también la sesión actual,** como la recuperación: obliga a volver a entrar sin ganar nada. Quien la cambió ya demostró conocer la anterior.

## Consecuencias

- Hay dos formas de cambiar la contraseña con sesión iniciada. Las dos aplican la misma política y las dos cierran sesiones; solo difieren en si cierran también la actual.
- Las dos contraseñas llegan como `SecretStr` **sin restricciones** en el schema. Pydantic pone en cualquier error de validación la entrada original en claro (y, si falta un campo, el cuerpo entero), así que un 422 habría devuelto la contraseña. Lo que no vale lo rechaza el service con los códigos del endpoint (`wrong_current_password`, `password_policy`); ver la trampa en autenticación §8.
- Con correo, cada cambio envía un email, y el aviso es un trabajo más del `worker` (`send_password_changed_email`).
