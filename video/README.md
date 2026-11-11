# Vídeo promocional

Vídeo de 60 s (1920×1080, 30 fps) de Applications Tracker hecho con [Remotion](https://www.remotion.dev/). No forma parte de la aplicación ni de su CI: es un proyecto aparte con su propio `package.json`.

## Preparación (una vez)

```bash
cd video
npm install
npm run audio          # genera la música y los efectos en public/audio/ (sin derechos de autor)
```

Las capturas no se versionan (`capturas/` está fuera de git). Cópialas a `public/shots/` con estos nombres, que son los que usa `src/content.ts`:

```
13-dashboard-oscuro.png   14-tablero-oscuro.png   15-detalle-oscuro.png
16-cv-con-ia-oscuro.png   07-carta-con-ia.png     08b-calendario-semana.png
17-movil-dashboard.png    19-movil-detalle.png    20-movil-calendario.png
```

El logo (`public/logo.png`) sí está versionado: es una copia de `frontend/public/brand/logo.png`.

## Uso

```bash
npm run studio         # vista previa con línea de tiempo
npm run render         # genera out/promo.mp4
npm run typecheck
```

## Qué editar

| Quiero cambiar… | Fichero |
|---|---|
| Textos, capturas y cifras | `src/content.ts` |
| Duración de cada escena, colores, tipografía | `src/theme.ts` |
| Zooms de cámara y marcos de cada plano de funcionalidades | `src/scenes/Features.tsx` (`SHOTS`) |
| Música y efectos de sonido | `scripts/generate-audio.mjs` |

Cada escena es un componente en `src/scenes/` (Intro, Presentation, Features, Result, Outro) y `src/Promo.tsx` las une. Las coordenadas de zoom y de los marcos están en unidades de pantalla de 2000×1250 sobre la captura.

El MP4 no se sube al repositorio: se publica como adjunto de una release de GitHub.
