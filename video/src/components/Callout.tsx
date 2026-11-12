import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../theme";
import { box, Rect } from "./Crop";

/** Marco luminoso que llama la atención sobre una zona de la captura (usar dentro de <Camera>). */
export const Callout: React.FC<{ rect: Rect; at: number; hideAt?: number; radius?: number }> = ({
  rect,
  at,
  hideAt,
  radius = 14,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - at, fps, config: { damping: 18, stiffness: 120 } });
  const out = hideAt === undefined ? 1 : Math.max(0, 1 - (frame - hideAt) / 10);
  if (frame < at || out <= 0) return null;
  const pulse = 0.5 + 0.5 * Math.sin((frame - at) / 7);
  return (
    <div
      style={{
        ...box(rect),
        borderRadius: radius,
        border: `3px solid ${COLORS.primary}`,
        boxShadow: `0 0 ${18 + pulse * 22}px ${COLORS.primary}aa, inset 0 0 24px ${COLORS.primary}33`,
        transform: `scale(${0.94 + 0.06 * p})`,
        opacity: p * out,
        pointerEvents: "none",
      }}
    />
  );
};
