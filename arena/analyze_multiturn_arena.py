#!/usr/bin/env python3
"""Bayesian ELO for the human multi-turn arena.

The multi-turn arena lets users vote on full 12-turn dialogues between two
models on the same adversarial seed. Different judging mode than the
single-message community arena:
  - Voters see entire conversations, not single replies → judges narrative arc
  - Same seeds as the LLM-judge multiturn pipeline → directly comparable
  - Smaller N — coverage is per-pair sparse, CIs will be wide

Input: data/multiturn_arena_votes.jsonl, the round-2 close as published on
plotlightstudios.com (arena/refresh_multiturn_arena_votes.py writes it; provenance
in data/multiturn_arena_votes.README.md).

Outputs:
  - results/multiturn_arena_bayesian.json     — per-model posterior ELO
  - prints comparison table vs LLM-judge multiturn + community arena
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

VOTES_FILE = Path("data/multiturn_arena_votes.jsonl")

# Kept in the votes file, not scored. These 30 ballots were cast on
# arena.l3vi4th4n.ai after its 507 round-2 votes were imported into
# plotlightstudios.com (2026-04-30), so they never reached the round-2 tally
# the site closed on 2026-06-13. Scoring them would publish a ranking that is
# not the round's. See data/multiturn_arena_votes.README.md.
UNSCORED_SOURCES = frozenset({"arena_l3vi4th4n_only"})

PRIOR_SIGMA = 300.0
SCALE = 400.0 / math.log(10)
N_CHAINS = 4
N_BURNIN = 3000
N_SAMPLES = 12000
PROPOSAL_STEP = 50.0


def load_rows():
    """Every scored vote record, as stored. Rows from UNSCORED_SOURCES and
    rows missing a side or a winner are dropped here, once, so the vote, pair
    and voter counts all describe the same set."""
    rows = []
    with open(VOTES_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            v = json.loads(line)
            if v.get("source") in UNSCORED_SOURCES:
                continue
            if not v.get("model_a") or not v.get("model_b") or not v.get("winner"):
                continue
            rows.append(v)
    return rows


def load_votes():
    return [(v["model_a"], v["model_b"], v["winner"]) for v in load_rows()]


def _spearmanr(x, y):
    """scipy.stats.spearmanr's rho and two-sided t-test p, for when scipy is
    not installed. Ties get average ranks, as in scipy."""
    def ranks(v):
        v = np.asarray(v, dtype=float)
        r = np.empty(len(v))
        r[np.argsort(v, kind="mergesort")] = np.arange(1, len(v) + 1)
        for val in np.unique(v):
            k = v == val
            r[k] = r[k].mean()
        return r
    rho = float(np.corrcoef(ranks(x), ranks(y))[0, 1])
    df = len(x) - 2
    if abs(rho) >= 1.0:
        return rho, 0.0
    t2 = rho * rho * df / (1.0 - rho * rho)
    return rho, _betainc(df / 2.0, 0.5, df / (df + t2))


def _betainc(a, b, x):
    """Regularized incomplete beta I_x(a, b) by continued fraction (Lentz)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _betainc(b, a, 1.0 - x)
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log1p(-x)) / a
    tiny = 1e-300
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / (d if abs(d) > tiny else tiny)
    f = d
    for m in range(1, 300):
        for num in (m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m)),
                    -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))):
            d = 1.0 + num * d
            d = 1.0 / (d if abs(d) > tiny else tiny)
            c = 1.0 + num / c
            c = c if abs(c) > tiny else tiny
            f *= c * d
        if abs(c * d - 1.0) < 1e-15:
            break
    return front * f


