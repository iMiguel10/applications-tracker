import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PhoneMockup } from "../components/PhoneMockup";
import { FadeUp, MaskedWords } from "../components/Reveal";
import { SceneFade } from "../components/SceneFade";
import { Sfx } from "../components/Sfx";
import { CONTENT } from "../content";
import { COLORS, FONT } from "../theme";

const SWAP = 190; // fotograma en que las cifras dan paso al mensaje principal

const Stat: React.FC<{ value: number; suffix: string; label: string; delay: number }> = ({
  value,
  suffix,
  label,
  delay,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - delay, fps, config: { damping: 200 } });
  const n = spring({ frame: frame - delay, fps, config: { damping: 200 }, durationInFrames: 50 });
  return (
    <div style={{ opacity: p, transform: `translateX(${(1 - p) * -40}px)`, fontFamily: FONT }}>
      <div
        style={{
          fontSize: 128,
          fontWeight: 700,
          lineHeight: 1,
          letterSpacing: -4,
          background: `linear-gradient(90deg, ${COLORS.text}, ${COLORS.primary})`,
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}
      >
        {Math.round(n * value)}
        {suffix}
      </div>
      <div style={{ fontSize: 30, color: COLORS.muted, marginTop: 6 }}>{label}</div>
    </div>
  );
};

/** 38–50 s · El resultado: cifras animadas, versión móvil y el mensaje principal. */
export const Result: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const r = CONTENT.result;

  const statsOut = interpolate(frame, [SWAP - 10, SWAP + 8], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const message = interpolate(frame, [SWAP + 6, SWAP + 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const phoneSpec = [
    { x: 1010, y: 190, rot: -9, z: 0, delay: 6, blur: 0 },
    { x: 1290, y: 120, rot: 0, z: 1, delay: 14, blur: 0 },
    { x: 1570, y: 210, rot: 9, z: 0, delay: 22, blur: 0 },
  ];
  // en el mensaje final los teléfonos retroceden: se desenfocan y bajan de opacidad
  const recede = interpolate(frame, [SWAP, SWAP + 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SceneFade>
      <Sfx name="whoosh" at={2} volume={0.5} />
      <Sfx name="tick" at={20} volume={0.45} />
      <Sfx name="tick" at={38} volume={0.45} />
      <Sfx name="tick" at={56} volume={0.45} />
      <Sfx name="riser" at={SWAP - 30} volume={0.4} />
      <Sfx name="hit" at={SWAP + 6} volume={0.6} />
      <AbsoluteFill style={{ perspective: 2000 }}>
        {r.phones.map((src, i) => {
          const s = phoneSpec[i];
          const p = spring({ frame: frame - s.delay, fps, config: { damping: 20, stiffness: 70 } });
          const float = Math.sin(frame / 38 + i * 2) * 10;
          const moveX = interpolate(recede, [0, 1], [0, i === 0 ? -520 : i === 2 ? 520 : 0]) * 0.5;
          return (
            <div
              key={src}
              style={{
                position: "absolute",
                left: s.x - 130 + moveX,
                top: s.y + (1 - p) * 300 + float,
                opacity: p * (1 - recede * 0.65),
                filter: `blur(${recede * 7}px)`,
                transform: `rotateY(${(i - 1) * -14}deg) rotate(${s.rot * p}deg) scale(${1 - recede * 0.12})`,
                zIndex: s.z,
              }}
            >
              <PhoneMockup src={src} width={300} />
            </div>
          );
        })}

        <div
          style={{
            position: "absolute",
            left: 110,
            top: 150,
            display: "flex",
            flexDirection: "column",
            gap: 46,
            opacity: statsOut,
          }}
        >
          <MaskedWords
            text={r.heading}
            delay={4}
            style={{ fontFamily: FONT, fontSize: 56, fontWeight: 700, color: COLORS.text, letterSpacing: -1.5, width: 700 }}
          />
          {r.stats.map((s, i) => (
            <Stat key={i} {...s} delay={18 + i * 18} />
          ))}
        </div>

        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: message }}>
          <MaskedWords
            text={r.message}
            delay={SWAP + 8}
            stagger={6}
            style={{
              fontFamily: FONT,
              fontSize: 132,
              fontWeight: 700,
              letterSpacing: -4,
              lineHeight: 1.05,
              textAlign: "center",
              color: COLORS.text,
              textShadow: "0 10px 60px rgba(0,0,0,0.7)",
            }}
          />
        </AbsoluteFill>
        <FadeUp delay={SWAP + 50} style={{ position: "absolute", bottom: 90, left: 0, right: 0, textAlign: "center" }}>
          <span style={{ fontFamily: FONT, fontSize: 34, color: COLORS.primary }}>{CONTENT.outro.sub}</span>
        </FadeUp>
      </AbsoluteFill>
    </SceneFade>
  );
};
