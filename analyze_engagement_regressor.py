#!/usr/bin/env python3
"""Engagement regressor — train a feature-based pairwise classifier on the
1,857 clean single-message arena human votes, then predict per-response
"engagement" for Phase B / R1 0528 models that lack arena coverage.

This is Option C from the engagement-axis discussion: the LLM-judge
proxy (Round 4) failed to validate. A simpler approach is to train
directly on the human vote signal using rule-based response features.

Pipeline:
    1. Load arena votes (web/data/votes.jsonl, mode='arena',
       suspect-filtered).
    2. Featurize response_a and response_b text into ~12-feature vectors
       (length, lexical, dialogue/action ratio, punctuation density).
    3. Train logistic regression on (feat_a - feat_b) -> winner ∈ {1, 0}
       (drop ties), with 5-fold CV.
    4. Validate against the engagement-proxy negative result by:
       a. Cross-validation accuracy on the held-out votes.
       b. Per-model engagement rank (regressor) vs Bayesian community
          arena ELO on Phase A overlap → Spearman ρ.
    5. Apply to Phase B and R1 0528 single-turn responses (from
       run_20260502_084528.json + the R1 multiturn data) to score them.
       Aggregate per-model.

Output:
    results/engagement_regressor.json
    + sorted leaderboard to stdout

Cost: $0 (rule-based features, no API).
Time: ~30 seconds (sklearn).
"""
import json
import re
import sys
from pathlib import Path
from collections import Counter

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegressionCV
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
VOTES_PATH = ROOT / "web" / "data" / "votes.jsonl"
PHASE_A_RUN = RESULTS / "run_20260413_155910.json"
PHASE_B_RUN = RESULTS / "run_20260502_084528.json"
R1_RUN     = RESULTS / "run_20260502_145120.json"  # full 27-scenario rerun
ARENA_BAYES = RESULTS / "community_arena_bayesian.json"
OUT = RESULTS / "engagement_regressor.json"

# Catch-pair scenario IDs (excluded from training — they're not real RP)
CATCH_PREFIXES = ("catch_",)

FEATURE_NAMES = [
    "word_count",
    "char_count",
    "ttr",
    "sentence_count",
    "avg_sentence_len",
    "dialogue_ratio",
    "action_ratio",
    "exclamation_per_1k",
    "ellipsis_per_1k",
    "comma_per_1k",
    "avg_word_len",
    "bigram_repetition",
]


def featurize(text: str) -> np.ndarray:
    """Return a fixed-length feature vector for a response."""
    if not text:
        return np.zeros(len(FEATURE_NAMES), dtype=np.float64)

    # Words
    words = re.findall(r"\b[\w'-]+\b", text)
    n_words = len(words)
    if n_words == 0:
        return np.zeros(len(FEATURE_NAMES), dtype=np.float64)

    n_chars = len(text)
    unique = len({w.lower() for w in words})
    ttr = unique / n_words

    # Sentences (simple split on .!?)
    sent_text = re.split(r"[.!?]+\s+", text)
    sentences = [s for s in sent_text if s.strip()]
    n_sent = max(1, len(sentences))
    avg_sent_len = n_words / n_sent

    # Dialogue: chars inside "..." or '...' or "..."
    dialogue_chars = sum(
        len(m.group(0))
        for m in re.finditer(r'"[^"]*"|"[^"]*"|"[^"]*"', text)
    )
    dialogue_ratio = dialogue_chars / max(1, n_chars)

    # Action: chars inside *...*
    action_chars = sum(
        len(m.group(0)) for m in re.finditer(r"\*[^*]+\*", text)
    )
    action_ratio = action_chars / max(1, n_chars)

    excl = text.count("!")
    ellipsis = text.count("...") + text.count("…") + text.count("—")
    comma = text.count(",")

    excl_per_1k = 1000 * excl / n_words
    ell_per_1k = 1000 * ellipsis / n_words
    comma_per_1k = 1000 * comma / n_words

    avg_word_len = sum(len(w) for w in words) / n_words

    # Bigram repetition
    bigrams = list(zip(words[:-1], words[1:]))
    if bigrams:
        unique_bg = len(set(bigrams))
        bg_rep = 1 - (unique_bg / len(bigrams))
    else:
        bg_rep = 0.0

    return np.array([
        n_words, n_chars, ttr, n_sent, avg_sent_len,
        dialogue_ratio, action_ratio,
        excl_per_1k, ell_per_1k, comma_per_1k,
        avg_word_len, bg_rep,
    ], dtype=np.float64)


