---
title: Activar la IA de la plataforma
sidebar_label: IA de la plataforma
---

La IA adapta un CV o escribe una carta para una oferta. Hay dos formas de usarla, y son independientes:

- Los **usos gratuitos** de la instalación, con el proveedor y el modelo que pongas tú (esta página).
- La **clave propia** de cada usuario, a su cargo ([Variables](variables.md): `AI_KEYS_ENCRYPTION_KEYS`).

**La IA de la plataforma es opcional y se activa después de desplegar, solo con variables.** Sin ella, nadie tiene usos gratuitos: la tarjeta de IA explica cómo seguir con una clave propia, y `GET /me/usage` no los devuelve. Para activarla, añade las variables de abajo y **vuelve a desplegar**.

Si defines `AI_PLATFORM_PROVIDER`, el modelo y la clave (con Ollama, su dirección) son obligatorios: sin ellos, la API no arranca y el log dice qué falta.

## Variables

| Variable | Por defecto | Qué es |
|---|---|---|
| `AI_PLATFORM_PROVIDER` | vacía | Proveedor de los usos gratuitos: `groq`, `anthropic`, `openai` u `ollama`. Vacía: no hay uso gratuito |
| `AI_PLATFORM_MODEL` | vacía | Modelo de ese proveedor, por ejemplo `openai/gpt-oss-120b` en Groq |
| `AI_PLATFORM_API_KEY` | vacía | Clave de API de la instalación en ese proveedor. Con Ollama no hace falta |
| `AI_OLLAMA_BASE_URL` | vacía | Dirección de tu Ollama, por ejemplo `http://192.168.1.50:11434`. Obligatoria con `ollama` |
| `AI_PLATFORM_INPUT_USD_PER_MTOK` | 0 | Precio del modelo por millón de tokens de entrada, en dólares. Solo sirve para estimar el coste de cada uso |
| `AI_PLATFORM_OUTPUT_USD_PER_MTOK` | 0 | Lo mismo para los tokens de salida |
| `AI_OLLAMA_CONTEXT_TOKENS` | 16384 | Tokens de contexto que se piden a Ollama, entrada y salida juntas. Más contexto, más memoria |
| `AI_REQUEST_TIMEOUT_SECONDS` | 120 | Tiempo máximo de espera de una respuesta del proveedor. Con un modelo local, súbelo (300) |
| `LIMIT_AI_CV_PROPOSALS` | 1 | Usos gratuitos para adaptar el CV, por cuenta. No se renuevan. `unlimited`: sin tope |
| `LIMIT_AI_COVER_LETTER_PROPOSALS` | 1 | Lo mismo para las cartas de presentación |

## Con un proveedor de pago

Groq, Anthropic u OpenAI:

```text
AI_PLATFORM_PROVIDER=groq
AI_PLATFORM_MODEL=openai/gpt-oss-120b
AI_PLATFORM_API_KEY=<tu clave del proveedor>
```

La clave se guarda como cualquier otra contraseña: quien la tenga gasta a cargo de tu cuenta en el proveedor. **Pon también un tope de gasto en la consola del proveedor.**

:::warning Usos gratuitos sin tope
`unlimited` quita el tope a todas las cuentas. Con un proveedor de pago, **el gasto queda sin límite**. A una cuenta concreta le puedes seguir dando un número con `set_user_limit` (por ejemplo, `ai_cv_proposals 5`), pero no dejarla sin tope.
:::

## Con Ollama

Con [Ollama](https://ollama.com) los usos gratuitos no te cuestan nada por uso, pero **Ollama no forma parte de este despliegue**: tiene que estar ya funcionando en otra máquina (mejor con GPU NVIDIA) o como un recurso aparte, y la API debe poder llegar a su dirección. Si es un recurso aparte de Coolify, conéctalo a la red del stack o usa una dirección alcanzable desde él.

1. En la máquina de Ollama, descarga el modelo, una sola vez:

    ```bash
    ollama pull qwen3:8b
    ```

2. Configura:

    ```text
    AI_PLATFORM_PROVIDER=ollama
    AI_PLATFORM_MODEL=qwen3:8b
    AI_OLLAMA_BASE_URL=http://192.168.1.50:11434
    AI_OLLAMA_CONTEXT_TOKENS=16384
    AI_REQUEST_TIMEOUT_SECONDS=300
    ```

La dirección la fijas tú: los usuarios nunca eligen una. Un modelo pequeño responde peor y tarda más.

## Comprobar que funciona

Con la instalación redesplegada, en la terminal del servicio `api` (o `docker exec -it <contenedor-api> …`; sin Coolify, `docker compose -f compose.prod.yml exec api …`), una llamada real que cuesta unas decenas de tokens:

```bash
python -m app.scripts.check_ai_provider
```

**Qué debe verse:** una línea como `groq/openai/gpt-oss-120b: funciona (stop, 40 tokens de entrada y 12 de salida).` y código de salida 0. Si falla, termina con código 1 y dice `falló con <código>` (`ai_provider_auth`: clave rechazada; `ai_provider_quota`: sin saldo o cuota; `ai_provider_unavailable`: proveedor o dirección inalcanzable; `ai_provider_rejected`: petición o modelo rechazados) o que falta `AI_PLATFORM_PROVIDER`.
