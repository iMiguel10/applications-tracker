import React from "react";
import { Img, staticFile } from "remotion";
import { SHOT } from "../theme";

export type Rect = { x: number; y: number; w: number; h: number };

/** Recorte de una captura: `rect` en unidades de pantalla (2000×1250), `width` en píxeles. */
export const Crop: React.FC<{
  src: string;
  rect: Rect;
  width: number;
  radius?: number;
  style?: React.CSSProperties;
}> = ({ src, rect, width, radius = 14, style }) => {
  const k = width / rect.w;
  return (
    <div
      style={{
        width,
        height: rect.h * k,
        overflow: "hidden",
        borderRadius: radius,
        position: "relative",
        ...style,
      }}
    >
      <Img
        src={staticFile(src)}
        style={{
          position: "absolute",
          width: SHOT.w * k,
          height: SHOT.h * k,
          left: -rect.x * k,
          top: -rect.y * k,
          maxWidth: "none",
        }}
      />
    </div>
  );
};

/** Estilo en porcentaje de un rectángulo en unidades de pantalla, para colocarlo sobre la captura. */
export const box = (r: Rect): React.CSSProperties => ({
  position: "absolute",
  left: `${(r.x / SHOT.w) * 100}%`,
  top: `${(r.y / SHOT.h) * 100}%`,
  width: `${(r.w / SHOT.w) * 100}%`,
  height: `${(r.h / SHOT.h) * 100}%`,
});
