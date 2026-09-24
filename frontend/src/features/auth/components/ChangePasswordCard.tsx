import { useState } from "react";
import { KeyRound } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";
import { useSendPasswordResetEmail } from "../hooks/mutations/useSendPasswordResetEmail";

/**
 * Cambiar la contraseña con sesión iniciada: el mismo enlace por email que la
 * recuperación (RF-03), enviado a la dirección de la cuenta. Así cambiarla exige
 * acceso al correo, no solo una sesión abierta (que podría ser robada), y no hay
 * una segunda vía que mantener.
 */
export function ChangePasswordCard({ email }: { email: string }) {
  const { t } = useTranslation();
  const { data: meta } = useMeta();
  const sendResetEmail = useSendPasswordResetEmail();
  const [sent, setSent] = useState(false);

  const send = () =>
    sendResetEmail.mutate(email, {
      onSuccess: (result) => {
        if (result === "ok") setSent(true);
        else toast.error(t("auth.errors.generic"));
      },
      onError: () => toast.error(t("auth.errors.generic")),
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("account.password.title")}</CardTitle>
        <CardDescription>
          {meta?.email_enabled === false
            ? t("account.password.unavailable")
            : t("account.password.description", { email })}
        </CardDescription>
      </CardHeader>
      {meta?.email_enabled !== false && (
        <CardContent>
          {sent ? (
            <p role="status" className="text-sm leading-relaxed">
              {t("account.password.sent", { email })}
            </p>
          ) : (
            <Button variant="outline" onClick={send} disabled={sendResetEmail.isPending}>
              <KeyRound />
              {t("account.password.send")}
            </Button>
          )}
        </CardContent>
      )}
    </Card>
  );
}
