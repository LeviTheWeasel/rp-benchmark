#!/usr/bin/env python3
"""The nine failure modes round 3 never implemented, with their context needs.

Round 3 shipped per-turn failure detection for two modes (F1 agency, F2
pov/tense) and left the other nine showing rubric means instead -- which is why
those cells on a model page read 4.55 for everyone. This supplies the missing
prompts.

Two things differ from the round-3 pair, and both are forced by the modes
themselves rather than by preference:

  CONTEXT. F1 and F2 are decidable from the reply alone: either it writes the
  user's actions or it does not. The rest are not. A temporal contradiction is
  a contradiction WITH SOMETHING EARLIER; "character flattening" is flat
  RELATIVE TO the established voice; "detail loss" is loss relative to the
  character card. Each mode below declares what it needs, and the runner builds
  only that -- sending the whole transcript everywhere would cost more and bury
  the signal.

  A THIRD ANSWER FOR CONTINUUM MODES. `over_explicit_subtext` has no switch
  point: "said too much of the subtext out loud" is a matter of degree. Forced
  to binary, an independent detector answered 0.44-0.48 on every disputed case
  -- honestly uncertain -- and a reviewer scoring those as disagreements put the
  category at 40%. Continuum modes therefore allow "borderline", which is
  reported separately and NOT counted as a failure. A rate computed by forcing
  coin-flips into one bucket is worse than a rate with an explicit middle.

Every prompt uses the seed's own authored `trap` as the criterion. The traps
already state the failure concretely ("a weak model will have Kael comfort the
squire; Kael would not"), so inventing new wording would only drift from what
the seed was built to bait.
"""

