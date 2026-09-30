import { useId, useMemo } from "react";
import { useTranslation } from "react-i18next";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { noticeHoursLabel } from "../lib/noticeHours";

type NoticeSelectProps = {
  value: number;
  options: readonly number[];
  disabled?: boolean;
  onChange: (hours: number) => void;
};

/** Con cuánta antelación llega un aviso. */
export function NoticeSelect({ value, options, disabled, onChange }: NoticeSelectProps) {
  const { t } = useTranslation();
  const labelId = useId();
  // Un valor fijado por la API que no esté en la lista también se puede ver.
  const items = useMemo(
    () =>
      [...new Set([...options, value])]
        .sort((a, b) => a - b)
        .map((hours) => ({ value: String(hours), label: noticeHoursLabel(hours, t) })),
    [options, value, t],
  );

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span id={labelId} className="text-sm text-muted-foreground">
        {t("notifications.noticeLabel")}
      </span>
      <Select
        items={items}
        value={String(value)}
        onValueChange={(next) => next !== null && onChange(Number(next))}
        disabled={disabled}
      >
        <SelectTrigger className="w-44" aria-labelledby={labelId}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {items.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
