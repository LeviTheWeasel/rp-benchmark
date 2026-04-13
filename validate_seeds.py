#!/usr/bin/env python3
"""Validate synthetic seeds — check if they differentiate models.

Runs 3 models on all 8 seeds, judges each, checks score spread.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from harness.api import chat_completion, judge_response
from harness.config import GENERATION_CONFIG, JUDGE_CONFIG
from harness.runner import load_judge_prompt

SEEDS_PATH = Path(__file__).parent / "hf_dataset" / "seeds" / "seeds.json"

# 3 models spanning quality range: strong, mid, small
VALIDATION_MODELS = {
    "claude_sonnet_4_5": "anthropic/claude-sonnet-4.5",
    "gemini_flash": "google/gemini-2.5-flash",
    "gemma_4_26b": "google/gemma-4-26b-a4b-it",
}

JUDGE = ("claude_sonnet", "anthropic/claude-sonnet-4")


def build_gen_prompt(seed: dict) -> tuple[str, str]:
    char = seed["character_name"]
    user = seed["user_name"]

    system = (
        f"You are roleplaying as {char}. Stay in character. "
        f"Write in third-person past tense. Do NOT write actions or dialogue for {user}.\n\n"
        f"## Your Character\n{seed['character_setting']}"
    )

    user_msg = f"{seed['opening_message']}\n\n{seed['user_name']}:\n{seed['initial_user_input']}\n\n[Continue as {char}.]"
    return system, user_msg


def build_judge_payload(seed: dict, response: str) -> str:
    return f"""<context>
{seed['opening_message']}

{seed['user_name']}:
{seed['initial_user_input']}
</context>

<character_card>
Character: {seed['character_name']}
Setting: {seed['character_setting'][:500]}
User: {seed['user_name']}
</character_card>

<response_to_evaluate>
{response}
</response_to_evaluate>

<evaluation_mode>single</evaluation_mode>"""


def extract_overall(scores: dict) -> float | None:
    if scores.get("parse_error"):
        return None
    return scores.get("aggregate", {}).get("overall")


def main():
    with open(SEEDS_PATH) as f:
        seeds = json.load(f)

    judge_key, judge_model = JUDGE
    judge_system = load_judge_prompt(judge_key)

    print("Seed Validation Run")
    print(f"  Seeds: {len(seeds)}")
    print(f"  Models: {list(VALIDATION_MODELS.keys())}")
    print(f"  Judge: {judge_key}")
    print(f"  Total calls: {len(seeds) * len(VALIDATION_MODELS) * 2}")
    print()

    # results[seed_id][model] = score
    results = {}

    for seed in seeds:
        sid = seed["id"]
        results[sid] = {}
        genres = ", ".join(seed.get("genre_tags", []))

        print(f"--- {sid} ({genres}) ---")

        for model_key, model_id in VALIDATION_MODELS.items():
            # Generate
            system, user_msg = build_gen_prompt(seed)
            gen = chat_completion(model_id, system, user_msg, GENERATION_CONFIG)
            response_text = gen["content"]
            print(f"  {model_key}: generated {len(response_text)} chars")

            # Judge
            payload = build_judge_payload(seed, response_text)
            judge_result = judge_response(judge_model, judge_system, payload)
            overall = extract_overall(judge_result["scores"])

            if overall is not None:
                results[sid][model_key] = overall
                print(f"    -> {overall:.2f}")
            else:
                print(f"    -> PARSE ERROR")
                results[sid][model_key] = None

        print()

    # Analysis
    print("=" * 70)
    print("SEED VALIDATION RESULTS")
    print("=" * 70)
    print()

    models = list(VALIDATION_MODELS.keys())
    print(f"{'Seed':<35} ", end="")
    for m in models:
        print(f"{m:<20}", end="")
    print(f"{'Spread':<8} {'Verdict'}")
    print("-" * 100)

    good_seeds = 0
    for seed in seeds:
        sid = seed["id"]
        scores = results.get(sid, {})

        print(f"{sid:<35} ", end="")
        valid_scores = []
        for m in models:
            s = scores.get(m)
            if s is not None:
                print(f"{s:<20.2f}", end="")
                valid_scores.append(s)
            else:
                print(f"{'ERR':<20}", end="")

        if len(valid_scores) >= 2:
            spread = max(valid_scores) - min(valid_scores)
            if spread >= 0.5:
                verdict = "GOOD"
                good_seeds += 1
            elif spread >= 0.25:
                verdict = "WEAK"
            else:
                verdict = "FLAT"
            print(f"{spread:<8.2f} {verdict}")
        else:
            print(f"{'N/A':<8} INSUFFICIENT")

    print("-" * 100)
    print(f"\nGOOD seeds (spread >= 0.5): {good_seeds}/{len(seeds)}")
    print(f"Recommendation: {'Seeds differentiate models well' if good_seeds >= 5 else 'Some seeds need rework' if good_seeds >= 3 else 'Seeds do not differentiate — rework needed'}")

    # Save raw results
    out = Path(__file__).parent / "results" / "seed_validation.json"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nRaw results saved to {out}")


if __name__ == "__main__":
    main()
