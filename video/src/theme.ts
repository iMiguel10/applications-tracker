import { loadFont } from "@remotion/google-fonts/Geist";

export const { fontFamily: FONT } = loadFont("normal", {
  weights: ["400", "500", "600", "700"],
  subsets: ["latin"],
});

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

export const COLORS = {
  bg: "#09090b",
  surface: "#151518",
  text: "#fafafa",
  muted: "#a1a1aa",
  primary: "#818cf8",
  primaryStrong: "#4f46e5",
  cyan: "#22d3ee",
  violet: "#a78bfa",
  green: "#34d399",
};

/** Escenas en fotogramas (30 fps). Cambiar la duración de una exige mover las siguientes. */
export const TIMELINE = {
  intro: { from: 0, dur: 150 }, // 0–5 s
  presentation: { from: 150, dur: 210 }, // 5–12 s
  features: { from: 360, dur: 780 }, // 12–38 s
  result: { from: 1140, dur: 360 }, // 38–50 s
  outro: { from: 1500, dur: 300 }, // 50–60 s
} as const;

export const TOTAL_FRAMES = 1800;
/** Fotogramas que se solapan al pasar de una escena a otra (fundido cruzado). */
export const OVERLAP = 12;
export const FEATURE_DUR = 156;

/** Las capturas son de 2000×1250 "unidades de pantalla": todas las coordenadas del vídeo usan esa rejilla. */
export const SHOT = { w: 2000, h: 1250 };
