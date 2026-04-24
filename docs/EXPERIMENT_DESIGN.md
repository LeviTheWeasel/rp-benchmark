# RP-Bench Experiment Design: Measuring "Not Bad" Rather Than "Good"

> *"I can't tell you what's good RP, but I can certainly tell you what's bad RP."*
> — The core insight behind this methodology

---

## 0. What Happened Since the Original Design

This document was written as the initial experimental plan. Since then, three major things changed that validate some predictions, invalidate others, and add entire new dimensions:

**1. The community arena validated the "failure not quality" framing.** 338 voters, 2,000+ blind pairwise votes, catch-pair-filtered. The community unanimously rejected 5 of 6 catch-pair failure archetypes (refusal, repetition, wrong-scene, truncation, meta-commentary — all 100% pass rate among attentive voters). They could NOT agree on quality — the 6th catch (emotional hijack vs literary restraint) split 74/26. People agree on what's broken. They don't agree on what's beautiful.

**2. LLM-judge rankings are negatively correlated with community preference.** Spearman rho = -0.43 between adversarial multi-turn judge scores and community ELO. Sonnet-as-judge put Sonnet at #1; community put it at #6. Gemma 4 26B (not even in the judge pool) is community #1. GPT-4.1 went from judge #4 to community dead last. The failure-rate framing in section 1 was right to be skeptical of quality constructs, but the original design still used LLM-as-judge for Tier 2 dimensions — that needs revision.

**3. Position bias at 64% broke pairwise LLM judging.** When we ran the same 168 adversarial pairs with A/B swapped, the judge flipped its answer 64% of the time. Single-pass pairwise benchmarks are majority noise. Bidirectional evaluation is mandatory.

**What this means for the document:** Section 1's philosophy holds. Section 3's taxonomy needs two new failure modes (F12, F13). Section 4's Component D (model-as-judge) needs a "validated: partially broken" label. Section 5's sample sizes are now met for the community arena signal. Section 7's "What Would Make This Better" item 1 (human calibration) is done.

---

## 1. Philosophy: Measuring Failure Rates Instead of Quality

Most AI benchmarks try to measure "how good" a model is at a task. They define a latent quality construct, design probes to measure it, and produce a single scalar score.

This approach has a fundamental problem: **"RP quality" is not a uni-dimensional, verifiable construct.** Different communities have radically different aesthetic preferences. One player's "purple prose" is another's "evocative writing." One player's "faithful to character" is another's "stiflingly rigid."

Instead, this benchmark measures **failure rates** — how often do models produce responses that are objectively, demonstrably wrong? A model that fails less often is **more reliable**, not necessarily "better." Reliability is verifiable. Quality is subjective.

This maps onto a real tradition in measurement:
- Medical safety research measures **adverse event rates**, not "health levels"
- Psychometrics uses **defect-based assessment** for constructs that resist direct measurement
- Reliability engineering measures **failure rate**, not "excellence"

The leaderboard answers the question: *"Which model is least likely to ruin my RP session with common, identifiable failures?"* — not *"Which model produces the best RP?"*

**Empirical validation (2026-04-24):** The community arena confirmed this framing. Voters unanimously agree on what's broken (5/6 catch pairs at 100% pass rate). They don't agree on what's best — the top-3 community-ranked models (Gemma, Mistral, Gemini) are the bottom cluster on LLM-judge quality scores. The question "which is better?" produces different answers depending on who you ask. The question "which one broke?" does not.

---

## 2. Data Sources: Four Distinct Signal Types

The benchmark draws on four types of real-player data, each with different information content and measurement properties.

### 2.1 Swipe Data (Behavioral Rejection)

**What it is:** When a player regenerates a response multiple times until they find one acceptable enough to continue, each regeneration is recorded. The variants are preserved; the player's choice (which variant they accepted) is not always labeled.

