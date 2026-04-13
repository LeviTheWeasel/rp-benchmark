"""Aggregate benchmark results into leaderboards with per-dimension rankings."""
import json
import math
from collections import defaultdict
from pathlib import Path

from .config import RESULTS_DIR

# Dimension metadata for display
DIMENSION_NAMES = {
    "1.1_agency_respect": "Agency Respect",
    "1.2_instruction_adherence": "Instruction Adherence",
    "1.3_continuity": "Continuity",
    "1.4_length_calibration": "Length Calibration",
    "1.5_distinct_voices": "Distinct Voices",
    "1.6_scene_grounding": "Scene Grounding",
    "2.1_anti_purple_prose": "Anti-Purple Prose",
    "2.2_anti_repetition": "Anti-Repetition",
    "2.3_anti_sycophancy": "Anti-Sycophancy",
    "2.4_anti_artificial_perfection": "Anti-Perfection",
    "2.5_show_dont_tell": "Show Don't Tell",
    "2.6_subtext": "Subtext",
    "2.7_pacing": "Pacing",
    "2.8_imperfect_coping": "Imperfect Coping",
    "3.1_earned_intimacy": "Earned Intimacy",
    "3.2_atmospheric_dread": "Atmospheric Dread",
    "3.3_structural_comedy": "Structural Comedy",
    "3.4_excavated_truth": "Excavated Truth",
    "3.5_spatial_precision": "Spatial Precision",
    "3.6_lived_in_worlds": "Lived-In Worlds",
    "3.7_information_architecture": "Info Architecture",
    "3.8_structural_inevitability": "Structural Inevitability",
    "3.9_threshold_logic": "Threshold Logic",
    "3.10_emotional_residue": "Emotional Residue",
    "3.11_erotic_craft": "Erotic Craft",
    "3.12_context_integration": "Context Integration",
}

TIER_LABELS = {
    "1": "Fundamentals",
    "2": "Quality Control",
    "3": "Genre Craft",
}


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _stdev(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))


def _ci95(vals: list[float]) -> tuple[float, float]:
    """95% confidence interval using t-distribution approximation."""
    if len(vals) < 2:
        m = _mean(vals)
        return (m, m)
    m = _mean(vals)
    se = _stdev(vals) / math.sqrt(len(vals))
    # t-value for 95% CI, approximate for small samples
    t = 2.0 if len(vals) >= 30 else 2.262 if len(vals) >= 10 else 2.776 if len(vals) >= 5 else 4.303
    return (round(m - t * se, 2), round(m + t * se, 2))


def extract_scores(judge_data: dict) -> dict | None:
    """Extract numeric scores from a judge result."""
    scores = judge_data.get("scores", {})
    if scores.get("parse_error"):
        return None

    flat = {}
    for tier_key in ["tier1_fundamentals", "tier2_quality_control", "tier3_genre_craft"]:
        tier = scores.get(tier_key, {})
        for dim_key, dim_data in tier.items():
            if isinstance(dim_data, dict) and "score" in dim_data:
                flat[dim_key] = dim_data["score"]

    return flat if flat else None


