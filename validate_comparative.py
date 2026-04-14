#!/usr/bin/env python3
"""Empirical validation of the comparative A/B judge.

Same 75 pairs as flaw hunter validation. Comparative judge sees BOTH
responses at once and picks a winner — theoretically easier for LLMs
than absolute scoring.
"""
import json
import glob
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from harness.api import judge_response
from harness.runner import load_judge_prompt


def run_comparative(text_a: str, text_b: str, judge_system: str) -> dict:
    """Judge A vs B, returns the winner."""
    payload = f"""<response_a>
{text_a}
</response_a>

<response_b>
{text_b}
</response_b>

Which response is better and why?"""
    try:
        result = judge_response("anthropic/claude-sonnet-4", judge_system, payload)
        scores = result["scores"]
        if scores.get("parse_error"):
            return {"error": "parse_error", "winner": None}
        return {
            "winner": scores.get("winner"),
            "confidence": scores.get("confidence"),
            "summary": scores.get("summary", ""),
        }
    except Exception as e:
        return {"error": str(e)[:100], "winner": None}


def main():
    target_pairs = int(sys.argv[1]) if len(sys.argv) > 1 else 75

    # Load all swipe pairs
    all_swipes = []
    for f in glob.glob("scenarios/*_swipes.json"):
        with open(f) as fh:
            all_swipes.extend(json.load(fh))

    valid = []
    for s in all_swipes:
        variants = s.get("variants", [])
        accepted = [v for v in variants if v.get("is_accepted")]
        rejected = [v for v in variants if not v.get("is_accepted")]
        if not accepted or not rejected:
            continue
        acc_text = accepted[0].get("text_clean", "")
        rej_text = rejected[0].get("text_clean", "")
        if len(acc_text) < 100 or len(rej_text) < 100:
            continue
        valid.append({
            "source": s.get("source", "unknown"),
            "lang": s.get("language", "en"),
            "accepted": acc_text,
            "rejected": rej_text,
        })

    # Sample — stratified
    random.seed(42)
    by_source = defaultdict(list)
    for v in valid:
        by_source[v["source"]].append(v)

    sampled = []
    per_source = max(1, target_pairs // len(by_source))
    for src, items in by_source.items():
        random.shuffle(items)
        sampled.extend(items[:per_source])
    random.shuffle(sampled)
    sampled = sampled[:target_pairs]

    print(f"Loaded {len(valid)} valid pairs, sampling {len(sampled)}")
    print(f"Est cost: ~${len(sampled) * 0.05:.2f} (half of flaw hunter since 1 call per pair)")
    print()

    judge_system = load_judge_prompt("claude_sonnet", mode="comparative")

    results = []
    errors = 0
    start = time.time()

    for i, pair in enumerate(sampled):
        print(f"[{i+1}/{len(sampled)}] {pair['source']}...", end=" ", flush=True)

        # Randomize order to remove position bias
        if random.random() < 0.5:
            text_a = pair["accepted"]
            text_b = pair["rejected"]
            accepted_is = "A"
        else:
            text_a = pair["rejected"]
            text_b = pair["accepted"]
            accepted_is = "B"

        result = run_comparative(text_a, text_b, judge_system)

        if result.get("error"):
            errors += 1
            print(f"ERROR: {result['error'][:50]}")
            continue

        winner = result.get("winner")
        if not winner:
            errors += 1
            print("no winner")
            continue

        agreed = winner == accepted_is
        results.append({
            "source": pair["source"],
            "lang": pair["lang"],
            "accepted_is": accepted_is,
            "judge_winner": winner,
            "agreed": agreed,
            "confidence": result.get("confidence", "?"),
        })
        marker = "✓" if agreed else "✗"
        print(f"{marker} judge picked {winner}, accepted was {accepted_is} ({result.get('confidence', '?')})")

    elapsed = time.time() - start
    print(f"\nCompleted {len(results)} pairs in {elapsed/60:.1f} min ({errors} errors)")

    if not results:
        return

    n = len(results)
    agreed = sum(1 for r in results if r["agreed"])

    print()
    print("=" * 75)
    print("COMPARATIVE JUDGE vs USER PREFERENCE")
    print("=" * 75)
    print()
    print(f"Total pairs: {n}")
    print(f"  Judge agreed with user: {agreed}/{n} ({100*agreed/n:.1f}%)")
    print(f"  Judge disagreed:        {n-agreed}/{n} ({100*(n-agreed)/n:.1f}%)")

    # Significance
    import math
    se = math.sqrt(0.5 * 0.5 / n)
    p = agreed / n
    z = (p - 0.5) / se if se > 0 else 0
    print(f"\nBinomial test vs 50%: p={p:.3f}, z={z:+.2f}")
    if abs(z) > 2.58:
        print("  Highly significant (p<0.01)")
    elif abs(z) > 1.96:
        print("  Significant (p<0.05)")
    else:
        print("  Not statistically significant")

    # By confidence
    print()
    print("BY CONFIDENCE:")
    conf_groups = defaultdict(list)
    for r in results:
        conf_groups[r.get("confidence", "?")].append(r)
    for conf, items in sorted(conf_groups.items()):
        a = sum(1 for r in items if r["agreed"])
        print(f"  {conf:<12} n={len(items):<3} agree={100*a/len(items):.0f}%")

    # By source
    print()
    print("BY SOURCE:")
    by_src = defaultdict(list)
    for r in results:
        by_src[r["source"]].append(r)
    for src, items in sorted(by_src.items(), key=lambda x: -len(x[1])):
        if len(items) < 3:
            continue
        a = sum(1 for r in items if r["agreed"])
        print(f"  {src:<25} n={len(items):<3} agree={100*a/len(items):.0f}%")

    # By language
    print()
    print("BY LANGUAGE:")
    for lang in ["en", "ru"]:
        items = [r for r in results if r["lang"] == lang]
        if not items:
            continue
        a = sum(1 for r in items if r["agreed"])
        print(f"  {lang.upper()}: n={len(items)}, agree={100*a/len(items):.0f}%")

    # Comparison summary
    print()
    print("=" * 75)
    print("SIGNAL COMPARISON (across all validation runs)")
    print("=" * 75)
    print()
    print(f"  Objective metrics (n=725): 42.3% agreement")
    print(f"  Slop detectors (n=725):    30.6% agreement")
    print(f"  Flaw hunter (n=75):        38.7% agreement")
    print(f"  Comparative judge (n={n}):    {100*agreed/n:.1f}% agreement  <- NEW")

    # Save
    out = Path("results") / "comparative_validation.json"
    with open(out, "w") as f:
        json.dump({
            "n_pairs": n,
            "agreed": agreed,
            "agreement_pct": round(100 * agreed / n, 1),
            "results": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
