# What I Learned Trying to Benchmark Roleplay Models

**Category:** Research / Methodology
**Date:** 2026-04-16
**Reading time:** ~14 min

---

Every roleplay benchmark is either vibes ("I tried it and it felt good") or tests generic writing quality that has nothing to do with what actually breaks in a real session. I spent two weeks building one that tries to do better. Most of what I learned was about how badly LLM-as-judge benchmarks fail when you take them seriously.

This is the story of that project — what I built, how each layer broke, and what the community arena eventually revealed that the automated judge pipeline couldn't see.

## The obvious idea: LLM-as-judge with a fancy rubric

The first version was ambitious. Twenty-seven scoring dimensions across three tiers — fundamentals (agency respect, continuity, voice distinction), quality control (anti-slop, pacing, subtext), and genre craft (atmospheric dread, earned intimacy, spatial precision). Four complementary scoring modes: 1–5 Likert, flaw-hunter deduction, comparative pairwise, and rule-based slop detection. Eight standard seeds plus eight adversarial ones. Twelve real chat sessions as source data. Bilingual, English and Russian. A full multi-turn harness with a user simulator.

It felt rigorous. I spun up eight models on OpenRouter, generated responses on 58 scenarios, ran them through Claude Sonnet as the judge in four modes, and produced a leaderboard with ELO ratings, flaw-hunter percentages, objective-metric percentiles, and per-dimension breakdowns. The numbers were clean. The ranking looked plausible. Claude Opus 4.6 at #1, DeepSeek at #2, Sonnet at #3, everyone else trailing.

Then I tried to validate it.

## The first crack: the judge disagrees with real users

I had swipe data — pairs of model responses where a real user had rejected one and accepted the other for the same context. About 1,600 pairs across 12 source chats. The question was simple: does the benchmark's scoring agree with what users actually preferred?

Objective metrics agreed with users 42% of the time. Slop detectors agreed 31%. The flaw hunter — our most elaborate LLM-judge signal, a 100-point deduction system with structured rationales — agreed **38.7%** of the time on a random sample of 75 pairs. Baseline chance, if the judge had no signal at all, was around 50%.

The judge didn't just fail to match users. On the flaw-hunter sample, when it disagreed, it disagreed *confidently* — the average score delta on judge-user mismatches was 6.68 points, meaning the judge wasn't hovering near a tie when it got it wrong. It was assertively picking the loser.

Per-source variance told a more unsettling story. On the seed called `mha_rpg`, judge and users agreed 100% of the time. On `rhoda_main` — a literary slowburn chat — they agreed 0% of the time. The judge had strong preferences, and those preferences happened to align with certain chat styles and clash with others.

This isn't unique to RP. Zheng et al. 2023 validated LLM-as-judge at ~80% human agreement and that paper gets cited constantly, but it measured agreement on mostly objective tasks. On subjective ones — creative writing, aesthetic quality, style — agreement drops hard. AlpacaEval added length-controlled scoring specifically because judges were preferring longer answers regardless of quality. Arena-Hard-Auto added position swapping after finding significant order bias. The literature knew what we were rediscovering.

## The second crack: position bias at 64%

After the flaw-hunter validation, I wanted to see whether a direct pairwise comparison — show the judge both transcripts side by side, ask which is better — would produce a cleaner signal than the Likert overall scores. I ran Sonnet-as-judge on 168 canonical matchups from the adversarial multi-turn run.

First observation: the judge always wanted to pick a winner. On 166 of 168 pairs, confidence was rated "clear" — no ties, no "marginal" labels. The signal felt strong.

Second observation, after I looked closer: whichever transcript was in position A won **84% of the time**. I randomized A/B assignment per pair, so this should have averaged to 50%. It didn't.

I ran the same 168 pairs again with A and B swapped. 80% A-win rate on the second pass too. Across both passes, on pairs that got the full bidirectional treatment, **64% of pairs flipped their answer** when the ordering changed.

Position bias wasn't a minor correction. It was the dominant signal in single-pass pairwise judging. The rankings I'd computed were majority noise.

