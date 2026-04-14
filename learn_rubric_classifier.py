#!/usr/bin/env python3
"""Train a classifier to predict user preference from feature combinations.

Individual features don't predict preference (as shown in learn_rubric_from_data.py).
But combinations might. This tests that hypothesis.

For each swipe pair:
  - Feature delta = accepted_features - rejected_features
  - Label = 1 (user prefers this direction)

Then train models:
  - Logistic Regression: identify which combinations matter
  - Random Forest: capture non-linear interactions
  - Test via cross-validation
"""
import json
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import cross_val_score, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from learn_rubric_from_data import extract_features


def main():
    all_swipes = []
    for f in glob.glob("scenarios/*_swipes.json"):
        with open(f) as fh:
            all_swipes.extend(json.load(fh))

    # Build training set: each pair becomes TWO examples (symmetric)
    # Example 1: delta = accepted - rejected, label = 1
    # Example 2: delta = rejected - accepted, label = 0
    # This forces the classifier to learn directional patterns

    X = []
    y = []
    sources = []
    langs = []

    print("Extracting features...")
    for s in all_swipes:
        variants = s.get("variants", [])
        accepted = [v for v in variants if v.get("is_accepted")]
        rejected = [v for v in variants if not v.get("is_accepted")]
        if not accepted or not rejected:
            continue

        acc_text = accepted[0].get("text_clean", "")
        if len(acc_text) < 100:
            continue
        acc_f = extract_features(acc_text)

        for r in rejected:
            rej_text = r.get("text_clean", "")
            if len(rej_text) < 100:
                continue
            rej_f = extract_features(rej_text)

            feat_names = sorted(acc_f.keys())
            delta = [acc_f[k] - rej_f[k] for k in feat_names]

            # Add positive example
            X.append(delta)
            y.append(1)
            sources.append(s.get("source", "?"))
            langs.append(s.get("language", "en"))

            # Add flipped negative example (symmetric)
            X.append([-d for d in delta])
            y.append(0)
            sources.append(s.get("source", "?"))
            langs.append(s.get("language", "en"))

    X = np.array(X, dtype=np.float32)
    y = np.array(y)
    print(f"Built {len(X)} training examples from {len(X)//2} pairs")
    print(f"Features: {len(feat_names)}")
    print()

    # ============ MODEL 1: LOGISTIC REGRESSION ============
    print("=" * 80)
    print("MODEL 1: Logistic Regression (linear combinations)")
    print("=" * 80)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, C=1.0)),
    ])

    scores = cross_val_score(pipeline, X, y, cv=5, scoring="accuracy")
    print(f"\n5-fold CV accuracy: {scores.mean()*100:.1f}% (± {scores.std()*100:.1f}%)")
    print(f"Individual folds: {[f'{s*100:.1f}%' for s in scores]}")

    # Fit on all data to get feature weights
    pipeline.fit(X, y)
    clf = pipeline.named_steps["clf"]
    coefs = list(zip(feat_names, clf.coef_[0]))
    coefs.sort(key=lambda x: abs(x[1]), reverse=True)

    print(f"\nTop features (positive coef = user prefers MORE of this in accepted):")
    for feat, coef in coefs[:10]:
        direction = "MORE" if coef > 0 else "LESS"
        print(f'  {feat:<25} coef={coef:+6.3f}  (accepted has {direction})')

    # ============ MODEL 2: RANDOM FOREST ============
    print()
    print("=" * 80)
    print("MODEL 2: Random Forest (non-linear interactions)")
    print("=" * 80)

    rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, n_jobs=1)
    scores = cross_val_score(rf, X, y, cv=5, scoring="accuracy")
    print(f"\n5-fold CV accuracy: {scores.mean()*100:.1f}% (± {scores.std()*100:.1f}%)")

    rf.fit(X, y)
    importances = list(zip(feat_names, rf.feature_importances_))
    importances.sort(key=lambda x: x[1], reverse=True)

    print(f"\nTop features by importance (non-linear):")
    for feat, imp in importances[:10]:
        bar = "█" * int(imp * 100)
        print(f'  {feat:<25} {imp:.3f} {bar}')

    # ============ MODEL 3: GRADIENT BOOSTING ============
    print()
    print("=" * 80)
    print("MODEL 3: Gradient Boosting (stronger non-linear)")
    print("=" * 80)

    gb = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42)
    scores = cross_val_score(gb, X, y, cv=5, scoring="accuracy")
    print(f"\n5-fold CV accuracy: {scores.mean()*100:.1f}% (± {scores.std()*100:.1f}%)")

    # ============ PER-SOURCE ANALYSIS ============
    print()
    print("=" * 80)
    print("PER-SOURCE: does some genre/style predict better than others?")
    print("=" * 80)

    from collections import defaultdict
    by_source = defaultdict(list)
    for i in range(len(X)):
        by_source[sources[i]].append(i)

    print(f'\n{"Source":<25} {"N pairs":<10} {"Linear CV":<12} {"RF CV":<12}')
    print("-" * 60)
    for src, idxs in sorted(by_source.items(), key=lambda x: -len(x[1])):
        if len(idxs) < 20:
            continue
        X_src = X[idxs]
        y_src = y[idxs]
        try:
            lr_score = cross_val_score(Pipeline([("s", StandardScaler()), ("c", LogisticRegression(max_iter=1000))]), X_src, y_src, cv=3).mean() * 100
            rf_score = cross_val_score(RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, n_jobs=1), X_src, y_src, cv=3).mean() * 100
            print(f'{src:<25} {len(idxs)//2:<10} {lr_score:>6.1f}%      {rf_score:>6.1f}%')
        except Exception as e:
            pass

    # ============ PER-LANGUAGE ============
    print()
    print("PER-LANGUAGE:")
    for lang in ["en", "ru"]:
        idxs = [i for i in range(len(X)) if langs[i] == lang]
        if len(idxs) < 20:
            continue
        X_l = X[idxs]
        y_l = y[idxs]
        lr_score = cross_val_score(Pipeline([("s", StandardScaler()), ("c", LogisticRegression(max_iter=1000))]), X_l, y_l, cv=3).mean() * 100
        rf_score = cross_val_score(RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, n_jobs=1), X_l, y_l, cv=3).mean() * 100
        print(f'  {lang.upper()}: n={len(idxs)//2}, linear={lr_score:.1f}%, RF={rf_score:.1f}%')

    # Save best model coefficients
    out = Path("results") / "learned_rubric.json"
    with open(out, "w") as f:
        json.dump({
            "n_pairs": len(X) // 2,
            "logistic_regression_cv_accuracy": float(scores.mean()),
            "top_features_linear": [
                {"feature": f, "coefficient": float(c), "direction": "more" if c > 0 else "less"}
                for f, c in coefs[:15]
            ],
            "top_features_importance": [
                {"feature": f, "importance": float(imp)}
                for f, imp in importances[:15]
            ],
        }, f, indent=2)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
