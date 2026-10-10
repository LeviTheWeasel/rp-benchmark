"""Configuration for RP-Bench harness."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Loaded HERE, not in api.py. This module reads os.environ at import time, and
# api.py imports it before calling load_dotenv -- so anything configured only
# in .env read as unset. OLLAMA_HOST hid the bug behind a default; the remote
# endpoint, which has no sensible default, surfaced it.
load_dotenv(Path(__file__).parent.parent / ".env")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
RESULTS_DIR = PROJECT_ROOT / "results"
BENCHMARK_FILE = PROJECT_ROOT / "benchmark_v0.3.json"
PAYLOADS_FILE = PROJECT_ROOT / "eval_payloads.json"

# OpenRouter
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Local Ollama (round 4: the adversarial user simulator runs locally).
# Model ids prefixed with LOCAL_PREFIX route here instead of OpenRouter, with
# no auth header and no shared rate gate. Override the host with OLLAMA_HOST.
LOCAL_PREFIX = "ollama/"
OLLAMA_BASE_URL = os.environ.get(
    "OLLAMA_HOST", "http://localhost:11434"
).rstrip("/") + "/v1"

# Rented inference (RunPod and the like). Model ids prefixed with
# REMOTE_PREFIX route to REMOTE_BASE_URL instead of OpenRouter.
#
# Separate from LOCAL_PREFIX for one reason that matters: the local route
# deliberately sends no Authorization header, because it talks to a loopback
# Ollama. A rented pod is reachable from the internet, so its endpoint must be
# able to carry a key -- reusing the local route would have quietly published
# an open inference endpoint.
#
# The key belongs to the pod, not to OpenRouter: the harness keeps the
# OpenRouter key local and sends only generation traffic to the pod, so a
# rented machine never sees the account key that pays for the judges.
REMOTE_PREFIX = "remote/"
REMOTE_BASE_URL = os.environ.get("REMOTE_BASE_URL", "").rstrip("/")
REMOTE_API_KEY = os.environ.get("REMOTE_API_KEY", "")

# User-simulator registry. Round 3 used a permissive-but-cooperative cloud sim;
# round 4 swaps in an uncensored local one that supplies naturalism while the
# seeds' scripted ladder supplies the escalation pressure.
USER_SIM_MODELS = {
    # cloud (rounds 1-3)
    "gemini_2_5_flash": "google/gemini-2.5-flash",   # default, SFW rounds
    "deepseek_v3_2": "deepseek/deepseek-v3.2",       # round 3 NSFW default
    # local (round 4 candidates — QC-gated by oneoff/dryrun_r4_sim_qc.py)
    "magmell_v9": "ollama/magmell-usersim-v9:latest",
    "magmell_v10": "ollama/magmell-usersim-v10:latest",
    "magmell_v11": "ollama/magmell-usersim-v11:latest",
    "magmell_v12": "ollama/magmell-usersim-v12:latest",
    # Stock Mag-Mell R1, without the strovolos writing-consultant finetune
    # that disqualified v9-v12 (see docs/ROUND4_DESIGN.md sec 10a).
    "magmell_stock": "ollama/magmell-usersim-stock:latest",
}

# Judge models
JUDGE_MODELS = {
    "claude_sonnet": "anthropic/claude-sonnet-4",
    "gpt_4_1": "openai/gpt-4.1",
    # Permissive NSFW-capable judge (round 3). Select with
    # `--judges claude_sonnet deepseek_r1` to run the dual-judge NSFW panel.
    "deepseek_r1": "deepseek/deepseek-r1-0528",
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
    "grok_4_3": "x-ai/grok-4.3",  # was grok-4.1-fast (delisted 2026-06)
    "minimax_m2_7": "minimax/minimax-m2.7",
    "qwen3_5_flash": "qwen/qwen3.5-flash-02-23",
    "mistral_small_2603": "mistralai/mistral-small-2603",  # was mistral-small-creative (delisted)
    "llama_4_maverick": "meta-llama/llama-4-maverick",
    # 2026-04-24: next-gen roster for the v2/v3 seed comparison
    "claude_opus_4_7": "anthropic/claude-opus-4.7",
    "deepseek_v4_pro": "deepseek/deepseek-v4-pro",
    "deepseek_v4_flash": "deepseek/deepseek-v4-flash",
    "glm_5_1": "z-ai/glm-5.1",
    "gemini_3_1_pro": "google/gemini-3.1-pro-preview",
    "gemini_3_1_flash_lite": "google/gemini-3.1-flash-lite-preview",
    "kimi_k2_5": "moonshotai/kimi-k2.5",
    "kimi_k2_6": "moonshotai/kimi-k2.6",
    "deepseek_r1_0528": "deepseek/deepseek-r1-0528",
    # 2026-06-08: round-3 (NSFW) additions.
    # Frontier refresh:
    "claude_opus_4_8": "anthropic/claude-opus-4.8",
    "claude_sonnet_4_6": "anthropic/claude-sonnet-4.6",
    "gpt_5_5": "openai/gpt-5.5",
    "gemini_3_5_flash": "google/gemini-3.5-flash",
    "qwen3_7_max": "qwen/qwen3.7-max",
    "minimax_m3": "minimax/minimax-m3",
    # RP / uncensored specialists (the NSFW-relevant cohort):
    "euryale_70b": "sao10k/l3.3-euryale-70b",
    "magnum_v4_72b": "anthracite-org/magnum-v4-72b",
    "cydonia_24b": "thedrummer/cydonia-24b-v4.1",
    "skyfall_36b": "thedrummer/skyfall-36b-v2",
    "lunaris_8b": "sao10k/l3-lunaris-8b",
    "unslopnemo_12b": "thedrummer/unslopnemo-12b",
    # 2026-09-24: the :free tier is gone; the model is now paid at 0.20/0.90.
    # Left in the roster because it is one of only five uncensored specialists.
    "venice_dolphin_24b": "cognitivecomputations/dolphin-mistral-24b-venice-edition",
    # 2026-06-08: additional requested models.
    "mimo_2_5_pro": "xiaomi/mimo-v2.5-pro",
    "gemma_4_31b": "google/gemma-4-31b-it",
    "qwen3_6_35b_a3b": "qwen/qwen3.6-35b-a3b",
    "qwen3_6_27b": "qwen/qwen3.6-27b",
    "deepseek_v3_0324": "deepseek/deepseek-chat-v3-0324",
    # 2026-09-21: round-4 wave 2. Frontier successors to the wave-1 roster.
    # Pinned versions only -- OpenRouter also exposes "~vendor/model-latest"
    # aliases, and a benchmark roster must never use one: the model behind it
    # changes silently and past results stop being attributable.
    "gpt_6_astra": "openai/gpt-6-astra",
    "claude_fable_5_1": "anthropic/claude-fable-5.1",
    "qwen3_8_max": "qwen/qwen3.8-max-0902",
    "muse_spark_1_3": "meta/muse-spark-1.3",
    "tencent_hy4": "tencent/hy4-preview",
    "gemini_3_8_flash": "google/gemini-3.8-flash",
    "deepseek_v4_1_flash": "deepseek/deepseek-v4.1-flash",
    "qwen3_8_flash": "qwen/qwen3.8-flash",
    "glm_5_3_flash": "z-ai/glm-5.3-flash",
    # 2026-09-21: wave 3. Missed in the wave-2 sweep -- the candidate list was
    # sorted by release date and truncated to the newest 40 of 114, and these
    # sit below that cut (Sonnet 5 2026-06-30, Opus 5 2026-07-24). Selecting
    # from a truncated view biased the roster toward recency over relevance.
    "claude_opus_5": "anthropic/claude-opus-5",
    "claude_sonnet_5": "anthropic/claude-sonnet-5",
    "gemini_3_7_flash": "google/gemini-3.7-flash",
    # 2026-09-21: Altworld/Hemmingway-1, a Qwen3.5-27B creative-writing
    # finetune with no OpenRouter listing. Served at bf16 from a rented H100
    # via vLLM, NOT quantised -- so unlike the local Q4_K_M attempt this card
    # is directly comparable to the rest of the roster, every one of which is
    # served at full precision. 4-bit degrades prose diversity and long-range
    # coherence, which are exactly the axes this benchmark scores.
    "hemmingway_1": "remote/Hemmingway-1",
    # 2026-09-24: wave 4. Everything OpenRouter listed between 2026-09-04 and
    # today that is a general-purpose chat model, pinned versions only.
    #
    # Three roster entries were dropped or repaired in the same pass:
    # openrouter/owl-alpha and thedrummer/rocinante-12b are no longer served
    # at all (other thedrummer models still are, so rocinante is specifically
    # delisted, not a vendor outage), and the Venice model lost its :free tier.
    # A delisted id fails the run rather than skipping the model, so these are
    # resolved before the wave rather than after it errors.
    #
    # GPT-6 is a family, not a model. Astra (already carded, 10/50) is the top
    # tier; Luna is a hundredth of its output price. Carding both ends decides
    # whether Astra's profile -- strong craft, worst-in-roster Youden's J --
    # belongs to the tier or to the family.
    "claude_opus_5_5": "anthropic/claude-opus-5.5",
    "gpt_6_sol": "openai/gpt-6-sol",
    "gpt_6_sol_pro": "openai/gpt-6-sol-pro",
    "gpt_6_luna": "openai/gpt-6-luna",
    "gpt_6_luna_pro": "openai/gpt-6-luna-pro",
    "grok_4_7": "x-ai/grok-4.7",
    "glm_5_3_prime": "z-ai/glm-5.3-prime",
    "glm_5_3_flashx": "z-ai/glm-5.3-flashx",
    "qwen3_8_max_prime": "qwen/qwen3.8-max-prime",
    "qwen3_8_omni_flash": "qwen/qwen3.8-omni-flash",
    "mimo_2_6_pro": "xiaomi/mimo-v2.6-pro",
    "mimo_2_6_flash": "xiaomi/mimo-v2.6-flash",
    "ember_1": "fireworks/ember-1",
    "command_a_plus": "cohere/command-a-plus",
    "aion_3_5": "aion-labs/aion-3.5",
    "fugu_max": "sakana/fugu-max",
    "mercury_2_5": "inception/mercury-2.5",
}

# Generation settings for test models
# max_tokens is a CEILING, not a target: a model that writes 400 tokens writes
# 400 tokens whatever this is set to. At 4096 it was silently truncating the
# reasoning models instead -- they spend the budget on thinking tokens that
# never reach the transcript, and the reply arrives empty or as a stub.
#
# Measured on one full-session context: tencent/hy4-preview returned 0
# characters for 4096 tokens, and 309 characters for 5212 when given room.
# Corpus-wide, 7 models burnt 12-96% of their turns this way, which is the
# whole of what the coverage gate was reading as models "dropping out".
#
# 16384 rather than a reasoning cap on purpose. Capping reasoning changes what
# the model does, and unevenly -- under a 512 cap glm-5.3-prime's prose got
# LONGER and hy4-preview's halved. A ceiling nobody reaches is one config for
# the whole roster; a cap is a different experiment per model.
GENERATION_CONFIG = {
    "temperature": 0.8,
    "max_tokens": 16384,
    "top_p": 0.95,
}

# Per-model generation overrides, merged over GENERATION_CONFIG at call time.
#
# Scoped per model on purpose: `reasoning_effort` is understood by Ollama's
# OpenAI-compatible endpoint, and sending it to an arbitrary cloud provider is
# a good way to earn a 400 on a paid run.
#
# Hemmingway-1 ships with thinking ON (its chat template defaults
# enable_thinking to true at reasoning effort "xhigh"). Left alone it spends
# the whole token budget reasoning and returns EMPTY content -- not degraded
# prose, none at all. Measured: default 31s and an empty reply, "none" 15s and
# clean narration.
# Keyed by the wire model id, not the roster key: run_session and the judges
# only ever see the id, so keying on the key would silently never match.
MODEL_CONFIG_OVERRIDES = {
    # Hemmingway-1's chat template defaults enable_thinking to true at
    # reasoning effort "xhigh". Left alone the model spends its whole token
    # budget reasoning: on Ollama it returned EMPTY content, and on vLLM the
    # reasoning lands in `content` and would be scored as the character's
    # prose. chat_template_kwargs drives the template variable directly.
    "remote/Hemmingway-1": {"chat_template_kwargs": {"enable_thinking": False}},
    "ollama/hemmingway-1-bench:latest": {"reasoning_effort": "none"},
}


# Judge settings (lower temp for consistent scoring)
JUDGE_CONFIG = {
    "temperature": 0.1,
    "max_tokens": 4096,
}

# Rate limiting
REQUEST_DELAY_SECONDS = 1.0
MAX_RETRIES = 3          # hard errors (bad JSON, malformed response, ...)
RETRY_DELAY_SECONDS = 5.0

# Transient failures (HTTP 429 and 5xx) get their own, much larger budget.
# A rate limit is a "wait longer" signal, not a failure, and it should not
# consume the same allowance as a malformed response. This matters more than
# it looks: one exhausted call kills an entire multi-turn session, so a 14-turn
# run is 26 consecutive chances to lose ~25 calls of completed work. Round 3
# lost 5 of Euryale's 20 sessions this way; round 4's P2 pilot lost both of
# Cydonia's Track A sessions at concurrency 4 AND serially.
MAX_TRANSIENT_RETRIES = 6
TRANSIENT_MAX_WAIT_SECONDS = 45.0
