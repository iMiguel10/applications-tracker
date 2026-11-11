import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

/** Texto que sube palabra a palabra desde detrás de una máscara. */
export const MaskedWords: React.FC<{
  text: string;
  delay?: number;
  stagger?: number;
  style?: React.CSSProperties;
  exitAt?: number; // fotograma en que empieza a salir (opcional)
  wordStyle?: React.CSSProperties; // p. ej. degradado de texto: debe ir en la palabra, no en el contenedor
}> = ({ text, delay = 0, stagger = 4, style, exitAt, wordStyle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const lines = text.split("\n");
  let index = 0;
  return (
    <div style={style}>
      {lines.map((line, li) => (
        <div key={li}>
          {line.split(" ").map((word) => {
            const i = index++;
            const enter = spring({
              frame: frame - delay - i * stagger,
              fps,
              config: { damping: 200, mass: 0.9 },
            });
            const exit =
              exitAt === undefined
                ? 0
                : interpolate(frame - exitAt - i * 2, [0, 14], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  });
            return (
              <span
                key={i}
                style={{
                  display: "inline-block",
                  overflow: "hidden",
                  verticalAlign: "top",
                  paddingBottom: "0.12em",
                  marginRight: "0.28em",
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    transform: `translateY(${(1 - enter) * 110 - exit * 110}%)`,
                    opacity: Math.min(1, enter * 2) * (1 - exit),
                    ...wordStyle,
                  }}
                >
                  {word}
                </span>
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};

/** Aparición con desplazamiento y fundido. */
export const FadeUp: React.FC<{
  children: React.ReactNode;
  delay?: number;
  distance?: number;
  style?: React.CSSProperties;
}> = ({ children, delay = 0, distance = 30, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - delay, fps, config: { damping: 200 } });
  return (
    <div style={{ ...style, opacity: p, transform: `translateY(${(1 - p) * distance}px)` }}>
      {children}
    </div>
  );
};