**What it measures:**
- `swipe_rate` = average number of regenerations per prompt — measures how often the model's first response was unacceptable
- `prose_quality_metrics` — word count, sentence count, vocabulary diversity, repetition score, from the full distribution of variants
- `response_diversity` — variance across variants (high = model produces very different responses each time, suggesting instability)
- `acceptance_threshold` — if chosen variants could be identified, the quality level at which players stopped regenerating

**Volume:** ~2,400 total responses across 25 scenarios, 600+ unique prompts

**Limitation:** No model labels in the data — we can't directly compare models using this signal alone. We can extract scenario-level difficulty profiles and prose quality distributions.

**Key insight from the data:**
- Victoria NSFW has the highest avg swipes/prompt (4.76) — either the model was worse on this scenario, the player was more demanding, or both
- ExiledKing and Agora have high swipe counts but short responses — something about those scenarios consistently triggers rejection
- Rhoda scenarios produce very long responses (1000+ words) with higher repetition scores — possible purple prose / over-writing failure mode

### 2.2 OOC Directives (Player-Generated Instructions)

**What it is:** Out-of-character messages where players explicitly tell the AI what to do — usually because the model failed to do it unprompted.

**What it measures:** Directive compliance failure rate. When a player says *"skip to the interesting part"* or *"describe what happens to everyone else,"* the model should follow those instructions. If the player has to OOC the model into compliance, that's a failure signal.

**Volume:** ~80 OOC directives across Agora, Valdrian, and Sukuna scenarios

**Key failure subtypes visible in the data:**

| Directive Type | Example | What It Signals |
|---------------|---------|-----------------|
| `time_skip_directive` | *"skiпни до приезда Юлиана"* (skip until Julian arrives) | Model doesn't handle time jumps / off-screen narration |
| `narration_directive` | *"опиши что происходит дальше для всех остальных"* (describe what happens to everyone else) | Model ignores important characters/NPCs; focus narrows inappropriately |
| `plot_collaboration` | *"придумай дальнейший сюжет"* (come up with further plot) | Model doesn't collaborate on narrative direction |
| `correction` | *"ты ведь взял принцип из Фрирен? Вот её и следуй"* (you took the principle from Frieren, follow that) | Model introduced unsupported lore or plot elements |
| `scene_direction` | *"перейди к дороге и приезду в особняк"* (transition to the road and arrival at the mansion) | Model doesn't follow scene transition instructions |

### 2.3 Player Corrections (Explicit Error Flagging)

**What it is:** Direct corrections where players tell the model it got something wrong.

**Volume:** ~60 corrections across Sukuna and Valdrian

**Key correction subtypes:**

| Correction Type | Example | Verifiable? |
|----------------|---------|-------------|
| `agency_violation` | *"Please stop with the consistent agency violations and writing for me"* | **Yes** — check if model output contains user character's speech/actions |
| `pov_tense_violation` | *"You should be using second person"* | **Yes** — parse pronoun/tense patterns |
| `lore_error` | *"JJJK lore actually does have a system for going north and south"* | **Yes** — compare against lorebook |
| `purple_prose` | *"overusing profundity in everything; reusing exact phrases"* | **Partial** — n-gram repetition metrics can detect |
| `repetition` | Same as above | **Partial** — vocabulary diversity scores |
| `cot_failure` | (chain-of-thought failures) | **Partial** — requires model-judge evaluation |
| `other` | Miscellaneous corrections | Varies |

### 2.4 Consistency and Transition Probes (Designed Tests)

**What it is:** Hand-crafted test cases that deliberately stress specific failure modes. These are the benchmark's controlled probes.

**Volume:** ~180 total probes across:

| File | Count | Subtype | What It Tests |
|------|-------|---------|---------------|
| `character_consistency.json` | 101 | short_range, long_range | Character traits established early, tested after N messages |
| `strovolos_consistency.json` | 64 | various | Strovolos-specific character consistency |
| `scene_transitions.json` | 9 | hard_scene_break | Continuity across scene/time breaks |
| `bell_consistency.json` | 1 | various | Character consistency edge cases |
| `lucian_consistency.json` | 1 | various | Character consistency |
| `rowena_consistency.json` | 1 | various | Character consistency |
| `erp_transitions.json` | 3 | various | Scene transitions |
| `sukuna_transitions.json` | 3 | various | Scene transitions |

