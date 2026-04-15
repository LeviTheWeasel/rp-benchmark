---
language:
- en
- ru
tags:
- roleplay
- benchmark
- creative-writing
- llm-evaluation
- character-ai
- sillytavern
- multilingual
pretty_name: RP-Bench
size_categories:
- n<1K
task_categories:
- text-generation
license: cc-by-nc-4.0
configs:
- config_name: seeds
  data_files:
  - split: train
    path: seeds/train.parquet
- config_name: adversarial_seeds
  data_files:
  - split: train
    path: adversarial_seeds/train.parquet
- config_name: rubric
  data_files:
  - split: train
    path: rubric/train.parquet
- config_name: results
  data_files:
  - split: train
    path: results/train.parquet
- config_name: leaderboard
  data_files:
  - split: train
    path: leaderboard/train.parquet
- config_name: elo
  data_files:
  - split: train
    path: elo/train.parquet
- config_name: flaw_hunter
  data_files:
  - split: train
    path: flaw_hunter/train.parquet
default: true
---

# RP-Bench: Roleplay Quality Benchmark for LLMs

A multi-dimensional evaluation framework for measuring how well LLMs perform in roleplay scenarios — not just writing quality, but character consistency, user agency respect, lorebook integration, temporal reasoning, and genre-specific craft.

