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
  const options = KIND_FILTERS.map((kind) => ({
    value: kind,
    label: t(`documents.filters.kindOptions.${kind}`),
  }));

  return (
    <Select
      items={options}
      value={params.kind}
      onValueChange={(kind) => onChange({ kind: kind as DocumentKindFilter })}
    >
      <SelectTrigger aria-label={t("documents.filters.kind")} className="w-48">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
