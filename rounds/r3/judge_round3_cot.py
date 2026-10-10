#!/usr/bin/env python3
"""CoT comparison: re-judge the same Round 3 sub-sample with a reasoning-first prompt.

Our existing SESSION_JUDGE_SYSTEM puts {"score": 0.0, "rationale": ""} per
dimension. Score precedes rationale in the schema, so the model commits
to a number autoregressively before justifying it. The CoT-judging
literature (Wei et al. 2022, Saha et al. 2024, Zheng et al.'s own MT-Bench
template) shows reasoning-first scaffolding produces more consistent and
higher-agreement scores.

This script runs an A/B comparison on the same 60 sessions used in
Round 3, with the same three judges (Sonnet 4, Gemini 3.1 Pro, GPT-5.5),
using a CoT-first variant of the prompt:

  1. A top-level `reasoning_summary` field comes FIRST in the JSON (free-
     form analysis of the session as a whole, written before any scoring).
  2. Per-dimension keys are reordered: {"rationale": "", "score": 0.0}.

Output saved alongside Round 3 data:
  - results/round3_cot_judge.json  (CoT variant; same schema as
    round3_multi_judge.json plus reasoning_summary at top level)

Then rounds/r3/analyze_round3_cot_compare.py contrasts the two passes:
  - Per-judge per-session score deltas (no-CoT vs CoT)
  - Inter-judge weighted Cohen's κ under each variant
  - Per-judge ρ vs multi-turn arena ELO under each variant

Cost estimate: 60 sessions × 3 judges = 180 calls. CoT prompts emit more
output tokens; estimate ~$10-15 total at current OpenRouter rates.

Usage:
    python3 rounds/r3/judge_round3_cot.py --max-models 5 --n-per-model 1   # smoke
    python3 rounds/r3/judge_round3_cot.py                                    # full
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness import multiturn
from harness.api import chat_completion


SESSIONS_FILE = Path("results/multiturn_merged_all_v2.json")
ROUND3_FILE   = Path("results/round3_multi_judge.json")
OUT_FILE      = Path("results/round3_cot_judge.json")

# Same 3 judges as Round 3 — including Sonnet 4 so we can A/B every judge.
JUDGES = {
    "claude_sonnet":  "anthropic/claude-4-sonnet-20250522",
    "gemini_3_1_pro": "google/gemini-3.1-pro-preview",
    "gpt_latest":     "~openai/gpt-latest",
}

# Same per-judge max_tokens as Round 3 — reasoning models need headroom,
# CoT prompting will burn ~50% more output tokens regardless.
JUDGE_MAX_TOKENS = {
    "claude_sonnet":  8000,
    "gemini_3_1_pro": 16000,
    "gpt_latest":     8000,
}

# CoT-first prompt. Two structural changes from SESSION_JUDGE_SYSTEM:
#   1. Top-level "reasoning_summary" written BEFORE any scored dimension.
#   2. Per-dimension keys reordered: rationale, then score.
# Otherwise identical to the original prompt — same dimensions, same
# scale, same calibration guidance.
SESSION_JUDGE_SYSTEM_COT = """You are evaluating a complete multi-turn roleplay session. You will score the AI CHARACTER's performance across the full conversation, not just individual responses.

## What You're Evaluating
The AI played %(character_name)s. A simulated user played %(user_name)s. The session ran for %(num_turns)s turns.

## Output Format — IMPORTANT

You will respond with ONLY valid JSON. The JSON has the following structure, and you must produce the keys IN ORDER:

1. First: a `reasoning_summary` field where you analyze the session as a whole BEFORE scoring any individual dimension. Walk through what worked, what didn't, where the character drifted (if at all), how the narrative moved, what stood out. 4-8 sentences. This analysis must come before any numeric score.

2. Then: each scored dimension below. For each dimension, you must produce the `rationale` (2-4 sentences citing specific session content) BEFORE the numeric `score`. The model autoregressively generates these in order, so reasoning precedes the score for each dimension.

3. Finally: aggregate fields (`quality_trajectory`, `overall`, `overall_notes`).

## Session-Level Dimensions (score 1-5)