def aggregate_run(run_path: str | Path) -> dict:
    """Aggregate a single run into a full leaderboard with per-dimension rankings.

    Returns structured leaderboard data with:
    - Overall rankings
    - Per-tier rankings
    - Per-dimension rankings
    - Confidence intervals (if multi-run data available)
    - Inter-judge agreement stats
    """
    with open(run_path) as f:
        run = json.load(f)

    # Collect all scores: model -> dimension -> [all scores across judges and runs]
    model_dim_scores = defaultdict(lambda: defaultdict(list))
    # Also per-judge for agreement analysis
    model_judge_dim = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    parse_failures = 0
    total_evals = 0
    scenario_count = defaultdict(int)
    reference_models = set()  # models that are reference data, not competitors

    for result in run["results"]:
        if "error" in result:
            continue

        model = result["test_model"]
        scenario_count[model] += 1

        if result.get("is_reference"):
            reference_models.add(model)

        for judge_key, judge_data in result.get("judges", {}).items():
            total_evals += 1
            scores = extract_scores(judge_data)
            if scores is None:
                parse_failures += 1
                continue

            for dim, score in scores.items():
                model_dim_scores[model][dim].append(score)
                model_judge_dim[model][judge_key][dim].append(score)

    # Build per-model stats
    model_stats = {}
    for model in model_dim_scores:
        dims = model_dim_scores[model]

        dim_stats = {}
        for dim, vals in dims.items():
            dim_stats[dim] = {
                "mean": round(_mean(vals), 2),
                "stdev": round(_stdev(vals), 2),
                "ci95": _ci95(vals),
                "n": len(vals),
                "min": round(min(vals), 2),
                "max": round(max(vals), 2),
            }

        # Tier averages
        tier_scores = {"1": [], "2": [], "3": []}
        for dim, stats in dim_stats.items():
            tier = dim.split(".")[0].split("_")[0]
            tier_scores[tier].append(stats["mean"])

        tier_avgs = {}
        for tier, vals in tier_scores.items():
            if vals:
                tier_avgs[tier] = {
                    "mean": round(_mean(vals), 2),
                    "dimensions_scored": len(vals),
                }

        # Overall score
        t1 = tier_avgs.get("1", {}).get("mean")
        t2 = tier_avgs.get("2", {}).get("mean")
        t3 = tier_avgs.get("3", {}).get("mean")

        if t1 is not None and t2 is not None and t3 is not None:
            overall = round(t1 * 0.40 + t2 * 0.35 + t3 * 0.25, 2)
        elif t1 is not None and t2 is not None:
            overall = round(t1 * 0.55 + t2 * 0.45, 2)
        else:
            overall = None

        # Inter-judge agreement for this model
        judge_overalls = {}
        for judge, judge_dims in model_judge_dim[model].items():
            all_judge_scores = []
            for vals in judge_dims.values():
                all_judge_scores.extend(vals)
            if all_judge_scores:
                judge_overalls[judge] = round(_mean(all_judge_scores), 2)

        judge_spread = None
        if len(judge_overalls) >= 2:
            vals = list(judge_overalls.values())
            judge_spread = round(max(vals) - min(vals), 2)

        model_stats[model] = {
            "overall": overall,
            "tier_avgs": tier_avgs,
            "dimensions": dim_stats,
            "scenario_count": scenario_count[model],
            "judge_overalls": judge_overalls,
            "judge_spread": judge_spread,
            "is_reference": model in reference_models,
        }

    # Separate competitive models from reference data
    competitive_stats = {m: s for m, s in model_stats.items() if not s["is_reference"]}
    reference_stats = {m: s for m, s in model_stats.items() if s["is_reference"]}

    # Build rankings (competitive models only)
    # 1. Overall leaderboard
    overall_ranking = _build_ranking(competitive_stats, lambda s: s["overall"])

    # 2. Per-tier leaderboards
    tier_rankings = {}
    for tier_id, tier_label in TIER_LABELS.items():
        tier_rankings[tier_label] = _build_ranking(
            competitive_stats,
            lambda s, t=tier_id: s["tier_avgs"].get(t, {}).get("mean"),
        )

    # 3. Per-dimension leaderboards
    all_dims = set()
    for stats in competitive_stats.values():
        all_dims.update(stats["dimensions"].keys())

    dimension_rankings = {}
    for dim in sorted(all_dims):
        display_name = DIMENSION_NAMES.get(dim, dim)
        dimension_rankings[dim] = {
            "display_name": display_name,
            "ranking": _build_ranking(
                competitive_stats,
                lambda s, d=dim: s["dimensions"].get(d, {}).get("mean"),
            ),
        }

    # Rating labels
    def rating_label(score):
        if score is None:
            return "unknown"
        if score >= 4.5:
            return "exceptional"
        if score >= 3.5:
            return "strong"
        if score >= 2.5:
            return "adequate"
        if score >= 1.5:
            return "below_average"
        return "poor"

    def _make_entry(entry, rank):
        stats = model_stats[entry["model"]]
        return {
            "rank": rank,
            "model": entry["model"],
            "overall": entry["score"],
            "rating": rating_label(entry["score"]),
            "tier1": stats["tier_avgs"].get("1", {}).get("mean"),
            "tier2": stats["tier_avgs"].get("2", {}).get("mean"),
            "tier3": stats["tier_avgs"].get("3", {}).get("mean"),
            "judge_spread": stats["judge_spread"],
            "scenarios": stats["scenario_count"],
        }

    # Reference data entries (not ranked competitively)
    reference_ranking = _build_ranking(reference_stats, lambda s: s["overall"])

    return {
        "run_id": run["run_id"],
        "timestamp": run.get("timestamp"),
        "total_evals": total_evals,
        "parse_failures": parse_failures,
        "models": model_stats,
        "rankings": {
            "overall": overall_ranking,
            "by_tier": tier_rankings,
            "by_dimension": dimension_rankings,
        },
        "leaderboard": [
            _make_entry(entry, i + 1)
            for i, entry in enumerate(overall_ranking)
        ],
        "reference_data": [
            _make_entry(entry, i + 1)
            for i, entry in enumerate(reference_ranking)
        ],
    }


