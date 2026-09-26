#!/usr/bin/env python3
"""Export RP-Bench data to HuggingFace-ready Parquet format.

Exports:
- seeds.parquet — Synthetic scenario templates (public)
- rubric.parquet — All 26 scoring dimensions with scales
- results.parquet — Leaderboard scores per model per dimension (from latest run)
- round 4 (willingness): leaderboard JSON + parquet, J and quadrant charts,
  profile_cards_v2.md, rater-agreement summaries, Track A per-row labels,
  Track A / Track B seed files. See export_round4() for what is left out.

Does NOT export raw chat data or scenario content, and never any round-4
Track B transcript or reply text (docs/ROUND4_DESIGN.md sec 9).

Usage:
  python hf_dataset/export.py                    # everything, into hf_dataset/
  python hf_dataset/export.py --out DIR          # everything, into a staging dir
  python hf_dataset/export.py --only round4      # round-4 artifacts only
  python hf_dataset/export.py --offline          # skip the live arena-votes fetch
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).parent.parent
# Run as a script, sys.path[0] is hf_dataset/, not the repo root; the shared
# guards live at the root. Appended, so nothing there shadows an import above.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
from publication_guards import (  # noqa: E402
    EVIDENCE_CAP, TEXT_FIELDS, TRACK_B, TRACK_B_SEED_PREFIXES,
    VOTER_HMAC_ENV, PublicationGuardError, VoterSecretError, _carries_text,
    _guard_path, _guard_record, _is_track_b, _read_public_json, voter_pseudonym,
    voter_secret)
HF_DIR = Path(__file__).parent
# Where exports are written. Sources are always read from HF_DIR/_source and
# PROJECT_ROOT/results; only the destination moves with --out.
OUT_DIR = HF_DIR


def _out(*parts) -> Path:
    """Destination path under OUT_DIR, with its parent directory created."""
    p = OUT_DIR.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def export_seeds():
    """Export synthetic seeds to Parquet."""
    with open(HF_DIR / "_source" / "seeds.json") as f:
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

    out = _out("seeds", "train.parquet")
    pq.write_table(table, out)
    print("Exported: %s (%d seeds)" % (out, len(seeds)))


def export_adversarial_seeds():
    """Export adversarial seeds to Parquet."""
    path = HF_DIR / "_source" / "adversarial_seeds.json"
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

    out = _out("adversarial_seeds", "train.parquet")
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

    out = _out("elo", "train.parquet")
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

    out = _out("rubric", "train.parquet")
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

    out = _out("results", "train.parquet")
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

    out = _out("leaderboard", "train.parquet")
    pq.write_table(table, out)
    print("Exported: %s (%d entries)" % (out, len(all_entries)))


def export_flaw_hunter_results():
    """Export flaw hunter per-model results to Parquet."""
    # Prefer merged (has Opus), fall back to any
    results_dir = PROJECT_ROOT / "results"
    merged = results_dir / "flaw_leaderboard_merged_opus.json"
    if merged.exists():
        fh_path = merged
    else:
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

    out = _out("flaw_hunter", "train.parquet")
    pq.write_table(table, out)
    print("Exported: %s (%d models)" % (out, len(lb)))


def export_community_arena(offline: bool = False):
    """Export community-voted leaderboard + raw votes to Parquet.

    Two outputs:
      - community_arena/train.parquet   — per-model aggregate (leaderboard)
      - community_votes/train.parquet   — one row per arena vote. voter_id
                                          is HMAC-SHA256(secret, raw id), never
                                          the raw id: that id is a long-lived
                                          voter cookie. The secret comes from
                                          PLOTPOINTS_VOTER_HMAC_SECRET; unset,
                                          the votes export refuses.
    """
    snapshot = PROJECT_ROOT / "results" / "community_arena_1000.json"
    if not snapshot.exists():
        candidates = sorted(
            (PROJECT_ROOT / "results").glob("community_arena*.json"), reverse=True
        )
        if not candidates:
            print("No community arena snapshot found (run analyze_community_arena.py)")
            return
        snapshot = candidates[0]

    with open(snapshot) as f:
        agg = json.load(f)

    lb = agg.get("leaderboard", [])
    if lb:
        table = pa.table({
            "rank": [e["rank"] for e in lb],
            "model": [e["model"] for e in lb],
            "elo": [e["elo"] for e in lb],
            "elo_stability": [e["stability"] for e in lb],
            "overall_winrate": [e["overall_winrate"] for e in lb],
            "overall_n": [e["overall_n"] for e in lb],
            "sfw_winrate": [e["sfw_winrate"] for e in lb],
            "sfw_n": [e["sfw_n"] for e in lb],
            "nsfw_winrate": [e["nsfw_winrate"] for e in lb],
            "nsfw_n": [e["nsfw_n"] for e in lb],
        })
        pq.write_table(table, _out("community_arena", "train.parquet"))
        print("Exported: community_arena/train.parquet (%d models)" % len(lb))

    # Raw votes — pulled live so the dataset tracks the current arena state.
    # Skipped if the production endpoint is unreachable, or with --offline
    # (the existing community_votes/ parquet is then left as it is).
    if offline:
        print("Offline: skipping the live community_votes fetch")
        return
    # Before any network: no secret, no votes (VoterSecretError).
    secret = voter_secret()
    import urllib.request
    try:
        with urllib.request.urlopen("https://arena.l3vi4th4n.ai/api/votes", timeout=30) as resp:
            votes = json.load(resp).get("votes", [])
    except Exception as e:
        print("Could not fetch live votes (%s) — skipping community_votes export" % e)
        return

    arena = [v for v in votes if v.get("mode") == "arena"]
    if not arena:
        print("No arena votes to export")
        return

    table = community_votes_table(arena, secret)
    pq.write_table(table, _out("community_votes", "train.parquet"))
    print("Exported: community_votes/train.parquet (%d votes, voter ids as "
          "HMAC-SHA256 pseudonyms)" % len(arena))


def community_votes_table(arena: list[dict], secret: bytes):
    """One row per arena vote; voter_id is the keyed pseudonym, never raw."""
    return pa.table({
        "vote_id": [v.get("id", "") for v in arena],
        "voter_id": [voter_pseudonym(secret, v.get("voter_id")) for v in arena],
        "timestamp": [v.get("timestamp", "") for v in arena],
        "scenario_id": [v.get("scenario_id", "") for v in arena],
        "model_a": [v.get("model_a", "") for v in arena],
        "model_b": [v.get("model_b", "") for v in arena],
        "winner": [v.get("winner", "") for v in arena],
        "is_catch": [bool(v.get("is_catch")) for v in arena],
        "catch_correct": [v.get("catch_correct") for v in arena],
    })


def export_analysis_artifacts():
    """Copy the project's analysis JSON/MD outputs into hf_dataset/analysis/.

    The HF Spaces leaderboard (and any external consumer) can fetch these
    via huggingface_hub.hf_hub_download(repo_id, filename="analysis/X.json",
    repo_type="dataset"). Files are static — re-exported each time this
    runs to keep them in sync with results/.
    """
    src_dir = PROJECT_ROOT / "results"
    out_dir = OUT_DIR / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Files we want to publish (whitelist — keeps junk from results/ out)
    files = [
        "community_arena_2000.json",
        "community_arena_bayesian.json",
        "multiturn_arena_bayesian.json",
        "multiturn_arena_bootstrap.json",
        "round3_multi_judge.json",
        "round3_kappa.json",
        "round3_cot_judge.json",
        "round3_cot_compare.json",
        "composite_leaderboard.json",
        "engagement_proxy.json",
        "engagement_regressor.json",
        "model_profiles.json",
        "behavioral_metrics.json",
        "method_correlations.json",
        "cost_efficiency.json",
        "latency_leaderboard.json",
        "quality_speed_leaderboard.json",
        "flaw_hunter_session_summary.json",
        "failure_target_validation.json",
        "adversarial_analysis.json",
        "adversarial_elo.json",
        "adversarial_pairwise_elo.json",
        "phase_a_analysis.json",
        "profile_cards.md",
        "profile_cards.json",
        "arena_timeseries.md",
        "pick_a_model.md",
        "model_clusters.json",
        "factor_analysis_matrix.json",
        "seed_discrimination_analysis.json",
        "multi_turn_analysis_report.json",
    ]
    n = 0
    for fname in files:
        src = src_dir / fname
        if not src.exists():
            print("  skip %s (not found)" % fname)
            continue
        _copy_public(src, "analysis", fname)
        n += 1
    print("Exported: analysis/ (%d files)" % n)


# -----------------------------------------------------------------------------
# Round 4 — willingness and judgment
#
# docs/ROUND4_DESIGN.md sec 9: no Track B transcript is exported, B-hard or
# B-policy. Published artifacts carry the label, a truncated evidence span and
# the judge rationale only. The raw Track B text lives in gitignored
# results/r4_trackb_transcripts__*.json companions (harness/r4_private.py);
# this script refuses to open them, and refuses to write any Track B record
# that carries dialogue or reply text.
#
# Track A transcripts are not exported either. Sec 9 says they "export as
# round 3's did", and round 3 exported no transcripts to this dataset: its
# analysis files carry scores and judge notes, and the transcripts stayed in
# results/round3gen_*.json in the source repo. Round 4's Track A transcripts
# are in results/r4_full_*.json there. What goes here is the numbers, the
# per-exchange labels for Track A, and the seeds.
# -----------------------------------------------------------------------------

# The guards themselves (TRACK_B, TEXT_FIELDS, EVIDENCE_CAP, _guard_path,
# _is_track_b, _guard_record, _read_public_json) live in the dependency-free
# publication_guards.py at the repo root, imported at the top of this file, so
# export_plotpoints_round4.py runs the same checks without pyarrow.
# The silent-refusal flag's thresholds, as in analyze_round4_willingness.py
# and make_j_barchart.py.
SILENT_EMPTY_RATE = 0.20
SILENT_RUNG_SLOPE = 0.25


def _write_json(obj, *parts):
    out = _out(*parts)
    _guard_path(out)
    _guard_record(obj, "/".join(parts))
    with open(out, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return out


def _write_parquet_rows(rows: list[dict], *parts):
    out = _out(*parts)
    _guard_path(out)
    _guard_record(rows, "/".join(parts))
    pq.write_table(pa.Table.from_pylist(rows), out)
    return out


def _copy_public(src: Path, *parts):
    """Copy a file byte for byte; JSON is parsed and guarded first."""
    _guard_path(src)
    out = _out(*parts)
    _guard_path(out)
    if src.suffix == ".json":
        _guard_record(_read_public_json(src), "/".join(parts))
    shutil.copy2(src, out)
    return out


def round4_flags(row: dict, rows: list[dict]) -> list[str]:
    """Reading flags for one leaderboard row. None of them changes a number.

    silent_refusal: a fifth or more of the Track A replies are empty and the
      empty rate climbs with the rung (the analyzer's own thresholds). J is
      then scored on the replies the model chose to give.
    reduced_data: fewer sessions than the full seed set, or fewer usable
      first asks than the full four, so one exchange weighs more.
    """
    flags = []
    if ((row.get("empty_rate_a") or 0) >= SILENT_EMPTY_RATE
            and (row.get("empty_rung_slope_a") or 0) >= SILENT_RUNG_SLOPE):
        flags.append("silent_refusal")
    top = lambda k: max((r.get(k) or 0) for r in rows)
    if (row["n_sessions_a"] < top("n_sessions_a")
            or row["n_sessions_b"] < top("n_sessions_b")
            or (row.get("held_first_n") or 0) < top("held_first_n")):
        flags.append("reduced_data")
    return flags


def export_round4_leaderboard():
    """Willingness leaderboard: the analyzer's JSON as is, plus a flat parquet.

    Needs the 2026-09-25 shape (ranked / rank / held_under_pressure): J on the
    first ask only, held_under_pressure beside it and not in J, and
    under-sampled models kept with their numbers but no rank.
    """
    src = PROJECT_ROOT / "results" / "round4_willingness_leaderboard.json"
    lb = _read_public_json(src)
    rows = lb["leaderboard"]
    missing = [r.get("model") for r in rows
               if not {"ranked", "rank", "held_under_pressure"} <= r.keys()]
    if missing:
        raise SystemExit(
            "round4_willingness_leaderboard.json predates the 2026-09-25 "
            "decisions (no ranked/rank/held_under_pressure on %d rows). Re-run "
            "analyze_round4_willingness.py first." % len(missing))
    _copy_public(src, "analysis", "round4_willingness_leaderboard.json")

    flat = []
    for r in rows:
        by_sub = r.get("empty_rate_a_by_subtrack") or {}
        flat.append({
            "rank": r["rank"],
            "ranked": r["ranked"],
            "unranked_reason": r["unranked_reason"],
            "model": r["model"],
            "J": r["J"],
            "held_line_rate": r["held_line_rate"],
            "held_first_n": r["held_first_n"],
            "held_under_pressure": r["held_under_pressure"],
            "held_under_pressure_n": r["held_under_pressure_n"],
            "folds_under_pressure": r["folds_under_pressure"],
            "over_refusal_hard_rungs": r["over_refusal_hard_rungs"],
            "over_refusal_hard_ungated": r["over_refusal_hard_ungated"],
            "over_refusal_rate": r["over_refusal_rate"],
            "over_refusal_intimacy": r["over_refusal_intimacy"],
            "over_refusal_gore": r["over_refusal_gore"],
            "policy_compliance_rate": r["policy_compliance_rate"],
            "overshoot_rate": r["overshoot_rate"],
            "quadrant": r["quadrant"],
            "n_sessions_a": r["n_sessions_a"],
            "n_sessions_b": r["n_sessions_b"],
            "usable_exchanges_a": r["usable_exchanges_a"],
            "exchanges_dropped_by_gate": r["exchanges_dropped_by_gate"],
            "gate_coverage": r["gate_coverage"],
            "hard_refusals_a": r["hard_refusals_a"],
            "empty_rate_a": r["empty_rate_a"],
            "empty_rate_a_intimacy": by_sub.get("intimacy"),
            "empty_rate_a_gore": by_sub.get("gore"),
            "empty_rung_slope_a": r["empty_rung_slope_a"],
            "flags": ",".join(round4_flags(r, rows)),
        })
    out = _write_parquet_rows(flat, "round4_leaderboard", "train.parquet")
    print("Exported: %s (%d models, %d ranked)"
          % (out, len(flat), sum(1 for r in flat if r["ranked"])))


def export_round4_figures():
    """J bar chart, 2x2 quadrant chart and the v2 profile cards, as built."""
    for fname in ("r4_j_leaderboard.svg", "round4_quadrants.svg",
                  "profile_cards_v2.md"):
        src = PROJECT_ROOT / "results" / fname
        if not src.exists():
            raise SystemExit("missing %s: build it before exporting" % src)
        _copy_public(src, "analysis", fname)
    print("Exported: analysis/ (J chart, quadrant chart, profile_cards_v2.md)")


def export_round4_agreement():
    """Rater agreement: Jev vs the Sonnet labels, and the GPT-5.5 cross-check.

    Summaries (by_track and calibration) for every wave. Per-row data for
    Track A only, as labels: no reply text (see the block comment above) and
    no Track B rows at all. round4_kappa.json is the older GPT-5.5 sample,
    already scope-labelled; its disagreements are labels only.
    """
    # The same files the analyzer reads (its JEV_FILES glob). The undated
    # results/jev_vs_sonnet_r4.json is an earlier wave-2 run and is not used.
    jev_files = sorted((PROJECT_ROOT / "results").glob("jev_vs_sonnet_r4_*.json"))
    if not jev_files:
        raise SystemExit("no results/jev_vs_sonnet_r4_*.json")
    waves, rows = [], []
    for f in jev_files:
        d = _read_public_json(f)
        waves.append({"file": f.name, "rater": d["model"], "wave": d["wave"],
                      "n": d["n"], "by_track": d["by_track"],
                      "calibration": d["calibration"]})
        for r in d["rows"]:
            if r.get("track") != "A":
                continue
            p = r.get("probabilities") or {}
            rows.append({
                "wave": d["wave"], "rater": d["model"],
                "model": r["model"], "seed": r["seed"],
                "rung": r["rung"], "turn": r.get("turn"),
                "rung_desc": r.get("desc"),
                "sonnet_label": r["sonnet"], "jev_label": r["jev"],
                "jev_confidence": r.get("confidence"),
                "p_engaged": p.get("engaged"),
                "p_soft_deflect": p.get("soft_deflect"),
                "p_refused": p.get("refused"),
            })
    summary = {
        "label": "Jev vs Sonnet on round-4 exchanges, per roster wave",
        "scope": ("by_track and calibration as each wave's run wrote them; "
                  "these are the published inter-rater figures. Per-row data "
                  "for Track A is the round4_rater_agreement config, labels "
                  "only. Track B rows are not published (ROUND4_DESIGN sec 9)."),
        "gate": ("over_refusal_hard_rungs counts a Track A L3-L5 exchange only "
                 "where jev_confidence >= 0.6."),
        "b_hard_by_turn": ("B-hard kappa by turn, from the leaderboard notes: "
                           "0.855 at the first ask (turn 2, n=225), 0.525 at "
                           "the second push (turn 4, n=225, 95% bootstrap "
                           "about 0.41-0.63). Only the first ask is in J."),
        "waves": waves,
    }
    _write_json(summary, "analysis", "round4_jev_vs_sonnet.json")
    _copy_public(PROJECT_ROOT / "results" / "round4_kappa.json",
                 "analysis", "round4_kappa.json")
    out = _write_parquet_rows(rows, "round4_rater_agreement", "train.parquet")
    print("Exported: analysis/round4_jev_vs_sonnet.json (%d waves), "
          "analysis/round4_kappa.json, %s (%d Track A rows)"
          % (len(waves), out, len(rows)))


def export_round4_seeds():
    """Track A ladders and Track B probes, as the repo tracks them."""
    def enc(v):
        return json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v

    for fname, cfg in (("adversarial_seeds_r4_track_a.json", "round4_track_a_seeds"),
                       ("adversarial_seeds_r4_track_b.json", "round4_track_b_probes")):
        src = HF_DIR / "_source" / fname
        seeds = _read_public_json(src)
        keys = []
        for s in seeds:
            keys += [k for k in s if k not in keys]
        rows = [{k: enc(s.get(k)) for k in keys} for s in seeds]
        out = _write_parquet_rows(rows, cfg, "train.parquet")
        if OUT_DIR != HF_DIR:
            _copy_public(src, "_source", fname)
        print("Exported: %s (%d seeds)" % (out, len(rows)))


def export_round4():
    export_round4_leaderboard()
    export_round4_figures()
    export_round4_agreement()
    export_round4_seeds()


def audit_output():
    """Last check over everything under OUT_DIR, whoever wrote it."""
    n = 0
    for p in sorted(OUT_DIR.rglob("*")):
        rel = p.relative_to(OUT_DIR)
        if not p.is_file() or ".cache" in rel.parts:
            continue
        _guard_path(rel)
        if p.suffix == ".json":
            _guard_record(_read_public_json(p), str(rel))
        elif p.suffix == ".parquet":
            _guard_record(pq.read_table(p).to_pylist(), str(rel))
        n += 1
    print("Audit: %d files under %s: no private file, no Track B text"
          % (n, OUT_DIR))


def stage_card():
    """A staging dir is a complete upload: carry the card and the seed sources."""
    if OUT_DIR == HF_DIR:
        return
    shutil.copy2(HF_DIR / "README.md", _out("README.md"))
    for fname in ("seeds.json", "adversarial_seeds.json",
                  "adversarial_seeds_v2.json", "adversarial_seeds_v3_bigcard.json"):
        _copy_public(HF_DIR / "_source" / fname, "_source", fname)


def main():
    global OUT_DIR
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=HF_DIR,
                    help="write here instead of hf_dataset/ (a staging dir to upload)")
    ap.add_argument("--only", choices=["round4"],
                    help="export only this part")
    ap.add_argument("--offline", action="store_true",
                    help="skip the live community-votes fetch")
    args = ap.parse_args()
    if args.only != "round4" and not args.offline:
        # Refuse before anything is written, not halfway through.
        try:
            voter_secret()
        except VoterSecretError as e:
            ap.error("%s. Set %s, or pass --offline to leave community_votes/ "
                     "as it is" % (e, VOTER_HMAC_ENV))
    OUT_DIR = args.out.resolve()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Exporting RP-Bench data to HuggingFace format into %s\n" % OUT_DIR)
    if args.only != "round4":
        export_seeds()
        export_adversarial_seeds()
        export_rubric()
        export_results()
        export_leaderboard()
        export_elo()
        export_flaw_hunter_results()
        export_community_arena(offline=args.offline)
        export_analysis_artifacts()
    export_round4()
    stage_card()
    audit_output()
    print("\nDone. Files are in %s" % OUT_DIR)
    print("\nTo upload to HuggingFace:")
    print("  hf upload lazyweasel/roleplay-bench %s . --repo-type dataset" % OUT_DIR)


if __name__ == "__main__":
    main()
