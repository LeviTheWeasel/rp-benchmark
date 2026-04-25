#!/usr/bin/env python3
"""Generate per-model profile cards in the experiment-design mockup format.

Combines four signals:
  - FAILURE RATES   <- per_turn_failures.jsonl (Wilson 95% CI)
  - BEHAVIORAL      <- behavioral_metrics.json
  - SUBJECTIVE      <- model_profiles.json (rubric-mapped)
  - OVERALL RANK    <- community_arena_bayesian.json

Output: results/profile_cards.md  (markdown blocks)
        results/profile_cards.json (structured for programmatic use)

Usage:
    python3 generate_profile_cards.py
"""
import json
import math
from collections import defaultdict
from pathlib import Path


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0, 0
    phat = k / n
    denom = 1 + z**2 / n
    centre = (phat + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n * n)) / denom
    return max(0, centre - margin), min(1, centre + margin)


def main():
    failures = [json.loads(l) for l in open("results/per_turn_failures.jsonl")]
    behavioral = json.load(open("results/behavioral_metrics.json"))
    profiles = json.load(open("results/model_profiles.json"))
    bayesian = json.load(open("results/community_arena_bayesian.json"))

    # Per-(model, mode) failure rate
    failure_rates = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in failures:
        failure_rates[r["model"]][r["mode"]][0] += 1
        if r["is_failure"]:
            failure_rates[r["model"]][r["mode"]][1] += 1

    bayesian_by_model = {e["model"]: e for e in bayesian["leaderboard"]}
    pop = behavioral["population"]
    pop_means = {k: v["mean"] for k, v in pop.items()}

    # All models (union)
    models = sorted(
        set(profiles.keys())
        | set(behavioral["per_model"].keys())
        | set(bayesian_by_model.keys())
    )

    # Sort by Bayesian ELO when available, else by avg failure rank
    def sort_key(m):
        b = bayesian_by_model.get(m)
        if b:
            return (-b["elo_mean"], 0)
        return (0, profiles.get(m, {}).get("avg_failure_rank") or 99)

    cards_md = []
    cards_json = []

    for m in sorted(models, key=sort_key):
        prof = profiles.get(m, {})
        beh = behavioral["per_model"].get(m, {})
        bay = bayesian_by_model.get(m)
        comm = prof.get("community", {})
        subj = prof.get("subjective_dimensions", {})

        # ---- FAILURE RATES ----
        f_blocks = []
        f_json = {}
        for mode_key, mode_label in [
            ("F1_agency", "Agency violations"),
            ("F2_pov_tense", "POV/Tense violations"),
        ]:
            if mode_key in failure_rates[m]:
                n, k = failure_rates[m][mode_key]
                rate = k / n if n else 0
                lo, hi = wilson_ci(k, n)
                ci_half = (hi - lo) / 2
                # Visual bar: 0-25% range, 12 chars wide
                bar_len = 12
                filled = int(min(rate / 0.25, 1) * bar_len)
                bar = "█" * filled + "░" * (bar_len - filled)
                f_blocks.append(
                    f"  {mode_label:<22}{rate*100:>5.1f}%  [±{ci_half*100:.1f}%]  {bar}  {n} probes"
                )
                f_json[mode_key] = {
                    "rate_pct": round(rate * 100, 2),
                    "ci_half_pct": round(ci_half * 100, 2),
                    "n": n,
                    "failures": k,
                }

        # ---- BEHAVIORAL METRICS ----
        b_blocks = []
        b_json = {}
        for metric, label in [
            ("word_count", "Avg words"),
            ("unique_word_ratio", "Prose quality (unique wr)"),
            ("bigram_repetition", "Repetition score"),
        ]:
            if metric in beh:
                val = beh[metric]["mean"]
                pop_val = pop_means.get(metric, 0)
                marker = ""
                # Direction-aware: lower repetition = better, higher unique-wr = better
                if metric == "bigram_repetition":
                    marker = " ↑" if val > pop_val * 1.2 else (" ↓" if val < pop_val * 0.8 else "")
                elif metric == "unique_word_ratio":
                    marker = " ↑" if val > pop_val + 0.05 else (" ↓" if val < pop_val - 0.05 else "")
                b_blocks.append(
                    f"  {label:<25}{val:>7.3f}  (population avg: {pop_val:.3f}){marker}"
                )
                b_json[metric] = {
                    "value": round(val, 4),
                    "population_avg": round(pop_val, 4),
                    "delta": round(val - pop_val, 4),
                }

        # ---- SUBJECTIVE ----
        s_blocks = []
        s_json = {}
        for k, label in [
            ("engagement", "Engagement"),
            ("tone_consistency", "Tone consistency"),
            ("collaboration", "Collaboration"),
        ]:
            if k in subj:
                v = subj[k]["mean"]
                s_blocks.append(f"  {label:<25}{v:>7.2f}/5")
                s_json[k] = round(v, 2)

        # ---- OVERALL RANK ----
        rank_block = ""
        if bay:
            rank_block = (
                f"OVERALL RELIABILITY RANK: #{bay['rank']} of {len(bayesian_by_model)}   "
                f"[Bayesian ELO: {bay['elo_mean']:.0f} ± {bay['elo_std']:.0f}, "
                f"95% CI [{bay['ci_low_95']:.0f}, {bay['ci_high_95']:.0f}]]"
            )
        elif "rank" in comm and comm["rank"]:
            rank_block = f"COMMUNITY RANK: #{comm['rank']}  ELO {comm.get('elo','—')}  (frequentist)"
        else:
            mt_mean = prof.get("multiturn_llm_judge", {}).get("overall_mean")
            if mt_mean:
                rank_block = f"NOT IN COMMUNITY ARENA POOL.  MT-judge mean: {mt_mean}"

        # Build markdown card
        lines = []
        lines.append(f"### {m}")
        lines.append("")
        lines.append("```")
        lines.append(f"Model: {m}")
        lines.append("─" * 78)
        if f_blocks:
            lines.append("")
            lines.append("FAILURE RATES (lower = better)")
            lines.extend(f_blocks)
        if b_blocks:
            lines.append("")
            lines.append("BEHAVIORAL METRICS")
            lines.extend(b_blocks)
        if s_blocks:
            lines.append("")
            lines.append("SUBJECTIVE (LLM-judge, rubric proxy)")
            lines.extend(s_blocks)
        if rank_block:
            lines.append("─" * 78)
            lines.append("")
            lines.append(rank_block)
        lines.append("```")
        lines.append("")

        cards_md.append("\n".join(lines))
        cards_json.append(
            {
                "model": m,
                "failure_rates": f_json,
                "behavioral": b_json,
                "subjective": s_json,
                "community": {
                    "rank": comm.get("rank"),
                    "elo": comm.get("elo"),
                    "n_votes": comm.get("n_votes"),
                },
                "bayesian": bay,
                "multiturn_judge_mean": prof.get("multiturn_llm_judge", {}).get("overall_mean"),
            }
        )

    md_path = Path("results/profile_cards.md")
    md_path.write_text("\n".join(cards_md))
    print(f"Saved: {md_path}")

    json_path = Path("results/profile_cards.json")
    with open(json_path, "w") as f:
        json.dump({"models": cards_json}, f, indent=2)
    print(f"Saved: {json_path}")
    print()
    print(f"Generated {len(cards_md)} profile cards")


if __name__ == "__main__":
    main()
