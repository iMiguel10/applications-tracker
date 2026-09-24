import { z } from "zod";

// Solo formato. La política de contraseñas (longitud, número…) vive en el backend
// (invariante 7) y llega como FIELD_ERROR: duplicarla aquí acabaría divergiendo.
export const loginSchema = z.object({
  email: z.string().trim().min(1, "auth.validation.emailRequired").email("auth.validation.emailInvalid"),
  password: z.string().min(1, "auth.validation.passwordRequired"),
});

export const registerSchema = loginSchema
  .extend({
    confirmPassword: z.string().min(1, "auth.validation.passwordRequired"),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "auth.validation.passwordsDoNotMatch",
    path: ["confirmPassword"],
  });

export const forgotPasswordSchema = loginSchema.pick({ email: true });

export const resetPasswordSchema = z
  .object({
    password: z.string().min(1, "auth.validation.passwordRequired"),
    confirmPassword: z.string().min(1, "auth.validation.passwordRequired"),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "auth.validation.passwordsDoNotMatch",
    path: ["confirmPassword"],
  });

export type LoginFormValues = z.infer<typeof loginSchema>;
export type RegisterFormValues = z.infer<typeof registerSchema>;
export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;
export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;
