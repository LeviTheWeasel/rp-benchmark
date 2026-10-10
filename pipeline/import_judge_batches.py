#!/usr/bin/env python3
"""Merge subagent verdicts into a single-rater label file.

Writes results/per_turn_failures_v2.jsonl and leaves the Sonnet labels in
per_turn_failures.jsonl untouched. Two reasons: the Sonnet pass is already paid
for and stays usable as a second rater for agreement, and a re-judge that
overwrote it would make the earlier agreement numbers unreproducible.

Idempotent -- re-running merges whatever new .out.json files exist. The corpus
is 4746 checks against a session budget that only just covers it, so the work
is built to stop anywhere and resume in another session without losing a verdict.
"""
import glob, json
from pathlib import Path

OUT = Path("results/per_turn_failures_v2.jsonl")


def main():
    base = glob.glob("/tmp/claude-1000/-home-levi-ST-VAUDEVILLE/*/scratchpad/judge_batches")
    base = [b for b in base if glob.glob(b + "/work_*.json")]
    if not base:
        raise SystemExit("no batch directory found")
    b = base[0]

    have = set()
    if OUT.exists():
        for line in open(OUT):
            r = json.loads(line)
            have.add((r["session_id"], r["turn"], r["mode"]))

    # model/seed come from the INPUT batch: the rater only echoes identifiers,
    # and re-deriving them from session_id would guess at underscores in names.
    meta = {}
    for f in glob.glob(b + "/work_*.json"):
        if ".out." in f:
            continue
        for it in json.load(open(f)):
            meta[(it["session_id"], it["turn"], it["mode"])] = (it["model"], it["seed"])

    added = 0
    with open(OUT, "a") as fh:
        for f in sorted(glob.glob(b + "/work_*.out.json")):
            try:
                rows = json.load(open(f))
            except Exception:
                print("  unreadable, skipped:", Path(f).name)
                continue
            for r in rows:
                key = (r["session_id"], r["turn"], r["mode"])
                if key in have or key not in meta:
                    continue
                model, seed = meta[key]
                fh.write(json.dumps({
                    "session_id": r["session_id"], "model": model, "seed": seed,
                    "turn": r["turn"], "mode": r["mode"],
                    "is_failure": bool(r["is_failure"]),
                    "verdict": r.get("verdict"),
                    "reason": (r.get("reason") or "")[:300],
                    "judge": "subagent-rater-v1"}) + "\n")
                have.add(key)
                added += 1

    total_in = sum(len(json.load(open(f))) for f in glob.glob(b + "/work_*.json")
                   if ".out." not in f)
    done_files = len(glob.glob(b + "/work_*.out.json"))
    all_files = len([f for f in glob.glob(b + "/work_*.json")
                     if ".out." not in f])
    print("merged %d new verdicts -> %s" % (added, OUT))
    # No percentage here on purpose. The old line divided total labels by the
    # CURRENT export's size, which the incremental exporter made the unscored
    # remainder -- so a complete corpus printed "269.4%".
    print("  labels on file: %d  (this run added %d)" % (len(have), added))
    print("  batches judged: %d of %d" % (done_files, all_files))
    remaining = [Path(f).stem for f in sorted(glob.glob(b + "/work_*.json"))
                 if ".out." not in f
                 and not Path(f.replace(".json", ".out.json")).exists()]
    if remaining:
        print("  next unjudged: %s" % ", ".join(remaining[:10]))


if __name__ == "__main__":
    main()
