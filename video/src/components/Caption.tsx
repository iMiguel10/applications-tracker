import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";

/** Subtítulo en una píldora de cristal, en la parte baja del encuadre. */
export const Caption: React.FC<{ text: string; at: number; hideAt: number }> = ({
  text,
  at,
  hideAt,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - at, fps, config: { damping: 200 } });
  const out = interpolate(frame, [hideAt, hideAt + 10], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 54,
        display: "flex",
        justifyContent: "center",
        opacity: p * out,
        transform: `translateY(${(1 - p) * 24}px)`,
      }}
    >
      <div
        style={{
          fontFamily: FONT,
          fontSize: 30,
          fontWeight: 500,
          color: COLORS.text,
          padding: "16px 34px",
          borderRadius: 999,
          background: "rgba(24,24,27,0.72)",
          border: "1px solid rgba(255,255,255,0.12)",
          backdropFilter: "blur(14px)",
          boxShadow: "0 10px 40px rgba(0,0,0,0.45)",
        }}
      >
        {text}
      </div>
    </div>
  );
};
