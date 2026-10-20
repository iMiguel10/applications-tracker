import { useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { ApiError } from "@/shared/lib/apiClient";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { useMe } from "@/features/auth/hooks/queries/useMe";
import { useAcceptLegal } from "@/features/auth/hooks/mutations/useAcceptLegal";
import { useSignOut } from "@/features/auth/hooks/mutations/useSignOut";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";
import { metaKeys } from "@/features/meta/meta.keys";
import { LegalConsent } from "./LegalConsent";

/**
 * Pide aceptar los términos y la privacidad vigentes antes de usar la aplicación
 * (issue #3, decisión 0026): a quien se registra, a las cuentas creadas por script, a
 * las que ya existían y a todas cuando cambia la versión. Solo si la instalación los
 * tiene. Mientras no se sabe (cargando o con error), deja pasar: no bloquea la
 * aplicación por un fallo de red.
 */
export function LegalGate({ children }: { children: ReactNode }) {
  const { data: meta } = useMeta();
  const { data: me } = useMe();

  const pending =
    meta?.legal.configured === true &&
    me !== undefined &&
    me.legal_accepted_version !== meta.legal.version;
  if (!pending) return children;
  return <LegalAcceptance version={meta.legal.version} />;
}

function LegalAcceptance({ version }: { version: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const accept = useAcceptLegal();
  const signOut = useSignOut();
  const [checked, setChecked] = useState(false);
  const [missing, setMissing] = useState(false);

  const submit = () => {
    if (!checked) {
      setMissing(true);
      return;
    }
    accept.mutate(version, {
      onError: (error) => {
        // La versión cambió con la pantalla abierta: se pide la nueva y se muestra.
        if (error instanceof ApiError && error.code === "legal_version_outdated") {
          void queryClient.invalidateQueries({ queryKey: metaKeys.all });
          setChecked(false);
        }
        toast.error(t(errorMessageKey(error), errorMessageParams(error)));
      },
    });
  };

  return (
    <div className="mx-auto max-w-lg py-8">
      <Card>
        <CardHeader>
          <CardTitle>
            <h1 className="text-xl font-semibold">{t("legal.accept.title")}</h1>
          </CardTitle>
          <CardDescription>{t("legal.accept.description", { version })}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-5">
          <div className="grid gap-2">
            <LegalConsent
              checked={checked}
              onChange={(value) => {
                setChecked(value);
                if (value) setMissing(false);
              }}
              errorId={missing ? "legal-consent-error" : undefined}
            />
            {missing && (
              <p id="legal-consent-error" className="text-sm text-destructive">
                {t("legal.consent.required")}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={submit} disabled={accept.isPending}>
              {t("legal.accept.button")}
            </Button>
            <Button variant="ghost" onClick={() => signOut.mutate()} disabled={signOut.isPending}>
              {t("auth.signOut")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
