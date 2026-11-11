import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BrowserMockup } from "../components/BrowserMockup";
import { Camera } from "../components/Camera";
import { Crop } from "../components/Crop";
import { MaskedWords } from "../components/Reveal";
import { SceneFade } from "../components/SceneFade";
import { Sfx } from "../components/Sfx";
import { CONTENT } from "../content";
import { COLORS, FONT } from "../theme";

const MOCK_W = 1280;
const SCREEN_H = MOCK_W / 1.6;

/** 5–12 s · El problema y la aplicación entrando en un navegador con movimiento 3D. */
export const Presentation: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const c = CONTENT.presentation;

  const enter = spring({ frame: frame - 6, fps, config: { damping: 22, stiffness: 70, mass: 1.1 } });
  const slow = interpolate(frame, [0, 210], [0, 1], { easing: Easing.inOut(Easing.quad) });
  const rotY = interpolate(enter, [0, 1], [-28, -6]) + slow * 7;
  const rotX = interpolate(enter, [0, 1], [26, 9]) - slow * 3;
  const scale = interpolate(enter, [0, 1], [0.72, 0.98]) + slow * 0.08;
  const y = interpolate(enter, [0, 1], [260, 0]);

  // dos widgets recortados flotan delante con otro ritmo: paralaje y profundidad
  const float = (period: number, amp: number, ph = 0) => Math.sin(frame / period + ph) * amp;
  const sideIn = spring({ frame: frame - 70, fps, config: { damping: 200 } });

  return (
    <SceneFade>
      <Sfx name="whoosh" at={4} volume={0.6} />
      <Sfx name="whoosh" at={92} volume={0.35} />
      <AbsoluteFill style={{ perspective: 2200 }}>
        {/* Texto: el problema y, después, la solución */}
        <div style={{ position: "absolute", top: 58, left: 0, right: 0, textAlign: "center" }}>
          <MaskedWords
            text={c.problem}
            delay={8}
            exitAt={84}
            style={{ fontFamily: FONT, fontSize: 62, fontWeight: 600, color: COLORS.muted, letterSpacing: -1 }}
          />
        </div>
        <div style={{ position: "absolute", top: 58, left: 0, right: 0, textAlign: "center" }}>
          <MaskedWords
            text={c.solution}
            delay={100}
            style={{ fontFamily: FONT, fontSize: 62, fontWeight: 700, color: COLORS.text, letterSpacing: -1.5 }}
          />
        </div>

        {/* Mockup principal */}
        <div
          style={{
            position: "absolute",
            left: (1920 - MOCK_W) / 2,
            top: 240,
            transformStyle: "preserve-3d",
            transform: `translateY(${y}px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale(${scale})`,
            opacity: Math.min(1, enter * 3),
          }}
        >
          <BrowserMockup width={MOCK_W} url={c.url}>
            <Camera
              src={c.shot}
              width={MOCK_W}
              height={SCREEN_H}
              keys={[
                { f: 0, s: 1, x: 1000, y: 625 },
                { f: 210, s: 1.1, x: 1000, y: 560 },
              ]}
            />
          </BrowserMockup>
        </div>

        {/* Widgets flotantes con desenfoque de profundidad */}
        <div
          style={{
            position: "absolute",
            left: 70 - (1 - sideIn) * 80,
            top: 420 + float(40, 10),
            opacity: sideIn,
            transform: "translateZ(140px) rotateY(18deg) rotate(-3deg)",
            filter: "blur(1.5px)",
            boxShadow: "0 40px 80px rgba(0,0,0,0.6)",
            borderRadius: 16,
          }}
        >
          <Crop src={c.shot} rect={{ x: 1474, y: 190, w: 304, h: 460 }} width={300} radius={16} />
        </div>
        <div
          style={{
            position: "absolute",
            right: 60 - (1 - sideIn) * 80,
            top: 520 + float(46, 12, 2),
            opacity: sideIn,
            transform: "translateZ(120px) rotateY(-18deg) rotate(3deg)",
            filter: "blur(1.5px)",
            boxShadow: "0 40px 80px rgba(0,0,0,0.6)",
            borderRadius: 16,
          }}
        >
          <Crop src={c.shot} rect={{ x: 748, y: 681, w: 504, h: 440 }} width={330} radius={16} />
        </div>
      </AbsoluteFill>
    </SceneFade>
  );
};
