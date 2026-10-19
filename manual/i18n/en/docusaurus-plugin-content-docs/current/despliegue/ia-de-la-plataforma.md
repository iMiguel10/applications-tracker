---
title: Enable the platform AI
sidebar_label: Platform AI
---

AI adapts a CV or writes a letter for a job posting. There are two ways to use it, and they are independent:

- The installation's **free uses**, with the provider and model you choose (this page).
- Each user's **own key**, at their expense ([Variables](variables.md): `AI_KEYS_ENCRYPTION_KEYS`).

**Platform AI is optional and is enabled after deploying, with variables only.** Without it, nobody gets free uses: the AI card explains how to continue with your own key, and `GET /me/usage` doesn't return them. To enable it, add the variables below and **deploy again**.

If you set `AI_PLATFORM_PROVIDER`, the model and the key (with Ollama, its address) are required: without them the API doesn't start and the log says what is missing.

## Variables

| Variable | Default | What it is |
|---|---|---|
| `AI_PLATFORM_PROVIDER` | empty | Provider of the free uses: `groq`, `anthropic`, `openai` or `ollama`. Empty: no free use |
| `AI_PLATFORM_MODEL` | empty | Model of that provider, for example `openai/gpt-oss-120b` on Groq |
| `AI_PLATFORM_API_KEY` | empty | The installation's API key with that provider. Not needed with Ollama |
| `AI_OLLAMA_BASE_URL` | empty | Address of your Ollama, for example `http://192.168.1.50:11434`. Required with `ollama` |
| `AI_PLATFORM_INPUT_USD_PER_MTOK` | 0 | Model price per million input tokens, in dollars. Only used to estimate the cost of each use |
| `AI_PLATFORM_OUTPUT_USD_PER_MTOK` | 0 | The same for output tokens |
| `AI_OLLAMA_CONTEXT_TOKENS` | 16384 | Context tokens requested from Ollama, input and output together. More context, more memory |
| `AI_REQUEST_TIMEOUT_SECONDS` | 120 | Maximum wait for a provider's response. With a local model, raise it (300) |
| `LIMIT_AI_CV_PROPOSALS` | 1 | Free uses to adapt the CV, per account. They don't renew. `unlimited`: no cap |
| `LIMIT_AI_COVER_LETTER_PROPOSALS` | 1 | The same for cover letters |

## With a paid provider

Groq, Anthropic or OpenAI:

```text
AI_PLATFORM_PROVIDER=groq
AI_PLATFORM_MODEL=openai/gpt-oss-120b
AI_PLATFORM_API_KEY=<your provider key>
```

The key is kept like any other password: whoever has it spends at the expense of your account with the provider. **Also set a spending cap in the provider's console.**

:::warning Free uses with no cap
`unlimited` removes the cap for every account. With a paid provider, **spending becomes unlimited**. You can still give a specific account a number with `set_user_limit` (for example, `ai_cv_proposals 5`), but not leave it uncapped.
:::

## With Ollama

With [Ollama](https://ollama.com) the free uses cost you nothing per use, but **Ollama is not part of this deployment**: it must already be running on another machine (preferably with an NVIDIA GPU) or as a separate resource, and the API must be able to reach its address. If it is a separate Coolify resource, connect it to the stack's network or use an address reachable from it.

1. On the Ollama machine, download the model, just once:

    ```bash
    ollama pull qwen3:8b
    ```

2. Configure:

    ```text
    AI_PLATFORM_PROVIDER=ollama
    AI_PLATFORM_MODEL=qwen3:8b
    AI_OLLAMA_BASE_URL=http://192.168.1.50:11434
    AI_OLLAMA_CONTEXT_TOKENS=16384
    AI_REQUEST_TIMEOUT_SECONDS=300
    ```

You set the address: users never choose one. A small model answers worse and takes longer.

## Check that it works

With the installation redeployed, in the `api` service's terminal (or `docker exec -it <api-container> …`; without Coolify, `docker compose -f compose.prod.yml exec api …`), a real call that costs a few dozen tokens:

```bash
python -m app.scripts.check_ai_provider
```

**What you should see:** a line like `groq/openai/gpt-oss-120b: funciona (stop, 40 tokens de entrada y 12 de salida).` and exit code 0. If it fails, it exits with code 1 and says `falló con <code>` (`ai_provider_auth`: key rejected; `ai_provider_quota`: no balance or quota; `ai_provider_unavailable`: provider or address unreachable; `ai_provider_rejected`: request or model rejected) or that `AI_PLATFORM_PROVIDER` is missing. The script's messages are in Spanish.
