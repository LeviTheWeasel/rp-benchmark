"""Cleanup pass — queued to fire AFTER rounds/r3/run_round3_followup.py finishes.
Scans every tagged round-3 result file for errored (seed/scenario, model)
entries, re-runs ONLY those with the matching per-pass config (fresh process =
hardened api.py), and merges recoveries back into the files (.bak backups).
Waits for 'FOLLOWUP_EXIT=' in the follow-up log (which itself waited for main).
"""
import json, shutil, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from harness import api
from harness.config import TEST_MODELS, RESULTS_DIR
from harness.multiturn import run_session, judge_session, load_seeds
from harness.runner import run_benchmark, run_single_scenario, load_benchmark

FOLLOWUP_LOG = RESULTS_DIR / "round3followup.log"
SONNET = {"claude_sonnet": "anthropic/claude-sonnet-4"}
DUAL = {"claude_sonnet": "anthropic/claude-sonnet-4",
        "deepseek_r1": "deepseek/deepseek-r1-0528"}
MT, ST = "multiturn", "singleturn"

# Per-file recipe, keyed by tagged filename (we named them, so this is exact).
FILES = {
    "round3gen_R3_nsfw.json":              dict(kind=MT, sim="deepseek/deepseek-v3.2",   nsfw=True,  turns=12, judges=DUAL,   seeds="nsfw"),
    "round3gen_R2_adversarial_catchup.json": dict(kind=MT, sim="google/gemini-2.5-flash", nsfw=False, turns=12, judges=SONNET, seeds="adv"),
    # Venice (:free) is unrecoverable — endpoint 429s on every attempt (R3 was
    # 0/20). Skipped so cleanup doesn't churn re-failing it / trip the tripwire.
    "round3gen_R1_singleturn_catchup.json": dict(kind=ST, mode="standard",    judges=SONNET),
    "round3gen_R1_flawhunter_catchup.json": dict(kind=ST, mode="flaw_hunter", judges=SONNET),
}


def banner(m): print("\n" + "#" * 72 + f"\n# {m}\n" + "#" * 72, flush=True)
def followup_done():
    try: return "FOLLOWUP_EXIT=" in FOLLOWUP_LOG.read_text()
    except FileNotFoundError: return False


banner("CLEANUP QUEUED — waiting for follow-up to finish")
mins = 0
while not followup_done():
    time.sleep(60); mins += 1
    if mins % 30 == 0: print(f"  still waiting ({mins} min)...", flush=True)
print(f"follow-up finished after ~{mins} min wait — scanning for errors", flush=True)

# seed / scenario lookups
seedmap = {"nsfw": {s["id"]: s for s in load_seeds(nsfw=True)},
           "adv":  {s["id"]: s for s in load_seeds(adversarial=True)}}
scenmap = {s["id"]: s for s in load_benchmark()["scenarios"]["completion"]}

# 1) collect errored entries across all files
tasks = []
for fname, cfg in FILES.items():
    path = RESULTS_DIR / fname
    if not path.exists():
        print(f"  [skip] {fname} (not found)", flush=True); continue
    d = json.load(open(path))
    entries = d.get("sessions" if cfg["kind"] == MT else "results", [])
    errs = [e for e in entries if isinstance(e, dict) and "error" in e]
    print(f"  {fname}: {len(errs)} errored", flush=True)
    for e in errs:
        tasks.append((fname, cfg, e))
print(f"\nTOTAL errored (seed/scenario,model) pairs to recover: {len(tasks)}", flush=True)

if not tasks:
    banner("CLEANUP — nothing to recover"); print("CLEANUP_DONE", flush=True); raise SystemExit

# 2) re-run each, gently (hardened api + 0.5s spacing)
api.set_min_interval(0.5)

def recover(fname, cfg, e):
    try:
        if cfg["kind"] == MT:
            seed = seedmap[cfg["seeds"]][e["seed_id"]]
            mid = e.get("test_model_id") or TEST_MODELS[e["test_model"]]
            sess = run_session(seed, mid, cfg["sim"], cfg["turns"], verbose=False)
            sess["test_model"] = e["test_model"]; sess["test_model_id"] = mid
            sess["judges"] = {jk: judge_session(sess, jid, nsfw=cfg["nsfw"])
                              for jk, jid in cfg["judges"].items()}
            return (fname, ("seed_id", e["seed_id"], e["test_model"]), sess)
        else:
            scen = scenmap[e["scenario_id"]]
            mid = TEST_MODELS[e["test_model"]]
            res = run_single_scenario(scen, e["test_model"], mid, cfg["judges"],
                                      judge_mode=cfg["mode"], verbose=False)
            return (fname, ("scenario_id", e["scenario_id"], e["test_model"]), res)
    except Exception as ex:
        return (fname, None, {"error": str(ex), "_orig": e})

recovered = {}   # fname -> list of (matchkey, entry)
done = 0
with ThreadPoolExecutor(max_workers=4) as ex:
    futs = [ex.submit(recover, f, c, e) for f, c, e in tasks]
    for fut in as_completed(futs):
        fname, key, entry = fut.result()
        done += 1
        good = key is not None and "error" not in entry
        print(f"  [{done}/{len(tasks)}] {fname} {key} -> {'recovered' if good else 'still failing'}", flush=True)
        if good:
            recovered.setdefault(fname, []).append((key, entry))

# 3) merge recoveries back into each file (with .bak), replacing the error rows
banner("MERGING RECOVERIES")
report = {}
for fname, recs in recovered.items():
    path = RESULTS_DIR / fname
    shutil.copy(path, path.with_suffix(".json.bak"))  # back up the ORIGINAL first
    d = json.load(open(path))
    listkey = "sessions" if FILES[fname]["kind"] == MT else "results"
    entries = d[listkey]
    idfield = recs[0][0][0]  # 'seed_id' or 'scenario_id'
    rmap = {(k[1], k[2]): v for k, v in recs}  # (id, model) -> new entry
    replaced = 0
    for i, en in enumerate(entries):
        if isinstance(en, dict) and "error" in en:
            mk = (en.get(idfield), en.get("test_model"))
            if mk in rmap:
                entries[i] = rmap[mk]; replaced += 1
    json.dump(d, open(path, "w"), indent=2, ensure_ascii=False)
    report[fname] = {"recovered": replaced}
    print(f"  {fname}: merged {replaced} recoveries (backup: {path.name}.bak)", flush=True)

still = len(tasks) - sum(r["recovered"] for r in report.values())
banner("CLEANUP COMPLETE")
print(json.dumps({"attempted": len(tasks), "recovered": sum(r['recovered'] for r in report.values()),
                  "still_failing": still, "by_file": report}, indent=2), flush=True)
json.dump(report, open(RESULTS_DIR / "round3gen_cleanup_report.json", "w"), indent=2)
print("CLEANUP_DONE", flush=True)
