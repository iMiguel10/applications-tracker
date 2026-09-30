import { useMutation, useQueryClient } from "@tanstack/react-query";
import { profileKeys } from "../../profile.keys";
import { profileService } from "../../services/profile.service";
import type { EntryInput, EntryKind } from "../../types/ProfileEntry";

type SaveEntry = { kind: EntryKind; id?: string; input: EntryInput };

/** Crea la entrada si no trae `id`; si lo trae, la sustituye. */
export function useSaveEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ kind, id, input }: SaveEntry) =>
      id ? profileService.updateEntry(id, input) : profileService.createEntry(kind, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: profileKeys.entries() }),
  });
}