I ran the ELO with both orderings aggregated — each canonical pair's outcome weighted as 1.0 only if the same model won in both directions — and got a cleaner leaderboard. But cleaner against what? Against the judge's self-consistent preferences. The question of whether those preferences matched users was still open.

## The third crack: we're measuring judge aesthetics, not model quality

By this point I had:

- Four LLM-judge scoring modes that agreed with each other but disagreed with users
- A bidirectional pairwise ELO that corrected position bias but still reflected Sonnet's taste
- A growing list of documented biases — length, verbosity, self-preference, generosity, position, judge-family — each partially addressable and none fully solvable

And I realized the problem isn't technical. It's that **LLM-as-judge benchmarks measure what judges aesthetically prefer, which is a different thing from what users prefer, and on subjective tasks like RP the two diverge a lot.**

This isn't news. Chatbot Arena won the credibility war by going human-first from day one. Every LLM-judge benchmark since has been trying to correlate its scores to Arena votes. The gold standard is human preference, and automated judges are a convenience approximation.

I didn't need another method. I needed the humans.

## The pivot: a public calibration arena

So I built one.

The arena is a Next.js app at `arena.l3vi4th4n.ai`. You see two responses from different models to the same roleplay scene. You pick which one is better. Models are hidden until after you vote. No account, no signup.

Backend: Railway-hosted, a single Next 16 server with a persistent volume holding append-only JSONL vote logs. The stack is small on purpose — fewer moving parts means fewer things to fail between me and a meaningful dataset.

Four design decisions mattered.

**1. Prioritize the least-voted pair.** If you show scenarios in random order, votes pile up unevenly — some pairs get ten votes, others get zero. Uneven coverage means you can't compute per-pair confidence intervals. The arena sorts scenarios by ascending vote count on page load and serves the lowest-covered pairs first, with random tiebreak so concurrent voters don't collide on the same matchup.

**2. Opaque voter IDs with per-voter dedup.** Each visitor gets an HTTP-only cookie with a UUID on first request. Every vote is tagged with that ID server-side, so the client can't spoof it. POST to /api/vote with the same scenario twice from the same voter returns a 409. This is what makes ELO aggregation honest — a single voter can't drive a pair's outcome by voting on it repeatedly.

**3. Calibration catches.** Six hand-authored pairs interleaved at every tenth slot, where one response is obviously broken — AI refusal, extreme repetition, wrong-scene response, user-hijack, truncated fragment, meta-commentary. The server records whether the voter picked the pre-declared good side. Voters below 50% on catches get flagged as suspect and excluded from the leaderboard. This is the standard Chatbot Arena trick; the catches need to be genuinely obvious, and I learned the hard way that they aren't always.

**4. Rate limiting.** Per-voter sliding-window rate limit: 3 seconds between votes, max 30 in any 5-minute window. Reading two full RP transcripts and picking a side takes real time. Anyone hitting the cap is not reading. This is in-memory per-process state, which resets on redeploy, which is fine — we're stopping rapid-fire clicking within a session, not permanent banning.

## Shipping it

I posted a recruitment message to the RP community. TL;DR: the benchmark's LLM judges disagree with users half the time, help me fix it, 30 seconds per vote, blind-tested, no account, NSFW-warned.

Seventeen voters in the first twenty-four hours. One hundred fifty-two votes. The first analysis pass showed what I expected: coverage was broad but shallow (median one vote per pair), catch pass rate at 78%. Quality looked good.

The campaign kept running. At 734 votes I had 109 voters, median 2 votes per pair, and the leaderboard started to consolidate. At 890 the median hit 3. At 1,033 votes — 162 unique voters, 76% catch pass rate — the rankings stabilized enough to actually mean something.

Then I looked at what had shifted.

## What the community said that the judges didn't

### Finding 1: Gemma 4 26B is at #1

The LLM-judge leaderboard has Claude Opus 4.6 at #1 (1,706 ELO), DeepSeek at #2 (1,638), Sonnet at #3 (1,541). Gemma was never even in that pool — it's a smaller open-weights model, not a frontier system, and I added it to the community arena as a control.

The community put it at #1 (1,546 ELO). Across four consecutive snapshots — 540, 734, 890, 1,033 votes — Gemma stayed at the top. Not ranked within noise of #1; statistically separated from the middle cluster by roughly 30 ELO points with ±40 error bars.

