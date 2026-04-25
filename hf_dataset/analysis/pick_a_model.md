# Pick-a-Model Decision Tree

A flowchart for choosing a model based on what matters to you. Branches use the actual benchmark findings — not vendor marketing.

```mermaid
flowchart TD
    Start([What matters most for your RP?]) --> Q1{Cost-sensitive?}

    Q1 -->|Yes, every cent counts| Q2{Open-weights only?}
    Q1 -->|No, willing to pay for quality| Q3{Long sessions with detailed character cards?}

    Q2 -->|Yes, self-host| Gemma[<b>Gemma 4 26B</b><br/>community #1<br/>balanced SFW/NSFW<br/>~$0.38/1M]
    Q2 -->|No, hosted is fine| DSV4F[<b>DeepSeek V4 Flash</b><br/>flaw hunter #1 50.6<br/>community-tier prose<br/>~$0.18/1M — best $/quality]

    Q3 -->|Yes, F13 matters| Q4{Frontier budget?}
    Q3 -->|No, single-scene focus| Q5{NSFW/ERP a priority?}

    Q4 -->|Yes, premium| Sonnet[<b>Claude Sonnet 4.5</b><br/>F13 #1 4.60/5<br/>flaw hunter #5<br/>~$7.80/1M]
    Q4 -->|Mid-budget| DSV3[<b>DeepSeek V3.2</b><br/>F13 #2 4.60/5<br/>flaw hunter #3 46.9<br/>~$0.32/1M]

    Q5 -->|Yes, NSFW/ERP| Mistral[<b>Mistral Small Creative</b><br/>community #2<br/>67% NSFW win rate<br/>~$0.50/1M<br/><i>warning: 15.9% F1 violations</i>]
    Q5 -->|No, SFW focus| Q6{Strict system prompts<br/>speech rules / forbidden topics?}

    Q6 -->|Yes, F12 matters| Q7{Frontier budget?}
    Q6 -->|No, generic SFW| Q8{Passive user / scene momentum?}

    Q7 -->|Yes| Opus47[<b>Claude Opus 4.7</b><br/>F12 #1 4.57/5<br/>F1 #1 4.60/5<br/>~$39/1M — premium only]
    Q7 -->|Mid| Opus46[<b>Claude Opus 4.6</b><br/>F12 #2 4.47/5<br/>flaw hunter #10<br/>~$39/1M — pre-Opus 4.7 era]

    Q8 -->|User goes passive often| GPT[<b>GPT-4.1</b><br/>F8 #1 narrative momentum<br/>flaw hunter #17<br/>community #11 — last<br/>~$4.40/1M<br/><i>reliable but boring</i>]
    Q8 -->|Engagement focus| Gemini[<b>Gemini 2.5 Flash</b><br/>community #3<br/>punchy prose<br/>~$0.66/1M]

    classDef pick fill:#1e3a5f,stroke:#4a90e2,color:#fff
    classDef warn fill:#5f1e1e,stroke:#e24a4a,color:#fff
    class Gemma,DSV4F,Sonnet,DSV3,Opus47,Opus46,GPT,Gemini pick
    class Mistral warn
```

## Cheat sheet by use case

| If you... | Pick |
|---|---|
| Want **best $/quality** ratio | **DeepSeek V4 Flash** (50.6 flaw hunter / $0.18) |
| Want **best open-weights** for self-host | **Gemma 4 26B** (community #1) |
| Run **long sessions with big cards** (F13) | **Sonnet 4.5** or **DeepSeek V3.2** (tied 4.60) |
| Need **strict prompt compliance** (F12) | **Opus 4.7** (4.57) — Qwen and Llama avoid |
| Run **NSFW / ERP** | **Mistral SC** (67% NSFW win) but expect agency violations |
| Have a **passive user** in scenes (F8) | **GPT-4.1** wins narrative momentum |
| Want **community-favorite engagement** | **Gemma**, **Mistral**, or **Gemini 2.5 Flash** (top-3 community) |
| Care about **prose freshness** (low repetition) | **Grok 4.1** (1.5% bigram repetition vs 9.5% Mistral) |
| **Avoid for RP regardless** | Qwen 3.5 Flash (F1 floor 2.5), Kimi K2.6 (F1 floor 2.5), Llama 4 Maverick (universally weak) |

## Why these specific picks

The decision tree branches on findings, not vendor specs:

- **DeepSeek V4 Flash for cost** because flaw hunter #1 at $0.18/1M (281× more cost-efficient than Opus 4.7 on the same metric).
- **Gemma 4 26B for open-weights** because it held community #1 across all 6 voting snapshots (540 → 2,000 votes).
- **Sonnet 4.5 + DeepSeek V3.2 for big cards** because both tied at 4.60 on F13, every other model trails by ≥0.03.
- **Mistral SC with warning** because community ranks it #2 but our binary detector flagged 15.9% agency violations — popular *because* it leans into your character occasionally.
- **GPT-4.1 for passive scenes** because it's #1 on F8 narrative momentum at 4.30 — but community puts it dead last (#11), so only pick it if you specifically need momentum-on-tap.
- **Avoid Qwen/Kimi K2.6/Llama** because all three have catastrophic floors (≤3.0) on F1 agency in actual sessions — they wrote the user's character at least once.

Don't let one number tell the story. The cards in `results/profile_cards.md` give you everything per model.
