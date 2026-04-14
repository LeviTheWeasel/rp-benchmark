# RP-Bench

Roleplay quality benchmark for LLMs. Measures what existing benchmarks don't — character consistency, user agency respect, lorebook integration, prose craft, and genre-specific skills across 27 dimensions.

**Dataset & Leaderboard:** [lazyweasel/roleplay-bench on HuggingFace](https://huggingface.co/datasets/lazyweasel/roleplay-bench)

## Why?

Every RP benchmark is either vibes-based ("I tried it and it felt good") or tests generic writing quality. RP-Bench tests what actually matters in a roleplay session:

- Does the model **respect your agency** or write your character for you?
- Does it **follow the character card** or drift into generic behavior?
- Does it **remember** what happened 50 turns ago?
- Does it **use lorebook context** naturally or dump it as exposition?
- Does it **track time** consistently across a long session?
- Is the prose actually **good** or just slop?
- Does the world **push back** or bend to the protagonist?

## Current Leaderboard (ELO)

Based on 1,507 pairwise matchups across 58 scenarios (30 English + 28 Russian), judged by Claude Sonnet in flaw-hunting mode:

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

Opus beats DeepSeek 58.2% head-to-head and Qwen 91.3%. Has the highest bonus rate per response (1.55 — finds novel specific details most often).

**Tension between scoring modes:** Opus wins on subjective quality (flaw hunter), but uses MORE cliches than GPT-4.1 per rule-based detection. GPT-4.1 wins on objective metrics despite losing on judge-based quality. See all four leaderboards in [`results/`](results/).

## Four Scoring Modes

The benchmark supports multiple complementary approaches to avoid LLM-judge generosity bias:

| Mode | What it does | Why it matters |
|------|-------------|---------------|
| **Standard** | 1-5 score per dimension | Backwards compatible, dimension breakdown |
| **Flaw Hunter** | Start at 100, deduct for each quoted flaw | Forces specific critique |
| **Comparative** | A/B pairwise with reasoning | Basis for ELO ratings |
| **Objective + Slop** | Rule-based pattern detection | Can't be gamed by judge mood |

Objective metrics include:
- 120+ curated AI-cliché detector ("ministrations", "breath hitched", "clicked into place")
- 10 rule-based slop pattern detectors (throat-clearing openers, filter words, fragmentary choppiness, negation-assertion, etc.)
- Vocabulary diversity (type-token ratio)
- Sentence rhythm variance
- Within-response repetition

Final leaderboard uses **relative percentile ranking** — each model's score is derived from how often it beats other models head-to-head on the same scenario. This produces real differentiation (48.9 point spread) rather than clustering at the top of an absolute scale.

## Quick Start

```bash
git clone https://github.com/LeviTheWeasel/rp-benchmark
cd rp-benchmark
pip install -r requirements.txt
cp .env.example .env  # Add your OpenRouter API key
```

```bash
# Quick smoke test (1 model, 1 scenario, 1 judge)
python3 run.py test

# Run the benchmark with flaw hunter mode (recommended)
python3 run.py run --types completion --judge-mode flaw_hunter

# Multi-turn benchmark with challenge turns
python3 run.py multiturn --turns 20 --max-seeds 4

# Adversarial seeds — test specific failure modes
python3 run.py multiturn --adversarial --turns 12

# ELO leaderboard from existing run
python3 analyze_elo.py results/run_XXXXXXXX.json

# Combined score (flaw hunter + objective + slop)
python3 analyze_combined.py
python3 analyze_relative.py
```

## Rubric: 27 Dimensions, 3 Tiers

### Tier 1: Fundamentals (40%)
Agency Respect, Instruction Adherence, Continuity, Length Calibration, Distinct Voices, Scene Grounding

### Tier 2: Quality Control (35%)
Anti-Purple Prose, Anti-Repetition, Anti-Sycophancy, Anti-Perfection, Show Don't Tell, Subtext, Pacing, Imperfect Coping

### Tier 3: Genre Craft (25%)
Earned Intimacy, Atmospheric Dread, Structural Comedy, Excavated Truth, Spatial Precision, Lived-In Worlds, Information Architecture, Structural Inevitability, Threshold Logic, Emotional Residue, Erotic Craft, Context Integration, Temporal Reasoning

Full rubric with 1-5 scoring scales: [`analysis/scoring_rubric_v2.md`](analysis/scoring_rubric_v2.md)

## How It Works

```
Scenario + Character Card + Lorebook
         |
         v
   Test Model (via OpenRouter)
         |
         v
   Generated RP Response
         |
    +----------+----------+----------+
    |          |          |          |
    v          v          v          v
 Flaw     Objective    Slop     Comparative
 Hunter   Metrics    Detectors    Judge
    |          |          |          |
    +----------+----------+----------+
                    |
                    v
       Percentile Rankings + ELO
                    |
                    v
           Final Leaderboard
```

## Multi-Turn Benchmarking

Single-turn completions cluster models in narrow bands (everyone can write one decent response). The real differentiation shows in multi-turn sessions:

- **20 turns per session** with scripted challenge turns at specific points
- **User simulator** (Gemini Flash) plays the user role naturally
- **Session judge** evaluates the full conversation holistically
- **6 session-level dimensions**: consistency over time, degradation resistance, narrative momentum, adaptive responsiveness, agency respect (session), temporal reasoning

Multi-turn reveals **degradation patterns** that single-turn hides — models that start strong but fall apart over 20 turns.

## Adversarial Seeds

8 scenarios specifically designed to break models in targeted ways:

| Seed | Failure Target |
|------|---------------|
| agency_bait | User invites ambiguity — does AI write user's reactions? |
| contradictory_lore | Two lorebook entries contradict — can AI navigate honestly? |
| passive_user | AI must create narrative momentum alone |
| impossible_physics | User demands physics-breaking thing — does AI sycophant? |
| time_pressure | 15-minute heist — does AI track time precisely? |
| subtle_ooc | Trauma never asked about — does AI trauma-dump? |
| character_break_bait | Stoic character, user baits emotional reaction |
| genre_shift | User tries horror→action/comedy — can AI hold genre? |

## Adversarial Results

From a run of 7 models × 8 adversarial seeds × 12 turns (56 sessions, judged by Claude Sonnet 4):

| Rank | Model | Mean | Std | Min | Degrad% |
|------|-------|------|-----|-----|---------|
| #1 | Claude Sonnet 4.5 | **4.44** | 0.18 | 4.2 | 0 |
| #2 | DeepSeek v3.2 | 4.36 | 0.13 | 4.2 | 0 |
| #3 | GPT-4.1 | 4.34 | 0.11 | 4.2 | 0 |
| #4 | GLM 4.7 | 4.33 | 0.21 | 4.1 | 0 |
| #5 | Qwen 3.5 Flash | 4.28 | 0.13 | 4.1 | 0 |
| #6 | Gemini 2.5 Flash | 4.24 | 0.09 | 4.1 | 0 |
| #7 | Mistral Small Creative | 4.19 | 0.19 | **3.8** | 12% |

(Opus 4.6 not in this run — next adversarial pass will include it.)

**Score compression is the headline.** The standard leaderboard spans 48.9 ELO points; adversarial scores span 0.25 points (4.19–4.44). Adversarial seeds successfully push every model toward the same floor, which is exactly what they're meant to do — strong models stop looking impressive when agency is dangled as bait, lore contradicts itself, or the user goes passive.

**Quality trajectory** (mean early → late) separates models more cleanly than raw overall score:

| Model | Early | Mid | Late | Δ late−early |
|-------|-------|-----|------|-------------|
| Claude Sonnet 4.5 | 4.15 | 4.42 | 4.51 | **+0.36** |
| DeepSeek v3.2 | 3.99 | 4.39 | 4.46 | **+0.48** |
| GPT-4.1 | 4.19 | 4.34 | 4.39 | +0.20 |
| GLM 4.7 | 4.12 | 4.39 | 4.28 | +0.15 |
| Mistral Small | 4.16 | 4.26 | 4.14 | −0.02 |
| Gemini 2.5 Flash | 4.20 | 4.20 | 4.15 | −0.05 |

Sonnet 4.5 and DeepSeek *improve* over 12 turns of adversarial pressure. Gemini, Qwen, and Mistral flatten or slightly regress. This is a better discriminator than the mean-score ranking.

**Dimension weaknesses** (mean across all 56 sessions):

- Weakest: `degradation_resistance` (4.15), `temporal_reasoning` (4.24)
- Strongest: `agency_respect` (4.74), `consistency_over_time` (4.59)

Models have internalized "don't write the user's actions," but holding time and quality across 12 turns under adversarial pressure is where they still struggle.

**Per-seed worst cases:**
- `adv_character_break_bait_07` → Mistral crashed to **3.8** (the only sub-4.0 score in the whole run)
- `adv_passive_user_03` was the hardest seed overall (mean 4.17, max 4.3) — nobody handled the passive-user failure mode well
- `adv_time_pressure_05` — even #1 Sonnet 4.5 was the worst performer (4.3)

Regenerate with `python3 analyze_adversarial.py`. Data: [`results/adversarial_analysis.json`](results/adversarial_analysis.json).

### Adversarial ELO (recovering spread)

Mean overall scores collapse into a 0.25-point band, hiding real differences. Converting the same sessions into pairwise matchups per seed (higher score wins; dimension-sum tiebreak) and running standard ELO recovers **259 rating points** of spread:

| Rank | Model | ELO | ± | Mean overall |
|------|-------|-----|---|--------------|
| #1 | Claude Sonnet 4.5 | **1639** | 24 | 4.44 |
| #2 | DeepSeek v3.2 | 1610 | 22 | 4.36 |
| #3 | GPT-4.1 | 1590 | 24 | 4.34 |
| #4 | GLM 4.7 | 1486 | 23 | 4.33 |
| #5 | Mistral Small Creative | 1419 | 26 | 4.19 |
| #6 | Gemini 2.5 Flash | 1392 | 22 | 4.24 |
| #7 | Qwen 3.5 Flash | 1364 | 20 | 4.28 |

Three tiers emerge: Sonnet/DeepSeek/GPT-4.1 at the top (within 50 ELO of each other, H2H 44–62%), GLM in the middle, and Qwen/Gemini/Mistral clustered at the bottom. Sonnet 4.5 wins 94% head-to-head against Qwen but only 56% against DeepSeek — the top three are genuinely close.

Note the rank-order swap vs mean-overall: **Mistral ranks ahead of Gemini and Qwen in ELO** despite having the lowest mean score. Its dimension-level signal is stronger per matchup — mean is dragged down by one 3.8 outlier on `character_break_bait`.

Regenerate with `python3 analyze_adversarial_elo.py`. Data: [`results/adversarial_elo.json`](results/adversarial_elo.json).

## CLI Reference

```bash
# Standard benchmark run
python3 run.py run [options]
  --models MODEL [...]         # Which models to test
  --judges JUDGE [...]         # Which judges to use
  --judge-mode MODE            # standard | flaw_hunter | comparative
  --types TYPE [...]           # completion, preference, consistency, ooc, degradation
  --language {en,ru}           # Filter scenarios by language
  --max N                      # Limit scenarios
  --runs N                     # Independent runs per scenario (for CIs)
  --charts                     # Auto-generate charts after run

# Multi-turn benchmark
python3 run.py multiturn [options]
  --models MODEL [...]
  --turns N                    # Turns per session (default 20)
  --max-seeds N                # Number of seeds to test
  --seeds SEED [...]           # Specific seed IDs
  --adversarial                # Use adversarial seeds

# Analysis
python3 analyze_elo.py [run.json]          # ELO leaderboard
python3 analyze_combined.py [run.json]     # Combined flaw+objective+slop
python3 analyze_relative.py [run.json]     # Percentile ranking
python3 aggregate_flaw_hunter.py [run.json] # Flaw hunter aggregation

# Results
python3 run.py leaderboard --view full
python3 run.py charts
python3 run.py list-models
```

## Adding Models

Edit `harness/config.py`:

```python
TEST_MODELS = {
    "your_model": "provider/model-id",  # OpenRouter model ID
}
```

Find model IDs at [openrouter.ai/models](https://openrouter.ai/models).

## Scenario Types

| Type | What it tests | Needs generation? |
|------|--------------|-------------------|
| `completion` | Model generates RP, judges score it | Yes |
| `ooc_correction` | Known failures from real chats — should score low | No (judge-only) |
| `degradation` | Early vs late responses from same conversation | No (judge-only) |
| `preference` | A/B from user swipes — should pick same winner | No (judge-only) |
| `consistency` | Character voice across long conversation gaps | No (judge-only) |

## Synthetic Seeds

8 standard + 8 adversarial = 16 standalone scenarios for benchmarking without private data. The standard seeds cover: fantasy slowburn, arctic horror, school comedy, tavern ERP, swamp politics, firefighter tragedy, ship AI thriller, bakery slowburn.

## Web UI — Human Validation Arena

Arena and rubric-scoring web app for human calibration:

```bash
cd web
npm install
npm run dev -- -p 3333
# Open http://localhost:3333
```

- **Arena**: blind A/B comparison of model responses
- **Rubric Score**: rate individual responses across 21 dimensions
- **Results**: aggregate vote data

Votes persist server-side to `data/votes.jsonl`. 271 matchups preloaded from the benchmark run.

## Empirical Validation (Honest Findings)

We validated all scoring signals against real user preferences — pairs of responses where users rejected one and accepted another for the same context.

### Signal vs User Preference

| Signal | Agreement | Ties | Disagree | Verdict |
|--------|-----------|------|----------|---------|
| Objective metrics (length-normalized) | 42.3% | 25.9% | 31.7% | Weak signal (p<0.01) |
| Slop detectors (density-normalized) | 30.6% | 42.5% | 26.9% | Not significant |
| **Flaw Hunter (LLM judge, sampled)** | **38.7%** | **10.7%** | **50.7%** | **Not significant, inverted-leaning** |

**Rule-based signals weakly track user preference. The LLM judge does NOT.**

### What This Reveals

The flaw hunter validation (75 pairs, $10) showed:
- **Judge disagreed with users more often than it agreed** (50.7% vs 38.7%)
- When the judge disagreed, it did so confidently (avg delta -6.68 points)
- `mha_rpg`: 100% agreement (judge matches users perfectly on this style)
- `rhoda_main`: 0% agreement (judge actively disagrees on literary slowburn)
- `lucian_virelia`: 0% agreement (Opus 4.6 chats the user loved, but judge nitpicks)

### Possible Reasons

1. **The "accepted" label is noisy** — users sometimes accept the second try because they're tired, not because it's better
2. **Judges have their own aesthetic preferences** — Claude Sonnet as judge prefers certain styles that don't match what RPers actually want
3. **Context stripped away** — judging a response in isolation misses character history, scene continuity, and relationship dynamics that users evaluate holistically
4. **Flaw-counting is inherently flawed** — some "purple prose" or "recycled descriptions" are intentional stylistic choices users appreciate

### Where the Rubric Does Work

Despite these limitations, meaningful patterns emerge:
- **NSFW/ERP evaluation**: both objective (60%) and slop (59%) agree with users on `mha_nsfw` and `victoria_nsfw` — cliche density matters more in explicit content
- **Length normalization halved the length-bias gap** — from 23pt to 12pt between "short wins" and "long wins"
- **English agreement jumped to 45%** after length normalization

### What This Means For The Leaderboard

**Our model rankings still tell a story — but it's "how models compare to each other under our specific rubric," not "what users actually prefer."** The rubric is an internally consistent lens with known biases, not a ground truth. Users interested in model selection should:
1. Check multiple leaderboards (ELO, Flaw Hunter, Relative) — they disagree
2. Look at per-source/per-style scores, not just overall
3. Trust human-validated outputs (the arena) over automated ones

See [`results/rubric_validation.json`](results/rubric_validation.json) and [`results/flaw_hunter_validation.json`](results/flaw_hunter_validation.json) for full data.

### Can We Learn a Rubric From Swipe Data?

We trained classifiers on 1,621 swipe pairs (24 features × symmetric +/- examples) to see whether **combinations** of features predict user preference where individual features could not.

| Model | 5-fold CV Accuracy |
|-------|--------------------|
| Logistic Regression | 57.1% (± 6.1%) |
| Random Forest | 63.2% (± 9.1%) |
| Gradient Boosting | **63.6% (± 8.6%)** |

Non-linear models beat the linear baseline by ~6 points, confirming that **feature interactions matter** — no single metric is predictive, but the joint shape of "paragraph rhythm × sensory density × dialogue mix" weakly tracks preference. Top RF feature importance: `avg_paragraph_length` (0.154) — ~3× anything else.

Per-source variance is large: `mha_rpg_b125` hits 70% agreement, `rhoda_b3_loom` only 46%. Some genres are learnable from these features; literary slowburn isn't. See [`learn_rubric_classifier.py`](learn_rubric_classifier.py) and [`results/learned_rubric.json`](results/learned_rubric.json).

> **ML runs in this repo** should set `n_jobs=1` in sklearn and launch with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1` — otherwise joblib/BLAS thread pools can balloon memory well past dataset size.

## Rubric Origins

The scoring dimensions are derived from:
- **[HawThorne V.2](https://github.com/Coneja-Chibi/The-HawThorne-Directives)** — A SillyTavern preset with 21 genre Directors, each defining prose voice, failure modes, and quality checks
- **Community slop-detection presets** — The "Gods' Prose" high-effort protocol with 10+ banned pattern categories
- **Real user feedback** — 87 OOC corrections from actual RP sessions across 12 source chats (English + Russian)
- **Swipe analysis** — 142 rejected/accepted response pairs

## Data Sources

12 real chat sessions across 6 characters and 5+ models:
- 6 English chats (Valen, Strovolos, Sukuna, Couch Smothering, Ryujin High, Bell)
- 6 Russian chats (Lucian/Virelia, Agora Imperial, Valdrian, Narlos, Rowena/Isekai, Exiled King)

Approximately 3,700 messages total. Raw chat content is **not** published — only derived signals (swipe comparisons, OOC correction patterns, scene summaries with character info).

## Project Structure

```
harness/                       # Python evaluation harness
  config.py                    # Model IDs, API settings
  api.py                       # OpenRouter client
  runner.py                    # Generate + judge pipeline
  multiturn.py                 # Multi-turn session runner
  objective_metrics.py         # Cliche detector, rhythm analysis
  slop_detectors.py            # 10 rule-based slop pattern detectors
  aggregate.py                 # Leaderboard aggregation
  visualize.py                 # Seaborn chart generation
prompts/                       # Judge system prompts
  judge_claude.md              # Claude-optimized (standard 1-5)
  judge_gpt.md                 # GPT-optimized (standard 1-5)
  judge_flaw_hunter.md         # 100-point deduction mode
  judge_comparative.md         # A/B pairwise for ELO
analysis/                      # Rubric definitions
hf_dataset/                    # HuggingFace export + seeds
  seeds/seeds.json             # 8 standard seeds
  seeds/adversarial_seeds.json # 8 adversarial seeds
results/                       # Run results and charts
web/                           # Human validation web UI
analyze_elo.py                 # ELO ratings from matchups
analyze_combined.py            # Combined multi-signal score
analyze_relative.py            # Percentile ranking
aggregate_flaw_hunter.py       # Flaw hunter leaderboard
```

## License

CC BY-NC 4.0 — Free for non-commercial research and community use.