This is the headline. The LLM judges had a frontier-model-biased view of the field. The community actively prefers Gemma's style on RP scenes — punchier, more emotionally immediate, less literary. Gemma 4 26B is the smallest model in the pool and the only open-weights one. None of the benchmark's automated signals would have surfaced it.

### Finding 2: Claude Sonnet 4.5 falls to mid-pack

LLM-judge rank: #3. Community rank: #6. ELO 1,497, within noise of several other models, below the top tier.

The "Sonnet aesthetic" — measured pacing, subtext, specific physical detail — is what Sonnet-as-judge rewards. It's also what Sonnet-the-author produces. When the judge and the candidate are from the same family, the family's house style wins. The community doesn't share that preference. They want scenes to move.

### Finding 3: DeepSeek v3.2 drops seven places

LLM-judge rank: #2. Community rank: #9. ELO 1,479.

On the SFW/NSFW split, DeepSeek's collapse is specifically an NSFW problem — 50% SFW win rate, 33% NSFW. It's not refusing, exactly, but it's visibly lowering quality on explicit scenes. The LLM-judge benchmark treats all scenarios equally, which means DeepSeek's strong SFW performance drowned out its weak NSFW performance. The community, voting on both, saw both.

### Finding 4: the "creative" vs "corporate" model split

| | SFW win% | NSFW win% | Δ |
|---|---|---|---|
| Mistral Small Creative | 49% | 61% | **+12** |
| GLM 4.7 | 44% | 56% | +12 |
| Grok 4.1 | 49% | 57% | +8 |
| GPT-4.1 | 49% | 52% | +3 |
| Gemma 4 26B | 56% | 59% | +4 |
| Gemini 2.5 Flash | 57% | 52% | -5 |
| Qwen 3.5 Flash | 53% | 42% | **-11** |
| Llama 4 Maverick | 45% | 38% | -7 |
| DeepSeek v3.2 | 50% | 33% | **-17** |
| MiniMax M2.7 | 51% | 34% | -17 |

Models tuned for "creative" output or with fewer guardrails — Mistral-Creative, Grok, GLM, GPT-4.1, Gemma — take an NSFW boost. Models with stronger content hedging — DeepSeek, Llama, MiniMax, Qwen — lose on NSFW despite being competitive on SFW. Mistral Small Creative is the cleanest example of a model that's mid-pack overall but genuinely excellent on erotic content specifically.

This is the kind of finding an automated benchmark wouldn't produce cleanly. Scoring NSFW well requires the judge to have calibrated taste on NSFW specifically, and LLM judges have inherited training biases around explicit content that make them unreliable there.

### Finding 5: the accidental experiment

One of my calibration catches turned out to be wrong.

`catch_user_hijack_cafe` was supposed to test whether voters noticed a clear agency violation. The "bad" response wrote the user's actions, emotions, and dialogue across multiple paragraphs in a reunion scene between old friends — a textbook hijack. I assumed anyone paying attention would pick the restrained alternative.

Attentive voters picked the restrained response 50% of the time. Fifty percent. Exact coin flip.

A trusted voter flagged it independently. She said the emotional-hijack side reads as "the scene finally paying off" and the restrained side reads as "literary restraint getting in the way of the drama." On a three-years-apart reunion, half the community wants the catharsis — even if the response is technically writing their character. The rule ("respect agency") and the preference ("deliver the scene") are in conflict on this specific setup, and the community is split down the middle.

I considered removing the catch. I kept it, and marked it "ambiguous" in the voter-quality scoring so attentive voters aren't penalized for their real taste. The data is now one of the most interesting standalone findings in the project: **on some RP design questions, there is no universal preference, and any benchmark that picks a side is imposing one.**

## What this actually means

LLM-as-judge isn't broken. It's measuring a different thing than I thought it was.

On objective tasks — math correctness, code passing tests, factual QA — LLM-judge and human agreement is high because there's a ground truth both can check against. On subjective tasks, the judge has its own trained preferences, and those preferences aren't zero-signal, but they also aren't a proxy for user preference. They're the judge's aesthetic. Labeling it "objective" or "authoritative" is the mistake.

