# 0023 — Producción en Coolify, con un solo dominio y un Nginx propio

- **Fecha:** 2026-10-18
- **Estado:** aceptada

## Contexto

F7 estaba en espera de un VPS ([0009](0009-f8-antes-que-f7.md)). El usuario tiene **Coolify** instalado en un servidor propio, y con eso se retoma. Coolify cambia piezas del diseño previsto:

- Trae su propio proxy (Traefik o Caddy), que pone el HTTPS con Let's Encrypt y publica los puertos 80 y 443. El Nginx previsto ya no tiene que encargarse del TLS.
- Despliega un `docker compose` desde el repositorio y construye las imágenes en el propio servidor.

Además, el diseño de autenticación ([autenticación §5](../arquitectura/autenticacion.md#5-cookies-y-dominios)) preveía dos subdominios, `app.` y `api.`.

## Decisión

Decisiones del usuario, tomadas al empezar F7:

- **Acceso público con dominio**, con el HTTPS de Coolify. Las cookies salen `Secure`.
- **Un solo dominio.** El frontend y la API comparten origen: `/api/` y `/auth/` van a la API por el mismo Nginx. `API_DOMAIN`, `WEBSITE_DOMAIN` y la URL de la API del frontend valen lo mismo, y `CORS_ORIGINS` queda vacío.
- **Un Nginx propio entre los contenedores y el proxy de Coolify** (imagen `web`, `deploy/web/`). Coolify solo pone el HTTPS y le pasa todo el tráfico del dominio. Nginx hace el resto:
  - sirve el frontend y el manual compilados, este en `/manual/`;
  - reparte `/api`, `/auth`, `/docs` y `/openapi.json` a la API;
  - aplica la primera capa del rate limiting ([límites y abuso §2](../arquitectura/limites-y-abuso.md#2-rate-limiting-rnf-04));
  - pone la caché y las cabeceras de seguridad, con la CSP.
- **Ningún contenedor publica puertos en el host**, tampoco Nginx. El proxy de Coolify llega a él por la red de Docker. Aunque fallara el firewall, Postgres, Valkey o SuperTokens nunca quedarían expuestos.
- **Sin correo y sin IA de la plataforma, de momento.** La app ya arranca sin SMTP (RNF-34) y sin IA de la plataforma (solo claves propias). Las dos se activan después con variables.

## Alternativas descartadas

- **Solo el proxy de Coolify, sin Nginx:**
  - el frontend necesita igualmente un servidor web, porque Traefik no sirve ficheros ni resuelve las rutas del SPA;
  - el reparto, el rate limit y las cabeceras irían en labels de Traefik o en el panel de Coolify: menos legibles, imposibles de probar con `nginx -t` en la CI y atados a Coolify.

  Con un Nginx en el repositorio, el mismo `compose.prod.yml` funciona en un VPS sin Coolify y se puede probar en local.
- **Dos subdominios (`app.` y `api.`):** exige CORS entre orígenes y dos rutas en Coolify. No aporta nada mientras la API no tenga otros clientes con dominio propio. Si los tiene algún día, la API sigue accesible en `/api/` del mismo dominio.
- **Construir las imágenes en GitHub Actions y publicarlas en GHCR:** solo compensaría si el servidor fuera justo para construir. Coolify construye en el servidor, y la CI se limita a comprobar que las imágenes de producción construyen.

## Consecuencias

- **La URL se incrusta al compilar.** Vite mete la URL de la API en el JavaScript, así que la imagen `web` va ligada a su dominio (`APP_URL` como argumento de build). Cambiar de dominio exige reconstruirla. Es aceptable con un solo despliegue.
- **Dos proxies encadenados para la IP real** (Coolify → Nginx → API):
  - Nginx se fía de las redes privadas (`set_real_ip_from`), porque solo es alcanzable desde redes de Docker, y toma la IP del cliente de `X-Forwarded-For` de derecha a izquierda;
  - la API solo necesita fiarse de Nginx, con `TRUSTED_PROXIES` igual a la subred del stack.

  Si delante de Coolify se pone un túnel (Cloudflare Tunnel), hay que volver a comprobarlo: el proxy de Coolify podría descartar el `X-Forwarded-For` que trae el túnel.
- **La CSP del frontend solo admite scripts del propio origen.** El script que aplica el tema antes de pintar salió de `index.html` a `public/theme-init.js`.
- **El panel de Coolify queda en la red local.** Un despliegue automático desde GitHub necesitará un runner self-hosted en el servidor (paso 5 de F7) en vez de una llamada directa desde Actions.
- Las cookies `SameSite=Lax` del diseño siguen valiendo: un solo origen es el caso más sencillo de "mismo sitio".
