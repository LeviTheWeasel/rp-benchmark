#!/usr/bin/env python3
"""RP-Bench CLI — run benchmarks, aggregate results, view leaderboard."""
import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from harness.config import TEST_MODELS, JUDGE_MODELS, RESULTS_DIR
from harness.runner import run_benchmark
from harness.multiturn import run_multiturn_benchmark, print_multiturn_results
from harness.aggregate import (
    aggregate_run,
    aggregate_latest,
    aggregate_multiple_runs,
    print_leaderboard,
)
from harness.visualize import generate_all as generate_charts


def cmd_run(args):
    """Run the benchmark."""
    # Filter test models
    if args.models:
        test_models = {k: v for k, v in TEST_MODELS.items() if k in args.models}
        if not test_models:
            print("No matching test models. Available: %s" % list(TEST_MODELS.keys()))
            sys.exit(1)
    else:
        test_models = TEST_MODELS

    # Filter judge models
    if args.judges:
        judge_models = {k: v for k, v in JUDGE_MODELS.items() if k in args.judges}
    else:
        judge_models = JUDGE_MODELS

    # Scenario types
    scenario_types = args.types or ["completion"]
    num_runs = args.runs or 1

    language = getattr(args, 'language', None)

    print("Test models: %s" % list(test_models.keys()))
    print("Judge models: %s" % list(judge_models.keys()))
    print("Scenario types: %s" % scenario_types)
    print("Language: %s" % (language or "all"))
    print("Max scenarios: %s" % (args.max or "all"))
    print("Runs per scenario: %d" % num_runs)
    print()

    all_run_files = []

    for run_num in range(num_runs):
        if num_runs > 1:
            print("=" * 60)
            print("  RUN %d/%d" % (run_num + 1, num_runs))
            print("=" * 60)

        results = run_benchmark(
            test_models=test_models,
            judge_models=judge_models,
            scenario_types=scenario_types,
            max_scenarios=args.max,
            language=language,
        )

        run_file = RESULTS_DIR / ("run_%s.json" % results["run_id"])
        all_run_files.append(run_file)

    # Aggregate
    if len(all_run_files) == 1:
        agg = aggregate_run(all_run_files[0])
    else:
        print("\nAggregating %d runs..." % len(all_run_files))
        agg = aggregate_multiple_runs(all_run_files)

    # Save aggregation
    agg_file = RESULTS_DIR / ("leaderboard_%s.json" % agg["run_id"])
    with open(agg_file, "w") as f:
        json.dump(agg, f, indent=2)

    print_leaderboard(agg, view=args.view or "overall")

    # Auto-generate charts
    if args.charts:
        generate_charts(agg)


def cmd_charts(args):
    """Generate visualization charts from latest or specified run."""
    if args.run:
        run_file = RESULTS_DIR / args.run
        if not run_file.exists():
            run_file = RESULTS_DIR / ("run_%s.json" % args.run)
        agg = aggregate_run(run_file)
    else:
        agg = aggregate_latest()

    out_dir = Path(args.output) if args.output else None
    generate_charts(agg, output_dir=out_dir)


def cmd_leaderboard(args):
    """Show leaderboard from latest or specified run."""
    if args.run:
        run_file = RESULTS_DIR / args.run
        if not run_file.exists():
            run_file = RESULTS_DIR / ("run_%s.json" % args.run)
        agg = aggregate_run(run_file)
    else:
        agg = aggregate_latest()

    # Save aggregation
    agg_file = RESULTS_DIR / ("leaderboard_%s.json" % agg["run_id"])
    with open(agg_file, "w") as f:
        json.dump(agg, f, indent=2)

    print_leaderboard(agg, view=args.view or "overall")


def cmd_list_models(args):
    """List available models."""
    print("Test models (models being benchmarked):")
    for key, model_id in TEST_MODELS.items():
        print("  %s: %s" % (key, model_id))
    print()
    print("Judge models:")
    for key, model_id in JUDGE_MODELS.items():
        print("  %s: %s" % (key, model_id))


def cmd_multiturn(args):
    """Run multi-turn session benchmark."""
    if args.models:
        test_models = {k: v for k, v in TEST_MODELS.items() if k in args.models}
        if not test_models:
            print("No matching test models. Available: %s" % list(TEST_MODELS.keys()))
            sys.exit(1)
    else:
        test_models = TEST_MODELS

    if args.judges:
        judge_models = {k: v for k, v in JUDGE_MODELS.items() if k in args.judges}
    else:
        judge_models = JUDGE_MODELS

    results = run_multiturn_benchmark(
        test_models=test_models,
        judge_models=judge_models,
        user_sim_model=args.user_sim,
        num_turns=args.turns,
        max_seeds=args.max_seeds,
        seed_ids=args.seeds,
    )

    print_multiturn_results(results)


