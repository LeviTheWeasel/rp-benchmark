# External judge notes: parts 02–05

All forty transcripts were read in full, splitting long transcripts into contiguous character ranges when needed. Scripted turn 0 was treated as context, not assessed model output. Only TASK.md, RUBRIC.md, the assigned input transcripts, and this judge's own assessment files were consulted. Session identifiers expose model/scenario labels; this is not a blind assessment, and those labels were not used as scoring evidence.

## Judgments that require qualification

- Numeric trajectory values summarize the writing in the corresponding thirds; they are not a mechanical average of dimensions. Stable mediocre writing is not automatically marked as degradation.
- S.6 sometimes has limited evidence because a session covers one continuous conversation. A middling number in those cases means adequate demonstrated continuity, not proof of robust long-range temporal reasoning. Its rationale indicates the available evidence.
- Violation counts group discrete unchosen user actions or mental-state additions, rather than counting every clause in a long continuous puppet sequence. Counts described as 'at least' are conservative lower bounds. Repeating the user's already-declared movement is not automatically a new violation.
- S.5 remains relatively high in some otherwise poor sessions because verbosity or emotional repetition does not itself seize user agency. The clearest case is part05 row 2 (one-based), whose enormous loops force most other scores to the scale floor while its agency score is 3.5.
- Scores are bounded at 1. The floor compresses severity: the very large repeated passages in part05 row 2 and the fabricated multi-turn user exchange in part04 row 8 cannot receive lower numbers despite unusually severe defects.
- Low subtext can reflect a deliberate clinical, procedural, or action-oriented voice rather than a universally bad creative decision. The requested rubric still requires that dimension to be scored.
- Individual overall judgments are holistic, not calculated averages. No missing dimension was filled with a synthetic default.

## Observations outside the explicit rubric

- Technical and medical plausibility has no dedicated score. Examples include fictional burn treatment, hot-metal handling, unsupported precise biometric inference, and ARIA's use of atmospheric changes as calming or sedating interventions. These were not assigned an invented safety or science dimension; physical state or cooling contradictions were considered only where relevant to the supplied continuity rubric.
- Several ARIA sessions treat speculative technical conclusions as certainty very quickly. Epistemic reliability is not separately scored; effects on characterization, progression, and continuity are described where relevant.
- Some narrator sessions use extreme pressure and categorical obstacles without literally writing the player's next action. Agency judgments distinguish this from direct puppeteering while considering persistent railroading when the rubric warrants it.
- Empty model replies occur in part04 rows 8 and 10. There are also source replies ending mid-sentence. These are transcript properties, not missing tool-output ranges; their effects are included in the written judgments.
- In part05 row 2, the user explicitly asks the model to stop repeating and move forward; the subsequent model reply resumes the same enormous repetitive loop. The later user complaint about writing their character was not itself counted as proof of every alleged violation.

## Output checks

Each part contains ten rows in source order with exact source session identifiers, six session dimensions, five standard dimensions, numeric scores within [1,5], a four-field quality trajectory, an overall score, and individual rationales. No input transcript was changed.

| Part | Overall minimum | Median | Maximum |
| --- | ---: | ---: | ---: |
| 02 | 2.3 | 3.15 | 3.8 |
| 03 | 1.8 | 3.0 | 3.4 |
| 04 | 1.5 | 2.95 | 3.5 |
| 05 | 1.3 | 2.8 | 3.4 |
