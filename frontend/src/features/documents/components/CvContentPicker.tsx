import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";
import { Checkbox } from "@/shared/components/ui/checkbox";
import type { Profile } from "@/features/profile/types/Profile";
import type { EntryKind, ProfileEntry } from "@/features/profile/types/ProfileEntry";
import type { ProfileLanguage, ProfileSkill } from "@/features/profile/types/ProfileSkill";
import { toggleItem, toggleSection, type CvSelectionState } from "../lib/cvSelection";
import { CV_SECTIONS, type CvSection } from "../types/Document";

interface CvContentPickerProps {
  profile: Profile;
  entries: ProfileEntry[];
  skills: ProfileSkill[];
  languages: ProfileLanguage[];
  value: CvSelectionState;
  onChange: (value: CvSelectionState) => void;
}

/**
 * Qué secciones y elementos del perfil entran en el CV (RF-103). Una sección
 * desmarcada deja sus elementos deshabilitados (no salen, se marquen o no). Una
 * sección sin nada en el perfil no se ofrece: no saldría en el CV.
 */
export function CvContentPicker({
  profile,
  entries,
  skills,
  languages,
  value,
  onChange,
}: CvContentPickerProps) {
  const { t } = useTranslation();

  const itemsOf = (section: CvSection): { id: string; label: string; children?: Item[] }[] => {
    switch (section) {
      case "summary":
        return [];
      case "skills":
        return skills.map((skill) => ({ id: skill.id, label: skill.name }));
      case "languages":
        return languages.map((language) => ({ id: language.id, label: language.language }));
      default:
        return entries
          .filter((entry) => entry.kind === (section as EntryKind))
          .map((entry) => ({
            id: entry.id,
            label: [entry.title, entry.organization].filter(Boolean).join(" · "),
            children: entry.bullets.map((bullet) => ({ id: bullet.id, label: bullet.text })),
          }));
    }
  };

  const available = CV_SECTIONS.filter((section) =>
    section === "summary" ? Boolean(profile.summary) : itemsOf(section).length > 0,
  );

  if (available.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("documents.generate.emptyProfile")}</p>;
  }

  const isOn = (id: string) => !value.excluded.has(id);

  return (
    <ul className="grid gap-3">
      {available.map((section) => {
        const sectionOn = value.sections.has(section);
        return (
          <li key={section} className="grid gap-2 rounded-lg border p-3">
            <CheckRow
              checked={sectionOn}
              onChange={() => onChange(toggleSection(value, section))}
              className="font-medium"
            >
              {t(`documents.generate.sections.${section}`)}
            </CheckRow>
            {itemsOf(section).length > 0 && (
              <ul className="grid gap-1.5 pl-6">
                {itemsOf(section).map((item) => (
                  <li key={item.id} className="grid gap-1.5">
                    <CheckRow
                      checked={sectionOn && isOn(item.id)}
                      disabled={!sectionOn}
                      onChange={() => onChange(toggleItem(value, item.id))}
                    >
                      {item.label}
                    </CheckRow>
                    {item.children && item.children.length > 0 && (
                      <ul className="grid gap-1.5 pl-6">
                        {item.children.map((child) => (
                          <li key={child.id}>
                            <CheckRow
                              checked={sectionOn && isOn(item.id) && isOn(child.id)}
                              disabled={!sectionOn || !isOn(item.id)}
                              onChange={() => onChange(toggleItem(value, child.id))}
                              className="text-muted-foreground"
                            >
                              <span className="line-clamp-2">{child.label}</span>
                            </CheckRow>
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}

interface Item {
  id: string;
  label: string;
}

function CheckRow({
  checked,
  disabled,
  onChange,
  className,
  children,
}: {
  checked: boolean;
  disabled?: boolean;
  onChange: () => void;
  className?: string;
  children: ReactNode;
}) {
  // Base UI enlaza la casilla con el texto del <label> que la envuelve
  // (aria-labelledby): así tiene nombre accesible sin un id propio.
  return (
    <label
      className={cn(
        "flex items-start gap-2 text-sm",
        disabled ? "opacity-50" : "cursor-pointer",
        className,
      )}
    >
      <Checkbox
        checked={checked}
        disabled={disabled}
        onCheckedChange={onChange}
        className="mt-0.5"
      />
      <span className="min-w-0">{children}</span>
    </label>
  );
}
