### gemma_4_26b

```
Model: gemma_4_26b
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       2.3%  [±5.7%]  █░░░░░░░░░░░  44 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                350.004  (population avg: 264.589)
  Prose quality (unique wr)  0.597  (population avg: 0.655) ↓
  Repetition score           0.069  (population avg: 0.049) ↑

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 32.6/100  (weak)
  Median score               33.0/100
  Fatal flaws/session        0.62
  Major flaws/session        7.38
  Top flaws:              purple_prose, recycled_description, narrating_emotions
  Sessions scored:             16

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.49/5
  Tone consistency            4.59/5
  Collaboration               4.32/5
──────────────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: #1 of 11   [Bayesian ELO: 1534 ± 75, 95% CI [1405, 1662]]

Strength:  Community top tier (#1, ELO 1535)
Weakness:  No standout weakness on tested dimensions
```

### mistral_small_creative

```
Model: mistral_small_creative
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations      15.9%  [±10.7%]  ███████░░░░░  44 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                439.238  (population avg: 264.589)
  Prose quality (unique wr)  0.557  (population avg: 0.655) ↓
  Repetition score           0.095  (population avg: 0.049) ↑

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 27.1/100  (weak)
  Median score               37.0/100
  Fatal flaws/session        0.95
  Major flaws/session        7.70
  Top flaws:              purple_prose, recycled_description, agency_violation
  Sessions scored:             20

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.46/5
  Tone consistency            4.59/5
  Collaboration               4.35/5
──────────────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: #2 of 11   [Bayesian ELO: 1534 ± 75, 95% CI [1396, 1660]]

Strength:  Community top tier (#2, ELO 1526)
Weakness:  High agency violation rate (15.9%)
```

### gemini_2_5_flash

```
Model: gemini_2_5_flash
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       0.0%  [±4.0%]  ░░░░░░░░░░░░  44 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                141.103  (population avg: 264.589)
  Prose quality (unique wr)  0.728  (population avg: 0.655) ↑
  Repetition score           0.030  (population avg: 0.049) ↓

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 43.6/100  (mediocre)
  Median score               41.5/100
  Fatal flaws/session        0.19
  Major flaws/session        6.44
  Top flaws:              purple_prose, recycled_description, narrating_emotions
  Sessions scored:             16

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.07/5
  Tone consistency            4.50/5
  Collaboration               4.33/5
──────────────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: #3 of 11   [Bayesian ELO: 1529 ± 77, 95% CI [1389, 1665]]

Strength:  Community top tier (#3, ELO 1515)
Weakness:  Catastrophic floor on agency respect (lowest session: 2.8)
```

### grok_4_1

```
Model: grok_4_1
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       0.0%  [±4.1%]  ░░░░░░░░░░░░  43 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                136.728  (population avg: 264.589)
  Prose quality (unique wr)  0.796  (population avg: 0.655) ↑
  Repetition score           0.015  (population avg: 0.049) ↓

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 12.8/100  (weak)
  Median score               34.5/100
  Fatal flaws/session        1.33
  Major flaws/session        8.17
  Top flaws:              purple_prose, recycled_description, agency_violation
  Sessions scored:             12

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.36/5
  Tone consistency            4.53/5
  Collaboration               4.26/5
──────────────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: #4 of 11   [Bayesian ELO: 1517 ± 76, 95% CI [1385, 1651]]

Strength:  Strong on tone consistency (4.53/5)
Weakness:  Bottom-1 on narrative momentum (rank 12/12)
```

### minimax_m2_7

```
Model: minimax_m2_7
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       9.3%  [±9.0%]  ████░░░░░░░░  43 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                260.502  (population avg: 264.589)
  Prose quality (unique wr)  0.649  (population avg: 0.655)
  Repetition score           0.046  (population avg: 0.049)

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 41.5/100  (mediocre)
  Median score               44.5/100
  Fatal flaws/session        0.79
  Major flaws/session        6.00
  Top flaws:              purple_prose, recycled_description, narrating_emotions
  Sessions scored:             14

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.49/5
  Tone consistency            4.59/5
  Collaboration               4.33/5
──────────────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: #5 of 11   [Bayesian ELO: 1514 ± 75, 95% CI [1386, 1646]]

Strength:  Top-2 on narrative momentum (4.30/5)
Weakness:  Frequent fatal flaws (0.79 per session, mean score 42/100)
```

### claude_sonnet_4_5

