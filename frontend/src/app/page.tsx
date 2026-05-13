"use client";

import { useCoAgent } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import VideoPreview from "@/components/VideoPreview";
import SceneEditor from "@/components/SceneEditor";
import PipelineStatus from "@/components/PipelineStatus";
import type { AgentState } from "@/lib/types";

export default function Home() {
  const { state, setState } = useCoAgent<AgentState>({
    name: "video_generation_agent",
    initialState: { script_json: null },
  });

  const scriptJson = state?.script_json ?? null;

  const handleSceneChange = (
    index: number,
    field: "speech" | "comment",
    value: string
  ) => {
    if (!scriptJson) return;
    const updatedScenes = scriptJson.scenes.map((scene, i) =>
      i === index ? { ...scene, [field]: value } : scene
    );
    setState({ ...state, script_json: { ...scriptJson, scenes: updatedScenes } });
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-base)" }}>
      {/* Chat panel */}
      <div
        className="flex flex-col border-r overflow-hidden"
        style={{ width: "40%", borderColor: "var(--border)" }}
      >
        <CopilotChat
          className="flex-1 overflow-hidden"
          labels={{
            title: "Video Generation Agent",
            initial:
              "Hi! Tell me which unit, lesson, and video you want to work on — or just describe what you need.",
          }}
        />
      </div>

      {/* Preview + editor panel */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {scriptJson ? (
          <>
            <PipelineStatus
              pipeline={scriptJson.pipeline}
              videoName={scriptJson.video_name}
              unit={scriptJson.unit}
              lesson={scriptJson.lesson}
            />
            <VideoPreview scriptJson={scriptJson} />
            <SceneEditor
              scenes={scriptJson.scenes}
              pipeline={scriptJson.pipeline}
              onSceneChange={handleSceneChange}
            />
          </>
        ) : (
          <div
            className="flex-1 flex items-center justify-center"
            style={{ color: "#6b7280" }}
          >
            <div className="text-center">
              <div className="text-5xl mb-4">🎬</div>
              <p className="text-lg">No video in progress.</p>
              <p className="text-sm mt-2">
                Start by telling the agent which video to build.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
