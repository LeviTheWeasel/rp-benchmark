#!/usr/bin/env python3
"""Does the subagent rater agree with ITSELF on identical items?

The Sonnet comparison answered a different question. It asked "can the two
raters be mixed", and the answer was no -- kappa 0.565 pooled, with F3 and F5
diverging in opposite directions. But once the whole corpus is re-judged by one
rater, Sonnet's labels are not the reference any more: they were produced under
rubrics that have since been corrected, so disagreement with them now partly
MEANS the correction landed.

For a single-rater corpus the validity question is reproducibility. Two
independent passes over byte-identical items, neither seeing the other, are
compared here. If they diverge, no change of rater fixes it and the rubric
itself is too loose to carry a number.
"""
import glob, json
from collections import defaultdict

from rounds.r4.analyze_r4_kappa import cohens_kappa


def load(pattern):
    out = {}
    for f in sorted(glob.glob(pattern)):
        for r in json.load(open(f)):
            out[(r["session_id"], r["turn"], r["mode"])] = bool(r["is_failure"])
    return out


def main():
    base = glob.glob("/tmp/claude-1000/-home-levi-ST-VAUDEVILLE/*/scratchpad/judge_batches")
    base = [b for b in base if glob.glob(b + "/cal_10*.out.json")]
    if not base:
        raise SystemExit("second-pass outputs (cal_10*.out.json) not found yet")
    b = base[0]
    a_pass = load(b + "/cal_00*.out.json")
    a_pass.update(load(b + "/cal_001.out.json"))
    b_pass = load(b + "/cal_10*.out.json")

    pairs, by_mode = [], defaultdict(list)
    for k, va in a_pass.items():
        if k not in b_pass:
            continue
        p = (str(va), str(b_pass[k]))
        pairs.append(p)
        by_mode[k[2]].append(p)

    print("=" * 72)
    print("  RATER SELF-CONSISTENCY  (two independent passes, identical items)")
    print("=" * 72)
    print("  compared %d items\n" % len(pairs))
    k = cohens_kappa(pairs)
    print("  POOLED   kappa %s   agreement %.3f" % (k.get("kappa"), k["observed"]))
    print("\n  %-30s %4s %8s %9s %8s %7s" % ("mode", "n", "kappa", "agree", "pass A", "pass B"))
    for mode in sorted(by_mode):
        g = by_mode[mode]
        kk = cohens_kappa(g)
        ra = sum(1 for x, y in g if x == "True") / len(g)
        rb = sum(1 for x, y in g if y == "True") / len(g)
        print("  %-30s %4d %8s %9.3f %7.0f%% %6.0f%%"
              % (mode, len(g), kk.get("kappa"), kk["observed"], 100 * ra, 100 * rb))
    dis = [(x, y) for x, y in pairs if x != y]
    print("\n  disagreements: %d of %d (%.1f%%)"
          % (len(dis), len(pairs), 100 * len(dis) / max(len(pairs), 1)))
    print("\n  Read this as the ceiling on any number the corpus can carry: a rate")
    print("  measured once cannot be more reliable than the rater is with itself.")


if __name__ == "__main__":
    main()
