import React from "react";
import { Img, staticFile } from "remotion";

/** Teléfono con una captura de 780×1688 dentro. */
export const PhoneMockup: React.FC<{ src: string; width: number; style?: React.CSSProperties }> = ({
  src,
  width,
  style,
}) => {
  const bezel = Math.round(width * 0.035);
  const inner = width - bezel * 2;
  const innerH = (inner * 1688) / 780;
  return (
    <div
      style={{
        width,
        padding: bezel,
        boxSizing: "border-box",
        borderRadius: width * 0.14,
        background: "linear-gradient(145deg, #3f3f46, #18181b)",
        border: "1px solid rgba(255,255,255,0.18)",
        boxShadow: "0 50px 90px rgba(0,0,0,0.6), 0 0 60px rgba(79,70,229,0.25)",
        position: "relative",
        ...style,
      }}
    >
      <div style={{ width: inner, height: innerH, borderRadius: width * 0.105, overflow: "hidden" }}>
        <Img src={staticFile(src)} style={{ width: "100%", height: "100%", display: "block" }} />
      </div>
      <div
        style={{
          position: "absolute",
          top: bezel + 6,
          left: "50%",
          width: width * 0.2,
          height: width * 0.045,
          marginLeft: -width * 0.1,
          borderRadius: 99,
          background: "#000",
        }}
      />
    </div>
  );
};
