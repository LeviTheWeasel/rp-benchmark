#!/usr/bin/env python3
"""Quality-per-second leaderboard.

Combines our quality metrics with OpenRouter-reported median generation time
to surface models that are both high-quality AND fast. A model that scores
4.5 Likert in 2 seconds is more useful than one scoring 4.6 in 60 seconds
for most production roleplay use cases.

Primary metric: likert_per_sec = Likert_overall / median_gen_seconds. Likert is
the only quality metric we have for all 20 test models (the older
combined_leaderboard.json only covers the original 8). Also surfaces flaw-hunter
session means and Bayesian ELO where available.

Inputs:
  - results/latency_leaderboard.json (median_gen_ms per model)
  - results/model_profiles.json (Likert overall mean)
  - results/flaw_hunter_session_summary.json (per-model flaw-finding mean)
  - results/community_arena_bayesian.json (Bayesian ELO from human votes)

Output:
  - results/quality_speed_leaderboard.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent / "results"


def load(name):
    return json.load(open(ROOT / name))


def main():
    latency = load("latency_leaderboard.json")["per_model"]
    profiles = load("model_profiles.json")
    flaw_sessions = load("flaw_hunter_session_summary.json").get("per_model", {})
    bayes = {e["model"]: e for e in load("community_arena_bayesian.json")["leaderboard"]}

    rows = []
    for key, lat in latency.items():
        if lat.get("role") in ("JUDGE", "user-sim"):
            continue
        gen_s = lat["median_gen_ms"] / 1000.0
        if gen_s <= 0:
            continue

        prof = profiles.get(key, {})
        likert = (prof.get("multiturn_llm_judge") or {}).get("overall_mean")
        flaw = (flaw_sessions.get(key) or {}).get("mean")
        elo = (bayes.get(key) or {}).get("elo_mean")
        cost = lat.get("median_actual_cost_usd", 0)

        row = {
            "model": key,
            "median_gen_seconds": round(gen_s, 2),
            "tokens_per_second": lat["tokens_per_second"],
            "median_completion_tokens": lat["median_completion_tokens"],
            "median_reasoning_tokens": lat.get("median_reasoning_tokens", 0),
            "truncation_pct": lat.get("truncation_pct", 0),
            "median_actual_cost_usd": cost,
            "likert_overall": likert,
            "flaw_hunter_mean": flaw,
            "bayes_elo": round(elo, 1) if elo else None,
            "likert_per_sec": round(likert / gen_s, 3) if likert else None,
            "flaw_hunter_per_sec": round(flaw / gen_s, 3) if flaw else None,
            "elo_per_sec": round(elo / gen_s, 2) if elo else None,
            "likert_per_dollar": round(likert / cost, 1) if likert and cost > 0 else None,
        }
        rows.append(row)

    print("=" * 138)
    print("QUALITY / SPEED LEADERBOARD — Likert quality per second of generation (primary metric)")
    print("=" * 138)
    print(f'{"Model":<26}{"gen(s)":<9}{"tok/s":<7}{"out":<7}{"reas":<7}'
          f'{"Likert":<9}{"Flaw↑":<8}{"ELO":<7}{"$/call":<10}{"Likert/s":<11}{"Flaw/s":<10}{"L/$":<8}{"trunc"}')
    print("-" * 138)
    rows_sorted = sorted(rows, key=lambda r: -(r["likert_per_sec"] or 0))
    for r in rows_sorted:
        print(
            f'{r["model"]:<26}'
            f'{r["median_gen_seconds"]:<9.1f}'
            f'{r["tokens_per_second"]:<7.0f}'
            f'{r["median_completion_tokens"]:<7}'
            f'{r["median_reasoning_tokens"]:<7}'
            f'{(r["likert_overall"] or 0):<9.2f}'
            f'{(r["flaw_hunter_mean"] or 0):<8.1f}'
            f'{(r["bayes_elo"] or 0):<7.0f}'
            f'${r["median_actual_cost_usd"]:<9.4f}'
            f'{(r["likert_per_sec"] or 0):<11.3f}'
            f'{(r["flaw_hunter_per_sec"] or 0):<10.2f}'
            f'{(r["likert_per_dollar"] or 0):<8.0f}'
            f'{r["truncation_pct"]:>3.0f}%'
        )

    print()
    print("Reading the table:")
    print("- gen(s)    : median end-to-end generation time per call (lower is faster)")
    print("- reas      : median reasoning tokens per call (0 = non-reasoning model)")
    print("- Likert    : multi-turn judge mean (1-5, higher is better)")
    print("- Flaw↑     : flaw-hunter session mean (raw points, higher = better at finding flaws)")
    print("- ELO       : Bayesian arena ELO from real users (higher is better; 0 = no votes yet)")
    print("- $/call    : actual median OpenRouter-billed cost per call")
    print("- Likert/s  : PRIMARY — Likert / gen(s). Higher = more quality per second.")
    print("- Flaw/s    : flaw-hunter / gen(s). Both axes scaled, see methodology.")
    print("- L/$       : Likert / $/call — dollar-efficiency. 0 = BYOK or free.")
    print("- trunc     : pct of calls cut off at length limit (a quality bug, not just speed)")

    out = ROOT / "quality_speed_leaderboard.json"
    with open(out, "w") as f:
        json.dump({
            "n_models": len(rows_sorted),
            "metric_definition": (
                "combined_per_sec = combined_score / median_gen_seconds. "
                "Higher = better quality per unit of latency."
            ),
            "leaderboard": rows_sorted,
        }, f, indent=2)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
