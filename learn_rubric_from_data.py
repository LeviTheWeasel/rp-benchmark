#!/usr/bin/env python3
"""Derive a data-driven rubric from real swipe preferences.

For each swipe pair, measure concrete differences between accepted and
rejected responses. Find patterns that CONSISTENTLY differ across many
pairs — those are the signals users actually care about.
"""
import json
import glob
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from harness.objective_metrics import compute_all as compute_obj
from harness.slop_detectors import detect_all_slop


def extract_features(text: str) -> dict:
    """Extract a wide set of features from text for comparison."""
    text_len = max(1, len(text))
    words = re.findall(r"\b[a-zA-Zа-яА-Я]+\b", text)
    word_count = len(words)
    sentences = [s for s in re.split(r'[.!?]+', text) if len(s.strip()) > 3]

    # Sentence length distribution
    sent_lengths = [len(s.split()) for s in sentences]
    avg_sent = sum(sent_lengths) / len(sent_lengths) if sent_lengths else 0
    short_sentences = sum(1 for l in sent_lengths if l <= 3)
    long_sentences = sum(1 for l in sent_lengths if l >= 20)

    # Dialogue characteristics
    dialogue_lines = len(re.findall(r'"[^"]+"', text))
    # Italic markers for actions
    italic_count = len(re.findall(r"\*[^*]+\*", text))

    # Punctuation patterns
    ellipses = text.count("...")
    em_dashes = text.count("—")
    question_marks = text.count("?")
    exclamations = text.count("!")

    # Paragraph structure
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    para_count = len(paragraphs)
    avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0

    # Body language density (common RP phrases)
    body_phrases = [
        "his hand", "her hand", "his eyes", "her eyes",
        "his lips", "her lips", "his fingers", "her fingers",
        "his breath", "her breath", "his jaw", "her jaw",
    ]
    body_count = sum(text.lower().count(p) for p in body_phrases)

    # Sensory language
    senses = ["smell", "scent", "taste", "sound", "touch", "warm", "cold", "soft", "rough"]
    sensory_count = sum(text.lower().count(s) for s in senses)

    # Character action density (verbs)
    action_words = ["said", "whispered", "laughed", "smiled", "frowned", "nodded", "looked",
                    "turned", "moved", "stepped", "leaned", "reached", "pulled", "pushed"]
    action_count = sum(len(re.findall(r'\b' + w + r'\b', text.lower())) for w in action_words)

    # Obj + slop metrics
    obj = compute_obj(text)
    slop = detect_all_slop(text)

    return {
        "length": text_len,
        "word_count": word_count,
        "sentence_count": len(sentences),
        "avg_sentence_length": round(avg_sent, 2),
        "short_sentences": short_sentences,
        "long_sentences": long_sentences,
        "paragraph_count": para_count,
        "avg_paragraph_length": round(avg_para_len, 1),
        "dialogue_lines": dialogue_lines,
        "italic_actions": italic_count,
        "ellipses_per_1k": round(ellipses * 1000 / text_len, 2),
        "em_dashes_per_1k": round(em_dashes * 1000 / text_len, 2),
        "question_marks_per_1k": round(question_marks * 1000 / text_len, 2),
        "exclamations_per_1k": round(exclamations * 1000 / text_len, 2),
        "body_phrases_per_1k": round(body_count * 1000 / text_len, 2),
        "sensory_words_per_1k": round(sensory_count * 1000 / text_len, 2),
        "action_words_per_1k": round(action_count * 1000 / text_len, 2),
        "dialogue_density": round(dialogue_lines * 1000 / text_len, 2),
        "cliches_per_1k": round(obj["cliches"]["total_weight"] * 1000 / text_len, 3),
        "ttr": obj["vocabulary_diversity"],
        "rhythm_score": obj["sentence_rhythm"].get("rhythm_score", 0),
        "rep_bigrams_per_1k": round(obj["repetition"]["repeated_bigrams"] * 1000 / text_len, 2),
        "rep_trigrams_per_1k": round(obj["repetition"]["repeated_trigrams"] * 1000 / text_len, 2),
        "slop_per_1k": slop.get("weight_per_1k_chars", 0),
    }


