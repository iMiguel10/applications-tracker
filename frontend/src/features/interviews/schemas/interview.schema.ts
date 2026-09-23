import { z } from "zod";
import { INTERVIEW_FORMATS, INTERVIEW_OUTCOMES, INTERVIEW_TYPES } from "../types/Interview";

const duration = z
  .string()
  .trim()
  .refine((v) => v === "" || /^\d{1,4}$/.test(v), "interviews.validation.durationNumber");

// Solo formato, para dar respuesta inmediata; la autoridad es el backend.
export const interviewSchema = z.object({
  scheduled_at: z.string().min(1, "interviews.validation.scheduledAtRequired"),
  duration_minutes: duration,
  interviewers: z.string().trim().max(500, "common.validation.tooLong"),
  interview_type: z.enum(INTERVIEW_TYPES).nullable(),
  format: z.enum(INTERVIEW_FORMATS).nullable(),
  // Solo se usa al editar: al crear, el backend fija "pending" (RF-41).
  outcome: z.enum(INTERVIEW_OUTCOMES),
  notes: z.string().max(5000, "common.validation.notesTooLong"),
});

export type InterviewFormValues = z.infer<typeof interviewSchema>;

export const emptyInterviewForm: InterviewFormValues = {
  scheduled_at: "",
  duration_minutes: "",
  interviewers: "",
  interview_type: null,
  format: null,
  outcome: "pending",
  notes: "",
};
