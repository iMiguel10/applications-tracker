# 0026 — Páginas legales por configuración

- **Fecha:** 2026-10-20
- **Estado:** aceptada (issue [#3](https://github.com/iMiguel10/applications-tracker/issues/3))

## Contexto

Cada instalación la despliega una persona distinta, que es la responsable de los datos de sus usuarios. Si da cuentas a otras personas necesita un aviso legal (LSSI-CE), una política de privacidad (RGPD, arts. 13 y 14), unos términos y una política de cookies. La aplicación no tenía ninguna página legal, y el autor del software no puede escribirlas por cada responsable.

## Decisión

Decisiones del usuario:

- **Plantillas en la aplicación, rellenas por configuración.** Los datos del responsable van en variables (`LEGAL_OPERATOR_NAME`, `LEGAL_CONTACT_EMAIL` y, opcionales, `LEGAL_ADDRESS`, `LEGAL_TAX_ID`, `LEGAL_SUPERVISORY_AUTHORITY`) y `GET /meta` los publica junto con lo que la instalación tiene activo (correo, IA de la plataforma, proveedores de claves propias y retención de las copias). El frontend monta cuatro páginas públicas, en español e inglés, en `/legal/:page`, y los textos solo nombran lo que existe.
- **Sin nombre y contacto, uso personal:** ni enlaces ni aceptación. Las páginas siguen en su URL y dicen que no están configuradas, sin inventar datos.
- **Aceptación de todas las cuentas,** también las que ya existían y las creadas por script: una pantalla al entrar (`LegalGate`) mientras la versión aceptada no sea la vigente, y una casilla en el registro. Se guardan versión y fecha (`users.legal_version`, `legal_accepted_at`, `POST /me/legal-acceptance`).
- **Textos para España y la UE** (LSSI, RGPD, AEPD), con la autoridad de control configurable.
- **La versión es del código** (`LEGAL_VERSION`): se sube cuando el contenido cambia de forma que haya que volver a aceptarlo.

## Alternativas descartadas

- **Textos escritos por cada responsable** (un Markdown montado en el contenedor o una URL externa): más flexible, pero casi nadie los escribiría y la aplicación no podría garantizar que dicen la verdad sobre lo que tiene activo. Quien necesite otros puede publicarlos aparte; queda como mejora posible.
- **Enlaces siempre visibles, aunque no estén configuradas:** en una instalación personal solo llevarían a un aviso de «sin configurar».
- **Pedir la aceptación solo a las cuentas nuevas:** las existentes, y las creadas con `create_user`, nunca habrían aceptado nada.
- **Exigir la aceptación en el backend** (rechazar las peticiones de una cuenta sin aceptar): rompería las integraciones por API sin ganar nada; lo que importa es que quede constancia de qué aceptó cada persona y cuándo.
- **Textos genéricos de la UE, sin la LSSI:** se quedarían cortos para el caso real, que es España.

## Consecuencias

- Cambiar los textos de forma importante obliga a subir `LEGAL_VERSION` en el mismo commit (trampa en `CLAUDE.md`), y todas las cuentas vuelven a aceptar.
- Los textos son una base, no asesoramiento legal: el manual pide a quien despliega leerlos y adaptarlos si su caso tiene algo más.
- Un cambio de configuración (activar la IA de la plataforma) cambia el texto de la privacidad sin cambiar la versión: la página dice la verdad, pero no se vuelve a pedir la aceptación. Si importa, quien despliega debe avisar a sus usuarios.
