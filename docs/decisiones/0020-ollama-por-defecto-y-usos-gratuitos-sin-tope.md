# 0020 — Ollama por defecto y usos gratuitos sin tope desde el entorno

- **Fecha:** 2026-10-08
- **Estado:** aceptada

## Contexto

Al terminar las claves propias (F15, paso 5), quedaba pendiente lo que el usuario pidió en [0019](0019-ollama-solo-como-ia-de-la-plataforma.md): que la IA de la plataforma por defecto fuera un **Ollama local** en lugar de Groq. Pidió además dos cosas:

- Poder probar Ollama en desarrollo con Docker, sin instalarlo en el equipo.
- Fijar desde el `.env` cuántos usos gratuitos de CV y de carta tiene cada cuenta, **o dejarlos sin tope**.

El número ya se fijaba desde el entorno (`LIMIT_AI_CV_PROPOSALS`, `LIMIT_AI_COVER_LETTER_PROPOSALS`, 0017). Lo que faltaba era "sin tope", y estaba prohibido a propósito: en F11 se decidió que los límites que protegen un recurso con coste (almacenamiento, IA) tuvieran tope siempre. Con un Ollama propio, la plataforma no paga por uso y esa razón desaparece.

## Decisión

- **Servicio `ollama` en el compose de desarrollo** (`ollama/ollama`, versión fijada), con los modelos en el volumen `ollama_data` y sin puertos publicados. Usa la CPU. Con una GPU NVIDIA se añade `compose.gpu.yml`, que no va en `compose.yml` porque en un equipo sin GPU el entorno entero no arrancaría.
- **`.env.example` arranca con Ollama** (`AI_PLATFORM_PROVIDER=ollama`, `AI_PLATFORM_MODEL=qwen3:8b`, `AI_OLLAMA_BASE_URL=http://ollama:11434`) y un tiempo de espera de 300 s. Groq queda como ejemplo comentado. En el código, `AI_PLATFORM_PROVIDER` sigue vacía por defecto: una instalación sin Ollama no debe creer que lo tiene.
- **`qwen3:8b` como modelo de desarrollo:** cabe entero en una GPU de 8 GB, escribe bien en español y admite el esquema de salida.
- **`AI_OLLAMA_CONTEXT_TOKENS`** (16 384 por defecto) se envía como `num_ctx` en cada llamada. La ventana por defecto de Ollama es de unos pocos miles de tokens, y si la entrada no cabe la recorta **sin avisar**: la propuesta saldría de medio perfil o de media oferta.
- **`LIMIT_AI_CV_PROPOSALS` y `LIMIT_AI_COVER_LETTER_PROPOSALS` admiten `unlimited`**, con cualquier proveedor: lo decide quien despliega, y el manual avisa de que con un proveedor de pago el gasto queda sin tope. Por defecto siguen siendo 1 y 1.
- **La excepción por cuenta no cambia:** `set_user_limit` sigue sin admitir "sin límite" en la IA, pero sí un número. Así, con la instalación sin tope, una cuenta concreta aún se puede limitar. Solo el valor global puede quitar el tope.

## Alternativas descartadas

- **`unlimited` solo con Ollama** (que la API no arrancara si el proveedor es de pago): más seguro, pero el usuario prefirió que lo decidiera quien despliega.
- **`gpt-oss:20b` en desarrollo**, el modelo que se usaba en Groq en versión pequeña: unos 13 GB, que no caben en una GPU de 8 GB ni en la memoria que Docker tiene en el equipo de desarrollo.
- **La GPU en `compose.yml`:** reservar un dispositivo NVIDIA hace fallar `docker compose up` en cualquier equipo sin él.
- **Que `api` y `worker` dependan de `ollama`:** con Ollama caído, la IA falla con `ai_provider_unavailable` y el resto de la aplicación sigue. No hay motivo para que la API espere a un modelo.
- **Que "sin límite" por cuenta se permitiera también en la IA:** reabriría la decisión de F11 para cada cuenta. Basta con poder quitar el tope a toda la instalación.

## Consecuencias

- La primera vez hay que descargar el modelo (`docker compose exec ollama ollama pull qwen3:8b`, unos 5 GB). Sin él, cada propuesta falla con `ai_provider_rejected` y `check_ai_provider` lo dice.
- Un modelo local tarda más que uno en la nube, y mucho más con la CPU. Si `AI_REQUEST_TIMEOUT_SECONDS` se queda corto, la propuesta falla y no se cobra.
- Arrancar el entorno sin `compose.gpu.yml` recrea `ollama` sin GPU. Funciona igual, más despacio.
- `GET /me/usage` ya respondía `limit: null` para "sin límite", y la interfaz deja de mostrar el contador de usos.
- Cambian RF-143 y RF-150 en la especificación, `limites-y-abuso.md` §1 e `ia.md` §6.
