# Límites, rate limiting y superficie pública

> Estado: **§1 y §2 construidos en F11** (límites de solicitudes, empresas y recordatorios; rate limiting de autenticación y límite general de la API); el resto, diseño (F12, F17) · Fecha: 2026-09-24 · Depende de la [especificación](../producto/especificacion.md) (RF-140…144, RNF-04, §10) y de la [arquitectura de la v2](v2.md) (A28–A30, A40)

Con registro abierto (v2), cualquiera puede crear una cuenta. Este documento reúne las tres defensas que eso exige: **cuánto** puede crear cada usuario (límites), **a qué ritmo** se puede llamar a la API (rate limiting) y **qué** responde sin sesión (superficie pública).

## 1. Límites por usuario

### Piezas

- `domain/limits.py`: un `StrEnum` `LimitKey` (`applications`, `companies`, `pending_reminders`, `documents`, `storage_bytes`, `ai_free_uses`) y, para cada uno, si **se renueva** (ninguno lo hace en la v2) y en qué unidad se muestra.
- Valores globales en la configuración (`LIMIT_*`, §10 de la especificación).
- Tabla `user_limit_overrides` para las excepciones de un usuario concreto (RF-143), que se ajustan con `scripts/set_user_limit.py`.
- `LimitService`: `limit_for(user, key)` (excepción o global), `usage_for(user, key)` (una consulta por límite sobre las tablas reales, sin contadores aparte) y `check(user, key, amount)`.

### Dónde se comprueba

