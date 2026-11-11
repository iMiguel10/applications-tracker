import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { MaskedWords } from "../components/Reveal";
import { SceneFade } from "../components/SceneFade";
import { Sfx } from "../components/Sfx";
import { CONTENT } from "../content";
import { COLORS, FONT } from "../theme";

/** 0–5 s · Logo, nombre y lema sobre el fondo de partículas. */
export const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logo = spring({ frame: frame - 10, fps, config: { damping: 16, stiffness: 90, mass: 0.8 } });
  const blur = interpolate(logo, [0, 1], [24, 0]);
  const ring = interpolate(frame, [14, 60], [0.6, 2.4], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const ringOpacity = interpolate(frame, [14, 60], [0.7, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const tagline = spring({ frame: frame - 62, fps, config: { damping: 200 } });
  // empuje final de cámara hacia el logo para enlazar con la presentación
  const push = interpolate(frame, [110, 150], [1, 1.12], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });

  return (
    <SceneFade fadeIn={0}>
      <Sfx name="whoosh" at={4} volume={0.5} />
      <Sfx name="hit" at={14} volume={0.8} />
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          transform: `scale(${push})`,
        }}
      >
        <div style={{ position: "relative", width: 230, height: 230, marginBottom: 26 }}>
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: "50%",
              border: `2px solid ${COLORS.primary}`,
              transform: `scale(${ring})`,
              opacity: ringOpacity,
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: -60,
              background: `radial-gradient(circle, ${COLORS.primaryStrong}66, transparent 65%)`,
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
              transform: `scale(${0.55 + 0.45 * logo})`,
              filter: `blur(${blur}px)`,
            }}
          />
        </div>
        <MaskedWords
          text={CONTENT.appName}
          delay={30}
          stagger={6}
          style={{
            fontFamily: FONT,
            fontSize: 112,
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
            marginTop: 18,
            fontFamily: FONT,
            fontSize: 38,
            fontWeight: 400,
            color: COLORS.muted,
            opacity: tagline,
            letterSpacing: interpolate(tagline, [0, 1], [10, 2]),
            transform: `translateY(${(1 - tagline) * 16}px)`,
          }}
        >
          {CONTENT.intro.tagline}
        </div>
      </AbsoluteFill>
    </SceneFade>
  );
};
