---
title: Tus obligaciones como responsable
sidebar_label: Obligaciones como responsable
---

Quien despliega una instalación y da cuentas a otras personas es el **responsable del tratamiento** de sus datos (RGPD). El autor del software no lo es: no ve tu instalación ni sus datos. Esta página resume qué te toca y qué te da hecho la aplicación.

:::caution No es asesoramiento legal
Es una guía orientativa con el RGPD y la normativa española como referencia. Si tu instalación tiene usuarios reales fuera de tu círculo, revísalo con alguien que conozca tu caso.
:::

## Cuándo te aplica

- **Solo para ti** (o para usos domésticos): el RGPD no se aplica a la actividad exclusivamente personal (art. 2.2.c). Puedes saltarte esta página.
- **Das cuentas a otras personas**, aunque sea gratis o a amigos: eres responsable de sus datos y lo que sigue te aplica.

## Qué datos trata la aplicación

| Datos | Dónde | Cuánto se guardan |
|---|---|---|
| Email y contraseña (cifrada con un hash) | Base de datos de SuperTokens | Hasta que se borra la cuenta |
| Solicitudes, empresas, historial, entrevistas, recordatorios y notas | Base de datos de la aplicación | Hasta que la persona los borra o borra la cuenta |
| Perfil profesional (con datos de contacto) | Base de datos de la aplicación | Ídem |
| PDF subidos y generados | Volumen `files_data` | Ídem |
| Preferencias (idioma, zona horaria, avisos) | Base de datos de la aplicación | Hasta que se borra la cuenta |
| Propuestas de IA (el texto generado, tokens y coste) y consentimientos | Base de datos de la aplicación | Hasta que se borra la cuenta (si se borra la solicitud, la propuesta queda sin ella, como registro de uso) |
| Claves de IA propias | Base de datos de la aplicación, **cifradas** | Hasta que la persona la quita o borra la cuenta |
| Registro de avisos enviados | Base de datos de la aplicación | 90 días tras enviarse (algunos, mientras la solicitud siga sin actividad) |
| IP y email de los intentos (límite de peticiones) | Valkey | Minutos u horas, lo que dura cada ventana |
| IP, dirección pedida y navegador de cada petición | Logs de los contenedores (`web`, `api`) | Lo que guarde Docker o Coolify: configura su rotación |
| Copias de seguridad de todo lo anterior | Carpeta del servidor y, si la configuras, fuera | 7 diarias y 4 semanales (unas 5 semanas); fuera, lo que digas tú |

Además, el navegador guarda la cookie de sesión y, sin cookies, el tema, el idioma y alguna preferencia de la interfaz. No hay analítica ni cookies de terceros.

## Registro de actividades de tratamiento

El RGPD pide llevar un registro de lo que haces con los datos (art. 30). Con menos de 250 empleados solo es obligatorio si el tratamiento no es ocasional, y una aplicación en uso no lo es: llévalo. Puedes partir de esta tabla, con tus datos de responsable arriba (nombre y contacto) y la fecha:

| Tratamiento | Finalidad | Base jurídica | Datos | Conservación |
|---|---|---|---|---|
| Cuentas y uso de la aplicación | Prestar el servicio | Contrato (art. 6.1.b) | Email, contraseña, datos de la búsqueda, perfil, documentos, preferencias | Hasta que se borra la cuenta, más las copias |
| Avisos por email | Recordatorios, entrevistas, resumen y propuestas listas | Contrato: es una función del servicio que cada persona apaga en **Avisos por email** | Email y lo que dice el aviso | Registro de envíos: 90 días |
| IA | Adaptar el CV y escribir cartas | Consentimiento (art. 6.1.a): la aplicación lo pide por proveedor antes de enviar nada y lo guarda | Perfil **sin datos de contacto** y la descripción de la oferta | Propuestas: hasta que se borra la cuenta |
| Seguridad | Frenar abusos y ataques (límite de peticiones, logs) | Interés legítimo (art. 6.1.f) | IP, email de los intentos, peticiones | Minutos en Valkey; logs según su rotación |
| Copias de seguridad | Recuperar los datos si algo falla | Interés legítimo y deber de seguridad (art. 32) | Todo lo anterior | Unas 5 semanas en el servidor; fuera, lo que digas |

