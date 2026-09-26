#!/usr/bin/env python3
"""Export whole-session flaw-hunter work as self-contained subagent batches.

Same reasoning as the per-turn re-judge: 500 of 876 sessions carry Sonnet
scores and 43 of 47 models have gaps, so finishing with a second rater would
build almost every model's flaw-hunter mean from two instruments. The per-turn
measurement put the cost of that mixing at pooled kappa 0.565, with individual
modes moving up to 24 points. So the whole corpus is re-scored by one rater and
the Sonnet pass is kept intact in its own file as a second opinion.

Batches are small (12 sessions) because each item carries a full transcript and
returns a structured flaw list, not a boolean.

Usage: python3 export_flaw_batches.py [--batch-size 12]
"""
import argparse, json
from pathlib import Path

from judge_session_flaw_hunter import build_transcript, TARGET_PRIMERS


def _session_sources():
    """Every generation run on disk, newest last.

    Hardcoding dated filenames meant a new craft-baseline or round-4 run
    silently never reached the judges: the file exists, the models are in it,
    and every downstream script keeps reporting the old roster as complete.
    Globbing makes a new run visible the moment it lands.
    """
    import glob as _g
    from pathlib import Path as _P
    # NEWEST FIRST, and that ordering is load-bearing.
    #
    # Every consumer dedupes by session_id with "first wins". With files in
    # ascending date order, re-running a model to repair a broken run would
    # write a newer file whose sessions were then silently discarded in favour
    # of the broken ones -- the re-run costs money and changes nothing, and
    # the coverage number it was meant to fix stays exactly where it was.
    #
    # Round-4 ladder files are deliberately excluded: the flaw hunter and the
    # eleven per-turn modes are defined over the adversarial seeds, not the
    # willingness rungs, and pulling r4 in here would silently change the
    # 876-session denominator they are all reported against.
    out = sorted(_g.glob("results/craft_baseline_*.json"), reverse=True)
    out.append("results/multiturn_merged_all_v2.json")
    return [p for p in out if _P(p).exists()]

OUT = Path("/tmp/claude-1000/-home-levi-ST-VAUDEVILLE/0e0eeb99-f00a-4b4d-87ff-9f01392fa806/scratchpad/flaw_batches")
SOURCES = _session_sources()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=12)
    ap.add_argument("--all", action="store_true",
                    help="re-batch everything, including scored sessions")
    args = ap.parse_args()

    seeds = {}
    for f in ("adversarial_seeds.json", "adversarial_seeds_v2.json",
              "adversarial_seeds_v3_bigcard.json"):
        p = Path("hf_dataset/_source") / f
        if p.exists():
            for s in json.load(open(p)):
                seeds[s["id"]] = s

    items, seen = [], set()
    for src in SOURCES:
        if not Path(src).exists():
            continue
        for s in json.load(open(src))["sessions"]:
            if "error" in s or "dialogue" not in s:
                continue
            sid = "%s::%s" % (s["test_model"], s["seed_id"])
            if sid in seen:
                continue
            seen.add(sid)
            seed = seeds.get(s["seed_id"], {})
            items.append({
                "session_id": sid,
                "model": s["test_model"],
                "seed": s["seed_id"],
                "character": s.get("character_name", "?"),
                "user": s.get("user_name", "?"),
                # The seed's declared failure target and the primer that goes
                # with it. The key is `failure_target`; an earlier version of
                # this exporter looked for `failure_mode`/`category`, found
                # neither, and shipped "general" for every session -- stripping
                # out exactly the target-awareness the rubric is built around.
                "target": seed.get("failure_target", "general"),
                "target_primer": TARGET_PRIMERS.get(seed.get("failure_target", ""), ""),
                "transcript": build_transcript(s),
            })

    OUT.mkdir(parents=True, exist_ok=True)
    # Only the INPUT batches are cleared. The first version globbed "*.json",
    # which also matched the raters' `.out.json` results and silently deleted
    # completed work mid-run -- a rater noticed its own output vanish and said
    # so, which is the only reason it was caught.
    # Skip what already has a score. Without this the exporter re-batches the
    # whole corpus every run: 1328 sessions in 111 batches when 829 of them
    # were already judged, which is a day of subagent time spent re-deciding
    # settled questions. Same rule the session-judge exporter uses.
    done_ids = set()
    scored = Path("results/session_flaw_hunter_v2.jsonl")
    if scored.exists() and not args.all:
        for line in open(scored):
            if line.strip():
                done_ids.add(json.loads(line)["session_id"])
    skipped = len([it for it in items if it["session_id"] in done_ids])
    items = [it for it in items if it["session_id"] not in done_ids]

    # Only clear inputs that have no finished output beside them.
    import re as _re
    _inp = _re.compile(r"flaw_\d{3}\.json$")
    for f in OUT.glob("flaw_*.json"):
        if _inp.search(f.name) and not f.with_suffix(".out.json").exists():
            f.unlink()
    # Number past whatever is on disk so an existing flaw_007.out.json is
    # never paired with a different flaw_007.json.
    used = [int(m.group(1)) for f in OUT.glob("flaw_*.json")
            for m in [_re.search(r"flaw_(\d{3})\.", f.name)] if m]
    start = (max(used) + 1) if used else 0
    n = start
    for i in range(0, len(items), args.batch_size):
        (OUT / ("flaw_%03d.json" % n)).write_text(
            json.dumps(items[i:i + args.batch_size], indent=1))
        n += 1
    ch = sum(len(it["transcript"]) for it in items)
    print("wrote %d sessions in %d batches (numbered from %03d) -> %s"
          % (len(items), n - start, start, OUT))
    if skipped:
        print("  skipped %d already scored  (--all to re-batch them)" % skipped)
    print("  transcript volume: %.1fM chars (~%.1fM tokens)" % (ch / 1e6, ch / 3.6e6))
    (OUT.parent / "flaw_rubric.md").write_text(Path("prompts/judge_flaw_hunter.md").read_text())
    print("  rubric copied to %s" % (OUT.parent / "flaw_rubric.md"))


if __name__ == "__main__":
    main()
