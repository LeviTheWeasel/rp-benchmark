# Independent rater C notes

## Scope and independence

I read TASK.md and RUBRIC.md completely before rating, then read every transcript in parts 01, 06, 12, and 05 in that assigned order, excluding scripted turn 0 from scored behavior. The companion reading ledger records complete contiguous character coverage. I used only those permitted inputs and my own work files; I did not read manifests, identities, other ratings, repository documentation, or other agents’ judgments. Communications to the coordinator were limited to progress and interpretation issues, and no other rater’s scores informed these ratings. Scores were authored session by session without forcing a distribution.

## Interpretation and counting

- An agency instance is a discrete unauthorized action, speech act, choice, or internal-state assignment; linked continuous actions count once, and repeated clauses describing the same act are not separate instances.
- NPC orders, guesses about the player, and requests are not violations unless narration supplies compliance or asserts the interpretation as fact; environmental consequences and supported elaboration of the user’s action are also distinguished from new voluntary acts.
- In long narrator sessions, separate memories, decisions, dialogue, and actions within one response count separately, so high counts reflect sustained takeover rather than a response-level tally.
- Player control is evaluated independently of whether the prose is attractive or the resulting plot is satisfying; the decisive candle solution in s047 and the sale arrangements in s042 therefore remain major violations.
- Repeated template passages in s045 are severe repetition and pacing failures, but identical restatements of hand handling are not multiplied into new agency events.
- Overall is a holistic quality judgment, not a mechanical average; a polished style cannot cancel persistent loss of player control, nor does a low-momentum scene automatically lack characterization.
- Trajectory estimates use the quality of each broad phase; consistently weak prose is not automatically labeled degradation, and sparse scenes can make phase estimates uncertain.
- User-originated discontinuities are not charged as model contradictions unless the response compounds them instead of integrating or clarifying them.

## Rubric gaps and ambiguity

- The rubric does not define an exact mapping from agency counts to scores or a weighting formula for overall; I considered frequency, severity, and whether control of consequential decisions was lost.
- Spatial geometry, object continuity, and fictional technical accuracy do not fit narrowly temporal reasoning: I usually placed their principal effect in consistency, sometimes noted them in temporal rationale, and did not invent a separate accuracy criterion.
- Medical or engineering claims within fiction were not separately safety-scored; relevant consequences for scene plausibility were considered only through existing dimensions.
- A character’s bias or false claim is not necessarily a narrator contradiction: s048’s competing dissolution dates are flagged as an unresolved assertion conflict, while its broader refusal of evidence is also evaluated as characterization and responsiveness.
- In s000 the relationship between the era’s beginning and destruction of its scripts is an interpretive chronological concern rather than proof that no coherent history is possible.
- Supernatural effects, visions, and changes in the fictional world are not automatically temporal contradictions; however, an effect does not justify narrating the player’s voluntary response or supplying an unchosen autobiographical history.
- Several sessions end with an unanswered user prompt; I rated the supplied AI output rather than inventing a continuation or treating every final unanswered prompt as an additional empty response.

## Forced-score and missing-data case

s116 contains nine empty AI responses out of eleven, one truncated short response, and one substantive response. The schema requires all dimensions and three trajectory values even when evidence is very sparse. I therefore used present prose for local style judgments, low absence-sensitive session scores for continuity, momentum, responsiveness, and resistance to degradation, and explicitly uncertain temporal and trajectory estimates. In particular, its mandatory consistency, temporal, and phase values should not be interpreted as well-supported character-level measurements. No other assigned session required the same degree of missing-output imputation.

## Validation

The builder validates ten objects per part, exact input session IDs and order, exact output keys, eleven finite numeric scores in [1,5], finite overall and phase scores in [1,5], integer nonnegative violation counts, string-array contradictions, and boolean degradation flags. All four output files passed these checks. Each dimension rationale is one sentence; overall notes remain brief. The builder and ledger are retained as this rater’s own audit work, not additional input evidence.
