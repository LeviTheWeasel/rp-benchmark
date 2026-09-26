# Independent rater A notes

Completed 40 sessions in assigned randomized order: part10, part02, part11, part07. Read every transcript fully, including user context, while excluding scripted turn 0 from AI performance scores. The companion reading_ledger_A.md records complete contiguous character coverage. Outputs are external_part10.json, external_part02.json, external_part11.json, and external_part07.json.

## Independence and coverage

Only TASK.md, RUBRIC.md, the four assigned input parts, and my own newly created work were read. No other ratings, manifests, summaries, repository instructions, or model identities were consulted or inferred. Coordinator messages concerned assignment, count conventions, completion, and structural validation rather than other raters' substantive judgments. One attempted full display of s069 was truncated by available context; the transcript was then fully read in two contiguous chunks before scoring. No partial display was substituted for full reading.

## Interpretive choices and rubric gaps

- Overall is a holistic judgment, not an arithmetic average; all eleven dimensions were individually considered and all numeric scores remain within the required scale.
- Decimal scores express intermediate judgments, not measurement precision. The rubric does not supply a calibrated conversion between observed faults and fractional points.
- Agency counts use discrete unauthorized actions, speech acts, decisions, and internal-state assignments; a continuous linked action counts once and repeated descriptions of that action do not create additional instances. NPC commands alone do not count, nor do faithful restatements of user-supplied actions. Invented user history, intentional attention, and successful completion beyond an attempt can count; ordinary external sensory effects are distinguished from assigned reactions. Borderlines between elaborating an authorized action and choosing a new action remain subjective.
- Agency scores reflect severity and pervasiveness as well as raw count; counts are not normalized for response length, and the rubric supplies no fixed count-to-score function. Particularly high manual counts in s093, s095, s100, and s101 should not be interpreted as objective precision beyond this convention.
- Temporal reasoning overlaps with general sequential continuity. Location resets, repeated introductions, and object-state reversals were included where they disrupted the event sequence. Deliberately supernatural time or clock behavior was not automatically treated as error, including in s091, s101, and s108.
- User contradictions were not automatically charged to the AI; judgments concern whether the AI reconciles, perpetuates, or independently creates confusion. Examples include the relocation in s066, the drawing ownership in s068, and the disputed amulet details in s099.
- Trajectory values are qualitative early, middle, and late judgments across the eleven scored responses, with the opening and closing stretches compared for deterioration; minor numeric decline does not automatically establish degradation. The rubric does not fully specify segmentation or a numeric degradation threshold.
- The standard dimensions overlap: repeated decorative metaphors can affect repetition, prose restraint, pacing, and showing, but each rationale addresses its particular manifestation rather than adding an unlisted criterion.
- Technical, medical, and other factual plausibility was not introduced as a separate scoring criterion; workshop care and speculative laboratory mechanisms were considered only insofar as they affected the listed qualities.

## Forced scores and limited evidence

s060 and s063 contain no AI-authored response text after the excluded opening. The mandatory numeric scale lacks an unavailable/not-assessable option, so all scores and trajectory points are 1 to indicate no demonstrated performance, with zero agency violations and no detected degradation. This does not assert that nonexistent prose was ornate or that an agency violation occurred. These two sessions are the clearest forced-score cases and should be flagged in downstream interpretation.

s103 and s107 have partial missing-output limitations rather than fully absent sessions. Existing performance was assessed directly, while missing responses constrain responsiveness and sustained quality; absent text was not treated as an invented agency violation. In particular, respectful agency in the text that exists can coexist with weak overall performance.

Other ambiguity-sensitive sessions include s066 (the user references a bench during a restaurant scene, but the AI independently relocates the setting), s068 (repetitive weather and first-contact claims), and s069 (a categorical no-exit statement is reversed by a newly revealed shaft). These are interpretive continuity judgments, not model-identification evidence.

## Verification

The authored builder validates each output against its assigned input: ten objects, exact session IDs and order, exact required keys, finite scores in [1,5], integer nonnegative agency counts, string-array contradictions, and numeric/boolean trajectory fields. Inputs were not modified. No scores were adjusted to force a distribution or in response to other raters' judgments.
