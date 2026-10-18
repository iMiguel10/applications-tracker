# Imagen `web` de producción (F7): el frontend y el manual compilados, servidos por
# Nginx, que además reparte /api y /auth a la API. Se construye desde la RAÍZ del
# repositorio (compose.prod.yml, context: .): el manual necesita
# docs/referencia/openapi.json, que está fuera de manual/.

# Origen público de la instalación, sin barra final (https://tracker.example.com).
# El frontend y la API comparten dominio (0023), así que es también la URL de la API.
ARG APP_URL


FROM node:24-alpine AS app
ARG APP_URL
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Vite incrusta la URL al compilar: cambiar de dominio exige reconstruir la imagen.
RUN test -n "$APP_URL" || (echo "Falta el argumento APP_URL" >&2 && exit 1)
ENV VITE_API_URL=$APP_URL
RUN npm run build


FROM node:24-alpine AS manual
ARG APP_URL
WORKDIR /app/manual
COPY manual/package.json manual/package-lock.json ./
RUN npm ci
COPY manual/ ./
COPY docs/referencia/openapi.json /app/docs/referencia/openapi.json
# Servido bajo /manual/ por el mismo Nginx (servicios y estructura §9). Los
# ejemplos de la referencia de la API apuntan a la propia instalación.
ENV MANUAL_URL=$APP_URL \
    MANUAL_BASE_URL=/manual/ \
    MANUAL_API_URL=$APP_URL
RUN npm run build


FROM nginx:1.29-alpine
# El fichero de la imagen oficial escucha en el 80 con su propia raíz: se sustituye.
RUN rm /etc/nginx/conf.d/default.conf
COPY deploy/web/nginx.conf /etc/nginx/conf.d/app.conf
COPY --from=app /app/frontend/dist /usr/share/nginx/html
COPY --from=manual /app/manual/build /usr/share/nginx/html/manual
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/healthz || exit 1
