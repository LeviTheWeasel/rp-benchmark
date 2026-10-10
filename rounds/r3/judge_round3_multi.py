#!/usr/bin/env python3
"""Round 3: re-judge a stratified sub-sample with two additional LLM judges.

Currently: 336 multi-turn sessions are scored by Anthropic Claude Sonnet 4.
The +0.495 cross-method correlation reported in our paper depends on this
single judge, which is the most predictable reviewer concern.

This script picks N sessions stratified across models and seeds, runs each
through two additional judges (Gemini 3.1 Pro and OpenRouter's
~openai/gpt-latest auto-route, currently GPT-5.5), and saves their scores
alongside the existing Sonnet 4 scores. Downstream:
rounds/r3/analyze_round3_kappa.py computes pairwise weighted Cohen's kappa and
per-judge cross-method Spearman rho.

Stratification: 3 sessions per model x 20 models = 60 sessions, with
the 3 sessions per model chosen across different adversarial seeds when
possible (so each judge sees diverse failure-mode content per model).

Cost estimate: 60 sessions x ~10K input tokens x 2 judges
  = ~$5 GPT-5.5 + ~$2 Gemini 3.1 Pro = ~$7 total

Usage:
    # Test on 5 sessions x 2 judges (~$1)
    python3 rounds/r3/judge_round3_multi.py --n-per-model 1 --max-models 5

    # Full 60-session run
    python3 rounds/r3/judge_round3_multi.py
"""
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness import multiturn
from harness.multiturn import judge_session


SESSIONS_FILE = Path("results/multiturn_merged_all_v2.json")
OUT_FILE = Path("results/round3_multi_judge.json")

# OpenRouter auto-route slugs.
SECOND_JUDGES = {
    "gemini_3_1_pro": "google/gemini-3.1-pro-preview",
    "gpt_latest":     "~openai/gpt-latest",
}

# Per-judge max_tokens override. Reasoning models burn extra budget on
# internal thinking before emitting the JSON; the default 4096 truncated
# Gemini's structured output mid-rationale on long sessions.
JUDGE_MAX_TOKENS = {
    "gemini_3_1_pro": 16000,
    "gpt_latest":     8000,
}


def stratified_subsample(sessions, n_per_model, max_models, rng):
    """Pick n_per_model sessions per model, biased toward diverse seeds."""
    by_model: dict[str, list[dict]] = {}
    for s in sessions:
        if s.get("dialogue") and "judges" in s and "claude_sonnet" in s["judges"]:
            by_model.setdefault(s["test_model"], []).append(s)

    models = sorted(by_model.keys())
    if max_models:
        models = models[:max_models]
    print(f"Stratifying across {len(models)} models, {n_per_model} sessions/model")

    picked = []
    for m in models:
        pool = by_model[m]
        # Diversify across seed_id when possible
        seen_seeds: set[str] = set()
        diverse = []
        rng.shuffle(pool)
        for s in pool:
            if s["seed_id"] not in seen_seeds:
                diverse.append(s)
                seen_seeds.add(s["seed_id"])
            if len(diverse) >= n_per_model:
                break
        # Fall back to any sessions if we ran out of unique seeds
        if len(diverse) < n_per_model:
            for s in pool:
                if s not in diverse:
                    diverse.append(s)
                if len(diverse) >= n_per_model:
                    break
        picked.extend(diverse[:n_per_model])
    return picked


def load_or_init_round3(sample_keys):
    """Resume from a prior partial run if it exists."""
    if OUT_FILE.exists():
        existing = json.loads(OUT_FILE.read_text())
        already = set(existing.get("results", {}).keys())
        print(f"  resuming: {len(already)} sessions already have round-3 scores")
        return existing, already
    return {"results": {}, "judge_models": SECOND_JUDGES}, set()


def session_key(s):
    return f"{s['test_model']}::{s['seed_id']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-model", type=int, default=3)
    ap.add_argument("--max-models", type=int, default=None,
                    help="Limit to first N models (sorted) for testing")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--judges", nargs="+", default=list(SECOND_JUDGES.keys()),
                    help="Subset of second-judge keys to run")
    args = ap.parse_args()

    if not SESSIONS_FILE.exists():
        print(f"ERROR: {SESSIONS_FILE} not found.")
        return 1

    print(f"Loading {SESSIONS_FILE}...")
    payload = json.loads(SESSIONS_FILE.read_text())
    sessions = payload["sessions"]
    print(f"  {len(sessions)} multi-turn sessions available")

    rng = random.Random(args.seed)
    picked = stratified_subsample(sessions, args.n_per_model, args.max_models, rng)
    print(f"  picked {len(picked)} sessions")

    sample_keys = [session_key(s) for s in picked]
    state, already = load_or_init_round3(sample_keys)

    judges = {k: SECOND_JUDGES[k] for k in args.judges if k in SECOND_JUDGES}
    print(f"  judges: {list(judges.keys())}")

    n_done = 0
    n_total = len(picked) * len(judges)
    t_start = time.time()

    for s in picked:
        key = session_key(s)
        if key not in state["results"]:
            state["results"][key] = {
                "test_model": s["test_model"],
                "seed_id": s["seed_id"],
                "claude_sonnet": s["judges"]["claude_sonnet"],  # canonical first judge
                "second_judges": {},
            }
        for judge_key, model_id in judges.items():
            existing = state["results"][key]["second_judges"].get(judge_key)
            if existing:
                # Skip only if previous run produced a usable score; retry
                # on parse-errors and API errors.
                ok = (
                    not existing.get("error")
                    and existing.get("scores")
                    and not existing["scores"].get("parse_error")
                    and existing["scores"].get("overall") is not None
                )
                if ok:
                    continue
            try:
                print(f"  [{n_done+1}] {key:<55} judge={judge_key:<20}", end=" ", flush=True)
                t0 = time.time()
                # Patch JUDGE_CONFIG.max_tokens for this call. judge_session
                # reads multiturn.JUDGE_CONFIG by name lookup at call time, so
                # mutating it here is sufficient.
                original_max = multiturn.JUDGE_CONFIG.get("max_tokens")
                multiturn.JUDGE_CONFIG["max_tokens"] = JUDGE_MAX_TOKENS.get(
                    judge_key, original_max
                )
                try:
                    result = judge_session(s, model_id)
                finally:
                    multiturn.JUDGE_CONFIG["max_tokens"] = original_max
                dt = time.time() - t0
                state["results"][key]["second_judges"][judge_key] = result
                overall = result.get("scores", {}).get("overall")
                if overall is None:
                    if result.get("scores", {}).get("parse_error"):
                        print(f"PARSE-ERROR ({dt:.0f}s)")
                    else:
                        print(f"NO-OVERALL ({dt:.0f}s)")
                else:
                    print(f"overall={overall:.2f} ({dt:.0f}s)")
            except Exception as e:
                print(f"FAILED: {type(e).__name__}: {e}")
                state["results"][key]["second_judges"][judge_key] = {
                    "error": f"{type(e).__name__}: {e}",
                }
            # Save after each judge call so we can resume on crash
            OUT_FILE.write_text(json.dumps(state, indent=2))
            n_done += 1

    elapsed = time.time() - t_start
    print(f"\nDone. {n_done} judge calls in {elapsed:.0f}s. Output: {OUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