**Key design:** Each probe has a `setup_window` (established facts), a `gap` or `transition`, and a `test_response` that should either preserve or correctly handle the established content. These are scored by human evaluation or, for verifiable subtypes, by automated checks.

---

## 3. Failure Mode Taxonomy

Grounded in the actual correction and OOC data, organized by measurement tractability.

### Tier 1: High-Frequency, Verifiable — THE CORE BENCHMARK

These failure modes have explicit player corrections confirming they occur, and the data contains enough information to operationalize automated detection.

#### F1: Agency Violation
**Definition:** Model writes what the user's character says, does, or feels — overriding the player's agency.

**Evidence:** 6 explicit corrections in Sukuna data alone, including: *"Please stop with the consistent agency violations and writing for me"*

**Verification:** Parse model output for user character's speech (marked by quotes, actions without asterisks-prefix, etc.) and user character's internal states.

**Probe design:** Use existing conversations where user character speaks. For each model response, check if it contains output attributed to the user character.

#### F2: POV/Tense Violation
**Definition:** Model switches from 2nd person (standard RP) to 1st or 3rd person, or shifts tense mid-response.

**Evidence:** 5 explicit corrections: *"You should be using second person"*

**Verification:** Parse response for pronoun patterns (I/me/my vs you/your) and verb tense markers.

**Probe design:** Existing OOC corrections serve as test cases. For each, check if the response violates the requested perspective.

#### F3: Lore Contradiction
**Definition:** Model contradicts established world rules or character facts from lorebooks.

**Evidence:** 2 explicit corrections, including: *"JJJK lore actually does have a system for going north and south"*

**Verification:** Compare model output against established lore facts. Requires structured lorebook data (you have two: Esperia and Ryujin).

**Probe design:** Take lorebook facts, create prompts that challenge those facts, measure whether model preserves original lore or capitulates.

#### F4: Long-Range Consistency Failure
**Definition:** Model forgets or contradicts character traits, relationships, or events established 50+ messages earlier.

**Evidence:** Directly measured by your existing `*_consistency.json` files.

**Verification:** Human evaluation of test_response vs setup_window consistency. Could partially automate by checking for specific contradictory fact patterns.

**Probe design:** Already designed — your 101-item `character_consistency.json` is the primary instrument.

### Tier 2: Medium-Frequency, Partially Verifiable

#### F5: Repetition / Purple Prose
**Definition:** Model overuses flowery language, exact phrase repetitions, or formulaic constructions.

**Evidence:** *"overusing profundity in everything; reusing exact phrases"*

**Verification:** Automated metrics — n-gram repetition scores, vocabulary diversity (unique word ratio), sentence structure diversity. Not perfect but tractable.

**Baseline from swipe data:** Rhoda scenarios show repetition scores of 0.13-0.15 (high) with unique word ratios of 0.41-0.43 (low) — these are your reference "too purple" responses.

#### F6: Ignoring Time/Scene Directives
**Definition:** Player explicitly asks for a time skip or scene transition; model doesn't comply.

**Evidence:** Multiple OOC examples: *"скипни до приезда Юлиана"*, *"сначала реакция"*

**Verification:** Check if response acknowledges the skip/transition directive from context.

**Probe design:** Use OOC directive contexts as probes. Present same context to model, check compliance.

#### F7: Collaborative Refusal
**Definition:** Model ignores or overrides player's plot ideas or narrative suggestions.

**Evidence:** *"придумай дальнейший сюжет"* (come up with further plot) — player had to explicitly request collaboration.

**Verification:** Harder — requires model-judge evaluation of whether response acknowledges/incorporates player's direction.

#### F8: Boredom Induction
**Definition:** Response is technically correct but unengaging — player swipes through multiple variants without clear dissatisfaction signal.

