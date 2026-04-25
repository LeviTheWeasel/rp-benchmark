#!/usr/bin/env python3
"""Per-turn binary failure detection on multi-turn sessions.

For each character (assistant) turn in sessions that target a specific
failure mode, ask Sonnet 4 a binary yes/no question and parse a JSON
response. Aggregates produce per-(model, mode) failure rates with
Wilson 95% CIs — the format the experiment-design mockup uses.

Scope (deliberately focused):
  - F1 agency violation: character response writes user's actions,
    dialogue, internal states, or physical reactions.
  - F2 POV/tense violation: character response slips out of the
    established 2nd-person past tense (or whatever the seed mandates).

Why these two:
  - Both are binary by nature ("did the response do X?")
  - Both can be checked from response text + character_name + user_name
    without needing the full lorebook or system prompt.
  - F3/F12/F13 require comparing against the original system prompt,
    so we'd need to pass the full character card per call. Larger,
    slower, more expensive — defer those for a separate run.

Output: results/per_turn_failures.jsonl (append-only, resumable).
Each line: {session_id, model, seed, turn, mode, is_failure, reason, usage}.

Usage:
    python3 judge_per_turn_failures.py [--source PATH] [--judge MODEL]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from harness.api import chat_completion
from harness.config import JUDGE_CONFIG

DEFAULT_SOURCE = Path("results/multiturn_merged_all_v2.json")
DEFAULT_JUDGE = "anthropic/claude-sonnet-4"
RAW_OUT = Path("results/per_turn_failures.jsonl")

MODE_SEEDS = {
    "F1_agency": [
        "adv_agency_bait_01",
        "adv_agency_emotional_climax_09",
        "adv_agency_combat_10",
        "adv_agency_romance_11",
    ],
    "F2_pov_tense": [
        "adv_pov_second_person_12",
        "adv_pov_multi_npc_13",
        "adv_pov_tense_action_14",
    ],
}

PROMPT_F1 = """You are checking a roleplay response for a single specific failure: AGENCY VIOLATION.

Context:
- Character (the model is playing this character): {char}
- User (the player controls this character): {user}

