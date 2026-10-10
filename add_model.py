#!/usr/bin/env python3
"""Add a new model to RP-Bench: run all auto-runnable evaluations + refresh
the composite leaderboard.

Workflow:
    1. Validate the model key is registered in harness/config.py TEST_MODELS
    2. Run multi-turn adversarial benchmark (20 seeds × 12 turns + LLM-judge Likert)
    3. Run single-turn 27-dim rubric (27 completion scenarios + Sonnet 4 judge)
    4. Run flaw-hunter on the new multi-turn sessions
    5. Re-aggregate model_profiles.json, flaw_hunter_session_summary.json,
       behavioral_metrics.json
    6. Re-run pipeline/analyze_composite_score.py and print the new model's row

Steps that require manual action are flagged at the end:
    a. Download a fresh OpenRouter activity CSV (operational axes — Speed, Cost)
    b. Optional: run multi-turn arena with humans for the new model (the
       headline arena ELO; 0.35 of composite weight). Without arena votes
       the model's mt_arena_elo component imputes to z=0; the rank is
       still produced but flagged with `*` in the leaderboard.

Usage:
    python3 add_model.py <model_key>
    python3 add_model.py <model_key> --skip-multiturn      # already done
    python3 add_model.py <model_key> --skip-rubric         # already done
    python3 add_model.py <model_key> --dry-run             # show plan only

Cost estimate per model:
    ~$1-3 for chat-tier models, ~$5-10 for Opus-class.

Time estimate:
    ~30-60 minutes sequential, depending on model latency.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run(cmd, description, dry_run=False):
    """Run a subprocess and stream output. Aborts on non-zero exit."""
    print(f"\n{'=' * 70}")
    print(f"STEP: {description}")
    print(f"  $ {' '.join(cmd)}")
    print('=' * 70, flush=True)
    if dry_run:
        print("  [dry-run, skipped]")
        return
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"\nSTEP FAILED: {description} (exit {result.returncode})")
        sys.exit(result.returncode)


def validate_model(model_key: str):
    """Check the model is in harness.config.TEST_MODELS."""
    sys.path.insert(0, str(ROOT))
    from harness.config import TEST_MODELS
    if model_key not in TEST_MODELS:
        print(f"ERROR: model_key '{model_key}' is not registered in "
              f"harness/config.py TEST_MODELS.\n"
              f"Add it first:\n"
              f'  TEST_MODELS["{model_key}"] = "<openrouter/slug>"\n'
              f"then re-run this script.")
        sys.exit(2)
    return TEST_MODELS[model_key]


def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    ap.add_argument("model_key", help="Model key from TEST_MODELS (e.g. claude_opus_4_8)")
    ap.add_argument("--skip-multiturn", action="store_true",
                    help="Skip multi-turn session generation + LLM-judge")
    ap.add_argument("--skip-rubric", action="store_true",
                    help="Skip single-turn 27-dim rubric run")
    ap.add_argument("--skip-flaw-hunter", action="store_true",
                    help="Skip flaw-hunter scoring")
    ap.add_argument("--skip-aggregation", action="store_true",
                    help="Skip the analyze_*.py aggregation refresh")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the plan without running anything")
    args = ap.parse_args()

    slug = validate_model(args.model_key)
    print(f"Adding model: {args.model_key}")
    print(f"  OpenRouter slug: {slug}")

    # 1. Multi-turn adversarial run + LLM-judge Likert
    if not args.skip_multiturn:
        run(
            [sys.executable, "-u", "-m", "harness.cli", "multiturn",
             "--models", args.model_key,
             "--turns", "12",
             "--adversarial"],
            "Multi-turn adversarial sessions + LLM-judge Likert",
            args.dry_run,
        )

    # 2. Single-turn 27-dim rubric
    if not args.skip_rubric:
        run(
            [sys.executable, "-u", "-m", "harness.cli", "run",
             "--models", args.model_key,
             "--judges", "claude_sonnet",
             "--judge-mode", "standard",
             "--types", "completion",
             "--max", "27"],
            "Single-turn 27-dimension rubric (Sonnet 4 judge)",
            args.dry_run,
        )

    # 3. Flaw-hunter on the new multi-turn sessions
    if not args.skip_flaw_hunter:
        # Find the most recent multiturn_*.json for this model
        candidates = sorted(
            (ROOT / "results").glob("multiturn_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            print("WARN: no multiturn_*.json found. Skipping flaw-hunter.")
        else:
            latest = candidates[0]
            run(
                [sys.executable, "-u", "pipeline/judge_session_flaw_hunter.py",
                 "--source", str(latest)],
                f"Flaw-hunter scoring of {latest.name}",
                args.dry_run,
            )

    # 4. Re-aggregate analysis JSONs
    if not args.skip_aggregation:
        run(
            [sys.executable, "-u", "pipeline/analyze_model_profiles.py"],
            "Refresh results/model_profiles.json (Likert per model)",
            args.dry_run,
        )
        run(
            [sys.executable, "-u", "pipeline/analyze_flaw_hunter_sessions.py"],
            "Refresh results/flaw_hunter_session_summary.json",
            args.dry_run,
        )
        run(
            [sys.executable, "-u", "pipeline/analyze_behavioral_metrics.py"],
            "Refresh results/behavioral_metrics.json (TTR / repetition / etc.)",
            args.dry_run,
        )
        # Added 2026-10-10. Without this the matrix never refreshes: its
        # published copy had been computed on 20 models while the corpus
        # reached 47, which moved nine of its cells across zero. Nothing in
        # the script was stale -- only the file, because adding a model never
        # re-ran it.
        run(
            [sys.executable, "-u", "pipeline/analyze_method_correlations.py"],
            "Refresh results/method_correlations.json (cross-method matrix)",
            args.dry_run,
        )
        run(
            [sys.executable, "-u", "pipeline/compute_coverage.py"],
            "Refresh results/model_coverage.json (answer rate per model)",
            args.dry_run,
        )
        # The round-4 artifacts record a hash of every input they read, and
        # three of them read each other: continuity hashes round4_overview, so
        # the overview has to be rebuilt first and continuity last. That order
        # used to live nowhere -- getting it wrong surfaced only later, as a
        # test naming one stale input at a time. pipeline/check_freshness.py
        # derives it from the recorded hashes; this runs them in that order.
        for cmd in ("rounds/r4/analyze_round4_second_judge.py",
                    "rounds/r4/analyze_round4_overview.py",
                    "rounds/r4/analyze_round4_continuity.py"):
            run([sys.executable, "-u", cmd],
                "Rebuild %s (ordered: continuity hashes the overview)"
                % cmd.rsplit("/", 1)[-1],
                args.dry_run)

    # 4b. Nothing downstream may be stale once the refresh is done. This is a
    # gate, not a report: a stale artifact means something above ran in the
    # wrong order or was skipped, and publishing it would ship a number built
    # from a file that has since changed.
    if not args.skip_aggregation:
        run(
            [sys.executable, "-u", "pipeline/check_freshness.py"],
            "Verify no derived artifact was built from a file that has changed",
            args.dry_run,
        )

    # 5. Composite leaderboard
    run(
        [sys.executable, "-u", "pipeline/analyze_composite_score.py"],
        "Refresh composite_leaderboard.json with the new model's row",
        args.dry_run,
    )

    # Final guidance for the manual operational steps
    print()
    print("=" * 70)
    print("MANUAL FOLLOW-UPS (operational axes — Speed, Cost)")
    print("=" * 70)
    print(
        "1. Download a fresh OpenRouter activity CSV at\n"
        "      https://openrouter.ai/activity\n"
        "   (last 7 days, click Export -> CSV).\n"
        "2. Run:\n"
        "      python3 pipeline/analyze_latency.py ~/Downloads/openrouter_activity_*.csv\n"
        "      python3 pipeline/analyze_quality_speed.py\n"
        "      python3 pipeline/analyze_composite_score.py\n"
        "   This will populate the Speed and Cost columns for the new model.\n"
        "\n"
        "3. (Optional, for the headline rho) Open the multi-turn arena at\n"
        "      https://plotlightstudios.com/plotpoints\n"
        "   so the public can vote on the new model's sessions vs. existing ones.\n"
        "   Until human votes accumulate, the new model's mt_arena_elo component\n"
        "   imputes to z=0 and the row is flagged with `*` in the composite.\n"
    )


if __name__ == "__main__":
    main()
