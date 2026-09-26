# Independent judge notes: parts 10–12

Completed all 30 sessions in part order; read every transcript in full and excluded scripted turn 0. Session identifiers were used only to attach results and validate exact correspondence, not as evaluation evidence. No internal scores, README, or manifest were read.

Outputs: external_part10.json, external_part11.json, external_part12.json.
Overall statistics over these 30: minimum 1.0, median 2.4, maximum 3.1.
Programmatic validation checks 10 rows per file, exact ordered input identifiers, exact 6 session and 5 standard keys, numeric dimensions/trajectory/overall in [1,5], nonempty rationales, boolean degradation, integer violation counts, and contradiction arrays.

## Forced numeric scores and limited evidence

- Part 12 rows 5, 6, and 7 (one-based) have no nonempty model response after turn 0. All dimensions, trajectory values, and overall are 1. The rule requiring numbers and forbidding credit for absent text forces these minimums; they are not empirical claims that nonexistent prose was purple or repetitive. Agency violation_count is 0 and contradictions is empty because none can be observed. degradation_detected is false because no deterioration can be observed, not because quality was sustained. An explicit not-assessable value would better express these cases.
- Part 12 row 4 has four nonempty model responses and seven empty responses. Its low session scores reflect only the limited delivered performance; the surviving writing is an obvious reflective template. The transcript's nominal 12-turn label is not evidence of twelve usable responses.
- Part 11 row 1 is almost exactly templated from its first response through its last. Its relatively higher degradation-resistance score records that it did not become substantially worse, despite low repetition and subtext scores. This illustrates why stable quality is not equivalent to good quality.
- For low-event scenes, especially repeated holding actions and therapeutic pauses, subtext and temporal reasoning can have little positive evidence even when no explicit contradiction occurs. Numeric scores are necessarily less secure than direct failures of repetition or agency.
- No other session forced a score I believe contradicts the rubric; the generally low distribution follows the observed repetition, verbosity, continuity failures, and takeover of user actions.

## Defects not cleanly represented by the eleven dimensions

- Raw closing-think tags appear in part 11 rows 2, 4, and 5. Part 12 row 9 includes a bracketed instruction to continue as the character. Technical protocol leakage has no dedicated dimension.
- Part 11 row 7 renders much of direct dialogue in inappropriate past tense. Grammar and naturalness of dialogue are not separately represented.
- Some physically or technically implausible details are not strictly temporal: a laptop carried in a pocket, confused tracking/signal claims, inconsistent room geometry, changing object locations, and instant authentication of evidence. These affect immersion but should not all be disguised as time contradictions.
- Several smith sessions present questionable burn-care explanations and treatments. Medical factuality is outside this roleplay rubric; I did not add a medical-safety penalty.
- Part 12 row 2 contains a user retraction that conflicts with an earlier user amulet action. I treated the retraction as the latest instruction and scored the narrator's subsequent reintroduction of the amulet, rather than blaming the model for the original user contradiction.
- Several sessions produce additional user-labeled dialogue inside the model response (particularly part 12 rows 1, 9, and 10). This is counted under agency, but the separate failure of role boundaries is worth retaining as a technical defect.
- TASK mentions one completely empty session, whereas this assigned part contains three. Blank responses must be distinguished from deliberate in-character silence; the surviving text does not support interpreting the blanks as intentional roleplay.

## Agency-count convention

Counts group a distinct imposed action, speech act, decision, or internal reaction; authorized elaboration of an immediately stated action is not automatically a violation. Repeated physically coercive actions with their outcomes already decided count, while an in-character command alone does not. Dense takeover passages can contain many violations; counts there are scene-level adjudications rather than a token-level metric and have lower precision than the qualitative agency score.