**S.1 Consistency Over Time** — Does the character voice, personality, and behavior remain consistent from turn 1 to the final turn? Or does the character drift, flatten, or become generic over time?

**S.2 Degradation Resistance** — Does the writing quality hold up? Compare the first 5 turns to the last 5. Look for: increasing verbosity, repetitive descriptions, lost details, flattened personality.

**S.3 Narrative Momentum** — Does the conversation go somewhere? Is there a sense of progression — emotional, narrative, or relational? Or does it loop, stagnate, or feel like the same beat repeated?

**S.4 Adaptive Responsiveness** — Does the AI adapt to what the user does? When the user redirects, does the AI follow? When the user escalates, does the AI match? When the user does something unexpected, does the AI handle it gracefully?

**S.5 Agency Respect (Session)** — Over the full session, how often does the AI write the user's actions, make decisions for them, or railroad the story? Count instances.

**S.6 Temporal Reasoning** — Does time pass consistently across the session? Track clock consistency, physical time progression (fatigue, hunger, healing), environmental time (light shifts, weather), event pacing, and contradictions.

## Standard Dimensions
Also score these from the standard rubric (averaged across the full session):
- 2.1 Anti-Purple Prose
- 2.2 Anti-Repetition
- 2.5 Show Don't Tell
- 2.6 Subtext
- 2.7 Pacing

## JSON Schema
```json
{
  "reasoning_summary": "Free-form 4-8 sentence analysis of the session as a whole. Cite specific moments. Discuss the arc, the character's consistency, where the model excelled or struggled. This field MUST come first and MUST be substantive — no scoring before reasoning.",
  "session_dimensions": {
    "S.1_consistency_over_time":   {"rationale": "", "score": 0.0},
    "S.2_degradation_resistance":  {"rationale": "", "score": 0.0},
    "S.3_narrative_momentum":      {"rationale": "", "score": 0.0},
    "S.4_adaptive_responsiveness": {"rationale": "", "score": 0.0},
    "S.5_agency_respect_session":  {"rationale": "", "violation_count": 0, "score": 0.0},
    "S.6_temporal_reasoning":      {"rationale": "", "contradictions": [], "score": 0.0}
  },
  "standard_dimensions": {
    "2.1_anti_purple_prose": {"rationale": "", "score": 0.0},
    "2.2_anti_repetition":   {"rationale": "", "score": 0.0},
    "2.5_show_dont_tell":    {"rationale": "", "score": 0.0},
    "2.6_subtext":           {"rationale": "", "score": 0.0},
    "2.7_pacing":            {"rationale": "", "score": 0.0}
  },
  "quality_trajectory": {
    "early_quality": 0.0,
    "mid_quality":   0.0,
    "late_quality":  0.0,
    "degradation_detected": false
  },
  "overall": 0.0,
  "overall_notes": ""
}
```

