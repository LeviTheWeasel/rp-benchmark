#!/usr/bin/env python3
"""Agreement between the subagent rater and the existing Sonnet labels.

OpenRouter credit ran out with 4233 of ~7200 per-turn checks labelled by
claude-sonnet-4, and every one of the 25 models is partially judged. Finishing
with a different rater therefore builds each model's failure rate out of two
instruments, which is the defect that made round 3's rubric axis unreadable.

This measures the cost of that before any new label is used. The reference
labels were held in a separate file the raters never saw.

Read the per-mode rows, not just the pooled number: F1 and F2 are 70% of the
corpus and would otherwise dominate a single figure, and the modes with 2-3
probes per model are exactly where a rater disagreement changes a card.
"""
import glob, json
from collections import defaultdict

from analyze_r4_kappa import cohens_kappa


def main():
    # Pick the scratchpad that actually holds the answers: several session
    # directories exist and the first glob hit is not necessarily this run's.
    hits = glob.glob("/tmp/claude-1000/-home-levi-ST-VAUDEVILLE/*/scratchpad/cal_answers.json")
    if not hits:
        raise SystemExit("cal_answers.json not found -- run export_judge_batches.py --calibration")
    base = hits[0].rsplit("/", 1)[0]
    answers = json.load(open(hits[0]))
    got = {}
    for f in sorted(glob.glob(base + "/judge_batches/cal_*.out.json")):
        for r in json.load(open(f)):
            got[(r["session_id"], r["turn"], r["mode"])] = bool(r["is_failure"])

    pairs, by_mode = [], defaultdict(list)
    missing = 0
    for k, ref in answers.items():
        sid, turn, mode = k.rsplit("|", 2)
        key = (sid, int(turn), mode)
        if key not in got:
            missing += 1
            continue
        pair = (str(bool(ref)), str(got[key]))
        pairs.append(pair)
        by_mode[mode].append(pair)

    print("=" * 74)
    print("  SUBAGENT RATER vs SONNET  (Sonnet = reference, not ground truth)")
    print("=" * 74)
    print("  judged %d of %d calibration items%s"
          % (len(pairs), len(answers),
             ("  (%d not returned)" % missing) if missing else ""))
    k = cohens_kappa(pairs)
    agree = k["observed"]
    sref = sum(1 for a, b in pairs if a == "True") / max(len(pairs), 1)
    snew = sum(1 for a, b in pairs if b == "True") / max(len(pairs), 1)
    print("\n  POOLED   kappa %s   agreement %.3f   Sonnet %.1f%% vs agent %.1f%%"
          % (k.get("kappa"), agree, 100 * sref, 100 * snew))

    print("\n  %-28s %4s %8s %9s %8s %7s" % ("mode", "n", "kappa", "agree", "Sonnet", "agent"))
    for mode in sorted(by_mode):
        g = by_mode[mode]
        kk = cohens_kappa(g)
        a = sum(1 for x, y in g if x == "True") / len(g)
        b = sum(1 for x, y in g if y == "True") / len(g)
        flag = ""
        if kk.get("kappa") is not None and kk["kappa"] < 0.6:
            flag = "  <-- low"
        print("  %-28s %4d %8s %9.3f %7.0f%% %6.0f%%%s"
              % (mode, len(g), kk.get("kappa"), kk["observed"], 100 * a, 100 * b, flag))

    dis = [(a, b) for a, b in pairs if a != b]
    print("\n  disagreements: %d of %d (%.1f%%)"
          % (len(dis), len(pairs), 100 * len(dis) / max(len(pairs), 1)))
    print("    Sonnet=True  agent=False : %d" % sum(1 for a, b in dis if a == "True"))
    print("    Sonnet=False agent=True  : %d" % sum(1 for a, b in dis if a == "False"))
    print("\n  Note: kappa is unstable where one class is rare -- read it beside the")
    print("  two rate columns, which is what made the F2 comparison unreadable.")


if __name__ == "__main__":
    main()
