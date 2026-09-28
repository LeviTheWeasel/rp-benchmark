#!/usr/bin/env python3
"""Export RP-Bench data to HuggingFace-ready Parquet format.

Exports:
- seeds.parquet — Synthetic scenario templates (public)
- rubric.parquet — All 26 scoring dimensions with scales
- results.parquet — Leaderboard scores per model per dimension (from latest run)
- round 4 (willingness): leaderboard JSON + parquet, J and quadrant charts,
  profile_cards_v2.md, rater-agreement summaries, Track A per-row labels,
  Track A / Track B seed files. See export_round4() for what is left out.
- round 4 overview (judge tier, J, watch-out; nothing summed) and continuity
  with rounds 1-3 (returning models, old judge as a band): the analyzers' JSON
  as is, round4_judge_elo.json as is, and one flat parquet each.

Does NOT export raw chat data or scenario content, never any round-4 Track B
transcript or reply text (docs/ROUND4_DESIGN.md sec 9), and never a
blind-judge keymap (results/judge_full_chatgpt/_manifest.json). Voter ids are
published raw by default: they are random per-voter UUIDs that exist to catch
vote stuffing, so the anti-stuffing analysis can be reproduced from the data.

Usage:
  python hf_dataset/export.py                    # everything, into hf_dataset/
  python hf_dataset/export.py --out DIR          # everything, into a staging dir
  python hf_dataset/export.py --only round4      # round-4 artifacts only
  python hf_dataset/export.py --offline          # skip the live arena-votes fetch
  python hf_dataset/export.py --votes-from PARQUET
                                                 # community_votes/ rebuilt from a
                                                 # local community_votes parquet
  python hf_dataset/export.py --voter-ids hmac   # voter ids as HMAC pseudonyms
                                                 # (PLOTPOINTS_VOTER_HMAC_SECRET)
  python hf_dataset/export.py --voter-ids drop   # no voter_id column
                                                 # (--drop-voter-ids is an alias)
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
    _guard_keymap, _guard_path, _guard_record, _is_track_b,
    _read_public_json, voter_pseudonym, voter_secret)
from fetch_arena_votes import (  # noqa: E402
    ARENA_CSV_URL, FETCH_TIMEOUT, carries_voter_ids, votes_from_csv)
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


# The site's public raw export of the round-1 single-message arena (CSV; it
# carries voter_id once the voter_id column ships on the site). The original
# arena's JSON endpoint is gone: its domain is no longer the project's, and
# nothing here fetches from it.
VOTES_URL = ARENA_CSV_URL
# How community_votes publishes voter ids: raw (default), hmac or drop.
VOTER_ID_MODES = ("raw", "hmac", "drop")
# The published vote fields, in column order. voter_id is added after vote_id
# by community_votes_table, as the mode says.
VOTE_FIELDS = ("vote_id", "timestamp", "scenario_id", "model_a", "model_b",
               "winner", "is_catch", "catch_correct")


def read_votes_parquet(path: Path) -> list[dict]:
    """Arena votes from an earlier community_votes export, for --votes-from.

    VOTE_FIELDS plus voter_id when the file has that column. Every row of a
    community_votes export is an arena vote."""
    path = Path(path)
    _guard_path(path)
    names = pq.read_schema(path).names
    missing = [c for c in VOTE_FIELDS if c not in names]
    if missing:
        raise SystemExit("%s is not a community_votes export: no %s"
                         % (path, ", ".join(missing)))
    cols = list(VOTE_FIELDS) + (["voter_id"] if "voter_id" in names else [])
    rows = pq.read_table(path, columns=cols).to_pylist()
    return [{"id": r["vote_id"], "mode": "arena",
             **{k: r[k] for k in cols if k != "vote_id"}} for r in rows]


def export_community_arena(offline: bool = False, voter_ids: str = "raw",
                           votes_from: Path | None = None):
    """Export community-voted leaderboard + raw votes to Parquet.

    Two outputs:
      - community_arena/train.parquet   — per-model aggregate (leaderboard)
      - community_votes/train.parquet   — one row per arena vote, with
                                          voter_id as voter_ids says: "raw"
                                          (default; random per-voter UUIDs,
                                          published so vote-stuffing checks can
                                          be reproduced), "hmac" (keyed
                                          pseudonyms, PLOTPOINTS_VOTER_HMAC_SECRET)
                                          or "drop" (no voter column).
    The votes come from the site's public CSV (VOTES_URL) or, with votes_from,
    from a local community_votes parquet. In raw and hmac modes a source with
    no voter ids stops the export instead of writing an empty column over a
    published one. The votes source is settled before anything is written, so
    a refusal or a failed fetch writes nothing.
    """
    if voter_ids not in VOTER_ID_MODES:
        raise ValueError("voter_ids must be one of %s" % (VOTER_ID_MODES,))
    arena = None
    secret = None
    if offline:
        print("Offline: skipping the live community_votes fetch")
    else:
        # Before any network: hmac mode needs its secret (VoterSecretError).
        if voter_ids == "hmac":
            secret = voter_secret()
        if votes_from is not None:
            arena = read_votes_parquet(votes_from)
            print("Votes: %d arena votes from %s" % (len(arena), votes_from))
        else:
            import urllib.request
            raw = None
            try:
                req = urllib.request.Request(
                    VOTES_URL, headers={"User-Agent": "rp-benchmark hf export"})
                with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
                    raw = resp.read()
            except Exception as e:
                raise SystemExit(
                    "Could not fetch live votes from %s (%s). community_votes/ "
                    "was NOT rebuilt. Re-run with --votes-from PARQUET (a local "
                    "community_votes export) or with --offline to leave it as "
                    "it is." % (VOTES_URL, e))
            # A CSV that is not the expected export stops here (SystemExit).
            arena = votes_from_csv(raw)
        if voter_ids != "drop" and not carries_voter_ids(arena):
            raise SystemExit(
                "the votes source carries no voter ids, so community_votes/ was "
                "NOT rebuilt (it would replace a published voter_id column with "
                "an empty one). Use a source with ids (the site CSV once its "
                "voter_id column is deployed, or --votes-from an id-bearing "
                "parquet), --voter-ids drop to publish without the column, or "
                "--offline to leave community_votes/ as it is.")

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

    # Raw votes. Skipped with --offline: the existing community_votes/
    # parquet is then left as it is.
    if arena is None:
        return
    if not arena:
        print("No arena votes to export")
        return
    table = community_votes_table(arena, voter_ids, secret)
    how = {"raw": "raw voter ids", "hmac": "voter ids as HMAC-SHA256 pseudonyms",
           "drop": "no voter_id column"}[voter_ids]
    pq.write_table(table, _out("community_votes", "train.parquet"))
    print("Exported: community_votes/train.parquet (%d votes, %s)"
          % (len(arena), how))


def _vote_columns(arena: list[dict]) -> dict:
    """The published vote fields (VOTE_FIELDS), in order; no voter column."""
    cols = {
        "vote_id": [v.get("id", "") for v in arena],
        "timestamp": [v.get("timestamp", "") for v in arena],
        "scenario_id": [v.get("scenario_id", "") for v in arena],
        "model_a": [v.get("model_a", "") for v in arena],
        "model_b": [v.get("model_b", "") for v in arena],
        "winner": [v.get("winner", "") for v in arena],
        "is_catch": [bool(v.get("is_catch")) for v in arena],
        "catch_correct": [v.get("catch_correct") for v in arena],
    }
    return cols


def community_votes_table(arena: list[dict], voter_ids: str = "raw",
                          secret: bytes | None = None):
    """One row per arena vote. voter_id follows vote_id: the raw id ("raw"),
    its keyed pseudonym ("hmac"), or no column at all ("drop")."""
    cols = _vote_columns(arena)
    if voter_ids == "drop":
        return pa.table(cols)
    if voter_ids == "hmac":
        ids = [voter_pseudonym(secret, v.get("voter_id")) for v in arena]
    elif voter_ids == "raw":
        ids = [v.get("voter_id") or "" for v in arena]
    else:
        raise ValueError("voter_ids must be one of %s" % (VOTER_ID_MODES,))
    return pa.table({"vote_id": cols.pop("vote_id"), "voter_id": ids, **cols})


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


def _guard_content(obj, where: str):
    """Every content guard: Track B text and a blind-judge keymap."""
    _guard_record(obj, where)
    _guard_keymap(obj, where)


def _write_json(obj, *parts):
    out = _out(*parts)
    _guard_path(out)
    _guard_content(obj, "/".join(parts))
    with open(out, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return out


def _write_parquet_rows(rows: list[dict], *parts):
    out = _out(*parts)
    _guard_path(out)
    _guard_content(rows, "/".join(parts))
    pq.write_table(pa.Table.from_pylist(rows), out)
    return out


def _copy_public(src: Path, *parts):
    """Copy a file byte for byte; JSON is parsed and guarded first."""
    _guard_path(src)
    out = _out(*parts)
    _guard_path(out)
    if src.suffix == ".json":
        _guard_content(_read_public_json(src), "/".join(parts))
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


# -----------------------------------------------------------------------------
# Round 4 overview and continuity
#
# analyze_round4_overview.py: judge tier, J and watch-out side by side, nothing
# summed, no position (rows inside a tier are alphabetical). Its judge ELO is a
# re-expression of the same scores and lives in round4_judge_elo.json only:
# that file is copied as is, and no ELO or rank enters the overview table.
#
# analyze_round4_continuity.py: the returning models with their earlier-round
# figures beside the round-4 ones, nothing converted. The old judge (the
# round-2/3 judge re-run on round-4 transcripts) leaves as a band, mean and
# half width, never a rank and never its interval ends as separate numbers
# (as export_plotpoints_round4.old_judge_band publishes it).
# -----------------------------------------------------------------------------

OVERVIEW_JUDGE = "subagent-sonnet-5"
CONTINUITY_OLD_JUDGE = "anthropic/claude-sonnet-4"
# Parquet column -> round4_overview.json judge_means key. Values as the JSON
# publishes them: the model + seed fit the tier is set on, and the plain mean.
OVERVIEW_JUDGE_MEANS = (("judge_overall", "overall"),
                        ("judge_agency", "S.5_agency_respect_session"),
                        ("judge_consistency", "S.1_consistency_over_time"),
                        ("judge_momentum", "S.3_narrative_momentum"))
OVERVIEW_WATCH_COUNTS = ("scenes", "turns", "answered_turns",
                         "empty_turns_outside_blank_scenes", "stub_turns",
                         "writes_your_character", "leaks", "loops")
# A row that carries any of these is refused: the judge ELO and its rank range
# belong to round4_judge_elo.json, never to the overview table.
OVERVIEW_ROW_BANNED = {"elo", "elo_lo", "elo_hi", "rank", "rank_lo", "rank_hi"}


def _tier_order(tier):
    return tier if tier else "Z"


def _scene_cell(s):
    """A blank scene is its seed id; a partial one {"seed", "answered",
    "turns"} reads "seed (answered of turns)"."""
    if isinstance(s, dict):
        return "%s (%s of %s)" % (s["seed"], s.get("answered"), s.get("turns"))
    return str(s)


def _overview_row(r, listed_as, jm, reason=None):
    j = r.get("J") or {}
    tier = r.get("judge_tier") or {}
    w = (r.get("watch_out") or {})
    c = w.get("counts") or {}
    m = jm.get(r["model"]) or {}
    row = {
        "model": r["model"],
        "listed_as": listed_as,
        "reason": reason,
        "n_seeds": r.get("n_seeds"),
        "judge_tier": tier.get("tier"),
        "judge_tier_band": tier.get("band"),
        "judge_n_sessions": m.get("n_sessions"),
        "judge_basis": m.get("basis"),
        "judge_note": m.get("note"),
    }
    for col, key in OVERVIEW_JUDGE_MEANS:
        row[col] = m.get(key)
        row[col + "_plain"] = m.get(key + "_plain")
    row.update({
        "J": j.get("value"),
        "J_display": j.get("display"),
        "J_status": j.get("status"),
        "J_quadrant": j.get("quadrant"),
        "J_unranked_reason": j.get("unranked_reason"),
    })
    for k in OVERVIEW_WATCH_COUNTS:
        row["watch_" + k] = c.get(k)
    row["watch_blank_scenes"] = len(c.get("blank_scenes") or [])
    row["watch_blank_scene_seeds"] = ",".join(
        _scene_cell(s) for s in c.get("blank_scenes") or [])
    row["watch_partial_scenes"] = len(c.get("partial_scenes") or [])
    row["watch_partial_scene_seeds"] = ",".join(
        _scene_cell(s) for s in c.get("partial_scenes") or [])
    row["watch_defects_source"] = c.get("defects_source")
    shown = w.get("shown") or []
    row["watch_out"] = ",".join(s["key"] for s in shown)
    row["watch_out_text"] = "; ".join(s["text"] for s in shown)
    return row


def round4_overview_rows(ov: dict) -> list[dict]:
    """One row per model in the overview: tiered, untiered, or absent.

    Tier, then name, as the overview orders them; untiered and absent models
    last. Refuses an overview that is not the Sonnet 5 judge's, whose tier and
    judge_means disagree, or whose rows carry an ELO or a rank."""
    jm_doc = ov.get("judge_means") or {}
    if jm_doc.get("judge") != OVERVIEW_JUDGE or not jm_doc.get("models"):
        raise SystemExit("round4_overview.json: judge_means missing or not from "
                         "%s; rerun analyze_round4_overview.py" % OVERVIEW_JUDGE)
    jm = jm_doc["models"]
    src = ([(r, "tiered", None) for r in ov["rows"]]
           + [(r, "untiered", r.get("reason")) for r in ov.get("unranked") or []]
           + [(r, "absent", r.get("reason")) for r in ov.get("absent") or []])
    for r, _, _ in src:
        hits = OVERVIEW_ROW_BANNED & set(r)
        if hits:
            raise SystemExit("round4_overview.json: row %s carries %s; the judge "
                             "ELO stays in round4_judge_elo.json"
                             % (r["model"], sorted(hits)))
        tier = (r.get("judge_tier") or {}).get("tier")
        if tier != (jm.get(r["model"]) or {}).get("tier"):
            raise SystemExit("round4_overview.json: %s tier %r differs from "
                             "judge_means" % (r["model"], tier))
    rows = [_overview_row(r, how, jm, reason) for r, how, reason in src]
    if len({r["model"] for r in rows}) != len(rows):
        raise SystemExit("round4_overview.json: a model is listed twice")
    rank_of = {"tiered": 0, "untiered": 1, "absent": 2}
    rows.sort(key=lambda r: (rank_of[r["listed_as"]],
                             _tier_order(r["judge_tier"]), r["model"]))
    return rows


def export_round4_overview():
    """Overview JSON and judge-ELO JSON as is, plus a flat overview parquet."""
    src = PROJECT_ROOT / "results" / "round4_overview.json"
    ov = _read_public_json(src)
    rows = round4_overview_rows(ov)
    _copy_public(src, "analysis", "round4_overview.json")
    _copy_public(PROJECT_ROOT / "results" / "round4_judge_elo.json",
                 "analysis", "round4_judge_elo.json")
    out = _write_parquet_rows(rows, "round4_overview", "train.parquet")
    n = {k: sum(1 for r in rows if r["listed_as"] == k)
         for k in ("tiered", "untiered", "absent")}
    print("Exported: analysis/round4_overview.json, analysis/round4_judge_elo.json, "
          "%s (%d tiered, %d untiered, %d absent)"
          % (out, n["tiered"], n["untiered"], n["absent"]))


def _r4_tier_cell(row):
    """The README's "R4 tier" cell: the letter, "untiered" for a model with
    round-4 craft sessions but too few seeds, or None with no craft run."""
    t = (row.get("v2_tier") or {}).get("tier")
    if t:
        return t
    return "untiered" if (row.get("same_transcripts") or {}).get("r4_sessions") else None


def round4_continuity_rows(cont: dict) -> list[dict]:
    """One row per returning model, the README table's fields, in its order
    (round-4 tier, then name; never by the old judge)."""
    oj = cont.get("old_judge") or {}
    if oj.get("judge") != CONTINUITY_OLD_JUDGE or not cont.get("rows"):
        raise SystemExit("round4_continuity.json: old_judge is not %s or no "
                         "rows; rerun analyze_round4_continuity.py"
                         % CONTINUITY_OLD_JUDGE)
    rows = []
    for r in cont["rows"]:
        h = r.get("r2_human") or {}
        r3 = r.get("r3_nsfw") or {}
        b = r.get("old_judge_r4")
        j = r.get("J") or {}
        tx = r.get("same_transcripts") or {}
        rows.append({
            "model": r["model"],
            "rounds": ",".join(r.get("rounds") or []),
            "finetune": bool(r.get("finetune")),
            "round4_runs": r.get("round4"),
            "r2_human_elo": h.get("elo"),
            "r2_human_ci95_low": (h.get("ci95") or [None, None])[0],
            "r2_human_ci95_high": (h.get("ci95") or [None, None])[1],
            "r2_human_n_votes": h.get("n_votes"),
            "r2_human_rank": h.get("rank"),
            "r2_human_of": h.get("of"),
            "r2_voted_transcripts": h.get("voted_transcripts"),
            "r3_nsfw_rank": r3.get("rank"),
            "r3_nsfw_tie": r3.get("tie"),
            "r3_nsfw_of": r3.get("of"),
            "r3_nsfw_craft": r3.get("craft"),
            "r3_nsfw_n": r3.get("n"),
            "r3_refusal_pct": r3.get("refusal_pct"),
            # A band: mean +/- half the 95% seed-bootstrap interval, two
            # decimals. Not a rank, not on the round-4 judge's scale.
            "old_judge_is_band": True if b else None,
            "old_judge_band_mean": round(float(b["mean"]), 2) if b else None,
            "old_judge_band_half_width": round(float(b["half_width"]), 2) if b else None,
            "old_judge_band_n_sessions": int(b["n_sessions"]) if b else None,
            "old_judge_missing": r.get("old_judge_r4_missing"),
            "r4_tier": _r4_tier_cell(r),
            "r4_tier_band": (r.get("v2_tier") or {}).get("band"),
            "J": j.get("value"),
            "J_display": j.get("display"),
            "J_rank": j.get("rank"),
            "J_ranked": j.get("ranked"),
            "J_of": j.get("of"),
            "J_unranked_reason": j.get("unranked_reason"),
            "r4_transcripts": tx.get("flag"),
            "r4_transcripts_generated": tx.get("generated"),
            "r4_transcripts_compared_with": tx.get("compared_with"),
            "r4_sessions": tx.get("r4_sessions"),
            "r4_sessions_identical": tx.get("identical"),
        })
    # analyze_round4_continuity.render_markdown's order: letter, then name;
    # "untiered" and no-craft rows after every letter.
    rows.sort(key=lambda r: (_tier_order(r["r4_tier"] if r["r4_tier"] != "untiered"
                                         else None), r["model"]))
    return rows


def export_round4_continuity():
    """Continuity JSON as is, plus one parquet row per returning model."""
    src = PROJECT_ROOT / "results" / "round4_continuity.json"
    cont = _read_public_json(src)
    rows = round4_continuity_rows(cont)
    _copy_public(src, "analysis", "round4_continuity.json")
    out = _write_parquet_rows(rows, "round4_continuity", "train.parquet")
    print("Exported: analysis/round4_continuity.json, %s (%d returning models, "
          "%d with an old-judge band)"
          % (out, len(rows), sum(1 for r in rows if r["old_judge_is_band"])))


def export_round4():
    export_round4_leaderboard()
    export_round4_figures()
    export_round4_agreement()
    export_round4_seeds()
    export_round4_overview()
    export_round4_continuity()


def audit_output():
    """Last check over everything under OUT_DIR, whoever wrote it."""
    n = 0
    for p in sorted(OUT_DIR.rglob("*")):
        rel = p.relative_to(OUT_DIR)
        if not p.is_file() or ".cache" in rel.parts:
            continue
        _guard_path(rel)
        if p.suffix == ".json":
            _guard_content(_read_public_json(p), str(rel))
        elif p.suffix == ".parquet":
            _guard_content(pq.read_table(p).to_pylist(), str(rel))
        n += 1
    print("Audit: %d files under %s: no private file, no Track B text, no "
          "blind-judge keymap" % (n, OUT_DIR))


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
    ap.add_argument("--voter-ids", choices=VOTER_ID_MODES, default="raw",
                    help="how community_votes/ publishes voter ids: raw (default), "
                         "hmac (needs %s) or drop (no column)" % VOTER_HMAC_ENV)
    ap.add_argument("--drop-voter-ids", action="store_true",
                    help="alias for --voter-ids drop")
    ap.add_argument("--votes-from", type=Path, metavar="PARQUET",
                    help="rebuild community_votes/ from this local community_votes "
                         "parquet instead of the live fetch")
    args = ap.parse_args()
    if args.drop_voter_ids:
        args.voter_ids = "drop"
    rebuilds_votes = args.voter_ids != "raw" or args.votes_from is not None
    if rebuilds_votes and (args.offline or args.only == "round4"):
        ap.error("--voter-ids/--drop-voter-ids/--votes-from rebuild "
                 "community_votes/, which --offline and --only round4 skip")
    if args.votes_from is not None and not args.votes_from.is_file():
        ap.error("--votes-from %s: no such file" % args.votes_from)
    if args.voter_ids == "hmac":
        # Refuse before anything is written, not halfway through.
        try:
            voter_secret()
        except VoterSecretError as e:
            ap.error("%s. Set %s, or choose --voter-ids raw or drop"
                     % (e, VOTER_HMAC_ENV))
    OUT_DIR = args.out.resolve()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Exporting RP-Bench data to HuggingFace format into %s\n" % OUT_DIR)
    if args.only != "round4":
        # First: its votes source (secret, fetch) is settled before it writes,
        # so a refusal or a failed fetch leaves OUT_DIR empty.
        export_community_arena(offline=args.offline,
                               voter_ids=args.voter_ids,
                               votes_from=args.votes_from)
        export_seeds()
        export_adversarial_seeds()
        export_rubric()
        export_results()
        export_leaderboard()
        export_elo()
        export_flaw_hunter_results()
        export_analysis_artifacts()
    export_round4()
    stage_card()
    audit_output()
    print("\nDone. Files are in %s" % OUT_DIR)
    print("\nTo upload to HuggingFace:")
    print("  hf upload lazyweasel/roleplay-bench %s . --repo-type dataset" % OUT_DIR)


if __name__ == "__main__":
    main()