def run_chain(theta_init, votes_a, votes_b, votes_outcome, n_models, seed):
    rng = np.random.default_rng(seed)
    theta = theta_init.copy()
    n_steps = N_BURNIN + N_SAMPLES

    vote_lookup = [
        (np.where(votes_a == m)[0], np.where(votes_b == m)[0])
        for m in range(n_models)
    ]

    def model_ll(m, current_theta):
        a_idx, b_idx = vote_lookup[m]
        ll = 0.0
        if len(a_idx) > 0:
            diff = (current_theta[m] - current_theta[votes_b[a_idx]]) / SCALE
            outcomes = votes_outcome[a_idx]
            ll += np.sum(outcomes * (-np.logaddexp(0, -diff))
                         + (1 - outcomes) * (-np.logaddexp(0, diff)))
        if len(b_idx) > 0:
            diff = (current_theta[votes_a[b_idx]] - current_theta[m]) / SCALE
            outcomes = votes_outcome[b_idx]
            ll += np.sum(outcomes * (-np.logaddexp(0, -diff))
                         + (1 - outcomes) * (-np.logaddexp(0, diff)))
        return ll

    samples = np.zeros((N_SAMPLES, n_models))
    n_accept = 0
    model_lls = np.array([model_ll(m, theta) for m in range(n_models)])

    for step in range(n_steps):
        m = rng.integers(0, n_models)
        old_val = theta[m]
        proposal = rng.normal(0, PROPOSAL_STEP)
        old_prior = -0.5 * (old_val / PRIOR_SIGMA) ** 2

        theta[m] = old_val + proposal
        new_ll = model_ll(m, theta)
        new_prior = -0.5 * (theta[m] / PRIOR_SIGMA) ** 2

        log_accept = (new_ll - model_lls[m]) + (new_prior - old_prior)
        if math.log(rng.random()) < log_accept:
            model_lls[m] = new_ll
            n_accept += 1
        else:
            theta[m] = old_val

        if step >= N_BURNIN:
            samples[step - N_BURNIN] = theta

    return samples, n_accept / n_steps