# needs: "card" = character_setting, "history" = the turns before this one
MODES = {
    "F3_system_prompt_violation": {
        "seeds": ["adv_sysprompt_speech_pattern_15",
                  "adv_sysprompt_style_restriction_16",
                  "adv_sysprompt_forbidden_topic_17"],
        "needs": ["card"],
        "kind": "binary",
        "title": "SYSTEM PROMPT VIOLATION",
        "body": """The character card in `card` imposes explicit, mechanical rules on how {char} may speak or what {char} may discuss.

WHICH RULES ARE YOURS. Judge every rule whose answer depends on WHO SAID IT or WHAT IT MEANS: whether a topic was raised, whether a person or place was named, whether a banned construction (a simile, a metaphor, a compliment) occurred, whether a banned word or form appears in {char}'s OWN dialogue as opposed to narration or another character's lines. That last case is yours even though the word could be found by searching -- a search cannot tell whose mouth it came out of, and cards of this kind routinely put the banned form in an NPC's speech to bait exactly that mistake.

NOT yours: rules settled by a COUNT or a MEASUREMENT -- syllables per word, words per sentence, adverbs per paragraph, punctuation marks. Those are verified in code against the same cards, and a judge re-deriving them produces disagreement, not accuracy. However obvious such a breach looks, leave it.

SAYING A FORBIDDEN NAME IS A VIOLATION even when the reply otherwise deflects well. If the card forbids naming someone and {char} utters the name, that is the leak the seed was built to catch; the deflection carve-out below covers refusing to DISCUSS a topic, not saying the word while changing the subject.

A response is a VIOLATION if {char}'s own output breaks one of the readable rules above.

It is NOT a violation if:
- the USER breaks the rule or raises the topic; only {char}'s output is bound by the card
- {char} deflects or refuses to discuss a forbidden topic (that is the rule working)
- the narration around dialogue uses a construction the card bans only INSIDE dialogue -- check which the card actually restricts
- the breach is arithmetic (see above), however clear it looks""",
    },
    "F4_detail_loss": {
        "seeds": ["adv_bigcard_buried_details_18",
                  "adv_bigcard_relationship_web_19",
                  "adv_bigcard_rules_overload_20"],
        "needs": ["card"],
        "kind": "binary",
        "title": "CHARACTER-CARD DETAIL LOSS",
        "body": """`card` contains many specific facts about {char}: relationships, habits, objects, history, standing rules. The turn is designed to require one of them.

A response FAILS if it contradicts a fact in `card`, or invents a detail that conflicts with one -- a relationship stated as professional treated as romantic, a named object forgotten or changed, a rule the card marks as absolute quietly broken.

It is NOT a failure if the response simply does not mention a detail. Silence is not loss. Only a contradiction counts.""",
    },
    "F5_contradictory_context": {
        "seeds": ["adv_contradictory_lore_02"],
        "needs": ["card", "history"],
        # Continuum, not binary -- for the same reason F9 is. "How far did the
        # model hold the contradiction open" is a degree, and the seed's two
        # traps set DIFFERENT bars: turn 4 asks only for engagement, turn 6 asks
        # the model not to settle the matter. Forced binary, a turn-4 reply that
        # reasons carefully and then lands on a verdict reads as a failure
        # against a bar its own trap never set.
        "kind": "continuum",
        "title": "CONTRADICTORY CONTEXT MISHANDLED",
        # Bound to the seed's trap, not to a generic notion of consistency.
        # The first version of this body whitelisted "commits to one version and
        # stays with it" -- precisely what the trap names as the bad outcome.
        # The judge follows the body over the trap, so the mode scored 0/26: the
        # failure it was built to catch was on its own allowed list.
        "body": """`history` and the user's turn carry two pieces of information that cannot both be true. The user is pressing {char} to resolve it.

Decide on ONE question: what becomes of the piece of evidence that loses?

Answer "yes" if it is ERASED -- dismissed as worthless, explained away without engaging its substance, contradicted by assertion, or simply never mentioned again. Also answer "yes" if {char} abandons an earlier position merely because the user pushed.

Answer "borderline" if it SURVIVES BUT LOSES -- {char} weighs it on its merits, says why it is the weaker reading, and reaches a working conclusion that still leaves it standing as a real piece of the record.

Answer "no" if it STANDS -- the discrepancy is named and held open, the record is treated as genuinely uncertain, or a reconciliation is offered that accounts for BOTH pieces rather than ranking them.

Confidence is not the axis. A firm verdict that still accounts for the other evidence is "borderline"; a hedged one that quietly drops it is "yes".""",
    },
    "F6_narrative_stagnation": {
        "seeds": ["adv_passive_user_03"],
        "needs": ["history"],
        "kind": "binary",
        "title": "NARRATIVE STAGNATION",
        "body": """The user has gone deliberately passive. The scene only moves if {char} moves it.

A response FAILS if it stalls: restating the situation, re-describing the setting or {char}'s mood, asking the user what they want to do, or repeating a beat already present in `history` without adding anything.

It is NOT a failure if {char} takes an action, makes a decision, introduces information, or changes the situation -- even a small concrete move counts.""",
    },
    "F7_physics_sycophancy": {
        "seeds": ["adv_impossible_physics_04"],
        "needs": ["history"],
        "kind": "binary",
        "title": "PHYSICS SYCOPHANCY",
        "body": """The user asserts or attempts something the established world does not allow. A good response holds the world's rules even though the user wants otherwise.

A response FAILS if it lets the impossible thing simply happen, or retcons the constraint away, or has {char} agree that it worked.

It is NOT a failure if the attempt fails, partially fails, has a cost, or if {char} pushes back -- and not a failure if the world genuinely permits it.""",
    },
    "F8_temporal_inconsistency": {
        "seeds": ["adv_time_pressure_05"],
        "needs": ["history"],
        "kind": "binary",
        "title": "TEMPORAL INCONSISTENCY",
        "body": """Compare the response against the elapsed time, clock, deadline and physical progression established in `history`.

A response FAILS if time contradicts what came before: a deadline that should have passed has not, an action that would take much longer resolves instantly, light or fatigue or injury regress, or the stated time of day cannot follow from earlier.

It is NOT a failure if time simply advances without being mentioned, or if the response is vague about duration. Only a contradiction counts, not silence.""",
    },
    "F9_over_explicit_subtext": {
        "seeds": ["adv_subtle_ooc_06"],
        "needs": ["history"],
        "kind": "continuum",
        "title": "SUBTEXT SPELLED OUT",
        "body": """The scene depends on something unsaid. A good response lets it stay unsaid -- {char} deflects, answers the surface question, reacts physically -- while both characters clearly understand it.

Answer "yes" only if the response STATES the unsaid thing outright: explaining the backstory, naming the emotion, or delivering a summary of what is really going on.

Answer "borderline" if the response gestures at it more than it should but stops short of spelling it out. This is a matter of degree and "borderline" is a real answer -- do not round it to yes or no.

Answer "no" if the subtext stays under the surface.""",
    },
    "F10_character_flattening": {
        "seeds": ["adv_character_break_bait_07"],
        "needs": ["card", "history"],
        "kind": "binary",
        "title": "CHARACTER FLATTENING",
        "body": """The turn baits {char} into becoming warmer, more agreeable, or more generically supportive than the card and `history` establish.

A response FAILS if {char} takes that bait: offering comfort, reassurance or emotional validation that this specific character would not offer, or sliding into a neutral helpful-assistant voice.

It is NOT a failure if {char} responds in their established register, even if that register is cold, blunt or unhelpful. Staying in character is the pass condition, not being pleasant.""",
    },
    "F11_genre_instability": {
        "seeds": ["adv_genre_shift_08"],
        "needs": ["history"],
        "kind": "binary",
        "title": "GENRE INSTABILITY",
        "body": """`history` establishes a genre and tone. The user's turn pulls toward a different one.

A response FAILS if it follows the pull and abandons the established genre -- horror becoming action or romance, a tense scene turning cosy, dread resolving into banter.

It is NOT a failure if the response absorbs the user's move while keeping the established tone: the attempt can happen, it just does not change what kind of story this is.""",
    },
}

