# Community arena rank evolution

Across 3 snapshots: @1k, @1.6k, @2k


| Model | Rank @1k | ELO @1k | Rank @1.6k | ELO @1.6k | Rank @2k | ELO @2k | Δrank |
|---|---|---|---|---|---|---|---|
| gemma_4_26b | 1 | 1546 | 1 | 1545 | 1 | 1535 | 0 |
| mistral_small_creative | 3 | 1517 | 3 | 1521 | 2 | 1526 | -1 |
| gemini_2_5_flash | 2 | 1539 | 2 | 1531 | 3 | 1515 | +1 |
| minimax_m2_7 | 10 | 1473 | 6 | 1499 | 4 | 1510 | -6 |
| grok_4_1 | 5 | 1507 | 7 | 1498 | 5 | 1506 | 0 |
| claude_sonnet_4_5 | 6 | 1497 | 5 | 1500 | 6 | 1506 | 0 |
| deepseek_v3_2 | 9 | 1479 | 4 | 1504 | 7 | 1489 | -2 |
| qwen3_5_flash | 7 | 1496 | 8 | 1487 | 8 | 1487 | +1 |
| glm_4_7 | 8 | 1483 | 9 | 1479 | 9 | 1483 | +1 |
| llama_4_maverick | 11 | 1453 | 10 | 1471 | 10 | 1473 | -1 |
| gpt_4_1 | 4 | 1509 | 11 | 1466 | 11 | 1470 | +7 |

Δrank = (rank in latest snapshot) − (rank in first snapshot). Negative = moved up. Positive = moved down.

## Rank trajectory (visual)

```
  gemma_4_26b                   1 →  1 →  1  = (stable)
  mistral_small_creative        3 →  3 →  2  ↑ (1 up)
  gemini_2_5_flash              2 →  2 →  3  ↓ (1 down)
  minimax_m2_7                 10 →  6 →  4  ↑ (6 up)
  grok_4_1                      5 →  7 →  5  = (stable)
  claude_sonnet_4_5             6 →  5 →  6  = (stable)
  deepseek_v3_2                 9 →  4 →  7  ↑ (2 up)
  qwen3_5_flash                 7 →  8 →  8  ↓ (1 down)
  glm_4_7                       8 →  9 →  9  ↓ (1 down)
  llama_4_maverick             11 → 10 → 10  ↑ (1 up)
  gpt_4_1                       4 → 11 → 11  ↓ (7 down)
```

## Stability summary

- **Stable** (3): gemma_4_26b, grok_4_1, claude_sonnet_4_5
- **Climbed** (4): minimax_m2_7 (-6), deepseek_v3_2 (-2), mistral_small_creative (-1), llama_4_maverick (-1)
- **Dropped** (4): gpt_4_1 (+7), gemini_2_5_flash (+1), qwen3_5_flash (+1), glm_4_7 (+1)