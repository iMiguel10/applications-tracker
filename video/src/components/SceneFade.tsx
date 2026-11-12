import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { OVERLAP } from "../theme";

/** Fundido de entrada y de salida de una escena (la salida cae en el solape con la siguiente). */
export const SceneFade: React.FC<{
  children: React.ReactNode;
  fadeIn?: number;
  fadeOut?: number;
}> = ({ children, fadeIn = OVERLAP, fadeOut = OVERLAP }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = interpolate(
    frame,
    [0, Math.max(1, fadeIn), durationInFrames - Math.max(1, fadeOut), durationInFrames],
    [fadeIn ? 0 : 1, 1, 1, fadeOut ? 0 : 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};
