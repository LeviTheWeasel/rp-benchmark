"""(A) Re-test the EMPTY-returning models with the REAL generation budget
(max_tokens=4096) to see if the empties were just a low-token ping artifact.
(B) Smoke-test the new --concurrency path end-to-end and time it.
"""
import json, time
from harness.api import chat_completion
from harness.config import TEST_MODELS, GENERATION_CONFIG, PROJECT_ROOT
from harness.multiturn import run_multiturn_benchmark

print("=== (A) re-test EMPTY models with max_tokens=4096 ===")
SYS = "You are roleplaying as Mara, a confident adult woman. Third-person past tense."
USER = '[Continue as Mara, 2-3 sentences.]\n\nMara: "Come here," she said.'
for key in ["glm_4_7", "kimi_k2_5", "kimi_k2_6"]:
    mid = TEST_MODELS[key]
    t0 = time.time()
    try:
        r = chat_completion(mid, SYS, USER, GENERATION_CONFIG)
        c = (r.get("content") or "").strip()
        reasoning = r["raw"]["choices"][0]["message"].get("reasoning")
        print(f"  {key:<14} chars={len(c):<5} reasoning_field={'yes' if reasoning else 'no'} "
              f"{round(time.time()-t0,1)}s :: {' '.join(c.split())[:70]}")
    except Exception as e:
        print(f"  {key:<14} ERROR {str(e)[:80]}")

print("\n=== (B) concurrency smoke (4 models x 1 seed, concurrency=4, nsfw, 4 turns) ===")
t0 = time.time()
res = run_multiturn_benchmark(
    test_models={k: TEST_MODELS[k] for k in
                 ["gemma_4_26b", "mistral_small_2603", "llama_4_maverick", "gemini_3_1_flash_lite"]},
    judge_models={"deepseek_r1": "deepseek/deepseek-r1-0528"},
    seed_ids=["adv_nsfw_pacing_voice_18"],
    num_turns=4,
    nsfw=True,
    concurrency=4,
)
dt = time.time() - t0
ok = [s for s in res["sessions"] if "error" not in s]
perr = [s["test_model"] for s in ok
        if any(jd["scores"].get("parse_error") for jd in s["judges"].values())]
print(f"\n  sessions={len(res['sessions'])} ok={len(ok)} parse_errors={perr or 'none'} "
      f"wall={dt:.1f}s  config.concurrency={res['config']['concurrency']}")
# name-strip spot check across all char turns
import re
leaks = []
for s in ok:
    for m in s["dialogue"]:
        if m["role"] == "character" and re.match(r"^\s*%s\s*:" % s["character_name"], m["content"]):
            leaks.append(s["test_model"])
print("  name-prefix leaks:", set(leaks) or "none")
print("VERIFY_DONE")
