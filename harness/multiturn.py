"""Multi-turn session runner for RP-Bench.

Runs full conversations: a test model plays the character while a
'user simulator' LLM plays the user role. The full session is then
judged for quality, consistency, and degradation over time.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .api import chat_completion
from .config import (
    JUDGE_MODELS,
    GENERATION_CONFIG,
    JUDGE_CONFIG,
    RESULTS_DIR,
    PROJECT_ROOT,
)
from .runner import load_judge_prompt, load_lorebook, build_lorebook_context

# User simulator prompt — plays the user character naturally
USER_SIM_SYSTEM = """You are simulating a human roleplayer in a text-based RP session. You are playing the character described below.

## Your Character
Name: {user_name}
{user_setting}

## Rules
- Write SHORT responses (1-4 sentences). Real users don't write novels.
- Stay in character. React naturally to what the AI character does.
- Mix action (*action*) and dialogue ("speech") like a real RPer.
- Occasionally do unexpected things — redirect the scene, introduce a complication, ask a question, express an emotion the AI didn't expect.
- Do NOT be a passive audience. Push the story. Make choices. Have opinions.
- Every 5-7 turns, try to advance the scene — suggest going somewhere, bringing up a new topic, or escalating/de-escalating the emotional stakes.
- If the AI violates your agency (writes your actions for you), correct it briefly in parentheses: (OOC: don't write my actions)
- Write like a real person, not a writing exercise. Typos and casual grammar are fine.
- NEVER break character to compliment the AI's writing or comment on the quality of the RP."""

# Session judge prompt — evaluates the full conversation
SESSION_JUDGE_SYSTEM = """You are evaluating a complete multi-turn roleplay session. You will score the AI CHARACTER's performance across the full conversation, not just individual responses.

## What You're Evaluating
The AI played %(character_name)s. A simulated user played %(user_name)s. The session ran for %(num_turns)s turns.

## Session-Level Dimensions (score 1-5)

In addition to the standard per-response rubric dimensions, score these SESSION-LEVEL qualities:

**S.1 Consistency Over Time** — Does the character voice, personality, and behavior remain consistent from turn 1 to the final turn? Or does the character drift, flatten, or become generic over time?

**S.2 Degradation Resistance** — Does the writing quality hold up? Compare the first 5 turns to the last 5. Look for: increasing verbosity, repetitive descriptions, lost details, flattened personality.

**S.3 Narrative Momentum** — Does the conversation go somewhere? Is there a sense of progression — emotional, narrative, or relational? Or does it loop, stagnate, or feel like the same beat repeated?

**S.4 Adaptive Responsiveness** — Does the AI adapt to what the user does? When the user redirects, does the AI follow? When the user escalates, does the AI match? When the user does something unexpected, does the AI handle it gracefully?

**S.5 Agency Respect (Session)** — Over the full session, how often does the AI write the user's actions, make decisions for them, or railroad the story? Count instances.

**S.6 Temporal Reasoning** — Does time pass consistently across the session? Track these:
- Clock consistency: if it's morning at turn 1, is it still morning at turn 20? Does the time of day advance naturally?
- Physical time: do characters show fatigue, hunger, healing progression? Do drinks go cold? Do candles burn down?
- Environmental time: does light shift, do shadows move, does weather change?
- Event pacing: does the amount of in-world time match what actually happened? (A 5-minute conversation shouldn't span hours. A journey shouldn't be instant.)
- Contradictions: any "later that evening" when it's already night? Any healed injuries that were fresh 3 turns ago?

## Standard Dimensions
Also score these from the standard rubric (averaged across the full session):
- 2.1 Anti-Purple Prose
- 2.2 Anti-Repetition
- 2.5 Show Don't Tell
- 2.6 Subtext
- 2.7 Pacing

## Output Format
Respond with ONLY valid JSON:
```json
{
  "session_dimensions": {
    "S.1_consistency_over_time": {"score": 0.0, "rationale": ""},
    "S.2_degradation_resistance": {"score": 0.0, "rationale": ""},
    "S.3_narrative_momentum": {"score": 0.0, "rationale": ""},
    "S.4_adaptive_responsiveness": {"score": 0.0, "rationale": ""},
    "S.5_agency_respect_session": {"score": 0.0, "rationale": "", "violation_count": 0},
    "S.6_temporal_reasoning": {"score": 0.0, "rationale": "", "contradictions": []}
  },
  "standard_dimensions": {
    "2.1_anti_purple_prose": {"score": 0.0, "rationale": ""},
    "2.2_anti_repetition": {"score": 0.0, "rationale": ""},
    "2.5_show_dont_tell": {"score": 0.0, "rationale": ""},
    "2.6_subtext": {"score": 0.0, "rationale": ""},
    "2.7_pacing": {"score": 0.0, "rationale": ""}
  },
  "quality_trajectory": {
    "early_quality": 0.0,
    "mid_quality": 0.0,
    "late_quality": 0.0,
    "degradation_detected": false
  },
  "overall": 0.0,
  "overall_notes": ""
}
```

Calibration: 3 = adequate, 4 = strong, 5 = exceptional (reserve this). Most decent models land 2.5-4.0."""


def load_seeds() -> list[dict]:
    """Load synthetic seed scenarios."""
    seeds_path = PROJECT_ROOT / "hf_dataset" / "seeds" / "seeds.json"
    with open(seeds_path) as f:
        return json.load(f)


def run_session(
    seed: dict,
    test_model_id: str,
    user_sim_model_id: str,
    num_turns: int = 20,
) -> dict:
    """Run a full multi-turn RP session.

    Args:
        seed: Scenario seed with character/user settings and opening.
        test_model_id: The model being benchmarked (plays the character).
        user_sim_model_id: Model that simulates the user.
        num_turns: Number of back-and-forth exchanges.

    Returns:
        Session dict with full dialogue and metadata.
    """
    character_name = seed["character_name"]
    user_name = seed["user_name"]

    # Build character system prompt
    char_system = (
        "You are roleplaying as %s. Stay in character at all times. "
        "Write in third-person past tense. Do NOT write actions or "
        "dialogue for %s — they are controlled by the user.\n\n"
        "## Your Character\n%s"
    ) % (character_name, user_name, seed["character_setting"])

    # Build user simulator system prompt
    user_system = USER_SIM_SYSTEM.format(
        user_name=user_name,
        user_setting=seed.get("user_setting", ""),
    )

    # Initialize conversation with seed content
    dialogue = []

    # Opening message (from the character/narrator)
    opening = seed["opening_message"]
    dialogue.append({
        "turn": 0,
        "role": "character",
        "name": character_name,
        "content": opening,
        "tokens": None,
    })

    # First user input (from the seed)
    first_input = seed["initial_user_input"]
    dialogue.append({
        "turn": 1,
        "role": "user",
        "name": user_name,
        "content": first_input,
        "tokens": None,
    })

    print("    Turn 0-1: seed opening + initial input")

    # Build challenge turn lookup: {actual_turn_number: challenge_data}
    challenge_map = {}
    for ct in seed.get("challenge_turns", []):
        challenge_map[ct["turn"]] = ct

    # Run the conversation
    for turn in range(2, num_turns * 2):
        actual_turn = (turn // 2) + 1
        # Build conversation history for the model
        history = _format_history(dialogue)

        if turn % 2 == 0:
            # Character's turn (the model being tested)
            prompt = history + "\n\n[Continue as %s. Write your next response.]" % character_name
            result = chat_completion(
                test_model_id, char_system, prompt, GENERATION_CONFIG,
            )
            role = "character"
            name = character_name
            content = result["content"]
            usage = result.get("usage", {})
        elif actual_turn in challenge_map:
            # Challenge turn — use scripted input instead of user sim
            challenge = challenge_map[actual_turn]
            content = challenge["user_input"]
            usage = {}
            role = "user"
            name = user_name
            print("    Turn %d/%d: CHALLENGE [%s]" % (actual_turn, num_turns, ", ".join(challenge["tests"])))
        else:
            # User's turn (simulated)
            prompt = history + "\n\n[Continue as %s. Write a short, natural response.]" % user_name
            result = chat_completion(
                user_sim_model_id, user_system, prompt, GENERATION_CONFIG,
            )
            role = "user"
            name = user_name
            content = result["content"]
            usage = result.get("usage", {})

        dialogue.append({
            "turn": turn,
            "role": role,
            "name": name,
            "content": content,
            "tokens": usage.get("completion_tokens"),
            "is_challenge": actual_turn in challenge_map and role == "user",
        })

        if turn % 2 == 0 and content:
            # Show progress on character turns
            preview = content[:80].replace("\n", " ")
            print("    Turn %d/%d: %s..." % (actual_turn, num_turns, preview))

    return {
        "seed_id": seed["id"],
        "character_name": character_name,
        "user_name": user_name,
        "num_turns": num_turns,
        "dialogue": dialogue,
        "total_messages": len(dialogue),
    }


def judge_session(
    session: dict,
    judge_model_id: str,
) -> dict:
    """Judge a complete multi-turn session."""
    character_name = session["character_name"]
    user_name = session["user_name"]
    num_turns = session["num_turns"]

    # Format the full dialogue for the judge
    dialogue_text = ""
    for msg in session["dialogue"]:
        dialogue_text += "\n**%s** (turn %d):\n%s\n" % (
            msg["name"], msg["turn"], msg["content"]
        )

    # Build judge system prompt
    judge_system = SESSION_JUDGE_SYSTEM % {
        "character_name": character_name,
        "user_name": user_name,
        "num_turns": num_turns,
    }

    judge_input = (
        "<session>\n%s\n</session>\n\n"
        "Score the AI CHARACTER's (%s) performance across this full %d-turn session."
    ) % (dialogue_text, character_name, num_turns)

    result = chat_completion(
        judge_model_id, judge_system, judge_input, JUDGE_CONFIG,
    )

    # Parse JSON
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


def _format_history(dialogue: list[dict]) -> str:
    """Format dialogue history for model input."""
    lines = []
    for msg in dialogue:
        lines.append("%s:\n%s" % (msg["name"], msg["content"]))
    return "\n\n".join(lines)


def run_multiturn_benchmark(
    test_models: dict[str, str],
    judge_models: dict[str, str] | None = None,
    user_sim_model: str = "google/gemini-2.5-flash",
    seed_ids: list[str] | None = None,
    num_turns: int = 20,
    max_seeds: int | None = None,
) -> dict:
    """Run multi-turn benchmark across models and seeds.

    Args:
        test_models: {name: model_id} for models to benchmark.
        judge_models: {name: model_id} for judges. Defaults to config.
        user_sim_model: Model ID for the user simulator.
        seed_ids: Specific seed IDs to run. None = all.
        num_turns: Turns per session.
        max_seeds: Limit number of seeds.
    """
    if judge_models is None:
        judge_models = JUDGE_MODELS

    seeds = load_seeds()
    if seed_ids:
        seeds = [s for s in seeds if s["id"] in seed_ids]
    if max_seeds:
        seeds = seeds[:max_seeds]

    total_sessions = len(seeds) * len(test_models)
    total_judge_calls = total_sessions * len(judge_models)
    # Each session: num_turns*2 generation calls + judge calls
    total_gen_calls = total_sessions * (num_turns * 2 - 2)  # minus seed messages

    print("RP-Bench Multi-Turn Run")
    print("  Seeds: %d" % len(seeds))
    print("  Test models: %s" % list(test_models.keys()))
    print("  User simulator: %s" % user_sim_model)
    print("  Turns per session: %d" % num_turns)
    print("  Total sessions: %d" % total_sessions)
    print("  Est. generation calls: ~%d" % total_gen_calls)
    print("  Est. judge calls: %d" % total_judge_calls)
    print()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    results = {
        "run_id": "mt_%s" % run_id,
        "type": "multiturn",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "test_models": test_models,
            "judge_models": judge_models,
            "user_sim_model": user_sim_model,
            "num_turns": num_turns,
            "seed_count": len(seeds),
        },
        "sessions": [],
    }

    step = 0
    for seed in seeds:
        for model_key, model_id in test_models.items():
            step += 1
            print("[%d/%d] %s x %s (%d turns)" % (
                step, total_sessions, seed["id"], model_key, num_turns
            ))

            try:
                # Run the session
                session = run_session(
                    seed, model_id, user_sim_model, num_turns,
                )
                session["test_model"] = model_key
                session["test_model_id"] = model_id

                # Judge the session
                session["judges"] = {}
                for judge_key, judge_id in judge_models.items():
                    print("    Judging with %s..." % judge_key)
                    judge_result = judge_session(session, judge_id)
                    session["judges"][judge_key] = judge_result

                    if judge_result["scores"].get("parse_error"):
                        print("      WARNING: Failed to parse judge JSON")

                results["sessions"].append(session)

            except Exception as e:
                print("    ERROR: %s" % e)
                results["sessions"].append({
                    "seed_id": seed["id"],
                    "test_model": model_key,
                    "error": str(e),
                })

    # Save
    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / ("multiturn_%s.json" % run_id)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\nResults saved to %s" % out_path)
    return results


def print_multiturn_results(results: dict):
    """Print multi-turn session results."""
    sessions = [s for s in results["sessions"] if "error" not in s]

    if not sessions:
        print("No successful sessions.")
        return

    print()
    print("=" * 78)
    print("  RP-BENCH MULTI-TURN RESULTS")
    print("  Run: %s | Sessions: %d | Turns: %s" % (
        results["run_id"], len(sessions), results["config"]["num_turns"],
    ))
    print("=" * 78)

    # Aggregate per model
    model_scores = {}
    for session in sessions:
        model = session["test_model"]
        if model not in model_scores:
            model_scores[model] = {
                "session_dims": {},
                "standard_dims": {},
                "overalls": [],
                "degradation_count": 0,
                "session_count": 0,
            }

        ms = model_scores[model]
        ms["session_count"] += 1

        for judge_key, judge_data in session.get("judges", {}).items():
            scores = judge_data.get("scores", {})
            if scores.get("parse_error"):
                continue

            # Session dimensions
            for dim, data in scores.get("session_dimensions", {}).items():
                if isinstance(data, dict) and "score" in data:
                    ms["session_dims"].setdefault(dim, []).append(data["score"])

            # Standard dimensions
            for dim, data in scores.get("standard_dimensions", {}).items():
                if isinstance(data, dict) and "score" in data:
                    ms["standard_dims"].setdefault(dim, []).append(data["score"])

            # Overall
            if "overall" in scores:
                ms["overalls"].append(scores["overall"])

            # Degradation
            traj = scores.get("quality_trajectory", {})
            if traj.get("degradation_detected"):
                ms["degradation_count"] += 1

    # Print leaderboard
    ranked = sorted(
        model_scores.items(),
        key=lambda x: (sum(x[1]["overalls"]) / len(x[1]["overalls"])) if x[1]["overalls"] else 0,
        reverse=True,
    )

    print()
    print("  %-5s %-24s %-9s %-12s %-12s %-10s" % (
        "Rank", "Model", "Overall", "Consistency", "Degradation", "Momentum"
    ))
    print("  " + "-" * 74)

    for i, (model, ms) in enumerate(ranked):
        overall = "%.2f" % (sum(ms["overalls"]) / len(ms["overalls"])) if ms["overalls"] else "-"

        def dim_avg(dims, key):
            vals = dims.get(key, [])
            return "%.2f" % (sum(vals) / len(vals)) if vals else "-"

        consistency = dim_avg(ms["session_dims"], "S.1_consistency_over_time")
        degradation = "%d/%d" % (ms["degradation_count"], ms["session_count"])
        momentum = dim_avg(ms["session_dims"], "S.3_narrative_momentum")

        print("  #%-4d %-24s %-9s %-12s %-12s %-10s" % (
            i + 1, model, overall, consistency, degradation, momentum
        ))

    # Per-session details
    print()
    print("  SESSION DETAILS")
    print("  " + "-" * 74)
    for session in sessions:
        model = session["test_model"]
        seed = session["seed_id"]
        turns = session["num_turns"]

        for judge_key, judge_data in session.get("judges", {}).items():
            scores = judge_data.get("scores", {})
            if scores.get("parse_error"):
                print("  %s x %s [%s]: PARSE ERROR" % (seed, model, judge_key))
                continue

            overall = scores.get("overall", "?")
            notes = scores.get("overall_notes", "")[:100]
            traj = scores.get("quality_trajectory", {})
            early = traj.get("early_quality", "?")
            late = traj.get("late_quality", "?")
            degraded = traj.get("degradation_detected", False)

            print("  %s x %s [%s]" % (seed, model, judge_key))
            print("    Overall: %s | Early: %s -> Late: %s %s" % (
                overall, early, late, "(DEGRADED)" if degraded else ""
            ))
            print("    %s" % notes)
