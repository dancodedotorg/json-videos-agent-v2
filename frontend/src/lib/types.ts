export interface Scene {
  comment: string;
  speech: string;
  elevenlabs?: string;
  gemini?: string;
  duration?: string;
  audio?: string;
  html?: string;
}

export interface Pipeline {
  grounding?: string;
  script?: string;
  html?: string;
  audio_tags?: string;
  audio?: string;
  assembled?: boolean | string;
}

export interface ScriptJson {
  video_name: string;
  unit: string;
  lesson: string;
  mode: string;
  brief: string | null;
  width: number;
  height: number;
  target_objectives: string[];
  target_vocabulary: string[];
  pipeline: Pipeline;
  tts: Record<string, unknown>;
  scenes: Scene[];
}

export interface AgentState {
  script_json: ScriptJson | null;
}
