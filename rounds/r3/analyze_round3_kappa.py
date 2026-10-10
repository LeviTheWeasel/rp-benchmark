#!/usr/bin/env python3
"""Round 3 analysis: pairwise Cohen's quadratic-weighted kappa between judges,
plus per-judge cross-method Spearman rho vs the multi-turn arena ELO.

Inputs:
  - results/round3_multi_judge.json    (from rounds/r3/judge_round3_multi.py)
  - results/multiturn_arena_bayesian.json
  - results/multiturn_merged_all_v2.json (for the original Sonnet 4 scores
    on the same selected sessions)

Outputs:
  - results/round3_kappa.json
  - prints a summary table
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr


ROUND3 = Path("results/round3_multi_judge.json")
MT_ARENA = Path("results/multiturn_arena_bayesian.json")
OUT = Path("results/round3_kappa.json")


def quadratic_weighted_kappa(y1, y2, n_levels=5):
    """Cohen's kappa with quadratic weights for ordinal scales.

    Maps each rating to the nearest of n_levels integer levels and computes:
        kappa = 1 - sum(w_ij * O_ij) / sum(w_ij * E_ij)
    with w_ij = (i-j)^2 / (n_levels-1)^2

    Both y1 and y2 are 1-D arrays of ratings on a 1..n_levels scale.
    """
    y1 = np.asarray(y1, dtype=float)
    y2 = np.asarray(y2, dtype=float)
    if len(y1) == 0 or len(y2) == 0 or len(y1) != len(y2):
        return None
    # Bin to integer levels (round to nearest 1..n_levels)
    b1 = np.clip(np.round(y1), 1, n_levels).astype(int)
    b2 = np.clip(np.round(y2), 1, n_levels).astype(int)
    n = len(b1)

    # Confusion matrix (observed)
    O = np.zeros((n_levels, n_levels), dtype=float)
    for a, b in zip(b1, b2):
        O[a-1, b-1] += 1
    # Marginals
    row = O.sum(axis=1, keepdims=True)
    col = O.sum(axis=0, keepdims=True)
    # Expected (independence)
    E = row @ col / n
    # Quadratic weights
    idx = np.arange(n_levels)
    W = (idx[:, None] - idx[None, :]) ** 2 / float((n_levels - 1) ** 2)

    num = float(np.sum(W * O))
    den = float(np.sum(W * E))
    if den == 0:
        return None
    return 1.0 - num / den


def main():
    if not ROUND3.exists():
        print(f"ERROR: {ROUND3} not found. Run rounds/r3/judge_round3_multi.py first.")
        return 1

    state = json.loads(ROUND3.read_text())
    results = state["results"]
    print(f"Round-3 sessions in store: {len(results)}")

    # --- Collect per-session per-judge overall scores ---
    judge_keys = set()
    for r in results.values():
        for k in r.get("second_judges", {}):
            judge_keys.add(k)
    judges = ["claude_sonnet"] + sorted(judge_keys)
    print(f"Judges in store: {judges}")

    # Per-session per-judge overall score (None if missing / parse error)
    per_session = {}  # key -> {judge: overall}
    parse_errors = defaultdict(int)
    for key, r in results.items():
        per_session[key] = {"test_model": r["test_model"], "seed_id": r["seed_id"]}
        # Sonnet
        sc = r.get("claude_sonnet", {}).get("scores", {})
        per_session[key]["claude_sonnet"] = sc.get("overall")
        # Second judges
        for jk, jres in r.get("second_judges", {}).items():
            sj_scores = jres.get("scores", {})
            if jres.get("error") or sj_scores.get("parse_error"):
                per_session[key][jk] = None
                parse_errors[jk] += 1
            else:
                per_session[key][jk] = sj_scores.get("overall")

    # --- Pairwise weighted kappa ---
    print()
    print("=" * 78)
    print("PAIRWISE COHEN'S QUADRATIC-WEIGHTED KAPPA (between judges, on overall Likert)")
    print("=" * 78)
    print(f'{"judge_a":<24}{"judge_b":<24}{"n":<6}{"kappa":<10}{"interpretation"}')
    print("-" * 78)

    pair_results = {}
    for i, ja in enumerate(judges):
        for jb in judges[i+1:]:
            xs, ys = [], []
            for key, sc in per_session.items():
                a = sc.get(ja); b = sc.get(jb)
                if a is not None and b is not None:
                    xs.append(a); ys.append(b)
            kappa = quadratic_weighted_kappa(xs, ys) if xs else None
            interp = "no data"
            if kappa is not None:
                if   kappa > 0.80: interp = "almost perfect"
                elif kappa > 0.60: interp = "substantial"
                elif kappa > 0.40: interp = "moderate"
                elif kappa > 0.20: interp = "fair"
                else:              interp = "poor"
            print(f'{ja:<24}{jb:<24}{len(xs):<6}'
                  f'{kappa if kappa is not None else float("nan"):<10.3f}{interp}')
            pair_results[f"{ja}__vs__{jb}"] = {
                "judge_a": ja, "judge_b": jb,
                "n_sessions": len(xs),
                "kappa_quadratic_weighted": (None if kappa is None else round(kappa, 4)),
                "interpretation": interp,
            }

    # --- Inter-judge per-model rank correlation ---
    # κ measures absolute Likert agreement (sensitive to calibration drift).
    # Spearman ρ between judges' per-model-mean rankings is calibration-invariant
    # and answers "do judges rank models the same way?"
    per_judge_per_model_for_corr = {j: defaultdict(list) for j in judges}
    for sc in per_session.values():
        for j in judges:
            v = sc.get(j)
            if v is not None:
                per_judge_per_model_for_corr[j][sc["test_model"]].append(v)
    per_judge_means_corr = {
        j: {m: float(np.mean(v)) for m, v in d.items() if v}
        for j, d in per_judge_per_model_for_corr.items()
    }

    print()
    print("=" * 78)
    print("INTER-JUDGE rank correlation (Spearman rho on per-model mean Likert)")
    print("=" * 78)
    inter_judge_rho = {}
    for i, ja in enumerate(judges):
        for jb in judges[i+1:]:
            common = sorted(m for m in per_judge_means_corr[ja]
                            if m in per_judge_means_corr[jb])
            if len(common) < 3:
                continue
            xs = [per_judge_means_corr[ja][m] for m in common]
            ys = [per_judge_means_corr[jb][m] for m in common]
            rho, p = spearmanr(xs, ys)
            print(f'  {ja:<24} ↔ {jb:<24}  n={len(common):<3} '
                  f'ρ = {rho:+.3f}  (p = {p:.3f})')
            inter_judge_rho[f"{ja}__vs__{jb}"] = {
                "n_models": len(common),
                "rho": round(float(rho), 4),
                "p_value": round(float(p), 4),
            }

    # --- Per-judge cross-method Spearman rho vs multi-turn arena ELO ---
    if MT_ARENA.exists():
        mt = json.loads(MT_ARENA.read_text())
        mt_elo = {e["model"]: e["elo_mean"] for e in mt["leaderboard"]}
        # Per-judge per-model mean Likert (averaged over sessions in this round-3 sample)
        per_judge_per_model = {j: defaultdict(list) for j in judges}
        for sc in per_session.values():
            for j in judges:
                v = sc.get(j)
                if v is not None:
                    per_judge_per_model[j][sc["test_model"]].append(v)
        per_judge_means = {
            j: {m: float(np.mean(v)) for m, v in d.items() if v}
            for j, d in per_judge_per_model.items()
        }

        print()
        print("=" * 78)
        print("PER-JUDGE SPEARMAN rho vs MULTI-TURN ARENA ELO (n = models)")
        print("=" * 78)
        rho_results = {}
        for j in judges:
            common = sorted(m for m in per_judge_means[j] if m in mt_elo)
            xs = [per_judge_means[j][m] for m in common]
            ys = [mt_elo[m] for m in common]
            if len(common) >= 3:
                rho, p = spearmanr(xs, ys)
                print(f'  {j:<24} n_models={len(common):<3}  rho = {rho:+.3f}  (p = {p:.3f})')
                rho_results[j] = {
                    "n_models": len(common),
                    "rho": round(float(rho), 4),
                    "p_value": round(float(p), 4),
                    "per_model_mean": {m: round(per_judge_means[j][m], 3) for m in common},
                }
            else:
                print(f'  {j:<24} n_models={len(common)}  insufficient data')
                rho_results[j] = {"n_models": len(common), "rho": None, "p_value": None}
    else:
        rho_results = {"note": "multiturn_arena_bayesian.json missing; per-judge rho skipped"}

    # --- Output ---
    out = {
        "n_sessions_in_subsample": len(per_session),
        "judges": judges,
        "parse_errors_per_judge": dict(parse_errors),
        "pairwise_kappa": pair_results,
        "inter_judge_rho_per_model": inter_judge_rho,
        "per_judge_rho_vs_mt_arena": rho_results,
        "per_session_overall_scores": [
            {
                "key": k,
                "test_model": s["test_model"],
                "seed_id": s["seed_id"],
                **{j: s[j] for j in judges},
            }
            for k, s in per_session.items()
        ],
    }
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nSaved: {OUT}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main() or 0)
