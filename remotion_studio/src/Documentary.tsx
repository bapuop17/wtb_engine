import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export interface BeatProps {
  id: string;
  chapter: string;
  narration: string;
  duration: number;
  asset?: { path?: string; kind?: string; label?: string };
  visual: { kind: string; headline: string; data?: Record<string, any> };
}

export interface DocumentaryProps {
  title: string;
  style?: string;
  audioPath?: string;
  beats: BeatProps[];
}

const BeatScene: React.FC<{ beat: BeatProps; index: number }> = ({ beat, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const totalFrames = Math.max(24, Math.round((beat.duration || 6) * fps));
  const pop = spring({ frame, fps, config: { damping: 14, stiffness: 120 } });
  const zoom = interpolate(frame, [0, totalFrames], [1.02, 1.11], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "#070d19", fontFamily: "Inter, sans-serif", color: "#f8fafc" }}>
      {beat.asset?.path && (
        <AbsoluteFill style={{ overflow: "hidden" }}>
          <Img
            src={beat.asset.path}
            style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})`, filter: "contrast(1.1) saturate(1.08)" }}
          />
          <AbsoluteFill
            style={{
              background: "linear-gradient(180deg, rgba(7,13,25,0.65) 0%, rgba(7,13,25,0.05) 28%, rgba(7,13,25,0.12) 72%, rgba(7,13,25,0.88) 100%)",
            }}
          />
        </AbsoluteFill>
      )}
      <div
        style={{
          position: "absolute",
          top: 44,
          left: 72,
          display: "flex",
          alignItems: "center",
          gap: 16,
          transform: `translateY(${(1 - pop) * -28}px)`,
          opacity: pop,
        }}
      >
        <span style={{ background: "#10B981", color: "#050b14", padding: "8px 18px", borderRadius: 8, fontWeight: 900, fontSize: 20, letterSpacing: 1.5 }}>
          WORLD TALK BRIEF
        </span>
        <span style={{ color: "#FACC15", fontWeight: 800, fontSize: 21, letterSpacing: 1.4 }}>
          {beat.chapter.toUpperCase()}
        </span>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 84,
          left: 110,
          right: 110,
          background: "rgba(6,11,22,0.82)",
          backdropFilter: "blur(18px)",
          border: "2px solid rgba(250,204,21,0.45)",
          borderRadius: 14,
          padding: "18px 28px",
          textAlign: "center",
          fontSize: 34,
          fontWeight: 800,
          lineHeight: 1.28,
          transform: `scale(${0.96 + 0.04 * pop})`,
        }}
      >
        {beat.narration}
      </div>
    </AbsoluteFill>
  );
};

export const WTBDocumentary: React.FC<DocumentaryProps> = ({ beats = [], audioPath }) => {
  const { fps } = useVideoConfig();
  let offset = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: "#070d19" }}>
      {audioPath ? <Audio src={audioPath} /> : null}
      {beats.map((beat, idx) => {
        const durFrames = Math.max(24, Math.round((beat.duration || 6) * fps));
        const from = offset;
        offset += durFrames;
        return (
          <Sequence key={beat.id || idx} from={from} durationInFrames={durFrames}>
            <BeatScene beat={beat} index={idx} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
