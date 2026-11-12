import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, staticFile } from "remotion";
import { Background } from "./components/Background";
import { Features } from "./scenes/Features";
import { Intro } from "./scenes/Intro";
import { Outro } from "./scenes/Outro";
import { Presentation } from "./scenes/Presentation";
import { Result } from "./scenes/Result";
import { FPS, OVERLAP, TIMELINE, TOTAL_FRAMES } from "./theme";

/** Composición principal: fondo y música continuos, y cada escena en su Sequence (con solape para el fundido). */
export const Promo: React.FC = () => {
  const { intro, presentation, features, result, outro } = TIMELINE;
  const seq = (s: { from: number; dur: number }, last = false) => ({
    from: s.from,
    durationInFrames: s.dur + (last ? 0 : OVERLAP),
  });
  return (
    <AbsoluteFill style={{ background: "#09090b" }}>
      <Audio
        src={staticFile("audio/music.wav")}
        volume={(f) =>
          0.7 * interpolate(f, [TOTAL_FRAMES - 4 * FPS, TOTAL_FRAMES], [1, 0], { extrapolateLeft: "clamp" })
        }
      />
      <Background />
      <Sequence {...seq(intro)} name="1 · Intro">
        <Intro />
      </Sequence>
      <Sequence {...seq(presentation)} name="2 · Presentación">
        <Presentation />
      </Sequence>
      <Sequence {...seq(features)} name="3 · Funcionalidades">
        <Features />
      </Sequence>
      <Sequence {...seq(result)} name="4 · Resultado">
        <Result />
      </Sequence>
      <Sequence {...seq(outro, true)} name="5 · Outro">
        <Outro />
      </Sequence>
    </AbsoluteFill>
  );
};
