"use client";

import type { Scene, Pipeline } from "@/lib/types";

interface Props {
  scenes: Scene[];
  pipeline: Pipeline;
  onSceneChange: (index: number, field: "speech" | "comment", value: string) => void;
}

export default function SceneEditor({ scenes, pipeline, onSceneChange }: Props) {
  if (!scenes.length) return null;

  const canEdit = !!pipeline.script;

  return (
    <div
      className="shrink-0 overflow-y-auto border-t"
      style={{
        height: "240px",
        borderColor: "var(--border)",
        background: "var(--bg-base)",
      }}
    >
      <div
        className="px-4 py-2 text-xs font-medium uppercase tracking-wide border-b sticky top-0"
        style={{
          color: "#94a3b8",
          borderColor: "var(--border)",
          background: "var(--bg-base)",
        }}
      >
        Scenes
        {canEdit && (
          <span className="ml-2 normal-case font-normal text-gray-500">
            — edits are picked up before the next pipeline stage
          </span>
        )}
      </div>
      <div>
        {scenes.map((scene, i) => (
          <div
            key={i}
            className="flex gap-3 px-4 py-3 border-b"
            style={{ borderColor: "var(--border)" }}
          >
            <div
              className="font-mono text-xs mt-1 shrink-0 w-6"
              style={{ color: "#475569" }}
            >
              {String(i + 1).padStart(2, "0")}
            </div>
            <div className="flex-1 flex flex-col gap-1 min-w-0">
              <input
                className="text-xs bg-transparent border-0 focus:outline-none truncate"
                style={{ color: "#64748b" }}
                value={scene.comment ?? ""}
                readOnly={!canEdit}
                onChange={(e) => onSceneChange(i, "comment", e.target.value)}
                placeholder="Scene description"
              />
              <textarea
                className="text-sm rounded px-2 py-1.5 resize-none focus:outline-none focus:ring-1"
                style={{
                  background: "var(--bg-card)",
                  color: canEdit ? "white" : "#94a3b8",
                }}
                rows={2}
                value={scene.speech ?? ""}
                readOnly={!canEdit}
                onChange={(e) => onSceneChange(i, "speech", e.target.value)}
                placeholder="Speech text..."
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
