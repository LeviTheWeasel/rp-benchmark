#!/usr/bin/env python3
"""Failure-target → flaw-type validation.

The flaw hunter outputs categorized flaws (purple_prose, agency_violation,
recycled_description, ...). Each session was run on a seed with a
declared failure_target (agency_violation, pov_tense_violation, etc.).

Cross-tabulating the two answers: "do seeds that target X actually
produce more X flaws?" If yes → seed designs are validated. If no →
the seeds aren't doing what we said they were.

Output: results/failure_target_validation.json + console table.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    records = [json.loads(l) for l in open("results/session_flaw_hunter.jsonl")]

    # Per (failure_target → flaw_type) counts. Two passes:
    # (a) all flaws — tells us the most-common failure mode overall (often
    #     dominated by minor "generic_detail" type flaws).
    # (b) fatal+major flaws only — tells us the SERIOUS failures, which
    #     should track the seed's failure_target if seeds are working.
    target_to_flaws = defaultdict(Counter)
    target_to_serious = defaultdict(Counter)
    target_session_count = Counter()

    for r in records:
        target = r["failure_target"]
        target_session_count[target] += 1
        for cat in ["fatal_flaws", "major_flaws", "minor_flaws"]:
            for f in r.get(cat, []):
                flaw = f.get("flaw", "?")
                target_to_flaws[target][flaw] += 1
                if cat in ("fatal_flaws", "major_flaws"):
                    target_to_serious[target][flaw] += 1

    # Compute "flaw rate per session" so different sample sizes are comparable
    target_to_rate = {
        target: {
            flaw: count / target_session_count[target]
            for flaw, count in flaws.items()
        }
        for target, flaws in target_to_flaws.items()
    }

    # All flaw types seen
    all_flaws = sorted({f for c in target_to_flaws.values() for f in c})

    # Print: rate of each flaw type per failure target
    print("FLAW TYPE RATE PER FAILURE TARGET")
    print("=" * 100)
    print("(rows = seed targets, cols = flaw types; values = avg flaws of that type per session)")
    print()
    targets = sorted(target_to_flaws, key=lambda t: -target_session_count[t])
    print(f'  {"Target":<40}{"n":<5}', end="")
    for f in all_flaws:
        print(f"{f[:14]:<15}", end="")
    print()
    print("  " + "-" * (45 + 15 * len(all_flaws)))

    for target in targets:
        n = target_session_count[target]
        print(f"  {target:<40}{n:<5}", end="")
        for f in all_flaws:
            rate = target_to_rate[target].get(f, 0)
            cell = f"{rate:.2f}" if rate else "—"
            print(f"{cell:<15}", end="")
        print()

    # Validation: does each target's TOP flaw match its declared failure mode?
    print()
    print("=" * 100)
    print("VALIDATION: top flaw type per target — does it match the seed's intent?")
    print("=" * 100)

    # Map of target → expected flaw archetype
    EXPECTED = {
        "agency_violation": ["agency_violation"],
        "pov_tense_violation": ["wrong_pov_tense", "pov_tense_violation", "wrong_language_pov_tense", "pov_tense"],
        "system_prompt_violation": ["character_break", "wrong_pov_tense", "wrong_language_pov_tense"],
        "system_prompt_detail_loss": ["character_break", "convenient_world"],
        "contradictory_context_resolution": ["character_break"],
        "narrative_stagnation": ["overlong_for_moment", "undercooked_for_moment", "samey_sentence_rhythm"],
        "physics_sycophancy": ["convenient_world"],
        "temporal_inconsistency": ["skipped_time_logic"],
        "over_explicit_subtext": ["narrating_emotions", "missed_subtext"],
        "character_flattening": ["character_break", "flat_npc_voice"],
        "genre_instability": ["character_break", "flat_npc_voice"],
    }

    print(f'  {"Target":<40}{"Top SERIOUS flaw":<28}{"Rate/session":<14}{"Expected match?":<20}')
    print("  " + "-" * 100)
    validation = {}
    for target in targets:
        # Use SERIOUS flaws only (fatal + major) — minor flaws like
        # "generic_detail" are universal noise that drowns out the signal.
        flaws = target_to_serious[target].most_common(5)
        if not flaws:
            continue
        top_flaw, top_count = flaws[0]
        rate = top_count / target_session_count[target]
        expected = EXPECTED.get(target, [])
        is_match = any(e in top_flaw or top_flaw in e for e in expected)
        # Also check if any of top-3 serious flaws matches expected
        top3_match = any(
            any(e in f or f in e for e in expected)
            for f, _ in flaws[:3]
        )
        match_str = ("YES (top-1)" if is_match else
                     "YES (in top-3)" if top3_match else
                     "no")
        validation[target] = {
            "top_serious_flaw": top_flaw,
            "top_serious_rate": round(rate, 2),
            "expected": expected,
            "matches_expected_top1": is_match,
            "matches_expected_top3": top3_match,
            "top_5_serious": [{"flaw": f, "count": c, "rate": round(c / target_session_count[target], 2)} for f, c in flaws],
        }
        print(f"  {target:<40}{top_flaw:<28}{rate:<14.2f}{match_str:<20}")

    matched_top1 = sum(1 for v in validation.values() if v["matches_expected_top1"])
    matched_top3 = sum(1 for v in validation.values() if v["matches_expected_top3"])
    total = len(validation)
    print()
    print(f"Top-1 match rate: {matched_top1}/{total} = {100*matched_top1/total:.0f}%")
    print(f"Top-3 match rate: {matched_top3}/{total} = {100*matched_top3/total:.0f}%")

    out_path = Path("results/failure_target_validation.json")
    with open(out_path, "w") as f:
        json.dump(
            {
                "n_records": len(records),
                "target_session_count": dict(target_session_count),
                "flaw_rate_per_target": target_to_rate,
                "validation": validation,
                "match_rate_top1": round(matched_top1 / total, 2) if total else 0,
            "match_rate_top3": round(matched_top3 / total, 2) if total else 0,
            },
            f,
            indent=2,
        )
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
