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
        "challenge_turns": [json.dumps(s.get("challenge_turns", [])) for s in seeds],
    })

    out = HF_DIR / "seeds" / "train.parquet"
    pq.write_table(table, out)
    print("Exported: %s (%d seeds)" % (out, len(seeds)))


def export_adversarial_seeds():
    """Export adversarial seeds to Parquet."""
    path = HF_DIR / "seeds" / "adversarial_seeds.json"
    if not path.exists():
        print("No adversarial seeds found")
        return
    with open(path) as f:
        seeds = json.load(f)

    table = pa.table({
        "id": [s["id"] for s in seeds],
        "genre_tags": [json.dumps(s["genre_tags"]) for s in seeds],
        "difficulty": [s["difficulty"] for s in seeds],
        "failure_target": [s["failure_target"] for s in seeds],
        "character_name": [s["character_name"] for s in seeds],
        "character_setting": [s["character_setting"] for s in seeds],
        "user_name": [s["user_name"] for s in seeds],
        "user_setting": [s["user_setting"] for s in seeds],
        "opening_message": [s["opening_message"] for s in seeds],
        "initial_user_input": [s["initial_user_input"] for s in seeds],
        "challenge_turns": [json.dumps(s["challenge_turns"]) for s in seeds],
        "num_turns": [s["num_turns"] for s in seeds],
        "evaluation_focus": [json.dumps(s["evaluation_focus"]) for s in seeds],
    })

    out_dir = HF_DIR / "adversarial_seeds"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "train.parquet"
    pq.write_table(table, out)
    print("Exported: %s (%d adversarial seeds)" % (out, len(seeds)))


def export_elo():
    """Export ELO leaderboard to Parquet."""
    elo_path = PROJECT_ROOT / "results" / "elo_leaderboard.json"
    if not elo_path.exists():
        print("No ELO leaderboard found")
        return

    with open(elo_path) as f:
        elo = json.load(f)

    ratings = elo.get("ratings", {})
    stability = elo.get("stability", {})
    winrates = elo.get("winrates", {})

    # Sort by rating
    ranked = sorted(ratings.items(), key=lambda x: -x[1])

    rows = []
    for rank, (model, rating) in enumerate(ranked, 1):
        total_w = total_l = total_t = 0
        opps = winrates.get(model, {})
        for opp, rec in opps.items():
            total_w += rec.get("wins", 0)
            total_l += rec.get("losses", 0)
            total_t += rec.get("ties", 0)

        total = total_w + total_l + total_t
        winrate = (total_w + 0.5 * total_t) / total if total > 0 else 0

        rows.append({
            "rank": rank,
            "model": model,
            "elo": round(rating, 1),
            "stability": round(stability.get(model, 0), 2),
            "wins": total_w,
            "losses": total_l,
            "ties": total_t,
            "winrate": round(winrate, 3),
        })

    table = pa.table({
        "rank": [r["rank"] for r in rows],
        "model": [r["model"] for r in rows],
        "elo": [r["elo"] for r in rows],
        "stability": [r["stability"] for r in rows],
        "wins": [r["wins"] for r in rows],
        "losses": [r["losses"] for r in rows],
        "ties": [r["ties"] for r in rows],
        "winrate": [r["winrate"] for r in rows],
    })

    out_dir = HF_DIR / "elo"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "train.parquet"
    pq.write_table(table, out)
    print("Exported: %s (%d models)" % (out, len(rows)))


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


def export_flaw_hunter_results():
    """Export flaw hunter per-model results to Parquet."""
    fh_path = PROJECT_ROOT / "results" / "flaw_leaderboard_20260413_231835.json"
    if not fh_path.exists():
        # Find any flaw leaderboard
        results_dir = PROJECT_ROOT / "results"
        files = sorted(results_dir.glob("flaw_leaderboard_*.json"), reverse=True)
        if not files:
            print("No flaw hunter leaderboard found")
            return
        fh_path = files[0]

    with open(fh_path) as f:
        data = json.load(f)

    lb = data.get("leaderboard", [])
    if not lb:
        print("No flaw hunter data")
        return

    table = pa.table({
        "model": [e["model"] for e in lb],
        "avg_score": [e["avg_score"] for e in lb],
        "min": [e["min"] for e in lb],
        "max": [e["max"] for e in lb],
        "avg_fatal_flaws": [e["avg_fatal"] for e in lb],
        "avg_major_flaws": [e["avg_major"] for e in lb],
        "avg_minor_flaws": [e["avg_minor"] for e in lb],
        "avg_bonuses": [e["avg_bonus"] for e in lb],
        "n_scenarios": [e["n"] for e in lb],
    })

    out_dir = HF_DIR / "flaw_hunter"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "train.parquet"
    pq.write_table(table, out)
    print("Exported: %s (%d models)" % (out, len(lb)))


def main():
    print("Exporting RP-Bench data to HuggingFace format...\n")
    export_seeds()
    export_adversarial_seeds()
    export_rubric()
    export_results()
    export_leaderboard()
    export_elo()
    export_flaw_hunter_results()
    print("\nDone. Files are in %s" % HF_DIR)
    print("\nTo upload to HuggingFace:")
    print("  cd %s" % HF_DIR)
    print("  hf upload lazyweasel/roleplay-bench . --repo-type dataset")


if __name__ == "__main__":
    main()