def _build_ranking(
    model_stats: dict,
    score_fn,
) -> list[dict]:
    """Build a sorted ranking from model stats using a score extraction function."""
    entries = []
    for model, stats in model_stats.items():
        score = score_fn(stats)
        if score is not None:
            entries.append({"model": model, "score": round(score, 2)})

    entries.sort(key=lambda x: x["score"], reverse=True)
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1
    return entries


def print_leaderboard(agg: dict, view: str = "overall"):
    """Print a human-readable leaderboard.

    Views: "overall", "tiers", "dimensions", "full"
    """
    print()
    print("=" * 78)
    print("  RP-BENCH LEADERBOARD")
    print("  Run: %s | Evals: %d | Parse failures: %d" % (
        agg["run_id"], agg["total_evals"], agg["parse_failures"]
    ))
    print("=" * 78)

    if view in ("overall", "full"):
        _print_overall(agg)

    if view in ("tiers", "full"):
        _print_tier_rankings(agg)

    if view in ("dimensions", "full"):
        _print_dimension_rankings(agg)

    if view in ("overall", "full"):
        _print_reference_data(agg)

    if view in ("overall", "full"):
        _print_judge_agreement(agg)


def _print_overall(agg: dict):
    """Print overall leaderboard."""
    lb = agg["leaderboard"]
    print()
    print("  OVERALL RANKING")
    print("  " + "-" * 74)
    print("  %-5s %-24s %-9s %-9s %-9s %-9s %-8s %s" % (
        "Rank", "Model", "Overall", "T1:Fund", "T2:QC", "T3:Genre", "Rating", "Spread"
    ))
    print("  " + "-" * 74)

    for entry in lb:
        spread_str = "%.2f" % entry["judge_spread"] if entry["judge_spread"] is not None else "-"
        t1 = "%.2f" % entry["tier1"] if entry["tier1"] else "-"
        t2 = "%.2f" % entry["tier2"] if entry["tier2"] else "-"
        t3 = "%.2f" % entry["tier3"] if entry["tier3"] else "-"
        overall = "%.2f" % entry["overall"] if entry["overall"] else "-"

        print("  #%-4d %-24s %-9s %-9s %-9s %-9s %-8s %s" % (
            entry["rank"], entry["model"], overall, t1, t2, t3,
            entry["rating"], spread_str
        ))

    print("  " + "-" * 74)


def _print_tier_rankings(agg: dict):
    """Print per-tier rankings."""
    tier_rankings = agg["rankings"]["by_tier"]

    for tier_name, ranking in tier_rankings.items():
        if not ranking:
            continue
        print()
        print("  %s" % tier_name.upper())
        print("  " + "-" * 40)
        for entry in ranking:
            print("  #%-4d %-24s %.2f" % (entry["rank"], entry["model"], entry["score"]))


