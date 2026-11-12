import React from "react";
import {
  Easing,
  interpolate,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
  AbsoluteFill,
  staticFile,
} from "remotion";
import { BrowserMockup } from "../components/BrowserMockup";
import { Callout } from "../components/Callout";
import { Camera, CameraKey } from "../components/Camera";
import { Caption } from "../components/Caption";
import { box, Rect } from "../components/Crop";
import { FadeUp, MaskedWords } from "../components/Reveal";
import { SceneFade } from "../components/SceneFade";
import { Sfx } from "../components/Sfx";
import { CONTENT } from "../content";
import { COLORS, FEATURE_DUR, FONT, SHOT } from "../theme";

const MOCK_W = 1110;
const SCREEN_H = MOCK_W / 1.6;

type Feature = (typeof CONTENT.features)[number];

type Shot = {
  keys: CameraKey[];
  callouts: { rect: Rect; at: number; hideAt?: number; sound?: boolean }[];
  overlay?: React.ReactNode;
  screenOverlay?: React.ReactNode;
};

// ---------- Plano 1 · Tablero: una tarjeta se arrastra de Guardada a En revisión ----------
const CARD_FROM: Rect = { x: 235, y: 459, w: 375, h: 118 };
const CARD_TO = { x: 1068, y: 459 };
const COLUMN_BG = "#151518";

