import EmailPassword from "supertokens-web-js/recipe/emailpassword";
import EmailVerification from "supertokens-web-js/recipe/emailverification";
import Session from "supertokens-web-js/recipe/session";

import { ApiError, apiClient } from "@/shared/lib/apiClient";
import type { AuthField, AuthResult, Me, ResetPasswordResult } from "../types/Auth";
import type { LoginFormValues } from "../schemas/auth.schema";

type SdkResponse =
  | { status: "OK" }
  | { status: "WRONG_CREDENTIALS_ERROR" }
  | { status: "FIELD_ERROR"; formFields: { id: string; error: string }[] }
  | { status: string };

function toAuthResult(response: SdkResponse): AuthResult {
  switch (response.status) {
    case "OK":
      return { status: "ok" };
    case "WRONG_CREDENTIALS_ERROR":
      return { status: "wrong_credentials" };
    case "FIELD_ERROR":
      return {
        status: "field_errors",
        fields: (response as { formFields: { id: string }[] }).formFields
          .map((field) => field.id)
          .filter((id): id is AuthField => id === "email" || id === "password"),
      };
    default:
      // SIGN_IN_NOT_ALLOWED, SIGN_UP_NOT_ALLOWED, GENERAL_ERROR…
      return { status: "error" };
  }
}

/**
 * Las llamadas del SDK de SuperTokens lanzan la propia `Response` si el estado es
 * 300 o más. Un 429 del rate limit (RNF-04) se convierte en el mismo `ApiError`
 * que devuelve `apiClient`, para que los formularios lo traduzcan igual.
 */
async function withRateLimit<T>(call: () => Promise<T>): Promise<T> {
  try {
    return await call();
  } catch (error) {
    if (error instanceof Response && error.status === 429) {
      const body = (await error.json().catch(() => ({}))) as { retry_after?: unknown };
      const header = Number(error.headers.get("Retry-After"));
      const retryAfter = typeof body.retry_after === "number" ? body.retry_after : header || 60;
      throw new ApiError(429, "Too many requests", "rate_limited", { retry_after: retryAfter });
    }
    throw error;
  }
}

function formFields({ email, password }: LoginFormValues) {
  return [
    { id: "email", value: email },
    { id: "password", value: password },
  ];
}

export const authService = {
  signIn: async (values: LoginFormValues): Promise<AuthResult> =>
    toAuthResult(
      await withRateLimit(() => EmailPassword.signIn({ formFields: formFields(values) })),
    ),

  signUp: async (values: LoginFormValues): Promise<AuthResult> =>
    toAuthResult(
      await withRateLimit(() => EmailPassword.signUp({ formFields: formFields(values) })),
    ),

  /**
   * Pide el email de recuperación. El backend responde lo mismo exista o no la
   * cuenta (T9), así que "ok" solo significa "petición aceptada".
   */
  sendPasswordResetEmail: async (email: string): Promise<"ok" | "error"> => {
    const response = await withRateLimit(() =>
      EmailPassword.sendPasswordResetEmail({ formFields: [{ id: "email", value: email }] }),
    );
    return response.status === "OK" ? "ok" : "error";
  },

  /**
   * Guarda la contraseña nueva. El SDK lee el `token` y el `tenantId` de la URL
   * del enlace: no se construye la llamada a mano (autenticación §8).
   */
  submitNewPassword: async (password: string): Promise<ResetPasswordResult> => {
    const response = await EmailPassword.submitNewPassword({
      formFields: [{ id: "password", value: password }],
    });
    switch (response.status) {
      case "OK":
        return { status: "ok" };
      case "RESET_PASSWORD_INVALID_TOKEN_ERROR":
        return { status: "invalid_link" };
      case "FIELD_ERROR":
        return { status: "password_policy" };
      default:
        return { status: "error" };
    }
  },

  /**
   * Pregunta al backend si el email de la sesión está verificado. De paso, el
   * backend actualiza ese dato dentro del access token: quien verificó desde otro
   * dispositivo deja de ver el aviso al volver a esta pestaña.
   */
  isEmailVerified: async (): Promise<boolean> =>
    (await EmailVerification.isEmailVerified()).isVerified,

  sendVerificationEmail: async (): Promise<"ok" | "already_verified" | "error"> => {
    const response = await withRateLimit(() => EmailVerification.sendVerificationEmail());
    if (response.status === "OK") return "ok";
    if (response.status === "EMAIL_ALREADY_VERIFIED_ERROR") return "already_verified";
    return "error";
  },

  /** Consume el token del enlace. El SDK lo lee de la URL, con su `tenantId`. */
  verifyEmail: async (): Promise<"ok" | "invalid_link" | "error"> => {
    const response = await EmailVerification.verifyEmail();
    if (response.status === "OK") return "ok";
    if (response.status === "EMAIL_VERIFICATION_INVALID_TOKEN_ERROR") return "invalid_link";
    return "error";
  },

  signOut: () => Session.signOut(),

  sessionExists: () => Session.doesSessionExist(),

  getMe: () => apiClient.get<Me>("/me"),

  deleteAccount: () => apiClient.delete<void>("/me"),
};