def _print_dimension_rankings(agg: dict):
    """Print per-dimension rankings — shows which model is best at each dimension."""
    dim_rankings = agg["rankings"]["by_dimension"]

    # Group by tier
    tiers = {"1": [], "2": [], "3": []}
    for dim_key, dim_data in dim_rankings.items():
        tier = dim_key.split(".")[0].split("_")[0]
        tiers.setdefault(tier, []).append((dim_key, dim_data))

    for tier_id in ["1", "2", "3"]:
        dims = tiers.get(tier_id, [])
        if not dims:
            continue

        tier_label = TIER_LABELS.get(tier_id, tier_id)
        print()
        print("  PER-DIMENSION: %s" % tier_label.upper())
        print("  " + "-" * 60)

        for dim_key, dim_data in sorted(dims):
            display = dim_data["display_name"]
            ranking = dim_data["ranking"]
            if not ranking:
                continue

            # Show top model and score, plus runner-up
            best = ranking[0]
            line = "  %-28s #1 %-16s %.2f" % (display, best["model"], best["score"])
            if len(ranking) > 1:
                second = ranking[1]
                line += "  #2 %-16s %.2f" % (second["model"], second["score"])
            print(line)


def _print_reference_data(agg: dict):
    """Print reference data (historical responses, not competing models)."""
    ref = agg.get("reference_data", [])
    if not ref:
        return

    print()
    print("  REFERENCE DATA (historical responses, not ranked competitively)")
    print("  " + "-" * 74)
    print("  %-5s %-24s %-9s %-9s %-9s %-9s %-8s" % (
        "", "Source", "Overall", "T1:Fund", "T2:QC", "T3:Genre", "Rating"
    ))
    print("  " + "-" * 74)

    for entry in ref:
        t1 = "%.2f" % entry["tier1"] if entry["tier1"] else "-"
        t2 = "%.2f" % entry["tier2"] if entry["tier2"] else "-"
        t3 = "%.2f" % entry["tier3"] if entry["tier3"] else "-"
        overall = "%.2f" % entry["overall"] if entry["overall"] else "-"
        print("  %-5s %-24s %-9s %-9s %-9s %-9s %-8s" % (
            "", entry["model"], overall, t1, t2, t3, entry["rating"]
        ))

    print("  " + "-" * 74)


def _print_judge_agreement(agg: dict):
    """Print inter-judge agreement stats."""
    models = agg["models"]
    has_multi_judge = any(
        len(s.get("judge_overalls", {})) >= 2 for s in models.values()
    )
    if not has_multi_judge:
        return

    print()
    print("  INTER-JUDGE AGREEMENT")
    print("  " + "-" * 60)
    for model, stats in models.items():
        jo = stats.get("judge_overalls", {})
        if len(jo) < 2:
            continue
        scores_str = ", ".join("%s=%.2f" % (j, s) for j, s in jo.items())
        spread = stats.get("judge_spread", 0)
        print("  %-24s %s (spread: %.2f)" % (model, scores_str, spread))


def aggregate_latest() -> dict:
    """Find and aggregate the most recent run."""
    if not RESULTS_DIR.exists():
        raise FileNotFoundError("No results directory at %s" % RESULTS_DIR)

    runs = sorted(RESULTS_DIR.glob("run_*.json"), reverse=True)
    if not runs:
        raise FileNotFoundError("No run files found")

    latest = runs[0]
    print("Aggregating: %s" % latest.name)
    return aggregate_run(latest)


def aggregate_multiple_runs(run_paths: list[str | Path]) -> dict:
    """Aggregate multiple runs together for multi-sampling analysis.

    Merges all results as if they were one big run, which naturally
    gives more data points per model/dimension for tighter CIs.
    """
    merged_results = []
    run_ids = []

    for path in run_paths:
        with open(path) as f:
            run = json.load(f)
        run_ids.append(run["run_id"])
        merged_results.extend(run["results"])

    # Create a synthetic merged run
    merged = {
        "run_id": "+".join(run_ids),
        "timestamp": None,
        "results": merged_results,
    }

    # Write temp file and aggregate
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(merged, f)
        tmp_path = f.name

    result = aggregate_run(tmp_path)
    Path(tmp_path).unlink()
    return result
