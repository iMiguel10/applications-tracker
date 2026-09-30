import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { SortableList } from "@/shared/components/common/SortableList";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { useReorderEntries } from "../hooks/mutations/useReorderEntries";
import { formatMonth } from "../lib/months";
import type { EntryKind, ProfileEntry } from "../types/ProfileEntry";
import { DeleteEntryDialog } from "./DeleteEntryDialog";
import { EntryFormDialog } from "./EntryFormDialog";

type Props = {
  kind: EntryKind;
  /** Las entradas de esta sección, en su orden. */
  entries: ProfileEntry[];
};

/** Una sección del perfil (experiencia, formación…) con sus entradas, que se
 * reordenan arrastrando o con el teclado. */
export function EntriesSection({ kind, entries }: Props) {
  const { t } = useTranslation();
  const reorder = useReorderEntries();
  const [editing, setEditing] = useState<ProfileEntry | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleting, setDeleting] = useState<ProfileEntry | null>(null);
  const section = `profile.entries.${kind}`;

  const openForm = (entry: ProfileEntry | null) => {
    setEditing(entry);
    setFormOpen(true);
  };

  const move = (from: number, to: number) => {
    const ids = entries.map((entry) => entry.id);
    const [moved] = ids.splice(from, 1);
    ids.splice(to, 0, moved);
    reorder.mutate(
      { kind, entryIds: ids },
      { onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))) },
    );
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <CardTitle>
          <h2>{t(`${section}.section`)}</h2>
        </CardTitle>
        <Button variant="outline" size="sm" onClick={() => openForm(null)}>
          <Plus aria-hidden />
          {t(`${section}.add`)}
        </Button>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t(`${section}.empty`)}</p>
        ) : (
          <SortableList
            items={entries.map((entry) => ({ ...entry, label: entry.title }))}
            onMove={move}
            className="grid gap-2"
            itemClassName="rounded-lg border bg-card"
            renderItem={(entry, handle) => (
              <div className="flex items-start gap-2 p-3">
                <div className="pt-0.5">{handle}</div>
                <EntrySummary entry={entry} />
                <div className="flex shrink-0 gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={t("profile.entries.edit", { title: entry.title })}
                    onClick={() => openForm(entry)}
                  >
                    <Pencil aria-hidden />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={t("profile.entries.delete", { title: entry.title })}
                    onClick={() => setDeleting(entry)}
                  >
                    <Trash2 aria-hidden />
                  </Button>
                </div>
              </div>
            )}
          />
        )}
      </CardContent>

      <EntryFormDialog kind={kind} open={formOpen} onOpenChange={setFormOpen} entry={editing} />
      <DeleteEntryDialog entry={deleting} onOpenChange={(open) => !open && setDeleting(null)} />
    </Card>
  );
}

function EntrySummary({ entry }: { entry: ProfileEntry }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "es";
  const place = [entry.organization, entry.location].filter(Boolean).join(", ");
  const start = entry.start_date ? formatMonth(entry.start_date, locale) : null;
  const end = entry.is_current
    ? t("profile.entries.present")
    : entry.end_date
      ? formatMonth(entry.end_date, locale)
      : null;
  const dates = start && end ? `${start} – ${end}` : (start ?? end);

  return (
    <div className="min-w-0 flex-1">
      <p className="font-medium">{entry.title}</p>
      {place && <p className="text-sm text-muted-foreground">{place}</p>}
      {dates && <p className="text-sm text-muted-foreground">{dates}</p>}
      {entry.bullets.length > 0 && (
        <p className="mt-1 text-xs text-muted-foreground">
          {t("profile.entries.bulletCount", { count: entry.bullets.length })}
        </p>
      )}
    </div>
  );
}
