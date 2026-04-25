#!/usr/bin/env python3
"""Cross-method correlation matrix.

Computes Spearman rank correlation between every pair of scoring
methods we have for the 20 models:

  - Likert overall (multi-turn judge mean)
  - Per-mode Likert means (F1, F2, F12, F13)
  - Binary failure rates (F1 from per_turn_failures)
  - Flaw hunter mean
  - Community Bayesian ELO

A high correlation means the two methods agree on rankings; low or
negative means they're measuring different things. Validates which
signals are redundant and which add unique information.

Output: results/method_correlations.json + console heatmap.
"""
import json
import statistics as st
from collections import defaultdict
from pathlib import Path


def spearman(xs, ys):
    """Spearman rank correlation. Returns NaN if fewer than 3 valid pairs."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xs, ys = zip(*pairs)
    rx = rank(xs)
    ry = rank(ys)
    n = len(xs)
    d_sq = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1 - 6 * d_sq / (n * (n * n - 1))


def rank(values):
    """Average-rank tied-handling rank vector."""
    sorted_vals = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(sorted_vals):
        j = i
        while j + 1 < len(sorted_vals) and sorted_vals[j + 1][1] == sorted_vals[i][1]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[sorted_vals[k][0]] = avg_rank
        i = j + 1
    return ranks


def main():
    profiles = json.load(open("results/model_profiles.json"))
    behavioral = json.load(open("results/behavioral_metrics.json"))
    bayesian = json.load(open("results/community_arena_bayesian.json"))
    flaw_hunter = json.load(open("results/flaw_hunter_session_summary.json"))
    failures = [json.loads(l) for l in open("results/per_turn_failures.jsonl")]

    bayesian_by_model = {e["model"]: e["elo_mean"] for e in bayesian["leaderboard"]}
    fh_by_model = {m: d["mean"] for m, d in flaw_hunter["per_model"].items()}

    # Binary F1 failure rate per model
    f1_rate = {}
    for r in failures:
        if r["mode"] != "F1_agency":
            continue
        m = r["model"]
        if m not in f1_rate:
            f1_rate[m] = [0, 0]
        f1_rate[m][0] += 1
        if r["is_failure"]:
            f1_rate[m][1] += 1
    f1_pct = {m: (k / n * 100) for m, (n, k) in f1_rate.items()}

    # Build per-model vectors
    models = sorted(profiles.keys())
    methods = {
        "Likert overall": {},
        "F1 Likert mean": {},
        "F2 Likert mean": {},
        "F12 Likert mean": {},
        "F13 Likert mean": {},
        "F1 binary rate": {},
        "Flaw hunter mean": {},
        "Bayesian ELO": {},
        "Behavioral unique-wr": {},
        "Behavioral repetition": {},
    }

    for m in models:
        p = profiles[m]
        mt = p.get("multiturn_llm_judge", {}).get("overall_mean")
        methods["Likert overall"][m] = mt

        for mode_key, label in [
            ("F1_agency", "F1 Likert mean"),
            ("F2_pov_tense", "F2 Likert mean"),
            ("F12_instruction_drift", "F12 Likert mean"),
            ("F13_context_attention_loss", "F13 Likert mean"),
        ]:
            fm = p.get("failure_modes", {}).get(mode_key)
            methods[label][m] = fm["mean"] if fm else None

        # Binary failure rate is "lower = better", so we negate to align with "higher = better"
        rate = f1_pct.get(m)
        methods["F1 binary rate"][m] = -rate if rate is not None else None

        methods["Flaw hunter mean"][m] = fh_by_model.get(m)
        methods["Bayesian ELO"][m] = bayesian_by_model.get(m)

        beh = behavioral["per_model"].get(m, {})
        if "unique_word_ratio" in beh:
            methods["Behavioral unique-wr"][m] = beh["unique_word_ratio"]["mean"]
        if "bigram_repetition" in beh:
            # Lower = better, negate
            methods["Behavioral repetition"][m] = -beh["bigram_repetition"]["mean"]

    # Build matrix
    method_names = list(methods.keys())
    matrix = {}
    for a in method_names:
        matrix[a] = {}
        for b in method_names:
            xs = [methods[a].get(m) for m in models]
            ys = [methods[b].get(m) for m in models]
            rho = spearman(xs, ys)
            matrix[a][b] = round(rho, 3) if rho is not None else None

    # Print heatmap
    print(f"{'':<26}", end="")
    for b in method_names:
        print(f"{b[:7]:>9}", end="")
    print()
    print("-" * (26 + 9 * len(method_names)))
    for a in method_names:
        print(f"{a:<26}", end="")
        for b in method_names:
            v = matrix[a][b]
            if v is None:
                cell = "  -  "
            else:
                cell = f"{v:+.2f}"
                # Visual marker
                if a != b and abs(v) >= 0.5:
                    cell += "*"
                else:
                    cell += " "
            print(f"{cell:>9}", end="")
        print()
    print()
    print("(* = |rho| >= 0.5, ie methods strongly agree or strongly disagree)")
    print()

    # Notable findings
    print("Notable correlations (off-diagonal, |rho| >= 0.5):")
    seen = set()
    for a in method_names:
        for b in method_names:
            if a == b or (b, a) in seen:
                continue
            seen.add((a, b))
            v = matrix[a][b]
            if v is not None and abs(v) >= 0.5:
                direction = "agrees" if v > 0 else "DISAGREES"
                print(f"  {a:<26} {direction:<11} {b:<26}  rho={v:+.2f}")

    # Print pairs with strong disagreement (negative rho)
    print()
    print("Methods that disagree on rankings (rho < 0):")
    for a in method_names:
        for b in method_names:
            if a >= b:
                continue
            v = matrix[a][b]
            if v is not None and v < 0:
                print(f"  {a:<26} vs {b:<26}  rho={v:+.2f}")

    out_path = Path("results/method_correlations.json")
    with open(out_path, "w") as f:
        json.dump(
            {
                "models": models,
                "methods": list(method_names),
                "values_per_model": {a: methods[a] for a in method_names},
                "spearman_matrix": matrix,
            },
            f,
            indent=2,
        )
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
