#!/usr/bin/env python3
"""Empirical validation of the flaw hunter judge against real swipe preferences.

For each swipe pair (accepted vs rejected), run flaw hunter on both and
check if accepted scores higher than rejected. If yes, the LLM judge
captures real user preference.

Cost: ~$10 for 100 pairs (200 Claude Sonnet calls).
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


def run_flaw_hunter(text: str, judge_system: str) -> dict:
    """Run flaw hunter on a single response and return the score."""
    payload = f"<response_to_evaluate>\n{text}\n</response_to_evaluate>"
    try:
        result = judge_response("anthropic/claude-sonnet-4", judge_system, payload)
        scores = result["scores"]
        if scores.get("parse_error"):
            return {"error": "parse_error", "score": None}
        return {
            "score": scores.get("final_score"),
            "fatal": len(scores.get("fatal_flaws", [])),
            "major": len(scores.get("major_flaws", [])),
            "minor": len(scores.get("minor_flaws", [])),
            "bonuses": len(scores.get("bonuses", [])),
        }
    except Exception as e:
        return {"error": str(e)[:100], "score": None}


def main():
    target_pairs = int(sys.argv[1]) if len(sys.argv) > 1 else 100

    # Load all swipe pairs
    all_swipes = []
    for f in glob.glob("scenarios/*_swipes.json"):
        with open(f) as fh:
            all_swipes.extend(json.load(fh))

    # Build valid pairs
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

    # Random sample for cost control, stratified by source
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

    print(f"Loaded {len(valid)} valid swipe pairs")
    print(f"Sampling {len(sampled)} pairs across {len(by_source)} sources")
    print(f"Est cost: ~${len(sampled) * 2 * 0.05:.2f}")
    print()

    judge_system = load_judge_prompt("claude_sonnet", mode="flaw_hunter")

    results = []
    errors = 0
    start = time.time()

    for i, pair in enumerate(sampled):
        print(f"[{i+1}/{len(sampled)}] {pair['source']}...", end=" ", flush=True)

        acc_result = run_flaw_hunter(pair["accepted"], judge_system)
        rej_result = run_flaw_hunter(pair["rejected"], judge_system)

        if acc_result.get("error") or rej_result.get("error"):
            errors += 1
            print("ERROR")
            continue

        agreed = acc_result["score"] > rej_result["score"]
        tied = acc_result["score"] == rej_result["score"]
        delta = acc_result["score"] - rej_result["score"]

        results.append({
            "source": pair["source"],
            "lang": pair["lang"],
            "acc_score": acc_result["score"],
            "rej_score": rej_result["score"],
            "delta": delta,
            "agreed": agreed,
            "tied": tied,
            "acc_fatal": acc_result["fatal"],
            "rej_fatal": rej_result["fatal"],
            "acc_major": acc_result["major"],
            "rej_major": rej_result["major"],
        })
        print(f"acc={acc_result['score']} rej={rej_result['score']} delta={delta:+d}")

    elapsed = time.time() - start
    print(f"\nCompleted {len(results)} pairs in {elapsed/60:.1f} min ({errors} errors)")

    if not results:
        print("No results")
        return

    # Stats
    n = len(results)
    agreed = sum(1 for r in results if r["agreed"])
    tied = sum(1 for r in results if r["tied"])
    disagreed = n - agreed - tied

    avg_delta = sum(r["delta"] for r in results) / n
    agreed_pairs = [r for r in results if r["agreed"]]
    disagreed_pairs = [r for r in results if not r["agreed"] and not r["tied"]]
    avg_delta_when_agree = sum(r["delta"] for r in agreed_pairs) / len(agreed_pairs) if agreed_pairs else 0
    avg_delta_when_disagree = sum(r["delta"] for r in disagreed_pairs) / len(disagreed_pairs) if disagreed_pairs else 0

    print()
    print("=" * 75)
    print("FLAW HUNTER vs USER PREFERENCE — VALIDATION RESULTS")
    print("=" * 75)
    print()
    print(f"Total pairs: {n}")
    print(f"  Judge agreed with user:    {agreed}/{n} ({100*agreed/n:.1f}%)")
    print(f"  Tied:                      {tied}/{n} ({100*tied/n:.1f}%)")
    print(f"  Judge disagreed with user: {disagreed}/{n} ({100*disagreed/n:.1f}%)")
    print()
    print(f"Avg score delta (accepted - rejected): {avg_delta:+.2f}")
    print(f"  When agreed: {avg_delta_when_agree:+.2f} (avg margin)")
    print(f"  When disagreed: {avg_delta_when_disagree:+.2f}")

    # Significance test
    import math
    if agreed + disagreed > 0:
        p = agreed / (agreed + disagreed)
        se = math.sqrt(0.5 * 0.5 / n)
        z = (p - 0.5) / se if se > 0 else 0
        print(f"\nBinomial test vs 50%: p={p:.3f}, z={z:+.2f}")
        if abs(z) > 2.58:
            print(f"  Highly significant (p<0.01)")
        elif abs(z) > 1.96:
            print(f"  Significant (p<0.05)")
        else:
            print(f"  Not statistically significant")

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
        t = sum(1 for r in items if r["tied"])
        avg_d = sum(r["delta"] for r in items) / len(items)
        print(f'  {src:<25} n={len(items):<3} agree={100*a/len(items):>3.0f}%  tied={100*t/len(items):>3.0f}%  avg delta={avg_d:+.1f}')

    # By language
    print()
    print("BY LANGUAGE:")
    for lang in ["en", "ru"]:
        items = [r for r in results if r["lang"] == lang]
        if not items:
            continue
        a = sum(1 for r in items if r["agreed"])
        avg_d = sum(r["delta"] for r in items) / len(items)
        print(f'  {lang.upper()}: n={len(items)}, agree={100*a/len(items):.0f}%, avg delta={avg_d:+.1f}')

    # Fatal flaw patterns
    print()
    print("FATAL FLAW PATTERNS (rejected should have more):")
    acc_fatal_total = sum(r["acc_fatal"] for r in results)
    rej_fatal_total = sum(r["rej_fatal"] for r in results)
    print(f"  Accepted total fatal flaws: {acc_fatal_total}")
    print(f"  Rejected total fatal flaws: {rej_fatal_total}")
    if rej_fatal_total > acc_fatal_total:
        print(f"  => Rejected responses have {rej_fatal_total - acc_fatal_total} more fatal flaws (good signal)")
    else:
        print(f"  => Fatal flaw count doesn't differentiate well")

    # Save
    out = Path("results") / "flaw_hunter_validation.json"
    with open(out, "w") as f:
        json.dump({
            "n_pairs": n,
            "agreed": agreed,
            "tied": tied,
            "disagreed": disagreed,
            "agreement_pct": round(100 * agreed / n, 1),
            "avg_delta": round(avg_delta, 2),
            "avg_delta_when_agree": round(avg_delta_when_agree, 2),
            "avg_delta_when_disagree": round(avg_delta_when_disagree, 2),
            "results": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