def main():
    rows = load_rows()
    votes = [(v["model_a"], v["model_b"], v["winner"]) for v in rows]
    print(f"Multi-turn arena votes: {len(votes)}")
    with open(VOTES_FILE) as f:
        n_unscored = sum(1 for line in f if line.strip()
                         and json.loads(line).get("source") in UNSCORED_SOURCES)
    if n_unscored:
        print(f"  not scored:    {n_unscored} (source in {sorted(UNSCORED_SOURCES)})")

    pairs = defaultdict(int)
    for v in rows:
        pairs[tuple(sorted([v["model_a"], v["model_b"]]))] += 1
    # The public round CSV carries no voter ids, and the repo stores none (or
    # only HMAC pseudonyms). A count over a partial id column would be a
    # wrong number, so it is reported only when every scored vote has one.
    ids = [v.get("voter_id") for v in rows]
    n_voters = len(set(ids)) if ids and all(ids) else None
    print(f"  unique voters: {n_voters if n_voters is not None else 'unknown (no voter ids in the votes file)'}")
    print(f"  unique pairs:  {len(pairs)}")

    models = sorted(set(a for a, _, _ in votes) | set(b for _, b, _ in votes))
    model_to_idx = {m: i for i, m in enumerate(models)}
    n_models = len(models)
    print(f"  models:        {n_models}")

    votes_a = np.array([model_to_idx[a] for a, _, _ in votes])
    votes_b = np.array([model_to_idx[b] for _, b, _ in votes])
    outcome_map = {"A": 1.0, "B": 0.0, "tie": 0.5}
    votes_outcome = np.array([outcome_map.get(w, 0.5) for _, _, w in votes])

    print()
    print(f"Running {N_CHAINS} chains × {N_BURNIN + N_SAMPLES} MCMC steps...")
    all_samples = []
    for c in range(N_CHAINS):
        theta0 = np.zeros(n_models)
        samples, accept = run_chain(theta0, votes_a, votes_b, votes_outcome, n_models, c)
        print(f"  chain {c+1}: {accept:.1%} accept")
        all_samples.append(samples)

    all_samples = np.concatenate(all_samples, axis=0)

    # Per-model summary
    summary = {}
    for i, m in enumerate(models):
        elo = 1500 + all_samples[:, i]
        summary[m] = {
            "elo_mean": float(elo.mean()),
            "elo_std":  float(elo.std()),
            "ci_low_95": float(np.percentile(elo, 2.5)),
            "ci_high_95": float(np.percentile(elo, 97.5)),
        }

    # Vote-count exposure
    exposure = defaultdict(int)
    for a, b, _ in votes:
        exposure[a] += 1
        exposure[b] += 1
    for m, s in summary.items():
        s["n_votes"] = exposure[m]

    sorted_models = sorted(summary.items(), key=lambda x: -x[1]["elo_mean"])

    # Load comparison data
    profiles = json.loads(Path("results/model_profiles.json").read_text())
    bayes_arena = {e["model"]: e for e in json.loads(
        Path("results/community_arena_bayesian.json").read_text())["leaderboard"]}

    print()
    print("=" * 105)
    print("MULTI-TURN ARENA — POSTERIOR ELO")
    print("=" * 105)
    print(f'{"Rank":<5}{"Model":<26}{"MT-arena ELO":<14}{"95% CI":<22}{"n":<6}'
          f'{"LLM Likert":<12}{"Comm-arena ELO":<14}')
    print("-" * 105)
    for rank, (m, s) in enumerate(sorted_models, 1):
        ci = f'[{s["ci_low_95"]:.0f}, {s["ci_high_95"]:.0f}]'
        likert = (profiles.get(m, {}).get("multiturn_llm_judge") or {}).get("overall_mean")
        ca = bayes_arena.get(m, {}).get("elo_mean")
        print(f'#{rank:<4}{m:<26}{s["elo_mean"]:<14.0f}{ci:<22}{s["n_votes"]:<6}'
              f'{(likert or 0):<12.2f}{(ca or 0):<14.0f}')

    print()
    print("Reading the table:")
    print("- MT-arena ELO: Bayesian Bradley-Terry from human votes on full dialogues")
    print("- 95% CI: posterior credible interval (small N → wide intervals)")
    print("- n: vote exposures (each vote counts for both models)")
    print("- LLM Likert: Sonnet 4 holistic judge mean (1-5) on the same multi-turn sessions")
    print("- Comm-arena ELO: single-message community arena Bayesian ELO (different judging mode)")

    # Output
    leaderboard = []
    for rank, (m, s) in enumerate(sorted_models, 1):
        leaderboard.append({"rank": rank, "model": m, **{k: round(v, 1) if isinstance(v, float) else v for k, v in s.items()}})

    # Cross-method correlations
    # scipy is optional: without it the same rho and t-test p come from
    # _spearmanr, instead of the correlations silently becoming null.
    try:
        from scipy.stats import spearmanr
    except ImportError:
        spearmanr = _spearmanr
    mt_elo = {m: s["elo_mean"] for m, s in summary.items()}
    ca_elo = {m: bayes_arena[m]["elo_mean"] for m in mt_elo if m in bayes_arena}
    lk = {m: (profiles.get(m, {}).get("multiturn_llm_judge") or {}).get("overall_mean")
          for m in mt_elo}
    common_ca = sorted(set(mt_elo) & set(ca_elo))
    common_lk = sorted(m for m in mt_elo if lk.get(m) is not None)
    rho_ca, p_ca = spearmanr([mt_elo[m] for m in common_ca],
                             [ca_elo[m] for m in common_ca])
    rho_lk, p_lk = spearmanr([mt_elo[m] for m in common_lk],
                             [lk[m] for m in common_lk])
    correlations = {
        "vs_community_arena_singlemsg": {"rho": float(rho_ca), "p": float(p_ca), "n": len(common_ca)},
        "vs_llm_judge_multiturn": {"rho": float(rho_lk), "p": float(p_lk), "n": len(common_lk)},
    }
    print()
    print(f"Cross-method Spearman correlations:")
    print(f"  vs community-arena (single-message):  ρ = {rho_ca:+.3f}  (p={p_ca:.3f}, n={len(common_ca)})")
    print(f"  vs LLM-judge multiturn (Likert):      ρ = {rho_lk:+.3f}  (p={p_lk:.3f}, n={len(common_lk)})")

    # Position-bias diagnostic
    a_wins = sum(1 for _, _, w in votes if w == "A")
    b_wins = sum(1 for _, _, w in votes if w == "B")
    ties = sum(1 for _, _, w in votes if w == "tie")
    print()
    print(f"Position bias check: A={a_wins}, B={b_wins}, tie={ties}  →  B-share of decided = {b_wins/(a_wins+b_wins):.3f}")

    out = {
        "method": "Bayesian Bradley-Terry MCMC (Metropolis-Hastings)",
        "prior_sigma": PRIOR_SIGMA,
        "scale": SCALE,
        "n_chains": N_CHAINS,
        "n_samples_per_chain": N_SAMPLES,
        "n_votes": len(votes),
        "n_voters": n_voters,
        "n_votes_not_scored": n_unscored,
        "n_pairs": len(pairs),
        "winner_distribution": {"A": a_wins, "B": b_wins, "tie": ties},
        "correlations": correlations,
        "leaderboard": leaderboard,
    }
    Path("results").mkdir(exist_ok=True)
    out_path = Path("results/multiturn_arena_bayesian.json")
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