A response contains an AGENCY VIOLATION if it writes ANY of the following for the user's character ({user}):
- Direct dialogue/speech ("Alex said...", or quotes attributed to {user})
- Physical actions ({user} reaches, walks, sits, etc.)
- Internal thoughts/feelings ({user} feels, thinks, realizes)
- Physical reactions ({user}'s heart races, breath catches, etc.)

A response is NOT a violation if it only describes:
- The character's own actions/dialogue
- The environment, atmosphere, or NPCs
- Things the character ({char}) observes about the user (e.g. "Alex looked tense" is OK if it's an external observation; "Alex felt tense" is NOT — that's writing internal state)

Response to evaluate:
\"\"\"
{response}
\"\"\"

Respond with strict JSON only:
{{"is_failure": true|false, "reason": "<one short sentence quoting the violating phrase, or 'no violation found'>"}}"""

PROMPT_F2 = """You are checking a roleplay response for a single specific failure: POV/TENSE VIOLATION.

The seed for this scene mandates a specific POV and tense. Common patterns:
- 2nd-person past tense: "You walked into the room. Your hand trembled."
- 2nd-person present tense: "You walk in. Your hand trembles."
- 3rd-person past for character, with user as 'you' — sometimes mixed.

A response is a POV/TENSE VIOLATION if it:
- Uses 1st-person ("I walk", "my hand") for the user's character ({user})
- Uses 3rd-person ("Alex walked") for the user's character when 2nd-person is mandated
- Switches tense mid-response (past → present → past)
- For 2nd-person mandates: refers to {user} by name in subject position (should be "you")

A response is NOT a violation if:
- It uses 3rd-person/named-reference for the CHARACTER ({char}) — that's fine, only {user} needs to be 'you'
- It quotes characters speaking in 1st-person — that's their dialogue, not the narration
- It uses past tense throughout consistently (or whatever tense was established)

Response to evaluate:
\"\"\"
{response}
\"\"\"

Respond with strict JSON only:
{{"is_failure": true|false, "reason": "<one short sentence quoting the slip, or 'no violation found'>"}}"""

PROMPTS = {"F1_agency": PROMPT_F1, "F2_pov_tense": PROMPT_F2}


def load_done(path: Path) -> set:
    """Returns set of (session_id, turn, mode) tuples already processed."""
    done = set()
    if not path.exists():
        return done
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
                done.add((r["session_id"], r["turn"], r["mode"]))
            except Exception:
                pass
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--judge", default=DEFAULT_JUDGE)
    ap.add_argument("--limit", type=int, default=None, help="Max checks per (model, mode) for testing")
    args = ap.parse_args()

    data = json.load(open(args.source))
    done = load_done(RAW_OUT)
    print(f"Already done: {len(done)} checks")

    # Build work list
    work = []
    for s in data["sessions"]:
        if "judges" not in s or "dialogue" not in s:
            continue
        seed = s["seed_id"]
        sid = f'{s["test_model"]}::{seed}'
        for mode, sids in MODE_SEEDS.items():
            if seed not in sids:
                continue
            for msg in s["dialogue"]:
                if msg.get("role") not in ("character", "assistant"):
                    continue
                turn = msg.get("turn")
                if turn == 0:
                    # Skip the seed-provided opening message — model didn't generate it.
                    continue
                content = msg.get("content")
                if not content or len(content) < 50:
                    continue
                key = (sid, turn, mode)
                if key in done:
                    continue
                work.append({
                    "session_id": sid,
                    "model": s["test_model"],
                    "seed": seed,
                    "turn": turn,
                    "mode": mode,
                    "char": s.get("character_name", "Character"),
                    "user": s.get("user_name", "User"),
                    "content": content,
                })

    if args.limit:
        # Cap per (model, mode) for smoke testing
        from collections import defaultdict
        seen_keys = defaultdict(int)
        capped = []
        for w in work:
            k = (w["model"], w["mode"])
            if seen_keys[k] >= args.limit:
                continue
            seen_keys[k] += 1
            capped.append(w)
        work = capped

    print(f"Judge: {args.judge}")
    print(f"Source: {args.source}")
    print(f"To check: {len(work)} (model × turn × mode triples)")
    print()

    if not work:
        print("Nothing to do.")
        return

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    errors = 0
    t0 = time.time()

    for i, w in enumerate(work):
        prompt = PROMPTS[w["mode"]].format(
            char=w["char"], user=w["user"], response=w["content"]
        )
        try:
            resp = chat_completion(
                model=args.judge,
                system_prompt="You are a strict, evidence-based binary classifier. Respond ONLY with the requested JSON.",
                user_content=prompt,
                config={"temperature": 0.0, "max_tokens": 200},
            )
        except Exception as e:
            errors += 1
            print(f"[{i+1}/{len(work)}] ERR {w['model']}/{w['seed']} t{w['turn']} {w['mode']}: {e}")
            if errors > 20:
                print("Too many errors. Stopping.")
                break
            continue

        # Parse
        content = resp.get("content", "")
        parsed = None
        for cand in (content, content.strip("` \n").replace("```json", "").replace("```", "")):
            try:
                parsed = json.loads(cand.strip())
                break
            except Exception:
                continue
        if not parsed or "is_failure" not in parsed:
            errors += 1
            continue

        rec = {
            "session_id": w["session_id"],
            "model": w["model"],
            "seed": w["seed"],
            "turn": w["turn"],
            "mode": w["mode"],
            "is_failure": bool(parsed["is_failure"]),
            "reason": parsed.get("reason", ""),
            "usage": resp.get("usage"),
            "judge": args.judge,
        }
        with open(RAW_OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")

        if (i + 1) % 25 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(work) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{len(work)}] {rate:.1f}/s  eta {eta/60:.0f}min  errors {errors}")

    print(f"\nDone. {errors} errors.")


if __name__ == "__main__":
    main()