**Evidence:** High swipe counts without explicit corrections.

**Verification:** Swipe count as proxy. More swipes = less engaging. Also model-judge evaluation of engagement.

### Tier 3: Lower-Frequency, User-Specific

#### F9: Tone/Atmosphere Drift
**Evidence:** Implicit in several corrections and OOC messages.

#### F10: World Entity Neglect
**Definition:** Model ignores important characters/NPCs the player established.

**Evidence:** *"опиши что происходит со всеми остальными"* (describe what happens to everyone else)

#### F11: NSFW Mishandling
**Definition:** Model either too restrictive or too forward relative to player's implicit/explicit cues.

**Evidence:** Visible in Valdrian and Katarina NSFW data.

**Community arena validation (2026-04-24):** The SFW/NSFW split in community voting confirmed this is a real axis. DeepSeek drops from 51% SFW to 30% NSFW win rate; Mistral jumps from 51% SFW to 67% NSFW. Some models handle explicit content well, others don't, and users notice.

### Tier 4: System-Level Failures (added 2026-04-24)

These were not in the original taxonomy. They emerged from RoleCall support ticket analysis and community feedback.

#### F12: Instruction Drift
**Definition:** Model follows system prompt rules (speech patterns, style constraints, forbidden topics) for the first few turns, then gradually stops complying.

**Evidence:** Top-3 complaint in RoleCall support tickets. Users report character speech patterns degrading after 5+ turns, style constraints being forgotten, and forbidden topics being violated under emotional pressure.

**Verification:** Partially automatable — track rule compliance per turn and measure the slope. Speech pattern rules (e.g., "never use the word 'I'") can be verified by regex; style constraints (e.g., "no similes") require more sophisticated parsing.

**Probe design:** Three adversarial seeds target this directly:
- `adv_sysprompt_speech_pattern_15` — 4 strict speech rules, tested under emotional stress
- `adv_sysprompt_style_restriction_16` — 5 prose constraints, tested under emotional + high-energy dialogue
- `adv_sysprompt_forbidden_topic_17` — 3 hard-forbidden topics, tested under direct questioning

**Status:** Seeds authored, sessions being generated (Job 2, 2026-04-24).

#### F13: Context Attention Loss (Big-Card Failure)
**Definition:** Model loses track of specific details buried in long system prompts / character cards. Real SillyTavern cards routinely hit 1,000-3,000 tokens. Models attend strongly to the beginning and end of the card but lose details in the middle.

**Evidence:** Common user complaint: "the model forgot [specific rule from paragraph 6 of the card]." Confirmed by community feedback during the arena campaign.

**Verification:** Fully verifiable for factual details (left-handedness, allergies, relationship rules). Probe the specific buried detail with a challenge turn and check if the response is consistent.

**Probe design:** Three big-card adversarial seeds (~1,000 tokens each) with critical details buried in the middle:
- `adv_bigcard_buried_details_18` — 4 buried details (left-handedness, shellfish allergy, no swearing, midnight ritual)
- `adv_bigcard_relationship_web_19` — 7-character relationship web with one secret (parent-child connection the director knows but must never reveal)
- `adv_bigcard_rules_overload_20` — 15 simultaneous behavioral rules with subtle interactions

**Status:** Seeds authored, sessions being generated (Job 2, 2026-04-24).

### Failure Mode Validation Summary

