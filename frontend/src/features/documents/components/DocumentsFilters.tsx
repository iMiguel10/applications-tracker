import { useTranslation } from "react-i18next";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import type { DocumentKindFilter, DocumentListParams } from "../types/Document";

const KIND_FILTERS: DocumentKindFilter[] = ["all", "cv", "cover_letter"];

interface DocumentsFiltersProps {
  params: DocumentListParams;
  onChange: (changes: Partial<DocumentListParams>) => void;
}

export function DocumentsFilters({ params, onChange }: DocumentsFiltersProps) {
  const { t } = useTranslation();
  const kinds = KIND_FILTERS.map((kind) => ({
    value: kind,
    label: t(`documents.filters.kindOptions.${kind}`),
  }));
  // RF-93: los archivados salen de la biblioteca, pero se pueden consultar aparte.
  const places = [
    { value: "library", label: t("documents.filters.placeOptions.library") },
    { value: "archived", label: t("documents.filters.placeOptions.archived") },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      <Select
        items={kinds}
        value={params.kind}
        onValueChange={(kind) => onChange({ kind: kind as DocumentKindFilter })}
      >
        <SelectTrigger aria-label={t("documents.filters.kind")} className="w-52">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {kinds.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        items={places}
        value={params.archived ? "archived" : "library"}
        onValueChange={(place) => onChange({ archived: place === "archived" })}
      >
        <SelectTrigger aria-label={t("documents.filters.place")} className="w-44">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {places.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
