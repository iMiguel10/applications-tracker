import React from "react";
import { Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { SHOT } from "../theme";

export type CameraKey = { f: number; s: number; x: number; y: number };

/** Posición de la cámara en el fotograma dado, interpolando entre fotogramas clave con aceleración suave. */
export const cameraAt = (frame: number, keys: CameraKey[]): CameraKey => {
  if (frame <= keys[0].f) return keys[0];
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i];
    const b = keys[i + 1];
    if (frame < b.f) {
      const t = Easing.inOut(Easing.cubic)((frame - a.f) / (b.f - a.f));
      return {
        f: frame,
        s: interpolate(t, [0, 1], [a.s, b.s]),
        x: interpolate(t, [0, 1], [a.x, b.x]),
        y: interpolate(t, [0, 1], [a.y, b.y]),
      };
    }
  }
  return keys[keys.length - 1];
};

/**
 * Pantalla de `width`×`height` px que enseña una captura con una cámara virtual.
 * Los hijos se colocan en el espacio de la captura (usa `box()`), así que se mueven y escalan con ella.
 */
export const Camera: React.FC<{
  src: string;
  width: number;
  height: number;
  keys: CameraKey[];
  children?: React.ReactNode;
}> = ({ src, width, height, keys, children }) => {
  const frame = useCurrentFrame();
  const c = cameraAt(frame, keys);
  const tx = width / 2 - (c.x / SHOT.w) * width * c.s;
  const ty = height / 2 - (c.y / SHOT.h) * height * c.s;
  return (
    <div style={{ width, height, overflow: "hidden", position: "relative", background: "#09090b" }}>
      <div
        style={{
          position: "absolute",
          width,
          height,
          transformOrigin: "0 0",
          transform: `translate(${tx}px, ${ty}px) scale(${c.s})`,
        }}
      >
        <Img src={staticFile(src)} style={{ width: "100%", height: "100%", display: "block" }} />
        {children}
      </div>
    </div>
  );
};
