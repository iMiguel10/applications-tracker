import { useState } from "react";
import { MailCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { Button } from "@/shared/components/ui/button";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";
import { useEmailVerified } from "../hooks/queries/useEmailVerified";
import { useSendVerificationEmail } from "../hooks/mutations/useSendVerificationEmail";

/**
 * Recuerda verificar el email (RF-05). La aplicación se usa igual sin verificar:
 * es un aviso, no un bloqueo. Sin correo en la instalación no se muestra, porque no
 * hay nada que el usuario pueda hacer.
 */
export function EmailVerificationBanner({ email }: { email: string }) {
  const { t } = useTranslation();
  const { data: meta } = useMeta();
  const emailEnabled = meta?.email_enabled === true;
  const { data: verified } = useEmailVerified({ enabled: emailEnabled });
  const resend = useSendVerificationEmail();
  const [resent, setResent] = useState(false);

  if (!emailEnabled || verified !== false) return null;

  const onResend = () =>
    resend.mutate(undefined, {
      onSuccess: (result) => {
        if (result === "ok") setResent(true);
        else if (result === "error") toast.error(t("auth.errors.generic"));
      },
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });

  return (
    <div role="status" className="border-b bg-muted/60">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5 text-sm">
        <MailCheck className="size-4 shrink-0 text-primary" aria-hidden />
        <p className="min-w-0 flex-1">
          {resent
            ? t("auth.verifyEmail.bannerResent", { email })
            : t("auth.verifyEmail.banner", { email })}
        </p>
        {!resent && (
          <Button size="sm" variant="outline" onClick={onResend} disabled={resend.isPending}>
            {t("auth.verifyEmail.resend")}
          </Button>
        )}
      </div>
    </div>
  );
}
