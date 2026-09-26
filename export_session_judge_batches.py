#!/usr/bin/env python3
"""Export whole sessions for subscription re-judging of the SUBJECTIVE block.

The 876 craft/adversarial sessions were judged once, by claude-sonnet-4 over
the API, and those scores feed the SUBJECTIVE dimensions on every profile card
(engagement <- S.3, tone_consistency <- S.1, collaboration <- S.4).

Adding new models judged by anything else would split that block across two
judges. Measured on the flaw hunter, two raters on one rubric and one session
agree at r = +0.20 with a 9.5-point systematic level shift -- so a split judge
is not a rounding difference, it is a different instrument. Re-judging the
whole corpus with one judge is the only way to add models and keep the block
readable.

Writes flaw-hunter-shaped batches; the rubric travels with them so a rater
never has to reconstruct it. The sonnet-4 scores stay untouched inside the
session files as a second rater.

Usage:
    python3 export_session_judge_batches.py [--batch-size 10]
"""
import argparse
import glob
import json
import shutil
from pathlib import Path

import harness.multiturn as multiturn


def _session_sources():
    """Newest craft run first, so a repair re-run supersedes what it repairs.

    Consumers dedupe with "first wins"; ascending order would let a broken
    earlier run outrank the re-run meant to replace it.
    """
    out = sorted(glob.glob("results/craft_baseline_*.json"), reverse=True)
    out.append("results/multiturn_merged_all_v2.json")
    return [p for p in out if Path(p).exists()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--out", default=None)
    ap.add_argument("--all", action="store_true",
                    help="re-batch everything, including sessions that already "
                         "have a score (a full re-judge, not an increment)")
    args = ap.parse_args()

    out_dir = Path(args.out) if args.out else None
    if out_dir is None:
        cands = [d for d in glob.glob(
            "/tmp/claude-1000/-home-levi-ST-VAUDEVILLE/*/scratchpad")
            if Path(d).is_dir()]
        if not cands:
            raise SystemExit("no scratchpad found; pass --out")
        # NOT judge_batches: export_judge_batches.py already owns that
        # directory for the per-turn pipeline (tag "work"). Two
        # pipelines in one scratch directory is how a glob in one
        # deletes the other's finished work.
        out_dir = Path(sorted(cands)[0]) / "session_judge_batches"

    # Rebuild from scratch, but never clobber finished work: outputs are kept.
    # An earlier exporter in this repo used OUT.glob("*.json") to clear the
    # directory and deleted completed results with it.
    out_dir.mkdir(parents=True, exist_ok=True)
    import re as _re
    _inp = _re.compile(r"/judge_\d{3}\.json$")
    for f in glob.glob(str(out_dir / "judge_*.json")):
        # Never delete an input whose output exists: that output is finished
        # work and the merge still needs the input to map session -> model.
        if _inp.search(f) and not Path(f.replace(".json", ".out.json")).exists():
            Path(f).unlink()

    items, seen = [], set()
    for src in _session_sources():
        for s in json.load(open(src))["sessions"]:
            if "error" in s or "dialogue" not in s:
                continue
            sid = "%s::%s" % (s["test_model"], s["seed_id"])
            if sid in seen:
                continue
            seen.add(sid)
            # The judge reads the whole dialogue, both sides, exactly as the
            # API judge did -- the session-level dimensions are about how the
            # character responds to the user, so stripping user turns would
            # change what S.4 even means.
            text = "".join(
                "\n**%s** (turn %s):\n%s\n"
                % (m.get("name"), m.get("turn"), m.get("content") or "")
                for m in s["dialogue"])
            items.append({
                "session_id": sid,
                "model": s["test_model"],
                "seed": s["seed_id"],
                "character_name": s["character_name"],
                "user_name": s["user_name"],
                "num_turns": s["num_turns"],
                "transcript": text,
            })

    # Skip what is already scored. Without this, adding 25 models re-batches
    # all 1376 sessions, the sort by session_id shifts every boundary, and the
    # 88 finished outputs no longer line up with any input file -- the merge
    # still works (it keys on session_id) but the "next:" list shows finished
    # work as pending and it gets judged a second time for nothing.
    done_ids = set()
    scored = Path("results/session_judge_v2.jsonl")
    if scored.exists() and not args.all:
        for line in open(scored):
            if line.strip():
                done_ids.add(json.loads(line)["session_id"])
    skipped = len([it for it in items if it["session_id"] in done_ids])
    items = [it for it in items if it["session_id"] not in done_ids]

    items.sort(key=lambda it: it["session_id"])
    batches = [items[i:i + args.batch_size]
               for i in range(0, len(items), args.batch_size)]
    # Continue the numbering past whatever is already on disk, so an existing
    # judge_007.out.json never ends up paired with a different judge_007.json.
    import re as _re2
    used = [int(m.group(1)) for f in glob.glob(str(out_dir / "judge_*.json"))
            for m in [_re2.search(r"judge_(\d{3})\.(?:out\.|recheck\.)?json$", f)]
            if m]
    start = (max(used) + 1) if used else 0
    for i, b in enumerate(batches, start):
        json.dump(b, open(out_dir / ("judge_%03d.json" % i), "w"),
                  ensure_ascii=False)

    rubric = multiturn.SESSION_JUDGE_SYSTEM
    (out_dir / "RUBRIC.md").write_text(rubric)

    done = len(glob.glob(str(out_dir / "judge_*.out.json")))
    print("exported %d sessions -> %d batches of %d  (numbered from %03d)"
          % (len(items), len(batches), args.batch_size, start))
    if skipped:
        print("  skipped %d session(s) already scored  (--all to re-batch them)"
              % skipped)
    print("  dir:     %s" % out_dir)
    print("  rubric:  %s  (%d chars, verbatim from harness.multiturn)"
          % (out_dir / "RUBRIC.md", len(rubric)))
    print("  already scored: %d batch(es)" % done)
    models = len({it["model"] for it in items})
    print("  models:  %d" % models)


if __name__ == "__main__":
    main()
