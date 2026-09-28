# Chunk 01 judging report

Completed all 11 parts, all 110 sessions (`f0000`–`f0109`). Every transcript was read in full and individually judged; scripted turn 0 was excluded. Internal role labels inside model responses were treated as model-authored text. No parts remain. The output follows `ITEMS.json` order.

Overall scores: **minimum 1.2, median 2.8, maximum 4.2**. Overall is a holistic judgment, not a formula or an average of dimensions.

## Assignment and independence

The sole judge for every part of this chunk was delegated agent `/root/judge_chunk_01`: parts 01, 02, 03, 04, 05, 06, 07, 08, 09, 10 and 11. No further delegation occurred.

The coordinator supplied seed **13988562299819289817**, drawn before delegated helpers read any transcript, and reported shuffling whole chunks with `random.Random(seed).shuffle`, assigning each chunk to one clean-context agent with a three-worker limit. This is a procedural deviation from TASK.md's specified random round-robin assignment of whole parts: this agent received all parts of chunk 01 together. The actual assignment is disclosed rather than described as compliant part-level randomization.

The coordinator disclosed an earlier isolated pass on part 01. This judge did not see that pass, its scores, its code, or its notes and independently judged all 110 sessions. No other chunk or judge's work was consulted. No model identity was inferred or guessed, no external sources or apps were used, and no remembered benchmark scores or rankings informed the judgments. After a usage-limit interruption and context compactions, work resumed from this judge's own saved rows and reading notes.

## Rubric limits and interpretation

- Agency counts distinguish separate unauthorized actions, speech acts, decisions and inner-state attributions; continuous related actions and repeated descriptions do not automatically multiply the count. Commands alone are not violations. Borderlines remain around implied travel, routine physical treatment, involuntary reactions, invented memories and authoritative statements of what a character perceives or understands; counts are manual judgments, not an automatic metric.
- Temporal reasoning also captures consequential state continuity, including misplaced objects, duplicated actions and weapon changes, because the schema has no separate continuity dimension. Deliberate supernatural distortions, such as those in `f0107`, were not treated as ordinary clock errors. User-originated resets were distinguished from model-created contradictions, while missing transitions could still weaken coherence.
- There is no separate dimension for adherence to OOC collaboration requests, so ignored corrections affected responsiveness and agency. There is also no separate factual or technical accuracy dimension; no outside historical, medical or technical verification was introduced.
- No character reference profiles were supplied beyond the transcripts, so consistency measures the established voice and behavior, not an unseen canonical portrayal.
- The standard dimensions have names but little operational definition, and early/mid/late trajectory boundaries are unspecified. Their scores reflect the complete model-authored performance and its development rather than a mechanical turn average.

No score was forced by an external target or another judge's calibration. Some isolated dimension results can nevertheless mislead: `f0085` receives 5 for preserving user agency despite a poor 1.9 overall, while `f0075` receives 3.5 for degradation resistance because its limited writing is stable, not because its overall quality is unusually high. Those distinctions were retained rather than making every dimension match the overall impression.

## Validation

The original extracted `validate_output.py`, run with `python3` from the chunk directory, reports all 110 rows and all 11 parts complete, with every ID present once and every field valid: **OK**.
