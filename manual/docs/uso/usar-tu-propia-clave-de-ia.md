---
title: Usar tu propia clave de IA
sidebar_label: Tu propia clave de IA
---

Para [adaptar el CV](adaptar-el-cv-con-ia.md) y [escribir cartas](escribir-una-carta-con-ia.md), la IA puede funcionar de dos formas:

- **Usos gratuitos**: los que ofrece la instalación. Son pocos y no se renuevan.
- **Tu propia clave** de un proveedor de IA (Anthropic, OpenAI o Groq, según lo que permita la instalación): **sin límite de usos**. Cada uso lo pagas en tu cuenta de ese proveedor, normalmente unos céntimos.

Todo se configura en **Preferencias**, en la tarjeta **Inteligencia artificial**. Si no aparece, la instalación no tiene IA.

## Añadir una clave

1. Consigue una clave de API en la web del proveedor. Suele estar en la sección de claves o "API keys" de tu cuenta, y hace falta tener saldo o un método de pago.
2. En **Tus claves**, junto al proveedor, pulsa **Añadir clave**.
3. Pega la clave en **Clave de API de** *proveedor*, elige el **Modelo** (el primero es el recomendado) y pulsa **Comprobar y guardar**.

La aplicación comprueba la clave con el proveedor sin generar texto, así que no tiene coste. Si es válida, la guarda **cifrada** y, desde ese momento, la IA la usa. Nunca se vuelve a mostrar: solo verás sus 4 últimos caracteres (**Clave …abcd**), para reconocerla.

La primera vez que pidas una propuesta con esa clave, la aplicación te pedirá permiso para enviar tus datos a ese proveedor, como con los usos gratuitos.

## Elegir con qué se usa la IA

En **Se usa** eliges entre los **Usos gratuitos** y cada clave que hayas guardado. La tarjeta **Adaptar con IA** de cada solicitud te dice con qué se va a pedir.

Con tu clave, si la llamada falla (clave revocada, sin saldo), la propuesta falla con su motivo: **nunca** se pasa en silencio a los usos gratuitos.

## Cambiar el modelo, la clave o borrarla

- **Modelo**: cámbialo en la lista que hay bajo la clave. Se comprueba que tu clave tiene acceso a él.
- **Cambiar clave**: para sustituirla por otra del mismo proveedor.
- El icono de la papelera borra la clave. Si era la que se usaba, se vuelve a los usos gratuitos. Las propuestas ya hechas se quedan.

Si la instalación deja de ofrecer el modelo que elegiste, verás un aviso: elige otro para seguir usando la clave.

## Retirar un permiso de envío

En **Permisos de envío** están los proveedores a los que has permitido enviar tu perfil y las ofertas. Con **Retirar el permiso a** *proveedor* no se les envía nada más. Si vuelves a usar ese proveedor, se te pedirá de nuevo.

## Si algo sale mal

| Mensaje | Qué significa |
|---|---|
| El proveedor no ha aceptado la clave | La clave no es válida o está revocada. Comprueba que la has copiado entera |
| Tu clave no tiene acceso a ese modelo | Tu cuenta del proveedor no puede usar ese modelo. Elige otro |
| Tu cuenta del proveedor no tiene saldo o ha llegado a su límite | Añade saldo en la web del proveedor |
| No se pudo contactar con el proveedor de IA | El proveedor no respondió. Inténtalo más tarde |
