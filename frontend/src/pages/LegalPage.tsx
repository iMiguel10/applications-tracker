import { useTranslation } from "react-i18next";
import { Link, Navigate, useParams } from "react-router-dom";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import { LanguageSwitcher } from "@/shared/components/LanguageSwitcher";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";
import { LegalLinks } from "@/features/legal/components/LegalLinks";
import { isLegalPage, legalPath } from "@/features/legal/lib/legalPages";
import es from "@/features/legal/content/es";
import en from "@/features/legal/content/en";

// Estilos del texto legal: titulares, párrafos y listas sin tocar cada etiqueta.
const PROSE =
  "text-sm leading-relaxed [&_h2]:mt-8 [&_h2]:mb-2 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-foreground [&_p]:mt-2 [&_ul]:mt-2 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5 [&_a]:text-primary [&_a]:underline [&_a]:underline-offset-4";

/**
 * Páginas legales de la instalación (issue #3, decisión 0026): aviso legal,
 * privacidad, términos y cookies. Públicas, con o sin sesión. Los textos se montan
 * con el responsable y lo que la instalación tiene activo (`GET /meta`); sin
 * responsable configurado, lo dicen en vez de inventar datos.
 */
export function LegalPage() {
  const { t, i18n } = useTranslation();
  const { page } = useParams();
  const { data: meta, isLoading, isError, isFetching, refetch } = useMeta();
  const known = isLegalPage(page);
  useDocumentTitle(known ? t(`legal.nav.${page}`) : "");

  if (!known) return <Navigate to={legalPath("notice")} replace />;

  const texts = i18n.resolvedLanguage?.startsWith("en") ? en : es;
  const versioned = page === "privacy" || page === "terms";

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-3">
          <Link to="/" className="flex items-center gap-2.5">
            <img src="/brand/logo.png" alt="" className="size-7" />
            <span className="bg-gradient-to-r from-chart-1 to-chart-2 bg-clip-text text-lg font-semibold tracking-tight whitespace-nowrap text-transparent">
              {t("app.name")}
            </span>
          </Link>
          <LanguageSwitcher />
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="text-2xl font-semibold">{t(`legal.nav.${page}`)}</h1>
        {isLoading && <ListSkeleton rows={6} />}
        {isError && <ErrorState onRetry={() => refetch()} retrying={isFetching} />}
        {meta && !meta.legal.configured && (
          <div role="status" className="mt-6 rounded-lg border bg-card p-4 text-sm">
            <p className="font-medium">{t("legal.notConfigured.title")}</p>
            <p className="mt-1 text-muted-foreground">{t("legal.notConfigured.body")}</p>
          </div>
        )}
        {meta?.legal.configured && (
          <>
            {versioned && (
              <p className="mt-1 text-sm text-muted-foreground">
                {t("legal.version", { version: meta.legal.version })}
              </p>
            )}
            <article className={PROSE}>
              {texts[page]({
                legal: meta.legal,
                emailEnabled: meta.email_enabled,
                site: window.location.origin,
              })}
            </article>
            <LegalLinks className="mt-10 border-t pt-6" />
          </>
        )}
      </main>
    </div>
  );
}
