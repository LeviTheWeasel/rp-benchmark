"""Compare DeepSeek variants as the USER SIMULATOR (vs Cydonia baseline).
Same seed + same explicit character (Cydonia, to force explicit context),
swap only the simulator. We care about the SIM-USER turns:
  - stays SHORT (sim prompt asks 1-4 sentences)?
  - stays in character / pushes the scene?
  - handles explicit context without soft-refusal?
"""
import json
from harness import multiturn
from harness.config import PROJECT_ROOT

SEED_ID = "adv_nsfw_midscene_refusal_02"
CHAR = "thedrummer/cydonia-24b-v4.1"        # forces explicit context
SHORT_TURNS = 5                              # yields ~2 free sim turns
SIMS = [
    "deepseek/deepseek-v3.2",
    "deepseek/deepseek-v4-flash",
    "deepseek/deepseek-v4-pro",
]

seed = {s["id"]: s for s in json.load(
    open(PROJECT_ROOT / "hf_dataset/_source/adversarial_seeds_nsfw.json"))}[SEED_ID]

out = []
for sim in SIMS:
    print("\n" + "=" * 70 + "\nSIM = %s\n" % sim + "=" * 70)
    try:
        sess = multiturn.run_session(seed, CHAR, sim, num_turns=SHORT_TURNS)
        sess["sim_model"] = sim
        out.append(sess)
    except Exception as e:
        print("  RUN ERROR:", e)
        out.append({"sim_model": sim, "error": str(e)})

json.dump(out, open(PROJECT_ROOT / "results/dryrun_sim_compare.json", "w"),
          indent=2, ensure_ascii=False)
print("\nSaved -> results/dryrun_sim_compare.json")
