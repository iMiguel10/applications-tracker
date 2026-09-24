import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { Card, CardContent } from "@/shared/components/ui/card";
import { ApplicationForm } from "@/features/applications/components/ApplicationForm";
import { useCreateApplication } from "@/features/applications/hooks/mutations/useCreateApplication";
import { emptyApplicationForm } from "@/features/applications/lib/formValues";

export function ApplicationNewPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("applications.newTitle"));
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const create = useCreateApplication();

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold">{t("applications.newTitle")}</h1>
      <Card>
        <CardContent>
          <ApplicationForm
            mode="create"
            defaultValues={emptyApplicationForm(searchParams.get("company_id") ?? "")}
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