def cmd_test(args):
    """Quick test with 1 scenario, 1 model, 1 judge."""
    print("Quick test: 1 scenario, 1 model, 1 judge")
    print()

    first_test = next(iter(TEST_MODELS.items()))
    first_judge = next(iter(JUDGE_MODELS.items()))

    results = run_benchmark(
        test_models={first_test[0]: first_test[1]},
        judge_models={first_judge[0]: first_judge[1]},
        scenario_types=["completion"],
        max_scenarios=1,
    )

    # Print the judge output
    for r in results["results"]:
        if "error" in r:
            print("Error: %s" % r["error"])
            continue

        gen = r.get("generation", {})
        if gen.get("content"):
            print("\nGenerated response (%d chars):" % len(gen["content"]))
            print(gen["content"][:500])
            print("...")

        for jname, jdata in r.get("judges", {}).items():
            print("\nJudge (%s):" % jname)
            scores = jdata.get("scores", {})
            if scores.get("parse_error"):
                print("  PARSE ERROR. Raw: %s" % scores.get("raw_content", "")[:200])
            else:
                a = scores.get("aggregate", {})
                print("  Overall: %s (%s)" % (a.get("overall", "?"), a.get("rating", "?")))
                print("  Notes: %s" % scores.get("overall_notes", "N/A"))


def main():
    parser = argparse.ArgumentParser(
        description="RP-Bench: Roleplay quality benchmark for LLMs"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run
    run_parser = subparsers.add_parser("run", help="Run the benchmark")
    run_parser.add_argument(
        "--models", nargs="+", help="Test model keys to benchmark (default: all)"
    )
    run_parser.add_argument(
        "--judges", nargs="+", help="Judge model keys (default: all)"
    )
    run_parser.add_argument(
        "--types",
        nargs="+",
        choices=["completion", "preference", "consistency", "ooc_correction", "degradation"],
        help="Scenario types to run (default: completion)",
    )
    run_parser.add_argument(
        "--max", type=int, help="Maximum number of scenarios to run"
    )
    run_parser.add_argument(
        "--runs", type=int, default=1, help="Number of independent runs per scenario (default: 1, use 3 for confidence intervals)"
    )
    run_parser.add_argument(
        "--language", choices=["en", "ru"], help="Filter scenarios by language (default: all)"
    )
    run_parser.add_argument(
        "--view",
        choices=["overall", "tiers", "dimensions", "full"],
        default="overall",
        help="Leaderboard view (default: overall)",
    )
    run_parser.add_argument(
        "--charts", action="store_true", help="Auto-generate visualization charts after run"
    )
    run_parser.set_defaults(func=cmd_run)

    # multiturn
    mt_parser = subparsers.add_parser("multiturn", help="Run multi-turn session benchmark")
    mt_parser.add_argument(
        "--models", nargs="+", help="Test model keys (default: all)"
    )
    mt_parser.add_argument(
        "--judges", nargs="+", help="Judge model keys (default: all)"
    )
    mt_parser.add_argument(
        "--user-sim", default="google/gemini-2.5-flash",
        help="Model for user simulation (default: gemini-2.5-flash)",
    )
    mt_parser.add_argument(
        "--turns", type=int, default=20,
        help="Turns per session (default: 20)",
    )
    mt_parser.add_argument(
        "--max-seeds", type=int, help="Limit number of seeds"
    )
    mt_parser.add_argument(
        "--seeds", nargs="+", help="Specific seed IDs to run"
    )
    mt_parser.set_defaults(func=cmd_multiturn)

    # charts
    charts_parser = subparsers.add_parser("charts", help="Generate visualization charts")
    charts_parser.add_argument("--run", help="Specific run ID or filename")
    charts_parser.add_argument("--output", help="Output directory for charts")
    charts_parser.set_defaults(func=cmd_charts)

    # leaderboard
    lb_parser = subparsers.add_parser("leaderboard", help="Show leaderboard")
    lb_parser.add_argument("--run", help="Specific run ID or filename")
    lb_parser.add_argument(
        "--view",
        choices=["overall", "tiers", "dimensions", "full"],
        default="overall",
        help="Leaderboard view (default: overall)",
    )
    lb_parser.set_defaults(func=cmd_leaderboard)

    # list-models
    list_parser = subparsers.add_parser("list-models", help="List available models")
    list_parser.set_defaults(func=cmd_list_models)

    # test
    test_parser = subparsers.add_parser(
        "test", help="Quick test: 1 scenario, 1 model, 1 judge"
    )
    test_parser.set_defaults(func=cmd_test)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
