"""Follow-up passes, queued to fire AFTER rounds/r3/run_round3_generation.py finishes.
  1. Venice solo — venice_dolphin_24b across R3/R2/R1 at concurrency=1 (its
     :free endpoint 429s under load, so gentle 1s spacing + isolation).
  2. R1 flaw_hunter — the 21 catch-up models x 58 completion scenarios in
     flaw_hunter mode (feeds the composite 'flaw' component; standard mode
     was already done by the main run).
Waits for the main log to show 'ORCH_EXIT='; polls once a minute.
"""
import json, time, traceback
from harness import api
from harness.config import TEST_MODELS, RESULTS_DIR
from harness.multiturn import run_multiturn_benchmark
from harness.runner import run_benchmark

MAIN_LOG = RESULTS_DIR / "round3gen.log"
VENICE = "venice_dolphin_24b"
CATCHUP = [
    "claude_opus_4_8", "claude_sonnet_4_6", "gpt_5_5", "gemini_3_5_flash",
    "qwen3_7_max", "minimax_m3", "grok_4_3", "mistral_small_2603",
    "euryale_70b", "magnum_v4_72b", "cydonia_24b", "skyfall_36b",
    "lunaris_8b", "rocinante_12b", "unslopnemo_12b", "owl_alpha",
    "mimo_2_5_pro", "gemma_4_31b", "qwen3_6_35b_a3b", "qwen3_6_27b",
    "deepseek_v3_0324",
]
SONNET = {"claude_sonnet": "anthropic/claude-sonnet-4"}
DUAL = {"claude_sonnet": "anthropic/claude-sonnet-4",
        "deepseek_r1": "deepseek/deepseek-r1-0528"}
sub = lambda keys: {k: TEST_MODELS[k] for k in keys}


def banner(m):
    print("\n" + "#" * 72 + f"\n# {m}\n" + "#" * 72, flush=True)


def tag(res, label):
    p = RESULTS_DIR / f"round3gen_{label}.json"
    json.dump(res, open(p, "w"), indent=2, ensure_ascii=False)
    print(f"  -> tagged: {p}", flush=True)


def main_done():
    try:
        return "ORCH_EXIT=" in MAIN_LOG.read_text()
    except FileNotFoundError:
        return False


# ---- wait for the main orchestration ----
banner("FOLLOW-UP QUEUED — waiting for main run to finish")
mins = 0
while not main_done():
    time.sleep(60)
    mins += 1
    if mins % 30 == 0:
        print(f"  still waiting ({mins} min elapsed)...", flush=True)
print(f"main run finished after ~{mins} min wait — starting follow-up", flush=True)

summary = {}

# ---- 1. Venice solo, gentle spacing, all three rounds ----
api.set_min_interval(1.0)  # :free tier — keep it gentle regardless of prior state
vsub = sub([VENICE])
banner("VENICE SOLO — R3 NSFW (concurrency=1)")
try:
    r = run_multiturn_benchmark(test_models=vsub, judge_models=DUAL,
                                num_turns=12, nsfw=True, concurrency=1)
    tag(r, "venice_R3_nsfw")
    summary["venice_R3"] = sum(1 for s in r["sessions"] if "error" not in s)
except Exception:
    summary["venice_R3"] = "FAILED"; print(traceback.format_exc(), flush=True)

banner("VENICE SOLO — R2 adversarial (concurrency=1)")
try:
    r = run_multiturn_benchmark(test_models=vsub, judge_models=SONNET,
                                num_turns=12, adversarial=True, concurrency=1)
    tag(r, "venice_R2_adversarial")
    summary["venice_R2"] = sum(1 for s in r["sessions"] if "error" not in s)
except Exception:
    summary["venice_R2"] = "FAILED"; print(traceback.format_exc(), flush=True)

banner("VENICE SOLO — R1 single-turn standard (concurrency=1)")
try:
    r = run_benchmark(test_models=vsub, judge_models=SONNET,
                      scenario_types=["completion"], judge_mode="standard", concurrency=1)
    tag(r, "venice_R1_singleturn")
    summary["venice_R1"] = sum(1 for x in r["results"] if "error" not in x)
except Exception:
    summary["venice_R1"] = "FAILED"; print(traceback.format_exc(), flush=True)

# ---- 2. R1 flaw_hunter for the 21 catch-up models ----
banner(f"R1 FLAW_HUNTER — {len(CATCHUP)} catch-up models x 58 completion (concurrency=10)")
try:
    r = run_benchmark(test_models=sub(CATCHUP), judge_models=SONNET,
                      scenario_types=["completion"], judge_mode="flaw_hunter", concurrency=10)
    tag(r, "R1_flawhunter_catchup")
    summary["R1_flaw"] = sum(1 for x in r["results"] if "error" not in x)
except Exception:
    summary["R1_flaw"] = "FAILED"; print(traceback.format_exc(), flush=True)

banner("FOLLOW-UP COMPLETE")
print(json.dumps(summary, indent=2), flush=True)
print("FOLLOWUP_DONE", flush=True)
