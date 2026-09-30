export const profileKeys = {
  all: ["profile"] as const,
  detail: () => [...profileKeys.all, "detail"] as const,
  entries: () => [...profileKeys.all, "entries"] as const,
  skills: () => [...profileKeys.all, "skills"] as const,
  languages: () => [...profileKeys.all, "languages"] as const,
};