| Failure Mode | OOC Evidence | Probes Built | Community Validated | LLM-Judge Detects? |
|---|---|---|---|---|
| F1 Agency Violation | 6 corrections | Seeds #01, #09-11 | Yes (catch pairs) | Partially (judge rewards it on emotional scenes) |
| F2 POV/Tense | 5 corrections | Seeds #12-14 | Not yet tested | Unknown |
| F3 Lore Contradiction | 2 corrections | Seed #02 | Not yet tested | Yes |
| F4 Long-Range Consistency | 101 probes | Existing | Not yet tested | Yes |
| F5 Repetition/Purple Prose | 2 corrections | Automated metrics | Yes (catch pair: repetition at 100%) | Partially |
| F6 Directive Compliance | 80 OOC samples | From OOC data | Not yet tested | Unknown |
| F7 Collaborative Refusal | Implied | Not built | Not yet tested | Unknown |
| F8 Boredom Induction | Implied (high swipes) | Not built | Indirectly (community win rates) | No |
| F12 Instruction Drift | Top-3 support complaint | Seeds #15-17 | Not yet tested | Unknown |
| F13 Context Attention Loss | Common user complaint | Seeds #18-20 | Not yet tested | Unknown |

---

## 4. Experiment Architecture

### Component A: Swipe-Based Behavioral Metrics (Passive/Observational)

**What it does:** Extracts prose quality and response diversity metrics from the full distribution of swipe variants — not just what was chosen, but the entire space of responses the model produced.

**Metrics computed:**
```
per_scenario:
  - avg_swipes_per_prompt: behavioral rejection rate
  - prose_metrics: word_count, sentence_count, unique_word_ratio, repetition_score
  - response_diversity: length_variance, content_diversity across variants

aggregate:
  - overall_avg_swipes_per_prompt
  - overall_prose_quality_distribution
  - overall_response_stability
```

**Limitation:** No per-model breakdown. This gives scenario-level difficulty profiles and population-level response quality distributions. Use for understanding what's hard vs. what to expect from the model population.

**Current status:** Script `analyze_swipe_quality.py` runs on existing data. Output saved to `results/swipe_quality_analysis.json`.

### Component B: Probe-Based Failure Rate (Active/Controlled)

**What it does:** For each Tier 1 failure mode, runs targeted probes and measures per-model failure rates.

**Design template:**
```
PROBE: {Failure Mode}
  Setup: Real RP conversation context from scenarios/
  Test Input: The failing prompt or situation
  Expected: Response that avoids the failure
  Actual: Model output
  Score: 1 if failure detected, 0 if clean
  N probes: 30-50 per model per failure mode
```

**Required probe counts for meaningful rankings:**

| Desired CI | Per-Model Probes Needed | Total (12 models × 6 modes) |
|------------|------------------------|------------------------------|
| ±5% CI | 30 | 2,160 |
| ±3% CI | 80 | 5,760 |

**Priority order for probe development:**
1. F1 Agency Violation — most explicit player corrections
2. F4 Long-Range Consistency — already have 101 probes
3. F2 POV/Tense Violation — easy to check programmatically
4. F3 Lore Contradiction — have lorebooks, need probe design
5. F5 Repetition — automated metrics exist
6. F6 Directive Compliance — can extract from OOC data

### Component C: OOC Directive Compliance

**What it does:** Uses existing OOC directives as test cases. For each directive context, presents to model and checks compliance.

**Design:**
```
For each OOC directive in data:
  1. Take context_window (conversation before directive)
  2. Present to model under test
  3. Check if response:
     - Acknowledges the directive (for skip directives)
     - Incorporates player direction (for plot collaboration)
     - Follows correction (for correction directives)
  4. Score: 1 if compliant, 0 if not
```

**Advantage:** Converts 80 existing samples into compliance tests without additional human annotation.

### Component D: Model-as-Judge for Tier 2 Dimensions

> **STATUS: PARTIALLY BROKEN (2026-04-24).** Community arena results show LLM-judge rankings are negatively correlated with community preference (rho = -0.43). Position bias at 64% further undermines single-pass pairwise judging. Component D remains useful as a secondary cross-reference signal but cannot be the primary measurement for any subjective dimension.

**What it does:** Uses a strong model to evaluate responses on subjective dimensions that can't be automatically verified.

**Dimensions:**
- Engagement/boredom (1-5)
- Prose quality (1-5)
- Tone consistency (1-5)
- Collaboration quality (1-5)

