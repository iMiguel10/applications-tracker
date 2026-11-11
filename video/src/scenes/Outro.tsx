import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { MaskedWords } from "../components/Reveal";
import { SceneFade } from "../components/SceneFade";
import { Sfx } from "../components/Sfx";
import { CONTENT } from "../content";
import { COLORS, FONT } from "../theme";

/** 50–60 s · Cierre: logo, nombre y frase final con fundido a negro. */
export const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const logo = spring({ frame: frame - 6, fps, config: { damping: 18, stiffness: 80 } });
  const line = interpolate(frame, [70, 130], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const black = interpolate(frame, [durationInFrames - 50, durationInFrames - 6], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const slowZoom = interpolate(frame, [0, durationInFrames], [1, 1.06]);

  return (
    <SceneFade fadeOut={0}>
      <Sfx name="hit" at={4} volume={0.7} />
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          transform: `scale(${slowZoom})`,
        }}
      >
        <div style={{ position: "relative", width: 200, height: 200, marginBottom: 18 }}>
          <div
            style={{
              position: "absolute",
              inset: -80,
              background: `radial-gradient(circle, ${COLORS.primaryStrong}55, transparent 65%)`,
              opacity: logo,
            }}
          />
          <Img
            src={staticFile(CONTENT.logo)}
            style={{
              position: "relative",
              width: "100%",
              height: "100%",
              opacity: logo,
              transform: `scale(${0.7 + 0.3 * logo})`,
            }}
          />
        </div>
        <div style={{ fontFamily: FONT, fontSize: 52, fontWeight: 600, color: COLORS.muted, opacity: logo, letterSpacing: -0.5 }}>
          {CONTENT.appName}
        </div>
        <MaskedWords
          text={CONTENT.outro.phrase}
          delay={34}
          stagger={7}
          style={{
            marginTop: 34,
            fontFamily: FONT,
            fontSize: 104,
            fontWeight: 700,
            letterSpacing: -3,
            textAlign: "center",
          }}
          wordStyle={{
            background: `linear-gradient(90deg, ${COLORS.text}, ${COLORS.primary} 70%, ${COLORS.cyan})`,
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        />
        <div
          style={{
            marginTop: 40,
            height: 3,
            width: 520 * line,
            borderRadius: 3,
            background: `linear-gradient(90deg, transparent, ${COLORS.primary}, transparent)`,
          }}
        />
        <div style={{ marginTop: 28, fontFamily: FONT, fontSize: 34, color: COLORS.muted, opacity: line }}>
          {CONTENT.outro.sub}
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "#000", opacity: black }} />
    </SceneFade>
  );
};
