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

We validated the rule-based scoring against **725 swipe pairs** from real RP sessions — moments where users rejected one response and accepted another for the same context. Ideal rubric: scores accepted higher than rejected.

**Results:**

| Signal | Accepted wins | Tied | Rejected wins | Verdict |
|--------|--------------|------|--------------|---------|
| Objective metrics (cliches, rhythm, diversity) | 33.2% | 41.0% | 25.8% | Marginal signal (p<0.01 but only 7.4pt edge) |
| Slop detectors (rule-based patterns) | 28.4% | 46.5% | 25.1% | Not statistically significant |

**What this means:** Our rule-based signals have **some** correlation with user preference, but it's weak. The large "tied" rate (41-46%) shows our detectors often can't differentiate between pairs that users clearly preferred one over the other.

**Where the rubric works best:**
- `mha_nsfw`: 60% objective agreement — rubric captures real quality differences
- `victoria_nsfw`: 59% slop agreement — ERP responses with more cliches ARE less preferred

**Where the rubric fails:**
- `katarina_nsfw`: 5% slop agreement — cliche-heavy but users still accepted
- `rhoda_*`: ~22-26% agreement across branches — literary prose is resistant to rule-based analysis
- Russian pairs: 22% objective agreement — rubric calibrated mostly for English

**The "shorter = wins" bias:**
- When accepted was shorter, rubric agreed 44% of the time
- When accepted was longer, rubric only agreed 21%
- The rubric is biased toward short clean prose, which isn't always what users want

**Implications:**
1. The LLM judge (flaw hunter) may be doing the actual work — rule-based signals alone are insufficient
2. User preferences include factors our rubric doesn't capture (emotional beats, character fit, scene continuation logic)
3. Style-matching matters — judging a 6,000-char literary response by the same rubric as a 1,500-char punchy response is apples-to-oranges

See [`results/rubric_validation.json`](results/rubric_validation.json) for full data.

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