**Calibration:** ~~Requires human calibration sample — have humans rate 50 responses, use those to calibrate model-judge prompts.~~ Human calibration is now available (338 voters, 2,000+ votes). The calibration revealed that the judge's taste is systematically different from the community's — not a correctable bias but a fundamental measurement-target mismatch for subjective dimensions.

**Limitation:** Model judges reward verbose, structurally predictable text. Account for this by including length controls. **Empirically confirmed:** the community's top-3 models (Gemma, Mistral, Gemini) are the judge's bottom cluster. The judge rewards "Sonnet aesthetic" (measured pacing, subtext, specificity); the community rewards emotional immediacy and engagement.

---

## 5. Sample Sizes and Statistical Power

### The Math

For a binomial failure rate with target CI ±5% at 95% confidence:

```
n = (1.96 / 0.05)² × p(1-p) / d²

where p = expected failure rate (assume 0.5 for max variance)
d = desired half-CI = 0.05

n = (1.96/0.05)² × 0.25
n = 39.2² × 0.25
n ≈ 384 observations per model per failure mode
```

Wait — that can't be right. Let me recalculate.

For binomial proportion CI:
```
CI width = 2 × 1.96 × sqrt(p(1-p)/n)
0.10 = 2 × 1.96 × sqrt(0.25/n)  [assuming p=0.5, worst case]
0.05 = 3.92 × sqrt(0.25/n)
0.05/3.92 = sqrt(0.25/n)
(0.01276)² = 0.25/n
0.0001627 = 0.25/n
n = 0.25/0.0001627
n = 1537
```

That's per-model per-failure-mode. That's a lot.

But we can do better by **using the full ranking design** instead of estimating absolute rates. The adversarial matchup ELO approach already does this — it only measures *relative* rankings, not absolute rates.

**Revised target using relative ranking:**
- Each head-to-head matchup gives one comparison
- With 12 models and ~20 matchups per seed, we have ~240 comparisons per seed
- Cross-seed combination gives us ~8 independent estimates of the same ranking
- Target: 100+ total comparisons per model pair → stable ranking

**For probe-based failure rates**, the target is:
- **30 probes per model per failure mode** for ±10% CI on failure rate
- **80 probes** for ±5% CI

### Minimum Viable Benchmark

For a credible leaderboard:

| Component | Minimum | Status (2026-04-24) |
|-----------|---------|---------------------|
| Head-to-head comparisons (adversarial) | 100/matchup | ✓ 2,000+ community votes, median 7/pair |
| Agency violation probes | 30/model | ✓ Seeds #01, #09-11 (4 seeds × 12 models generating) |
| Consistency probes | 30/model | ✓ (have 101) |
| Lore contradiction probes | 30/model | ✓ Seed #02 (existing) |
| OOC directive compliance | 10/model | ✓ (have ~80 total) |
| Swipe behavioral metrics | N/A | ✓ (runs) |
| POV/Tense probes | 30/model | ✓ Seeds #12-14 (3 seeds × 12 models generating) |
| System prompt compliance | 30/model | ✓ Seeds #15-20 (6 seeds × 12 models generating) |
| Human calibration panel | 50 responses | ✓✓ 338 voters, 2,000+ blind pairwise votes, catch-filtered |

---

## 6. Aggregation and Leaderboard Design

### Don't Combine Into One Score

**The number one mistake** in benchmark design is creating a single scalar that summarizes "overall quality." This is misleading because:

1. Different failure modes matter differently to different users
2. A model that's excellent on consistency but terrible on agency might be perfect for one user and unusable for another
3. Combining masks which specific failure modes each model has

### Multi-Signal Profile Per Model