def load_arena_votes():
    """Load suspect-filtered single-message arena votes with response text."""
    if not VOTES_PATH.exists():
        print(f"ERROR: {VOTES_PATH} not found. This needs the original arena "
              "server's vote log, which kept each vote's response text; the "
              "site's public export (fetch_arena_votes.py) carries none.")
        sys.exit(1)

    votes = []
    with open(VOTES_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            v = json.loads(line)
            if v.get("mode") != "arena":
                continue
            if v.get("is_catch"):
                continue
            sid = v.get("scenario_id", "")
            if any(sid.startswith(p) for p in CATCH_PREFIXES):
                continue
            if not (v.get("response_a") and v.get("response_b") and v.get("winner") in ("A", "B", "tie")):
                continue
            votes.append(v)
    if not votes:
        print(f"ERROR: no arena vote in {VOTES_PATH} carries response_a and "
              "response_b. The site's public export (fetch_arena_votes.py) "
              "has no response text, so this regressor cannot train on it.")
        sys.exit(1)
    return votes


def load_runs():
    """Load Phase A + B run results: {(model, scenario_id): response_text}."""
    out = {}
    for src in [PHASE_A_RUN, PHASE_B_RUN, R1_RUN]:
        if not src.exists():
            continue
        d = json.loads(src.read_text())
        for r in d.get("results", []):
            mk = r.get("test_model")
            sid = r.get("scenario_id")
            content = (r.get("generation") or {}).get("content")
            if mk and sid and content:
                out[(mk, sid)] = content
    return out


def load_r1_multiturn_responses():
    """R1 0528 has multi-turn data, no single-turn run yet. Use empty mapping
    for now; if/when R1 single-turn run is done it'll be in PHASE_B_RUN.
    """
    return {}  # placeholder — R1 single-turn rubric was actually in the
               # PHASE_B-style run; load_runs() already picks it up if so.


def main():
    votes = load_arena_votes()
    print(f"Loaded {len(votes)} clean arena votes (catches excluded)")

    # Featurize each vote
    X_diff = []
    y = []
    for v in votes:
        if v["winner"] == "tie":
            continue
        fa = featurize(v["response_a"])
        fb = featurize(v["response_b"])
        X_diff.append(fa - fb)
        y.append(1 if v["winner"] == "A" else 0)
    X = np.array(X_diff)
    y = np.array(y)
    print(f"Training set: {len(y)} pairs (ties dropped)")
    print(f"  A-wins: {sum(y == 1)}, B-wins: {sum(y == 0)}")

    # Standardize
    scaler = StandardScaler()
    X_std = scaler.fit_transform(X)

    # 5-fold CV accuracy
    clf = LogisticRegressionCV(cv=5, max_iter=2000, scoring="accuracy")
    cv_scores = cross_val_score(
        clf, X_std, y, cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        scoring="accuracy",
    )
    cv_mean, cv_std = cv_scores.mean(), cv_scores.std()
    print(f"5-fold CV accuracy: {cv_mean:.4f} ± {cv_std:.4f}")
    if cv_mean < 0.55:
        print(f"  WARN: accuracy is at-or-near chance (0.5). Features carry weak signal.")

    # Fit on all data and inspect coefficients
    clf.fit(X_std, y)
    coefs = list(zip(FEATURE_NAMES, clf.coef_[0]))
    coefs.sort(key=lambda c: -abs(c[1]))
    print("\nFeature coefficients (standardized, sign = direction of A advantage):")
    for name, c in coefs:
        print(f"  {name:<22}{c:+8.4f}")

    # ----- Apply: predict per-response engagement skill -----
    # Skill = expected log-odds A-wins-against-the-population-mean.
    # For each (model, scenario) response in our run files, compute features,
    # standardize using the trained scaler, and dot with classifier coefficients
    # → standardized engagement skill. Aggregate per-model.
    runs = load_runs()
    print(f"\nLoaded {len(runs)} (model, scenario) responses from Phase A + B")

    # Population-mean feature vector — what an "average" response looks like
    # across the full pool of training votes.
    all_response_features = []
    for v in votes:
        all_response_features.append(featurize(v["response_a"]))
        all_response_features.append(featurize(v["response_b"]))
    pop_mean = np.mean(np.vstack(all_response_features), axis=0)

    skills = {}
    for (model, sid), content in runs.items():
        f_resp = featurize(content)
        # log-odds of beating the population-mean response on this scenario
        x = f_resp - pop_mean
        x_std = scaler.transform(x.reshape(1, -1))[0]
        skill = float(np.dot(clf.coef_[0], x_std) + clf.intercept_[0])
        skills.setdefault(model, []).append({"scenario_id": sid, "skill": skill})

    per_model = {}
    for m, items in skills.items():
        ss = [i["skill"] for i in items]
        per_model[m] = {
            "engagement_skill_mean": round(float(np.mean(ss)), 4),
            "engagement_skill_std":  round(float(np.std(ss)), 4),
            "n_scored":              len(ss),
        }

    # ----- Validate against human single-msg arena ELO -----
    arena = json.loads(ARENA_BAYES.read_text())
    arena_elo = {e["model"]: e["elo_mean"] for e in arena["leaderboard"]}
    common = sorted(m for m in per_model if m in arena_elo)
    if len(common) >= 3:
        xs = [per_model[m]["engagement_skill_mean"] for m in common]
        ys = [arena_elo[m] for m in common]
        rho, p = spearmanr(xs, ys)
        validation = {
            "n_models_overlap": len(common),
            "rho_vs_human_arena_elo": round(float(rho), 4),
            "p_value":               round(float(p), 4),
            "interpretation": (
                "trustworthy as proxy" if rho > 0.7
                else "moderate proxy"   if rho > 0.4
                else "weak / suspect proxy"
            ),
        }
        print(f"\nValidation: ρ(regressor, human arena ELO) on {len(common)} models = "
              f"{rho:+.3f}  (p = {p:.3f})  [{validation['interpretation']}]")
    else:
        validation = {"n_models_overlap": len(common), "rho_vs_human_arena_elo": None}
        print("\nValidation skipped: too few overlap models.")

    # ----- Print leaderboard -----
    rows = sorted(per_model.items(), key=lambda x: -x[1]["engagement_skill_mean"])
    print()
    print(f"{'rank':<5}{'model':<26}{'skill':<10}{'std':<8}{'n':<5}{'human ELO':<11}")
    print("-" * 70)
    for i, (m, s) in enumerate(rows, 1):
        elo = arena_elo.get(m)
        elo_s = f"{elo:.0f}" if elo else "—"
        print(f"{i:<5}{m:<26}{s['engagement_skill_mean']:<10.3f}"
              f"{s['engagement_skill_std']:<8.3f}{s['n_scored']:<5}{elo_s:<11}")

    output = {
        "method": "logistic regression on pairwise feature differences",
        "training_set_size": len(y),
        "feature_names": FEATURE_NAMES,
        "cv_accuracy": {
            "mean": round(float(cv_mean), 4),
            "std":  round(float(cv_std), 4),
        },
        "feature_coefficients": dict(zip(FEATURE_NAMES, [float(c) for c in clf.coef_[0]])),
        "intercept": float(clf.intercept_[0]),
        "validation_against_human_arena": validation,
        "per_model": dict(rows),
    }
    OUT.write_text(json.dumps(output, indent=2))
    print(f"\nSaved: {OUT}")


if __name__ == "__main__":
    main()
