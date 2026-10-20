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

:::note Sin correo, la contraseña olvidada no se puede recuperar
Sin SMTP, cada persona puede **cambiar** su contraseña desde **Preferencias** escribiendo la actual, pero no **recuperarla** si la olvida: no hay enlace que enviar. Entonces hay que borrar su cuenta y crearla de nuevo con el script, o configurar el [correo](correo.md).
:::

## Abrir el registro

Con `SIGNUP_ENABLED=true` (y volviendo a desplegar), cualquiera puede registrarse desde la pantalla de inicio de sesión. Piénsalo antes: cada cuenta usa disco y, si tienes IA de la plataforma, puede gastar sus usos gratuitos. Los [límites por cuenta](variables.md) acotan el daño, pero no lo evitan.

El script `create_user` sigue sirviendo con el registro abierto.

## Cuenta de demostración

Para que otras personas prueben la aplicación sin que les des una cuenta, puedes mantener una cuenta pública (`demo@example.com`) con una contraseña que todos conocen. Como cualquiera puede ensuciarla, **se vuelve a crear de cero cada día**.

1. Añade la variable `DEMO_PASSWORD` (la contraseña que quieras publicar) y vuelve a desplegar.
2. Crea la cuenta por primera vez, en la terminal del servicio `api`:

    ```bash
    python -m app.scripts.reset_demo
    ```

3. Programa el mismo comando cada día. En Coolify: en el recurso, **Scheduled Tasks** → añade una tarea con el comando `python -m app.scripts.reset_demo`, el contenedor `api` y la frecuencia `0 4 * * *`. Sin Coolify, una entrada de `cron` en el servidor: `0 4 * * * docker compose -f compose.prod.yml exec -T api python -m app.scripts.reset_demo`.

Cada ejecución **borra la cuenta entera** (solicitudes, documentos, perfil, claves de IA, sesiones abiertas) y la crea de nuevo con el email ya verificado, esa contraseña y estos límites: 15 solicitudes, 10 empresas, 10 recordatorios, 3 documentos, 2 MB de almacenamiento y **ninguna** propuesta de IA. Los avisos por email quedan apagados. Quien tenga la sesión abierta en ese momento la pierde. Con `--email` y `--language` puedes cambiar la dirección y el idioma.

**Qué debe verse:** el script imprime `Cuenta de demostración … lista`, puedes entrar con `demo@example.com` y la contraseña, y **Preferencias** muestra el uso de la cuenta con esos límites.

:::caution La contraseña es pública
No pongas datos reales en esa cuenta. Si alguien cambia su contraseña, queda así hasta el siguiente reseteo. El servidor de la hora de Coolify puede estar en UTC: ajusta el cron si te importa la hora local.
:::
