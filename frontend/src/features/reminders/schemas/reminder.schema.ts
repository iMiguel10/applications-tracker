import { z } from "zod";

export const reminderSchema = z.object({
  title: z
    .string()
    .trim()
    .min(1, "reminders.validation.titleRequired")
    .max(200, "common.validation.tooLong"),
  due_at: z.string().min(1, "reminders.validation.dueAtRequired"),
});

export type ReminderFormValues = z.infer<typeof reminderSchema>;

export const emptyReminderForm: ReminderFormValues = { title: "", due_at: "" };
