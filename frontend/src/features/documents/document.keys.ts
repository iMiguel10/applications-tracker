import type { DocumentListParams } from "./types/Document";

export const documentKeys = {
  all: ["documents"] as const,
  lists: () => [...documentKeys.all, "list"] as const,
  list: (params: DocumentListParams) => [...documentKeys.lists(), params] as const,
  file: (id: string) => [...documentKeys.all, "file", id] as const,
};
