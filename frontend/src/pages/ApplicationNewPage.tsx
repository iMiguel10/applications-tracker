import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { ApplicationForm } from "@/features/applications/components/ApplicationForm";
import { useCreateApplication } from "@/features/applications/hooks/mutations/useCreateApplication";
import { emptyApplicationForm } from "@/features/applications/lib/formValues";

export function ApplicationNewPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const create = useCreateApplication();

  return (
    <div className="grid max-w-3xl gap-6">
      <h1 className="text-2xl font-semibold">{t("applications.newTitle")}</h1>
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
    </div>
  );
}
