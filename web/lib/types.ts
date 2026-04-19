export interface Vote {
  id: string;
  timestamp: string;
  mode: "arena" | "rubric" | "multiturn_arena";
  scenario_id: string;
  context: string;
  /** Set server-side from the voter cookie; clients never populate this. */
  voter_id?: string;
  /** Server-set: true when this vote was on a calibration/catch pair. */
  is_catch?: boolean;
  /** Server-set: true if the voter picked the pre-declared good response on a catch pair, false if they didn't, undefined for non-catch votes. */
  catch_correct?: boolean;
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
  character_info?: {
    character_name: string;
    user_name: string;
    setting_summary: string;
  };
  responses: {
    model: string;
    content: string;
  }[];
}

export const RUBRIC_DIMENSIONS = [
  // Tier 1: Fundamentals (always score)
  { id: "agency_respect", name: "Agency Respect", tier: 1, description: "Doesn't write your character's actions" },
  { id: "instruction_adherence", name: "Instruction Adherence", tier: 1, description: "Follows character card, POV, tense" },
  { id: "continuity", name: "Continuity", tier: 1, description: "Remembers prior details" },
  { id: "length_calibration", name: "Length Calibration", tier: 1, description: "Right amount for the scene" },
  { id: "distinct_voices", name: "Distinct Voices", tier: 1, description: "NPCs sound different" },
  { id: "scene_grounding", name: "Scene Grounding", tier: 1, description: "Can picture the room" },
  // Tier 2: Quality Control (always score)
  { id: "anti_purple_prose", name: "Anti-Purple Prose", tier: 2, description: "Prose serves the story" },
  { id: "anti_repetition", name: "Anti-Repetition", tier: 2, description: "Fresh descriptions" },
  { id: "anti_sycophancy", name: "Anti-Sycophancy", tier: 2, description: "World pushes back" },
  { id: "show_dont_tell", name: "Show Don't Tell", tier: 2, description: "Emotions through behavior" },
  { id: "subtext", name: "Subtext", tier: 2, description: "Gap between said and meant" },
  { id: "pacing", name: "Pacing", tier: 2, description: "Moments breathe" },
  // Tier 3: Genre Craft (score if applicable — skip if N/A)
  { id: "earned_intimacy", name: "Earned Intimacy", tier: 3, description: "Romance tension through restraint" },
  { id: "atmospheric_dread", name: "Atmospheric Dread", tier: 3, description: "Horror through wrongness, not announcement" },
  { id: "structural_comedy", name: "Structural Comedy", tier: 3, description: "Character-driven humor" },
  { id: "excavated_truth", name: "Excavated Truth", tier: 3, description: "Choices have real cost" },
  { id: "spatial_precision", name: "Spatial Precision", tier: 3, description: "Can draw the room, hits persist" },
  { id: "lived_in_worlds", name: "Lived-In Worlds", tier: 3, description: "World has rules, costs, logistics" },
  { id: "erotic_craft", name: "Erotic Craft", tier: 3, description: "Specific, emotionally loaded, well-paced" },
  { id: "context_integration", name: "Context Integration", tier: 3, description: "Lorebook woven naturally" },
  { id: "temporal_reasoning", name: "Temporal Reasoning", tier: 3, description: "Time passes consistently" },
] as const;
