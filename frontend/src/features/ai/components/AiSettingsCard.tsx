import { useEffect, useId, useState } from "react";
import { ExternalLink, KeyRound, Loader2, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { formatDateTime } from "@/shared/lib/format";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { useAccountZone } from "@/features/auth/hooks/useAccountZone";
import { useChangeAiKeyModel } from "../hooks/mutations/useChangeAiKeyModel";
import { useDeleteAiKey } from "../hooks/mutations/useDeleteAiKey";
import { useRevokeAiConsent } from "../hooks/mutations/useRevokeAiConsent";
import { useSaveAiKey } from "../hooks/mutations/useSaveAiKey";
import { useSetActiveAiProvider } from "../hooks/mutations/useSetActiveAiProvider";
import { useAiConsents } from "../hooks/queries/useAiConsents";
import { useAiKeys } from "../hooks/queries/useAiKeys";
import { AI_SETTINGS_ID, keyPageUrl, providerName } from "../lib/providers";
import type { AiProvider, AiProviderOption } from "../types/Ai";
import { HelpLink } from "@/shared/components/help/HelpLink";

// El valor del selector para los usos gratuitos (un proveedor nunca se llama así).
const PLATFORM = "platform";

/**
 * La IA en Preferencias: con qué se usa (los usos gratuitos o una clave propia),
 * las claves propias (RF-151: se comprueban con el proveedor, se guardan cifradas y
 * nunca se muestran) y los permisos de envío, que se pueden retirar (RF-116).
 */
export function AiSettingsCard() {
  const { t } = useTranslation();
  const keys = useAiKeys();
  const consents = useAiConsents();
  const setActive = useSetActiveAiProvider();
  const revoke = useRevokeAiConsent();
  const usingLabelId = useId();

  const platform = consents.data?.platform_provider ?? null;
  const ownKeys = keys.data?.own_keys_enabled ?? false;
  const loaded = !!keys.data && !!consents.data;
  // Los enlaces de "cómo seguir" (RF-156) traen aquí: la tarjeta se pinta cuando
  // llegan los datos, así que el navegador no puede bajar solo hasta ella.
  useEffect(() => {
    if (loaded && window.location.hash === `#${AI_SETTINGS_ID}`) {
      document.getElementById(AI_SETTINGS_ID)?.scrollIntoView({ block: "start" });
    }
  }, [loaded]);
  // Sin IA en la instalación no hay nada que configurar.
  if (!keys.data || !consents.data || (!platform && !ownKeys)) return null;

  const saved = keys.data.providers.filter((option) => option.key);
  const using = keys.data.active_provider ?? PLATFORM;
  const usingItems = [
    ...(platform
      ? [{ value: PLATFORM, label: t("ai.settings.free", { provider: providerName(platform) }) }]
      : []),
    ...saved.map((option) => ({
      value: option.provider,
      label: t("ai.settings.ownKey", { provider: providerName(option.provider) }),
    })),
  ];
  const granted = consents.data.consents.filter((consent) => consent.granted);
  const onError = (error: unknown) =>
    toast.error(t(errorMessageKey(error), errorMessageParams(error)));

  return (
    <Card id={AI_SETTINGS_ID} className="scroll-mt-20">
      <CardHeader>
        <CardTitle>{t("ai.settings.title")}</CardTitle>
        <CardAction>
          <HelpLink page="ownAiKey" />
        </CardAction>
        <CardDescription>{t("ai.settings.description")}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        {usingItems.length > 0 && (
          <div className="grid gap-2">
            <span id={usingLabelId} className="text-sm font-medium">
              {t("ai.settings.using")}
            </span>
            <Select
              items={usingItems}
              value={using}
              onValueChange={(next) =>
                next !== null &&
                setActive.mutate(next === PLATFORM ? null : (next as AiProvider), { onError })
              }
              disabled={setActive.isPending}
            >
              <SelectTrigger className="w-full sm:w-80" aria-labelledby={usingLabelId}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {usingItems.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {ownKeys && (
          <section className="grid gap-3" aria-labelledby="ai-own-keys">
            <div className="grid gap-1">
              <h3 id="ai-own-keys" className="text-sm font-medium">
                {t("ai.settings.keysTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">{t("ai.settings.keysHint")}</p>
            </div>
            <ul className="grid gap-3">
              {keys.data.providers.map((option) => (
                <ProviderKeyRow key={option.provider} option={option} onError={onError} />
              ))}
            </ul>
          </section>
        )}

        <section className="grid gap-3" aria-labelledby="ai-consents">
          <div className="grid gap-1">
            <h3 id="ai-consents" className="text-sm font-medium">
              {t("ai.settings.consentsTitle")}
            </h3>
            <p className="text-sm text-muted-foreground">{t("ai.settings.consentsHint")}</p>
          </div>
          {granted.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("ai.settings.noConsents")}</p>
          ) : (
            <ul className="grid gap-2">
              {granted.map((consent) => (
                <li
                  key={consent.provider}
                  className="flex flex-wrap items-center justify-between gap-2 text-sm"
                >
                  <span>{providerName(consent.provider)}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={revoke.isPending}
                    onClick={() => revoke.mutate(consent.provider, { onError })}
                  >
                    {t("ai.settings.revoke", { provider: providerName(consent.provider) })}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </CardContent>
    </Card>
  );
}

function ProviderKeyRow({
  option,
  onError,
}: {
  option: AiProviderOption;
  onError: (error: unknown) => void;
}) {
  const { t, i18n } = useTranslation();
  const zone = useAccountZone();
  const [editing, setEditing] = useState(false);
  const changeModel = useChangeAiKeyModel();
  const remove = useDeleteAiKey();
  const name = providerName(option.provider);
  const modelLabelId = useId();
  const key = option.key;

  return (
    <li className="grid gap-3 rounded-lg border p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="grid gap-0.5">
          <span className="font-medium">{name}</span>
          <span className="text-sm text-muted-foreground">
            {key
              ? t("ai.settings.saved", {
                  last4: key.last4,
                  date: formatDateTime(key.validated_at, i18n.language, zone),
                })
              : t("ai.settings.noKey")}
          </span>
          {!key && keyPageUrl(option.provider) && (
            <a
              href={keyPageUrl(option.provider) ?? undefined}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 justify-self-start text-sm text-muted-foreground underline underline-offset-2 hover:text-foreground"
              aria-label={t("ai.settings.getKeyLabel", { provider: name })}
            >
              {t("ai.settings.getKey")}
              <ExternalLink className="size-3.5" aria-hidden />
            </a>
          )}
        </div>
        <div className="flex gap-2">
          {!editing && (
            <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
              <KeyRound />
              {t(key ? "ai.settings.replace" : "ai.settings.add")}
            </Button>
          )}
          {key && !editing && (
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t("ai.settings.delete", { provider: name })}
              disabled={remove.isPending}
              onClick={() =>
                remove.mutate(option.provider, {
                  onSuccess: () => toast.success(t("ai.settings.deleted", { provider: name })),
                  onError,
                })
              }
            >
              <Trash2 />
            </Button>
          )}
        </div>
      </div>

      {key && !editing && (
        <div className="grid gap-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span id={modelLabelId} className="text-sm text-muted-foreground">
              {t("ai.settings.model")}
            </span>
            <ModelSelect
              labelId={modelLabelId}
              models={option.models}
              value={key.model}
              disabled={changeModel.isPending}
              onChange={(model) =>
                changeModel.mutate({ provider: option.provider, model }, { onError })
              }
            />
            {changeModel.isPending && <Loader2 className="size-4 animate-spin" aria-hidden />}
          </div>
          {!key.model_allowed && (
            <p className="text-sm text-amber-800 dark:text-amber-300">
              {t("ai.settings.modelRetired")}
            </p>
          )}
        </div>
      )}

      {editing && <KeyForm option={option} onDone={() => setEditing(false)} onError={onError} />}
    </li>
  );
}

function KeyForm({
  option,
  onDone,
  onError,
}: {
  option: AiProviderOption;
  onDone: () => void;
  onError: (error: unknown) => void;
}) {
  const { t } = useTranslation();
  const save = useSaveAiKey();
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(option.key?.model ?? option.models[0]);
  const inputId = useId();
  const modelLabelId = useId();
  const name = providerName(option.provider);

  return (
    <form
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        save.mutate(
          { provider: option.provider, apiKey, model },
          {
            onSuccess: () => {
              // La clave no se queda en el formulario más de lo necesario.
              setApiKey("");
              toast.success(t("ai.settings.savedToast", { provider: name }));
              onDone();
            },
            onError,
          },
        );
      }}
    >
      <div className="grid gap-2 sm:max-w-md">
        <Label htmlFor={inputId}>{t("ai.settings.keyLabel", { provider: name })}</Label>
        <Input
          id={inputId}
          type="password"
          autoComplete="off"
          spellCheck={false}
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
        />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span id={modelLabelId} className="text-sm text-muted-foreground">
          {t("ai.settings.model")}
        </span>
        <ModelSelect
          labelId={modelLabelId}
          models={option.models}
          value={model}
          onChange={setModel}
        />
      </div>
      <p className="text-xs text-muted-foreground">
        {t("ai.settings.keyNote", { provider: name })}
      </p>
      <div className="flex gap-2">
        <Button type="submit" disabled={!apiKey.trim() || save.isPending}>
          {save.isPending && <Loader2 className="animate-spin" />}
          {t("ai.settings.save")}
        </Button>
        <Button type="button" variant="ghost" onClick={onDone} disabled={save.isPending}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}

function ModelSelect({
  labelId,
  models,
  value,
  disabled,
  onChange,
}: {
  labelId: string;
  models: string[];
  value: string;
  disabled?: boolean;
  onChange: (model: string) => void;
}) {
  // Un modelo retirado de la lista también se ve, para saber cuál era.
  const items = [...new Set([...models, value])].map((model) => ({ value: model, label: model }));
  return (
    <Select
      items={items}
      value={value}
      onValueChange={(next) => next !== null && onChange(next)}
      disabled={disabled}
    >
      <SelectTrigger className="w-56" aria-labelledby={labelId}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {items.map((item) => (
          <SelectItem key={item.value} value={item.value}>
            {item.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
