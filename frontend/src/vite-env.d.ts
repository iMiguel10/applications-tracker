/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  /** Base del manual de uso (issue #6). Sin ella, `/manual/` del mismo dominio. */
  readonly VITE_MANUAL_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
