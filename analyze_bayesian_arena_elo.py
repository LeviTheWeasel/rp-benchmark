#!/usr/bin/env python3
"""Bayesian ELO with credible intervals from community arena votes.

Bradley-Terry latent-skill model with weakly-informative prior, sampled
via Metropolis-Hastings. Pure NumPy — runs in ~30-60s on a Mac mini.

Model:
    θ_m ~ N(0, σ²)
    P(i beats j) = sigmoid((θ_i - θ_j) / scale)

Output ELO = 1500 + θ_m (standard ELO scale; 400-point gap = 10× odds).

The 95% credible interval reflects ALL uncertainty (prior + finite votes).
It's wider than the frequentist `±stability` because that only captured
shuffle variance, not vote-count uncertainty.

Usage:
    python3 analyze_bayesian_arena_elo.py
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

PRIOR_SIGMA = 300.0
SCALE = 400.0 / math.log(10)
N_CHAINS = 4
N_BURNIN = 3000
N_SAMPLES = 12000
PROPOSAL_STEP = 50.0
AMBIGUOUS_CATCHES = {"catch_user_hijack_cafe"}


def load_votes() -> list[tuple[str, str, str]]:
    parquet = Path("hf_dataset/community_votes/train.parquet")
    if parquet.exists():
        try:
            import pyarrow.parquet as pq
            df = pq.read_table(parquet).to_pandas()
        except ImportError:
            df = None
    else:
        df = None

    if df is None:
        votes = []
        with open("web/data/votes.jsonl") as f:
            for line in f:
                if not line.strip():
                    continue
                v = json.loads(line)
                if v.get("mode") != "arena" or v.get("is_catch"):
                    continue
                votes.append((v["model_a"], v["model_b"], v["winner"]))
        return votes

    catches = df[df["is_catch"] == True]
    per_voter = defaultdict(lambda: [0, 0])
    for _, row in catches.iterrows():
        if row["scenario_id"] in AMBIGUOUS_CATCHES:
            continue
        v = row["voter_id"]
        per_voter[v][0] += 1
        if row["catch_correct"]:
            per_voter[v][1] += 1
    suspects = {v for v, (t, c) in per_voter.items() if t >= 2 and c / t < 0.5}
    print(f"Suspect voters excluded: {len(suspects)}")

    real = df[(df["is_catch"] == False) & (~df["voter_id"].isin(suspects))]
    return [(r["model_a"], r["model_b"], r["winner"]) for _, r in real.iterrows()]


def run_chain(theta_init, votes_a, votes_b, votes_outcome, n_models, model_to_idx, seed):
    """Vectorized Metropolis-Hastings.

    theta_init: (n_models,) initial skills
    votes_a, votes_b: (n_votes,) int arrays of model indices
    votes_outcome: (n_votes,) array of {1.0, 0.0, 0.5} (A wins / B wins / tie)
    """
    rng = np.random.default_rng(seed)
    theta = theta_init.copy()
    n_steps = N_BURNIN + N_SAMPLES

    # Precompute: for each model, which votes involve it
    # vote_lookup[m] = (indices_where_a_is_m, indices_where_b_is_m)
    vote_lookup = [
        (np.where(votes_a == m)[0], np.where(votes_b == m)[0])
        for m in range(n_models)
    ]

    def model_log_likelihood(m, current_theta):
        """Log-likelihood contribution of model m's votes."""
        a_idx, b_idx = vote_lookup[m]
        ll = 0.0
        # Votes where m is in position A
        if len(a_idx) > 0:
            diff = (current_theta[m] - current_theta[votes_b[a_idx]]) / SCALE
            outcomes = votes_outcome[a_idx]
            # Log P(observed outcome) = outcome*log(σ(d)) + (1-outcome)*log(σ(-d))
            ll += np.sum(outcomes * (-np.logaddexp(0, -diff)) + (1 - outcomes) * (-np.logaddexp(0, diff)))
        if len(b_idx) > 0:
            diff = (current_theta[votes_a[b_idx]] - current_theta[m]) / SCALE
            outcomes = votes_outcome[b_idx]
            ll += np.sum(outcomes * (-np.logaddexp(0, -diff)) + (1 - outcomes) * (-np.logaddexp(0, diff)))
        return ll

    samples = np.zeros((N_SAMPLES, n_models))
    n_accept = 0

    # Pre-compute per-model log-likelihoods so we only update the affected one
    model_lls = np.array([model_log_likelihood(m, theta) for m in range(n_models)])
    # Each vote contributes to TWO models' LLs, so total LL = sum / 2... no wait,
    # the likelihood per vote depends on θ_a − θ_b. When we change θ_m, only votes
    # involving m have their LL changed. So model_log_likelihood(m) gives the SUM
    # of LLs of all votes involving m. When we change m, the delta is:
    #   new_ll_for_m_votes - old_ll_for_m_votes
    # That's a complete and minimal update.

    log_prior = -0.5 * np.sum((theta / PRIOR_SIGMA) ** 2)

    for step in range(n_steps):
        m = rng.integers(0, n_models)
        proposal = rng.normal(0, PROPOSAL_STEP)
        old_val = theta[m]
        old_ll_m = model_lls[m]
        old_prior_m = -0.5 * (old_val / PRIOR_SIGMA) ** 2

        theta[m] = old_val + proposal
        new_ll_m = model_log_likelihood(m, theta)
        new_prior_m = -0.5 * (theta[m] / PRIOR_SIGMA) ** 2

        log_accept = (new_ll_m - old_ll_m) + (new_prior_m - old_prior_m)
        if math.log(rng.random()) < log_accept:
            model_lls[m] = new_ll_m
            log_prior += (new_prior_m - old_prior_m)
            n_accept += 1
        else:
            theta[m] = old_val

        if step >= N_BURNIN:
            samples[step - N_BURNIN] = theta

    return samples, n_accept / n_steps


