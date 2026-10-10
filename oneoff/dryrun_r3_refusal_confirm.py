"""Round-3 refusal-axis confirmation: run a midscene_refusal seed with
frontier models likely to pull back, plus a willing control, and verify the
new judge `refusal` object actually registers (and discriminates).
"""
import json
from harness.multiturn import run_multiturn_benchmark
from harness.config import PROJECT_ROOT

SEED = "adv_nsfw_midscene_refusal_02"   # explicit-continue bait at challenge turn 4
res = run_multiturn_benchmark(
    test_models={
        "gemini_2_5_flash": "google/gemini-2.5-flash",   # likely refuser
        "claude_sonnet_4_5": "anthropic/claude-sonnet-4.5",  # likely soft pull-back
        "deepseek_v3_2": "deepseek/deepseek-v3.2",       # willing control
    },
    judge_models={"deepseek_r1": "deepseek/deepseek-r1-0528"},
    user_sim_model="deepseek/deepseek-v3.2",
    seed_ids=[SEED],
    num_turns=6,
    nsfw=True,
)

summary = []
for s in res["sessions"]:
    if "error" in s:
        summary.append({"model": s.get("test_model"), "error": s["error"]})
        continue
    sc = s["judges"]["deepseek_r1"]["scores"]
    sd = sc.get("session_dimensions", {})
    # character response to the explicit-continue bait (first char turn after turn 7)
    post = next((m["content"] for m in s["dialogue"]
                 if m["role"] == "character" and m["turn"] >= 8), "")
    summary.append({
        "model": s["test_model"],
        "refusal": sc.get("refusal"),
        "S9_consent_agency": sd.get("S.9_consent_agency_intimacy", {}).get("score"),
        "overall": sc.get("overall"),
        "post_bait_char_turn": " ".join(post.split())[:500],
    })

out = {"seed": SEED, "sim": res["config"]["user_sim_model"], "summary": summary}
json.dump(out, open(PROJECT_ROOT / "results/dryrun_r3_refusal_confirm.json", "w"),
          indent=2, ensure_ascii=False)
print("WROTE_SUMMARY results/dryrun_r3_refusal_confirm.json")
for r in summary:
    print("\n###", r.get("model"))
    if "error" in r:
        print("  ERROR:", r["error"]); continue
    print("  refusal:", r["refusal"])
    print("  S.9:", r["S9_consent_agency"], "| overall:", r["overall"])
    print("  post-bait char turn:", r["post_bait_char_turn"][:300])
print("\nDONE_REFUSAL_CONFIRM")
