import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { Card, CardContent } from "@/shared/components/ui/card";
import { DetailSkeleton } from "@/shared/components/common/Skeletons";
import { ApplicationForm } from "@/features/applications/components/ApplicationForm";
import { ApplicationLoadError } from "@/features/applications/components/ApplicationLoadError";
import { useApplication } from "@/features/applications/hooks/queries/useApplication";
import { useUpdateApplication } from "@/features/applications/hooks/mutations/useUpdateApplication";
import { toFormValues } from "@/features/applications/lib/formValues";

export function ApplicationEditPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("applications.editTitle"));
  const navigate = useNavigate();
  const { applicationId = "" } = useParams();
  const { data: application, isLoading, error, isFetching, refetch } =
    useApplication(applicationId);
  const update = useUpdateApplication();

  if (isLoading) return <DetailSkeleton />;
  if (!application) {
    return (
      <ApplicationLoadError error={error} onRetry={() => refetch()} retrying={isFetching} />
    );
  }

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold">{t("applications.editTitle")}</h1>
      <Card>
        <CardContent>
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
        </CardContent>
      </Card>
    </div>
  );
}
