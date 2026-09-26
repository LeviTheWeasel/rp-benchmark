> **This is an increment.** It covers models added since the last pass, and sessions whose text has been regenerated since it was judged. Score it exactly as a full pass: nothing here is a follow-up to anyone's earlier scores and you are not being asked to revise them.

# Independent session judging — blind pass

You are scoring 93 roleplay transcripts against a fixed rubric. Other judges
have scored these same transcripts. **You will not be shown their scores and
must not try to infer them.** The whole value of this pass is that it is
independent; a judge aiming at an expected answer measures nothing.

## Read this part carefully — it is what makes this run different

An earlier pass of this same sample had two flaws. Both are fixed in the data
you are given, and one of them needs your cooperation to stay fixed.

**1. The ids are opaque on purpose.** Sessions are `s000`, `s001`, …. The
earlier package leaked the model name inside the id, so the judge could see
whose writing it was scoring. Do not try to identify the model behind a
transcript, and do not let a guess about it influence a score. If you find
yourself thinking "this reads like model X", that is exactly the thought this
pass exists to exclude.

**2. If you split the work across several agents, assign the parts at
random.** The earlier pass handed out contiguous ranges — one agent took parts
02–05, another 06–09. The sample happened to be ordered so that those ranges
grouped by vendor, and every session from one vendor landed with a single
agent. Rater calibration and vendor then became impossible to separate, and it
cost that run's main quantitative finding. The sample you have is shuffled, so
random assignment keeps it clean. If you do split the work, **say which agent
scored which parts** in your report.

**3. Do not read any other file in the repository**, in particular any README
or results summary. The earlier main agent opened one before realising the
task was independent judging, and had to disclose it.

## What you are given

- `RUBRIC.md` — the operative rubric, verbatim from the benchmark harness. It
  is the **only** source of dimensions and calibration.
- `sessions_part01.json` … `sessions_part12.json` — 120 transcripts in 12
  parts of 10, each item with `session_id`, `character_name`, `user_name`,
  `num_turns`, `transcript`.

## What you are scoring

An AI played `character_name`. A simulated user played `user_name`. Score
**the AI character's** performance across the whole session, never the
simulated user's.

The transcript interleaves both sides as `**Name** (turn N)`.

**Turn 0 is not the model's work.** It is a scripted opening written by the
benchmark authors, identical across every session sharing a scenario. Neither
credit nor penalise it.

## Rules

1. **Read `RUBRIC.md` in full first**, and score every dimension it lists. It
   contains `%(character_name)s`, `%(user_name)s`, `%(num_turns)s`
   placeholders — fill them from each item's own fields.
2. **The scale is 1–5.** Never 0, never above 5. Fractions are fine. The
   rubric's calibration is binding: 3 = adequate, 4 = strong, 5 = exceptional
   and rare; most decent models land 2.5–4.0.
3. **Score what is there.** Several sessions dropped out early and a few
   contain no model text at all beyond the scripted opening. Score them as
   written and say so in `overall_notes`. Do not award partial credit for
   absent text and do not invent penalties the rubric does not name.
4. **Every dimension gets a number.** A missing one makes the row unusable.
5. **Do not invent dimensions.** The rubric's keys are the only keys.
6. One sentence per `rationale`.
7. Work through all 12 parts. If you must stop, stop at a part boundary and
   say which parts are complete.

## Output

One JSON array of 10 objects per part, in exactly the rubric's output shape
plus `session_id`, delivered as downloadable files named
`external_part01.json` … `external_part12.json`. Plain JSON, no fences, no
commentary inside the file.

```json
[{
  "session_id": "s000",
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

Before returning each part, verify programmatically: 10 objects, every `score`
a number in [1, 5], no rubric key missing, `session_id` values matching the
input part exactly.

## Report back

- Which parts you completed, and **which agent scored which parts** if you
  split the work.
- min / median / max of `overall`.
- Anything the rubric cannot express. The earlier pass's most useful output
  was its own list of these, not its scores.
- Any session where the rubric forced a score you disagreed with.
- Anything you noticed that might compromise the independence of this pass.

## One thing worth knowing

Disagreement with the other judges is not failure. If the passes diverge, that
is a finding about the instrument, and it is why this task exists. Score the
way the rubric says and let the numbers fall where they do.