[![Community votes](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Farena.l3vi4th4n.ai%2Fapi%2Fstats&query=%24.arena&label=Community%20arena%20votes&color=blue&cacheSeconds=300)](https://arena.l3vi4th4n.ai/arena) [![Voters](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Farena.l3vi4th4n.ai%2Fapi%2Fstats&query=%24.voters&label=Voters&color=purple&cacheSeconds=300)](https://arena.l3vi4th4n.ai/results) [![Pairs covered](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Farena.l3vi4th4n.ai%2Fapi%2Fstats&query=%24.pairs_covered&label=Pairs%20covered&color=green&cacheSeconds=300)](https://arena.l3vi4th4n.ai/results)

The LLM-as-judge signals in this benchmark disagree with real users about half the time. We're calibrating against human preferences via a public blind-arena. Help out at **[arena.l3vi4th4n.ai](https://arena.l3vi4th4n.ai/arena)** — each vote takes ~30 seconds.

## Current Leaderboards

Based on 1,507 pairwise matchups across 58 scenarios (30 English + 28 Russian). The three leaderboards tell different but complementary stories.

### ELO Ratings (head-to-head dominance)

| Rank | Model | ELO | Tier |
|------|-------|-----|------|
| **#1** | **Claude Opus 4.6** | **1706** | **S+** |
| #2 | DeepSeek v3.2 | 1638 | S |
| #3 | Claude Sonnet 4.5 | 1541 | A |
| #4 | GPT-4.1 | 1523 | A |
| #5 | GLM 4.7 | 1492 | A |
| #6 | Gemini 2.5 Flash | 1408 | B |
| #7 | Mistral Small Creative | 1360 | C |
| #8 | Qwen 3.5 Flash | 1332 | C |

### Flaw Hunter (subjective quality, 0-100)

Score = 100 minus deductions for quoted flaws found by judge.

| Rank | Model | Score | Fatal Flaws | Avg Bonuses |
|------|-------|-------|-------------|-------------|
| #1 | Claude Opus 4.6 | 72.1 | 0.15 | **1.55** |
| #2 | DeepSeek v3.2 | 68.8 | 0.07 | 1.12 |
| #3 | Claude Sonnet 4.5 | 67.1 | **0.04** | 1.21 |
| #4 | GLM 4.7 | 65.6 | 0.11 | 1.37 |
| #5 | GPT-4.1 | 65.5 | **0.04** | 1.12 |
| #6 | Gemini 2.5 Flash | 60.0 | 0.18 | 0.75 |
| #7 | Mistral Small Creative | 59.6 | 0.14 | 1.04 |
| #8 | Qwen 3.5 Flash | 58.3 | 0.16 | 0.93 |

### Relative Percentile (objective + slop detectors combined)

Percentile = average share of other models this one beats on rule-based metrics (cliche detection, vocabulary diversity, sentence rhythm, slop patterns).

| Rank | Model | Combined % | FlawHunt % | Objective % | Slop % |
|------|-------|-----------|-----------|-------------|--------|
| **#1** | **GPT-4.1** | **69.4** | 56.5 | **78.5** | **85.9** |
| #2 | Claude Sonnet 4.5 | 67.7 | 62.6 | 72.4 | 73.1 |
| #3 | DeepSeek v3.2 | 63.6 | 69.0 | 60.9 | 55.4 |
| #4 | Gemini 2.5 Flash | 50.1 | 37.3 | 58.0 | 68.0 |
| #5 | GLM 4.7 | 50.0 | 49.0 | 55.6 | 46.5 |
| #6 | Claude Opus 4.6 | 43.6 | **72.6** | 20.4 | 9.1 |
| #7 | Qwen 3.5 Flash | 29.9 | 26.2 | 31.2 | 36.2 |
| #8 | Mistral Small Creative | 25.3 | 27.3 | 22.2 | 24.5 |

### Key Insight: Three Signals Disagree

These leaderboards reveal a genuine tension:

- **Claude Opus 4.6** dominates subjective quality (ELO #1, Flaw Hunter #1) but uses the most community-flagged cliches (Slop percentile: 9.1 — dead last)
- **GPT-4.1** wins on objective metrics (cleanest prose by rules) but is only mid-pack on judge evaluation
- **DeepSeek v3.2** is the most balanced — top 3 on every signal

Which leaderboard matters depends on what you're measuring: "genuinely good prose" (ELO) vs "clean prose by community standards" (Relative).

### Russian vs English

| Model | English | Russian | RU-EN Δ |
|-------|---------|---------|---------|
| Claude Opus 4.6 | 70.2 | 73.6 | +3.3 |
| DeepSeek v3.2 | 65.9 | 71.3 | +5.4 |
| Claude Sonnet 4.5 | 64.3 | 69.6 | +5.3 |
| GLM 4.7 | 64.7 | 66.5 | +1.8 |
| GPT-4.1 | 65.0 | 65.9 | +0.8 |
| Gemini 2.5 Flash | 56.9 | 62.8 | **+6.0** |
| Mistral Small Creative | 59.1 | 60.0 | +0.9 |
| Qwen 3.5 Flash | 58.6 | 58.1 | **−0.5** |

Every model except Qwen scores higher on Russian. Gemini Flash has the biggest RU boost. Qwen is the only model where English is stronger.

## Adversarial Multi-Turn Results

A separate run of 7 models × 8 adversarial seeds × 12 turns (56 sessions, judged by Claude Sonnet 4):

| Rank | Model | Mean | Std | Min | Degrad% |
|------|-------|------|-----|-----|---------|
| #1 | Claude Sonnet 4.5 | **4.44** | 0.18 | 4.2 | 0 |
| #2 | DeepSeek v3.2 | 4.36 | 0.13 | 4.2 | 0 |
| #3 | GPT-4.1 | 4.34 | 0.11 | 4.2 | 0 |
| #4 | GLM 4.7 | 4.33 | 0.21 | 4.1 | 0 |
| #5 | Qwen 3.5 Flash | 4.28 | 0.13 | 4.1 | 0 |
| #6 | Gemini 2.5 Flash | 4.24 | 0.09 | 4.1 | 0 |
| #7 | Mistral Small Creative | 4.19 | 0.19 | **3.8** | 12% |

(Opus 4.6 not in this run — separate standard-seed multi-turn has it at 4.58 mean.)

### Score Compression Is the Headline

The standard leaderboard spans 48.9 ELO points; adversarial scores span **0.25 points** (4.19–4.44). Adversarial seeds push every model toward the same floor — strong models stop looking impressive when agency is baited, lore contradicts, or the user goes passive. This is the seeds working as designed.

### Quality Trajectory Is a Better Discriminator

Mean score barely separates the field, but trajectory across 12 turns does:

| Model | Early | Mid | Late | Δ late−early |
|-------|-------|-----|------|-------------|
| Claude Sonnet 4.5 | 4.15 | 4.42 | 4.51 | **+0.36** |
| DeepSeek v3.2 | 3.99 | 4.39 | 4.46 | **+0.48** |
| GPT-4.1 | 4.19 | 4.34 | 4.39 | +0.20 |
| GLM 4.7 | 4.12 | 4.39 | 4.28 | +0.15 |
| Mistral Small | 4.16 | 4.26 | 4.14 | −0.02 |
| Gemini 2.5 Flash | 4.20 | 4.20 | 4.15 | −0.05 |

Sonnet 4.5 and DeepSeek *improve* under sustained adversarial pressure. Gemini, Qwen, and Mistral flatten or regress. If you're picking a model for long sessions where things get messy, this matters more than the mean.

### Dimension Weaknesses (all models, all seeds)

- **Weakest:** `degradation_resistance` (4.15), `temporal_reasoning` (4.24)
- **Strongest:** `agency_respect` (4.74), `consistency_over_time` (4.59)

Models have internalized "don't write the user's actions" — agency respect is near-saturated. Holding quality and time consistency across 12 adversarial turns is where the remaining headroom lives.

### Worst-Case Cells

- `adv_character_break_bait_07` → Mistral crashed to **3.8** (only sub-4.0 in the run)
- `adv_passive_user_03` was the hardest seed overall (mean 4.17, max 4.3) — nobody aced "create narrative momentum alone"
- Even #1 Sonnet 4.5 was the worst performer on `adv_time_pressure_05`

Full aggregated data: [`results/adversarial_analysis.json`](results/adversarial_analysis.json).

### Adversarial ELO

Mean scores compress to a 0.25-point band. Converting the same sessions into per-seed pairwise matchups and running standard ELO recovers **259 rating points** of spread:

| Rank | Model | ELO | Mean overall |
|------|-------|-----|--------------|
| #1 | Claude Sonnet 4.5 | **1639** | 4.44 |
| #2 | DeepSeek v3.2 | 1610 | 4.36 |
| #3 | GPT-4.1 | 1590 | 4.34 |
| #4 | GLM 4.7 | 1486 | 4.33 |
| #5 | Mistral Small Creative | 1419 | 4.19 |
| #6 | Gemini 2.5 Flash | 1392 | 4.24 |
| #7 | Qwen 3.5 Flash | 1364 | 4.28 |

Three tiers: Sonnet/DeepSeek/GPT-4.1 at the top (H2H 44–62%), GLM in the middle, Qwen/Gemini/Mistral at the bottom. Sonnet 4.5 beats Qwen 94% head-to-head but only 56% against DeepSeek — the top three are genuinely close.

Rank-order shifts vs mean-overall: Mistral ranks **above** Gemini and Qwen in ELO despite having the lowest mean score; its dimension-level signal is stronger per matchup, dragged down by one 3.8 outlier on `character_break_bait`.

## Why RP-Bench?

Existing benchmarks (MMLU, HumanEval, MT-Bench) don't measure RP-specific skills. The RP community evaluates models through vibes and anecdotal testing. RP-Bench provides structured, reproducible evaluation using:

- **Real quality signals** from actual RP sessions (swipes, OOC corrections, quality degradation patterns)
- **27 scoring dimensions** across 3 tiers, derived from the HawThorne V.2 preset + community slop-detection protocols
- **Four scoring modes**: standard (1-5), flaw hunter (100-point deduction), comparative (ELO-ready), rule-based slop detectors
- **Multi-turn sessions** with scripted challenge turns that expose degradation
- **Adversarial seeds** targeting specific failure modes (agency violations, genre shifts, physics sycophancy, etc.)
- **Bilingual** — English and Russian RP evaluation
- **Objective + subjective** — LLM-judge signals combined with rule-based pattern detection that can't be gamed

## Rubric: 27 Dimensions, 3 Tiers

### Tier 1: Fundamentals (40% weight)
| Dimension | What it measures |
|-----------|-----------------|
| Agency Respect | Don't hijack the user's character |
| Instruction Adherence | Follow character card, POV, tense, system prompt |
| Continuity | Remember names, events, injuries, promises |
| Length Calibration | Match response length to scene weight |
| Distinct Voices | NPCs sound different from each other |
| Scene Grounding | Spatial coherence — can you picture the room? |

### Tier 2: Quality Control (35% weight)
| Dimension | What it measures |
|-----------|-----------------|
| Anti-Purple Prose | Prose serves the story, not itself |
| Anti-Repetition | Fresh descriptions, no recycled phrases |
| Anti-Sycophancy | World pushes back, doesn't bend to protagonist |
| Anti-Perfection | Characters are realistically imperfect |
| Show Don't Tell | Emotions through behavior, not narration |
| Subtext & Indirection | Gap between what's said and what's meant |
| Pacing & Restraint | Meaningful moments breathe |
| Imperfect Coping | Messy vulnerability, not stoic composure |

### Tier 3: Genre Craft (25% weight)
| Dimension | Applies when |
|-----------|-------------|
| Earned Intimacy | Romance/attraction scenes |
| Atmospheric Dread | Horror/supernatural scenes |
| Structural Comedy | Comedy/absurdity scenes |
| Excavated Truth | Drama/difficult decisions |
| Spatial Precision | Action/combat scenes |
| Lived-In Worlds | Worldbuilding/magic/travel |
| Information Architecture | Mystery/thriller scenes |
| Structural Inevitability | Tragedy scenes |
| Threshold Logic | Surreal/absurdist scenes |
| Emotional Residue | Trauma callbacks/intense emotion |
| Erotic Craft | Explicit sexual content |
| Context Integration | Lorebook/world info usage |

## Dataset Structure

### Seeds (`seeds/`)
8 synthetic scenario templates covering different genres and difficulty levels. Each seed includes:
- Character card (name, detailed personality, physical description)
- User persona
- Opening message
- Initial user input
- Evaluation focus dimensions
- Recommended turn count

**Genres covered:** Fantasy slowburn, Arctic horror, School comedy, ERP, Political worldbuilding, Modern tragedy, Sci-fi thriller, Modern romance

### Rubric (`rubric/`)
Full scoring rubric with definitions, failure modes, and 1-5 scale descriptions for all 26 dimensions.

### Results (`results/`)
Leaderboard data from benchmark runs: per-model, per-dimension scores with inter-judge agreement statistics.

### Harness (`harness/`)
Python evaluation harness source code. Uses OpenRouter API for model-agnostic benchmarking.

## How to Use

### Run the benchmark yourself
```bash
git clone https://github.com/LeviTheWeasel/rp-benchmark
cd rp-benchmark
pip install -r requirements.txt
cp .env.example .env  # Add your OpenRouter API key
python run.py run --types completion --charts
python run.py leaderboard --view full
```

### Load the dataset
```python
from datasets import load_dataset
ds = load_dataset("lazyweasel/roleplay-bench")
```

## Methodology

### Evaluation Pipeline
1. **Generate**: Send scenario context + character card + lorebook to test model via OpenRouter
2. **Judge**: Two independent judge models (Claude Sonnet, GPT-4.1) score the response on all applicable dimensions
3. **Aggregate**: Cross-judge average, per-dimension rankings, confidence intervals

### Rubric Origins
The scoring dimensions are derived from:
- **HawThorne V.2** — A SillyTavern preset with 21 genre "Directors," each defining prose voice, failure modes, and quality checks
- **Real user feedback** — 24 OOC corrections from actual RP sessions, categorized by failure type
- **Swipe analysis** — 34 rejected/accepted response pairs showing what users actually prefer

### What Makes This Different from MiniMax Role-Play Bench?
| | MiniMax RPB | RP-Bench |
|---|---|---|
| Dimensions | 6 (basics, logic, knowledge, diversity, content logic, interaction) | 26 (fundamentals + quality control + genre craft) |
| Genre specificity | General | Per-genre scoring (romance, horror, comedy, etc.) |
| Lorebook testing | No | Yes — tests context integration with real lorebooks |
| ERP evaluation | No | Yes — Erotic Craft dimension |
| Source data | Synthetic dialogues | Real RP sessions with user-annotated quality signals |
| Evaluation approach | Negative (flooring) | Balanced (1-5 scale across all dimensions) |

## Empirical Validation (Honest Findings)

We validated all scoring signals against real user preferences — swipe pairs where users rejected one response and accepted another for the same context.

### Signal vs User Preference

| Signal | N | Agreement | Tied | Disagree | Effect |
|--------|---|-----------|------|----------|--------|
| Objective metrics (length-normalized) | 725 | 42.3% | 25.9% | 31.7% | p<0.01, weak |
| Slop detectors (density-normalized) | 725 | 30.6% | 42.5% | 26.9% | Not significant |
| **Flaw Hunter (LLM judge)** | **75** | **38.7%** | **10.7%** | **50.7%** | **Inverted-leaning** |

**Rule-based signals weakly track user preference. The LLM judge does NOT agree with users.**

### The Flaw Hunter Problem

The flaw hunter validation ($10, 75 sampled pairs) revealed:
- Judge disagreed with users more often than it agreed (50.7% vs 38.7%)
- When the judge disagreed, it did so confidently (avg delta -6.68 points)
- Per-source variance is huge: `mha_rpg` 100% agreement, `rhoda_main` 0%
- Judge-user disagreement is not random — it's systematic, suggesting the judge has its own aesthetic preferences

### Why This Might Happen

1. **"Accepted" label is noisy** — users sometimes accept the second try because they're tired or because the first was good enough, not because it was actually better
2. **Judge aesthetic bias** — Claude Sonnet as judge has preferences (economy, subtext, specific detail) that don't match what RPers actually want in-flow
3. **Missing context** — judging a response in isolation loses character history, scene continuity, and relationship dynamics that users weigh heavily
4. **Flaw-counting is reductive** — some "flaws" are intentional stylistic choices users appreciate

### Where The Rubric Does Work

- **NSFW/ERP**: Objective metrics agree at 60% on `mha_nsfw`, slop at 59% on `victoria_nsfw` — cliches matter more in explicit content
- **Length normalization worked**: reduced length bias gap from 23pt to 12pt
- **English improved to 45%** after normalization

### What This Means For Users

**Our leaderboard is "how models compare under our specific rubric," not "what users actually prefer."** The rubric is internally consistent with known biases, not ground truth. For model selection:

1. Check multiple leaderboards (ELO, Flaw Hunter, Relative) — they disagree for a reason
2. Look at per-source/per-style breakdowns
3. Weight human-validated data (the arena) over automated scoring when available

The benchmark's most reliable signal may be **not which model is #1, but which models consistently appear near the top across different scoring modes.**

## Limitations

### Data sparsity
- Source scenarios derived from 12 chat sessions by ~5 users (English + Russian)
- Small demographic slice — doesn't represent global RP community preferences
- Heavily romance-weighted (90% of completions have "romance" tag)

### Judge bias
- LLM judges (Claude, GPT) have systematic generosity bias — absolute scores cluster in 4.0-4.5 range (1-5 scale) or 85-100 range (0-100 scale)
- We mitigate by using percentile ranking, pairwise ELO, and flaw-hunter deduction mode
- Still, judges don't capture everything users care about (see empirical validation above)

### Rubric limitations
- Rubric was derived from one preset (HawThorne V.2) and community slop-detection protocols — specific aesthetic bias
- Rule-based signals have weak correlation with user preference (see validation)
- Biased toward short, clean prose — may undervalue literary slowburn styles
- Calibrated primarily for English; Russian evaluation is less validated
- No user-preference modeling — treats "good RP" as monolithic

### Synthetic seeds
- 8 standard + 8 adversarial seeds — small sample size
- Authored by project maintainers, not validated by human preference data yet
- Known not to fully differentiate strong models in single-turn mode

### Methodological caveats
- The "accepted" swipe in our data isn't necessarily the "best" — it's just the most recent regeneration when the user stopped swiping. Users sometimes give up and accept suboptimal responses.
- Multi-turn user simulator (Gemini Flash) introduces bias — a smarter user sim would test models differently
- Adversarial seeds test specific failure modes but can't cover all possible RP failure cases

### What we're NOT measuring
- Safety/harmfulness (out of scope)
- Multi-modal RP (images, voice)
- Long-context recall beyond 20 turns
- Model's ability to switch characters mid-scene
- Performance under context-compressed scenarios

## Citation

```bibtex
@dataset{rp_bench_2026,
  title={RP-Bench: Roleplay Quality Benchmark for LLMs},
  year={2026},
  url={https://huggingface.co/datasets/lazyweasel/roleplay-bench}
}
```

## License

CC BY-NC 4.0 — Free for non-commercial research and community use. No raw chat data is included.
