/** Las entrevistas siempre se piden dentro de una solicitud: no hay detail() propio. */
export const interviewKeys = {
  all: (applicationId: string) => ["applications", applicationId, "interviews"] as const,
};
