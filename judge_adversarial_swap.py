#!/usr/bin/env python3
"""Re-run every pair from adversarial_pairwise_raw.jsonl with A/B swapped.

The original run showed a massive 84% A-position bias. Re-running each
pair in the reverse ordering gives us both directions; the ELO analysis
then uses both outcomes, which neutralizes position bias.

Appends to a *separate* file so we can tell the two passes apart.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from harness.api import chat_completion
from harness.config import JUDGE_CONFIG
from judge_adversarial_pairwise import (
    JUDGE_PROMPT_FILE,
    DEFAULT_SOURCE,
    DEFAULT_JUDGE,
    build_user_content,
)

ORIGINAL_RAW = Path("results/adversarial_pairwise_raw.jsonl")
SWAPPED_RAW = Path("results/adversarial_pairwise_raw_swapped.jsonl")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--judge", default=DEFAULT_JUDGE)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if not ORIGINAL_RAW.exists():
        print(f"Missing {ORIGINAL_RAW}. Run judge_adversarial_pairwise.py first.")
        sys.exit(1)

    originals = [json.loads(line) for line in open(ORIGINAL_RAW)]

    # Skip pairs already swapped
    done = set()
    if SWAPPED_RAW.exists():
        for line in open(SWAPPED_RAW):
            try:
                r = json.loads(line)
                done.add((r["seed_id"], r["model_a"], r["model_b"]))
            except Exception:
                pass

    # Work list: reverse each (seed, a, b) into (seed, b, a)
    work = []
    for r in originals:
        swapped_key = (r["seed_id"], r["model_b"], r["model_a"])
        if swapped_key in done:
            continue
        work.append(swapped_key)

    if args.limit:
        work = work[: args.limit]

    data = json.load(open(args.source))
    sessions_by_key = {
        (s["seed_id"], s["test_model"]): s for s in data["sessions"] if "judges" in s
    }
    judge_prompt = JUDGE_PROMPT_FILE.read_text()

    print(f"Judge: {args.judge}")
    print(f"Original pairs: {len(originals)}")
    print(f"Already swapped: {len(done)}")
    print(f"To run now: {len(work)}")

    errors = 0
    t0 = time.time()

    for i, (seed, ma, mb) in enumerate(work):
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
            print(f"[{i+1}/{len(work)}] ERR {seed} {ma}v{mb}: {e}")
            if errors > 10:
                print("Too many errors.")
                break
            continue

        content = resp.get("content", "")
        parsed = None
        for cand in (content, content.strip("` \n")):
            try:
                parsed = json.loads(cand.replace("```json", "").replace("```", "").strip())
                break
            except Exception:
                continue
        if not parsed or "winner" not in parsed:
            errors += 1
            print(f"[{i+1}/{len(work)}] PARSE-ERR {seed} {ma}v{mb}")
            continue

        winner_ab = parsed["winner"]
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
            "pass": "swapped",
        }
        with open(SWAPPED_RAW, "a") as f:
            f.write(json.dumps(rec) + "\n")

        elapsed = time.time() - t0
        rate = (i + 1) / elapsed
        eta = (len(work) - i - 1) / rate if rate > 0 else 0
        print(f'[{i+1}/{len(work)}] {seed:<30} {ma[:14]:<14} vs {mb[:14]:<14} → {winner_ab} ({parsed.get("confidence","?")})  eta {eta/60:.1f}min')

    print(f"\nDone. {errors} errors. Results in {SWAPPED_RAW}")


if __name__ == "__main__":
    main()
