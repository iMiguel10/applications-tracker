import { useEffect } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { FormActions, FormInput, FormTextarea } from "@/shared/components/form";
import { Button } from "@/shared/components/ui/button";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { useUpdateProfile } from "../hooks/mutations/useUpdateProfile";
import {
  profileBasicsSchema,
  toProfileBasicsForm,
  type ProfileBasicsFormValues,
} from "../schemas/profileBasics.schema";
import { MAX_LINKS, SUMMARY_MAX_LENGTH, type Profile } from "../types/Profile";

type Props = {
  profile: Profile;
  /** Se propone como email de contacto mientras no se haya guardado otro. */
  accountEmail?: string | null;
};

export function ProfileBasicsForm({ profile, accountEmail }: Props) {
  const { t } = useTranslation();
  const update = useUpdateProfile();

  const form = useForm<ProfileBasicsFormValues>({
    resolver: zodResolver(profileBasicsSchema),
    defaultValues: toProfileBasicsForm(profile, accountEmail),
  });
  const links = useFieldArray({ control: form.control, name: "links" });

  // El email de la cuenta llega después que el perfil: se propone sin pisar lo
  // que el usuario ya esté escribiendo.
  useEffect(() => {
    form.reset(toProfileBasicsForm(profile, accountEmail), { keepDirtyValues: true });
  }, [profile, accountEmail, form]);

  const onSubmit = (values: ProfileBasicsFormValues) => {
    update.mutate(values, {
      onSuccess: () => toast.success(t("profile.saved")),
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });
  };

  const summaryLength = useWatch({ control: form.control, name: "summary" })?.length ?? 0;

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-8" noValidate>
      <section className="grid gap-4" aria-labelledby="profile-contact">
        <div>
          <h2 id="profile-contact" className="text-lg font-semibold">
            {t("profile.sections.contact")}
          </h2>
          <p className="text-sm text-muted-foreground">{t("profile.sections.contactHint")}</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <FormInput form={form} name="full_name" label={t("profile.fields.fullName")} autoComplete="name" />
          <FormInput
            form={form}
            name="headline"
            label={t("profile.fields.headline")}
            placeholder={t("profile.placeholders.headline")}
          />
          <FormInput
            form={form}
            name="contact_email"
            type="email"
            label={t("profile.fields.contactEmail")}
            autoComplete="email"
          />
          <FormInput
            form={form}
            name="phone"
            type="tel"
            label={t("profile.fields.phone")}
            autoComplete="tel"
          />
          <FormInput
            form={form}
            name="location"
            label={t("profile.fields.location")}
            placeholder={t("profile.placeholders.location")}
          />
        </div>
      </section>

      <section className="grid gap-4" aria-labelledby="profile-links">
        <div>
          <h2 id="profile-links" className="text-lg font-semibold">
            {t("profile.sections.links")}
          </h2>
          <p className="text-sm text-muted-foreground">{t("profile.sections.linksHint")}</p>
        </div>
        {links.fields.map((link, index) => (
          <div key={link.id} className="grid items-start gap-3 sm:grid-cols-[12rem_1fr_auto]">
            <FormInput
              form={form}
              name={`links.${index}.label`}
              label={t("profile.fields.linkLabel")}
              placeholder="LinkedIn"
            />
            <FormInput
              form={form}
              name={`links.${index}.url`}
              type="url"
              label={t("profile.fields.linkUrl")}
              placeholder="https://"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="sm:mt-7"
              aria-label={t("profile.removeLink", { label: link.label || index + 1 })}
              onClick={() => links.remove(index)}
            >
              <Trash2 aria-hidden />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          className="w-fit"
          disabled={links.fields.length >= MAX_LINKS}
          onClick={() => links.append({ label: "", url: "" })}
        >
          <Plus aria-hidden />
          {t("profile.addLink")}
        </Button>
      </section>

      <section className="grid gap-2" aria-labelledby="profile-summary">
        <h2 id="profile-summary" className="text-lg font-semibold">
          {t("profile.sections.summary")}
        </h2>
        <FormTextarea
          form={form}
          name="summary"
          label={t("profile.fields.summary")}
          placeholder={t("profile.placeholders.summary")}
          rows={6}
        />
        <p className="text-right text-xs text-muted-foreground">
          {t("profile.summaryCount", { count: summaryLength, max: SUMMARY_MAX_LENGTH })}
        </p>
      </section>

      <FormActions loading={update.isPending} submitLabel={t("common.save")} />
    </form>
  );
}
