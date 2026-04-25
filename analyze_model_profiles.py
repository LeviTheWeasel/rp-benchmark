#!/usr/bin/env python3
"""Multi-signal profile per model.

Combines all the signals we have into one per-model report:
  - Community arena ELO + SFW/NSFW win rates (from community_arena_2000.json)
  - Multi-turn LLM-judge overall mean (from multiturn_merged_all.json)
  - Per failure-mode mean and rank (F1 agency, F2 POV/tense, F3 lore,
    F8 narrative momentum, F12 instruction drift, F13 big-card attention)
  - Floor scores (worst single session per mode) — surfaces where the
    model catastrophically fails

Output: results/model_profiles.json (per-model dicts) and a printed
human-readable summary.

Usage:
    python3 analyze_model_profiles.py
"""
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

TAXONOMY = {
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
    "F3_lore_contradiction": [
        "adv_contradictory_lore_02",
    ],
    "F8_narrative_momentum": [
        "adv_passive_user_03",
    ],
    "F12_instruction_drift": [
        "adv_sysprompt_speech_pattern_15",
        "adv_sysprompt_style_restriction_16",
        "adv_sysprompt_forbidden_topic_17",
    ],
    "F13_context_attention_loss": [
        "adv_bigcard_buried_details_18",
        "adv_bigcard_relationship_web_19",
        "adv_bigcard_rules_overload_20",
    ],
    "Other": [
        "adv_impossible_physics_04",
        "adv_time_pressure_05",
        "adv_subtle_ooc_06",
        "adv_character_break_bait_07",
        "adv_genre_shift_08",
    ],
}


