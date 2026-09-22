import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import {
  createApplicationSchema,
  type CreateApplicationFormValues,
} from "../schemas/application.schema";
import { useCreateApplication } from "../hooks/mutations/useCreateApplication";

export function CreateApplicationForm() {
  const { t } = useTranslation();
  const createApplication = useCreateApplication();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateApplicationFormValues>({
    resolver: zodResolver(createApplicationSchema),
    defaultValues: { position_title: "", company_name: "" },
  });

  const onSubmit = (values: CreateApplicationFormValues) =>
    createApplication.mutate(values, {
      onSuccess: () => {
        reset();
        toast.success(t("applications.created"));
      },
      onError: () => toast.error(t("applications.createError")),
    });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 rounded-lg border p-4" noValidate>
      <div className="grid gap-2">
        <Label htmlFor="position_title">{t("applications.fields.position")}</Label>
        <Input
          id="position_title"
          aria-invalid={!!errors.position_title}
          {...register("position_title")}
        />
        {errors.position_title?.message && (
          <p className="text-sm text-destructive">{t(errors.position_title.message)}</p>
        )}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="company_name">{t("applications.fields.company")}</Label>
        <Input
          id="company_name"
          aria-invalid={!!errors.company_name}
          {...register("company_name")}
        />
        {errors.company_name?.message && (
          <p className="text-sm text-destructive">{t(errors.company_name.message)}</p>
        )}
      </div>

      <Button type="submit" disabled={createApplication.isPending} className="justify-self-start">
        {t("applications.create")}
      </Button>
    </form>
  );
}
