import { Check, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import type { AiProvider } from "../types/Ai";
import { providerName } from "../lib/providers";

interface AiConsentDialogProps {
  provider: AiProvider;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAccept: () => void;
  accepting: boolean;
}

/**
 * Consentimiento antes de enviar datos a un proveedor de IA (RF-116, RF-154): qué
 * se envía, qué no, a quién y para qué. Se pide por proveedor.
 */
export function AiConsentDialog({
  provider,
  open,
  onOpenChange,
  onAccept,
  accepting,
}: AiConsentDialogProps) {
  const { t } = useTranslation();
  const name = providerName(provider);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("ai.consent.title", { provider: name })}</DialogTitle>
          <DialogDescription>{t("ai.consent.description", { provider: name })}</DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 text-sm">
          <div className="grid gap-1.5">
            <p className="font-medium">{t("ai.consent.sentTitle")}</p>
            <ul className="grid gap-1">
              {(["profile", "offer"] as const).map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <Check className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
                  <span>{t(`ai.consent.sent.${item}`)}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="grid gap-1.5">
            <p className="font-medium">{t("ai.consent.notSentTitle")}</p>
            <ul className="grid gap-1">
              <li className="flex items-start gap-2">
                <X className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                <span>{t("ai.consent.notSent")}</span>
              </li>
            </ul>
          </div>
          <p className="text-muted-foreground">{t("ai.consent.revoke")}</p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button onClick={onAccept} disabled={accepting}>
            {t("ai.consent.accept")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
