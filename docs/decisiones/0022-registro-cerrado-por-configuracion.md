# 0022 — Registro cerrado por configuración y cuentas creadas con un script

- **Fecha:** 2026-10-17
- **Estado:** aceptada

## Contexto

La especificación da por hecho un **registro abierto** (RF-01): cualquiera puede crearse una cuenta, y por eso la v2 se diseñó con límites, rate limiting, verificación de email y una cuota de IA que no se renueva. Pensando en la puesta en producción (F7), el usuario propuso poder **cerrar el registro con una variable de entorno**: una instalación personal, o para unos pocos conocidos, no necesita que cualquiera se dé de alta, y cerrarlo evita de raíz el abuso de la IA y del almacenamiento con cuentas falsas.

## Decisión

- **`SIGNUP_ENABLED`**, activada por defecto (el comportamiento de siempre). Con `false`:
  - El backend rechaza el registro: la operación responde `GENERAL_ERROR` con el mensaje `signup_disabled`, sin crear nada ni encolar el email de verificación. Va en el override de `sign_up_post` (`core/auth_emails.py`), no en un middleware por la ruta, porque SuperTokens atiende la misma operación en varias URL (`/auth/signup`, `/auth/signup/`, `/auth/public/signup`), como se vio con el rate limit en F11.
  - Las cuentas que ya existen siguen igual: inicio de sesión, recuperación de contraseña y todo lo demás.
  - `GET /meta` publica `signup_enabled`. El frontend oculta «¿No tienes cuenta? Crear cuenta» en el login y, en `/register`, explica que el registro está cerrado en lugar del formulario.
- **Las cuentas las crea quien administra con un script**, decisión del usuario: `python -m app.scripts.create_user <email> [--language es|en]` (`AccountProvisioningService`). Funciona también con el registro abierto.
  - La cuenta nace con una **contraseña aleatoria que nadie ve** y con el **email ya verificado**: lo da por bueno quien la crea.
  - La persona elige su contraseña con el **enlace de recuperación**. Si hay SMTP, le llega un email propio, «Tu cuenta de Applications Tracker está creada» (`templates/email/account_created/`), no el de recuperar la contraseña, que diría que alguien la pidió. Sin SMTP, o si el envío falla, el script imprime el enlace para pasárselo a mano. Caduca en 60 minutos, como el de recuperación.
  - Si el email ya existe, el script termina con 1 sin tocar nada.

## Alternativas descartadas

- **Un 403 en `/auth/signup`** (lo que se propuso al principio): exigía un middleware por la ruta, saltable por las otras URL, o salirse de las respuestas de SuperTokens. `GENERAL_ERROR` es la respuesta del propio SDK para un rechazo de la operación, y el frontend ya la recibe por el mismo camino.
- **Desactivar la ruta en el SDK** (`disable_sign_up_post`): respondería 404, sin explicar nada a un cliente de la API.
- **Invitaciones desde la aplicación:** un enlace o un código que la persona canjea al registrarse. Necesita una tabla, un rol de administración con interfaz (fuera de alcance desde el MVP) y más pantallas. El script cubre una instalación pequeña.
- **Que el script pida o imprima una contraseña:** quien administra la conocería, y viajaría por un canal que no es el de la propia persona.

## Consecuencias

- Con el registro cerrado, RF-01 deja de aplicarse en esa instalación. Las protecciones contra el registro abierto (verificación, límites, rate limiting) siguen activas y no estorban.
- Sin SMTP, una cuenta creada con el script depende de que quien administra le pase el enlace antes de que caduque. Si caduca, sin correo no hay «¿Olvidaste tu contraseña?»: se borra la cuenta y se vuelve a crear.
- Cambiar `SIGNUP_ENABLED` exige recrear `api` (`--force-recreate`), como cualquier variable del `.env`.
