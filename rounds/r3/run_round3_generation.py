"""Round-3 generation orchestrator. Runs three passes back-to-back:
  R3  NSFW multiturn      — ALL models (minus venice) x 20 NSFW seeds, dual judge
  R2  adversarial multiturn — 21 catch-up models x 20 adv seeds, sonnet judge
  R1  single-turn          — 21 catch-up models x 58 completion scenarios, standard
Venice (:free, 429s under load) is excluded — run it solo later at concurrency=1.
Each pass writes its own results file + a tagged copy; failures in one pass don't
abort the others.
"""
import json, time, traceback
from datetime import datetime, timezone
from harness.config import TEST_MODELS, RESULTS_DIR
from harness.multiturn import run_multiturn_benchmark
from harness.runner import run_benchmark

CONC = 10
VENICE = "venice_dolphin_24b"

# 22 models missing from round-1/round-2 (minus venice -> 21)
CATCHUP = [
    "claude_opus_4_8", "claude_sonnet_4_6", "gpt_5_5", "gemini_3_5_flash",
    "qwen3_7_max", "minimax_m3", "grok_4_3", "mistral_small_2603",
    "euryale_70b", "magnum_v4_72b", "cydonia_24b", "skyfall_36b",
    "lunaris_8b", "rocinante_12b", "unslopnemo_12b", "owl_alpha",
    "mimo_2_5_pro", "gemma_4_31b", "qwen3_6_35b_a3b", "qwen3_6_27b",
    "deepseek_v3_0324",
]
ALL_EX_VENICE = [k for k in TEST_MODELS if k != VENICE]
sub = lambda keys: {k: TEST_MODELS[k] for k in keys}


def banner(msg):
    print("\n" + "#" * 72 + f"\n# {msg}\n" + "#" * 72, flush=True)


def tag_copy(res, label):
    """Save a stable, named copy alongside the harness's timestamped file."""
    p = RESULTS_DIR / f"round3gen_{label}.json"
    with open(p, "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(f"  -> tagged copy: {p}", flush=True)


t_all = time.time()
summary = {}

# ---- PASS R3: NSFW multiturn, all models except venice, dual judge ----
banner(f"PASS R3 — NSFW multiturn | {len(ALL_EX_VENICE)} models x 20 seeds | conc={CONC}")
try:
    t0 = time.time()
    r3 = run_multiturn_benchmark(
        test_models=sub(ALL_EX_VENICE),
        judge_models={"claude_sonnet": "anthropic/claude-sonnet-4",
                      "deepseek_r1": "deepseek/deepseek-r1-0528"},
        num_turns=12, nsfw=True, concurrency=CONC,
    )
    tag_copy(r3, "R3_nsfw")
    okc = sum(1 for s in r3["sessions"] if "error" not in s)
    summary["R3"] = {"sessions": len(r3["sessions"]), "ok": okc, "min": round((time.time()-t0)/60, 1)}
except Exception:
    summary["R3"] = {"FAILED": traceback.format_exc()[-500:]}
    print(traceback.format_exc(), flush=True)

# ---- PASS R2: adversarial multiturn catch-up, sonnet judge, gemini sim ----
banner(f"PASS R2 — adversarial multiturn | {len(CATCHUP)} catch-up models x 20 seeds | conc={CONC}")
try:
    t0 = time.time()
    r2 = run_multiturn_benchmark(
        test_models=sub(CATCHUP),
        judge_models={"claude_sonnet": "anthropic/claude-sonnet-4"},
        num_turns=12, adversarial=True, concurrency=CONC,
    )
    tag_copy(r2, "R2_adversarial_catchup")
    okc = sum(1 for s in r2["sessions"] if "error" not in s)
    summary["R2"] = {"sessions": len(r2["sessions"]), "ok": okc, "min": round((time.time()-t0)/60, 1)}
except Exception:
    summary["R2"] = {"FAILED": traceback.format_exc()[-500:]}
    print(traceback.format_exc(), flush=True)

# ---- PASS R1: single-turn catch-up, standard rubric, sonnet judge ----
banner(f"PASS R1 — single-turn | {len(CATCHUP)} catch-up models x 58 completion | conc={CONC}")
try:
    t0 = time.time()
    r1 = run_benchmark(
        test_models=sub(CATCHUP),
        judge_models={"claude_sonnet": "anthropic/claude-sonnet-4"},
        scenario_types=["completion"], judge_mode="standard", concurrency=CONC,
    )
    tag_copy(r1, "R1_singleturn_catchup")
    okc = sum(1 for x in r1["results"] if "error" not in x)
    summary["R1"] = {"results": len(r1["results"]), "ok": okc, "min": round((time.time()-t0)/60, 1)}
except Exception:
    summary["R1"] = {"FAILED": traceback.format_exc()[-500:]}
    print(traceback.format_exc(), flush=True)

banner("ALL PASSES COMPLETE")
print(json.dumps(summary, indent=2), flush=True)
print(f"TOTAL wall: {round((time.time()-t_all)/60,1)} min", flush=True)
print("ORCHESTRATOR_DONE", flush=True)