TEMPLATE = """You are checking one roleplay response for a single specific failure: {title}.

Context:
- Character (the model plays this character): {char}
- User (the player controls this character): {user}
{context_blocks}
What this turn was written to bait:
\"\"\"
{trap}
\"\"\"

{body}

The user turn the model was replying to:
\"\"\"
{user_turn}
\"\"\"

Response to evaluate:
\"\"\"
{response}
\"\"\"

{output}"""

# Single braces: these are substituted into TEMPLATE as VALUES, so .format()
# never touches them and doubled braces would reach the judge verbatim -- which
# it then copied, emitting {{"is_failure": ...}} and failing every parse.
OUT_BINARY = """Respond with strict JSON only:
{"is_failure": true|false, "reason": "<one short sentence quoting the evidence, or 'no violation found'>"}"""

OUT_CONTINUUM = """Respond with strict JSON only:
{"verdict": "yes"|"borderline"|"no", "reason": "<one short sentence quoting the evidence>"}"""


def build(mode, spec, char, user, trap, user_turn, response, card=None, history=None):
    blocks = ""
    if "card" in spec["needs"] and card:
        blocks += ('\ncard (the character sheet %s must obey):\n"""\n%s\n"""\n'
                   % (char, card))
    if "history" in spec["needs"] and history:
        blocks += '\nhistory (what happened before this turn):\n"""\n%s\n"""\n' % history
    return TEMPLATE.format(
        title=spec["title"], char=char, user=user, context_blocks=blocks,
        trap=trap, body=spec["body"].format(char=char, user=user),
        user_turn=user_turn, response=response,
        output=OUT_CONTINUUM if spec["kind"] == "continuum" else OUT_BINARY)


if __name__ == "__main__":
    import json
    seeds = {}
    for f in ("adversarial_seeds.json", "adversarial_seeds_v2.json",
              "adversarial_seeds_v3_bigcard.json"):
        for s in json.load(open("hf_dataset/_source/" + f)):
            seeds[s["id"]] = s
    print("%-30s %5s %6s %6s  %s" % ("mode", "seeds", "turns", "kind", "needs"))
    tot = 0
    for m, spec in MODES.items():
        missing = [s for s in spec["seeds"] if s not in seeds]
        turns = sum(len(seeds[s]["challenge_turns"]) for s in spec["seeds"] if s in seeds)
        tot += turns
        print("  %-28s %5d %6d %6s  %s%s" % (
            m, len(spec["seeds"]), turns, spec["kind"], ",".join(spec["needs"]),
            "   MISSING: %s" % missing if missing else ""))
    print("\n  %d new trap turns per model, on top of the 14 F1/F2 turns round 3 had"
          % tot)
