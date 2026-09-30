import { useTranslation } from "react-i18next";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import { Card, CardContent } from "@/shared/components/ui/card";
import { useMe } from "@/features/auth/hooks/queries/useMe";
import { EntriesSection } from "@/features/profile/components/EntriesSection";
import { ProfileBasicsForm } from "@/features/profile/components/ProfileBasicsForm";
import { useProfile } from "@/features/profile/hooks/queries/useProfile";
import { useProfileEntries } from "@/features/profile/hooks/queries/useProfileEntries";
import { ENTRY_KINDS } from "@/features/profile/types/ProfileEntry";

/** Perfil profesional (RF-100…102): la materia prima de los CVs generados. */
export function ProfilePage() {
  const { t } = useTranslation();
  useDocumentTitle(t("profile.title"));
  const profile = useProfile();
  const entries = useProfileEntries();
  const { data: me } = useMe();

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold">{t("profile.title")}</h1>
        <p className="text-muted-foreground">{t("profile.description")}</p>
      </div>

      {profile.isLoading && <ListSkeleton rows={4} />}
      {profile.isError && (
        <ErrorState onRetry={() => profile.refetch()} retrying={profile.isFetching} />
      )}
      {profile.data && (
        <Card>
          <CardContent>
            <ProfileBasicsForm profile={profile.data} accountEmail={me?.email} />
          </CardContent>
        </Card>
      )}

      {entries.isLoading && <ListSkeleton rows={4} />}
      {entries.isError && (
        <ErrorState onRetry={() => entries.refetch()} retrying={entries.isFetching} />
      )}
      {entries.data &&
        ENTRY_KINDS.map((kind) => (
          <EntriesSection
            key={kind}
            kind={kind}
            entries={entries.data.filter((entry) => entry.kind === kind)}
          />
        ))}
    </div>
  );
}