def main():
    votes = load_votes()
    print(f"Clean arena votes: {len(votes)}")
    if not votes:
        return

    models = sorted(set(a for a, _, _ in votes) | set(b for _, b, _ in votes))
    model_to_idx = {m: i for i, m in enumerate(models)}
    n_models = len(models)
    print(f"Models in pool: {n_models}")

    # Convert to numpy arrays
    votes_a = np.array([model_to_idx[a] for a, _, _ in votes])
    votes_b = np.array([model_to_idx[b] for _, b, _ in votes])
    outcome_map = {"A": 1.0, "B": 0.0, "tie": 0.5}
    votes_outcome = np.array([outcome_map.get(w, 0.5) for _, _, w in votes])
    print()

    print(f"Running {N_CHAINS} chains × {N_BURNIN + N_SAMPLES} steps...")
    all_samples = []
    for c in range(N_CHAINS):
        theta0 = np.zeros(n_models)
        samples, accept = run_chain(theta0, votes_a, votes_b, votes_outcome, n_models, model_to_idx, c)
        print(f"  chain {c+1}: {accept:.2%} accept")
        all_samples.append(samples)

    all_samples = np.concatenate(all_samples, axis=0)  # (n_chains × N_SAMPLES, n_models)
    print(f"  combined: {len(all_samples)} posterior samples")

    # Per-model summary
    summary = {}
    for i, m in enumerate(models):
        elo_samples = 1500 + all_samples[:, i]
        summary[m] = {
            "elo": float(elo_samples.mean()),
            "std": float(elo_samples.std()),
            "ci_low": float(np.percentile(elo_samples, 2.5)),
            "ci_high": float(np.percentile(elo_samples, 97.5)),
        }
        summary[m]["ci_width"] = summary[m]["ci_high"] - summary[m]["ci_low"]

    sorted_models = sorted(summary.items(), key=lambda x: -x[1]["elo"])
    print()
    print(f"Posterior summary ({len(all_samples)} samples)")
    print("=" * 80)
    print(f'{"Rank":<5}{"Model":<28}{"ELO":<8}{"std":<7}{"95% credible":<22}{"width":<8}')
    print("-" * 80)
    for rank, (m, s) in enumerate(sorted_models, 1):
        ci = f'[{s["ci_low"]:.0f}, {s["ci_high"]:.0f}]'
        print(f'#{rank:<4}{m:<28}{s["elo"]:<8.0f}{s["std"]:<7.1f}{ci:<22}{s["ci_width"]:<8.0f}')

    # Compare to frequentist
    freq_path = Path("results/community_arena_2000.json")
    if freq_path.exists():
        freq = json.load(open(freq_path))
        freq_elo = {e["model"]: e["elo"] for e in freq["leaderboard"]}
        print()
        print("Bayesian vs frequentist (100-shuffle):")
        print("-" * 60)
        print(f'{"Model":<28}{"Bayesian":<12}{"Freq":<10}{"Δ":<8}')
        for m, s in sorted_models:
            if m in freq_elo:
                d = s["elo"] - freq_elo[m]
                print(f'  {m:<26}{s["elo"]:<12.0f}{freq_elo[m]:<10.0f}{d:+.0f}')

    out = {
        "method": "Bradley-Terry with Metropolis-Hastings",
        "prior": f"N(0, {PRIOR_SIGMA}²)",
        "scale": "ELO (400 = 10× odds)",
        "n_chains": N_CHAINS,
        "n_samples": int(len(all_samples)),
        "n_votes": len(votes),
        "leaderboard": [
            {
                "rank": rank,
                "model": m,
                "elo_mean": round(s["elo"], 1),
                "elo_std": round(s["std"], 1),
                "ci_low_95": round(s["ci_low"], 1),
                "ci_high_95": round(s["ci_high"], 1),
                "ci_width_95": round(s["ci_width"], 1),
            }
            for rank, (m, s) in enumerate(sorted_models, 1)
        ],
    }
    out_path = Path("results/community_arena_bayesian.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
