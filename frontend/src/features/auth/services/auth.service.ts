import EmailPassword from "supertokens-web-js/recipe/emailpassword";
import Session from "supertokens-web-js/recipe/session";

import { apiClient } from "@/shared/lib/apiClient";
import type { AuthField, AuthResult, Me } from "../types/Auth";
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

  signOut: () => Session.signOut(),

  sessionExists: () => Session.doesSessionExist(),

  getMe: () => apiClient.get<Me>("/me"),

  deleteAccount: () => apiClient.delete<void>("/me"),
};
