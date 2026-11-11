import React from "react";
import { Composition } from "remotion";
import { Promo } from "./Promo";
import { FPS, HEIGHT, TOTAL_FRAMES, WIDTH } from "./theme";

export const Root: React.FC = () => (
  <Composition
    id="Promo"
    component={Promo}
    durationInFrames={TOTAL_FRAMES}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
  />
);
