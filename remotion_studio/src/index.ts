import React from "react";
import { Composition, registerRoot } from "remotion";
import { WTBDocumentary, DocumentaryProps } from "./Documentary";

const Root: React.FC = () => {
  return (
    <Composition
      id="WTBDocumentary"
      component={WTBDocumentary}
      durationInFrames={24 * 60}
      fps={24}
      width={1920}
      height={1080}
      defaultProps={{ title: "World Talk Brief", beats: [] } as DocumentaryProps}
      calculateMetadata={({ props }) => {
        const totalSec = (props.beats || []).reduce((acc, b) => acc + (b.duration || 6), 0);
        return { durationInFrames: Math.max(24, Math.round(totalSec * 24)) };
      }}
    />
  );
};

registerRoot(Root);