| Límite | Cómo | Por qué así |
|---|---|---|
| Solicitudes, empresas, recordatorios (en cualquier estado, [0011](../decisiones/0011-limite-de-recordatorios-en-todos-los-estados.md)) | Contar e insertar en la misma transacción, **sin** bloqueo (como en la v1) | Pasarse en uno por una carrera no cuesta nada |
| Documentos y almacenamiento | Con la fila del usuario bloqueada (A30) | Disco |
| Usos gratuitos de IA | Con la fila del usuario bloqueada, contando lo que está en curso ([IA §6](ia.md#6-elegir-la-clave-y-contar-el-consumo)) | Dinero |

### Qué ve el usuario (RF-141, RF-142, RF-144)

- `GET /me/usage` devuelve, por cada límite, `used`, `limit`, `remaining` y si se renueva. El frontend calcula ahí mismo el aviso del 80 %.
- Al superar un límite, el error lleva el código de siempre (`<recurso>_limit_reached`) **y** los números: `{"detail", "code", "limit", "used"}`. `AppException` gana un campo `extra` opcional para datos como estos, que el handler añade a la respuesta.

**Construido en F11:** `domain/limits.py` (`LimitKey`, `LIMIT_RULES` con el código de error de cada límite y si se renueva, `WARNING_RATIO`), los `LIMIT_*` en `core/config.py`, la tabla `user_limit_overrides` (clave primaria `user_id` + `limit_key`, `ON DELETE CASCADE`), `LimitService` (`check`, `usage`, `set_override`, `clear_override`), `GET /me/usage` con `warning_ratio` y `scripts/set_user_limit.py`. Los services de solicitudes, empresas y recordatorios llaman a `LimitService.check` en lugar de comparar con una constante. Documentos, almacenamiento e IA se añadirán a `LimitKey` en F13 y F15.

- **"Sin límite" por cuenta, solo donde no cuesta nada.** Una excepción con `value` nulo deja a la cuenta sin tope en ese límite (`set_user_limit … --unlimited`, o `all --unlimited`); `GET /me/usage` responde `limit` y `remaining` a `null` y la interfaz muestra "sin límite", sin barra ni avisos. **Decisión del usuario en F11: los límites que protegen un recurso con coste (almacenamiento, IA) tienen tope siempre.** Cada `LimitRule` declara `allows_unlimited` (falso por defecto, así que un límite nuevo nace protegido) y la BD lo impone además con el CHECK `unlimited_only_where_allowed`, que lista las claves permitidas. Una prueba compara esa lista con la del dominio.
- **Los códigos de error no cambian.** `LimitKey.REMINDERS` responde `reminders_limit_reached`, el código del MVP: el código es contrato de la API. Lo que cambió al construirlo es qué cuenta: todos los estados, no solo los pendientes ([0011](../decisiones/0011-limite-de-recordatorios-en-todos-los-estados.md)).
- **En la interfaz:** la tarjeta **Uso de la cuenta** de Preferencias (el usuario la prefirió a una página propia mientras solo haya tres límites; se moverá a una página cuando lleguen almacenamiento e IA) y `LimitWarning` en los formularios de creación, que no pinta nada por debajo del 80 %. Los mensajes de error interpolan `limit` y `used`: `ApiError` guarda los campos extra de la respuesta y `errorMessageParams` los pasa a la traducción.

> **Trampa — contadores que se desincronizan.** Guardar "usos consumidos" en una columna que se incrementa es más rápido de leer, pero cualquier camino que borre o cree sin pasar por el incremento (un borrado en cascada, un script, un fallo a mitad) la deja mal para siempre. El consumo se **calcula** sobre las tablas reales (`COUNT`, `SUM(size_bytes)`), que con los índices por `user_id` es barato. La única excepción que se paga en rendimiento, la cuota de IA, también se calcula desde `ai_proposals`.

## 2. Rate limiting (RNF-04)

### Piezas

- `infra/rate_limit.py`: la librería `limits` con almacenamiento en Valkey, estrategia de **ventana deslizante** (evita que alguien concentre el doble de peticiones en el cambio de ventana).
- En nuestros endpoints: la dependencia `rate_limit(nombre, por=…)`, declarada igual que `get_current_user`.
- En `/auth/*` (lo sirve SuperTokens, no nuestros endpoints): un **middleware** añadido de forma que quede **por fuera** del de SuperTokens y lo alcance primero.

**Construido en F11:**

- `infra/rate_limit/`: `RateLimiter` con `LimitsRateLimiter` (`limits[async-valkey]`, `MovingWindowRateLimiter`, almacén `async+valkey://` derivado de `VALKEY_URL`; `async+memory://` en las pruebas) y `DisabledRateLimiter`. Se crea en el `lifespan` y vive en `app.state.rate_limiter`; antes del lifespan, y en las pruebas, está desactivado.
- `domain/rate_limits.py`: las reglas (`RateRule`: nombre, `"10/minute"`, clave IP/email/usuario) y `AUTH_RULES`, las rutas `/auth/*` limitadas.
- `api/auth_rate_limit.py`: el middleware de `/auth/*`, añadido entre el de SuperTokens y CORS (`main.py`). Para el reenvío de la verificación, el usuario sale del access token validado con el SDK (`get_session_without_request_response`). Rechaza con 413 un cuerpo de más de 64 KB: leerlo entero para buscar el email no debe servir para agotar la memoria.
- `core/client_ip.py`: la IP del cliente con `TRUSTED_PROXIES`.
- **Límite general por usuario** (añadido en F11 a petición del usuario, no estaba en el diseño): 600 peticiones por minuto en todo el router `protected`, con la dependencia `enforce_api_rate_limit`. Nadie lo nota usando la aplicación, pero frena un script que machaque la API.
- **Valkey caído: se deja pasar** (decisión del usuario en F11). Sin almacén no hay rate limit y queda un aviso en el log; la alternativa, bloquear, dejaría a todo el mundo sin poder iniciar sesión mientras dura la caída.
- **Respuesta:** `RateLimitedError` (`AppException` gana `headers`) o el propio middleware: `429`, `{"detail", "code": "rate_limited", "retry_after"}` y la cabecera `Retry-After`, expuesta por CORS. En el frontend, `auth.service` convierte el 429 del SDK de SuperTokens (que lanza la `Response`) en el mismo `ApiError`, y el mensaje dice cuánto esperar ("dentro de 44 segundos").
- **Comprobado:** con el middleware devolviendo un cuerpo vacío, un inicio de sesión correcto responde `FIELD_ERROR` y la prueba L4 se pone en rojo.

> **Trampa — en producción, todos detrás de la IP del proxy.** Detrás de Nginx (F7), la conexión siempre llega desde el proxy. Si `TRUSTED_PROXIES` se queda vacía, `X-Forwarded-For` se ignora y **todos los usuarios comparten una IP**: 10 inicios de sesión por minuto entre todos. Y sin la protección contraria, si se aceptara `X-Forwarded-For` de cualquiera, cada atacante se inventaría una IP por intento. Por eso solo se lee de los proxies declarados, y de derecha a izquierda.

### Valores iniciales

| Qué | Límite | Clave |
|---|---|---|
| Inicio de sesión | 10 / min | por IP |
| Inicio de sesión | 10 / hora | por email |
| Registro | 5 / hora | por IP |
| Pedir recuperación de contraseña | 3 / hora | por email |
| Pedir recuperación de contraseña | 10 / hora | por IP |
| Reenviar verificación de email | 3 / hora | por usuario |
| Toda la API con sesión **[añadido en F11]** | 600 / min | por usuario |
| Propuestas de IA | 5 / min y 50 / día | por usuario (también con clave propia: el `worker` es de todos) |
| Guardar o validar una clave de IA | 10 / hora | por usuario |
| Subir documentos | 20 / hora | por usuario |
| Generar PDF | 30 / hora | por usuario |
| Feed ICS | 60 / hora | por token |
| Baja de avisos | 30 / hora | por IP |

Son valores de partida, configurables, que se ajustarán con uso real. Al superarlos: `429`, cabecera `Retry-After` y código `rate_limited`, que el frontend traduce en "espera N minutos".

> **Trampa — leer el cuerpo en un middleware se lo come.** Para limitar por email hay que leer el email del JSON de `/auth/signin`, pero el cuerpo de una petición ASGI se lee una sola vez: si el middleware lo consume, SuperTokens recibe un cuerpo vacío y responde con un error de formato confuso. El middleware lee el cuerpo, lo guarda y **vuelve a inyectarlo** con una función `receive` propia antes de pasar la petición. Una prueba comprueba que un inicio de sesión correcto sigue funcionando con el middleware delante.

> **Trampa — limitar por email permite bloquear a otro.** Si 10 intentos fallidos **bloquearan** la cuenta de un email, cualquiera podría dejar sin acceso a otra persona sabiendo solo su email. Aquí el límite **frena** (hay que esperar) pero no bloquea la cuenta. Y el límite por IP es el que para a quien prueba muchos emails desde el mismo sitio.

> **Trampa — la IP del cliente detrás de un proxy.** Explicada en la [arquitectura de la v2](v2.md#5-flujos): solo se lee `X-Forwarded-For` si la conexión viene de una IP de `TRUSTED_PROXIES`. En desarrollo no hay proxy y se usa la IP de la conexión.

> **Trampa — el rate limit en las pruebas.** Con un límite de 10 inicios de sesión por minuto, una batería de pruebas que inicia sesión 30 veces empieza a fallar por `429` de forma intermitente, según el orden de ejecución. Las pruebas usan un Valkey propio que se vacía entre pruebas, y las que no prueban el rate limit lo desactivan por configuración.

## 3. Verificación de email como defensa

Las funciones con coste exigen email verificado (RF-06): así una cuenta falsa creada por un bot no puede gastar IA, disco ni emails. La comprobación es una dependencia del backend, `require_verified_email`. El detalle de cómo se lee el estado de verificación está en [autenticación §8](autenticacion.md#8-ampliacion-de-la-v2-verificacion-y-recuperacion).

## 4. Endpoints públicos

Todo lo que responde sin sesión, y nada más:

| Endpoint | Para qué | Protección |
|---|---|---|
| `GET /health` | Salud (v1) | — |
| `GET /api/v1/meta` | **[nuevo]** Capacidades de la instalación: `email_enabled`, proveedores de IA habilitados, usos gratuitos por cuenta. Lo usa la página de login para ocultar la recuperación de contraseña sin SMTP | Solo datos de configuración, nada de usuarios |
| `/auth/*` | SuperTokens (v1): registro, sesión, verificación, recuperación | Rate limit por IP y email |
| `GET /calendar/{token}.ics` | Feed del calendario (RF-132) | Token de 32 bytes aleatorios; en la BD solo su hash (A40); rate limit por token |
| `POST /notifications/unsubscribe` | Baja de un tipo de aviso con un clic (RF-85) | Token firmado con HMAC; rate limit por IP |

Viven en el router `public` de `api/v1/router.py`. **La prueba T1** (ya existe desde F1) lee las rutas del OpenAPI y exige sesión a todas; en la v2, compara las rutas sin sesión con esta lista, **escrita en la propia prueba**. Un endpoint público nuevo exige tocar la prueba, y por tanto una revisión consciente.

### El feed ICS en detalle

- **Token**: `secrets.token_urlsafe(32)`, que se muestra una sola vez al crear o regenerar el enlace. En la BD solo va su SHA-256. Buscar por hash es buscar por igualdad, sin comparación de cadenas vulnerable a ataques de tiempo.
- **Contenido**: entrevistas y recordatorios pendientes de −30 a +180 días, con título, empresa y hora; nada de notas (RF-134). `UID` estable por evento (el id de la entrevista o del recordatorio), para que el calendario externo **actualice** un evento movido en lugar de duplicarlo.
- **Caché**: `Cache-Control: private, max-age=900`. Google Calendar refresca los calendarios suscritos cuando quiere (a menudo cada varias horas); el manual lo avisa para que nadie piense que no funciona.

> **Trampa — un `UID` que cambia duplica los eventos.** Si el `UID` de cada evento del ICS se generara en cada respuesta, o dependiera de la fecha, los calendarios que se suscriben verían un evento **nuevo** en cada refresco y acumularían copias. El `UID` sale del id de la fila, que no cambia nunca.

## 5. Pruebas que demuestran el diseño

| # | Prueba | Qué demuestra |
|---|---|---|
| L1 | Con una excepción de usuario, su límite es el de la excepción y el de los demás no cambia | RF-143 |
| L2 | `GET /me/usage` coincide con lo creado, y tras un borrado en cascada sigue coincidiendo | Consumo calculado, no contado |
| L3 | El error de límite superado incluye `limit` y `used` | RF-142 |
| L4 | El 11.º inicio de sesión en un minuto desde la misma IP → `429` con `Retry-After`; un inicio de sesión correcto con el middleware delante funciona | Rate limit en `/auth/*` y cuerpo reinyectado |
| L5 | Con `X-Forwarded-For` falso desde una IP que no está en `TRUSTED_PROXIES`, el límite se aplica a la IP real | Proxy de confianza |
| L6 | Superar el límite por email no impide iniciar sesión a esa cuenta pasada la ventana | Frenar, no bloquear |
| L7 | La lista de rutas sin sesión del OpenAPI es exactamente la lista blanca | Superficie pública controlada |
| L8 | Feed ICS: token inválido → 404; token regenerado → el antiguo deja de funcionar; ningún evento contiene notas | RF-132, RF-134 |
| L9 | Dos respuestas del feed para el mismo evento tienen el mismo `UID`; mover la entrevista cambia la hora, no el `UID` | Sin duplicados en el calendario externo |
| L10 | `GET /api/v1/meta` no contiene nada de ningún usuario | Superficie pública mínima |

## 6. Lo que no se hace todavía

| Funcionalidad | Estado | Costura que lo permitirá |
|---|---|---|
| Planes (más límite pagando) | `[C]` | Un plan sería otra fuente del valor de `limit_for`, igual que las excepciones |
| CAPTCHA en el registro | Si el rate limit no basta | Un paso más en el registro de SuperTokens (override de su API) |
| Panel de administración para ajustar límites | `[C]` | Hoy es un script; un panel llamaría al mismo `LimitService` |
| Bloqueo por reputación de IP | `[C]` | Nginx o el proveedor del VPS |
