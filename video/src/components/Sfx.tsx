import React from "react";
import { Audio, Sequence, staticFile } from "remotion";

export type SfxName = "whoosh" | "hit" | "tick" | "pop" | "riser";

/** Efecto de sonido que empieza en el fotograma `at` (relativo a la escena donde se use). */
export const Sfx: React.FC<{ name: SfxName; at: number; volume?: number }> = ({
  name,
  at,
  volume = 0.7,
}) => (
  <Sequence from={at} layout="none">
    <Audio src={staticFile(`audio/${name}.wav`)} volume={volume} />
  </Sequence>
);