const BoardDrag: React.FC<{ src: string }> = ({ src }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = interpolate(frame, [58, 98], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const lift = spring({ frame: frame - 52, fps, config: { damping: 14, stiffness: 140 } });
  const drop = spring({ frame: frame - 98, fps, config: { damping: 12, stiffness: 160 } });
  const x = CARD_FROM.x + (CARD_TO.x - CARD_FROM.x) * t;
  const y = CARD_FROM.y + (CARD_TO.y - CARD_FROM.y) * t - Math.sin(t * Math.PI) * 50;
  const grabbed = frame >= 52 ? 1 : 0;
  const scale = 1 + 0.05 * lift - 0.05 * drop;
  const rot = Math.sin(t * Math.PI) * 4 * (1 - t);
  return (
    <>
      {/* hueco que deja la tarjeta al levantarse */}
      <div
        style={{
          ...box({ x: CARD_FROM.x - 3, y: CARD_FROM.y - 3, w: CARD_FROM.w + 6, h: CARD_FROM.h + 6 }),
          background: COLUMN_BG,
          opacity: grabbed ? 1 : 0,
          borderRadius: 14,
        }}
      />
      {frame >= 50 && (
        <div
          style={{
            ...box({ x, y, w: CARD_FROM.w, h: CARD_FROM.h }),
            transform: `scale(${scale}) rotate(${rot}deg)`,
            boxShadow: `0 ${24 * lift}px ${50 * lift}px rgba(0,0,0,0.65), 0 0 ${30 * lift}px ${COLORS.primary}66`,
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          <img
            src={staticFile(src)}
            style={{
              position: "absolute",
              maxWidth: "none",
              width: `${(SHOT.w / CARD_FROM.w) * 100}%`,
              height: `${(SHOT.h / CARD_FROM.h) * 100}%`,
              left: `${(-CARD_FROM.x / CARD_FROM.w) * 100}%`,
              top: `${(-CARD_FROM.y / CARD_FROM.h) * 100}%`,
            }}
          />
        </div>
      )}
    </>
  );
};

// ---------- Plano 3 · CV con IA: contador de encaje ----------
const MatchBadge: React.FC<{ feature: Feature }> = ({ feature }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = feature as Feature & { metricFrom: number; metricTo: number; metricLabel: string };
  const p = spring({ frame: frame - 56, fps, config: { damping: 200 } });
  const count = spring({ frame: frame - 68, fps, config: { damping: 200 }, durationInFrames: 40 });
  const value = Math.round(interpolate(count, [0, 1], [f.metricFrom, f.metricTo]));
  return (
    <div
      style={{
        position: "absolute",
        left: 120,
        bottom: 190,
        opacity: p,
        transform: `translateY(${(1 - p) * 30}px)`,
        padding: "22px 30px",
        borderRadius: 22,
        background: "rgba(24,24,27,0.78)",
        border: "1px solid rgba(255,255,255,0.14)",
        backdropFilter: "blur(14px)",
        boxShadow: `0 20px 60px rgba(0,0,0,0.5), 0 0 50px ${COLORS.primaryStrong}44`,
        fontFamily: FONT,
      }}
    >
      <div style={{ fontSize: 22, color: COLORS.muted }}>{f.metricLabel}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
        <span style={{ fontSize: 40, color: COLORS.muted, textDecoration: "line-through" }}>{f.metricFrom} %</span>
        <span style={{ fontSize: 64, fontWeight: 700, color: COLORS.green }}>{value} %</span>
      </div>
    </div>
  );
};

const SHOTS: Shot[] = [
  {
    keys: [
      { f: 0, s: 1, x: 1000, y: 625 },
      { f: 38, s: 1.5, x: 800, y: 520 },
      { f: 156, s: 1.5, x: 800, y: 520 },
    ],
    callouts: [{ rect: { x: 1056, y: 271, w: 400, h: 580 }, at: 100, sound: true }],
  },
  {
    keys: [
      { f: 0, s: 1, x: 1000, y: 625 },
      { f: 30, s: 1.75, x: 1420, y: 420 },
      { f: 84, s: 1.75, x: 1420, y: 420 },
      { f: 118, s: 1.7, x: 1430, y: 800 },
      { f: 156, s: 1.7, x: 1430, y: 800 },
    ],
    callouts: [
      { rect: { x: 1169, y: 258, w: 610, h: 280 }, at: 34, hideAt: 100, sound: true },
      { rect: { x: 1169, y: 570, w: 610, h: 400 }, at: 98, sound: true },
    ],
  },
  {
    keys: [
      { f: 0, s: 1, x: 1000, y: 625 },
      { f: 30, s: 1.6, x: 700, y: 500 },
      { f: 88, s: 1.6, x: 700, y: 500 },
      { f: 122, s: 1.5, x: 1000, y: 830 },
      { f: 156, s: 1.5, x: 1000, y: 830 },
    ],
    callouts: [
      { rect: { x: 235, y: 455, w: 470, h: 110 }, at: 36, hideAt: 100, sound: true },
      { rect: { x: 240, y: 575, w: 330, h: 355 }, at: 62, hideAt: 100 },
      { rect: { x: 1005, y: 1050, w: 755, h: 175 }, at: 106, sound: true },
    ],
  },
  {
    keys: [
      { f: 0, s: 1, x: 1000, y: 625 },
      { f: 30, s: 1.55, x: 800, y: 560 },
      { f: 88, s: 1.55, x: 800, y: 560 },
      { f: 122, s: 1.55, x: 1355, y: 850 },
      { f: 156, s: 1.55, x: 1355, y: 850 },
    ],
    callouts: [
      { rect: { x: 245, y: 618, w: 1078, h: 136 }, at: 36, hideAt: 104, sound: true },
      { rect: { x: 1355, y: 570, w: 402, h: 380 }, at: 106, sound: true },
    ],
  },
  {
    keys: [
      { f: 0, s: 1, x: 1000, y: 625 },
      { f: 30, s: 1.7, x: 860, y: 480 },
      { f: 88, s: 1.7, x: 860, y: 480 },
      { f: 122, s: 1.8, x: 1444, y: 420 },
      { f: 156, s: 1.8, x: 1444, y: 420 },
    ],
    callouts: [
      { rect: { x: 446, y: 317, w: 435, h: 190 }, at: 36, hideAt: 104, sound: true },
      { rect: { x: 1342, y: 317, w: 436, h: 190 }, at: 108, sound: true },
    ],
  },
];

const FeatureShot: React.FC<{ feature: Feature; index: number }> = ({ feature, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const shot = SHOTS[index];

  const enter = spring({ frame: frame - 2, fps, config: { damping: 24, stiffness: 80 } });
  const tilt = interpolate(frame, [0, FEATURE_DUR], [-6, -2]);
  const lean = interpolate(enter, [0, 1], [18, 0]);
  // salida: el plano se desliza hacia la izquierda mientras entra el siguiente
  const exit = interpolate(frame, [FEATURE_DUR - 6, FEATURE_DUR + 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });

  return (
    <SceneFade fadeIn={8} fadeOut={8}>
      <Sfx name="whoosh" at={0} volume={0.45} />
      {shot.callouts.map((c, i) => c.sound && <Sfx key={i} name="tick" at={c.at} volume={0.5} />)}
      {index === 0 && <Sfx name="pop" at={98} volume={0.7} />}
      {index === 0 && <Sfx name="tick" at={52} volume={0.5} />}
      <AbsoluteFill style={{ perspective: 2400 }}>
        {/* Columna de texto */}
        <div style={{ position: "absolute", left: 100 - exit * 120, top: 250, width: 600 }}>
          <FadeUp delay={4} distance={16}>
            <div
              style={{
                display: "inline-block",
                fontFamily: FONT,
                fontSize: 22,
                fontWeight: 600,
                color: COLORS.primary,
                padding: "8px 18px",
                borderRadius: 99,
                background: `${COLORS.primaryStrong}33`,
                border: `1px solid ${COLORS.primary}55`,
                marginBottom: 26,
              }}
            >
              {feature.chip}
            </div>
          </FadeUp>
          <MaskedWords
            text={feature.title}
            delay={8}
            style={{ fontFamily: FONT, fontSize: 78, lineHeight: 1.04, fontWeight: 700, color: COLORS.text, letterSpacing: -2 }}
          />
          <FadeUp delay={30} distance={18}>
            <div style={{ marginTop: 22, fontFamily: FONT, fontSize: 31, lineHeight: 1.35, color: COLORS.muted }}>
              {feature.sub}
            </div>
          </FadeUp>
        </div>

        {/* Mockup con cámara */}
        <div
          style={{
            position: "absolute",
            left: 720 + (1 - enter) * 160 - exit * 260,
            top: 100,
            opacity: Math.min(1, enter * 2.5),
            transform: `rotateY(${tilt + lean}deg) rotateX(2deg)`,
            transformOrigin: "left center",
          }}
        >
          <BrowserMockup width={MOCK_W} url="applications-tracker">
            <Camera src={feature.shot} width={MOCK_W} height={SCREEN_H} keys={shot.keys}>
              {index === 0 && <BoardDrag src={feature.shot} />}
              {shot.callouts.map((c, i) => (
                <Callout key={i} rect={c.rect} at={c.at} hideAt={c.hideAt} />
              ))}
            </Camera>
          </BrowserMockup>
        </div>
        {index === 2 && <MatchBadge feature={feature} />}
      </AbsoluteFill>
      <Caption text={feature.caption} at={26} hideAt={FEATURE_DUR - 22} />
    </SceneFade>
  );
};

/** 12–38 s · Cinco funcionalidades con zoom, llamadas de atención y subtítulos. */
export const Features: React.FC = () => (
  <>
    {CONTENT.features.map((f, i) => (
      <Sequence key={i} from={i * FEATURE_DUR} durationInFrames={FEATURE_DUR + 8} name={f.chip}>
        <FeatureShot feature={f} index={i} />
      </Sequence>
    ))}
  </>
);
