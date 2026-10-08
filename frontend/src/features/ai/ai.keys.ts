export const aiKeys = {
  all: ["ai"] as const,
  consents: () => [...aiKeys.all, "consents"] as const,
  keys: () => [...aiKeys.all, "keys"] as const,
  proposals: (applicationId: string) => [...aiKeys.all, "proposals", applicationId] as const,
  proposal: (applicationId: string, proposalId: string) =>
    [...aiKeys.proposals(applicationId), proposalId] as const,
};
