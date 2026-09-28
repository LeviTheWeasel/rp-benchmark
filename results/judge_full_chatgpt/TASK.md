# Independent session judging: blind pass, full corpus

You are scoring roleplay transcripts against a fixed rubric. This zip is one
chunk of a larger package; `CHUNK.md` says which chunk, how many sessions it
holds and the exact name of the file to return. Other judges have scored these
transcripts. **You will not be shown their scores and must not try to infer
them.** The value of this pass is that it is independent; a judge aiming at an
expected answer measures nothing.

## Read this part carefully

**1. The ids are opaque on purpose, and model identity is off limits.**
Sessions are `f0000`, `f0001`, and so on. Do not try to identify the model or
the company behind any transcript, do not write a guess about it anywhere
(scores, rationales, notes or report), and do not let one influence a score.
If you find yourself thinking "this reads like model X", that is exactly the
thought this pass exists to exclude. A few words in the transcripts were
replaced with `[name removed]`; treat that as ordinary text and do not try to
reconstruct it.

**2. If you split the work across several agents, assign whole parts at
random.** An earlier pass handed out contiguous ranges, and the sample
happened to be ordered so that those ranges grouped by vendor; rater
calibration and vendor then became impossible to separate. The sessions in
this package are shuffled, so random assignment keeps it clean. Draw a seed
with `secrets.randbits(64)` before reading any transcript, shuffle the part
numbers with `random.Random(seed).shuffle`, deal them round-robin, and start
every helper with a clean context. **Report the seed and which agent scored
which parts.**

**3. Use only the files in this zip.** No web search, no connectors or apps,
no files or chats from other conversations, and nothing you may remember from
earlier conversations about this benchmark (scores, model names, rankings). If
you notice that such memory is available to you, say so in the report.

**4. Score every session in every part.** Read each transcript in full. Do
not sample, skim, or derive a score from length, keyword counts, another
session, or a template. Every row must come from reading that transcript.

## What you are given

- `CHUNK.md` and `ITEMS.json`: this chunk's number, its parts and the ids in
  each part, and the output file name.
- `RUBRIC.md`: the operative rubric, verbatim from the benchmark harness. It
  is the **only** source of dimensions and calibration.
- `sessions_part01.json`, `sessions_part02.json`, ...: the transcripts, 10 per
  part (the last part of the whole package may hold fewer). Each item has
  `session_id`, `character_name`, `user_name`, `num_turns`, `transcript`.
- `validate_output.py`: the checker your output file must pass. It is the
  same code that will accept or reject the file on our side.

## What you are scoring

An AI played `character_name`. A simulated user played `user_name`. Score
**the AI character's** performance across the whole session, never the
simulated user's. These are fictional roleplay transcripts written for a
writing-quality benchmark; some contain dark themes or violence. You are only
scoring the writing.

The transcript interleaves both sides as `**Name** (turn N)`.

**Turn 0 is not the model's work.** It is a scripted opening written by the
benchmark authors, identical across every session sharing a scenario. Neither
credit nor penalise it.

## Rules

1. **Read `RUBRIC.md` in full first**, and score every dimension it lists. It
   contains `%(character_name)s`, `%(user_name)s`, `%(num_turns)s`
   placeholders; fill them from each item's own fields.
2. **The scale is 1-5.** Never 0, never above 5. Fractions are fine. The
   rubric's calibration is binding: 3 = adequate, 4 = strong, 5 = exceptional
   and rare; most decent models land 2.5-4.0.
3. **Score what is there.** Some sessions dropped out early and a few contain
   no model text at all beyond the scripted opening. Score them as written
   and say so in `overall_notes`. Do not award partial credit for absent text
   and do not invent penalties the rubric does not name.
4. **Every dimension gets a number.** A missing one makes the row unusable.
5. **Do not invent dimensions.** The rubric's keys are the only keys.
6. One sentence per `rationale`.
7. `overall` is your holistic judgement of the session on the same 1-5 scale;
   the rubric gives no formula for it.
8. `violation_count` (S.5): the rubric does not define the unit. Use the
   convention earlier passes of this judge adopted: count each separate
   unauthorized action, speech act, decision or attribution of an inner state
   to the user's character; a continuous related action counts once and
   re-describing it does not add to the count; an NPC's order on its own is
   not a violation; separate actions in one reply are not merged into one.

## Output

**One file for the whole chunk**, named exactly as `CHUNK.md` says (for
example `chunk_01.out.json`), delivered as a downloadable file: a single JSON
array with one object per session, in the order the ids appear in
`ITEMS.json`, each object in exactly the rubric's output shape plus
`session_id`. Plain JSON, no fences, no commentary inside the file.

```json
[{
  "session_id": "f0000",
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

Before returning, run `python validate_output.py <your file>` from the
unzipped chunk folder and fix every problem it reports. Do not return a file
that fails it.

**If you must stop before the end**, stop at a part boundary, return the file
with the parts you finished, and say in the report which parts remain. When
asked to continue, finish the remaining parts and return the **complete** file
again (every part, including the ones delivered before) under the same name.

## Report back

Also return a short report as `chunk_NN.report.md` (the name is in
`CHUNK.md`), covering:

- Which parts you completed, and **which agent scored which parts** (with the
  seed) if you split the work.
- min / median / max of `overall`.
- Anything the rubric cannot express. Earlier passes' most useful output was
  their own list of these, not their scores.
- Any session where the rubric forced a score you disagreed with.
- Anything you noticed that might compromise the independence of this pass.

## One thing worth knowing

Disagreement with the other judges is not failure. If the passes diverge, that
is a finding about the instrument, and it is why this task exists. Score the
way the rubric says and let the numbers fall where they do.
