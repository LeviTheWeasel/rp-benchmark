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


MODE_LABELS = {
    "F1_agency": "agency respect",
    "F2_pov_tense": "POV/tense consistency",
    "F3_lore_contradiction": "lore consistency",
    "F8_narrative_momentum": "narrative momentum",
    "F12_instruction_drift": "instruction following",
    "F13_context_attention_loss": "long-context attention",
    "Other": "general adversarial robustness",
}


def derive_strength_weakness(
    m: str,
    profiles: dict,
    behavioral: dict,
    failure_rates: dict,
    bayesian_by_model: dict,
    bayesian_n: int,
    mode_pool_sizes: dict[str, int],
    flaw_hunter: dict | None = None,
) -> tuple[str, str]:
    """Pick the most notable strength + weakness for this model."""
    prof = profiles.get(m, {})
    fail_modes = prof.get("failure_modes", {})
    comm = prof.get("community", {})
    subj = prof.get("subjective_dimensions", {})
    bay = bayesian_by_model.get(m)

    # ---- STRENGTH ----
    strength = None
    # 1. Top-3 on a failure mode
    for mode, data in fail_modes.items():
        if data.get("rank") in (1, 2):
            label = MODE_LABELS.get(mode, mode)
            strength = f"Top-{data['rank']} on {label} ({data['mean']:.2f}/5)"
            break

    # 2. Top community rank
    if not strength and comm.get("rank") and comm["rank"] <= 3:
        strength = f"Community top tier (#{comm['rank']}, ELO {comm['elo']:.0f})"

    # 3. Top Bayesian rank
    if not strength and bay and bay["rank"] <= 3:
        strength = f"Top-{bay['rank']} community Bayesian ELO ({bay['elo_mean']:.0f})"

    # 4. Best subjective
    if not strength and subj:
        best_subj = max(subj.items(), key=lambda x: x[1]["mean"])
        if best_subj[1]["mean"] >= 4.5:
            strength = f"Strong on {best_subj[0].replace('_', ' ')} ({best_subj[1]['mean']:.2f}/5)"

    # 5. NSFW specialist
    if not strength and comm.get("nsfw_winrate") and comm["nsfw_winrate"] >= 60:
        strength = f"NSFW specialist ({comm['nsfw_winrate']}% NSFW win rate)"

    # 6. Behavioral outlier (low repetition or high diversity)
    if not strength and m in behavioral.get("per_model", {}):
        beh = behavioral["per_model"][m]
        if "bigram_repetition" in beh:
            rep = beh["bigram_repetition"]["mean"]
            if rep <= 0.020:
                strength = f"Lowest phrase repetition ({rep:.3f} vs population {behavioral['population']['bigram_repetition']['mean']:.3f})"

    # 7. Flaw hunter top-3
    if not strength and flaw_hunter and m in flaw_hunter.get("per_model", {}):
        fh_models = flaw_hunter["per_model"]
        sorted_fh = sorted(fh_models.items(), key=lambda x: -x[1]["mean"])
        rank = next((i for i, (mm, _) in enumerate(sorted_fh, 1) if mm == m), 0)
        if rank and rank <= 3:
            strength = f"Top-{rank} on flaw hunter ({fh_models[m]['mean']:.1f}/100)"

    if not strength:
        strength = "No standout strength on tested dimensions"

    # ---- WEAKNESS ----
    weakness = None

    # 1. Floor < 3.5 on any failure mode
    for mode, data in fail_modes.items():
        if data.get("floor", 5) < 3.5:
            label = MODE_LABELS.get(mode, mode)
            weakness = f"Catastrophic floor on {label} (lowest session: {data['floor']})"
            break

    # 2. High binary failure rate
    if not weakness and m in failure_rates:
        for mode, (n, k) in failure_rates[m].items():
            if n >= 20 and k / n >= 0.10:
                rate = k / n * 100
                label = MODE_LABELS.get(mode, mode).replace(" consistency", "").replace(" respect", "")
                weakness = f"High {label} violation rate ({rate:.1f}%)"
                break

    # 3. Last or second-to-last on a failure mode (using actual pool size per mode)
    if not weakness and fail_modes:
        for mode, data in fail_modes.items():
            rank = data.get("rank")
            pool_n = mode_pool_sizes.get(mode, 0)
            if rank and pool_n and rank >= pool_n - 1:
                label = MODE_LABELS.get(mode, mode)
                bottom_pos = pool_n - rank + 1
                weakness = f"Bottom-{bottom_pos} on {label} (rank {rank}/{pool_n})"
                break

    # 4. Bottom Bayesian rank
    if not weakness and bay and bay["rank"] >= bayesian_n - 1:
        weakness = f"Bottom community ELO (#{bay['rank']}/{bayesian_n})"

    # 5. Bottom community rank
    if not weakness and comm.get("rank") and comm["rank"] >= 9:
        weakness = f"Lower community half (#{comm['rank']})"

    # 6. NSFW collapse
    if not weakness and comm.get("nsfw_winrate") and comm["nsfw_winrate"] <= 35:
        weakness = f"NSFW collapse ({comm['nsfw_winrate']}% NSFW win rate)"

    # 7. Behavioral outlier (high repetition)
    if not weakness and m in behavioral.get("per_model", {}):
        beh = behavioral["per_model"][m]
        if "bigram_repetition" in beh:
            rep = beh["bigram_repetition"]["mean"]
            pop_rep = behavioral["population"]["bigram_repetition"]["mean"]
            if rep > pop_rep * 1.5:
                weakness = f"High phrase repetition ({rep:.3f} vs population {pop_rep:.3f})"

    # 8. Flaw hunter bottom (high fatal-flaws-per-session)
    if not weakness and flaw_hunter and m in flaw_hunter.get("per_model", {}):
        fh = flaw_hunter["per_model"][m]
        if fh["fatal_per_session"] >= 0.75:
            weakness = f"Frequent fatal flaws ({fh['fatal_per_session']:.2f} per session, mean score {fh['mean']:.0f}/100)"

    if not weakness:
        weakness = "No standout weakness on tested dimensions"

    return strength, weakness


