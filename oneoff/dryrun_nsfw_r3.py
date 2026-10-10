"""Round-3 NSFW dry run: generate 1-2 sessions with Cydonia as user simulator,
score with the permissive judge (DeepSeek R1). Sanity-checks, NOT a real run:
  1. Does the user simulator stay in explicit character (no soft-refusal)?
  2. Do the scripted challenge turns fire at the right places?
  3. Will the judge score explicit content without refusing / parse OK?
Sessions are shortened (num_turns override) to keep cost/time low.
"""
import json
import sys
from pathlib import Path

from harness import multiturn
from harness.config import PROJECT_ROOT

SIM_MODEL = "thedrummer/cydonia-24b-v4.1"          # candidate user simulator
JUDGE_MODEL = "deepseek/deepseek-r1-0528"          # candidate permissive judge
SHORT_TURNS = 6                                     # covers challenge turns at 2/4/6

# (seed_id, character/test model) — pick a willing char model so the scene
# actually goes explicit and we can observe the simulator under those conditions.
RUNS = [
    ("adv_nsfw_consent_intimate_01", "deepseek/deepseek-v3.2"),   # roster model
    ("adv_nsfw_midscene_refusal_02", SIM_MODEL),                  # guarantee explicit
]

seeds = json.load(open(PROJECT_ROOT / "hf_dataset/_source/adversarial_seeds_nsfw.json"))
by_id = {s["id"]: s for s in seeds}

out = {"sim_model": SIM_MODEL, "judge_model": JUDGE_MODEL, "sessions": []}

for seed_id, char_model in RUNS:
    seed = by_id[seed_id]
    print("\n" + "=" * 70)
    print("SEED %s | char=%s | sim=%s | turns=%d"
          % (seed_id, char_model, SIM_MODEL, SHORT_TURNS))
    print("=" * 70)
    session = multiturn.run_session(seed, char_model, SIM_MODEL, num_turns=SHORT_TURNS)
    session["test_model"] = char_model

    print("  -> judging with %s ..." % JUDGE_MODEL)
    try:
        judged = multiturn.judge_session(session, JUDGE_MODEL)
        session["judge"] = judged
        parse_ok = "parse_error" not in (judged.get("scores", judged) or {})
        print("  -> judge returned (parse_ok=%s)" % parse_ok)
    except Exception as e:
        session["judge_error"] = str(e)
        print("  -> JUDGE ERROR: %s" % e)

    out["sessions"].append(session)

dest = PROJECT_ROOT / "results/dryrun_nsfw_r3.json"
json.dump(out, open(dest, "w"), indent=2, ensure_ascii=False)
print("\nSaved -> %s" % dest)
