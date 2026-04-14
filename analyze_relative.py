#!/usr/bin/env python3
"""Relative (percentile-based) leaderboard.

Instead of absolute scores, rank each model by how often they beat others
on each scenario. This forces differentiation.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from harness.objective_metrics import compute_all as compute_obj, objective_score
from harness.slop_detectors import detect_all_slop


def main():
    run_path = sys.argv[1] if len(sys.argv) > 1 else "results/run_20260413_231835.json"

    with open(run_path) as f:
        run = json.load(f)

    # Group by scenario
    by_scenario = defaultdict(list)  # {scenario_id: [(model, fh, obj, slop)]}

    for r in run["results"]:
        if not r.get("generation"):
            continue
        model = r.get("test_model")
        sid = r.get("scenario_id")
        text = r["generation"]["content"]

        fh = None
        for jdata in r.get("judges", {}).values():
            scores = jdata.get("scores", {})
            if "final_score" in scores:
                fh = scores["final_score"]
                break
        if fh is None:
            continue

        obj_result = objective_score(compute_obj(text))
        slop_result = detect_all_slop(text)
        slop = 100 - min(40, slop_result["total_weight"] * 3)

        by_scenario[sid].append({
            "model": model,
            "fh": fh,
            "obj": obj_result["objective_score"],
            "slop": slop,
        })

    # For each scenario, compute rank (1 = best) for each model on each signal
    # Then convert rank to percentile: best = 100, worst = 0
    model_percentiles = defaultdict(lambda: {"fh": [], "obj": [], "slop": [], "combined_rank": []})

    for sid, entries in by_scenario.items():
        if len(entries) < 2:
            continue

        n = len(entries)

        # Rank by each signal (higher score = better rank)
        for signal in ["fh", "obj", "slop"]:
            ranked = sorted(entries, key=lambda e: -e[signal])
            for rank, entry in enumerate(ranked):
                # Percentile: best (rank 0) = 100, worst (rank n-1) = 0
                percentile = 100 * (n - 1 - rank) / (n - 1) if n > 1 else 50
                model_percentiles[entry["model"]][signal].append(percentile)

        # Combined rank: average the 3 percentiles per entry, then rank by that
        combined_scored = []
        for e in entries:
            # Need to know each entry's percentile — recompute here
            fh_rank = sorted(entries, key=lambda x: -x["fh"]).index(e)
            obj_rank = sorted(entries, key=lambda x: -x["obj"]).index(e)
            slop_rank = sorted(entries, key=lambda x: -x["slop"]).index(e)
            fh_pct = 100 * (n - 1 - fh_rank) / (n - 1) if n > 1 else 50
            obj_pct = 100 * (n - 1 - obj_rank) / (n - 1) if n > 1 else 50
            slop_pct = 100 * (n - 1 - slop_rank) / (n - 1) if n > 1 else 50
            combined_pct = fh_pct * 0.5 + obj_pct * 0.25 + slop_pct * 0.25
            combined_scored.append((e["model"], combined_pct))

        for model, pct in combined_scored:
            model_percentiles[model]["combined_rank"].append(pct)

    # Aggregate
    lb = []
    for m, data in model_percentiles.items():
        fh_avg = sum(data["fh"]) / len(data["fh"]) if data["fh"] else 0
        obj_avg = sum(data["obj"]) / len(data["obj"]) if data["obj"] else 0
        slop_avg = sum(data["slop"]) / len(data["slop"]) if data["slop"] else 0
        combined = sum(data["combined_rank"]) / len(data["combined_rank"]) if data["combined_rank"] else 0
        lb.append({
            "model": m,
            "combined_pct": round(combined, 1),
            "fh_pct": round(fh_avg, 1),
            "obj_pct": round(obj_avg, 1),
            "slop_pct": round(slop_avg, 1),
            "n": len(data["combined_rank"]),
        })
    lb.sort(key=lambda x: -x["combined_pct"])

    print()
    print("=" * 90)
    print("  RP-BENCH RELATIVE LEADERBOARD (percentile-based)")
    print("  Higher = beats more models. 100 = always wins. 0 = always loses.")
    print("=" * 90)
    print()
    print(f'  {"Rank":<5} {"Model":<28} {"Combined":<10} {"FlawHunt":<10} {"Objective":<11} {"Slop":<8}')
    print("  " + "-" * 82)
    for i, e in enumerate(lb):
        print(f'  #{i+1:<4} {e["model"]:<28} {e["combined_pct"]:<10.1f} {e["fh_pct"]:<10.1f} {e["obj_pct"]:<11.1f} {e["slop_pct"]:<8.1f}')
    print("  " + "-" * 82)

    # Save
    out = Path(run_path).parent / "relative_leaderboard.json"
    with open(out, "w") as f:
        json.dump({"leaderboard": lb}, f, indent=2)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
