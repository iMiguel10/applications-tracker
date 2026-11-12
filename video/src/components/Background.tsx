import React from "react";
import { AbsoluteFill, interpolate, random, useCurrentFrame } from "remotion";
import { COLORS, HEIGHT, WIDTH } from "../theme";

const PARTICLES = 70;

/** Fondo persistente: degradados que derivan, rejilla tenue, partículas y viñeta. */
export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const drift = (a: number, b: number, period: number, phase = 0) =>
    a + (b - a) * (0.5 + 0.5 * Math.sin((frame / period) * Math.PI * 2 + phase));

  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(900px 700px at ${drift(15, 35, 600)}% ${drift(20, 40, 520, 1)}%, rgba(79,70,229,0.32), transparent 70%),
            radial-gradient(800px 700px at ${drift(70, 88, 700, 2)}% ${drift(65, 90, 640, 3)}%, rgba(34,211,238,0.16), transparent 70%),
            radial-gradient(700px 600px at ${drift(45, 60, 800, 4)}% ${drift(90, 105, 560)}%, rgba(167,139,250,0.14), transparent 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          opacity: 0.5,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
          backgroundSize: "80px 80px",
          backgroundPosition: `${(frame * 0.15) % 80}px ${(frame * 0.1) % 80}px`,
          maskImage: "radial-gradient(ellipse at center, black 20%, transparent 75%)",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 20%, transparent 75%)",
        }}
      />
      {Array.from({ length: PARTICLES }, (_, i) => {
        const x = random(`px${i}`) * WIDTH;
        const y0 = random(`py${i}`) * HEIGHT;
        const speed = 0.15 + random(`ps${i}`) * 0.5;
        const size = 1.5 + random(`pz${i}`) * 3.5;
        const y = (((y0 - frame * speed) % HEIGHT) + HEIGHT) % HEIGHT;
        const tw = 0.35 + 0.65 * Math.abs(Math.sin(frame / (30 + random(`pt${i}`) * 50) + i));
        const color = i % 3 === 0 ? COLORS.cyan : COLORS.primary;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x + Math.sin(frame / 90 + i) * 12,
              top: y,
              width: size,
              height: size,
              borderRadius: "50%",
              background: color,
              opacity: tw * interpolate(size, [1.5, 5], [0.35, 0.8]),
              filter: size > 3.5 ? "blur(1px)" : undefined,
              boxShadow: `0 0 ${size * 4}px ${color}`,
            }}
          />
        );
      })}
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.55) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};
