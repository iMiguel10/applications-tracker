import type { AiProvider } from "../types/Ai";

/** Nombre comercial de cada proveedor: es un nombre propio, no se traduce. */
const PROVIDER_NAMES: Record<AiProvider, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  groq: "Groq",
  ollama: "Ollama",
};

export const providerName = (provider: AiProvider) => PROVIDER_NAMES[provider];

/** Dónde se consigue una clave de API de cada proveedor de claves propias (RF-156).
 * Ollama no tiene: solo es IA de la plataforma (0019). */
const KEY_PAGES: Partial<Record<AiProvider, string>> = {
  anthropic: "https://platform.claude.com/settings/keys",
  openai: "https://platform.openai.com/api-keys",
  groq: "https://console.groq.com/keys",
};

export const keyPageUrl = (provider: AiProvider): string | null => KEY_PAGES[provider] ?? null;

/** "Anthropic, OpenAI o Groq" en el idioma de la interfaz. */
export const providerList = (providers: AiProvider[], language: string) =>
  new Intl.ListFormat(language, { type: "disjunction" }).format(providers.map(providerName));

/** La tarjeta de IA de Preferencias: el enlace lleva directamente a ella. */
export const AI_SETTINGS_ID = "ai-settings";
export const AI_SETTINGS_PATH = `/preferences#${AI_SETTINGS_ID}`;