def main():
    all_swipes = []
    for f in glob.glob("scenarios/*_swipes.json"):
        with open(f) as fh:
            all_swipes.extend(json.load(fh))

    # Extract features for all pairs
    pair_features = []  # [(acc_features, rej_features, source, lang)]

    print(f"Processing {len(all_swipes)} swipe pairs...")
    for s in all_swipes:
        variants = s.get("variants", [])
        accepted = [v for v in variants if v.get("is_accepted")]
        rejected = [v for v in variants if not v.get("is_accepted")]
        if not accepted or not rejected:
            continue

        acc_text = accepted[0].get("text_clean", "")
        if len(acc_text) < 100:
            continue

        acc_feat = extract_features(acc_text)

        for r in rejected:
            rej_text = r.get("text_clean", "")
            if len(rej_text) < 100:
                continue
            rej_feat = extract_features(rej_text)
            pair_features.append((acc_feat, rej_feat, s.get("source", "?"), s.get("language", "en")))

    n = len(pair_features)
    print(f"Analyzed {n} pairs with valid features")
    print()

    # For each feature, compute: how often does accepted > rejected?
    feature_wins = {}  # {feature_name: {"acc_higher": N, "rej_higher": N, "tied": N, "avg_delta": X}}

    all_features = list(pair_features[0][0].keys())

    for feat in all_features:
        acc_higher = 0
        rej_higher = 0
        tied = 0
        deltas = []

        for acc_f, rej_f, _, _ in pair_features:
            a = acc_f.get(feat)
            r = rej_f.get(feat)
            if a is None or r is None:
                continue
            if a > r:
                acc_higher += 1
            elif a < r:
                rej_higher += 1
            else:
                tied += 1
            deltas.append(a - r)

        total = acc_higher + rej_higher + tied
        if total == 0:
            continue

        avg_delta = sum(deltas) / len(deltas)

        # Compute agreement rate: how often does accepted differ in consistent direction?
        agreement = max(acc_higher, rej_higher) / total
        # Direction: does accepted usually have MORE or LESS of this feature?
        direction = "MORE" if acc_higher > rej_higher else "LESS"
        dominant = max(acc_higher, rej_higher)

        feature_wins[feat] = {
            "acc_higher": acc_higher,
            "rej_higher": rej_higher,
            "tied": tied,
            "avg_delta": round(avg_delta, 3),
            "agreement_rate": round(100 * dominant / total, 1),
            "accepted_direction": direction,
            "total": total,
        }

    # Rank features by signal strength (deviation from 50/50)
    ranked = sorted(
        feature_wins.items(),
        key=lambda x: abs(x[1]["acc_higher"] - x[1]["rej_higher"]) / x[1]["total"],
        reverse=True,
    )

    print("=" * 90)
    print("  DATA-DRIVEN FEATURE RANKING (which features track user preference)")
    print("=" * 90)
    print()
    print(f'  {"Feature":<25} {"Direction":<13} {"Accept>Rej":<12} {"Accept<Rej":<12} {"Tied":<6} {"AvgDelta":<10} {"Signal":<7}')
    print("  " + "-" * 88)

    for feat, stats in ranked:
        n_total = stats["total"]
        acc_pct = 100 * stats["acc_higher"] / n_total
        rej_pct = 100 * stats["rej_higher"] / n_total
        signal_strength = abs(stats["acc_higher"] - stats["rej_higher"]) / n_total * 100

        signal_marker = ""
        if signal_strength > 20:
            signal_marker = "STRONG"
        elif signal_strength > 10:
            signal_marker = "moderate"
        elif signal_strength > 5:
            signal_marker = "weak"
        else:
            signal_marker = "noise"

        direction = "more=accept" if stats["accepted_direction"] == "MORE" else "less=accept"

        print(f'  {feat:<25} {direction:<13} {acc_pct:>5.1f}%       {rej_pct:>5.1f}%       {stats["tied"]:<6} {stats["avg_delta"]:>+8.3f}  {signal_marker}')

    # Summary: what matters
    print()
    print("=" * 90)
    print("  ACTIONABLE DATA-DRIVEN RUBRIC")
    print("=" * 90)
    print()
    print("Features that track user preference at >10pt above chance (i.e. >55% or <45%):")
    print()

    for feat, stats in ranked:
        n_total = stats["total"]
        acc_pct = 100 * stats["acc_higher"] / n_total
        # Effective signal: abs distance from 50%
        # Need both sides non-trivial
        non_tied = stats["acc_higher"] + stats["rej_higher"]
        if non_tied == 0:
            continue
        pct_of_non_tied = 100 * stats["acc_higher"] / non_tied
        if abs(pct_of_non_tied - 50) < 10:
            continue

        direction = "MORE" if pct_of_non_tied > 50 else "LESS"
        print(f"  • Accepted responses have {direction} {feat}")
        print(f"    ({pct_of_non_tied:.0f}% of the time when they differ — avg delta {stats['avg_delta']:+.3f})")

    # Save
    out = Path("results") / "data_driven_rubric.json"
    with open(out, "w") as f:
        json.dump({
            "n_pairs": n,
            "features": feature_wins,
        }, f, indent=2)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
