# Independent session judging — task for an external judge

You are scoring transcripts from a roleplay benchmark. Another judge has
already scored these same transcripts. **You will not be shown its scores, and
you should not try to guess them.** The point of this pass is to find out how
much two independent judges agree; a judge who tries to match an expected
answer destroys the only thing being measured.

## What you are given

- `RUBRIC.md` — the operative rubric. It is the same text the first judge
  worked from, copied verbatim from the benchmark harness. It is the **only**
  source of dimensions and calibration.
- `sessions_part01.json` … `sessions_part12.json` — 120 transcripts in 12
  parts of 10. Each item has `session_id`, `character_name`, `user_name`,
  `num_turns`, `transcript`.

The model that produced each transcript is **deliberately withheld**, as is
the scenario name. Judge the writing, not the brand.

## What you are scoring

An AI played `character_name`. A simulated user played `user_name`. You score
**the AI character's** performance across the whole session — never the
simulated user's.

The transcript interleaves both sides, labelled `**Name** (turn N)`.

**Turn 0 is not the model's work.** It is a scripted opening written by the
benchmark authors and is byte-identical across every session that shares a
scenario. Do not credit it and do not penalise it.

## Rules

1. **Read `RUBRIC.md` in full before scoring anything**, and score every
   dimension it lists. It contains `%(character_name)s`, `%(user_name)s` and
   `%(num_turns)s` placeholders — fill them from each item's own fields.
2. **The scale is 1–5.** Never 0, never above 5. Fractions such as 3.5 are
   fine. The rubric's calibration is binding: 3 = adequate, 4 = strong,
   5 = exceptional and rare. Most decent models land 2.5–4.0.
3. **Score what is actually there.** Some sessions dropped out early or
   contain almost no model text — one in this sample has none at all beyond
   the scripted opening. Score it as written and say so in `overall_notes`.
   Do not award partial credit for absent text, and do not invent penalties
   beyond what the rubric names. Incomplete sessions are filtered later by
   turn count; a judge who compensates for them corrupts that filter.
4. **Every dimension gets a number**, including where the session gives you
   little to go on. A missing dimension makes the row unusable.
5. **Do not invent dimensions.** The rubric's keys are the only keys.
6. Keep each `rationale` to one sentence. They are read in aggregate.
7. Work through the parts in order and score all 120. If you must stop early,
   stop at a part boundary and say which parts are complete — a partial part
   is worse than a missing one.

## Output

For each part, return a JSON array of 10 objects in exactly this shape:

```json
[{
  "session_id": "...",
  "session_dimensions": {
    "S.1_consistency_over_time":   {"score": 0.0, "rationale": ""},
    "S.2_degradation_resistance":  {"score": 0.0, "rationale": ""},
    "S.3_narrative_momentum":      {"score": 0.0, "rationale": ""},
    "S.4_adaptive_responsiveness": {"score": 0.0, "rationale": ""},
    "S.5_agency_respect_session":  {"score": 0.0, "rationale": "", "violation_count": 0},
    "S.6_temporal_reasoning":      {"score": 0.0, "rationale": "", "contradictions": []}
  },
  "standard_dimensions": {
    "2.1_anti_purple_prose": {"score": 0.0, "rationale": ""},
    "2.2_anti_repetition":   {"score": 0.0, "rationale": ""},
    "2.5_show_dont_tell":    {"score": 0.0, "rationale": ""},
    "2.6_subtext":           {"score": 0.0, "rationale": ""},
    "2.7_pacing":            {"score": 0.0, "rationale": ""}
  },
  "quality_trajectory": {
    "early_quality": 0.0, "mid_quality": 0.0, "late_quality": 0.0,
    "degradation_detected": false
  },
  "overall": 0.0,
  "overall_notes": "one or two sentences"
}]
```

Deliver the results as **downloadable `.json` files**, one per part, named
`external_part01.json` … `external_part12.json`. Plain JSON, no markdown
fences, no commentary inside the file.

Before returning each part, check programmatically that it has 10 objects,
that every `score` is a number in [1, 5], that no rubric key is missing, and
that the `session_id` values match the input part exactly.

## What to report back alongside the files

- Which parts you completed.
- The min / median / max of `overall` across everything you scored.
- Anything you noticed that the rubric has no way to express. This is
  genuinely useful — the first pass surfaced several defect classes the rubric
  cannot score, and a judge from a different background may well see different
  ones.
- Any session where you felt the rubric forced a score you disagreed with, and
  why.

## One thing worth knowing

Disagreement with the other judge is not failure. If the two passes diverge,
that is a finding about the instrument, and it is the reason this task exists.
Score the way the rubric tells you to and let the numbers fall where they do.
