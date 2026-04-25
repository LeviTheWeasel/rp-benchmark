"""RP-Bench CLI entry point.

Installed as the `rp-bench` console script via pyproject.toml. The CLI
logic itself lives in this module so `python -m harness.cli` and
`rp-bench` both work, and `python run.py` (the legacy entrypoint at
the repo root) can shim into this same `main()`.

Subcommands:
    run         single-turn benchmark (generate + judge)
    multiturn   multi-turn session benchmark
    test        smoke test with 1 scenario / 1 model / 1 judge
    leaderboard render existing aggregations
    charts      regenerate visualizations
    list-models show TEST_MODELS / JUDGE_MODELS
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import TEST_MODELS, JUDGE_MODELS, RESULTS_DIR
from .runner import run_benchmark
from .multiturn import run_multiturn_benchmark, print_multiturn_results
from .aggregate import (
    aggregate_run,
    aggregate_latest,
    aggregate_multiple_runs,
    print_leaderboard,
)
from .visualize import generate_all as generate_charts


def cmd_run(args):
    if args.models:
        test_models = {k: v for k, v in TEST_MODELS.items() if k in args.models}
        if not test_models:
            print("No matching test models. Available: %s" % list(TEST_MODELS.keys()))
            sys.exit(1)
    else:
        test_models = TEST_MODELS

    judge_models = (
        {k: v for k, v in JUDGE_MODELS.items() if k in args.judges}
        if args.judges
        else JUDGE_MODELS
    )

    scenario_types = args.types or ["completion"]
    num_runs = args.runs or 1
    language = getattr(args, "language", None)
    judge_mode = getattr(args, "judge_mode", "standard")

    print("Test models: %s" % list(test_models.keys()))
    print("Judge models: %s" % list(judge_models.keys()))
    print("Judge mode: %s" % judge_mode)
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
            judge_mode=judge_mode,
        )

        run_file = RESULTS_DIR / ("run_%s.json" % results["run_id"])
        all_run_files.append(run_file)

    if len(all_run_files) == 1:
        agg = aggregate_run(all_run_files[0])
    else:
        print("\nAggregating %d runs..." % len(all_run_files))
        agg = aggregate_multiple_runs(all_run_files)

    agg_file = RESULTS_DIR / ("leaderboard_%s.json" % agg["run_id"])
    with open(agg_file, "w") as f:
        json.dump(agg, f, indent=2)

    print_leaderboard(agg, view=args.view or "overall")

    if args.charts:
        generate_charts(agg)


def cmd_multiturn(args):
    test_models = (
        {k: v for k, v in TEST_MODELS.items() if k in args.models}
        if args.models
        else TEST_MODELS
    )
    if args.models and not test_models:
        print("No matching test models. Available: %s" % list(TEST_MODELS.keys()))
        sys.exit(1)

    judge_models = (
        {k: v for k, v in JUDGE_MODELS.items() if k in args.judges}
        if args.judges
        else JUDGE_MODELS
    )

    results = run_multiturn_benchmark(
        test_models=test_models,
        judge_models=judge_models,
        user_sim_model=args.user_sim,
        num_turns=args.turns,
        max_seeds=args.max_seeds,
        seed_ids=args.seeds,
        adversarial=getattr(args, "adversarial", False),
    )
    print_multiturn_results(results)


def cmd_charts(args):
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
    if args.run:
        run_file = RESULTS_DIR / args.run
        if not run_file.exists():
            run_file = RESULTS_DIR / ("run_%s.json" % args.run)
        agg = aggregate_run(run_file)
    else:
        agg = aggregate_latest()

    agg_file = RESULTS_DIR / ("leaderboard_%s.json" % agg["run_id"])
    with open(agg_file, "w") as f:
        json.dump(agg, f, indent=2)
    print_leaderboard(agg, view=args.view or "overall")


def cmd_list_models(args):
    print("Test models (models being benchmarked):")
    for key, model_id in TEST_MODELS.items():
        print("  %s: %s" % (key, model_id))
    print()
    print("Judge models:")
    for key, model_id in JUDGE_MODELS.items():
        print("  %s: %s" % (key, model_id))


def cmd_test(args):
    print("Quick test: 1 scenario, 1 model, 1 judge\n")
    first_test = next(iter(TEST_MODELS.items()))
    first_judge = next(iter(JUDGE_MODELS.items()))

    results = run_benchmark(
        test_models={first_test[0]: first_test[1]},
        judge_models={first_judge[0]: first_judge[1]},
        scenario_types=["completion"],
        max_scenarios=1,
    )

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rp-bench",
        description="RP-Bench: Roleplay quality benchmark for LLMs",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run
    run_p = subparsers.add_parser("run", help="Run the single-turn benchmark")
    run_p.add_argument("--models", nargs="+", help="Test model keys (default: all)")
    run_p.add_argument("--judges", nargs="+", help="Judge model keys (default: all)")
    run_p.add_argument(
        "--types", nargs="+",
        choices=["completion", "preference", "consistency", "ooc_correction", "degradation"],
        help="Scenario types (default: completion)",
    )
    run_p.add_argument("--max", type=int, help="Max scenarios")
    run_p.add_argument("--runs", type=int, default=1, help="Independent runs per scenario")
    run_p.add_argument("--language", choices=["en", "ru"], help="Language filter")
    run_p.add_argument(
        "--judge-mode",
        choices=["standard", "flaw_hunter", "comparative"],
        default="standard",
    )
    run_p.add_argument(
        "--view",
        choices=["overall", "tiers", "dimensions", "full"],
        default="overall",
    )
    run_p.add_argument("--charts", action="store_true")
    run_p.set_defaults(func=cmd_run)

    # multiturn
    mt_p = subparsers.add_parser("multiturn", help="Run multi-turn benchmark")
    mt_p.add_argument("--models", nargs="+")
    mt_p.add_argument("--judges", nargs="+")
    mt_p.add_argument("--user-sim", default="google/gemini-2.5-flash")
    mt_p.add_argument("--turns", type=int, default=20)
    mt_p.add_argument("--max-seeds", type=int)
    mt_p.add_argument("--seeds", nargs="+")
    mt_p.add_argument("--adversarial", action="store_true")
    mt_p.set_defaults(func=cmd_multiturn)

    # charts
    ch_p = subparsers.add_parser("charts", help="Regenerate visualizations")
    ch_p.add_argument("--run")
    ch_p.add_argument("--output")
    ch_p.set_defaults(func=cmd_charts)

    # leaderboard
    lb_p = subparsers.add_parser("leaderboard", help="Show leaderboard")
    lb_p.add_argument("--run")
    lb_p.add_argument(
        "--view",
        choices=["overall", "tiers", "dimensions", "full"],
        default="overall",
    )
    lb_p.set_defaults(func=cmd_leaderboard)

    # list-models
    ls_p = subparsers.add_parser("list-models", help="List available models")
    ls_p.set_defaults(func=cmd_list_models)

    # test
    t_p = subparsers.add_parser("test", help="Quick smoke test")
    t_p.set_defaults(func=cmd_test)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