def main():
    merged = json.load(open("results/multiturn_merged_all.json"))
    comm = json.load(open("results/community_arena_2000.json"))
    comm_by_model = {e["model"]: e for e in comm["leaderboard"]}

    # Group MT scores by model + mode + per-dimension
    mt_by_mode = defaultdict(lambda: defaultdict(list))
    mt_overall = defaultdict(list)
    # Subjective dimensions — mapped from existing rubric:
    #   Engagement       <- S.3_narrative_momentum
    #   Tone consistency <- S.1_consistency_over_time
    #   Collaboration    <- S.4_adaptive_responsiveness
    SUBJECTIVE_MAP = {
        "engagement": "S.3_narrative_momentum",
        "tone_consistency": "S.1_consistency_over_time",
        "collaboration": "S.4_adaptive_responsiveness",
    }
    mt_subjective = defaultdict(lambda: defaultdict(list))

    for s in merged["sessions"]:
        if "judges" not in s:
            continue
        j = list(s["judges"].values())[0]["scores"]
        o = j.get("overall")
        if o is None:
            continue
        m = s["test_model"]
        mt_overall[m].append(o)
        for mode, sids in TAXONOMY.items():
            if s["seed_id"] in sids:
                mt_by_mode[mode][m].append(o)

        # Subjective dimensions from session_dimensions
        sd = j.get("session_dimensions", {})
        for label, src_dim in SUBJECTIVE_MAP.items():
            entry = sd.get(src_dim, {})
            if isinstance(entry, dict) and "score" in entry:
                mt_subjective[label][m].append(entry["score"])

    # Compute per-mode rankings
    mode_ranks = {}
    for mode in TAXONOMY:
        sorted_m = sorted(
            mt_by_mode[mode], key=lambda m: -st.mean(mt_by_mode[mode][m])
        )
        mode_ranks[mode] = {m: i + 1 for i, m in enumerate(sorted_m)}

    # Build per-model profiles
    profiles = {}
    all_models = sorted(mt_overall)
    for m in all_models:
        comm_entry = comm_by_model.get(m, {})
        mt_mean = st.mean(mt_overall[m]) if mt_overall[m] else None

        per_mode = {}
        for mode in TAXONOMY:
            scores = mt_by_mode[mode].get(m, [])
            if scores:
                per_mode[mode] = {
                    "mean": round(st.mean(scores), 2),
                    "floor": round(min(scores), 1),
                    "n": len(scores),
                    "rank": mode_ranks[mode].get(m),
                }

        # Subjective dimensions (mapped from rubric)
        subjective = {}
        for label in ("engagement", "tone_consistency", "collaboration"):
            scores = mt_subjective[label].get(m, [])
            if scores:
                subjective[label] = {
                    "mean": round(st.mean(scores), 2),
                    "n": len(scores),
                }

        profiles[m] = {
            "community": {
                "rank": comm_entry.get("rank"),
                "elo": comm_entry.get("elo"),
                "stability": comm_entry.get("stability"),
                "overall_winrate": comm_entry.get("overall_winrate"),
                "sfw_winrate": comm_entry.get("sfw_winrate"),
                "nsfw_winrate": comm_entry.get("nsfw_winrate"),
                "n_votes": comm_entry.get("overall_n"),
            },
            "multiturn_llm_judge": {
                "overall_mean": round(mt_mean, 2) if mt_mean else None,
                "n_sessions": len(mt_overall[m]),
            },
            "failure_modes": per_mode,
            "subjective_dimensions": subjective,
        }

    # Average failure-mode rank per model
    for m, prof in profiles.items():
        ranks = [prof["failure_modes"][k]["rank"] for k in TAXONOMY if k in prof["failure_modes"]]
        prof["avg_failure_rank"] = round(st.mean(ranks), 2) if ranks else None

    out = Path("results/model_profiles.json")
    with open(out, "w") as f:
        json.dump(profiles, f, indent=2)
    print(f"Saved: {out}")
    print()

    # Human-readable summary
    print("=" * 92)
    print("MULTI-SIGNAL MODEL PROFILES")
    print("=" * 92)
    for m in sorted(profiles, key=lambda x: profiles[x]["avg_failure_rank"] or 99):
        p = profiles[m]
        c = p["community"]
        mt = p["multiturn_llm_judge"]

        c_rank = c.get("rank") or "—"
        c_elo = c.get("elo") or "—"
        c_n = c.get("n_votes") or "—"
        c_sfw = c.get("sfw_winrate")
        c_nsfw = c.get("nsfw_winrate")
        sfw_str = f"{c_sfw}%" if c_sfw is not None else "—"
        nsfw_str = f"{c_nsfw}%" if c_nsfw is not None else "—"

        print()
        print(f"  {m}")
        print(f"  {'─' * 80}")
        print(f"  Community arena:    rank #{c_rank}   ELO {c_elo}   SFW {sfw_str}   NSFW {nsfw_str}   n={c_n}")
        print(f"  Multi-turn judge:   {mt['overall_mean']} mean ({mt['n_sessions']} sessions)")
        print(f"  Avg failure rank:   {p['avg_failure_rank']:.1f}")
        print(f"  Per failure mode:")

        for mode in TAXONOMY:
            if mode in p["failure_modes"]:
                fm = p["failure_modes"][mode]
                rank = fm["rank"]
                bar = "█" * int(max(0, fm["mean"] - 3.5) * 4)
                rank_str = f"#{rank}/12"
                flag = ""
                if fm["floor"] < 3.5:
                    flag = "  ⚠ FLOOR " + str(fm["floor"])
                print(f"    {mode:<32} {fm['mean']:.2f}  {rank_str:<7}  {bar}{flag}")

        # Subjective dimensions (mapped from existing rubric)
        subj = p.get("subjective_dimensions", {})
        if subj:
            print(f"  Subjective (proxied from rubric, scale 1-5):")
            for label in ("engagement", "tone_consistency", "collaboration"):
                if label in subj:
                    e = subj[label]
                    bar = "█" * int(max(0, e["mean"] - 3.5) * 4)
                    print(f"    {label:<32} {e['mean']:.2f}/5  {bar}")


if __name__ == "__main__":
    main()