## Encargados del tratamiento

Cada servicio externo que recibe datos por ti es un **encargado** y necesitas un contrato de encargo con él (art. 28). Los grandes proveedores lo incluyen en sus condiciones (busca *DPA* o *Data Processing Agreement*). Depende de lo que actives:

| Servicio | Cuándo | Qué recibe | Qué revisar |
|---|---|---|---|
| Alojamiento (VPS, nube) | Si el servidor no es tuyo | Todo | Su DPA y en qué país están los datos |
| Correo (SMTP) | Con [correo](correo.md) | El email de cada persona y el contenido de sus avisos | Su DPA |
| IA de la plataforma: Anthropic, OpenAI o Groq | Con [IA de la plataforma](ia-de-la-plataforma.md) | El perfil sin datos de contacto y la oferta | Su DPA, que no usen los datos de la API para entrenar y la **transferencia a EE. UU.** (Marco de Privacidad de Datos UE-EE. UU. o cláusulas contractuales tipo) |
| Ollama | Si está en un servidor de otro | Lo mismo | Un Ollama en un equipo tuyo no es un encargado: no sale nada |
| Almacén de las copias de fuera (S3, R2, un NAS ajeno) | Con `BACKUP_RCLONE_REMOTE` | Todo | Su DPA. [Cifrarlas](copias-de-seguridad.md#cifrar-las-copias-de-fuera) reduce mucho el riesgo |

Con **claves propias**, la persona usa su propia cuenta del proveedor: el contrato es suyo, no tuyo. Aun así, la aplicación envía sus datos allí, y tu política de privacidad debe decirlo.

## Informar a tus usuarios

Cada persona debe saber quién eres, qué datos tratas, para qué, con quién los compartes, cuánto los guardas y cómo ejercer sus derechos (arts. 13 y 14): es la **política de privacidad**. Si ofreces el servicio a otras personas, también necesitas un **aviso legal** con tus datos (LSSI-CE, art. 10) y unos **términos**.

La aplicación las trae, en español y en inglés: **Aviso legal**, **Privacidad**, **Términos** y **Cookies**, en `/legal/…`. Para activarlas:

1. Pon tus datos en las [variables de textos legales](variables.md#textos-legales): como mínimo `LEGAL_OPERATOR_NAME` y `LEGAL_CONTACT_EMAIL`.
2. Vuelve a desplegar.
3. **Léelas** (por ejemplo, `https://tracker.example.com/legal/privacy`) y comprueba que encajan con tu caso.

**Qué debe verse:** los enlaces a las cuatro páginas aparecen bajo el formulario de inicio de sesión y al pie de la aplicación, y al entrar, cada cuenta ve **Antes de seguir** hasta aceptar los términos y la privacidad. En el registro, si está abierto, hay que marcar la casilla para crear la cuenta. Se guarda qué versión aceptó cada uno y cuándo.

Los textos se montan con lo que tiene activa tu instalación: nombran el correo solo si lo tienes, el proveedor de la IA de la plataforma y la transferencia a EE. UU. si es Anthropic, OpenAI o Groq (no con Ollama), los proveedores de claves propias que ofreces y los días que un dato borrado sigue en las copias (de `BACKUP_KEEP_DAILY` y `BACKUP_KEEP_WEEKLY`). Están pensados para España (LSSI, RGPD y la AEPD); con `LEGAL_SUPERVISORY_AUTHORITY` puedes nombrar otra autoridad. Son una base: si tu caso tiene algo más (cobras por el servicio, tratas otros datos), escribe tus propios textos y publícalos tú.

Cuando una actualización de la aplicación cambia los textos de forma importante, cambia su versión y todas las cuentas vuelven a ver **Antes de seguir**.

En España, el consentimiento de un menor solo vale desde los **14 años** (LOPDGDD, art. 7): no des cuentas a menores de esa edad.

## Atender los derechos

Tienes **un mes** para responder a cada petición, ampliable dos más en casos complejos (art. 12.3). Comprueba antes que la pide la titular, por ejemplo que llega desde el email de la cuenta.

| Derecho | Cómo |
|---|---|
| **Acceso y portabilidad** (arts. 15 y 20) | La persona descarga todo en **Preferencias › Tus datos**. Si no puede entrar, lo generas tú con [`export_user`](cuentas.md#exportar-los-datos-de-una-cuenta) |
| **Rectificación** (art. 16) | Corrige sus datos en la aplicación. El email lo cambias tú con [`change_email`](cuentas.md#cambiar-el-email-de-una-cuenta) |
| **Supresión** (art. 17) | **Eliminar cuenta**, en Preferencias: lo borra todo al momento. En las copias sigue unas 5 semanas, hasta que caducan; díselo si te lo pregunta |
| **Retirar el consentimiento y oposición** (arts. 7.3 y 21) | Apaga cada aviso en **Avisos por email** y la IA con **Retirar el permiso a…** en la tarjeta **Inteligencia artificial** |
| **Limitación** (art. 18) | La aplicación no tiene una función para bloquear una cuenta sin borrarla: resuélvelo caso a caso |

Si no atiendes una petición, la persona puede reclamar ante la autoridad de control (en España, la [AEPD](https://www.aepd.es)).

## Seguridad

La aplicación trae de serie HTTPS, contraseñas con hash, límites de peticiones, sesiones que caducan, claves de IA cifradas y [copias de seguridad](copias-de-seguridad.md) diarias. Lo que te toca a ti (art. 32):

- Mantén el servidor y la aplicación [actualizados](actualizar.md).
- Guarda los secretos **fuera del servidor**, en un gestor de contraseñas.
- **Cifra las copias que salen del servidor** y, si alguien más puede llegar físicamente al equipo, el disco.
- Configura la **rotación de los logs** de Docker o Coolify: llevan IPs.
- Comprueba de vez en cuando que las copias se pueden restaurar.

## Si hay una brecha de seguridad

Una brecha es cualquier acceso, pérdida o filtración de datos personales: un servidor comprometido, una copia expuesta, un portátil perdido con un `.env`.

1. **Contén.** Cambia los secretos comprometidos en las [variables](variables.md) y vuelve a desplegar. Para las claves de IA, añade una clave nueva a `AI_KEYS_ENCRYPTION_KEYS` y ejecuta `python -m app.scripts.rotate_ai_keys` en `api`. Si los datos se alteraron, [restaura](copias-de-seguridad.md#restaurar) una copia anterior.
2. **Notifica a la autoridad de control en 72 horas** desde que lo sepas (art. 33), salvo que sea improbable que suponga un riesgo para las personas. En España, en la sede electrónica de la AEPD.
3. **Avisa a las personas afectadas** sin demora si el riesgo es alto (art. 34), con qué ha pasado y qué deben hacer (por ejemplo, cambiar su contraseña y la de otros sitios donde usen la misma).
4. **Anótala** con lo que pasó, sus efectos y lo que hiciste, también si no la notificas (art. 33.5).

## La IA

- **No es un sistema de alto riesgo** según el Reglamento de IA de la UE, en nuestra lectura: los de alto riesgo en el empleo son los que usa quien contrata para seleccionar o evaluar a candidatos. Aquí es la propia candidata la que la usa, sobre sus datos, y decide qué envía.
- **Transparencia:** la persona pide cada propuesta, ve qué modelo la generó y revisa cada cambio antes de crear el PDF. Nada sale sin que lo acepte.
- **Minimización:** la IA nunca recibe los datos de contacto del perfil (nombre, email, teléfono, ubicación ni enlaces), y solo con consentimiento previo para cada proveedor.
