import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { ApplicationForm } from "@/features/applications/components/ApplicationForm";
import { useApplication } from "@/features/applications/hooks/queries/useApplication";
import { useUpdateApplication } from "@/features/applications/hooks/mutations/useUpdateApplication";
import { toFormValues } from "@/features/applications/lib/formValues";

export function ApplicationEditPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { applicationId = "" } = useParams();
  const { data: application, isLoading, isError } = useApplication(applicationId);
  const update = useUpdateApplication();

  if (isLoading) return <p className="text-muted-foreground">{t("common.loading")}</p>;
  if (isError || !application) return <p className="text-destructive">{t("errors.not_found")}</p>;

  return (
    <div className="grid max-w-3xl gap-6">
      <h1 className="text-2xl font-semibold">{t("applications.editTitle")}</h1>
      <ApplicationForm
        // key: si cambia la solicitud cargada, el formulario se reinicia con sus datos.
        key={application.updated_at}
        mode="edit"
        defaultValues={toFormValues(application)}
        initialCompany={application.company}
        submitting={update.isPending}
        onSubmit={async (values) => {
          await update.mutateAsync({ id: application.id, values });
          toast.success(t("applications.updated"));
          navigate(`/applications/${application.id}`, { replace: true });
        }}
        onCancel={() => navigate(`/applications/${application.id}`)}
      />
    </div>
  );
}
