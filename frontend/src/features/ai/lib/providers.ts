import type { AiProvider } from "../types/Ai";

/** Nombre comercial de cada proveedor: es un nombre propio, no se traduce. */
const PROVIDER_NAMES: Record<AiProvider, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  groq: "Groq",
};

export const providerName = (provider: AiProvider) => PROVIDER_NAMES[provider];
