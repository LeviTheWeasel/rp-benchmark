#!/usr/bin/env python3
"""Per-model latency leaderboard from OpenRouter activity CSVs.

OpenRouter's activity export captures per-call timing (time-to-first-token
and total generation time) which we never recorded in our own logs.
This script ingests one or more CSVs, filters to RP-Bench traffic,
and produces a latency leaderboard:

  - Median TTFT (time to first token) — proxy for warm-up latency
  - Median generation time — total wall time per call
  - Tokens per second — output_tokens / generation_time
  - p95 generation time — tail latency
  - Time per 1k output tokens — length-normalized speed

Usage:
    # Single CSV
    python3 analyze_latency.py ~/Downloads/openrouter_activity_2026-04-24.csv

    # Glob pattern (multiple CSVs, deduped by generation_id)
    python3 analyze_latency.py ~/Downloads/openrouter_activity_*.csv

    # Default: all CSVs in ~/Downloads/ matching the openrouter_activity pattern
    python3 analyze_latency.py
"""
import argparse
import csv
import glob
import json
import os
import statistics as st
from collections import defaultdict
from pathlib import Path


def model_key_from_slug(slug: str) -> str:
    """Map openrouter permaslug → our short model key.
    e.g. 'anthropic/claude-opus-4.7' → 'claude_opus_4_7'
    """
    if not slug:
        return slug
    # Drop date suffixes like -20260205
    parts = slug.split("/", 1)
    base = parts[1] if len(parts) == 2 else parts[0]
    base = base.split("-")[:6]  # heuristic: drop trailing date
    rejoined = "-".join(base)
    return (
        rejoined.replace("-", "_")
        .replace(".", "_")
        .replace("claude_opus_4_7", "claude_opus_4_7")
        .replace("claude_sonnet_4_5", "claude_sonnet_4_5")
    )


# Manual mapping for known mismatches between OR slugs and our keys
SLUG_TO_KEY = {
    "anthropic/claude-opus-4.6":                         "claude_opus_4_6",
    "anthropic/claude-opus-4.7":                         "claude_opus_4_7",
    "anthropic/claude-4.6-opus-20260205":                "claude_opus_4_6",
    "anthropic/claude-4.7-opus-20260418":                "claude_opus_4_7",
    "anthropic/claude-sonnet-4.5":                       "claude_sonnet_4_5",
    "anthropic/claude-4.5-sonnet-20250929":              "claude_sonnet_4_5",
    "anthropic/claude-4-sonnet-20250522":                "claude_sonnet_4",  # the judge
    "anthropic/claude-sonnet-4":                         "claude_sonnet_4",
    "openai/gpt-4.1":                                    "gpt_4_1",
    "openai/gpt-4.1-2025-04-14":                         "gpt_4_1",
    "google/gemini-2.5-flash":                           "gemini_2_5_flash",
    "google/gemini-3.1-pro-preview":                     "gemini_3_1_pro",
    "google/gemini-3.1-flash-lite-preview":              "gemini_3_1_flash_lite",
    "google/gemma-4-26b-a4b-it":                         "gemma_4_26b",
    "google/gemma-4-26b-a4b-it-20260403":                "gemma_4_26b",
    "deepseek/deepseek-v3.2":                            "deepseek_v3_2",
    "deepseek/deepseek-v3.2-20251201":                   "deepseek_v3_2",
    "deepseek/deepseek-v4-pro":                          "deepseek_v4_pro",
    "deepseek/deepseek-v4-flash":                        "deepseek_v4_flash",
    "z-ai/glm-4.7":                                      "glm_4_7",
    "z-ai/glm-4.7-20251222":                             "glm_4_7",
    "z-ai/glm-5.1":                                      "glm_5_1",
    "x-ai/grok-4.1-fast":                                "grok_4_1",
    "minimax/minimax-m2.7":                              "minimax_m2_7",
    "minimax/minimax-m2.7-20260318":                     "minimax_m2_7",
    "qwen/qwen3.5-flash-02-23":                          "qwen3_5_flash",
    "qwen/qwen3.5-flash-20260224":                       "qwen3_5_flash",
    "mistralai/mistral-small-creative":                  "mistral_small_creative",
    "mistralai/mistral-small-creative-20251216":         "mistral_small_creative",
    "meta-llama/llama-4-maverick":                       "llama_4_maverick",
    "meta-llama/llama-4-maverick-17b-128e-instruct":     "llama_4_maverick",
    "moonshotai/kimi-k2.5":                              "kimi_k2_5",
    "moonshotai/kimi-k2.6":                              "kimi_k2_6",
}


