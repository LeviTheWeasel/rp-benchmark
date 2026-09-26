#!/usr/bin/env python3
"""Per-model response coverage: how many turns the model actually answered.

Every other metric in the benchmark silently drops the turns a model did not
answer. The per-turn judging skips any reply under 50 characters, so an empty
turn is not scored as a failure -- it leaves the denominator entirely. The
effect runs the wrong way: the less a model says, the better it looks.

Measured over the corpus: 474 of 9636 model turns are empty or near-empty, and
they are not spread evenly. tencent_hy4 answered 10 of its 220 turns; its card
was being built from 4% of its data and read like an ordinary model with wide
intervals. glm_5_3_flash is two-thirds empty.

Round 4 already guards against this -- tencent_hy4 is excluded from that
leaderboard with "0 usable Track A exchanges". The cards had no equivalent.

Threshold: a model answering under 80% of turns is not comparable to one
answering all of them, because the turns it dropped are not a random sample --
they are disproportionately the hard ones late in a session.
"""
import json
from collections import Counter
from pathlib import Path


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

SOURCES = _session_sources()
MIN_CHARS = 50          # same bar the per-turn judging uses
EXCLUDE_BELOW = 0.80    # below this, rank position is not meaningful
OUT = Path("results/model_coverage.json")


def main():
    answered, total = Counter(), Counter()
    # Dedupe by session, newest source first. Without this a model that was
    # re-generated is counted TWICE -- once on the transcript being replaced
    # and once on its replacement -- and coverage reports the average of the
    # two. tencent_hy4 read 51.8% that way: 4% from the truncated run and 99%
    # from the repair. Every other consumer already had this rule; this one
    # never did, and it is the gate the others depend on.
    seen = set()
    for f in SOURCES:
        if not Path(f).exists():
            continue
        for s in json.load(open(f))["sessions"]:
            if "error" in s or "dialogue" not in s:
                continue
            sid = "%s::%s" % (s["test_model"], s["seed_id"])
            if sid in seen:
                continue
            seen.add(sid)
            m = s["test_model"]
            for msg in s["dialogue"]:
                if msg.get("role") != "character" or not msg.get("turn"):
                    continue
                total[m] += 1
                if len((msg.get("content") or "").strip()) >= MIN_CHARS:
                    answered[m] += 1

    rows = {m: {"answered": answered[m], "turns": total[m],
                "coverage": round(answered[m] / total[m], 4),
                "excluded": answered[m] / total[m] < EXCLUDE_BELOW}
            for m in total}
    OUT.write_text(json.dumps(
        {"min_chars": MIN_CHARS, "exclude_below": EXCLUDE_BELOW,
         "per_model": rows}, indent=1))

    bad = sorted((v["coverage"], m) for m, v in rows.items() if v["excluded"])
    print("response coverage over %d models, %d turns" % (len(rows), sum(total.values())))
    print("  excluded below %.0f%%: %d model(s)" % (100 * EXCLUDE_BELOW, len(bad)))
    for cov, m in bad:
        print("    %-22s %5.1f%%  (%d of %d turns answered)"
              % (m, 100 * cov, rows[m]["answered"], rows[m]["turns"]))
    low = sorted((v["coverage"], m) for m, v in rows.items()
                 if not v["excluded"] and v["coverage"] < 1.0)[:6]
    if low:
        print("  below 100%% but retained:")
        for cov, m in low:
            print("    %-22s %5.1f%%" % (m, 100 * cov))
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
