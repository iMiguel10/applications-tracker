import { useTranslation } from "react-i18next";

import { Button } from "@/shared/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { SearchInput } from "@/shared/components/common/SearchInput";
import { DEFAULT_LIST_PARAMS, hasActiveFilters } from "../lib/listParams";
import {
  APPLICATION_SOURCES,
  APPLICATION_STATUSES,
  WORK_MODES,
  type ApplicationListParams,
  type ApplicationSort,
  type ArchivedFilter,
} from "../types/Application";

const ALL = "__all__";

interface ApplicationFiltersProps {
  params: ApplicationListParams;
  onChange: (changes: Partial<ApplicationListParams>) => void;
}

interface FilterSelectProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

function FilterSelect({ label, value, options, onChange }: FilterSelectProps) {
  return (
    <Select items={options} value={value} onValueChange={(next) => onChange(String(next))}>
      <SelectTrigger aria-label={label} className="w-44">
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

/**
 * Barra de filtros del listado. La API admite varios valores por filtro
 * (?status=a&status=b); la interfaz ofrece uno o "todos", que cubre el uso habitual.
 */
export function ApplicationFilters({ params, onChange }: ApplicationFiltersProps) {
  const { t } = useTranslation();

  const withAll = (values: readonly string[], prefix: string, allLabel: string) => [
    { value: ALL, label: allLabel },
    ...values.map((value) => ({ value, label: t(`${prefix}.${value}`) })),
  ];
  const single = <T extends string>(values: T[]) => values[0] ?? ALL;
  const toList = <T extends string>(value: string) => (value === ALL ? [] : [value as T]);

  const sorts: ApplicationSort[] = ["applied_at", "updated_at", "company", "position_title"];

  return (
    <div className="flex flex-wrap items-center gap-2">
      <SearchInput
        value={params.q}
        onChange={(q) => onChange({ q })}
        placeholder={t("applications.searchPlaceholder")}
      />
      <FilterSelect
        label={t("applications.fields.status")}
        value={single(params.status)}
        options={withAll(APPLICATION_STATUSES, "applications.status", t("applications.filters.allStatuses"))}
        onChange={(value) => onChange({ status: toList(value) })}
      />
      <FilterSelect
        label={t("applications.fields.workMode")}
        value={single(params.work_mode)}
        options={withAll(WORK_MODES, "applications.workMode", t("applications.filters.allWorkModes"))}
        onChange={(value) => onChange({ work_mode: toList(value) })}
      />
      <FilterSelect
        label={t("applications.fields.source")}
        value={single(params.source)}
        options={withAll(APPLICATION_SOURCES, "applications.source", t("applications.filters.allSources"))}
        onChange={(value) => onChange({ source: toList(value) })}
      />
      <FilterSelect
        label={t("applications.filters.archived")}
        value={params.archived}
        options={(["active", "archived", "all"] as ArchivedFilter[]).map((value) => ({
          value,
          label: t(`applications.filters.archivedOptions.${value}`),
        }))}
        onChange={(value) => onChange({ archived: value as ArchivedFilter })}
      />
      <FilterSelect
        label={t("applications.filters.sortBy")}
        value={`${params.sort_by}:${params.order}`}
        options={sorts.flatMap((sort) =>
          (["desc", "asc"] as const).map((order) => ({
            value: `${sort}:${order}`,
            label: t(`applications.sort.${sort}.${order}`),
          })),
        )}
        onChange={(value) => {
          const [sort_by, order] = value.split(":") as [ApplicationSort, "asc" | "desc"];
          onChange({ sort_by, order });
        }}
      />
      {hasActiveFilters(params) && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            onChange({
              ...DEFAULT_LIST_PARAMS,
              sort_by: params.sort_by,
              order: params.order,
            })
          }
        >
          {t("applications.filters.clear")}
        </Button>
      )}
    </div>
  );
}
