#!/usr/bin/env python3
"""Aggregate per-session flaw hunter scores into per-model and per-target stats.

Reads results/session_flaw_hunter.jsonl produced by
judge_session_flaw_hunter.py. Outputs:

  - results/flaw_hunter_session_summary.json — per-model and per-target
    aggregates with mean, std, n, fatal/major/minor counts, top flaws.
  - Console table sorted by per-model mean score.

With --rater v2 it reads session_flaw_hunter_v2.jsonl (the single-rater
re-score) and writes flaw_hunter_session_summary_v2.json instead. The two
files stay separate on purpose: five other analyses -- composite score, cost
efficiency, method correlations, quality/speed -- already consume the Sonnet
summary, and overwriting it in place would silently restate their published
numbers under a different rater.

Usage:
    python3 analyze_flaw_hunter_sessions.py [--rater v2]
"""
import argparse
import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rater", choices=("sonnet", "v2"), default="sonnet")
    args = ap.parse_args()
    suffix = "_v2" if args.rater == "v2" else ""

    src = Path("results/session_flaw_hunter%s.jsonl" % suffix)
    print(f"Rater: {args.rater}  ({src})")
    records = [json.loads(l) for l in open(src) if l.strip()]
    print(f"Records: {len(records)}")

    # Per-model and per-target aggregates
    by_model = defaultdict(list)
    by_target = defaultdict(list)
    by_model_target = defaultdict(lambda: defaultdict(list))
    flaw_freq_by_model = defaultdict(Counter)
    fatal_count_by_model = defaultdict(int)
    major_count_by_model = defaultdict(int)
    minor_count_by_model = defaultdict(int)
    bonus_count_by_model = defaultdict(int)

    for r in records:
        m = r["model"]
        # The Sonnet pass calls it failure_target, the v2 re-score calls it
        # target. Same field.
        t = r.get("failure_target") or r.get("target") or "general"
        score = r["final_score"]
        by_model[m].append(score)
        by_target[t].append(score)
        by_model_target[m][t].append(score)
        # Only the Sonnet pass precomputes n_fatal/n_major/n_minor/n_bonus.
        # The v2 file carries the flaw lists themselves, so count them. A bare
        # .get(..., 0) would have printed "fatal/session 0.00" on every v2 card
        # -- a clean-looking number that simply means the key was absent.
        def _n(pre, key):
            if pre in r:
                return r[pre]
            return len(r.get(key) or [])
        fatal_count_by_model[m] += _n("n_fatal", "fatal_flaws")
        major_count_by_model[m] += _n("n_major", "major_flaws")
        minor_count_by_model[m] += _n("n_minor", "minor_flaws")
        bonus_count_by_model[m] += _n("n_bonus", "bonuses")
        for f in r.get("fatal_flaws", []):
            flaw_freq_by_model[m][f"FATAL:{f.get('flaw','?')}"] += 1
        for f in r.get("major_flaws", []):
            flaw_freq_by_model[m][f"MAJOR:{f.get('flaw','?')}"] += 1

    # Build summary
    summary = {
        "n_sessions": len(records),
        "n_models": len(by_model),
        "per_model": {},
        "per_failure_target": {},
        "per_model_target": {},
    }

    for m, scores in by_model.items():
        summary["per_model"][m] = {
            "mean": round(st.mean(scores), 1),
            "median": round(st.median(scores), 1),
            "std": round(st.stdev(scores), 1) if len(scores) > 1 else 0,
            "min": min(scores),
            "max": max(scores),
            "n": len(scores),
            "total_fatal": fatal_count_by_model[m],
            "total_major": major_count_by_model[m],
            "total_minor": minor_count_by_model[m],
            "total_bonus": bonus_count_by_model[m],
            "fatal_per_session": round(fatal_count_by_model[m] / len(scores), 2),
            "major_per_session": round(major_count_by_model[m] / len(scores), 2),
            "top_flaws": [
                {"flaw": flaw, "count": count}
                for flaw, count in flaw_freq_by_model[m].most_common(5)
            ],
        }

    for t, scores in by_target.items():
        summary["per_failure_target"][t] = {
            "mean": round(st.mean(scores), 1),
            "median": round(st.median(scores), 1),
            "n": len(scores),
        }

    for m, by_t in by_model_target.items():
        summary["per_model_target"][m] = {
            t: {"mean": round(st.mean(s), 1), "n": len(s)}
            for t, s in by_t.items()
        }

    # Print
    print()
    print(f'{"Model":<28}{"Mean":<8}{"Median":<8}{"Min":<6}{"Max":<6}{"Fatal/s":<10}{"Major/s":<10}{"n":<5}')
    print("-" * 80)
    sorted_models = sorted(by_model.items(), key=lambda x: -st.mean(x[1]))
    for m, scores in sorted_models:
        d = summary["per_model"][m]
        print(f'  {m:<26}{d["mean"]:<8.1f}{d["median"]:<8.1f}{d["min"]:<6}{d["max"]:<6}{d["fatal_per_session"]:<10}{d["major_per_session"]:<10}{d["n"]:<5}')

    print()
    print("Per failure-target avg score (lower = harder seed):")
    for t, scores in sorted(by_target.items(), key=lambda x: st.mean(x[1])):
        d = summary["per_failure_target"][t]
        print(f"  {t:<35}  mean={d['mean']:.1f}  n={d['n']}")

    out_path = Path("results/flaw_hunter_session_summary%s.json" % suffix)
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
