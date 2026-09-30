# 0013 — Sin correo, no se exige verificar el email

- **Fecha:** 2026-09-30
- **Estado:** aceptada

## Contexto

Las funciones con coste (subir documentos desde F13, la IA desde F15) dependen de `require_verified_email` (A38, RF-06): sin el email verificado responden 403 `email_not_verified`. La dependencia existe desde F11, pero ninguna ruta la usaba hasta ahora. La subida de documentos de F13 es la primera.

El correo es opcional (RNF-34): sin `SMTP_HOST` la aplicación arranca y no envía nada. En una instalación así **nadie puede verificar su email**, porque el enlace de verificación nunca llega. La interfaz ya lo tiene en cuenta desde F11: oculta el aviso de verificación y la tarjeta **Email** dice que la instalación no envía emails. Y los avisos de F12, que también exigen la verificación, ni siquiera se programan sin SMTP.

Con la dependencia tal cual, una instalación sin correo tendría la subida de documentos (y la IA) bloqueada para siempre, sin nada que el usuario pudiera hacer.

## Decisión

Sin correo configurado (`settings.email_enabled` falso), `require_verified_email` deja pasar como si el email estuviera verificado. Con correo, todo sigue igual: el claim del token y, ante un "no", otra consulta al core (T12).

La comprobación vive en la propia dependencia, no en cada endpoint: las funciones con coste la declaran igual en los dos casos.

## Alternativas descartadas

- **Exigirla siempre.** Es lo más estricto, pero convierte el SMTP en obligatorio para subir un documento, contra RNF-34, y el mensaje de error pediría algo imposible.
- **Marcar como verificados a todos los usuarios al registrarse cuando no hay correo.** Deja un dato falso en SuperTokens que sobreviviría a configurar el SMTP más tarde: esas cuentas quedarían verificadas sin haber demostrado nunca que el email es suyo.
- **Decidirlo por endpoint.** Cada función con coste repetiría la misma condición, y bastaría olvidarla en una para romper la regla.

## Consecuencias

- Una instalación sin correo no tiene la protección de la verificación: quien se registre con un email ajeno puede subir documentos. Es coherente con lo que ya pasa en ella (tampoco hay recuperación de contraseña), y los límites de almacenamiento y el rate limit de la subida siguen protegiendo el disco.
- Si más tarde se configura el SMTP, la verificación se exige desde ese momento también a las cuentas antiguas, que verán el aviso y podrán verificar.
- La prueba `test_without_email_verification_is_not_required` lo fija. Las demás pruebas de la verificación simulan una instalación con correo.
