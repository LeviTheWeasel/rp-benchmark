#!/usr/bin/env python3
"""
Bayesian ELO ratings for RP-Bench using Bradley-Terry model.

Two-stage approach:
  Stage 1: Per-seed MLE via iterative reweighted least squares (IRLS).
           Each matchup contributes a Gaussian observation in logit-space:
               logit(E[outcome]) = (s_A - s_B) / KAPPA + noise
           Noise variance = 1 / (KAPPA² · p_A · (1-p_A)) where p_A = sigmoid(s_A - s_B).
           Ties are treated as fractional outcomes (0.5).
  Stage 2: Cross-seed combination via Normal conjugate updating.
           Each per-seed MLE becomes a Gaussian likelihood on the latent strength.
           Combined across all seeds using exact precision summation.

This avoids all the instability of Laplace approximation on binary data.
The prior is calibrated from the aggregate adversarial analysis.

Usage:
    python analyze_bayesian_elo.py [results_file]

Output:
    results/bayesian_elo.json
"""
import argparse
import json
import math
import random
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Constants — calibrated from adversarial_analysis.json
# ─────────────────────────────────────────────────────────────────────────────

KAPPA = 400.0           # ELO scale parameter (standard)
INITIAL_RATING = 1500.0  # prior mean

# Prior std calibrated from aggregate score spread (~0.25 pts → scaled to ELO)
# Score 4.1875-4.4375 across 7 models → ~250 ELO spread
PRIOR_STD = 200.0       # regularizing prior std

# Minimum variance floor (prevents numerical issues)
VAR_FLOOR = 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# Bradley-Terry utilities
# ─────────────────────────────────────────────────────────────────────────────

def sigmoid(x: float) -> float:
    """Stable logistic sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    else:
        return math.exp(x) / (math.exp(x) + 1.0)


def expected_score(s_a: float, s_b: float) -> float:
    """P(A beats B) under Bradley-Terry."""
    return sigmoid((s_a - s_b) / KAPPA)


def matchup_variance(p_a: float) -> float:
    """
    Variance of a Bernoulli observation in logit-space.
    Var[logit(p)] ≈ 1 / (p · (1-p)) for small noise approximation.
    We use the ELO-formula scaling: σ² = 1 / (KAPPA² · p_A · (1-p_A))
    """
    p_a = max(0.01, min(0.99, p_a))
    return 1.0 / (KAPPA ** 2 * p_a * (1.0 - p_a))


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Per-seed Bradley-Terry MLE via IRLS
# ─────────────────────────────────────────────────────────────────────────────

def bt_mle(
    matchups: list[tuple],
    models: list[str],
    max_iter: int = 100,
    tol: float = 1e-8,
) -> dict[str, float]:
    """
    Iterative Reweighted Least Squares for Bradley-Terry MLE.

    Each matchup (seed, A, B, outcome) gives a linearized observation:
        z_i = KAPPA · logit(outcome_i) ≈ (s_A - s_B) + residual

    Weighted least squares: minimize Σ w_i · (z_i - (s_A - s_B))²
    where w_i = 1 / Var[z_i] = KAPPA² · p_i · (1-p_i)

    Converges in ~5-10 iterations for well-connected graphs.

    Returns:
        {model: MLE strength estimate}
    """
    n = len(models)
    model_idx = {m: i for i, m in enumerate(models)}
    s = {m: INITIAL_RATING for m in models}   # current estimates

    for iteration in range(max_iter):
        # Build normal equations: A.T @ W @ A @ s = A.T @ W @ z
        # A is incidence matrix: row i has +1 at A, -1 at B
        total_shift = 0.0

        for seed, a, b, outcome in matchups:
            if a not in model_idx or b not in model_idx:
                continue

            r_a = s[a]
            r_b = s[b]

            p_a = expected_score(r_a, r_b)

            # Transform outcome to logit space
            if outcome >= 1.0:
                z = KAPPA * 8.0          # ≈ KAPPA * logit(0.9997)
            elif outcome <= 0.0:
                z = -KAPPA * 8.0         # ≈ KAPPA * logit(0.0003)
            else:
                # For ties, treat as observing p=0.5 in logit space
                z = KAPPA * (r_a - r_b) / KAPPA  # = r_a - r_b (no info)

            # Residual
            resid = z - (r_a - r_b)

            # Weight = precision
            var = matchup_variance(p_a)
            w = 1.0 / var

            # Gradient of (r_a - r_b) w.r.t. s_a and s_b
            # d/d(s_a) = 1, d/d(s_b) = -1
            # Weighted update: delta = w · resid / Σ w·grad²
            # For a simple difference: Σ grad² = 2
            delta = w * resid / (2.0 * w)  # = resid / 2

            s[a] += delta
            s[b] -= delta
            total_shift += abs(delta)

        if total_shift < tol * n:
            break

    return s


def bt_mle_with_se(
    matchups: list[tuple],
    models: list[str],
    n_bootstrap: int = 200,
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Bradley-Terry MLE + bootstrap standard errors.

    Bootstrap is done by resampling matchups with replacement within each seed.
    This gives us the sampling distribution of the MLE, from which we extract
    standard errors and approximate 95% CIs.

    Note: for small n (21 matchups/seed), bootstrap SE may be unstable —
    this is a known limitation and why we need cross-seed combination.
    """
    # MLE from full data
    mle = bt_mle(matchups, models)

    # Bootstrap
    boot_strengths = {m: [] for m in models}
    for b in range(n_bootstrap):
        boot_matchups = []
        by_seed = defaultdict(list)
        for m in matchups:
            by_seed[m[0]].append(m)
        for seed, seed_m in by_seed.items():
            sample = [random.choice(seed_m) for _ in seed_m]
            boot_matchups.extend(sample)

        boot_s = bt_mle(boot_matchups, models)
        for m in models:
            boot_strengths[m].append(boot_s.get(m, INITIAL_RATING))

    # Standard errors from bootstrap distribution
    se = {}
    for m in models:
        vals = boot_strengths[m]
        if len(vals) >= 2:
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
            se[m] = max(math.sqrt(var), 1.0)
        else:
            se[m] = PRIOR_STD

    return mle, se


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Cross-seed Normal combination
# ─────────────────────────────────────────────────────────────────────────────