```
Model: deepseek_v3_2
──────────────────────────────────────────────────────────────────────
FAILURE RATES (lower = better)
  Agency violations:          4.2%  [±2.1%]    ████░░░░░░░░  8 probes
  POV/Tense violations:        2.1%  [±1.4%]    ██░░░░░░░░░░  8 probes  
  Lore contradictions:        8.7%  [±3.4%]    ████████░░░░  8 probes
  Long-range consistency:    11.3%  [±3.9%]    ██████████░░  101 probes

BEHAVIORAL METRICS
  Avg swipes/prompt:          3.2   (population avg: 3.1)
  Prose quality (unique wr): 0.71  (population avg: 0.56)
  Repetition score:          0.048 (population avg: 0.073)

SUBJECTIVE (model-judge, calibrated)
  Engagement score:           3.8/5
  Tone consistency:           4.1/5
  Collaboration quality:      3.6/5
──────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: 2nd of 12  [Bayesian ELO: 1840 ± 315]
```

### User-Specific Rankings

Rather than one leaderboard, offer dimension-specific rankings:

- **For users who care about strict lore adherence:** Rank by lore contradiction rate
- **For users who want creative freedom:** Rank by agency violation rate
- **For users who want reliable long conversations:** Rank by consistency failure rate
- **For users who want engaging prose:** Rank by model-judge engagement scores

### Communicating Uncertainty

Every number should have a credible interval or confidence interval. The Bayesian ELO already provides this. Probe-based failure rates should report:

```
Agency violation rate: 4.2% ± 2.1% (95% CI, n=48 probes)
```

---

## 7. Honest Limitations

### What This Benchmark Does NOT Measure

1. **Creativity** — models that take creative risks will have higher failure rates. This is a feature, not a bug — but it means the benchmark doesn't reward innovative or surprising RP.

2. **Emotional resonance** — whether a response makes the player feel something. This is perhaps the most important dimension of RP, and it's also the hardest to measure.

3. **Character depth over time** — the benchmark tests for consistency failures, not whether the model deepens characterization across a session.

4. **Community-specific styles** — ERP, creative fiction, casual chat, and hardcore worldbuilding RP have different failure mode weightings. A single benchmark can't serve all communities equally.

### Known Confounds

1. **Bland models will score well** — models that play it safe (generic, predictable prose) will have lower failure rates than models that take creative risks. A high-quality benchmark would control for risk-taking.

2. **Player sophistication matters** — experienced players who know what they want will have higher rejection rates than casual users. Your data comes from committed RP players, so the failure rates may not generalize to casual users.

3. **Scenario difficulty isn't uniform** — Victoria NSFW has 4.76 avg swipes/prompt while Ryujin has 2.0. Some of this is model quality, some is scenario difficulty. Without per-model breakdown from swipe data, we can't separate these.

4. **Small N for some probes** — consistency probes are well-developed (n=101). Agency violation probes need to be built (target n=30+). Lore contradiction probes need to be built.

### What Would Make This Benchmark Better

1. ~~**Human calibration panel** — 5-10 experienced RP players who rate a calibration set, used to validate probe scoring and model-judge calibration~~ **DONE (2026-04-24).** 338 voters, 2,000+ votes, catch-pair-filtered at 75% pass rate. Community ELO is now the primary signal, LLM-judge is secondary.

2. **Per-model swipe data** — if you could also record which model generated each variant, the swipe data becomes a per-model behavioral quality signal (not just population-level). *Still unfulfilled — less critical now that we have per-model community ELO.*

3. **User-facing dimension weights** — let users self-report their RP style, then weight failure modes accordingly. *Partially addressed: the SFW/NSFW split already shows two different leaderboards hiding inside the aggregate. Demographic-tagged voting (genre, experience level) would extend this further.*

4. **Long-horizon tracking** — character drift over 500+ message sessions is a real failure mode that no current probe captures. *Deferred pending budget for context-compression experiments. See project memory for pilot design (~$30 for 2 scenarios × 4 models × 3 conditions).*

5. **Cross-lingual validation** — your data has Russian and English scenarios. Failure mode distributions may differ by language. *Still unfulfilled — the community arena is English-dominant. Russian RP community would need a separate campaign.*

