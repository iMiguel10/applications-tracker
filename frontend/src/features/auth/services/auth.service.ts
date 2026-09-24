import EmailPassword from "supertokens-web-js/recipe/emailpassword";
import Session from "supertokens-web-js/recipe/session";

import { apiClient } from "@/shared/lib/apiClient";
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

function formFields({ email, password }: LoginFormValues) {
  return [
    { id: "email", value: email },
    { id: "password", value: password },
  ];
}

export const authService = {
  signIn: async (values: LoginFormValues): Promise<AuthResult> =>
    toAuthResult(await EmailPassword.signIn({ formFields: formFields(values) })),

  signUp: async (values: LoginFormValues): Promise<AuthResult> =>
    toAuthResult(await EmailPassword.signUp({ formFields: formFields(values) })),

  /**
   * Pide el email de recuperación. El backend responde lo mismo exista o no la
   * cuenta (T9), así que "ok" solo significa "petición aceptada".
   */
  sendPasswordResetEmail: async (email: string): Promise<"ok" | "error"> => {
    const response = await EmailPassword.sendPasswordResetEmail({
      formFields: [{ id: "email", value: email }],
    });
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

  signOut: () => Session.signOut(),

  sessionExists: () => Session.doesSessionExist(),

  getMe: () => apiClient.get<Me>("/me"),

  deleteAccount: () => apiClient.delete<void>("/me"),
};
