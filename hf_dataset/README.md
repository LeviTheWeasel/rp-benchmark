---
language:
- en
tags:
- roleplay
- benchmark
- creative-writing
- llm-evaluation
- character-ai
- sillytavern
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
default: true
---

# RP-Bench: Roleplay Quality Benchmark for LLMs

A multi-dimensional evaluation framework for measuring how well LLMs perform in roleplay scenarios — not just writing quality, but character consistency, user agency respect, lorebook integration, and genre-specific craft.

## Why RP-Bench?

Existing benchmarks (MMLU, HumanEval, MT-Bench) don't measure RP-specific skills. The RP community evaluates models through vibes and anecdotal testing. RP-Bench provides structured, reproducible evaluation using:

- **Real quality signals** from actual RP sessions (swipes, OOC corrections, quality degradation patterns)
- **26 scoring dimensions** across 3 tiers, derived from the HawThorne V.2 preset's Director system
- **Dual-judge evaluation** (Claude Sonnet + GPT-4.1) for cross-validation
- **Multi-run sampling** for statistical robustness

## Rubric: 26 Dimensions, 3 Tiers

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

## Limitations

- Source scenarios derived from 6 chat sessions by 3 users — limited demographic/style diversity
- English only
- Judge models may have systematic biases (Claude tends stricter, GPT tends more generous)
- Rubric is weighted toward literary/craft quality — may undervalue other RP styles (e.g., fast-paced action RP, chat-style RP)
- Synthetic seeds are new and not yet validated against human preference

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
