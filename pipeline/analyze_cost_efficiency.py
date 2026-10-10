#!/usr/bin/env python3
"""Cost-adjusted leaderboard.

For each model, computes "quality per dollar" using OpenRouter pricing
(approximate — sourced from public pricing pages as of 2026-04 and
verified against actual usage logs from our runs).

Two metrics:
  - Likert points per dollar       = mt_judge_mean / cost_per_1m_blended
  - Flaw hunter points per dollar  = flaw_hunter_mean / cost_per_1m_blended

Where cost_per_1m_blended is a 60/40 input/output weighted average per
1M tokens (matches our actual call profile: ~60% input from growing
context, ~40% output from generation).

Surfaces the practical question: which models give the most quality
per dollar, ignoring the absolute leaderboard?

Output: results/cost_efficiency.json + console table.
"""
import json
import statistics as st
from pathlib import Path

# OpenRouter prices in $/1M tokens (input, output). Approximate — these
# move around. Verified roughly against our usage in the per-call cost
# field of the OpenRouter response logs.
PRICING = {
    "claude_opus_4_6":         (15.00, 75.00),
    "claude_opus_4_7":         (15.00, 75.00),
    "claude_sonnet_4_5":       ( 3.00, 15.00),
    "deepseek_v3_2":           ( 0.27,  0.40),
    "deepseek_v4_pro":         ( 2.00,  5.00),
    "deepseek_v4_flash":       ( 0.10,  0.30),
    "gemini_2_5_flash":        ( 0.30,  1.20),
    "gemini_3_1_pro":          ( 7.00, 20.00),
    "gemini_3_1_flash_lite":   ( 0.10,  0.30),
    "gemma_4_26b":             ( 0.30,  0.50),
    "glm_4_7":                 ( 0.50,  1.50),
    "glm_5_1":                 ( 1.00,  3.00),
    "gpt_4_1":                 ( 2.00,  8.00),
    "grok_4_1":                ( 0.20,  0.50),
    "kimi_k2_5":               ( 0.60,  2.50),
    "kimi_k2_6":               ( 0.60,  2.50),
    "llama_4_maverick":        ( 0.20,  0.60),
    "minimax_m2_7":            ( 0.30,  1.10),
    "mistral_small_creative":  ( 0.30,  0.80),
    "qwen3_5_flash":           ( 0.20,  0.60),
}


def blended(model: str, input_share: float = 0.6) -> float:
    """60/40 input/output weighted blended cost per 1M tokens."""
    p = PRICING.get(model)
    if p is None:
        return None
    return input_share * p[0] + (1 - input_share) * p[1]


def main():
    profiles = json.load(open("results/model_profiles.json"))
    flaw_hunter = json.load(open("results/flaw_hunter_session_summary.json"))
    bayesian = json.load(open("results/community_arena_bayesian.json"))
    bayesian_by_model = {e["model"]: e["elo_mean"] for e in bayesian["leaderboard"]}

    rows = []
    for m, prof in profiles.items():
        cost = blended(m)
        if cost is None:
            continue
        likert = prof.get("multiturn_llm_judge", {}).get("overall_mean")
        fh_mean = flaw_hunter["per_model"].get(m, {}).get("mean")
        bay_elo = bayesian_by_model.get(m)

        rows.append({
            "model": m,
            "cost_per_1m": round(cost, 3),
            "likert": likert,
            "fh": fh_mean,
            "bayesian_elo": bay_elo,
            # Quality-per-dollar metrics
            "likert_per_dollar": round(likert / cost, 3) if (likert and cost) else None,
            "fh_per_dollar": round(fh_mean / cost, 3) if (fh_mean and cost) else None,
            "bay_per_dollar": round(bay_elo / cost, 1) if (bay_elo and cost) else None,
        })

    # Sort by Likert/$
    rows.sort(key=lambda r: -(r["likert_per_dollar"] or 0))

    print("COST-EFFICIENCY LEADERBOARD")
    print("=" * 90)
    print(f'{"Rank":<5}{"Model":<28}{"$/1M":<9}{"Likert":<9}{"L/$":<9}{"FH":<8}{"FH/$":<9}{"Bayes":<9}')
    print("-" * 90)
    for i, r in enumerate(rows, 1):
        likert = f"{r['likert']:.2f}" if r['likert'] else "—"
        fh = f"{r['fh']:.1f}" if r['fh'] else "—"
        bay = f"{int(r['bayesian_elo'])}" if r['bayesian_elo'] else "—"
        l_per = f"{r['likert_per_dollar']:.2f}" if r['likert_per_dollar'] else "—"
        fh_per = f"{r['fh_per_dollar']:.1f}" if r['fh_per_dollar'] else "—"
        print(f'#{i:<4}{r["model"]:<28}${r["cost_per_1m"]:<7.2f}{likert:<9}{l_per:<9}{fh:<8}{fh_per:<9}{bay:<9}')

    print()
    print("Interpretation:")
    print("  L/$  = Likert mean / blended cost per 1M tokens (higher = more quality per $)")
    print("  FH/$ = Flaw hunter mean / blended cost per 1M tokens")
    print()

    # Top efficiency picks
    top_likert = max(rows, key=lambda r: r["likert_per_dollar"] or 0)
    sorted_fh = sorted(
        [r for r in rows if r["fh_per_dollar"]],
        key=lambda r: -r["fh_per_dollar"],
    )

    print(f'Best Likert-per-dollar:     {top_likert["model"]} '
          f'({top_likert["likert"]:.2f} / ${top_likert["cost_per_1m"]:.2f} = {top_likert["likert_per_dollar"]:.2f})')
    if sorted_fh:
        print(f'Best FlawHunter-per-dollar: {sorted_fh[0]["model"]} '
              f'({sorted_fh[0]["fh"]:.1f} / ${sorted_fh[0]["cost_per_1m"]:.2f} = {sorted_fh[0]["fh_per_dollar"]:.1f})')

    out_path = Path("results/cost_efficiency.json")
    with open(out_path, "w") as f:
        json.dump({"pricing_source": "OpenRouter approx 2026-04",
                   "blended_share_input": 0.6,
                   "leaderboard": rows}, f, indent=2)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
