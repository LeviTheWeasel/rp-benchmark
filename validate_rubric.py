#!/usr/bin/env python3
"""Empirical rubric validation.

Question: Does our rubric actually agree with human preferences?

Method: Take all swipe pairs (rejected vs accepted responses for the
same context). Run each through our scoring signals. Check if accepted
responses score higher than rejected ones.

If accepted > rejected, rubric is validated (captures real preference).
If they're equal, rubric is noise.
If rejected > accepted, rubric is inverted (catastrophic).
"""
import json
import glob
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from harness.objective_metrics import compute_all as compute_obj, objective_score
from harness.slop_detectors import detect_all_slop


def main():
    # Load all swipe data
    all_swipes = []
    for f in glob.glob("scenarios/*_swipes.json"):
        with open(f) as fh:
            all_swipes.extend(json.load(fh))

    print(f"Loaded {len(all_swipes)} swipe scenarios")

    # For each swipe scenario, get accepted vs rejected and score both
    results = []  # [(accepted_scores, rejected_scores), ...]

    for s in all_swipes:
        variants = s.get("variants", [])
        accepted = [v for v in variants if v.get("is_accepted")]
        rejected = [v for v in variants if not v.get("is_accepted")]
        if not accepted or not rejected:
            continue

        acc_text = accepted[0].get("text_clean", "")
        if len(acc_text) < 50:
            continue

        # Score accepted (length-normalized)
        acc_obj = objective_score(compute_obj(acc_text), normalize_length=True)
        acc_slop = detect_all_slop(acc_text)

        # Score each rejected (average if multiple)
        rej_obj_scores = []
        rej_slop_weights = []
        rej_slop_densities = []
        for r in rejected:
            rt = r.get("text_clean", "")
            if len(rt) < 50:
                continue
            rej_obj_scores.append(objective_score(compute_obj(rt), normalize_length=True)["objective_score"])
            rs = detect_all_slop(rt)
            rej_slop_weights.append(rs["total_weight"])
            rej_slop_densities.append(rs.get("weight_per_1k_chars", 0))

        if not rej_obj_scores:
            continue

        acc_score = acc_obj["objective_score"]
        rej_score = sum(rej_obj_scores) / len(rej_obj_scores)
        acc_slop_w = acc_slop["total_weight"]
        rej_slop_w = sum(rej_slop_weights) / len(rej_slop_weights)
        acc_slop_density = acc_slop.get("weight_per_1k_chars", 0)
        rej_slop_density = sum(rej_slop_densities) / len(rej_slop_densities) if rej_slop_densities else 0

        results.append({
            "source": s.get("source", "unknown"),
            "lang": s.get("language", "en"),
            "acc_obj": acc_score,
            "rej_obj": rej_score,
            "acc_slop_weight": acc_slop_w,
            "rej_slop_weight": rej_slop_w,
            "acc_slop_density": acc_slop_density,
            "rej_slop_density": rej_slop_density,
            "acc_len": len(acc_text),
            "rej_len": sum(len(r.get("text_clean", "")) for r in rejected) / len(rejected),
        })

    print(f"Analyzed {len(results)} pairs\n")

    # ============ OBJECTIVE METRICS VALIDATION ============
    print("=" * 75)
    print("OBJECTIVE METRICS — does accepted beat rejected?")
    print("=" * 75)

    obj_accepted_wins = sum(1 for r in results if r["acc_obj"] > r["rej_obj"])
    obj_ties = sum(1 for r in results if r["acc_obj"] == r["rej_obj"])
    obj_rejected_wins = sum(1 for r in results if r["acc_obj"] < r["rej_obj"])
    n = len(results)

    print(f"\nAccepted scored higher: {obj_accepted_wins}/{n} ({100*obj_accepted_wins/n:.1f}%)")
    print(f"Tied:                  {obj_ties}/{n} ({100*obj_ties/n:.1f}%)")
    print(f"Rejected scored higher: {obj_rejected_wins}/{n} ({100*obj_rejected_wins/n:.1f}%)")

    avg_acc = sum(r["acc_obj"] for r in results) / n
    avg_rej = sum(r["rej_obj"] for r in results) / n
    print(f"\nAvg accepted objective score: {avg_acc:.1f}")
    print(f"Avg rejected objective score: {avg_rej:.1f}")
    print(f"Delta: {avg_acc - avg_rej:+.1f}")

    # Binomial test: is the result significantly different from 50%?
    # Using normal approximation
    import math
    p = obj_accepted_wins / (obj_accepted_wins + obj_rejected_wins) if (obj_accepted_wins + obj_rejected_wins) > 0 else 0.5
    se = math.sqrt(0.5 * 0.5 / n)
    z = (p - 0.5) / se if se > 0 else 0
    print(f"\nBinomial test vs 50%: p={p:.3f}, z={z:+.2f}")
    if abs(z) > 2.58:
        print(f"  Highly significant (p<0.01)")
    elif abs(z) > 1.96:
        print(f"  Significant (p<0.05)")
    else:
        print(f"  Not statistically significant")

    # ============ SLOP DETECTOR VALIDATION (density-normalized) ============
    print()
    print("=" * 75)
    print("SLOP DETECTORS (length-normalized) — does rejected have higher slop DENSITY?")
    print("=" * 75)

    slop_accepted_less = sum(1 for r in results if r["acc_slop_density"] < r["rej_slop_density"])
    slop_ties = sum(1 for r in results if r["acc_slop_density"] == r["rej_slop_density"])
    slop_accepted_more = sum(1 for r in results if r["acc_slop_density"] > r["rej_slop_density"])

    print(f"\nAccepted had LESS slop density: {slop_accepted_less}/{n} ({100*slop_accepted_less/n:.1f}%)")
    print(f"Tied:                           {slop_ties}/{n} ({100*slop_ties/n:.1f}%)")
    print(f"Accepted had MORE slop density:  {slop_accepted_more}/{n} ({100*slop_accepted_more/n:.1f}%)")

    avg_acc_slop = sum(r["acc_slop_density"] for r in results) / n
    avg_rej_slop = sum(r["rej_slop_density"] for r in results) / n
    print(f"\nAvg accepted slop density: {avg_acc_slop:.2f} per 1k chars")
    print(f"Avg rejected slop density: {avg_rej_slop:.2f} per 1k chars")

    if slop_accepted_less + slop_accepted_more > 0:
        p = slop_accepted_less / (slop_accepted_less + slop_accepted_more)
        se = math.sqrt(0.5 * 0.5 / n)
        z = (p - 0.5) / se if se > 0 else 0
        print(f"\nBinomial test vs 50%: p={p:.3f}, z={z:+.2f}")
        if abs(z) > 2.58:
            print(f"  Highly significant (p<0.01)")
        elif abs(z) > 1.96:
            print(f"  Significant (p<0.05)")
        else:
            print(f"  Not statistically significant")

    # ============ PER-SOURCE BREAKDOWN ============
    print()
    print("=" * 75)
    print("BREAKDOWN BY SOURCE — where does the rubric work best?")
    print("=" * 75)

    by_src = defaultdict(list)
    for r in results:
        by_src[r["source"]].append(r)

    print(f"\n{'Source':<25} {'N':<5} {'Obj wins':<10} {'Slop wins':<12}")
    print('-' * 60)
    for src, items in sorted(by_src.items(), key=lambda x: -len(x[1])):
        if len(items) < 5: continue
        obj_w = sum(1 for r in items if r["acc_obj"] > r["rej_obj"])
        slop_w = sum(1 for r in items if r["acc_slop_density"] < r["rej_slop_density"])
        n_src = len(items)
        print(f'{src:<25} {n_src:<5} {obj_w:>3}/{n_src} ({100*obj_w/n_src:>3.0f}%)  {slop_w:>3}/{n_src} ({100*slop_w/n_src:>3.0f}%)')

    # ============ LANGUAGE BREAKDOWN ============
    print()
    print("=" * 75)
    print("BREAKDOWN BY LANGUAGE")
    print("=" * 75)
    for lang in ["en", "ru"]:
        items = [r for r in results if r["lang"] == lang]
        if not items: continue
        obj_w = sum(1 for r in items if r["acc_obj"] > r["rej_obj"])
        slop_w = sum(1 for r in items if r["acc_slop_density"] < r["rej_slop_density"])
        print(f'\n{lang.upper()}: {len(items)} pairs')
        print(f'  Objective agrees with user: {obj_w}/{len(items)} ({100*obj_w/len(items):.0f}%)')
        print(f'  Slop agrees with user:      {slop_w}/{len(items)} ({100*slop_w/len(items):.0f}%)')

    # ============ LENGTH CONTROL ============
    print()
    print("=" * 75)
    print("LENGTH CONTROL — is shorter ALWAYS scored higher?")
    print("=" * 75)

    # How often does accepted beat rejected ONLY because it's shorter?
    # vs when accepted is longer but still wins?
    shorter_wins = []
    longer_wins = []
    for r in results:
        is_shorter = r["acc_len"] < r["rej_len"]
        obj_wins = r["acc_obj"] > r["rej_obj"]
        if is_shorter:
            shorter_wins.append(obj_wins)
        else:
            longer_wins.append(obj_wins)

    if shorter_wins:
        print(f'\nWhen accepted was SHORTER: {sum(shorter_wins)}/{len(shorter_wins)} objective agreed ({100*sum(shorter_wins)/len(shorter_wins):.0f}%)')
    if longer_wins:
        print(f'When accepted was LONGER:  {sum(longer_wins)}/{len(longer_wins)} objective agreed ({100*sum(longer_wins)/len(longer_wins):.0f}%)')

    # Save
    out = Path("results") / "rubric_validation.json"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w") as f:
        json.dump({
            "n_pairs": n,
            "objective_agreement": {
                "accepted_wins": obj_accepted_wins,
                "rejected_wins": obj_rejected_wins,
                "ties": obj_ties,
                "pct_agreement": round(100 * obj_accepted_wins / n, 1),
                "avg_accepted_score": round(avg_acc, 1),
                "avg_rejected_score": round(avg_rej, 1),
            },
            "slop_agreement": {
                "accepted_had_less": slop_accepted_less,
                "accepted_had_more": slop_accepted_more,
                "ties": slop_ties,
                "pct_agreement": round(100 * slop_accepted_less / n, 1),
                "avg_accepted_slop": round(avg_acc_slop, 2),
                "avg_rejected_slop": round(avg_rej_slop, 2),
            },
        }, f, indent=2)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
