import { apiClient } from "@/shared/lib/apiClient";
import type { Profile } from "../types/Profile";
import type { EntryInput, EntryKind, ProfileEntry } from "../types/ProfileEntry";
import type { ProfileBasicsFormValues } from "../schemas/profileBasics.schema";
import type { LanguagesFormValues, SkillsFormValues } from "../schemas/skills.schema";
import type { ProfileLanguage, ProfileSkill } from "../types/ProfileSkill";

export const profileService = {
  get: () => apiClient.get<Profile>("/profile"),

  /** Sustituye los datos básicos enteros; un campo vacío se guarda como `null`. */
  update: (values: ProfileBasicsFormValues) => apiClient.put<Profile>("/profile", values),

  /** Todas las entradas, por sección y en su orden (RF-101, RF-102). */
  listEntries: () => apiClient.get<ProfileEntry[]>("/profile/entries"),

  createEntry: (kind: EntryKind, input: EntryInput) =>
    apiClient.post<ProfileEntry>("/profile/entries", { kind, ...input }),

  updateEntry: (id: string, input: EntryInput) =>
    apiClient.put<ProfileEntry>(`/profile/entries/${id}`, input),

  deleteEntry: (id: string) => apiClient.delete<void>(`/profile/entries/${id}`),

  /** El orden nuevo de una sección: todos sus ids. */
  reorderEntries: (kind: EntryKind, entryIds: string[]) =>
    apiClient.put<ProfileEntry[]>("/profile/entries/order", { kind, entry_ids: entryIds }),
};

export const profileSkillService = {
  listSkills: () => apiClient.get<ProfileSkill[]>("/profile/skills"),

  /** La lista entera, en su orden; cada una con `id` conserva su identidad. */
  saveSkills: (values: SkillsFormValues) =>
    apiClient.put<ProfileSkill[]>("/profile/skills", {
      skills: values.skills.map(({ id, ...skill }) => (id ? { id, ...skill } : skill)),
    }),

  listLanguages: () => apiClient.get<ProfileLanguage[]>("/profile/languages"),

  saveLanguages: (values: LanguagesFormValues) =>
    apiClient.put<ProfileLanguage[]>("/profile/languages", {
      languages: values.languages.map(({ id, ...language }) =>
        id ? { id, ...language } : language,
      ),
    }),
};
