#!/usr/bin/env python3
"""
Seed Discrimination Analysis for RP-Bench Multi-Turn Results.

Computes which adversarial seeds actually differentiate models vs. which are
ceiling/floor effects. With n=1 per (model, seed) we use:
  - spread: max(mean) - min(mean) across models
  - CV: coefficient of variation of model means
  - eta_sq / omega_sq: effect size of model on score

Usage:
    python analyze_seed_discrimination.py [results_file]

Output:
    results/seed_discrimination_analysis.json
"""
import argparse
import json
import math
from collections import defaultdict, OrderedDict
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
RESULTS_DIR = PROJECT_ROOT / "harness" / "results"
if not RESULTS_DIR.exists():
    RESULTS_DIR = PROJECT_ROOT / "results"

DEFAULT_RESULTS = RESULTS_DIR / "multiturn_20260414_042100.json"


def load_multiturn_results(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def compute_seed_discrimination(data: dict) -> list[dict]:
    """Compute discrimination metrics per seed."""
    seed_model_scores = defaultdict(lambda: defaultdict(list))

    for session in data["sessions"]:
        seed_id = session["seed_id"]
        model = session["test_model"]
        for judge_key, judge_data in session.get("judges", {}).items():
            scores = judge_data.get("scores", {})
            if scores.get("parse_error") or "overall" not in scores:
                continue
            seed_model_scores[seed_id][model].append(scores["overall"])

    results = []
    for seed_id in sorted(seed_model_scores.keys()):
        model_scores = seed_model_scores[seed_id]
        means = {m: sum(v) / len(v) for m, v in model_scores.items()}
        all_vals = [(m, v) for m, vals in model_scores.items() for v in vals]

        grand_mean = sum(v for _, v in all_vals) / len(all_vals)
        n_models = len(model_scores)
        n_total = len(all_vals)

        # Between-model variance (signal)
        ss_between = sum(
            len(model_scores[m]) * (means[m] - grand_mean) ** 2 for m in means
        )
        df_between = n_models - 1

        # Total variance
        ss_total = sum((v - grand_mean) ** 2 for _, v in all_vals)

        # eta-squared
        eta_sq = ss_between / ss_total if ss_total > 0 else 0
        omega_sq = eta_sq  # With n=1 these are equivalent

        # Model mean spread
        mean_vals = list(means.values())
        mean_range = max(mean_vals) - min(mean_vals)
        mean_std = math.sqrt(
            sum((m - grand_mean) ** 2 for m in mean_vals) / len(mean_vals)
        ) if mean_vals else 0
        cv = mean_std / grand_mean if grand_mean > 0 else 0

        best_model = max(means, key=means.get)
        worst_model = min(means, key=means.get)

        results.append(
            {
                "seed": seed_id,
                "spread": round(mean_range, 4),
                "cv": round(cv, 4),
                "eta_sq": round(eta_sq, 4),
                "omega_sq": round(omega_sq, 4),
                "grand_mean": round(grand_mean, 4),
                "best_model": best_model,
                "best_score": round(means[best_model], 3),
                "worst_model": worst_model,
                "worst_score": round(means[worst_model], 3),
                "scores": {m: round(v, 3) for m, v in means.items()},
                "n_models": n_models,
                "n_sessions": n_total,
            }
        )

    results.sort(key=lambda x: -x["spread"])
    return results


TIER_THRESHOLDS = [
    (0.50, "Tier 1 (excellent)"),
    (0.30, "Tier 2 (good)"),
    (0.15, "Tier 3 (moderate)"),
    (0.0, "Tier 4 (poor)"),
]


def assign_tiers(results: list[dict]) -> list[dict]:
    """Assign quality tiers based on spread."""
    for r in results:
        spread = r["spread"]
        for threshold, tier in TIER_THRESHOLDS:
            if spread > threshold:
                r["tier"] = tier
                break
    return results


def print_report(results: list[dict]):
    print("=" * 90)
    print("SEED DISCRIMINATION ANALYSIS")
    print("=" * 90)
    print()
    print(
        "Metrics:\n"
        "  spread   = max(mean) - min(mean) across models (raw discrimination power)\n"
        "  CV       = coefficient of variation of model means (normalized spread)\n"
        "  eta_sq   = eta-squared from one-way ANOVA (effect size)\n"
        "  omega_sq = omega-squared (less biased effect size estimate)\n"
    )

    print(
        f"{'Seed':<35} {'Spread':>7} {'CV':>7} {'eta2':>7} {'Best':>20} {'Worst':>20}"
    )
    print("-" * 90)
    for r in results:
        print(
            f"{r['seed']:<35} {r['spread']:>7.3f} {r['cv']:>7.3f} "
            f"{r['eta_sq']:>7.3f} "
            f"{r['best_model']} ({r['best_score']:.2f}) "
            f"{r['worst_model']} ({r['worst_score']:.2f})"
        )

    print()
    print("=" * 90)
    print("SEED QUALITY TIERS")
    print("=" * 90)
    print(
        "  spread interpretation:\n"
        "    > 0.50 : Excellent — clear winner/loser separation\n"
        "    0.30-0.50: Good — meaningful differentiation\n"
        "    0.15-0.30: Moderate — some signal but models cluster\n"
        "    < 0.15 : Poor — all models perform similarly\n"
    )

    by_tier = defaultdict(list)
    for r in results:
        by_tier[r["tier"]].append(r["seed"])

    for tier in ["Tier 1 (excellent)", "Tier 2 (good)", "Tier 3 (moderate)", "Tier 4 (poor)"]:
        seeds = by_tier.get(tier, [])
        if seeds:
            print(f"\n  {tier} ({len(seeds)} seeds):")
            for s in seeds:
                r = next(r for r in results if r["seed"] == s)
                print(f"    {s}: spread={r['spread']:.3f}")

    poor_seeds = by_tier.get("Tier 4 (poor)", [])
    print()
    print("=" * 90)
    print("RECOMMENDATIONS")
    print("=" * 90)
    if poor_seeds:
        print(f"\n  DROP (Tier 4): {', '.join(poor_seeds)}")
        print("    → All models cluster near the same score — seed doesn't discriminate")
    else:
        print("\n  All seeds provide meaningful discrimination.")

    moderate = by_tier.get("Tier 3 (moderate)", [])
    if moderate:
        print(f"\n  CONSIDER REVISING ({', '.join(moderate)}):")
        print("    → Low spread means models perform similarly — seed may need harder adversarial pressure")


def save_results(results: list[dict], output_path: Path):
    output = {
        "methodology": (
            "n=1 per cell; spread = max(mean) - min(mean) across models; "
            "CV = coefficient of variation of model means; eta2 = eta-squared; "
            "omega2 = omega-squared (less biased)"
        ),
        "tiers": {
            "Tier 1 (excellent)": [],
            "Tier 2 (good)": [],
            "Tier 3 (moderate)": [],
            "Tier 4 (poor)": [],
        },
        "recommendations": [],
        "seeds": results,
    }

    for r in results:
        spread = r["spread"]
        for threshold, tier in TIER_THRESHOLDS:
            if spread > threshold:
                output["tiers"][tier].append(r["seed"])
                break

    poor = output["tiers"].get("Tier 4 (poor)", [])
    if poor:
        output["recommendations"].append(
            f"DROP: {', '.join(poor)} — models cluster at similar scores"
        )
    else:
        output["recommendations"].append("All seeds provide meaningful discrimination")

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Seed discrimination analysis")
    parser.add_argument(
        "results_file",
        nargs="?",
        type=Path,
        default=DEFAULT_RESULTS,
        help="Path to multiturn results JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path (default: results/seed_discrimination_analysis.json)",
    )
    args = parser.parse_args()

    if not args.results_file.exists():
        print(f"Error: {args.results_file} not found")
        print(f"Available multiturn files in {RESULTS_DIR}:")
        for f in sorted(RESULTS_DIR.glob("multiturn_*.json")):
            print(f"  {f.name}")
        return

    print(f"Loading: {args.results_file}")
    data = load_multiturn_results(args.results_file)
    print(f"  Sessions: {len(data['sessions'])}, Config: {data['config'].get('seed_count', '?')} seeds")

    results = compute_seed_discrimination(data)
    results = assign_tiers(results)

    print_report(results)

    output_path = args.output or RESULTS_DIR / "seed_discrimination_analysis.json"
    save_results(results, output_path)


if __name__ == "__main__":
    main()
