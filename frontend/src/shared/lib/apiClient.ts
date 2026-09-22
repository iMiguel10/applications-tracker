const API_URL = import.meta.env.VITE_API_URL;

if (!API_URL) {
  throw new Error("Falta la variable de entorno VITE_API_URL");
}

export class ApiError extends Error {
  readonly status: number;
  /** Código estable de la API (p. ej. "company_name_taken"); se traduce con errors.<code>. */
  readonly code: string | null;

  constructor(status: number, message: string, code: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown };

/**
 * Único punto de acceso HTTP a la API. Solo los `services/` de cada feature
 * deben importarlo; los hooks y componentes nunca llaman a fetch directamente.
 *
 * No gestiona el 401: el SDK de SuperTokens intercepta fetch, refresca la sesión
 * y reintenta. Refrescar también aquí provocaría refrescos duplicados, que
 * SuperTokens interpreta como robo de token y revoca la sesión (invariante 10).
 */
async function request<T>(path: string, { body, headers, ...init }: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_URL}/api/v1${path}`, {
    ...init,
    // Las cookies de sesión (httpOnly) solo viajan con credentials: "include".
    credentials: "include",
    headers: {
      ...(body !== undefined && { "Content-Type": "application/json" }),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    // Los 422 de validación de FastAPI traen `detail` como lista y sin `code`.
    const message = typeof data?.detail === "string" ? data.detail : response.statusText;
    throw new ApiError(response.status, message, data?.code ?? null);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string, init?: RequestOptions) => request<T>(path, { ...init, method: "GET" }),
  post: <T>(path: string, body?: unknown, init?: RequestOptions) =>
    request<T>(path, { ...init, method: "POST", body }),
  put: <T>(path: string, body?: unknown, init?: RequestOptions) =>
    request<T>(path, { ...init, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, init?: RequestOptions) =>
    request<T>(path, { ...init, method: "PATCH", body }),
  delete: <T>(path: string, init?: RequestOptions) => request<T>(path, { ...init, method: "DELETE" }),
};
