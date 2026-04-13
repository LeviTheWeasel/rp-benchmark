#!/usr/bin/env python3
"""Export RP-Bench data to HuggingFace-ready Parquet format.

Exports:
- seeds.parquet — Synthetic scenario templates (public)
- rubric.parquet — All 26 scoring dimensions with scales
- results.parquet — Leaderboard scores per model per dimension (from latest run)

Does NOT export raw chat data or scenario content.
"""
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).parent.parent
HF_DIR = Path(__file__).parent


def export_seeds():
    """Export synthetic seeds to Parquet."""
    with open(HF_DIR / "seeds" / "seeds.json") as f:
        seeds = json.load(f)

    table = pa.table({
        "id": [s["id"] for s in seeds],
        "genre_tags": [json.dumps(s["genre_tags"]) for s in seeds],
        "character_name": [s["character_name"] for s in seeds],
        "character_setting": [s["character_setting"] for s in seeds],
        "user_name": [s["user_name"] for s in seeds],
        "user_setting": [s["user_setting"] for s in seeds],
        "opening_message": [s["opening_message"] for s in seeds],
        "initial_user_input": [s["initial_user_input"] for s in seeds],
        "evaluation_focus": [json.dumps(s["evaluation_focus"]) for s in seeds],
        "num_turns": [s["num_turns"] for s in seeds],
        "difficulty": [s["difficulty"] for s in seeds],
    })

    out = HF_DIR / "seeds" / "train.parquet"
    pq.write_table(table, out)
    print("Exported: %s (%d seeds)" % (out, len(seeds)))


def export_rubric():
    """Export rubric dimensions to Parquet."""
    with open(PROJECT_ROOT / "analysis" / "scoring_rubric_v2.json") as f:
        rubric = json.load(f)

    rows = []
    for tier_name, tier_data in rubric["tiers"].items():
        for dim_key, dim_info in tier_data["dimensions"].items():
            rows.append({
                "dimension_id": dim_info.get("id", dim_key),
                "dimension_key": dim_key,
                "tier": tier_name,
                "tier_weight": tier_data["weight"],
                "category": dim_info.get("category", ""),
                "genres": json.dumps(dim_info.get("genres", [])),
                "sources": json.dumps(dim_info.get("sources", [])),
            })

    table = pa.table({
        "dimension_id": [r["dimension_id"] for r in rows],
        "dimension_key": [r["dimension_key"] for r in rows],
        "tier": [r["tier"] for r in rows],
        "tier_weight": [r["tier_weight"] for r in rows],
        "category": [r["category"] for r in rows],
        "genres": [r["genres"] for r in rows],
        "sources": [r["sources"] for r in rows],
    })

    out = HF_DIR / "rubric" / "train.parquet"
    pq.write_table(table, out)
    print("Exported: %s (%d dimensions)" % (out, len(rows)))


def export_results(run_path: Path | None = None):
    """Export leaderboard results to Parquet."""
    # Find latest leaderboard
    results_dir = PROJECT_ROOT / "results"
    if run_path:
        lb_files = [run_path]
    else:
        lb_files = sorted(results_dir.glob("leaderboard_*.json"), reverse=True)

    if not lb_files:
        print("No leaderboard files found. Run the benchmark first.")
        return

    with open(lb_files[0]) as f:
        agg = json.load(f)

    print("Using leaderboard: %s" % lb_files[0].name)

    # Flatten: one row per model per dimension
    rows = []
    for model, stats in agg.get("models", {}).items():
        is_ref = stats.get("is_reference", False)
        overall = stats.get("overall")

        for dim_key, dim_stats in stats.get("dimensions", {}).items():
            rows.append({
                "model": model,
                "is_reference": is_ref,
                "overall_score": overall,
                "dimension": dim_key,
                "mean": dim_stats.get("mean"),
                "stdev": dim_stats.get("stdev"),
                "ci95_low": dim_stats.get("ci95", [None, None])[0],
                "ci95_high": dim_stats.get("ci95", [None, None])[1],
                "n_samples": dim_stats.get("n"),
                "min_score": dim_stats.get("min"),
                "max_score": dim_stats.get("max"),
            })

    if not rows:
        print("No result data to export.")
        return

    table = pa.table({
        "model": [r["model"] for r in rows],
        "is_reference": [r["is_reference"] for r in rows],
        "overall_score": [r["overall_score"] for r in rows],
        "dimension": [r["dimension"] for r in rows],
        "mean": [r["mean"] for r in rows],
        "stdev": [r["stdev"] for r in rows],
        "ci95_low": [r["ci95_low"] for r in rows],
        "ci95_high": [r["ci95_high"] for r in rows],
        "n_samples": [r["n_samples"] for r in rows],
        "min_score": [r["min_score"] for r in rows],
        "max_score": [r["max_score"] for r in rows],
    })

    out = HF_DIR / "results" / "train.parquet"
    pq.write_table(table, out)
    print("Exported: %s (%d rows, %d models)" % (
        out, len(rows), len(set(r["model"] for r in rows))
    ))


def export_leaderboard(run_path: Path | None = None):
    """Export compact leaderboard (one row per model) to Parquet."""
    results_dir = PROJECT_ROOT / "results"
    if run_path:
        lb_files = [run_path]
    else:
        lb_files = sorted(results_dir.glob("leaderboard_*.json"), reverse=True)

    if not lb_files:
        print("No leaderboard files found.")
        return

    with open(lb_files[0]) as f:
        agg = json.load(f)

    lb = agg.get("leaderboard", [])
    ref = agg.get("reference_data", [])

    all_entries = [(e, False) for e in lb] + [(e, True) for e in ref]
    if not all_entries:
        print("No leaderboard entries.")
        return

    table = pa.table({
        "rank": [e["rank"] for e, _ in all_entries],
        "model": [e["model"] for e, _ in all_entries],
        "is_reference": [is_ref for _, is_ref in all_entries],
        "overall": [e.get("overall") for e, _ in all_entries],
        "tier1_fundamentals": [e.get("tier1") for e, _ in all_entries],
        "tier2_quality_control": [e.get("tier2") for e, _ in all_entries],
        "tier3_genre_craft": [e.get("tier3") for e, _ in all_entries],
        "rating": [e.get("rating", "") for e, _ in all_entries],
        "judge_spread": [e.get("judge_spread") for e, _ in all_entries],
        "scenarios": [e.get("scenarios") for e, _ in all_entries],
    })

    out = HF_DIR / "leaderboard" / "train.parquet"
    pq.write_table(table, out)
    print("Exported: %s (%d entries)" % (out, len(all_entries)))


def main():
    print("Exporting RP-Bench data to HuggingFace format...\n")
    export_seeds()
    export_rubric()
    export_results()
    export_leaderboard()
    print("\nDone. Files are in %s" % HF_DIR)
    print("\nTo upload to HuggingFace:")
    print("  cd %s" % HF_DIR)
    print("  hf upload lazyweasel/roleplay-bench . --repo-type dataset")


if __name__ == "__main__":
    main()
