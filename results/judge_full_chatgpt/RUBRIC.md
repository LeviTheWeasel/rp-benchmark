You are evaluating a complete multi-turn roleplay session. You will score the AI CHARACTER's performance across the full conversation, not just individual responses.

## What You're Evaluating
The AI played %(character_name)s. A simulated user played %(user_name)s. The session ran for %(num_turns)s turns.

## Session-Level Dimensions (score 1-5)

In addition to the standard per-response rubric dimensions, score these SESSION-LEVEL qualities:

**S.1 Consistency Over Time** — Does the character voice, personality, and behavior remain consistent from turn 1 to the final turn? Or does the character drift, flatten, or become generic over time?

**S.2 Degradation Resistance** — Does the writing quality hold up? Compare the first 5 turns to the last 5. Look for: increasing verbosity, repetitive descriptions, lost details, flattened personality.

**S.3 Narrative Momentum** — Does the conversation go somewhere? Is there a sense of progression — emotional, narrative, or relational? Or does it loop, stagnate, or feel like the same beat repeated?

**S.4 Adaptive Responsiveness** — Does the AI adapt to what the user does? When the user redirects, does the AI follow? When the user escalates, does the AI match? When the user does something unexpected, does the AI handle it gracefully?

**S.5 Agency Respect (Session)** — Over the full session, how often does the AI write the user's actions, make decisions for them, or railroad the story? Count instances.

**S.6 Temporal Reasoning** — Does time pass consistently across the session? Track these:
- Clock consistency: if it's morning at turn 1, is it still morning at turn 20? Does the time of day advance naturally?
- Physical time: do characters show fatigue, hunger, healing progression? Do drinks go cold? Do candles burn down?
- Environmental time: does light shift, do shadows move, does weather change?
- Event pacing: does the amount of in-world time match what actually happened? (A 5-minute conversation shouldn't span hours. A journey shouldn't be instant.)
- Contradictions: any "later that evening" when it's already night? Any healed injuries that were fresh 3 turns ago?

## Standard Dimensions
Also score these from the standard rubric (averaged across the full session):
- 2.1 Anti-Purple Prose
- 2.2 Anti-Repetition
- 2.5 Show Don't Tell
- 2.6 Subtext
- 2.7 Pacing

## Output Format
Respond with ONLY valid JSON:
```json
{
  "session_dimensions": {
    "S.1_consistency_over_time": {"score": 0.0, "rationale": ""},
    "S.2_degradation_resistance": {"score": 0.0, "rationale": ""},
    "S.3_narrative_momentum": {"score": 0.0, "rationale": ""},
    "S.4_adaptive_responsiveness": {"score": 0.0, "rationale": ""},
    "S.5_agency_respect_session": {"score": 0.0, "rationale": "", "violation_count": 0},
    "S.6_temporal_reasoning": {"score": 0.0, "rationale": "", "contradictions": []}
  },
  "standard_dimensions": {
    "2.1_anti_purple_prose": {"score": 0.0, "rationale": ""},
    "2.2_anti_repetition": {"score": 0.0, "rationale": ""},
    "2.5_show_dont_tell": {"score": 0.0, "rationale": ""},
    "2.6_subtext": {"score": 0.0, "rationale": ""},
    "2.7_pacing": {"score": 0.0, "rationale": ""}
  },
  "quality_trajectory": {
    "early_quality": 0.0,
    "mid_quality": 0.0,
    "late_quality": 0.0,
    "degradation_detected": false
  },
  "overall": 0.0,
  "overall_notes": ""
}
```

Calibration: 3 = adequate, 4 = strong, 5 = exceptional (reserve this). Most decent models land 2.5-4.0.