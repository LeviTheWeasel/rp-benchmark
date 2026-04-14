#!/usr/bin/env python3
"""Combined analysis: flaw hunter + objective metrics + slop detectors.

Produces a unified leaderboard that weighs all three signals.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from harness.objective_metrics import compute_all as compute_objective
from harness.slop_detectors import detect_all_slop


def combined_score(flaw_hunter_score: int, objective_data: dict, slop_data: dict) -> dict:
    """Combine all three signals into one 0-100 score.

    - 50% flaw hunter (subjective quality)
    - 25% objective (cliches, diversity, rhythm)
    - 25% slop detectors (rule-based pattern hits)
    """
    # Flaw hunter: 0-100 already
    fh = flaw_hunter_score

    # Objective: already 0-100
    obj = objective_data.get("objective_score", 0) if isinstance(objective_data, dict) else 0
    if "objective_score" not in objective_data and "raw_metrics" in objective_data:
        obj = objective_data["objective_score"]

    # Slop: start at 100, deduct weight*3
    slop_penalty = min(40, slop_data.get("total_weight", 0) * 3)
    slop_score = 100 - slop_penalty

    combined = fh * 0.5 + obj * 0.25 + slop_score * 0.25
    return {
        "combined": round(combined, 1),
        "flaw_hunter": fh,
        "objective": obj,
        "slop_score": slop_score,
    }


def main():
    run_path = sys.argv[1] if len(sys.argv) > 1 else "results/run_20260413_231835.json"

    with open(run_path) as f:
        run = json.load(f)

    model_scores = defaultdict(list)
    model_breakdown = defaultdict(lambda: {"fh": [], "obj": [], "slop": []})

    for r in run["results"]:
        if not r.get("generation"):
            continue

        model = r.get("test_model")
        text = r["generation"]["content"]

        # Get flaw hunter score
        fh_score = None
        for jdata in r.get("judges", {}).values():
            scores = jdata.get("scores", {})
            if "final_score" in scores:
                fh_score = scores["final_score"]
                break
        if fh_score is None:
            continue

        # Compute objective
        obj_metrics = compute_objective(text)
        from harness.objective_metrics import objective_score as compute_obj_score
        obj_result = compute_obj_score(obj_metrics)

        # Compute slop
        slop_result = detect_all_slop(text)

        combined = combined_score(fh_score, obj_result, slop_result)

        model_scores[model].append(combined["combined"])
        model_breakdown[model]["fh"].append(combined["flaw_hunter"])
        model_breakdown[model]["obj"].append(combined["objective"])
        model_breakdown[model]["slop"].append(combined["slop_score"])

    # Leaderboard
    lb = []
    for m, scores in model_scores.items():
        if not scores:
            continue
        avg = sum(scores) / len(scores)
        fh_avg = sum(model_breakdown[m]["fh"]) / len(model_breakdown[m]["fh"])
        obj_avg = sum(model_breakdown[m]["obj"]) / len(model_breakdown[m]["obj"])
        slop_avg = sum(model_breakdown[m]["slop"]) / len(model_breakdown[m]["slop"])
        lb.append({
            "model": m,
            "combined": round(avg, 1),
            "flaw_hunter": round(fh_avg, 1),
            "objective": round(obj_avg, 1),
            "slop": round(slop_avg, 1),
            "n": len(scores),
        })
    lb.sort(key=lambda x: -x["combined"])

    print()
    print("=" * 90)
    print("  RP-BENCH COMBINED LEADERBOARD")
    print("  (50% flaw hunter + 25% objective + 25% slop detectors)")
    print("=" * 90)
    print()
    print(f'  {"Rank":<5} {"Model":<28} {"Combined":<10} {"FlawHunt":<10} {"Objective":<11} {"Slop":<8}')
    print("  " + "-" * 82)
    for i, e in enumerate(lb):
        print(f'  #{i+1:<4} {e["model"]:<28} {e["combined"]:<10.1f} {e["flaw_hunter"]:<10.1f} {e["objective"]:<11.1f} {e["slop"]:<8.1f}')
    print("  " + "-" * 82)

    # Save
    out = Path(run_path).parent / "combined_leaderboard.json"
    with open(out, "w") as f:
        json.dump({"leaderboard": lb}, f, indent=2)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
