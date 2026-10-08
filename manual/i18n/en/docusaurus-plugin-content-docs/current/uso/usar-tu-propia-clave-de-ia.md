---
title: Use your own AI key
sidebar_label: Your own AI key
---

To [tailor your CV](adaptar-el-cv-con-ia.md) and [write cover letters](escribir-una-carta-con-ia.md), the AI can work in two ways:

- **Free uses**: the ones the installation offers. There are usually few and they don't renew.
- **Your own key** from an AI provider (Anthropic, OpenAI or Groq, depending on what the installation allows): **no usage limit**. You pay for each use in your account with that provider, usually a few cents.

Everything is set up in **Preferences**, in the **Artificial intelligence** card. If it doesn't appear, the installation has no AI.

## Add a key

1. Get an API key on the provider's website. It is usually in the keys or "API keys" section of your account, and you need credit or a payment method.
2. In **Your keys**, next to the provider, click **Add key**.
3. Paste the key in *provider* **API key**, choose the **Model** (the first one is the recommended one) and click **Check and save**.

The application checks the key with the provider without generating text, so it costs nothing. If it is valid, it is stored **encrypted** and, from then on, the AI uses it. It is never shown again: you only see its last 4 characters (**Key …abcd**), to recognise it.

The first time you ask for a proposal with that key, the application asks for your permission to send your data to that provider, as with the free uses.

## Choose what the AI uses

In **In use** you choose between the **Free uses** and each key you have saved. The **Tailor with AI** card of each application tells you what it will use.

With your key, if the call fails (revoked key, no credit), the proposal fails with its reason: it **never** silently switches to the free uses.

## Change the model, the key or delete it

- **Model**: change it in the list under the key. It checks that your key has access to it.
- **Change key**: to replace it with another key from the same provider.
- The bin icon deletes the key. If it was the one in use, the AI goes back to the free uses. Proposals already made are kept.

If the installation stops offering the model you chose, you'll see a warning: choose another to keep using the key.

## Revoke a sending permission

**Sending permissions** lists the providers you have allowed to receive your profile and job descriptions. With **Revoke permission for** *provider*, nothing else is sent to them. If you use that provider again, you'll be asked again.

## If something goes wrong

| Message | What it means |
|---|---|
| The provider didn't accept the key | The key isn't valid or has been revoked. Check that you copied all of it |
| Your key doesn't have access to that model | Your provider account can't use that model. Choose another |
| Your provider account has no credit left or has reached its limit | Add credit on the provider's website |
| The AI provider couldn't be reached | The provider didn't answer. Try again later |
