export const authKeys = {
  all: ["auth"] as const,
  me: () => [...authKeys.all, "me"] as const,
  preferences: () => [...authKeys.all, "preferences"] as const,
  emailVerified: () => [...authKeys.all, "emailVerified"] as const,
};