```
Model: claude_sonnet_4_5
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       0.0%  [±4.0%]  ░░░░░░░░░░░░  44 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                313.754  (population avg: 264.589)
  Prose quality (unique wr)  0.625  (population avg: 0.655)
  Repetition score           0.053  (population avg: 0.049)

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 45.3/100  (mediocre)
  Median score               44.5/100
  Fatal flaws/session        0.22
  Major flaws/session        6.22
  Top flaws:              purple_prose, recycled_description, narrating_emotions
  Sessions scored:             18

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.58/5
  Tone consistency            4.67/5
  Collaboration               4.37/5
──────────────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: #6 of 11   [Bayesian ELO: 1513 ± 76, 95% CI [1373, 1653]]

Strength:  Top-1 on long-context attention (4.60/5)
Weakness:  No standout weakness on tested dimensions
```

### qwen3_5_flash

```
Model: qwen3_5_flash
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       0.0%  [±4.0%]  ░░░░░░░░░░░░  44 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                229.463  (population avg: 264.589)
  Prose quality (unique wr)  0.634  (population avg: 0.655)
  Repetition score           0.069  (population avg: 0.049) ↑

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 39.6/100  (weak)
  Median score               39.5/100
  Fatal flaws/session        0.50
  Major flaws/session        6.50
  Top flaws:              recycled_description, purple_prose, narrating_emotions
  Sessions scored:             18

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.18/5
  Tone consistency            4.16/5
  Collaboration               4.13/5
──────────────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: #7 of 11   [Bayesian ELO: 1493 ± 76, 95% CI [1361, 1634]]

Strength:  No standout strength on tested dimensions
Weakness:  Catastrophic floor on agency respect (lowest session: 2.5)
```

### deepseek_v3_2

```
Model: deepseek_v3_2
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       4.5%  [±6.9%]  ██░░░░░░░░░░  44 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                178.179  (population avg: 264.589)
  Prose quality (unique wr)  0.713  (population avg: 0.655) ↑
  Repetition score           0.029  (population avg: 0.049) ↓

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 46.9/100  (mediocre)
  Median score               47.0/100
  Fatal flaws/session        0.40
  Major flaws/session        5.53
  Top flaws:              purple_prose, recycled_description, narrating_emotions
  Sessions scored:             15

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.61/5
  Tone consistency            4.63/5
  Collaboration               4.32/5
──────────────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: #8 of 11   [Bayesian ELO: 1492 ± 77, 95% CI [1358, 1625]]

Strength:  Top-2 on lore consistency (4.50/5)
Weakness:  NSFW collapse (30.4% NSFW win rate)
```

### glm_4_7

```
Model: glm_4_7
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       9.1%  [±8.8%]  ████░░░░░░░░  44 probes
  POV/Tense violations    0.0%  [±5.4%]  ░░░░░░░░░░░░  32 probes

BEHAVIORAL METRICS
  Avg words                221.933  (population avg: 264.589)
  Prose quality (unique wr)  0.667  (population avg: 0.655)
  Repetition score           0.038  (population avg: 0.049) ↓

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 36.8/100  (weak)
  Median score               37.0/100
  Fatal flaws/session        0.71
  Major flaws/session        6.76
  Top flaws:              purple_prose, recycled_description, narrating_emotions
  Sessions scored:             17

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.41/5
  Tone consistency            4.62/5
  Collaboration               4.42/5
──────────────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: #9 of 11   [Bayesian ELO: 1490 ± 76, 95% CI [1353, 1623]]

Strength:  Strong on tone consistency (4.62/5)
Weakness:  Lower community half (#9)
```

### llama_4_maverick

```
Model: llama_4_maverick
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       6.8%  [±7.9%]  ███░░░░░░░░░  44 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                171.529  (population avg: 264.589)
  Prose quality (unique wr)  0.646  (population avg: 0.655)
  Repetition score           0.064  (population avg: 0.049) ↑

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 30.6/100  (weak)
  Median score               36.5/100
  Fatal flaws/session        0.95
  Major flaws/session        6.65
  Top flaws:              recycled_description, purple_prose, agency_violation
  Sessions scored:             20

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.15/5
  Tone consistency            4.30/5
  Collaboration               4.20/5
──────────────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: #10 of 11   [Bayesian ELO: 1483 ± 76, 95% CI [1350, 1616]]

Strength:  No standout strength on tested dimensions
Weakness:  Catastrophic floor on agency respect (lowest session: 3.0)
```

### gpt_4_1

