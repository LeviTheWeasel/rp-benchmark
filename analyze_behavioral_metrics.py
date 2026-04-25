#!/usr/bin/env python3
"""Behavioral metrics on multi-turn assistant responses.

For each session in the multi-turn results, computes per-response:
  - unique_word_ratio:   unique tokens / total tokens (vocabulary diversity)
  - bigram_repetition:   1 - (unique_bigrams / total_bigrams) (recycling)
  - word_count:          response length
  - sentence_length_var: variance of sentence lengths (rhythm)

Aggregates per-model (mean + std across that model's responses) and
computes population averages across all models. These are the
"BEHAVIORAL METRICS" block in the per-model profile card.

Pure prose statistics — no API calls. Operates on existing session
data. Input files default to multiturn_merged_all.json +
multiturn_phase_a_new_gen.json + multiturn_phase_b_frontier.json
(if present).

Usage:
    python3 analyze_behavioral_metrics.py
"""
import json
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

INPUTS = [
    "results/multiturn_merged_all.json",
    "results/multiturn_phase_a_new_gen.json",
    "results/multiturn_phase_b_frontier.json",
]
OUTPUT = Path("results/behavioral_metrics.json")


def tokenize(text: str) -> list[str]:
    """Lowercase, alpha-only word tokens."""
    return re.findall(r"[a-zA-Z']+", text.lower())


def split_sentences(text: str) -> list[str]:
    """Split on sentence-ending punctuation. Crude but fine for English."""
    parts = re.split(r"[.!?]+\s+", text)
    return [p for p in parts if p.strip()]


def per_response_metrics(text: str | None) -> dict | None:
    """Compute all metrics for one response. Returns None if too short."""
    if not text:
        return None
    tokens = tokenize(text)
    if len(tokens) < 20:
        return None

    unique_word_ratio = len(set(tokens)) / len(tokens)

    bigrams = [(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)]
    bigram_repetition = 1 - (len(set(bigrams)) / len(bigrams)) if bigrams else 0

    sentences = split_sentences(text)
    sentence_lengths = [len(tokenize(s)) for s in sentences]
    sentence_length_var = (
        st.variance(sentence_lengths) if len(sentence_lengths) >= 2 else 0
    )

    return {
        "word_count": len(tokens),
        "unique_word_ratio": unique_word_ratio,
        "bigram_repetition": bigram_repetition,
        "sentence_length_var": sentence_length_var,
    }


def main():
    # Collect every assistant response across all sessions, deduped by
    # (test_model, seed_id, turn) so re-runs don't double-count.
    seen = set()
    per_model_metrics = defaultdict(lambda: defaultdict(list))
    all_responses = []  # for population averages

    for path in INPUTS:
        if not Path(path).exists():
            print(f"  skip {path} (not found)")
            continue
        data = json.load(open(path))
        for s in data.get("sessions", []):
            if "dialogue" not in s:
                continue
            model = s["test_model"]
            seed = s["seed_id"]
            for msg in s["dialogue"]:
                # Only model-generated responses (the character side).
                # User-sim turns + scripted user inputs aren't "the model under test".
                if msg.get("role") not in ("character", "assistant"):
                    continue
                key = (model, seed, msg.get("turn"))
                if key in seen:
                    continue
                seen.add(key)

                m = per_response_metrics(msg.get("content", ""))
                if m is None:
                    continue
                for metric, val in m.items():
                    per_model_metrics[model][metric].append(val)
                    all_responses.append(val if metric == "word_count" else None)

    # Population averages — recompute across all responses
    population = {}
    pop_collect = defaultdict(list)
    for model, metrics in per_model_metrics.items():
        for metric, vals in metrics.items():
            pop_collect[metric].extend(vals)
    for metric, vals in pop_collect.items():
        population[metric] = {
            "mean": round(st.mean(vals), 4),
            "median": round(st.median(vals), 4),
            "std": round(st.stdev(vals), 4) if len(vals) > 1 else 0,
            "n_responses": len(vals),
        }

    # Per-model aggregates with delta-from-population
    per_model = {}
    for model, metrics in per_model_metrics.items():
        per_model[model] = {}
        for metric, vals in metrics.items():
            mean = st.mean(vals)
            pop_mean = population[metric]["mean"]
            per_model[model][metric] = {
                "mean": round(mean, 4),
                "n": len(vals),
                "std": round(st.stdev(vals), 4) if len(vals) > 1 else 0,
                "vs_population": round(mean - pop_mean, 4),
            }

    out = {
        "n_models": len(per_model),
        "n_total_responses": sum(p["word_count"]["n"] for p in per_model.values()),
        "population": population,
        "per_model": per_model,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(out, f, indent=2)

    # Pretty print
    print(f"Saved: {OUTPUT}")
    print()
    print(f"Population averages (n={out['n_total_responses']} responses across {out['n_models']} models):")
    for metric, p in population.items():
        print(f"  {metric:<25} mean={p['mean']:.3f}  median={p['median']:.3f}  std={p['std']:.3f}")
    print()
    print(f'{"Model":<28}{"word_ct":<10}{"unique_wr":<11}{"bigram_rep":<12}{"sent_var":<10}')
    print("-" * 70)

    # Sort by unique_word_ratio (proxy for prose quality)
    sorted_models = sorted(per_model, key=lambda m: -per_model[m]["unique_word_ratio"]["mean"])
    for m in sorted_models:
        d = per_model[m]
        wc = d["word_count"]["mean"]
        uwr = d["unique_word_ratio"]["mean"]
        rep = d["bigram_repetition"]["mean"]
        var = d["sentence_length_var"]["mean"]
        print(f'  {m:<26}{wc:>5.0f}     {uwr:.3f}        {rep:.3f}       {var:.1f}')


if __name__ == "__main__":
    main()
