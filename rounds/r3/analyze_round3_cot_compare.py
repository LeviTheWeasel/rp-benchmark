#!/usr/bin/env python3
"""Compare no-CoT (Round 3) vs CoT-first (this experiment) judge prompts.

For the same 60-session sub-sample and the same three judges, contrast
the two prompt variants on three axes:

  1. Per-judge per-session score deltas (paired) — does CoT change
     individual session scores? (Pearson r and mean signed difference.)

  2. Inter-judge weighted Cohen's κ — does CoT bring the three judges
     into closer absolute-Likert agreement?

  3. Per-judge cross-method ρ vs multi-turn arena ELO — does CoT change
     the per-model rank correlation against the human arena?

Inputs:
  - results/round3_multi_judge.json    (no-CoT, original Round 3)
  - results/round3_cot_judge.json      (CoT-first, new experiment)
  - results/multiturn_arena_bayesian.json (for the per-judge ρ test)

Output:
  - results/round3_cot_compare.json
  - prints a side-by-side comparison table
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr


NO_COT  = Path("results/round3_multi_judge.json")
COT     = Path("results/round3_cot_judge.json")
MT_ARENA = Path("results/multiturn_arena_bayesian.json")
OUT     = Path("results/round3_cot_compare.json")


def quadratic_weighted_kappa(y1, y2, n_levels=5):
    y1 = np.asarray(y1, dtype=float)
    y2 = np.asarray(y2, dtype=float)
    if len(y1) == 0 or len(y2) == 0 or len(y1) != len(y2):
        return None
    b1 = np.clip(np.round(y1), 1, n_levels).astype(int)
    b2 = np.clip(np.round(y2), 1, n_levels).astype(int)
    n = len(b1)
    O = np.zeros((n_levels, n_levels), dtype=float)
    for a, b in zip(b1, b2):
        O[a-1, b-1] += 1
    row = O.sum(axis=1, keepdims=True)
    col = O.sum(axis=0, keepdims=True)
    E = row @ col / n
    idx = np.arange(n_levels)
    W = (idx[:, None] - idx[None, :]) ** 2 / float((n_levels - 1) ** 2)
    den = float(np.sum(W * E))
    if den == 0:
        return None
    return 1.0 - float(np.sum(W * O)) / den


def overall_from_block(block, judge_key, source):
    """Pull overall from a {key -> {test_model, seed_id, ...}} mapping
    for the given prompt variant.

    `source` is "no_cot" (looks at second_judges + claude_sonnet at top)
    or "cot" (looks at judges_cot)."""
    if source == "no_cot":
        if judge_key == "claude_sonnet":
            sc = block.get("claude_sonnet", {}).get("scores", {})
        else:
            jres = block.get("second_judges", {}).get(judge_key, {})
            if jres.get("error"):
                return None
            sc = jres.get("scores", {})
    else:
        jres = block.get("judges_cot", {}).get(judge_key, {})
        if jres.get("error"):
            return None
        sc = jres.get("scores", {})
    if sc.get("parse_error"):
        return None
    return sc.get("overall")


def build_per_session(no_cot_state, cot_state):
    """Return {key: {test_model, seed_id, no_cot: {judge: overall}, cot: {judge: overall}}}."""
    keys = sorted(set(no_cot_state["results"].keys()) | set(cot_state["results"].keys()))
    per = {}
    judge_keys = ["claude_sonnet", "gemini_3_1_pro", "gpt_latest"]
    for k in keys:
        nc_block = no_cot_state["results"].get(k, {})
        cot_block = cot_state["results"].get(k, {})
        meta = nc_block or cot_block
        per[k] = {
            "test_model": meta.get("test_model"),
            "seed_id":    meta.get("seed_id"),
            "no_cot":     {j: overall_from_block(nc_block,  j, "no_cot") for j in judge_keys},
            "cot":        {j: overall_from_block(cot_block, j, "cot")    for j in judge_keys},
        }
    return per, judge_keys


def main():
    if not NO_COT.exists():
        print(f"ERROR: {NO_COT} missing. Run rounds/r3/judge_round3_multi.py first.")
        return 1
    if not COT.exists():
        print(f"ERROR: {COT} missing. Run rounds/r3/judge_round3_cot.py first.")
        return 1

    no_cot_state = json.loads(NO_COT.read_text())
    cot_state    = json.loads(COT.read_text())
    per, judges = build_per_session(no_cot_state, cot_state)

    print(f"sessions in either set: {len(per)}")

    # --- 1. Per-judge per-session score deltas (paired) ---
    print()
    print("=" * 88)
    print("PER-JUDGE PAIRED COMPARISON (no-CoT vs CoT, same 60 sessions)")
    print("=" * 88)
    print(f'{"judge":<18}{"n_paired":<10}{"mean Δ(CoT-noCoT)":<22}'
          f'{"|Δ| mean":<11}{"Pearson r":<12}{"p":<8}')
    print("-" * 88)
    paired_results = {}
    for j in judges:
        a, b = [], []
        for sc in per.values():
            x = sc["no_cot"].get(j)
            y = sc["cot"].get(j)
            if x is not None and y is not None:
                a.append(x); b.append(y)
        if not a:
            print(f'{j:<18}{0:<10}  (no paired data)')
            paired_results[j] = {"n_paired": 0}
            continue
        a_arr = np.array(a); b_arr = np.array(b)
        diffs = b_arr - a_arr
        if len(a) >= 3:
            r, p = pearsonr(a_arr, b_arr)
        else:
            r, p = float("nan"), float("nan")
        print(f'{j:<18}{len(a):<10}{diffs.mean():+10.3f}            '
              f'{np.abs(diffs).mean():<11.3f}{r:+10.3f}  {p:.3f}')
        paired_results[j] = {
            "n_paired":     len(a),
            "mean_delta":   round(float(diffs.mean()), 4),
            "mean_abs_delta": round(float(np.abs(diffs).mean()), 4),
            "pearson_r":    round(float(r), 4) if not np.isnan(r) else None,
            "pearson_p":    round(float(p), 4) if not np.isnan(p) else None,
        }

    # --- 2. Inter-judge κ under each variant ---
    print()
    print("=" * 88)
    print("INTER-JUDGE WEIGHTED COHEN'S κ (no-CoT vs CoT)")
    print("=" * 88)
    print(f'{"pair":<48}{"no-CoT κ":<11}{"CoT κ":<11}{"Δκ":<10}')
    print("-" * 88)
    kappa_results = {}
    for i, ja in enumerate(judges):
        for jb in judges[i+1:]:
            xs_nc, ys_nc, xs_co, ys_co = [], [], [], []
            for sc in per.values():
                a_nc = sc["no_cot"].get(ja); b_nc = sc["no_cot"].get(jb)
                a_co = sc["cot"].get(ja);    b_co = sc["cot"].get(jb)
                if a_nc is not None and b_nc is not None:
                    xs_nc.append(a_nc); ys_nc.append(b_nc)
                if a_co is not None and b_co is not None:
                    xs_co.append(a_co); ys_co.append(b_co)
            k_nc = quadratic_weighted_kappa(xs_nc, ys_nc) if xs_nc else None
            k_co = quadratic_weighted_kappa(xs_co, ys_co) if xs_co else None
            delta = (k_co - k_nc) if (k_nc is not None and k_co is not None) else None
            label = f"{ja} ↔ {jb}"
            print(f'  {label:<46}'
                  f'{(k_nc if k_nc is not None else float("nan")):<11.3f}'
                  f'{(k_co if k_co is not None else float("nan")):<11.3f}'
                  f'{(delta if delta is not None else float("nan")):<+10.3f}')
            kappa_results[f"{ja}__vs__{jb}"] = {
                "n_no_cot":      len(xs_nc),
                "n_cot":         len(xs_co),
                "kappa_no_cot":  None if k_nc is None else round(k_nc, 4),
                "kappa_cot":     None if k_co is None else round(k_co, 4),
                "delta_kappa":   None if delta is None else round(delta, 4),
            }

    # --- 3. Per-judge ρ vs multi-turn arena under each variant ---
    print()
    print("=" * 88)
    print("PER-JUDGE ρ vs MULTI-TURN ARENA ELO  (per-model mean Likert from subsample)")
    print("=" * 88)
    rho_results = {}
    if MT_ARENA.exists():
        mt = json.loads(MT_ARENA.read_text())
        mt_elo = {e["model"]: e["elo_mean"] for e in mt["leaderboard"]}
        print(f'{"judge":<18}{"variant":<10}{"n_models":<10}{"ρ":<10}{"p":<8}')
        print("-" * 88)
        for j in judges:
            row = {}
            for variant in ("no_cot", "cot"):
                per_model = defaultdict(list)
                for sc in per.values():
                    v = sc[variant].get(j)
                    if v is not None:
                        per_model[sc["test_model"]].append(v)
                means = {m: float(np.mean(v)) for m, v in per_model.items() if v}
                common = sorted(m for m in means if m in mt_elo)
                if len(common) >= 3:
                    rho, p = spearmanr([means[m] for m in common],
                                       [mt_elo[m] for m in common])
                    print(f'  {j:<16}{variant:<10}{len(common):<10}'
                          f'{rho:+8.3f}  {p:.3f}')
                    row[variant] = {"n_models": len(common),
                                    "rho": round(float(rho), 4),
                                    "p": round(float(p), 4)}
                else:
                    print(f'  {j:<16}{variant:<10}{len(common):<10}  insufficient')
                    row[variant] = {"n_models": len(common), "rho": None, "p": None}
            rho_results[j] = row
    else:
        print("multiturn_arena_bayesian.json missing; per-judge ρ skipped")

    out = {
        "n_sessions_in_subsample": len(per),
        "judges": judges,
        "paired_score_comparison": paired_results,
        "inter_judge_kappa": kappa_results,
        "per_judge_rho_vs_mt_arena": rho_results,
    }
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nSaved: {OUT}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main() or 0)
