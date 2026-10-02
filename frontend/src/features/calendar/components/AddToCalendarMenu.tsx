import { CalendarPlus, Download, ExternalLink } from "lucide-react";
import { useTranslation } from "react-i18next";

import { downloadBlob } from "@/shared/lib/download";
import { Button } from "@/shared/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/components/ui/dropdown-menu";
import { buildIcs, googleCalendarUrl, icsFilename, type CalendarEntry } from "../lib/addToCalendar";

interface AddToCalendarMenuProps {
  entry: CalendarEntry;
  className?: string;
}

/**
 * Añadir un evento suelto a otro calendario (RF-133): Google Calendar con el
 * evento ya rellenado, o un `.ics` que importa cualquiera (Outlook, Apple…). Todo
 * en el navegador; es una copia que no se actualiza si el evento cambia.
 */
export function AddToCalendarMenu({ entry, className }: AddToCalendarMenuProps) {
  const { t } = useTranslation();
  const label = t("calendar.add.menu");

  const openGoogle = () => {
    window.open(googleCalendarUrl(entry), "_blank", "noopener,noreferrer");
  };
  const downloadIcs = () => {
    const blob = new Blob([buildIcs(entry)], { type: "text/calendar;charset=utf-8" });
    downloadBlob(blob, icsFilename(entry));
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={label}
            title={label}
            className={className}
          />
        }
      >
        <CalendarPlus />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        <DropdownMenuGroup>
          <DropdownMenuItem onClick={openGoogle}>
            <ExternalLink />
            {t("calendar.add.google")}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={downloadIcs}>
            <Download />
            {t("calendar.add.ics")}
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
