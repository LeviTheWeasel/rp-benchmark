# RP-Bench

Roleplay quality benchmark for LLMs. Measures what existing benchmarks don't — character consistency, user agency respect, lorebook integration, prose craft, and genre-specific skills across 26 dimensions.

**Dataset & Leaderboard:** [lazyweasel/roleplay-bench on HuggingFace](https://huggingface.co/datasets/lazyweasel/roleplay-bench)

## Why?

Every RP benchmark is either vibes-based ("I tried it and it felt good") or tests generic writing quality. RP-Bench tests what actually matters in a roleplay session:

- Does the model **respect your agency** or write your character for you?
- Does it **follow the character card** or drift into generic behavior?
- Does it **remember** what happened 50 turns ago?
- Does it **use lorebook context** naturally or dump it as exposition?
- Is the prose actually **good** or just purple?
- Does the world **push back** or bend to the protagonist?

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

# Run the benchmark
python3 run.py run --types completion --charts

# View leaderboard
python3 run.py leaderboard --view full

# Generate visualization charts
python3 run.py charts
```

## Rubric: 26 Dimensions, 3 Tiers

### Tier 1: Fundamentals (40%)
Agency Respect, Instruction Adherence, Continuity, Length Calibration, Distinct Voices, Scene Grounding

### Tier 2: Quality Control (35%)
Anti-Purple Prose, Anti-Repetition, Anti-Sycophancy, Anti-Perfection, Show Don't Tell, Subtext, Pacing, Imperfect Coping

### Tier 3: Genre Craft (25%)
Earned Intimacy, Atmospheric Dread, Structural Comedy, Excavated Truth, Spatial Precision, Lived-In Worlds, Information Architecture, Structural Inevitability, Threshold Logic, Emotional Residue, Erotic Craft, Context Integration

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
    +-----------+
    |           |
    v           v
 Claude     GPT-4.1
 (Judge)    (Judge)
    |           |
    v           v
  Scores     Scores
    |           |
    +-----+-----+
          |
          v
    Cross-judge average
    Per-dimension ranking
    Leaderboard + Charts
```

## CLI Reference

```bash
# Run benchmark
python3 run.py run [options]
  --models MODEL [MODEL ...]     # Which models to test (default: all in config)
  --judges JUDGE [JUDGE ...]     # Which judges to use (default: all)
  --types TYPE [TYPE ...]        # completion, ooc_correction, degradation, preference, consistency
  --max N                        # Limit scenarios
  --runs N                       # Independent runs per scenario (3 recommended for CIs)
  --charts                       # Auto-generate charts after run
  --view VIEW                    # overall, tiers, dimensions, full

# View results
python3 run.py leaderboard --view full
python3 run.py leaderboard --view dimensions  # Who's #1 at each dimension?

# Generate charts
python3 run.py charts
python3 run.py charts --output ~/Desktop/charts

# List configured models
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

8 standalone scenarios for benchmarking without private data:

| Seed | Genre | Difficulty |
|------|-------|-----------|
| Fantasy Slowburn | Romance/drama | Medium |
| Arctic Horror | Horror/thriller | Hard |
| School Comedy | Comedy/slice of life | Medium |
| Tavern ERP | ERP/fantasy | Medium |
| Swamp Politics | Worldbuilding/political | Hard |
| Firefighter Tragedy | Drama/tragedy | Hard |
| Ship AI Thriller | Sci-fi/thriller | Hard |
| Bakery Slowburn | Modern romance | Medium |

## Rubric Origins

The scoring dimensions are derived from:
- **[HawThorne V.2](https://github.com/Coneja-Chibi/The-HawThorne-Directives)** — A SillyTavern preset with 21 genre Directors, each defining prose voice, failure modes, and quality checks
- **Real user feedback** — 24 OOC corrections from actual RP sessions
- **Swipe analysis** — 34 rejected/accepted response pairs

## Project Structure

```
harness/           # Python evaluation harness
  config.py        # Model IDs, API settings
  api.py           # OpenRouter client
  runner.py        # Generate + judge pipeline
  aggregate.py     # Leaderboard aggregation
  visualize.py     # Seaborn chart generation
prompts/           # Judge system prompts
  judge_claude.md  # Claude-optimized judge
  judge_gpt.md     # GPT-optimized judge
analysis/          # Rubric and analysis data
scenarios/         # Extracted test scenarios (private, not in HF dataset)
raw/               # Lorebooks and metadata
hf_dataset/        # HuggingFace export scripts and data
results/           # Run results and charts
```

## License

CC BY-NC 4.0 — Free for non-commercial research and community use.
