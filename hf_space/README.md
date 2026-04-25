---
title: RP-Bench Leaderboard
emoji: 🎭
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
pinned: false
license: cc-by-nc-4.0
---

# RP-Bench Leaderboard

Interactive view of the [RP-Bench](https://github.com/LeviTheWeasel/rp-benchmark) findings: Bayesian community ELO, multi-turn judge scores, flaw hunter rankings, cost efficiency, behavioral metrics, cross-method correlations, and per-model profile cards.

Data is pulled from the [`lazyweasel/roleplay-bench`](https://huggingface.co/datasets/lazyweasel/roleplay-bench) dataset on startup, so the Space stays in sync with the source repo.

## Three findings to read first

1. **LLM judges disagree with humans.** Spearman rho between Bayesian community ELO and every LLM-judge method is between −0.31 and −0.07.
2. **Engagement and reliability are orthogonal.** Community ranks Gemma / Mistral / Gemini at the top; frontier closed models (Opus, Sonnet, GPT-4.1) lead on rule-following but trail on engagement.
3. **Position bias breaks single-pass pairwise.** 64% of LLM-judged pair comparisons flip when A/B is swapped — bidirectional evaluation is mandatory.

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

The app prefers local data files (when run from inside the rp-benchmark repo) and falls back to the HF dataset.

## License

CC BY-NC 4.0 — same as the parent benchmark.