def main():
    failures = [json.loads(l) for l in open("results/per_turn_failures.jsonl")]
    behavioral = json.load(open("results/behavioral_metrics.json"))
    profiles = json.load(open("results/model_profiles.json"))
    bayesian = json.load(open("results/community_arena_bayesian.json"))
    # Flaw hunter aggregates per model
    fh_path = Path("results/flaw_hunter_session_summary.json")
    flaw_hunter = json.load(open(fh_path)) if fh_path.exists() else None

    # Per-(model, mode) failure rate
    failure_rates = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in failures:
        failure_rates[r["model"]][r["mode"]][0] += 1
        if r["is_failure"]:
            failure_rates[r["model"]][r["mode"]][1] += 1

    # Per-mode pool sizes (how many models have data on each failure mode)
    mode_pool_sizes = defaultdict(set)
    for model_key, prof in profiles.items():
        for mode in prof.get("failure_modes", {}):
            mode_pool_sizes[mode].add(model_key)
    mode_pool_sizes = {mode: len(s) for mode, s in mode_pool_sizes.items()}

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

        # ---- FLAW HUNTER (deduction-based 0-100) ----
        fh_blocks = []
        fh_json = {}
        if flaw_hunter and m in flaw_hunter.get("per_model", {}):
            fh = flaw_hunter["per_model"][m]
            mean = fh["mean"]
            median = fh["median"]
            band = ("exceptional" if mean >= 80 else "strong" if mean >= 70
                    else "good" if mean >= 55 else "mediocre" if mean >= 40
                    else "weak")
            top_flaws = ", ".join(f["flaw"].split(":", 1)[-1] for f in fh.get("top_flaws", [])[:3]) or "—"
            fh_blocks.append(f"  Mean score              {mean:>7.1f}/100  ({band})")
            fh_blocks.append(f"  Median score            {median:>7.1f}/100")
            fh_blocks.append(f"  Fatal flaws/session     {fh['fatal_per_session']:>7.2f}")
            fh_blocks.append(f"  Major flaws/session     {fh['major_per_session']:>7.2f}")
            fh_blocks.append(f"  Top flaws:              {top_flaws}")
            fh_blocks.append(f"  Sessions scored:        {fh['n']:>7}")
            fh_json = {
                "mean": mean,
                "median": median,
                "fatal_per_session": fh["fatal_per_session"],
                "major_per_session": fh["major_per_session"],
                "top_flaws": [f["flaw"] for f in fh.get("top_flaws", [])[:3]],
                "n_sessions": fh["n"],
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

        # ---- STRENGTH / WEAKNESS ----
        strength, weakness = derive_strength_weakness(
            m, profiles, behavioral, failure_rates, bayesian_by_model,
            len(bayesian_by_model), mode_pool_sizes, flaw_hunter,
        )

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
        if fh_blocks:
            lines.append("")
            lines.append("FLAW HUNTER (100 - deductions, target-aware)")
            lines.extend(fh_blocks)
        if s_blocks:
            lines.append("")
            lines.append("SUBJECTIVE (LLM-judge, rubric proxy)")
            lines.extend(s_blocks)
        if rank_block:
            lines.append("─" * 78)
            lines.append("")
            lines.append(rank_block)
        lines.append("")
        lines.append(f"Strength:  {strength}")
        lines.append(f"Weakness:  {weakness}")
        lines.append("```")
        lines.append("")

        cards_md.append("\n".join(lines))
        cards_json.append(
            {
                "model": m,
                "failure_rates": f_json,
                "behavioral": b_json,
                "subjective": s_json,
                "flaw_hunter": fh_json,
                "community": {
                    "rank": comm.get("rank"),
                    "elo": comm.get("elo"),
                    "n_votes": comm.get("n_votes"),
                },
                "bayesian": bay,
                "multiturn_judge_mean": prof.get("multiturn_llm_judge", {}).get("overall_mean"),
                "strength": strength,
                "weakness": weakness,
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