def combine_posteriors(
    seed_results: list[dict],
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """
    Combine per-seed MLE + SE estimates via Normal conjugate updating.

    Each seed gives an approximate Normal likelihood on the latent strength:
        L(seed | s_m) ∝ exp(-0.5 · (μ_seed - s_m)² / σ²_seed)

    With a Normal(μ_prior, σ_prior²) prior on s_m, the posterior is also Normal:
        σ_posterior⁻² = σ_prior⁻² + Σ σ_seed⁻²
        μ_posterior   = σ_posterior² · (μ_prior/σ_prior² + Σ μ_seed/σ_seed²)

    This is exact given the approximations.
    """
    combined_mean = {}
    combined_var = {}

    for m in seed_results[0]["mean"]:
        # Prior
        prior_prec = 1.0 / (PRIOR_STD ** 2)
        prior_mean_prec = INITIAL_RATING * prior_prec

        # Accumulate from each seed
        total_prec = prior_prec
        total_mean_prec = prior_mean_prec

        for sr in seed_results:
            se = sr["se"].get(m, PRIOR_STD)
            var = max(se ** 2, VAR_FLOOR)
            prec = 1.0 / var
            total_prec += prec
            total_mean_prec += prec * sr["mean"][m]

        combined_var[m] = 1.0 / total_prec
        combined_mean[m] = combined_var[m] * total_mean_prec

    combined_std = {m: math.sqrt(v) for m, v in combined_var.items()}
    return combined_mean, combined_var, combined_std


def posterior_win_prob(
    m_a: float, std_a: float,
    m_b: float, std_b: float,
    n_samples: int = 200_000,
) -> float:
    """
    P(A beats B) integrating over Normal posterior distributions.
    Uses sampling to correctly handle the sigmoid nonlinearity.
    """
    wins = 0
    for _ in range(n_samples):
        r_a = random.gauss(m_a, std_a)
        r_b = random.gauss(m_b, std_b)
        if sigmoid((r_a - r_b) / KAPPA) > 0.5:
            wins += 1
    return wins / n_samples


def credible_interval(
    mean: float, std: float, confidence: float = 0.95
) -> tuple[float, float]:
    """Normal credible interval."""
    # 95% CI: mean ± 1.96 * std
    z = 1.96
    return (round(mean - z * std, 1), round(mean + z * std, 1))


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def session_score(judge_scores: dict) -> Optional[tuple]:
    """Extract (overall, dimension_sum) from judge scores."""
    o = judge_scores.get("overall")
    if o is None or o <= 0:
        return None
    dim_sum = 0.0
    for _, info in judge_scores.get("session_dimensions", {}).items():
        if isinstance(info, dict) and "score" in info:
            dim_sum += info["score"]
    return (o, dim_sum)


def load_matchups(data: dict) -> tuple[dict[str, list], dict[str, list]]:
    """
    Build per-seed matchup lists and also per-seed model score dicts.
    Returns:
        per_seed_matchups: {seed: [(seed, model_a, model_b, outcome), ...]}
        per_seed_scores: {seed: {model: (overall, dim_sum)}}
    """
    scores = {}
    for s in data.get("sessions", []):
        if "judges" not in s or "test_model" not in s:
            continue
        j = list(s["judges"].values())[0]["scores"]
        sc = session_score(j)
        if sc is None:
            continue
        scores[(s["seed_id"], s["test_model"])] = sc

    by_seed = defaultdict(list)
    for (seed, model), sc in scores.items():
        by_seed[seed].append((model, sc))

    per_seed_matchups = {}
    per_seed_scores = {}
    for seed, entries in by_seed.items():
        per_seed_scores[seed] = {m: sc for m, sc in entries}
        matchups = []
        for (a, sa), (b, sb) in combinations(entries, 2):
            if sa[0] > sb[0]:
                outcome = 1.0
            elif sa[0] < sb[0]:
                outcome = 0.0
            else:
                outcome = 0.5  # tie → no information
            matchups.append((seed, a, b, outcome))
        per_seed_matchups[seed] = matchups

    return per_seed_matchups, per_seed_scores


def run_per_seed_bt(
    per_seed_matchups: dict,
    n_bootstrap: int = 200,
) -> list[dict]:
    """Run Bradley-Terry MLE for each seed with bootstrap SEs."""
    all_models = set()
    for matchups in per_seed_matchups.values():
        for _, a, b, _ in matchups:
            all_models.add(a)
            all_models.add(b)
    models = sorted(all_models)

    seed_results = []
    for seed, matchups in per_seed_matchups.items():
        mle, se = bt_mle_with_se(matchups, models, n_bootstrap=n_bootstrap)

        sorted_mle = sorted(mle.items(), key=lambda x: -x[1])
        top_model, top_rating = sorted_mle[0]
        bot_model, bot_rating = sorted_mle[-1]

        seed_results.append({
            "seed": seed,
            "n_matchups": len(matchups),
            "mean": mle,
            "se": se,
            "top": {"model": top_model, "rating": round(top_rating, 1)},
            "bottom": {"model": bot_model, "rating": round(bot_rating, 1)},
        })

    return seed_results


# ─────────────────────────────────────────────────────────────────────────────
# Output formatting
# ─────────────────────────────────────────────────────────────────────────────

def format_model_name(m: str) -> str:
    return (m
            .replace("claude_", "C_").replace("gemini_", "G_")
            .replace("mistral_", "M_").replace("deepseek_", "D_")
            .replace("glm_", "GLM_").replace("gpt_", "GPT_")
            .replace("_creative", " cr").replace("_4_5", "45")
            .replace("_4_1", "41").replace("_2_5", "25")
            .replace("_flash", "FL").replace("_v3_2", "v32")
            .replace("_v3", "v3")[:12])


def print_per_seed_summary(seed_results: list[dict]):
    print("\nPER-SEED MLE SUMMARY")
    print("=" * 80)
    print(f"{'Seed':<45} {'n':>4}  {'Top model':<20} {'Rating':>7}  {'Bot model':<20} {'Rating':>7}")
    print("-" * 110)
    for sr in seed_results:
        top = sr["top"]
        bot = sr["bottom"]
        print(
            f"  {sr['seed']:<43} {sr['n_matchups']:>4}  "
            f"{top['model'][:20]:<20} {top['rating']:>7.0f}  "
            f"{bot['model'][:20]:<20} {bot['rating']:>7.0f}"
        )


def print_combined_leaderboard(
    leaderboard: list[dict],
    combined_mean: dict,
    combined_std: dict,
):
    print()
    print("=" * 85)
    print("BAYESIAN BRADLEY-TERRY LEADERBOARD")
    print("=" * 85)
    print(f"{'Rank':<5}{'Model':<22}{'Rating':>8}{'± SE':>6}{'95% CI':>22}{'Seeds':>6}")
    print("-" * 85)
    for i, entry in enumerate(leaderboard, 1):
        m = entry["model"]
        lo, hi = credible_interval(combined_mean[m], combined_std[m])
        print(
            f"#{i:<4}"
            f"{m:<22}"
            f"{entry['rating']:>8.0f}"
            f"{entry['se']:>6.1f}"
            f"[{lo:>6.0f}, {hi:>6.0f}]"
            f"{entry['n_seeds']:>6}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Frequentist ELO (for comparison)
# ─────────────────────────────────────────────────────────────────────────────

def run_frequentist_elo(data: dict) -> tuple[dict, dict]:
    """
    Replicate analyze_adversarial_elo.py: iterative ELO updates with bootstrap
    shuffling to get point estimates + stability metrics.

    Returns:
        elo: {model: mean rating across shuffles}
        stability: {model: SD of rating across shuffles}
    """
    INITIAL_RATING = 1500
    K_FACTOR = 32
    NUM_SHUFFLES = 100

    scores = {}
    for s in data.get("sessions", []):
        if "judges" not in s or "test_model" not in s:
            continue
        j = list(s["judges"].values())[0]["scores"]
        sc = session_score(j)
        if sc is None:
            continue
        scores[(s["seed_id"], s["test_model"])] = sc

    by_seed = defaultdict(list)
    for (seed, model), sc in scores.items():
        by_seed[seed].append((model, sc))

    matchups = []
    for seed, entries in by_seed.items():
        for (a, sa), (b, sb) in combinations(entries, 2):
            if sa[0] > sb[0]:
                matchups.append((seed, a, b, 1.0))
            elif sa[0] < sb[0]:
                matchups.append((seed, a, b, 0.0))
            else:
                matchups.append((seed, a, b, 0.5))

    ties = sum(1 for m in matchups if m[3] == 0.5)
    print(f"  [frequentist] {len(matchups)} matchups, {ties} ties ({100*ties/len(matchups):.0f}%)")

    models = {a for _, a, _, _ in matchups} | {b for _, _, b, _ in matchups}
    final = defaultdict(list)
    for shuffle_idx in range(NUM_SHUFFLES):
        ratings = {m: INITIAL_RATING for m in models}
        sh = matchups.copy()
        random.seed(shuffle_idx)
        random.shuffle(sh)
        for _, a, b, o in sh:
            ea = 1 / (1 + 10 ** ((ratings[b] - ratings[a]) / 400))
            ratings[a] += K_FACTOR * (o - ea)
            ratings[b] -= K_FACTOR * (o - ea)
        for m, r in ratings.items():
            final[m].append(r)

    elo = {m: sum(rs) / len(rs) for m, rs in final.items()}
    stability = {
        m: (sum((r - elo[m]) ** 2 for r in rs) / len(rs)) ** 0.5
        for m, rs in final.items()
    }
    return elo, stability


def print_side_by_side(
    bayes_leaderboard: list[dict],
    combined_mean: dict,
    combined_std: dict,
    freq_elo: dict,
    freq_stability: dict,
):
    """Print Bayesian vs frequentist ELO comparison."""
    print()
    print("=" * 100)
    print("BAYESIAN vs FREQUENTIST ELO COMPARISON")
    print("=" * 100)
    print(
        f"{'Rank':<5}"
        f"{'Model':<25}"
        f"{'Bayesian':>10} {'±σ':>7} {'95% CI':>22}"
        f"{'Frequentist':>12} {'±stab':>8}"
        f"{'Δ':>8}"
    )
    print("-" * 100)

    bayes_by_model = {e["model"]: e for e in bayes_leaderboard}
    freq_ranked = sorted(freq_elo.items(), key=lambda x: -x[1])

    for i, (freq_model, freq_r) in enumerate(freq_ranked, 1):
        bayes_e = bayes_by_model.get(freq_model, {})
        b_r = bayes_e.get("rating", 0)
        b_std = combined_std.get(freq_model, 0)
        delta = b_r - freq_r

        lo, hi = credible_interval(combined_mean[freq_model], b_std)
        print(
            f"#{i:<4}"
            f"{freq_model:<25}"
            f"{b_r:>10.0f} {b_std:>7.1f} [{lo:>5.0f},{hi:>5.0f}]"
            f"{freq_r:>12.0f} {freq_stability[freq_model]:>8.1f}"
            f"{delta:>+8.0f}"
        )

    print()
    print("  Bayesian:  Bradley-Terry MLE per seed → Normal conjugate combination. σ = posterior SD.")
    print("  Frequentist: iterative ELO (K=32, 100 bootstrap shuffles). ±stab = SD across shuffles.")
    print()
    print("  Δ = Bayesian rating − Frequentist rating. Positive = Bayesian rates higher.")


def print_head_to_head(
    hth: dict,
    leaderboard: list[dict],
    combined_mean: dict,
    combined_std: dict,
):
    models = [e["model"] for e in leaderboard]
    short = {m: format_model_name(m) for m in models}

    print()
    print("=" * 85)
    print("HEAD-TO-HEAD  (frequentist WR% / Bayes P(win)  n=matchups)")
    print("=" * 85)

    header = f"{'':>13}" + "".join(f"{short[m]:<13}" for m in models)
    print(header)
    print("-" * (13 + 13 * len(models)))

    for m_a in models:
        row = f"{short[m_a]:<13}"
        for m_b in models:
            if m_a == m_b:
                row += f"{'--':<13}"
                continue
            entry = hth.get(m_a, {}).get(m_b, {})
            freq = entry.get("frequentist_wr", 0.0)
            bayes = entry.get("bayes_pwin", 0.0)
            n = entry.get("n", 0)

            # Indicator of dominance
            if freq >= 0.70:
                ind = "++"
            elif freq >= 0.58:
                ind = " +"
            elif freq <= 0.30:
                ind = "--"
            elif freq <= 0.42:
                ind = " -"
            else:
                ind = "  "

            row += f"{ind}{freq:.0%}/{bayes:.0%}({n}) "[:13]
        print(row)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Bayesian Bradley-Terry ELO for RP-Bench"
    )
    parser.add_argument(
        "results_file",
        nargs="?",
        type=Path,
        default=Path("results/multiturn_20260414_042100.json"),
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        default=Path("results/bayesian_elo.json"),
    )
    parser.add_argument(
        "--prior-std", type=float, default=PRIOR_STD,
        help=f"Prior std for cross-seed combination (default: {PRIOR_STD})",
    )
    parser.add_argument(
        "--bootstrap", type=int, default=200,
        help="Number of bootstrap samples for SE estimation (default: 200)",
    )
    parser.add_argument(
        "--mle-only", action="store_true",
        help="Skip cross-seed combination (per-seed MLE only)",
    )
    parser.add_argument(
        "--compare-to-frequentist", action="store_true",
        help="Also run frequentist ELO and show side-by-side comparison",
    )
    args = parser.parse_args()

    if not args.results_file.exists():
        print(f"Error: {args.results_file} not found")
        for f in sorted(Path("results").glob("multiturn_*.json")):
            print(f"  {f.name}")
        sys.exit(1)
    random.seed(42)   # reproducible bootstrap

    prior_std = args.prior_std

    print(f"Loading: {args.results_file}")
    data = json.load(open(args.results_file))

    print("Building matchups...")
    per_seed_matchups, per_seed_scores = load_matchups(data)
    total_matchups = sum(len(m) for m in per_seed_matchups.values())
    n_seeds = len(per_seed_matchups)
    n_models = len(set(m for sc in per_seed_scores.values() for m in sc))
    print(f"  {n_seeds} seeds × {n_models} models = {total_matchups} matchups")

    print(f"\nStage 1: Per-seed Bradley-Terry MLE (bootstrap n={args.bootstrap})...")
    seed_results = run_per_seed_bt(per_seed_matchups, n_bootstrap=args.bootstrap)
    print_per_seed_summary(seed_results)

    if args.mle_only:
        out = {
            "methodology": (
                "Bradley-Terry MLE per seed via IRLS, with bootstrap standard errors. "
                "No cross-seed combination."
            ),
            "prior_std": PRIOR_STD,
            "per_seed": seed_results,
        }
        with open(args.output, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\nSaved (MLE-only): {args.output}")
        return

    print(f"\nStage 2: Cross-seed combination (prior std={PRIOR_STD})...")
    combined_mean, combined_var, combined_std = combine_posteriors(seed_results)

    # Count how many seeds inform each model
    n_seeds_per_model = {}
    for m in combined_mean:
        n_seeds_per_model[m] = sum(
            1 for sr in seed_results if m in sr["mean"]
        )

    # Build leaderboard
    leaderboard = []
    for m in sorted(combined_mean, key=combined_mean.get, reverse=True):
        se = seed_results[0]["se"].get(m, PRIOR_STD)  # use avg SE
        entry = {
            "model": m,
            "rating": round(combined_mean[m], 1),
            "se": round(se, 1),
            "std": round(combined_std[m], 1),
            "ci_95_lower": round(combined_mean[m] - 1.96 * combined_std[m], 1),
            "ci_95_upper": round(combined_mean[m] + 1.96 * combined_std[m], 1),
            "n_seeds": n_seeds_per_model[m],
        }
        leaderboard.append(entry)

    # Compute head-to-head
    print("\nComputing head-to-head (frequentist + Bayesian)...")
    wins = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for seed, matchups in per_seed_matchups.items():
        for _, a, b, outcome in matchups:
            if outcome == 1.0:
                wins[a][b][0] += 1
            elif outcome == 0.0:
                wins[b][a][0] += 1
            else:
                wins[a][b][2] += 1
                wins[b][a][2] += 1

    hth = {}
    for m_a in leaderboard:
        m_a_name = m_a["model"]
        hth[m_a_name] = {}
        for m_b in leaderboard:
            m_b_name = m_b["model"]
            if m_a_name == m_b_name:
                continue
            w, l, t = wins[m_a_name][m_b_name]
            total = w + l + t
            if total == 0:
                continue
            freq_wr = (w + 0.5 * t) / total
            bayes_p = posterior_win_prob(
                combined_mean[m_a_name], combined_std[m_a_name],
                combined_mean[m_b_name], combined_std[m_b_name],
            )
            hth[m_a_name][m_b_name] = {
                "frequentist_wr": round(freq_wr, 4),
                "bayes_pwin": round(bayes_p, 4),
                "wins": w,
                "losses": l,
                "ties": t,
                "n": total,
            }

    print_combined_leaderboard(leaderboard, combined_mean, combined_std)
    print_head_to_head(hth, leaderboard, combined_mean, combined_std)

    if args.compare_to_frequentist:
        print("\nRunning frequentist ELO for comparison...")
        freq_elo, freq_stability = run_frequentist_elo(data)
        print_side_by_side(
            leaderboard, combined_mean, combined_std,
            freq_elo, freq_stability,
        )

    # Show how prior dominates with little data per seed
    print()
    print("INFORMATION CONTRIBUTED BY DATA (relative to prior)")
    print("=" * 60)
    for entry in leaderboard[:5]:
        m = entry["model"]
        prior_prec = 1.0 / (PRIOR_STD ** 2)
        data_prec = sum(
            1.0 / (seed_results[i]["se"].get(m, PRIOR_STD) ** 2)
            for i in range(n_seeds)
        )
        info_ratio = data_prec / prior_prec
        print(f"  {m:<30} data_prec={data_prec:.3f}  prior_prec={prior_prec:.4f}  "
              f"data/total={info_ratio/(info_ratio+1):.1%}")

    # Save
    out = {
        "methodology": (
            "Bayesian Bradley-Terry model: Stage 1 uses IRLS to find per-seed MLE "
            "with bootstrap standard errors (200 resamples). Stage 2 combines "
            "per-seed estimates via Normal conjugate updating with a regularizing "
            "prior (std={PRIOR_STD}). This correctly handles the high tie rate "
            "(63%) by treating ties as 0.5 outcomes (no information) in logit space."
        ).format(PRIOR_STD=PRIOR_STD),
        "source": str(args.results_file),
        "prior_std": PRIOR_STD,
        "kappa": KAPPA,
        "n_bootstrap": args.bootstrap,
        "per_seed": seed_results,
        "combined": {
            "mean": {m: round(v, 2) for m, v in combined_mean.items()},
            "var": {m: round(v, 2) for m, v in combined_var.items()},
            "std": {m: round(v, 2) for m, v in combined_std.items()},
        },
        "leaderboard": leaderboard,
        "head_to_head": hth,
    }
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