Calibration: 3 = adequate, 4 = strong, 5 = exceptional (reserve this). Most decent models land 2.5-4.0."""


def judge_session_cot(session: dict, judge_model_id: str, max_tokens: int) -> dict:
    """Re-implementation of harness.multiturn.judge_session that uses the
    CoT-first prompt and a per-call max_tokens override."""
    character_name = session["character_name"]
    user_name = session["user_name"]
    num_turns = session["num_turns"]

    dialogue_text = ""
    for msg in session["dialogue"]:
        dialogue_text += "\n**%s** (turn %d):\n%s\n" % (
            msg["name"], msg["turn"], msg["content"]
        )

    judge_system = SESSION_JUDGE_SYSTEM_COT % {
        "character_name": character_name,
        "user_name": user_name,
        "num_turns": num_turns,
    }
    judge_input = (
        "<session>\n%s\n</session>\n\n"
        "Score the AI CHARACTER's (%s) performance across this full %d-turn session. "
        "Begin with reasoning_summary, then per-dimension rationale-then-score, "
        "then aggregate fields. Reasoning MUST precede any numeric score."
    ) % (dialogue_text, character_name, num_turns)

    config = dict(multiturn.JUDGE_CONFIG)
    config["max_tokens"] = max_tokens

    result = chat_completion(judge_model_id, judge_system, judge_input, config)
    content = result["content"].strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(l for l in lines if not l.strip().startswith("```"))

    try:
        scores = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                scores = json.loads(content[start:end])
            except json.JSONDecodeError:
                scores = {"parse_error": True, "raw_content": result["content"]}
        else:
            scores = {"parse_error": True, "raw_content": result["content"]}

    return {
        "scores": scores,
        "usage": result.get("usage", {}),
        "model": result.get("model"),
    }


def session_key(s):
    return f"{s['test_model']}::{s['seed_id']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-models", type=int, default=None,
                    help="For smoke testing — limit to first N models")
    ap.add_argument("--n-per-model", type=int, default=None,
                    help="For smoke testing — limit sessions/model")
    ap.add_argument("--judges", nargs="+", default=list(JUDGES.keys()))
    args = ap.parse_args()

    if not ROUND3_FILE.exists():
        print(f"ERROR: {ROUND3_FILE} not found. Run rounds/r3/judge_round3_multi.py first")
        return 1
    if not SESSIONS_FILE.exists():
        print(f"ERROR: {SESSIONS_FILE} not found.")
        return 1

    # Load the same Round 3 sub-sample
    r3 = json.loads(ROUND3_FILE.read_text())
    sessions_full = json.loads(SESSIONS_FILE.read_text())["sessions"]
    by_key = {session_key(s): s for s in sessions_full}

    target_keys = list(r3["results"].keys())

    # Optional smoke-test filtering
    if args.max_models or args.n_per_model:
        per_model: dict[str, list[str]] = {}
        for k in target_keys:
            test_model = k.split("::")[0]
            per_model.setdefault(test_model, []).append(k)
        models = list(per_model.keys())
        if args.max_models:
            models = models[: args.max_models]
        target_keys = []
        for m in models:
            keys = per_model[m]
            if args.n_per_model:
                keys = keys[: args.n_per_model]
            target_keys.extend(keys)

    print(f"Re-judging {len(target_keys)} sessions with CoT prompt")
    judges = {k: JUDGES[k] for k in args.judges if k in JUDGES}
    print(f"  judges: {list(judges.keys())}")
    print(f"  cost rough estimate: {len(target_keys) * len(judges)} calls × ~$0.06 ≈ ${len(target_keys) * len(judges) * 0.06:.2f}")

    # Load or init output state
    if OUT_FILE.exists():
        state = json.loads(OUT_FILE.read_text())
        already = set(state.get("results", {}).keys())
        print(f"  resuming: {len(already)} sessions already have CoT scores")
    else:
        state = {
            "prompt_variant": "cot_first",
            "judges": judges,
            "results": {},
        }

    n_done = 0
    t_start = time.time()
    for key in target_keys:
        if key not in by_key:
            print(f"  WARN: session {key} not in {SESSIONS_FILE.name}, skipping")
            continue
        s = by_key[key]
        if key not in state["results"]:
            state["results"][key] = {
                "test_model": s["test_model"],
                "seed_id": s["seed_id"],
                "judges_cot": {},
            }
        for judge_key, model_id in judges.items():
            existing = state["results"][key]["judges_cot"].get(judge_key)
            if existing:
                ok = (
                    not existing.get("error")
                    and existing.get("scores")
                    and not existing["scores"].get("parse_error")
                    and existing["scores"].get("overall") is not None
                )
                if ok:
                    continue
            try:
                print(f"  [{n_done+1}] {key:<55} judge={judge_key:<18}", end=" ", flush=True)
                t0 = time.time()
                max_tokens = JUDGE_MAX_TOKENS.get(judge_key, 8000)
                result = judge_session_cot(s, model_id, max_tokens)
                dt = time.time() - t0
                state["results"][key]["judges_cot"][judge_key] = result
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
                state["results"][key]["judges_cot"][judge_key] = {
                    "error": f"{type(e).__name__}: {e}",
                }
            OUT_FILE.write_text(json.dumps(state, indent=2))
            n_done += 1

    elapsed = time.time() - t_start
    print(f"\nDone. {n_done} judge calls in {elapsed:.0f}s. Output: {OUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
