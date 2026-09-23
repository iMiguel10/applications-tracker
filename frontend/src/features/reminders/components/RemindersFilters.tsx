import { useTranslation } from "react-i18next";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import type { ReminderListParams, ReminderStatusFilter } from "../types/Reminder";

const STATUS_FILTERS: ReminderStatusFilter[] = ["pending", "done", "dismissed", "all"];

interface RemindersFiltersProps {
  params: ReminderListParams;
  onChange: (changes: Partial<ReminderListParams>) => void;
}

export function RemindersFilters({ params, onChange }: RemindersFiltersProps) {
  const { t } = useTranslation();
  const options = STATUS_FILTERS.map((status) => ({
    value: status,
    label: t(`reminders.filters.statusOptions.${status}`),
  }));

  return (
    <Select
      items={options}
      value={params.status}
      onValueChange={(status) => onChange({ status: status as ReminderStatusFilter })}
    >
      <SelectTrigger aria-label={t("reminders.filters.status")} className="w-44">
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