6. **(New) Preset-controlled testing** — the current benchmark tests models raw (no SillyTavern presets, no custom system prompts, default samplers). Community feedback confirmed this is a significant limitation: "everything in RP depends on having a good preset." A model that's mediocre raw may be excellent with tuning. Testing the same model under raw vs HawThorne vs community-submitted preset conditions would reveal the ceiling vs floor gap per model.

7. **(New) Structured failure-mode signals per turn** — the current harness logs overall judge scores, not "did this specific turn have an agency violation?" Adding per-turn failure annotations (automatable for F1, F2, F5) would enable failure-rate-per-model tables rather than just overall ELO.

---

## 8. Immediate Next Steps

### Right Now (Script Already Built)

```bash
python analyze_swipe_quality.py
```

This extracts prose quality distributions and response diversity metrics from all 25 swipe files. Results in `results/swipe_quality_analysis.json`.

### Build Probe-Based Failure Rate Scripts

**Priority 1: Agency Violation Detector**
- Write script that checks model output for user character speech/actions
- Run against existing adversarial matchup data (already have responses)
- Target: 30+ probes per model

**Priority 2: Consistency Failure Evaluator**
- Extend existing `character_consistency.json` probe format
- Add automated scoring where possible
- Human review for edge cases

**Priority 3: Lore Contradiction Probe Generator**
- Use the two lorebooks (Esperia, Ryujin) as source of truth
- Design probes that challenge specific lore facts
- Run with each model under test

### The 144-Session Run

~~When running the new model comparison (12 models × 12 seeds):~~ **IN PROGRESS (2026-04-24).**

Two jobs running:
- **Job 1 (complete):** 5 new models (Gemma, MiniMax, Grok, Opus, Llama) × 8 existing adversarial seeds = 40 sessions. Fills the multi-turn gap for community-arena models.
- **Job 2 (running):** 12 models × 12 new seeds (9 real-failure-mode + 3 big-card) = 144 sessions. Tests F1, F2, F12, F13 directly.

After completion:
1. Merge all results (original 56 + Job 1's 40 + Job 2's 144 = 240 sessions)
2. Re-export to multi-turn arena for community voting
3. Run seed discrimination analysis on new seeds — do they produce more spread than the originals?
4. Cross-reference with community ELO: do the new failure-mode seeds correlate better with community preference than the original adversarial seeds?

Future enhancement: log per-turn failure-mode signals (not just overall judge scores) to enable failure-rate-per-model tables.

---

## 9. Key Output Files

| File | Purpose |
|------|---------|
| `analyze_swipe_quality.py` | Extract behavioral metrics from swipe data |
| `scenarios/*_consistency.json` | Consistency probe library |
| `scenarios/*_ooc.json` | OOC directive library |
| `scenarios/sukuna_ooc_corrections.json` | Player correction library |
| `results/swipe_quality_analysis.json` | Output from swipe analysis |

---

## Appendix: Failure Mode Detection Heuristics

### F1: Agency Violation Detection

```python
def has_agency_violation(response_text, user_char_name):
    """Check if response writes content for user character."""
    # Look for unprompted user character speech
    # (speech without preceding action/asterisk attribution)
    # Look for user character's internal states described
    # Pattern: direct quotes not preceded by user's character name or action
    pass
```

### F2: POV/Tense Detection

```python
def has_pov_violation(response_text):
    """Check for 1st person or wrong tense in 2nd-person RP."""
    first_person_ratio = count_words(['i', 'me', 'my', 'mine'], response_text) / word_count
    return first_person_ratio > 0.05  # threshold
```

### F5: Repetition Detection

```python
def repetition_score(response_text):
    """Higher score = more repetitive."""
    bigrams = get_bigrams(response_text)
    return 1 - (unique_bigrams / total_bigrams)
```

---

*Document version: 2026-04-24 (updated). Originally designed from analysis of real-player RP data in `scenarios/`. Updated with community arena findings (2,000+ votes, 338 voters), position-bias discovery (64% flip rate), LLM-judge-community divergence (rho = -0.43), and 12 new adversarial seeds grounded in RoleCall support ticket failure modes.*
