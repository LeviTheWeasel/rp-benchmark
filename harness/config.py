"""Configuration for RP-Bench harness."""
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
RESULTS_DIR = PROJECT_ROOT / "results"
BENCHMARK_FILE = PROJECT_ROOT / "benchmark_v0.4.json"
PAYLOADS_FILE = PROJECT_ROOT / "eval_payloads.json"

# OpenRouter
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Judge models
JUDGE_MODELS = {
    "claude_sonnet": "anthropic/claude-sonnet-4",
    "gpt_4_1": "openai/gpt-4.1",
}

# Test models (models being benchmarked — add more as needed)
TEST_MODELS = {
    "claude_opus_4_6": "anthropic/claude-opus-4.6",
    "claude_sonnet_4_5": "anthropic/claude-sonnet-4.5",
    "gpt_4_1": "openai/gpt-4.1",
    "gemini_2_5_flash": "google/gemini-2.5-flash",
    "deepseek_v3_2": "deepseek/deepseek-v3.2",
    "glm_4_7": "z-ai/glm-4.7",
    "gemma_4_26b": "google/gemma-4-26b-a4b-it",
    "grok_4_1": "x-ai/grok-4.1-fast",
    "minimax_m2_7": "minimax/minimax-m2.7",
    "qwen3_5_flash": "qwen/qwen3.5-flash-02-23",
    "mistral_small_creative": "mistralai/mistral-small-creative",
    "llama_4_maverick": "meta-llama/llama-4-maverick",
}

# Generation settings for test models
GENERATION_CONFIG = {
    "temperature": 0.8,
    "max_tokens": 4096,
    "top_p": 0.95,
}

# Judge settings (lower temp for consistent scoring)
JUDGE_CONFIG = {
    "temperature": 0.1,
    "max_tokens": 4096,
}

# Rate limiting
REQUEST_DELAY_SECONDS = 1.0
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5.0
