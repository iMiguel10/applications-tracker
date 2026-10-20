import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { Card, CardContent } from "@/shared/components/ui/card";
import { ApplicationForm } from "@/features/applications/components/ApplicationForm";
import { useCreateApplication } from "@/features/applications/hooks/mutations/useCreateApplication";
import { emptyApplicationForm } from "@/features/applications/lib/formValues";
import { useAccountZone } from "@/features/auth/hooks/useAccountZone";
import { todayIn } from "@/shared/lib/dates";
import { HelpLink } from "@/shared/components/help/HelpLink";

export function ApplicationNewPage() {
  const { t } = useTranslation();
  const zone = useAccountZone();
  useDocumentTitle(t("applications.newTitle"));
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const create = useCreateApplication();

  return (
    <div className="grid gap-6">
      <div className="flex items-center gap-1">
        <h1 className="text-2xl font-semibold">{t("applications.newTitle")}</h1>
        <HelpLink page="registerApplication" />
      </div>
      <Card>
        <CardContent>
          <ApplicationForm
            mode="create"
            defaultValues={emptyApplicationForm(todayIn(zone), searchParams.get("company_id") ?? "")}
            submitting={create.isPending}
            onSubmit={async (values) => {
              const application = await create.mutateAsync(values);
              toast.success(t("applications.created"));
              navigate(`/applications/${application.id}`, { replace: true });
            }}
            onCancel={() => navigate(-1)}
          />
        </CardContent>
      </Card>
    </div>
  );
}
