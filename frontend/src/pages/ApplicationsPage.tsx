import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApplicationsList } from "@/features/applications/components/ApplicationsList";
import { CreateApplicationForm } from "@/features/applications/components/CreateApplicationForm";

const PAGE_SIZE = 10;

// F0: página mínima. En F2 los filtros y la página pasan a la URL (decisión A16).
export function ApplicationsPage() {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);

  return (
    <main className="mx-auto grid max-w-2xl gap-6 p-6">
      <h1 className="text-2xl font-semibold">{t("applications.title")}</h1>
      <CreateApplicationForm />
      <ApplicationsList page={page} limit={PAGE_SIZE} onPageChange={setPage} />
    </main>
  );
}
