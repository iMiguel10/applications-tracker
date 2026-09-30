export const notificationKeys = {
  all: ["notifications"] as const,
  unsubscribeLink: (token: string) => [...notificationKeys.all, "unsubscribe", token] as const,
};
