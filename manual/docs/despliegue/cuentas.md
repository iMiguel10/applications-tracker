---
title: Crear cuentas
sidebar_label: Cuentas
---

En producción el **registro viene cerrado** (`SIGNUP_ENABLED=false`): la pantalla de inicio de sesión no ofrece crear una cuenta y la página de registro explica que está cerrado. Las cuentas las creas tú con un script. Las que ya existen funcionan igual.

## Crear una cuenta

En el servicio `api`:

- **Coolify:** en el recurso, abre la terminal del servicio `api`. Si la terminal del panel no funciona, por SSH: `docker exec -it $(docker ps --format '{{.Names}}' | grep '^api-') <comando>`.
- **Sin Coolify:** `docker compose -f compose.prod.yml exec api <comando>`.

```bash
python -m app.scripts.create_user ana@example.com
python -m app.scripts.create_user ana@example.com --language en   # cuenta y email en inglés
```

La cuenta se crea con el email ya verificado y con una contraseña aleatoria que nadie conoce. La persona elige la suya con un enlace:

| Instalación | Qué pasa |
|---|---|
| **Con [correo](correo.md)** | Le llega un email («Tu cuenta de Applications Tracker está creada») con el enlace |
| **Sin correo**, o si el envío falla | El script **imprime el enlace** para que se lo pases tú |

El enlace caduca en **60 minutos**. Si caduca, puede pedir otro con **¿Olvidaste tu contraseña?**, siempre que la instalación envíe emails. Sin ellos, borra la cuenta y créala de nuevo.

**Qué debe verse:** el script termina sin error y, abriendo el enlace en el navegador, aparece la pantalla para elegir la contraseña. El script no hace nada si ya existe una cuenta con ese email.

:::note Sin correo, no se puede cambiar la contraseña desde la aplicación
Sin SMTP, una cuenta no puede cambiar ni recuperar su contraseña por sí sola (la aplicación no ofrece el enlace). Si quieres que lo pueda hacer, configura el [correo](correo.md).
:::

## Abrir el registro

Con `SIGNUP_ENABLED=true` (y volviendo a desplegar), cualquiera puede registrarse desde la pantalla de inicio de sesión. Piénsalo antes: cada cuenta usa disco y, si tienes IA de la plataforma, puede gastar sus usos gratuitos. Los [límites por cuenta](variables.md) acotan el daño, pero no lo evitan.

El script `create_user` sigue sirviendo con el registro abierto.
