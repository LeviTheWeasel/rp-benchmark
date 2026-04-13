"""RP-Bench: Roleplay quality benchmark for LLMs."""
from .runner import run_benchmark
from .aggregate import (
    aggregate_run,
    aggregate_latest,
    aggregate_multiple_runs,
    print_leaderboard,
)
