import { useTranslation } from "react-i18next";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import { Card, CardContent } from "@/shared/components/ui/card";
import { useMe } from "@/features/auth/hooks/queries/useMe";
import { ProfileBasicsForm } from "@/features/profile/components/ProfileBasicsForm";
import { useProfile } from "@/features/profile/hooks/queries/useProfile";

/** Perfil profesional (RF-100…102): la materia prima de los CVs generados. */
export function ProfilePage() {
  const { t } = useTranslation();
  useDocumentTitle(t("profile.title"));
  const { data, isLoading, isError, isFetching, refetch } = useProfile();
  const { data: me } = useMe();

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold">{t("profile.title")}</h1>
        <p className="text-muted-foreground">{t("profile.description")}</p>
      </div>

      {isLoading && <ListSkeleton rows={4} />}
      {isError && <ErrorState onRetry={() => refetch()} retrying={isFetching} />}
      {data && (
        <Card>
          <CardContent>
            <ProfileBasicsForm profile={data} accountEmail={me?.email} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
