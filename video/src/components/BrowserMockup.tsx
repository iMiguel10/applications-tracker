import React from "react";
import { COLORS, FONT } from "../theme";

export const CHROME_H = 46;

/** Ventana de navegador. La pantalla interior es `width`×`width/1.6` (formato de las capturas). */
export const BrowserMockup: React.FC<{
  width: number;
  url: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ width, url, children, style }) => (
  <div
    style={{
      width,
      borderRadius: 18,
      overflow: "hidden",
      background: "#18181b",
      border: "1px solid rgba(255,255,255,0.14)",
      boxShadow: `0 60px 120px rgba(0,0,0,0.65), 0 0 90px ${COLORS.primaryStrong}44`,
      ...style,
    }}
  >
    <div
      style={{
        height: CHROME_H,
        display: "flex",
        alignItems: "center",
        gap: 9,
        padding: "0 18px",
        background: "linear-gradient(#27272a, #1c1c1f)",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
        <div key={c} style={{ width: 13, height: 13, borderRadius: "50%", background: c }} />
      ))}
      <div
        style={{
          margin: "0 auto",
          transform: "translateX(-30px)",
          fontFamily: FONT,
          fontSize: 15,
          color: COLORS.muted,
          background: "rgba(0,0,0,0.35)",
          padding: "6px 60px",
          borderRadius: 8,
        }}
      >
        {url}
      </div>
    </div>
    {children}
  </div>
);
