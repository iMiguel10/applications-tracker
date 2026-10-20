import { Trans } from "react-i18next";

import { Checkbox } from "@/shared/components/ui/checkbox";
import { legalPath } from "../lib/legalPages";

const LINK = "font-medium text-primary underline underline-offset-4";

/**
 * «He leído y acepto los términos y la política de privacidad» (issue #3), en el
 * registro y en la pantalla de aceptación. Los enlaces se abren en otra pestaña para
 * no perder lo escrito.
 */
export function LegalConsent({
  checked,
  onChange,
  errorId,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** Id del mensaje de error, para `aria-describedby`. */
  errorId?: string;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-2 text-sm leading-relaxed">
      <Checkbox
        checked={checked}
        onCheckedChange={(value) => onChange(value === true)}
        aria-invalid={errorId ? true : undefined}
        aria-describedby={errorId}
        className="mt-1"
      />
      <span>
        <Trans
          i18nKey="legal.consent.label"
          components={{
            terms: <a href={legalPath("terms")} target="_blank" rel="noopener" className={LINK} />,
            privacy: (
              <a href={legalPath("privacy")} target="_blank" rel="noopener" className={LINK} />
            ),
          }}
        />
      </span>
    </label>
  );
}