def load_csvs(paths: list[str]) -> list[dict]:
    rows = []
    seen_ids = set()
    for p in paths:
        if not os.path.exists(p):
            print(f"  skip {p} (not found)")
            continue
        with open(p) as f:
            reader = csv.DictReader(f)
            for r in reader:
                gid = r.get("generation_id")
                if gid and gid in seen_ids:
                    continue
                seen_ids.add(gid)
                rows.append(r)
        print(f"  loaded {p}: total rows so far {len(rows)}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csvs", nargs="*", help="OpenRouter activity CSVs")
    ap.add_argument("--app", default="RP-Bench", help="Filter to this app_name")
    ap.add_argument("--include-judge", action="store_true",
                    help="Include judge-model calls in the per-model stats (default: exclude)")
    args = ap.parse_args()

    paths = args.csvs
    if not paths:
        paths = sorted(glob.glob(os.path.expanduser("~/Downloads/openrouter_activity*.csv")))
    if not paths:
        print("No CSVs found. Pass paths explicitly or download an OpenRouter activity export.")
        return

    print(f"Loading {len(paths)} CSV(s)...")
    rows = load_csvs(paths)
    print(f"Total unique rows: {len(rows)}")

    # Filter
    rows = [r for r in rows if r.get("app_name") == args.app]
    rows = [r for r in rows if r.get("cancelled") != "true"]
    print(f"After app + cancelled filter: {len(rows)}")
    if not rows:
        return

    # Group by our model key
    per_model = defaultdict(list)
    unknown_slugs = set()
    for r in rows:
        slug = r.get("model_permaslug", "")
        key = SLUG_TO_KEY.get(slug)
        if not key:
            # Try variant ID like 'anthropic/claude-opus-4.7' (no date)
            for known_slug, k in SLUG_TO_KEY.items():
                if slug.startswith(known_slug.split("-202")[0]):
                    key = k
                    break
        if not key:
            unknown_slugs.add(slug)
            continue
        per_model[key].append(r)

    if unknown_slugs:
        print(f"Unmapped slugs (skipped): {len(unknown_slugs)}")
        for s in sorted(unknown_slugs)[:5]:
            print(f"  {s}")

    # Decide which models are judges/user-sims
    JUDGE_KEYS = {"claude_sonnet_4"}
    USER_SIM_KEYS = {"gemini_2_5_flash"}
    # Note: gemini_2_5_flash is BOTH a test model AND the user simulator.
    # We can't tell them apart from the CSV alone, but in practice the
    # user-sim share dominates so we mark gemini_2_5_flash with a caveat.

    print()
    print("=" * 100)
    print("LATENCY LEADERBOARD (OpenRouter-reported)")
    print("=" * 100)
    print(f'{"Model":<28}{"calls":<8}{"TTFT":<8}{"med gen":<10}{"p95 gen":<10}{"tok/s":<7}{"out":<8}{"reas":<10}{"trunc":<8}{"$/call":<11}{"role"}')
    print("-" * 130)

    summary = {}
    for key, calls in sorted(per_model.items(), key=lambda x: -len(x[1])):
        def to_int(v):
            try: return int(float(v or 0))
            except: return 0

        ttfts = [to_int(r["time_to_first_token_ms"]) for r in calls if r.get("time_to_first_token_ms")]
        gens = [to_int(r["generation_time_ms"]) for r in calls if r.get("generation_time_ms")]
        outs = [to_int(r["tokens_completion"]) for r in calls if r.get("tokens_completion")]
        reasoning_tokens = [to_int(r.get("tokens_reasoning")) for r in calls]
        costs = [float(r.get("cost_total") or 0) for r in calls]
        finishes = [r.get("finish_reason_normalized", "") for r in calls]

        # Tokens per second (per call): out_tokens / (gen_time_s)
        rates = []
        for r in calls:
            ot = to_int(r.get("tokens_completion"))
            gt = to_int(r.get("generation_time_ms"))
            if ot > 50 and gt > 100:
                rates.append(ot / (gt / 1000))

        if not gens:
            continue

        median_ttft = st.median(ttfts) if ttfts else 0
        median_gen = st.median(gens)
        p95_gen = sorted(gens)[int(0.95 * len(gens))]
        median_out = st.median(outs) if outs else 0
        median_rate = st.median(rates) if rates else 0
        median_reasoning = st.median([r for r in reasoning_tokens if r > 0]) if any(r > 0 for r in reasoning_tokens) else 0
        reasoning_pct = sum(1 for r in reasoning_tokens if r > 0) / len(reasoning_tokens) * 100
        # Actual median cost per call (from OR's reported cost)
        paid_costs = [c for c in costs if c > 0]
        median_cost = st.median(paid_costs) if paid_costs else 0
        # Truncation rate (finish_reason='length')
        n_truncated = sum(1 for f in finishes if f == "length")
        trunc_pct = 100 * n_truncated / len(finishes) if finishes else 0

        role = ""
        if key in JUDGE_KEYS:
            role = "JUDGE"
        elif key in USER_SIM_KEYS:
            role = "user-sim"

        print(f'{key:<28}{len(calls):<8}{int(median_ttft):>5}ms   {int(median_gen):>6}ms  {int(p95_gen):>6}ms  {median_rate:>5.1f}  {int(median_out):>5}   {int(median_reasoning):>5}     {trunc_pct:>4.0f}%   ${median_cost:.4f}   {role}')

        summary[key] = {
            "calls": len(calls),
            "median_ttft_ms": int(median_ttft),
            "median_gen_ms": int(median_gen),
            "p95_gen_ms": int(p95_gen),
            "median_completion_tokens": int(median_out),
            "median_reasoning_tokens": int(median_reasoning),
            "uses_reasoning_pct": round(reasoning_pct, 1),
            "tokens_per_second": round(median_rate, 2),
            "median_actual_cost_usd": round(median_cost, 6),
            "truncation_pct": round(trunc_pct, 2),
            "role": role or "test_model",
        }

    print()
    print("Notes:")
    print("- TTFT (time to first token) is provider-reported; non-streaming calls have ttft=0.")
    print("- p95 gen captures tail latency. High p95 / median ratios suggest unstable inference.")
    print("- gemini_2_5_flash is mostly user-simulator traffic, not test-model.")
    print("- Judge (claude_sonnet_4) shown for reference but not directly comparable.")

    out = Path("results/latency_leaderboard.json")
    with open(out, "w") as f:
        json.dump({"sources": paths, "n_rows_after_filter": len(rows), "per_model": summary}, f, indent=2)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
