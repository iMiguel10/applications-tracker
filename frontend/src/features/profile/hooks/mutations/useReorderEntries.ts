import { useMutation, useQueryClient } from "@tanstack/react-query";
import { profileKeys } from "../../profile.keys";
import { profileService } from "../../services/profile.service";
import type { EntryKind, ProfileEntry } from "../../types/ProfileEntry";

type Reorder = { kind: EntryKind; entryIds: string[] };

/** Reordena una sección. El orden nuevo se ve al soltar, sin esperar a la API; si
 * falla, vuelve el que había. */
export function useReorderEntries() {
  const queryClient = useQueryClient();
  const key = profileKeys.entries();

  return useMutation({
    mutationFn: ({ kind, entryIds }: Reorder) => profileService.reorderEntries(kind, entryIds),
    onMutate: async ({ kind, entryIds }: Reorder) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<ProfileEntry[]>(key);
      if (previous) {
        const position = new Map(entryIds.map((id, index) => [id, index]));
        const others = previous.filter((entry) => entry.kind !== kind);
        const section = previous
          .filter((entry) => entry.kind === kind)
          .sort((a, b) => (position.get(a.id) ?? 0) - (position.get(b.id) ?? 0));
        queryClient.setQueryData(key, [...others, ...section]);
      }
      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous);
    },
    onSuccess: (entries) => queryClient.setQueryData(key, entries),
  });
}
