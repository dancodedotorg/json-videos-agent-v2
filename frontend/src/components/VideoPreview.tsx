"use client";

import { useEffect, useRef, useState } from "react";
import type { ScriptJson } from "@/lib/types";

// Typed alias for <json-video> web component so TypeScript doesn't complain
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const JsonVideo = "json-video" as any;

interface Props {
  scriptJson: ScriptJson;
}

export default function VideoPreview({ scriptJson }: Props) {
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wcLoadedRef = useRef(false);

  const { unit, lesson, video_name: video, pipeline } = scriptJson;

  // Load <json-video> web component once on mount
  useEffect(() => {
    if (wcLoadedRef.current) return;
    wcLoadedRef.current = true;
    const script = document.createElement("script");
    script.type = "module";
    script.src = "/player/json-video.js";
    document.head.appendChild(script);
  }, []);

  // Poll /preview/data/ whenever html or assembled stage changes
  useEffect(() => {
    if (!unit || !lesson || !video) return;
    // Nothing to show until at least HTML slides are generated
    if (!pipeline.html && !pipeline.assembled) return;

    const fetchPreview = async () => {
      try {
        const res = await fetch(`/preview/data/${unit}/${lesson}/${video}`);
        if (res.ok) {
          const json = await res.json();
          // Pass the URL with a cache-busting param so <json-video> re-fetches
          setPreviewSrc(
            `/preview/data/${unit}/${lesson}/${video}?t=${Date.now()}`
          );
          // Silence unused-variable warning — we verify ok but let <json-video> fetch
          void json;
        }
      } catch {
        // backend not ready yet; try again on next interval
      }
    };

    fetchPreview();
    intervalRef.current = setInterval(fetchPreview, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [unit, lesson, video, pipeline.html, pipeline.assembled]);

  if (!previewSrc) {
    return (
      <div
        className="flex-1 flex items-center justify-center"
        style={{ background: "#0a0a0a", color: "#475569" }}
      >
        <p className="text-sm">
          Preview appears once HTML slides are generated.
        </p>
      </div>
    );
  }

  return (
    <div
      className="flex-1 flex items-center justify-center overflow-hidden"
      style={{ background: "#000" }}
    >
      <JsonVideo
        src={previewSrc}
        style={{ width: "100%", height: "100%", display: "block" }}
      />
    </div>
  );
}
