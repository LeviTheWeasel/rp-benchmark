#!/usr/bin/env python3
"""LLM-judged pairwise comparisons on the adversarial multi-turn run.

Score-delta ELO uses the judge's Likert overall score per session and
infers winners from the delta. That's cheap but leaks information at the
0.1 rounding boundary (16% ties after dimension tiebreak).

This script runs the comparative judge directly on the full session
transcripts: for each seed, compare every pair of models head-to-head
and record the winner. A/B position is randomized per pair to reduce
position bias.

Cost: ~168 pairs × ~11k input tokens ≈ 1.8M tokens. About $5 on Sonnet 4.

Usage:
    python3 judge_adversarial_pairwise.py [--dry-run] [--judge MODEL]

Outputs to results/adversarial_pairwise_raw.jsonl (append-only), one
line per completed comparison. Re-running skips already-judged pairs.
"""
import argparse
import json
import random
import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from harness.api import chat_completion
from harness.config import JUDGE_CONFIG

JUDGE_PROMPT_FILE = Path("prompts/judge_comparative.md")
RAW_OUT = Path("results/adversarial_pairwise_raw.jsonl")
DEFAULT_SOURCE = Path("results/multiturn_20260414_042100.json")
DEFAULT_JUDGE = "anthropic/claude-sonnet-4"


def format_transcript(session):
    lines = []
    for msg in session["dialogue"]:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f'[USER]\n{content}')
        else:
            lines.append(f'[CHARACTER]\n{content}')
    return "\n\n".join(lines)


def build_user_content(session_a, session_b, seed_id, character_name):
    ta = format_transcript(session_a)
    tb = format_transcript(session_b)
    return (
        f"Seed: {seed_id}\n"
        f"Character: {character_name}\n\n"
        f"You are comparing two full multi-turn roleplay sessions (same seed, same opening, same user simulator — only the model playing the character differs). "
        f"Each is {session_a['num_turns']} turns long. "
        f"Apply the comparative rubric to the session as a whole, not to any single turn. "
        f"Focus on what the session does well across its arc.\n\n"
        f"=== RESPONSE A ===\n\n{ta}\n\n"
        f"=== RESPONSE B ===\n\n{tb}\n"
    )


def load_existing(path):
    done = set()
    if not path.exists():
        return done
    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
                done.add((rec["seed_id"], rec["model_a"], rec["model_b"]))
                # Also mark reversed ordering as done
                done.add((rec["seed_id"], rec["model_b"], rec["model_a"]))
            except Exception:
                pass
    return done


def canonical_pair_key(seed, m1, m2):
    a, b = sorted([m1, m2])
    return (seed, a, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--judge", default=DEFAULT_JUDGE)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="Max pairs to judge (for testing)")
    args = ap.parse_args()

    data = json.load(open(args.source))
    sessions_by_key = {}
    for s in data["sessions"]:
        if "judges" not in s:
            continue
        sessions_by_key[(s["seed_id"], s["test_model"])] = s

    # Build work list: (seed, model_a, model_b) canonical (sorted) keys
    seeds = sorted({seed for seed, _ in sessions_by_key})
    models_per_seed = {seed: sorted({m for s, m in sessions_by_key if s == seed}) for seed in seeds}

    work = []
    for seed in seeds:
        for m1, m2 in combinations(models_per_seed[seed], 2):
            work.append(canonical_pair_key(seed, m1, m2))

    # Skip already-judged (canonical key)
    done_canonical = set()
    if RAW_OUT.exists():
        with open(RAW_OUT) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    done_canonical.add(canonical_pair_key(rec["seed_id"], rec["model_a"], rec["model_b"]))
                except Exception:
                    pass
    work = [w for w in work if w not in done_canonical]

    if args.limit:
        work = work[: args.limit]

    print(f"Judge: {args.judge}")
    print(f"Source: {args.source}")
    print(f"Total canonical pairs: {len(seeds) * 21}")
    print(f"Already done: {len(done_canonical)}")
    print(f"To judge now: {len(work)}")

    if args.dry_run:
        for w in work[:5]:
            print(" ", w)
        if len(work) > 5:
            print(f"  ... and {len(work)-5} more")
        return

    judge_prompt = JUDGE_PROMPT_FILE.read_text()
    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(42)
    errors = 0
    t0 = time.time()

    for i, (seed, m1, m2) in enumerate(work):
        # Randomize A/B order
        if rng.random() < 0.5:
            ma, mb = m1, m2
        else:
            ma, mb = m2, m1
        sa = sessions_by_key[(seed, ma)]
        sb = sessions_by_key[(seed, mb)]
        user_content = build_user_content(sa, sb, seed, sa.get("character_name", "?"))

        try:
            resp = chat_completion(
                model=args.judge,
                system_prompt=judge_prompt,
                user_content=user_content,
                config=JUDGE_CONFIG,
            )
        except Exception as e:
            errors += 1
            print(f"[{i+1}/{len(work)}] ERR {seed} {m1}v{m2}: {e}")
            if errors > 10:
                print("Too many errors, stopping.")
                break
            continue

        content = resp.get("content", "")
        # Strip code fences if present
        parsed = None
        for candidate in (content, content.strip("` \n"), content.split("```")[1] if "```" in content else None):
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate.replace("```json", "").replace("```", "").strip())
                break
            except Exception:
                continue

        if not parsed or "winner" not in parsed:
            errors += 1
            print(f"[{i+1}/{len(work)}] PARSE-ERR {seed} {m1}v{m2}")
            continue

        winner_ab = parsed.get("winner")
        winner_model = ma if winner_ab == "A" else mb if winner_ab == "B" else None

        rec = {
            "seed_id": seed,
            "model_a": ma,
            "model_b": mb,
            "winner_ab": winner_ab,
            "winner_model": winner_model,
            "confidence": parsed.get("confidence"),
            "summary": parsed.get("summary"),
            "key_differences": parsed.get("key_differences", []),
            "usage": resp.get("usage"),
            "judge": args.judge,
        }
        with open(RAW_OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")

        elapsed = time.time() - t0
        rate = (i + 1) / elapsed
        eta = (len(work) - i - 1) / rate if rate > 0 else 0
        print(f'[{i+1}/{len(work)}] {seed:<30} {ma[:14]:<14} vs {mb[:14]:<14} → {winner_ab} ({parsed.get("confidence","?"):<8})  eta {eta/60:.1f}min')

    print(f"\nDone. {errors} errors. Results in {RAW_OUT}")


if __name__ == "__main__":
    main()
