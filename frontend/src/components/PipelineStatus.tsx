"use client";

import type { Pipeline } from "@/lib/types";

const STAGES: { key: keyof Pipeline; label: string }[] = [
  { key: "grounding", label: "Ground" },
  { key: "script", label: "Script" },
  { key: "html", label: "Slides" },
  { key: "audio_tags", label: "Tags" },
  { key: "audio", label: "Audio" },
  { key: "assembled", label: "Final" },
];

interface Props {
  pipeline: Pipeline;
  videoName: string;
  unit: string;
  lesson: string;
}

export default function PipelineStatus({ pipeline, videoName, unit, lesson }: Props) {
  const previewUrl = `/preview/${unit}/${lesson}/${videoName}`;

  return (
    <div
      className="flex items-center gap-2 px-4 py-2 border-b text-xs shrink-0"
      style={{ borderColor: "var(--border)", background: "var(--bg-panel)" }}
    >
      <span className="font-mono text-gray-400 mr-1 truncate max-w-40" title={videoName}>
        {videoName}
      </span>
      <span className="text-gray-600 mr-1">|</span>
      {STAGES.map(({ key, label }) => {
        const val = pipeline[key];
        const done = val === "complete" || val === true;
        const active = val && !done;
        return (
          <span
            key={key}
            className="px-2 py-0.5 rounded font-medium"
            style={{
              background: done ? "#14532d" : active ? "#713f12" : "#1e293b",
              color: done ? "#86efac" : active ? "#fde68a" : "#64748b",
            }}
          >
            {label}
          </span>
        );
      })}
      <a
        href={previewUrl}
        target="_blank"
        rel="noreferrer"
        className="ml-auto text-blue-400 hover:text-blue-300 shrink-0"
      >
        Open preview ↗
      </a>
    </div>
  );
}
