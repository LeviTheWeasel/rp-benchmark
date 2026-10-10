#!/usr/bin/env python3
"""Voter-clustered bootstrap CIs for the multi-turn arena Bradley-Terry rating.

Multiple votes from the same voter are not independent — they share a
common taste latent. Treating each vote as independent (as our default MCMC
analyzer does) underestimates posterior variance. This script provides a
sanity check using a frequentist voter-resampled bootstrap:

    for b in 1..B:
        sampled_voters = sample_with_replacement(voters, n=len(voters))
        boot_votes = flatten(by_voter[v] for v in sampled_voters)
        theta_b = MLE_fit(boot_votes)
    ELO_m       = 1500 + mean_b(theta_b[m])
    CI_95(ELO)  = [percentile(2.5), percentile(97.5)]

The bootstrap CIs widen relative to MCMC posterior CIs to the extent that
voter-level clustering matters; if voters are heterogeneous and votes are
nearly i.i.d. across voters, the two procedures give similar widths.

Also reports a bootstrap CI for the headline Spearman ρ between multi-turn
arena ELO and LLM-judge multi-turn Likert.
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import spearmanr


PRIOR_SIGMA = 300.0
SCALE = 400.0 / math.log(10)
B = 1000  # bootstrap iterations
SEED = 42


def neg_log_post(theta, votes_a, votes_b, votes_o, sigma):
    diff = (theta[votes_a] - theta[votes_b]) / SCALE
    ll = float(np.sum(votes_o * (-np.logaddexp(0.0, -diff))
                      + (1.0 - votes_o) * (-np.logaddexp(0.0, diff))))
    log_prior = -0.5 * float(np.sum((theta / sigma) ** 2))
    return -(ll + log_prior)


def neg_log_post_grad(theta, votes_a, votes_b, votes_o, sigma):
    n = len(theta)
    diff = (theta[votes_a] - theta[votes_b]) / SCALE
    p_a = 1.0 / (1.0 + np.exp(-diff))  # P(A wins)
    # d/d theta[a] log P(o) = (o - p_a) / SCALE per vote (if a is in pos A)
    grad = np.zeros(n)
    contrib = (votes_o - p_a) / SCALE
    np.add.at(grad,  votes_a,  contrib)
    np.add.at(grad,  votes_b, -contrib)
    grad -= theta / (sigma * sigma)  # prior gradient
    return -grad


def fit_bt(votes_a, votes_b, votes_o, n_models, sigma=PRIOR_SIGMA):
    theta0 = np.zeros(n_models)
    result = minimize(
        neg_log_post,
        theta0,
        args=(votes_a, votes_b, votes_o, sigma),
        jac=neg_log_post_grad,
        method="L-BFGS-B",
    )
    return result.x


def main():
    # The same scored set as the MCMC analyzer, so the two stay comparable.
    from arena.analyze_multiturn_arena import load_rows
    raw = load_rows()

    print(f"Loaded {len(raw)} multi-turn arena votes")
    # Resampling needs a voter per vote. The public round CSV has no voter
    # ids and the repo stores none raw (data/multiturn_arena_votes.README.md);
    # grouping on a missing id would make the whole file one "voter" and
    # print CIs that look valid. HMAC pseudonyms are enough.
    missing = sum(1 for v in raw if not v.get("voter_id"))
    if missing:
        raise SystemExit(
            f"{missing} of {len(raw)} votes carry no voter_id; the "
            "voter-clustered bootstrap cannot run. results/"
            "multiturn_arena_bootstrap.json still describes the 1,262-vote "
            "pull of 2026-06-04.")

    # Group votes by voter for cluster-resampling
    by_voter = defaultdict(list)
    for v in raw:
        by_voter[v["voter_id"]].append(v)
    voters = list(by_voter.keys())
    print(f"  unique voters: {len(voters)}")
    print(f"  median votes/voter: {np.median([len(vs) for vs in by_voter.values()]):.0f}")
    print(f"  max votes/voter:    {max(len(vs) for vs in by_voter.values())}")

    models = sorted(set(v["model_a"] for v in raw) | set(v["model_b"] for v in raw))
    m2i = {m: i for i, m in enumerate(models)}
    n_models = len(models)
    out_map = {"A": 1.0, "B": 0.0, "tie": 0.5}

    def to_arrays(votes):
        a = np.array([m2i[v["model_a"]] for v in votes], dtype=np.int64)
        b = np.array([m2i[v["model_b"]] for v in votes], dtype=np.int64)
        o = np.array([out_map[v["winner"]] for v in votes], dtype=np.float64)
        return a, b, o

    # --- original fit on full data ---
    va, vb, vo = to_arrays(raw)
    theta_orig = fit_bt(va, vb, vo, n_models)
    elo_orig = 1500 + theta_orig

    # --- bootstrap ---
    print(f"\nRunning {B} voter-clustered bootstrap iterations...")
    rng = np.random.default_rng(SEED)
    boot_thetas = np.zeros((B, n_models))
    for b in range(B):
        sampled = rng.choice(len(voters), size=len(voters), replace=True)
        boot_votes = []
        for idx in sampled:
            boot_votes.extend(by_voter[voters[idx]])
        ba, bb, bo = to_arrays(boot_votes)
        boot_thetas[b] = fit_bt(ba, bb, bo, n_models)
        if (b + 1) % 100 == 0:
            print(f"  iter {b+1}/{B}")

    boot_elo = 1500 + boot_thetas
    ci_low = np.percentile(boot_elo, 2.5, axis=0)
    ci_high = np.percentile(boot_elo, 97.5, axis=0)
    ci_width = ci_high - ci_low

    # --- compare to MCMC posterior ---
    mcmc = json.load(open("results/multiturn_arena_bayesian.json"))
    mcmc_by_model = {e["model"]: e for e in mcmc["leaderboard"]}

    print()
    print("=" * 105)
    print("MULTI-TURN ARENA — voter-clustered bootstrap (BT-MLE) vs MCMC posterior")
    print("=" * 105)
    header = f'{"model":<26}{"ELO_MLE":<10}{"boot 95% CI":<22}{"width":<8}'\
             f'{"ELO_MCMC":<10}{"MCMC 95% CI":<22}{"width":<7}'
    print(header)
    print("-" * 105)

    rows = []
    for i, m in enumerate(models):
        b_ci = f'[{ci_low[i]:.0f}, {ci_high[i]:.0f}]'
        bw = ci_width[i]
        mc = mcmc_by_model.get(m, {})
        mc_ci = f'[{mc.get("ci_low_95", 0):.0f}, {mc.get("ci_high_95", 0):.0f}]'
        mc_w = mc.get("ci_high_95", 0) - mc.get("ci_low_95", 0)
        print(f'{m:<26}{elo_orig[i]:<10.0f}{b_ci:<22}{bw:<8.0f}'
              f'{mc.get("elo_mean", 0):<10.0f}{mc_ci:<22}{mc_w:<7.0f}')
        rows.append({
            "model": m,
            "elo_mle":          round(float(elo_orig[i]), 1),
            "boot_ci_low_95":   round(float(ci_low[i]), 1),
            "boot_ci_high_95":  round(float(ci_high[i]), 1),
            "boot_ci_width_95": round(float(ci_width[i]), 1),
            "elo_mcmc_mean":    round(float(mc.get("elo_mean", 0) or 0), 1),
            "mcmc_ci_low_95":   round(float(mc.get("ci_low_95", 0) or 0), 1),
            "mcmc_ci_high_95":  round(float(mc.get("ci_high_95", 0) or 0), 1),
            "mcmc_ci_width_95": round(float(mc_w), 1),
        })

    print()
    print(f"Median bootstrap CI width: {np.median(ci_width):.0f} ELO")
    print(f"Median MCMC CI width:      "
          f"{np.median([mcmc_by_model[m]['ci_high_95'] - mcmc_by_model[m]['ci_low_95'] for m in models]):.0f} ELO")

    # --- bootstrap CI for the headline rho ---
    profiles = json.load(open("results/model_profiles.json"))
    likert = {m: (profiles.get(m, {}).get("multiturn_llm_judge") or {}).get("overall_mean")
              for m in models}
    lk_models = [m for m in models if likert[m] is not None]
    lk_idx = [m2i[m] for m in lk_models]
    lk_vals = np.array([likert[m] for m in lk_models])

    rhos = np.zeros(B)
    for b in range(B):
        elo_b = boot_elo[b, lk_idx]
        rho, _ = spearmanr(elo_b, lk_vals)
        rhos[b] = rho
    rho_orig, p_orig = spearmanr(elo_orig[lk_idx], lk_vals)
    rho_low, rho_high = np.percentile(rhos, [2.5, 97.5])
    print()
    print(f"Headline rho (multi-turn arena ↔ LLM-judge Likert), n={len(lk_models)}:")
    print(f"  point estimate (MLE):       rho = {rho_orig:+.3f}  (p = {p_orig:.3f})")
    print(f"  bootstrap mean:             rho = {rhos.mean():+.3f}")
    print(f"  bootstrap 95% CI:           [{rho_low:+.3f}, {rho_high:+.3f}]")
    p_above_zero = float(np.mean(rhos > 0))
    print(f"  fraction of bootstraps with rho > 0: {p_above_zero:.3f}")

    out = {
        "method": "voter-clustered bootstrap of Bradley-Terry MLE",
        "n_iterations": B,
        "seed": SEED,
        "prior_sigma": PRIOR_SIGMA,
        "n_voters": len(voters),
        "n_votes": len(raw),
        "median_bootstrap_ci_width_elo": round(float(np.median(ci_width)), 1),
        "median_mcmc_ci_width_elo":     round(float(np.median(
            [mcmc_by_model[m]['ci_high_95'] - mcmc_by_model[m]['ci_low_95'] for m in models]
        )), 1),
        "rho_vs_llm_judge_likert": {
            "n_models": len(lk_models),
            "point_estimate": round(float(rho_orig), 4),
            "p_value":         round(float(p_orig), 4),
            "bootstrap_mean":  round(float(rhos.mean()), 4),
            "bootstrap_ci_low_95":  round(float(rho_low), 4),
            "bootstrap_ci_high_95": round(float(rho_high), 4),
            "fraction_bootstraps_above_zero": p_above_zero,
        },
        "per_model": rows,
    }
    out_path = Path("results/multiturn_arena_bootstrap.json")
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
