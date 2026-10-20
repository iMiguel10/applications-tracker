import { Download } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { HelpLink } from "@/shared/components/help/HelpLink";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { useExportAccountData } from "../hooks/mutations/useExportAccountData";

/** Descargar todos los datos de la cuenta (issue #4, RGPD arts. 15 y 20): un `.zip`
 * con un JSON por tipo de dato y los PDF. */
export function ExportDataCard() {
  const { t } = useTranslation();
  const exportData = useExportAccountData();

  const download = () =>
    exportData.mutate(undefined, {
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("account.export.title")}</CardTitle>
        <CardAction>
          <HelpLink page="exportData" />
        </CardAction>
        <CardDescription>{t("account.export.description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button variant="outline" onClick={download} disabled={exportData.isPending}>
          <Download />
          {exportData.isPending ? t("account.export.preparing") : t("account.export.button")}
        </Button>
      </CardContent>
    </Card>
  );
}
