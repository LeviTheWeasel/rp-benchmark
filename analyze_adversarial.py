#!/usr/bin/env python3
"""Aggregate adversarial multi-turn runs.

Adversarial seeds are designed to push models toward specific failure
modes (agency violations, contradictory lore, passive users, impossible
physics, subtle OOC drift, time pressure, character-break bait, genre shift).

A standard run produces a wide score spread. An adversarial run should
compress scores and surface which seeds actually break which models.

Usage:
    python3 analyze_adversarial.py results/multiturn_*.json
"""
import json
import sys
import statistics as st
from collections import defaultdict
from pathlib import Path


def load_runs(paths):
    sessions = []
    for p in paths:
        d = json.load(open(p))
        if d.get("type") != "multiturn":
            continue
        for s in d["sessions"]:
            if not s.get("seed_id", "").startswith("adv_"):
                continue
            sessions.append(s)
    return sessions


def main():
    paths = sys.argv[1:] or sorted(Path("results").glob("multiturn_*.json"))
    sessions = load_runs(paths)
    if not sessions:
        print("No adversarial sessions found.")
        sys.exit(1)

    by_model = defaultdict(list)
    by_seed = defaultdict(list)
    by_ms = {}
    dims_by_model = defaultdict(lambda: defaultdict(list))
    degradation = defaultdict(list)
    trajectory = defaultdict(lambda: {"early": [], "mid": [], "late": []})

    for s in sessions:
        m = s["test_model"]
        seed = s["seed_id"]
        judge = list(s["judges"].values())[0]["scores"]
        overall = judge.get("overall")
        if overall is None:
            continue
        by_model[m].append(overall)
        by_seed[seed].append((m, overall))
        by_ms[(m, seed)] = overall
        for dim, info in judge.get("session_dimensions", {}).items():
            if isinstance(info, dict) and "score" in info:
                dims_by_model[m][dim].append(info["score"])
        qt = judge.get("quality_trajectory", {})
        if "degradation_detected" in qt:
            degradation[m].append(bool(qt["degradation_detected"]))
        for k, bucket in (("early_quality", "early"), ("mid_quality", "mid"), ("late_quality", "late")):
            v = qt.get(k)
            if isinstance(v, (int, float)):
                trajectory[m][bucket].append(v)

    ranked = sorted(by_model.items(), key=lambda x: -st.mean(x[1]))

    print(f"Adversarial sessions: {len(sessions)}")
    print(f"Models: {len(by_model)}, seeds: {len(by_seed)}")
    print()
    print("=" * 80)
    print("ADVERSARIAL LEADERBOARD")
    print("=" * 80)
    print(f'{"Model":<28} {"Mean":<7} {"Std":<7} {"Min":<6} {"Max":<6} {"N":<4} {"Degrad%":<8}')
    print("-" * 72)
    for m, scores in ranked:
        deg = degradation[m]
        deg_pct = 100 * sum(deg) / len(deg) if deg else 0
        sd = st.stdev(scores) if len(scores) > 1 else 0
        print(f'{m:<28} {st.mean(scores):<7.2f} {sd:<7.2f} {min(scores):<6.1f} {max(scores):<6.1f} {len(scores):<4} {deg_pct:<8.0f}')

    print()
    print("=" * 80)
    print("PER-SEED BREAKDOWN (which seeds compressed scores the most?)")
    print("=" * 80)
    print(f'{"Seed":<32} {"Mean":<7} {"Min":<6} {"Max":<6} {"Spread":<8} {"Worst model":<24}')
    print("-" * 85)
    seed_rows = []
    for seed in sorted(by_seed):
        pairs = by_seed[seed]
        vals = [v for _, v in pairs]
        worst_m, worst_v = min(pairs, key=lambda x: x[1])
        row = {
            "seed": seed,
            "mean": st.mean(vals),
            "min": min(vals),
            "max": max(vals),
            "spread": max(vals) - min(vals),
            "worst_model": worst_m,
        }
        seed_rows.append(row)
        print(f'{seed:<32} {row["mean"]:<7.2f} {row["min"]:<6.1f} {row["max"]:<6.1f} {row["spread"]:<8.2f} {worst_m:<24}')

    print()
    print("=" * 80)
    print("DIMENSION WEAKNESSES (mean across all models)")
    print("=" * 80)
    dim_means = defaultdict(list)
    for m, dims in dims_by_model.items():
        for d, scores in dims.items():
            dim_means[d].extend(scores)
    dim_sorted = sorted(dim_means.items(), key=lambda x: st.mean(x[1]))
    for d, scores in dim_sorted:
        bar = "█" * int((st.mean(scores) - 3.5) * 20)
        print(f'  {d:<35} {st.mean(scores):.2f}  {bar}')

    print()
    print("=" * 80)
    print("QUALITY TRAJECTORY (early → mid → late)")
    print("=" * 80)
    print(f'{"Model":<28} {"Early":<8} {"Mid":<8} {"Late":<8} {"Δ late-early":<10}')
    for m, _ in ranked:
        t = trajectory[m]
        if not all(t[k] for k in ("early", "mid", "late")):
            continue
        e, mi, la = st.mean(t["early"]), st.mean(t["mid"]), st.mean(t["late"])
        print(f'{m:<28} {e:<8.2f} {mi:<8.2f} {la:<8.2f} {la - e:<+10.2f}')

    out = {
        "n_sessions": len(sessions),
        "leaderboard": [
            {
                "model": m,
                "mean": st.mean(scores),
                "std": st.stdev(scores) if len(scores) > 1 else 0.0,
                "min": min(scores),
                "max": max(scores),
                "n": len(scores),
                "degradation_pct": 100 * sum(degradation[m]) / len(degradation[m]) if degradation[m] else 0.0,
            }
            for m, scores in ranked
        ],
        "per_seed": seed_rows,
        "dimension_means": {d: st.mean(scores) for d, scores in dim_sorted},
        "trajectory": {
            m: {k: st.mean(v) for k, v in t.items() if v}
            for m, t in trajectory.items()
        },
    }
    out_path = Path("results") / "adversarial_analysis.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
