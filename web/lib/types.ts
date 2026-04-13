export interface Vote {
  id: string;
  timestamp: string;
  mode: "arena" | "rubric";
  scenario_id: string;
  context: string;
  // Arena mode
  model_a?: string;
  model_b?: string;
  response_a?: string;
  response_b?: string;
  winner?: "A" | "B" | "tie";
  // Rubric mode
  model?: string;
  response?: string;
  scores?: Record<string, number>;
  notes?: string;
}

export interface Scenario {
  id: string;
  context: string;
  responses: {
    model: string;
    content: string;
  }[];
}

export const RUBRIC_DIMENSIONS = [
  { id: "agency_respect", name: "Agency Respect", tier: 1, description: "Doesn't write your character's actions" },
  { id: "instruction_adherence", name: "Instruction Adherence", tier: 1, description: "Follows character card, POV, tense" },
  { id: "continuity", name: "Continuity", tier: 1, description: "Remembers prior details" },
  { id: "length_calibration", name: "Length Calibration", tier: 1, description: "Right amount for the scene" },
  { id: "distinct_voices", name: "Distinct Voices", tier: 1, description: "NPCs sound different" },
  { id: "scene_grounding", name: "Scene Grounding", tier: 1, description: "Can picture the room" },
  { id: "anti_purple_prose", name: "Anti-Purple Prose", tier: 2, description: "Prose serves the story" },
  { id: "anti_repetition", name: "Anti-Repetition", tier: 2, description: "Fresh descriptions" },
  { id: "anti_sycophancy", name: "Anti-Sycophancy", tier: 2, description: "World pushes back" },
  { id: "show_dont_tell", name: "Show Don't Tell", tier: 2, description: "Emotions through behavior" },
  { id: "subtext", name: "Subtext", tier: 2, description: "Gap between said and meant" },
  { id: "pacing", name: "Pacing", tier: 2, description: "Moments breathe" },
] as const;