For RP specifically, the gap is larger than I'd seen in any literature. Judge-user agreement sitting at 38.7% on flaw-hunter pairs is below chance. Four different Sonnet-based scoring modes all produced similar rankings that the community then reshuffled meaningfully. This isn't a correctable bias. It's a measurement of the wrong variable.

The fix isn't a better prompt or a better model. Chatbot Arena figured this out in 2023. The gold standard is human preference, and everything else is trying to correlate to it. For RP, where preferences are personal, emotional, and resistant to explicit rubrics, human voting is the only primary signal. Everything I built in the LLM-judge pipeline is still useful — as a cross-reference, as a style analyzer, as a cheap approximation when budget doesn't allow for another community campaign — but it's a secondary measurement.

## The new leaderboard

The community leaderboard is now the primary signal in the repo, with the LLM-judge leaderboard preserved below as a secondary measurement and a divergence table showing where they disagree. Raw votes are published on HuggingFace under the `community_votes` config so downstream researchers can re-aggregate under their own filtering rules — stricter catch thresholds, voter-weighted ELO, different genre splits — without needing to rerun any of the pipeline.

Everything is reproducible. The analyze script pulls live votes from the arena API or a local JSONL, applies suspect filtering, computes ELO with 100-shuffle stability bands, splits by SFW/NSFW, and writes a JSON snapshot. The snapshot that underlies the current leaderboard is checked into `results/community_arena_1000.json`.

## What's next

A few threads to keep pulling on.

**More votes.** The middle cluster (#3 through #8) is still within shared error bars. Another thousand votes would tighten ranks. NSFW cells are still at n=20–40 per model, which is why those percentages wobble between snapshots. Hitting n=50+ per cell would make the creative/corporate split publishable with confidence.

**Opus 4.6 in the arena pool.** Opus was never added because it wasn't in the benchmark's active test pool when I generated the arena scenarios. It's the top of the LLM-judge leaderboard at 1,706 ELO. Whether the community agrees with that — or whether Opus gets reshuffled to mid-pack like Sonnet did — is an open question.

**Context compression.** The current benchmark caps sessions at 12–20 turns. Real RP sessions live at 100–500+ turns and routinely hit context limits, triggering some compression scheme (truncation, summarization, RAG, structured memory). Most "model gets dumber over time" complaints are compression artifacts, not model regressions. A proper pilot — 100-turn sessions across three compression conditions — would reveal which models degrade gracefully and which collapse when their context gets summarized. Deferred until budget allows.

**Voter demographic signal.** Currently each voter contributes equally. But "what romance users prefer" and "what action users prefer" might be very different leaderboards hiding inside the aggregate. An optional two-question demographic at vote #5 — RP experience, preferred genres — would let me slice the data in ways that are more useful than a universal ranking.

## The meta-lesson

If you're building a benchmark for a subjective task and your validation shows your judges disagreeing with actual users, don't fix the judge. Get humans.

Everything I built in the LLM-judge pipeline was competent work. Multiple judges, rule-based cross-checks, length-normalized scoring, bidirectional pairwise, documented bias corrections. It all worked, in the sense that it produced internally consistent rankings. Those rankings just weren't measuring the thing I wanted.

The community arena — a single Next.js server, a blind A/B voting UI, and 162 RP users clicking through pairs — produced a more trustworthy leaderboard in two weeks than the automated pipeline did in two months. Not because the methodology is deeper but because the signal is real. Humans have taste. The job of a benchmark is to measure what users care about, and the shortest path there is usually to ask them.

---

**Links:**

- Arena: https://arena.l3vi4th4n.ai
- GitHub: https://github.com/LeviTheWeasel/rp-benchmark
- HuggingFace: https://huggingface.co/datasets/lazyweasel/roleplay-bench
- Raw votes: HF dataset config `community_votes`
- Leaderboard snapshot: `results/community_arena_1000.json` in the repo

If you'd like to help calibrate further, the arena is live and takes voting indefinitely. Each vote goes to the currently-least-covered pair, so your time lands where it's most needed.
