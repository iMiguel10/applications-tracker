import type { ApplicationListParams } from "./types/Application";

export const applicationKeys = {
  all: ["applications"] as const,
  lists: () => [...applicationKeys.all, "list"] as const,
  list: (params: ApplicationListParams) => [...applicationKeys.lists(), params] as const,
};
