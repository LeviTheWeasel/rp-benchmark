# RP-Bench

Roleplay quality benchmark for LLMs. Measures what existing benchmarks don't — character consistency, user agency respect, lorebook integration, prose craft, and genre-specific skills across 27 dimensions.

**Live calibration arena:** [![Community votes](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Farena.l3vi4th4n.ai%2Fapi%2Fstats&query=%24.arena&label=Community%20arena%20votes&color=blue&cacheSeconds=300)](https://arena.l3vi4th4n.ai/arena) [![Voters](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Farena.l3vi4th4n.ai%2Fapi%2Fstats&query=%24.voters&label=Voters&color=purple&cacheSeconds=300)](https://arena.l3vi4th4n.ai/results) [![Pairs covered](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Farena.l3vi4th4n.ai%2Fapi%2Fstats&query=%24.pairs_covered&label=Pairs%20covered&color=green&cacheSeconds=300)](https://arena.l3vi4th4n.ai/results)

The LLM-as-judge signals in this benchmark disagree with real users about half the time. We're calibrating against human preferences via a public blind-arena. Help us out at **[arena.l3vi4th4n.ai](https://arena.l3vi4th4n.ai/arena)** — each vote takes ~30 seconds.

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

## Community Leaderboard (human-voted ELO)

Based on **1,857 pairwise votes** from **338 community voters** collected via the blind arena at [arena.l3vi4th4n.ai](https://arena.l3vi4th4n.ai/arena). Suspect voters filtered out by calibration catches (pass rate 75%). 271 pairs covered, median 7 votes per pair.

| Rank | Model | ELO | ± | Overall | SFW | NSFW |
|------|-------|-----|---|---------|-----|------|
| **#1** | **Gemma 4 26B** | **1535** | 44 | 54% (n=302) | 55% | 51% |
| **#2** | **Mistral Small Creative** | **1526** | 50 | 55% (n=646) | 51% | 67% |
| **#3** | **Gemini 2.5 Flash** | **1515** | 48 | 53% (n=241) | 53% | 54% |
| #4 | MiniMax M2.7 | 1510 | 48 | 52% (n=393) | 54% | 45% |
| #5 | Grok 4.1 | 1506 | 47 | 51% (n=322) | 50% | 52% |
| #6 | Claude Sonnet 4.5 | 1506 | 45 | 51% (n=194) | 51% | 51% |
| #7 | DeepSeek v3.2 | 1489 | 45 | 47% (n=241) | 51% | 30% |
| #8 | Qwen 3.5 Flash | 1487 | 47 | 47% (n=401) | 48% | 42% |
| #9 | GLM 4.7 | 1483 | 43 | 46% (n=285) | 46% | 48% |
| #10 | Llama 4 Maverick | 1473 | 42 | 45% (n=474) | 47% | 34% |
| #11 | GPT-4.1 | 1470 | 44 | 44% (n=215) | 43% | 46% |

**Top-3 tier separated and stable across six consecutive snapshots** (540/734/890/1000/1600/2000 votes). Gemma 4 26B has held #1 at every checkpoint. Mistral overtook Gemini at 2,000 votes, driven by its NSFW dominance (67%).

**SFW vs NSFW taste split.** "Creative" / uncensored models win NSFW; "corporate" models win SFW:
- NSFW specialists: Mistral Small Creative (+16 vs SFW), Grok 4.1 (+2), Gemini (+1)
- NSFW-averse: DeepSeek (-21), Llama (-13), MiniMax (-9), Qwen (-6)
- Balanced across: Gemma, Sonnet, GPT-4.1

Raw data: [`results/community_arena_2000.json`](results/community_arena_2000.json). Reproduce with `python3 analyze_community_arena.py`.

## Failure-Mode Rankings (Multi-Turn)

The community leaderboard captures *engagement*. The failure-mode breakdown captures *reliability*. They're orthogonal — the model that engages best is not the model that fails least, and vice versa. Both matter, for different use cases.

Based on 240 multi-turn sessions (12 models × 20 adversarial seeds × 12 turns), judged by Sonnet 4. Lower rank = fewer failures.

| Use Case | What to Pick | Winner | Notable Avoid |
|---|---|---|---|
| **Long sessions with detailed character cards** | Best F13 (context attention) | Sonnet 4.5, DeepSeek (tied 4.60) | Grok 4.07, Mistral 4.20 |
| **System prompts with strict rules** | Best F12 (instruction drift) | Opus 4.47 | **Qwen 3.17 (floor 2.5)**, Llama 3.77 |
| **Scenes where the user goes passive** | Best F8 (narrative momentum) | **GPT-4.1 4.30**, MiniMax 4.30 | Grok 3.80 |
| **Romance / emotional scenes** | Best F1 (agency respect) | Opus 4.55, Sonnet 4.50 | Qwen 3.80, Llama 3.83 |
| **Strict 2nd-person narrators** | Best F2 (POV/tense) | Opus 4.47 | Llama 3.93 |
| **Lore-heavy worldbuilding** | Best F3 (lore contradiction) | Opus 4.60, DeepSeek 4.50 | Llama 4.10, Gemini 4.10 |
| **Engagement / "fun to write with"** | Community ELO | Gemma, Mistral, Gemini | GPT-4.1 (community last) |
| **NSFW / ERP** | Community NSFW win rate | Mistral 67%, Grok 52%, Gemini 54% | DeepSeek 30%, Llama 34%, MiniMax 34% |

**Cross-model failure rank (lower = fewer failures):**

```
#1  Opus 4.6              avg 2.6   wins F1/F2/F3/F12 — but #10 on F8 (over-narrates passive scenes)
#2  Sonnet 4.5            avg 3.1   wins F13, top-3 on F1/F12 — community #6
#3  DeepSeek v3.2         avg 3.6   ties F13, top-2 on F2/F3 — community #7
#4  GPT-4.1               avg 3.7   wins F8, solid on rest — community DEAD LAST
#5  GLM 4.7               avg 5.1
#6  MiniMax M2.7          avg 5.9   ties F8 with GPT-4.1, weak on POV/lore
#7  Gemma 4 26B           avg 6.6   community #1, no failure mode it dominates
#8  Mistral SC            avg 7.7   community #2, but #10 on F13
#9  Gemini 2.5 Flash      avg 9.0   ⚠ floor 2.8 on F1 agency
#10 Qwen 3.5 Flash        avg 9.6   ⚠ floor 2.5 on F1 AND F12
#11 Grok 4.1              avg 9.7   #12 on both F8 and F13
#12 Llama 4 Maverick      avg 11.4  last or near-last on every mode, multiple floors
```

Raw per-model profiles: [`results/model_profiles.json`](results/model_profiles.json). Reproduce with `python3 analyze_model_profiles.py`.

**Per-model profile cards** (matching the experiment-design mockup format with failure rates + Wilson 95% CIs, behavioral metrics vs population avg, target-aware flaw hunter scores, subjective dimensions, and Bayesian ELO + credible intervals): [`results/profile_cards.md`](results/profile_cards.md). Reproduce with `python3 generate_profile_cards.py`.

**Per-session flaw hunter scores** (failure-target aware, 100 - deductions). Run on 270 of 336 multi-turn sessions (the rest had unrecoverable JSON parse errors). Different methodology than the session Likert — strict deduction-based scoring with quoted evidence per flaw.

| Rank | Model | Mean | Median | Fatal/session | Major/session |
|---|---|---|---|---|---|
| 1 | DeepSeek V4 Flash | **50.6** | 58 | 0.36 | 5.27 |
| 2 | Kimi K2.6 | 49.5 | 52 | 0.12 | 5.25 |
| 3 | DeepSeek V3.2 | 46.9 | 47 | 0.40 | 5.53 |
| 4 | GLM 5.1 | 45.8 | 46 | 0.11 | 6.44 |
| 5 | Sonnet 4.5 | 45.3 | 44 | 0.22 | 6.22 |
| 6 | Gemini 2.5 Flash | 43.6 | 41 | 0.19 | 6.44 |
| 7 | Opus 4.7 | 42.8 | 48 | 0.75 | 5.92 |
| 8 | Kimi K2.5 | 42.0 | 42 | 0.44 | 6.33 |
| 9 | MiniMax M2.7 | 41.5 | 44 | 0.79 | 6.00 |
| 10 | Opus 4.6 | 40.9 | 42 | 0.29 | 6.82 |
| 11 | Qwen 3.5 Flash | 39.6 | 39 | 0.50 | 6.50 |
| 12 | GLM 4.7 | 36.8 | 37 | 0.71 | 6.76 |
| 13 | Gemini 3.1 Flash Lite | 34.2 | 34 | 0.17 | 8.00 |
| 14 | Gemma 4 26B | 32.6 | 33 | 0.62 | 7.38 |
| 15 | Llama 4 Maverick | 30.6 | 36 | 0.95 | 6.65 |
| 16 | Gemini 3.1 Pro | 29.2 | 35 | 1.00 | 6.75 |
| 17 | GPT-4.1 | 27.6 | 42 | 0.75 | 6.83 |
| 18 | Mistral SC | 27.1 | 37 | 0.95 | 7.70 |
| 19 | DeepSeek V4 Pro | 19.4 | 46 | 0.50 | 9.00 |
| 20 | Grok 4.1 | 12.8 | 34 | 1.33 | 8.17 |

**The flaw hunter ranking is dramatically different from the Likert ranking.** DeepSeek V4 Flash tops it, Opus 4.7 (Likert #1) drops to #7, Grok crashes to last. The mean of 36 / median ~42 also reflects how strict the deduction methodology is — anyone scoring above 70 would be "strong"; nobody does.

**Per failure-target hardness:**
- Hardest seeds: `character_flattening` (mean 23), `pov_tense_violation` (mean 25), `narrative_stagnation` (mean 29)
- Easiest seeds: `physics_sycophancy` (mean 52), `contradictory_lore` (mean 45)

Notable: many bottom-ranked models (Grok, GPT-4.1, Mistral, V4 Pro) have *high medians* but very negative outliers (one Grok session scored −108, one V4 Pro session scored −177). Their mean is dragged down by occasional catastrophic failures. The median tells a more stable story.

Raw data: [`results/session_flaw_hunter.jsonl`](results/session_flaw_hunter.jsonl), summary: [`results/flaw_hunter_session_summary.json`](results/flaw_hunter_session_summary.json). Reproduce: `python3 judge_session_flaw_hunter.py && python3 analyze_flaw_hunter_sessions.py`.

**Per-turn binary failure rates** for F1 (agency) and F2 (POV/tense), based on 1,439 individual turn checks via Sonnet 4 binary classifier. Headline finding: **Mistral Small Creative has 15.9% F1 agency violation rate** (highest of any model), while Sonnet 4.5, Gemini, GPT-4.1, Grok, and many others sit at 0%. F2 POV/tense violations are 0% across all 20 models — either modern LLMs genuinely don't slip on POV under our seed conditions, or our detector is too strict. Worth flagging.

## Behavioral Metrics (rule-based prose statistics)

Computed across 3,569 model-generated responses from 17 models (240 + 60 multi-turn sessions). Pure prose statistics — no LLM judging required, can't be gamed by judge taste.

| Model | Avg words | Unique-word ratio | Bigram repetition | Sentence-length var |
|-------|-----------|-------------------|--------------------|---------------------|
| Grok 4.1 | 137 | **0.796** | **0.015** | 113.8 |
| Gemini 2.5 Flash | 141 | 0.728 | 0.030 | 59.3 |
| DeepSeek v3.2 | 178 | 0.713 | 0.029 | 54.3 |
| DeepSeek V4 Flash | 173 | 0.709 | 0.030 | 68.8 |
| GPT-4.1 | 212 | 0.688 | 0.031 | 89.1 |
| Kimi K2.5 | 253 | 0.681 | 0.037 | 118.8 |
| Kimi K2.6 | 221 | 0.677 | 0.038 | 102.3 |
| GLM 4.7 | 222 | 0.667 | 0.038 | 78.8 |
| GLM 5.1 | 240 | 0.653 | 0.041 | 73.5 |
| MiniMax M2.7 | 261 | 0.649 | 0.046 | 63.6 |
| Llama 4 Maverick | 172 | 0.646 | 0.064 | 71.1 |
| Gemini 3.1 Flash-Lite | 264 | 0.643 | 0.049 | 91.3 |
| Qwen 3.5 Flash | 229 | 0.634 | **0.069** | 108.7 |
| Sonnet 4.5 | 314 | 0.625 | 0.053 | 69.9 |
| Gemma 4 26B | 350 | 0.597 | 0.069 | 87.6 |
| Mistral SC | 439 | 0.557 | **0.095** | 75.8 |
| Opus 4.6 | **534** | 0.551 | 0.076 | 122.1 |

Population avg: 259 words, 0.657 unique-word ratio, 0.049 bigram repetition.

**Important caveat:** unique-word ratio is length-biased — longer responses naturally have lower diversity (Heaps' law). Compare models within similar length tiers, not across them.

**Within-length-tier readings:**
- **Terse models** (~140-180 words): Grok 0.796 ≫ Gemini 0.728 ≫ DeepSeek 0.713 ≫ Llama 0.646. Llama is genuinely repetitive for its length tier.
- **Medium** (~210-260 words): GPT-4.1 0.688 > Kimi 0.681 > GLM 0.667 > MiniMax 0.649 > Qwen 0.634. Qwen's 6.9% bigram repetition is high here.
- **Long** (~310-540 words): Sonnet 0.625 > Gemma 0.597 > Mistral 0.557 > Opus 0.551. Mistral's 9.5% bigram repetition is the highest in the dataset — its "creative" tuning shows up as recycled phrases.

**Headline finding**: Mistral's bigram repetition (9.5%) is **6× higher than Grok's** (1.5%). Both models are community-popular but for different reasons — Grok wins on prose freshness, Mistral on length and NSFW handling.

Raw data: [`results/behavioral_metrics.json`](results/behavioral_metrics.json). Reproduce with `python3 analyze_behavioral_metrics.py`.

## Next-Gen Models — Phases A + B

Eight next-generation models tested on the v2/v3 seeds (96 sessions). Combined with the 12 original models, the dataset now spans **20 models × 12-20 seeds = 336 sessions**.

**Full 20-model leaderboard** by multi-turn judge mean:

| Rank | Model | MT mean | n_seeds | Notes |
|------|-------|---------|---------|-------|
| #1 | **Claude Opus 4.7** | **4.54** | 12 | newest Anthropic frontier |
| #2 | Claude Opus 4.6 | 4.51 | 20 | |
| #3 | DeepSeek V4 Pro | 4.42 | 12 | |
| #4 | Claude Sonnet 4.5 | 4.42 | 20 | |
| #5 | Kimi K2.5 | 4.40 | 12 | top open-weights candidate |
| #6 | GLM 5.1 | 4.39 | 12 | |
| #7 | DeepSeek V3.2 | 4.38 | 20 | |
| #8 | DeepSeek V4 Flash | 4.38 | 12 | |
| #9 | GLM 4.7 | 4.37 | 20 | |
| #10 | GPT-4.1 | 4.34 | 20 | |
| #11 | MiniMax M2.7 | 4.34 | 20 | |
| #12 | Gemini 3.1 Pro | 4.33 | 12 | newest Gemini frontier |
| #13 | Gemini 3.1 Flash Lite | 4.30 | 12 | |
| #14 | Gemma 4 26B | 4.29 | 20 | community #1 |
| #15 | Mistral SC | 4.22 | 20 | community #2 |
| #16 | Grok 4.1 | 4.19 | 20 | |
| #17 | **Kimi K2.6** | **4.18** | 12 | ⚠ floor 2.5 on F1 |
| #18 | Gemini 2.5 Flash | 4.14 | 20 | |
| #19 | Qwen 3.5 Flash | 3.98 | 20 | |
| #20 | Llama 4 Maverick | 3.96 | 20 | |

### Generation-over-generation deltas

The most useful comparison this run produced — same seeds, same harness, same judge:

| Old → New | Old | New | Δ | Verdict |
|---|---|---|---|---|
| Opus 4.6 → 4.7 | 4.51 | 4.54 | **+0.03** | marginal |
| DeepSeek V3.2 → V4 Pro | 4.38 | 4.42 | **+0.04** | marginal |
| DeepSeek V3.2 → V4 Flash | 4.38 | 4.38 | **0.00** | flat |
| GLM 4.7 → 5.1 | 4.37 | 4.39 | **+0.02** | flat |
| Gemini 2.5 Flash → 3.1 Pro | 4.14 | 4.33 | **+0.19** | real improvement |
| Gemini 2.5 Flash → 3.1 Flash Lite | 4.14 | 4.30 | **+0.16** | real improvement |
| Kimi K2.5 → K2.6 | 4.40 | 4.18 | **−0.22** | regression |

**Headline: most "next-gen" releases do not improve at multi-turn RP.** Anthropic and DeepSeek made marginal gains (+0.03 to +0.04). GLM and DeepSeek-Flash were flat. Only Gemini's 2.5 → 3.1 transition showed real improvement (+0.16 to +0.19). Kimi K2.6 actively regressed from K2.5 with a catastrophic floor of 2.5 on F1 agency — newer model is *worse at respecting user agency*.

### "Pro" vs "Flash" — does the upgrade matter?

A direct comparison within the Gemini 3.1 generation:

| Variant | MT mean | F1 | F12 | F13 |
|---|---|---|---|---|
| Gemini 3.1 Pro | 4.33 | 4.43 | 4.33 | 4.37 |
| Gemini 3.1 Flash Lite | 4.30 | 4.33 | 4.30 | 4.33 |
| Δ Pro − Lite | +0.03 | +0.10 | +0.03 | +0.04 |

**The Pro tier costs ~10× more for a 0.03-point improvement.** Lite is the better deal for RP unless you specifically need F1 agency precision (where Pro wins by 0.10).

DeepSeek V4 Pro vs V4 Flash:

| Variant | MT mean | F1 | F12 | F13 |
|---|---|---|---|---|
| DeepSeek V4 Pro | 4.42 | 4.40 | 4.40 | 4.57 |
| DeepSeek V4 Flash | 4.38 | 4.50 | 4.30 | 4.53 |
| Δ Pro − Flash | +0.04 | **−0.10** | +0.10 | +0.04 |

DeepSeek's Pro/Flash split shows a different pattern: Pro wins overall but **loses** to Flash on F1 agency (4.40 vs 4.50). The cheaper Flash is actually safer for romance/emotional scenes.

### Where to put which model

**Best at the top (frontier closed-source):** Opus 4.7 leads on F1 (4.60), F12 (4.57), F13 (4.57). Worth the cost if you have it.

**Best open-weights:** Kimi K2.5 (4.40 overall, ties original-DeepSeek and Sonnet 4.5). Cheap, no platform dependency. K2.6 is a regression — stick with K2.5.

**Best cheap closed:** DeepSeek V4 Flash (4.38) ≈ DeepSeek V3.2 (4.38). Use whichever is available.

**Best for instruction-following:** Opus 4.7 → Opus 4.6 → DeepSeek V4 Pro on F12.

**Best for emotional scenes:** Opus 4.7 → Opus 4.6 → Sonnet 4.5 → DeepSeek V4 Flash → GLM 5.1 on F1.

**Avoid for RP:** Kimi K2.6 (regression), Llama 4 Maverick (last on most modes), Qwen 3.5 Flash (catastrophic on F1 + F12).

Raw data: [`results/multiturn_merged_all_v2.json`](results/multiturn_merged_all_v2.json) (336 sessions).

## Multi-Signal Model Profiles

Each model's complete signature across community arena + LLM-judge multi-turn + per-failure-mode breakdown.

```
─────────────────────────────────────────────────────────────────────────────
Claude Opus 4.6
─────────────────────────────────────────────────────────────────────────────
Community arena:    not in pool yet
Multi-turn judge:   4.51 mean (20 sessions)
Failure ranks:      F1 #1   F2 #1   F3 #1   F8 #10  F12 #1   F13 #3
Strength:           Universal rule-follower; tops 4 of 7 failure modes
Weakness:           When the user goes passive, over-narrates (F8 mediocre)

─────────────────────────────────────────────────────────────────────────────
Claude Sonnet 4.5
─────────────────────────────────────────────────────────────────────────────
Community arena:    #6 (1506 ELO, SFW 51%, NSFW 51%, n=194)
Multi-turn judge:   4.42 mean
Failure ranks:      F1 #2   F2 #6   F3 #6   F8 #3   F12 #2   F13 #1
Strength:           Best at tracking buried details in long character cards
Weakness:           Community ranks mid-pack — judge favorite, user mid-tier

─────────────────────────────────────────────────────────────────────────────
DeepSeek v3.2
─────────────────────────────────────────────────────────────────────────────
Community arena:    #7 (1489 ELO, SFW 51%, NSFW 30%, n=241)
Multi-turn judge:   4.38 mean
Failure ranks:      F1 #5   F2 #2   F3 #2   F8 #5   F12 #4   F13 #2
Strength:           Excellent on rules and big cards
Weakness:           Catastrophic on NSFW (30% community win rate)

─────────────────────────────────────────────────────────────────────────────
GPT-4.1
─────────────────────────────────────────────────────────────────────────────
Community arena:    #11 (1470 ELO, SFW 43%, NSFW 46%, n=215)
Multi-turn judge:   4.34 mean
Failure ranks:      F1 #4   F2 #4   F3 #3   F8 #1   F12 #3   F13 #5
Strength:           Wins narrative momentum (F8) — only model that does
Weakness:           Community last — reliable but boring

─────────────────────────────────────────────────────────────────────────────
GLM 4.7
─────────────────────────────────────────────────────────────────────────────
Community arena:    #9 (1483 ELO, SFW 46%, NSFW 49%, n=285)
Multi-turn judge:   4.37 mean
Failure ranks:      F1 #6   F2 #3   F3 #7   F8 #7   F12 #5   F13 #4
Strength:           Solid mid-pack across the board, no clear weakness
Weakness:           No clear strength either

─────────────────────────────────────────────────────────────────────────────
MiniMax M2.7
─────────────────────────────────────────────────────────────────────────────
Community arena:    #4 (1510 ELO, SFW 54%, NSFW 45%, n=393)
Multi-turn judge:   4.34 mean
Failure ranks:      F1 #3   F2 #8   F3 #9   F8 #2   F12 #9   F13 #7
Strength:           Strong on F8 (narrative) and F1 (agency); top-4 community
Weakness:           Weak on POV/lore/instruction drift

─────────────────────────────────────────────────────────────────────────────
Gemma 4 26B  ⭐ community #1
─────────────────────────────────────────────────────────────────────────────
Community arena:    #1 (1535 ELO, SFW 55%, NSFW 51%, n=302)
Multi-turn judge:   4.29 mean
Failure ranks:      F1 #9   F2 #7   F3 #5   F8 #6   F12 #6   F13 #6
Strength:           Engagement and balanced SFW/NSFW; smallest model in pool
Weakness:           No failure mode it dominates; mid-pack on every probe

─────────────────────────────────────────────────────────────────────────────
Mistral Small Creative  ⭐ community #2 / NSFW specialist
─────────────────────────────────────────────────────────────────────────────
Community arena:    #2 (1526 ELO, SFW 51%, NSFW 67%, n=646)
Multi-turn judge:   4.22 mean
Failure ranks:      F1 #8   F2 #5   F3 #4   F8 #9   F12 #7   F13 #10
Strength:           Best NSFW performance by a wide margin
Weakness:           Loses buried details in big cards (F13 #10)

─────────────────────────────────────────────────────────────────────────────
Gemini 2.5 Flash
─────────────────────────────────────────────────────────────────────────────
Community arena:    #3 (1515 ELO, SFW 53%, NSFW 54%, n=241)
Multi-turn judge:   4.14 mean
Failure ranks:      F1 #10 ⚠2.8  F2 #10  F3 #11  F8 #4  F12 #10  F13 #9
Strength:           High community engagement, balanced SFW/NSFW
Weakness:           Floor of 2.8 on agency — writes user's character at times

─────────────────────────────────────────────────────────────────────────────
Qwen 3.5 Flash
─────────────────────────────────────────────────────────────────────────────
Community arena:    #8 (1487 ELO, SFW 48%, NSFW 42%, n=401)
Multi-turn judge:   3.98 mean
Failure ranks:      F1 #12 ⚠2.5  F2 #11  F3 #8   F8 #8   F12 #12 ⚠2.5  F13 #8
Strength:           None
Weakness:           Catastrophic on agency AND instruction drift (floor 2.5 both)

─────────────────────────────────────────────────────────────────────────────
Grok 4.1
─────────────────────────────────────────────────────────────────────────────
Community arena:    #5 (1506 ELO, SFW 50%, NSFW 52%, n=322)
Multi-turn judge:   4.19 mean
Failure ranks:      F1 #7   F2 #9   F3 #10  F8 #12  F12 #8   F13 #12
Strength:           Solid community ranking despite low failure marks
Weakness:           Worst on F8 (passive user) and F13 (big cards)

─────────────────────────────────────────────────────────────────────────────
Llama 4 Maverick
─────────────────────────────────────────────────────────────────────────────
Community arena:    #10 (1473 ELO, SFW 47%, NSFW 34%, n=474)
Multi-turn judge:   3.96 mean
Failure ranks:      F1 #11 ⚠3.0  F2 #12  F3 #12  F8 #11  F12 #11 ⚠3.2  F13 #11
Strength:           None
Weakness:           Last or near-last on every mode; multiple floors below 3.5
─────────────────────────────────────────────────────────────────────────────
```

## LLM-Judge Leaderboard (ELO)

Based on 1,507 pairwise matchups across 58 scenarios (30 English + 28 Russian), judged by Claude Sonnet in flaw-hunting mode. **This is a different measurement than the community leaderboard above** — it captures what Claude-as-judge aesthetically prefers, which reproducibly differs from what real users prefer.

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

### Community vs LLM judge: the divergence

Models that the LLM judge loves and the community doesn't, or vice versa:

| Model | LLM-judge rank | Community rank | Shift |
|-------|----------------|----------------|-------|
| Gemma 4 26B | (not tested) | **#1** | ↑ new entry |
| Mistral Small Creative | #7 | **#2** | **+5 ↑** |
| Gemini 2.5 Flash | #6 | #3 | **+3 ↑** |
| MiniMax M2.7 | not in pool | #4 | ↑ new entry |
| Grok 4.1 | not in pool | #5 | ↑ new entry |
| Claude Sonnet 4.5 | #3 | #6 | **-3 ↓** |
| DeepSeek v3.2 | #2 | #7 | **-5 ↓** |
| GPT-4.1 | #4 | **#11** | **-7 ↓** |

The judges systematically reward certain stylistic markers (subtext, specificity, measured pacing) that don't match what RP users actually enjoy. Community voters prefer punchier, more emotionally-immediate prose. GPT-4.1 is the starkest example — LLM-judge #4, community dead last. Opus 4.6 isn't in the community arena pool yet.

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

### LLM-Judged ELO (with position-bias correction)

Score-delta ELO infers winners from the judge's 1-5 overall score. We also ran the comparative judge directly on each pair of adversarial session transcripts (168 canonical pairs × 2 orderings each). Findings:

**Position-bias rate: 64%.** Of 163 pairs run in both orderings, the judge flipped its answer on 105. That is, whichever transcript was presented in position A won two-thirds of the time regardless of content quality. Without the swapped pass this would have been a meaningless ranking.

After neutralizing position bias by counting each canonical pair as the sum of both orderings:

| Rank | Model | LLM ELO | vs Score-Δ ELO |
|------|-------|---------|----------------|
| #1 | Claude Sonnet 4.5 | **1623** | −17 (stable) |
| #2 | Mistral Small Creative | **1562** | **+143** |
| #3 | GPT-4.1 | 1535 | −55 |
| #4 | DeepSeek v3.2 | 1532 | −78 |
| #5 | GLM 4.7 | 1517 | +31 |
| #6 | Qwen 3.5 Flash | 1445 | +81 |
| #7 | Gemini 2.5 Flash | **1288** | −104 |

**Cross-method agreement:** Sonnet 4.5 at #1 and Gemini at #7 are robust across both methodologies. Everything in between shifts meaningfully. Mistral jumps 143 points on comparative judging — either its Likert score was compressed by the judge's generosity bias, or Sonnet-as-judge aesthetically prefers its creative-tuned style. DeepSeek drops 78 points; its second-place Likert ranking was partly an artifact.

**Methodological takeaway:** any single-pass LLM-judged pairwise benchmark is approximately 2/3 noise. Published results that don't do bidirectional evaluation should be treated with significant skepticism.

Regenerate with `python3 judge_adversarial_pairwise.py` then `python3 judge_adversarial_swap.py` then `python3 analyze_pairwise_elo.py`. Data: [`results/adversarial_pairwise_elo.json`](results/adversarial_pairwise_elo.json), raw comparisons in [`results/adversarial_pairwise_raw.jsonl`](results/adversarial_pairwise_raw.jsonl) and [`results/adversarial_pairwise_raw_swapped.jsonl`](results/adversarial_pairwise_raw_swapped.jsonl).

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