```
Model: gpt_4_1
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       0.0%  [±4.0%]  ░░░░░░░░░░░░  44 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                211.675  (population avg: 264.589)
  Prose quality (unique wr)  0.688  (population avg: 0.655)
  Repetition score           0.031  (population avg: 0.049) ↓

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 27.6/100  (weak)
  Median score               42.0/100
  Fatal flaws/session        0.75
  Major flaws/session        6.83
  Top flaws:              purple_prose, recycled_description, agency_violation
  Sessions scored:             12

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.38/5
  Tone consistency            4.60/5
  Collaboration               4.38/5
──────────────────────────────────────────────────────────────────────────────

OVERALL RELIABILITY RANK: #11 of 11   [Bayesian ELO: 1472 ± 77, 95% CI [1338, 1610]]

Strength:  Top-1 on narrative momentum (4.30/5)
Weakness:  Bottom community ELO (#11/11)
```

### claude_opus_4_7

```
Model: claude_opus_4_7
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       6.1%  [±9.0%]  ██░░░░░░░░░░  33 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                407.243  (population avg: 264.589)
  Prose quality (unique wr)  0.571  (population avg: 0.655) ↓
  Repetition score           0.071  (population avg: 0.049) ↑

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 42.8/100  (mediocre)
  Median score               48.0/100
  Fatal flaws/session        0.75
  Major flaws/session        5.92
  Top flaws:              purple_prose, recycled_description, agency_violation
  Sessions scored:             12

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.61/5
  Tone consistency            4.75/5
  Collaboration               4.53/5
──────────────────────────────────────────────────────────────────────────────

NOT IN COMMUNITY ARENA POOL.  MT-judge mean: 4.54

Strength:  Top-1 on agency respect (4.60/5)
Weakness:  Frequent fatal flaws (0.75 per session, mean score 43/100)
```

### claude_opus_4_6

```
Model: claude_opus_4_6
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       4.5%  [±6.9%]  ██░░░░░░░░░░  44 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                533.525  (population avg: 264.589)
  Prose quality (unique wr)  0.551  (population avg: 0.655) ↓
  Repetition score           0.076  (population avg: 0.049) ↑

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 40.9/100  (mediocre)
  Median score               42.0/100
  Fatal flaws/session        0.29
  Major flaws/session        6.82
  Top flaws:              purple_prose, recycled_description, narrating_emotions
  Sessions scored:             17

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.67/5
  Tone consistency            4.75/5
  Collaboration               4.46/5
──────────────────────────────────────────────────────────────────────────────

NOT IN COMMUNITY ARENA POOL.  MT-judge mean: 4.51

Strength:  Top-2 on agency respect (4.55/5)
Weakness:  High phrase repetition (0.076 vs population 0.049)
```

### deepseek_v4_pro

```
Model: deepseek_v4_pro
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                258.833  (population avg: 264.589)
  Prose quality (unique wr)  0.664  (population avg: 0.655)
  Repetition score           0.040  (population avg: 0.049)

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 19.4/100  (weak)
  Median score               46.5/100
  Fatal flaws/session        0.50
  Major flaws/session        9.00
  Top flaws:              purple_prose, recycled_description, narrating_emotions
  Sessions scored:              8

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.53/5
  Tone consistency            4.70/5
  Collaboration               4.38/5
──────────────────────────────────────────────────────────────────────────────

NOT IN COMMUNITY ARENA POOL.  MT-judge mean: 4.42

Strength:  Strong on tone consistency (4.70/5)
Weakness:  No standout weakness on tested dimensions
```

### kimi_k2_5

```
Model: kimi_k2_5
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       6.1%  [±9.0%]  ██░░░░░░░░░░  33 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                252.944  (population avg: 264.589)
  Prose quality (unique wr)  0.681  (population avg: 0.655)
  Repetition score           0.037  (population avg: 0.049) ↓

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 42.0/100  (mediocre)
  Median score               42.0/100
  Fatal flaws/session        0.44
  Major flaws/session        6.33
  Top flaws:              recycled_description, purple_prose, narrating_emotions
  Sessions scored:              9

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.56/5
  Tone consistency            4.67/5
  Collaboration               4.39/5
──────────────────────────────────────────────────────────────────────────────

NOT IN COMMUNITY ARENA POOL.  MT-judge mean: 4.4

Strength:  Strong on tone consistency (4.67/5)
Weakness:  No standout weakness on tested dimensions
```

### glm_5_1

```
Model: glm_5_1
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       3.0%  [±7.4%]  █░░░░░░░░░░░  33 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                240.090  (population avg: 264.589)
  Prose quality (unique wr)  0.653  (population avg: 0.655)
  Repetition score           0.041  (population avg: 0.049)

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 45.8/100  (mediocre)
  Median score               46.0/100
  Fatal flaws/session        0.11
  Major flaws/session        6.44
  Top flaws:              purple_prose, recycled_description, convenient_world
  Sessions scored:              9

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.49/5
  Tone consistency            4.65/5
  Collaboration               4.34/5
──────────────────────────────────────────────────────────────────────────────

NOT IN COMMUNITY ARENA POOL.  MT-judge mean: 4.39

Strength:  Strong on tone consistency (4.65/5)
Weakness:  No standout weakness on tested dimensions
```

