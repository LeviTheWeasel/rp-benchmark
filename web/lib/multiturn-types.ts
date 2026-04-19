export interface MultiturnMessage {
  role: "user" | "assistant";
  content: string;
}

export interface MultiturnSession {
  seed_id: string;
  test_model: string;
  character_name: string;
  user_name: string;
  num_turns: number;
  dialogue: MultiturnMessage[];
}

export interface MultiturnPair {
  id: string;
  seed_id: string;
  model_a: string;
  model_b: string;
}

export interface SeedMeta {
  failure_target: string;
  setting_summary: string;
  character_name: string;
  user_name: string;
}
