# 0008 — El borrado de cuenta entra en el alcance, en F8

- **Fecha:** 2026-09-24
- **Estado:** aceptada

## Contexto

La [especificación](../producto/especificacion.md#0-contexto-del-proyecto) marcaba el borrado de cuenta como pospuesto `[C]` ("borrado de cuenta con retención"), con la costura ya puesta desde el diseño inicial: todo cuelga de `user_id` con `ON DELETE CASCADE` (RNF-40, arquitectura §4). El usuario pidió explícitamente construirlo dentro de F8 (revisión final), antes de F7.

## Decisión

Se construye el borrado de cuenta como **borrado inmediato y completo**, no como el "borrado con retención" que describía el alcance pospuesto: `DELETE /api/v1/me` (204), dentro del router protegido. `UserService.delete_account()` borra primero la fila propia en `users` con `UserRepository.delete()` (todo lo demás — empresas, solicitudes, historial, entrevistas, recordatorios — cae por `ON DELETE CASCADE`), confirma esa transacción, y solo entonces borra la identidad en SuperTokens con `IdentityRepository.delete()` (credenciales y sesiones en el core). Es el orden que ya fijaba arquitectura §4: primero los datos propios y después el usuario de SuperTokens, porque al revés quedarían datos huérfanos imposibles de reclamar.

En el frontend, `/preferences` gana una tarjeta "Eliminar cuenta" que exige escribir el email de la cuenta para confirmar. `useDeleteAccount` borra, cierra sesión (ignorando su fallo), vacía la caché de TanStack Query y navega a `/login` — el mismo patrón que T8 (`useSignOut`).

## Alternativas descartadas

- **Esperar a un periodo de gracia** (marcar la cuenta como "pendiente de purgar" y borrarla de verdad días después): es lo que describía el alcance pospuesto original, y sigue pospuesto `[C]`. No se construye ahora porque el usuario pidió el borrado tal cual, sin ese matiz, y añadirlo habría exigido un estado nuevo, un job en segundo plano y una forma de deshacer el borrado — nada de lo que pide RNF-40 en su forma mínima.
- **Borrar primero en SuperTokens y después los datos propios**: si el borrado de los datos propios fallase a mitad, quedarían filas huérfanas de un usuario que ya no puede volver a entrar para reclamarlas ni reintentar el borrado. Con el orden elegido, un fallo a mitad deja una identidad viva sin datos propios, que puede reintentarlo.

## Consecuencias

- RNF-40 pasa de `[C]` a implementado; solo queda pospuesto el periodo de gracia (retención antes de purgar), no el borrado en sí.
- Un access token ya emitido antes del borrado sigue validándose sin consultar al core hasta que caduca (máximo 5 minutos, [decisión 0002](0002-access-token-de-5-minutos.md)): si llegase una petición con él, `get_current_user` recrearía una fila vacía en `users` para un `supertokens_user_id` que ya no existe. Es inofensivo, pero real; documentado en [autenticacion.md](../arquitectura/autenticacion.md#3-backend). El frontend cierra la sesión del navegador justo después de borrar, en la misma mutación, para no dejar abierta esa ventana más de lo necesario.
- `docs/producto/especificacion.md` y `docs/arquitectura/index.md` se actualizan para reflejar el borrado como implementado, no como costura pendiente.