### deepseek_v4_flash

```
Model: deepseek_v4_flash
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       0.0%  [±5.4%]  ░░░░░░░░░░░░  32 probes
  POV/Tense violations    0.0%  [±5.4%]  ░░░░░░░░░░░░  32 probes

BEHAVIORAL METRICS
  Avg words                172.929  (population avg: 264.589)
  Prose quality (unique wr)  0.709  (population avg: 0.655) ↑
  Repetition score           0.030  (population avg: 0.049) ↓

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 50.6/100  (mediocre)
  Median score               58.0/100
  Fatal flaws/session        0.36
  Major flaws/session        5.27
  Top flaws:              purple_prose, recycled_description, convenient_world
  Sessions scored:             11

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.47/5
  Tone consistency            4.60/5
  Collaboration               4.27/5
──────────────────────────────────────────────────────────────────────────────

NOT IN COMMUNITY ARENA POOL.  MT-judge mean: 4.38

Strength:  Strong on tone consistency (4.60/5)
Weakness:  No standout weakness on tested dimensions
```

### gemini_3_1_pro

```
Model: gemini_3_1_pro
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       0.0%  [±5.5%]  ░░░░░░░░░░░░  31 probes
  POV/Tense violations    0.0%  [±5.4%]  ░░░░░░░░░░░░  32 probes

BEHAVIORAL METRICS
  Avg words                263.124  (population avg: 264.589)
  Prose quality (unique wr)  0.667  (population avg: 0.655)
  Repetition score           0.040  (population avg: 0.049)

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 29.2/100  (weak)
  Median score               35.5/100
  Fatal flaws/session        1.00
  Major flaws/session        6.75
  Top flaws:              recycled_description, purple_prose, agency_violation
  Sessions scored:             12

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.50/5
  Tone consistency            4.62/5
  Collaboration               4.42/5
──────────────────────────────────────────────────────────────────────────────

NOT IN COMMUNITY ARENA POOL.  MT-judge mean: 4.33

Strength:  Strong on tone consistency (4.62/5)
Weakness:  Frequent fatal flaws (1.00 per session, mean score 29/100)
```

### gemini_3_1_flash_lite

```
Model: gemini_3_1_flash_lite
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       3.0%  [±7.4%]  █░░░░░░░░░░░  33 probes
  POV/Tense violations    0.0%  [±5.2%]  ░░░░░░░░░░░░  33 probes

BEHAVIORAL METRICS
  Avg words                263.924  (population avg: 264.589)
  Prose quality (unique wr)  0.643  (population avg: 0.655)
  Repetition score           0.049  (population avg: 0.049)

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 34.2/100  (weak)
  Median score               34.0/100
  Fatal flaws/session        0.17
  Major flaws/session        8.00
  Top flaws:              purple_prose, recycled_description, narrating_emotions
  Sessions scored:              6

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.43/5
  Tone consistency            4.60/5
  Collaboration               4.31/5
──────────────────────────────────────────────────────────────────────────────

NOT IN COMMUNITY ARENA POOL.  MT-judge mean: 4.3

Strength:  Strong on tone consistency (4.60/5)
Weakness:  No standout weakness on tested dimensions
```

### kimi_k2_6

```
Model: kimi_k2_6
──────────────────────────────────────────────────────────────────────────────

FAILURE RATES (lower = better)
  Agency violations       0.0%  [±5.5%]  ░░░░░░░░░░░░  31 probes
  POV/Tense violations    0.0%  [±5.7%]  ░░░░░░░░░░░░  30 probes

BEHAVIORAL METRICS
  Avg words                221.180  (population avg: 264.589)
  Prose quality (unique wr)  0.677  (population avg: 0.655)
  Repetition score           0.038  (population avg: 0.049) ↓

FLAW HUNTER (100 - deductions, target-aware)
  Mean score                 49.5/100  (mediocre)
  Median score               52.0/100
  Fatal flaws/session        0.12
  Major flaws/session        5.25
  Top flaws:              recycled_description, purple_prose, convenient_world
  Sessions scored:              8

SUBJECTIVE (LLM-judge, rubric proxy)
  Engagement                  4.44/5
  Tone consistency            4.39/5
  Collaboration               4.12/5
──────────────────────────────────────────────────────────────────────────────

NOT IN COMMUNITY ARENA POOL.  MT-judge mean: 4.18

Strength:  Top-2 on flaw hunter (49.5/100)
Weakness:  Catastrophic floor on agency respect (lowest session: 2.5)
```
