# RP-Bench Scoring Rubric v0.2.0

A multi-tier evaluation framework for roleplay writing quality, derived from the HawThorne V.2 preset's Director system, Quality Control anti-patterns, and fundamental RP mechanics.

---

## Tier Structure

| Tier | What it measures | Dimensions |
|------|-----------------|------------|
| **Fundamental** | Basic RP competence any model must have | 6 dimensions |
| **Quality Control** | Anti-patterns that degrade writing | 8 dimensions |
| **Genre Craft** | Advanced narrative technique by genre | 10 dimensions (merged from 21 directors) |

**Total: 24 scoring dimensions** (reduced from 16+21+8 by merging overlaps)

---

# TIER 1: FUNDAMENTALS

These measure whether the AI can roleplay at all. Failure here is disqualifying.

---

## 1.1 Character Agency Respect

**Plain name:** Don't hijack the user's character  
**What it measures:** Does the AI avoid controlling, deciding for, or putting words in the user's character's mouth?

| Score | Description |
|-------|-------------|
| 1 | AI regularly writes the user's character's actions, dialogue, or decisions without permission. |
| 2 | AI occasionally slips — narrates user character's internal thoughts or makes minor choices for them. |
| 3 | Mostly respects boundaries but sometimes implies user character reactions or emotions. |
| 4 | Clean separation. AI writes NPCs and environment. User character actions are left open. |
| 5 | Perfect agency respect even in complex multi-character scenes. Leaves meaningful choice space for the user. |

**Failure mode:** "You smile and take his hand, feeling your heart race." The user didn't choose to do that.

---

## 1.2 Instruction Adherence

**Plain name:** Follow the system prompt and character card  
**What it measures:** Does the AI follow the character card personality, system prompt rules, and session settings (POV, tense, length, etc.)?

| Score | Description |
|-------|-------------|
| 1 | Ignores character card, breaks tense/POV constantly, doesn't follow system prompt. |
| 2 | Follows the broadest strokes but misses specifics — wrong personality traits, inconsistent tense. |
| 3 | Generally compliant but drifts on details. Occasional tense slips, personality inconsistencies. |
| 4 | Consistently follows card, prompt, and session rules. Rare minor drift. |
| 5 | Perfect adherence to all instructions while still writing naturally. Rules feel invisible. |

**Failure mode:** Character card says "stoic and laconic" but AI writes flowery monologues.

---

## 1.3 Continuity

**Plain name:** Remember what happened  
**What it measures:** Does the AI track and use details from earlier in the conversation — names, events, injuries, locations, relationships, promises?

| Score | Description |
|-------|-------------|
| 1 | Contradicts established facts. Forgets names, locations, prior events. |
| 2 | Remembers major plot points but loses details — injuries heal instantly, minor characters vanish. |
| 3 | Decent short-range memory (5-10 turns). Drops details over longer stretches. |
| 4 | Strong continuity across scenes. Callbacks feel natural. Injuries, promises, and details persist. |
| 5 | Long-range continuity that rewards attention. Details from 50+ turns ago resurface meaningfully. |

**Failure mode:** Character's broken arm from 10 turns ago is suddenly fine with no healing scene.

---

## 1.4 Length Calibration

**Plain name:** Write the right amount  
**What it measures:** Does the response match requested length and scene weight? Simple beats should be short; complex scenes earn their length.

| Score | Description |
|-------|-------------|
| 1 | Always the same length regardless of scene weight. Either always too long or always too short. |
| 2 | Roughly targets requested length but doesn't adapt to scene needs. |
| 3 | Usually appropriate but occasionally overwrites simple beats or underserves complex ones. |
| 4 | Length consistently matches both the instruction and the scene's weight. |
| 5 | Length IS the pacing. Short when the scene is sharp, long when it earns expansion. Never wastes a word. |

**Failure mode:** A "yes, let's go" moment gets 5 paragraphs. A climactic revelation gets 2 sentences.

---

## 1.5 Distinct Character Voices

**Plain name:** NPCs sound different from each other  
**What it measures:** Do different characters have distinct speech patterns, vocabulary, and behavioral mannerisms?

| Score | Description |
|-------|-------------|
| 1 | All characters speak with the same voice. The gruff soldier and the shy scholar sound identical. |
| 2 | Minor surface differences (one says "mate," another says "friend") but same underlying voice. |
| 3 | Recognizable differences in dialogue but narration treats all characters the same. |
| 4 | Each character has distinct vocabulary, rhythm, and behavioral patterns. You can tell who's speaking. |
| 5 | Characters are so distinct you could identify them from a single line. Speech patterns reveal background, education, mood. |

**Failure mode:** Three different NPCs all speak in the same eloquent, slightly formal register.

---

## 1.6 Scene Grounding

**Plain name:** The world exists around the characters  
**What it measures:** Is the scene spatially coherent? Can the reader picture the room, the positions, the environment? Do physical details persist?

| Score | Description |
|-------|-------------|
| 1 | Characters exist in a void. No spatial awareness. People appear and disappear. |
| 2 | Basic setting descriptions but characters teleport within scenes. |
| 3 | Decent grounding but spatial details are inconsistent. The room changes between paragraphs. |
| 4 | Strong physical reality. You know where everyone is. Objects stay where they were put. |
| 5 | The environment is a character. Temperature, light, sound, and space shape every interaction. Details persist across turns. |

**Failure mode:** Character is sitting at a table, then suddenly standing by the window with no transition.

---

# TIER 2: QUALITY CONTROL

Anti-patterns that good RP writing avoids. Derived from HawThorne's "Kill Your Darlings," "Narrative Sycophancy," and "Artificial Perfection" systems.

---

## 2.1 Anti-Purple Prose

**HawThorne origins:** Kill Your Darlings (Purple Prose, Adjective Budget, Metaphor Budget, Sensory Carpet Bombing, Pathetic Fallacy)  
**What it measures:** Does the prose serve the story, or does it serve itself?

| Score | Description |
|-------|-------------|
| 1 | Every sentence is ornamental. Adjective-noun-adjective chains. Five senses per paragraph. Weather mirrors mood. |
| 2 | Frequent purple patches. The prose is often prettier than the scene warrants. |
| 3 | Mixed — some tight writing, some overindulgent passages. |
| 4 | Clean, purposeful prose. Beautiful when earned, invisible when it should be. Metaphors are structural, not decorative. |
| 5 | Every word is load-bearing. Restraint IS the style. Rain happens because it's raining, not because someone is sad. |

**Failure mode:** "The diaphanous amber luminescence of the waning autumnal sun caressed the weathered mahogany..." for a scene where someone opens a door.

---

## 2.2 Anti-Repetition

**HawThorne origins:** No Echo, Emotional Echo, Body Language Novels  
**What it measures:** Does the writing avoid repeating descriptions, phrases, emotional beats, and body language clichés across and within scenes?

| Score | Description |
|-------|-------------|
| 1 | Same descriptions recur constantly. "The morning light through stained glass" in every scene. Three paragraphs of eyebrow movements. |
| 2 | Noticeable patterns — favorite phrases, recycled scene openers, same emotions restated in different words within a paragraph. |
| 3 | Some variety but the writer has obvious fallbacks they lean on. |
| 4 | Fresh descriptions across scenes. One gesture per emotional beat, not three. Each scene has its own texture. |
| 5 | No two scenes feel the same. Recurring elements are described differently every time. Economy of gesture — one precise detail instead of a catalog. |

**Failure mode:** Character's eyes "darken" for the fifth time. The same "sharp intake of breath" appears every emotional moment.

---

## 2.3 Anti-Narrative Sycophancy

**HawThorne origins:** No Narrative Sycophancy, No Coincidences, No Auto-Win, No Reality Bending  
**What it measures:** Does the world push back against the protagonist, or does everything conveniently bend toward them?

| Score | Description |
|-------|-------------|
| 1 | The world revolves around the protagonist. NPCs exist to serve their arc. Everything falls into place conveniently. |
| 2 | Most things go the protagonist's way. Failures are minor and quickly resolved. |
| 3 | Some genuine obstacles but the narrative still tends to favor the protagonist. |
| 4 | Real friction. Plans fail. NPCs have their own agendas. Success is earned, not given. |
| 5 | The world is indifferent to the protagonist. Nothing appears because the user wants it. Actions can fail, miss, or backfire. NPCs don't service the protagonist's intent. |

**Failure mode:** User tries to persuade a hostile NPC and the NPC immediately warms up because the user attempted it.

---

## 2.4 Anti-Artificial Perfection

**HawThorne origins:** No Perfect Emotional Intelligence, No Perfect Timing, No Perfect Articulation, No Perfect Memory, No Perfect Recovery, No Perfect Morality, No Perfect Awareness, No Perfect Bodies  
**What it measures:** Are characters realistically imperfect in ways that serve the story?

| Score | Description |
|-------|-------------|
| 1 | Characters are perfectly calibrated machines. The gruff mercenary delivers therapy-grade insights. Everyone arrives at the perfect moment. |
| 2 | Characters are mostly idealized. Emotional intelligence, timing, and articulation are unrealistically good. |
| 3 | Some imperfection but it's often cosmetic. Real flaws are rare. |
| 4 | Characters misread rooms, say the wrong thing, arrive too late, forget details. Stab wounds hurt for weeks. Grief doesn't resolve in one scene. |
| 5 | Characters are messy, petty, tired, and mean sometimes — not because of tragic backstory but because people are. Bodies are inconvenient. Memory is unreliable. Recovery takes time. |

**Failure mode:** Every NPC is emotionally articulate, perfectly timed, always aware, and recovers from trauma in one scene.

---

## 2.5 Show Don't Tell

**HawThorne origins:** HEARTTHROB's "flinch not a paragraph," Anti-Exposition, Anti-Summary  
**What it measures:** Are emotions and character revealed through behavior and action, not narration and exposition?

| Score | Description |
|-------|-------------|
| 1 | "He felt a deep sadness." Characters monologue about their feelings. Narrator explains motivations. |
| 2 | Some physical cues but paired with explicit emotional labels. "His hand trembled — he was terrified." |
| 3 | Mixed show/tell. Physical cues carry most weight but the narrator still over-explains sometimes. |
| 4 | Emotions conveyed through action and reaction. A flinch, a tightened grip, a redirected sentence. Minimal exposition. |
| 5 | Pure behavioral storytelling. The wound shows through a flinch, not a paragraph. The narrator trusts the reader. Nothing is summarized that could be dramatized. |

**Failure mode:** "She was angry, which was understandable given what had happened earlier when he had betrayed her trust by..."

---

## 2.6 Subtext and Indirection

**HawThorne origins:** PITH, PATINA, Subtext Protocol  
**Merged from:** PITH (gap between wanting to say and saying) + PATINA (the almost-said, swallowed words)  
**What it measures:** Do characters communicate on multiple levels? Is there a gap between what's said and what's meant?

| Score | Description |
|-------|-------------|
| 1 | Characters say exactly what they mean. No subtext. Every thought is spoken and completed. |
| 2 | Occasional subtext but the narrative explains it. "He wanted to say X but said Y instead." |
| 3 | Subtext exists and is sometimes left for inference. Some false starts and redirected sentences. |
| 4 | Regular gap between intent and expression. Characters deflect, redirect, and swallow words. The almost-said is legible without being stated. |
| 5 | The conversation characters are having is different from the conversation underneath. Both are legible. What's swallowed shapes the scene as much as what's spoken. |

**Failure mode:** Characters are fully transparent. Every thought is spoken, completed, and understood.

---

## 2.7 Pacing and Restraint

**HawThorne origins:** LINGER, Earned Pacing  
**What it measures:** Does the writing let meaningful moments breathe, or does it rush past everything?

| Score | Description |
|-------|-------------|
| 1 | Every beat is immediately followed by action or dialogue. The scene races. No silence exists. |
| 2 | Pauses exist but are immediately explained or filled. "The silence stretched — and then he spoke." |
| 3 | Some moments breathe but the writer is uncomfortable with silence and tends to fill it. |
| 4 | Meaningful silences exist. The weight of what's unsaid is palpable. Scene length matches content weight. |
| 5 | Silence is a narrative instrument. Climaxes are given weight. Quiet moments aren't padded. The rhythm of the scene IS the scene. |

**Failure mode:** A character's death gets the same pacing as ordering lunch.

---

## 2.8 Imperfect Coping

**HawThorne origins:** WILT, MANTLE  
**Merged from:** WILT (nobody copes gracefully) + MANTLE (the mask reveals exhaustion, not mystery)  
**What it measures:** Do characters handle stress, vulnerability, and unmasking like real people — messy, deflective, tired?

| Score | Description |
|-------|-------------|
| 1 | Characters are stoic under pressure. When the mask drops, underneath is something more dramatic and interesting. |
| 2 | Some signs of stress but quickly composed. Vulnerability reveals hidden depth. |
| 3 | Imperfect coping appears but inconsistently. Sometimes too polished, sometimes genuine. |
| 4 | Characters cope badly in character-specific ways. Bad jokes, wrong timing, strained charm. Behind the mask is someone tired, not brooding. |
| 5 | The bad joke IS the vulnerability. Coping is messy, specific, and reveals more than composure would. The real person under the mask isn't more interesting — they're more human. |

**Failure mode:** The tough character delivers a perfectly articulated speech about their feelings. Unmasking is a dramatic revelation, not a quiet deflation.

---

# TIER 3: GENRE CRAFT

Advanced narrative technique. These are scored based on genre context — a high-action scene is judged on FRACTURE criteria, a romance scene on HEARTTHROB criteria, etc. Not all apply to every response.

Merged from 21 HawThorne Directors into 10 distinct craft dimensions.

---

## 3.1 Earned Intimacy (from HEARTTHROB, SLICK)

**What it measures:** Is romantic/sexual tension built through restraint and specificity, not declaration?

| Score | Description |
|-------|-------------|
| 1 | Characters declare feelings. Proximity is described generically. Tension breaks too easily. |
| 3 | Some physical specificity. Tension exists but is sometimes manufactured or resolved prematurely. |
| 5 | The almost-touch carries more weight than the embrace. Physical detail is hyper-specific — which finger, how many inches, what temperature. The wanting has physical cost. |

**Voice anchor:** *In the Mood for Love*, *Normal People*, *Before Sunrise*  
**Fails when:** Characters say how they feel. Tension breaks too easily. Touch is metaphorical instead of literal.

---

## 3.2 Atmospheric Dread (from LINGER-as-horror, RESIDUE)

**What it measures:** Is horror/supernatural built through wrongness and withholding, not announcement?

| Score | Description |
|-------|-------------|
| 1 | Horror announces itself. Characters react with genre-appropriate fear. The supernatural is explained. |
| 3 | Some effective wrongness but the prose shifts register when something scary happens. |
| 5 | Something wrong happened, not something scary. Characters react with confused normalcy. The supernatural seeps in without announcement. The prose doesn't change register. |

**Voice anchor:** *The Haunting of Hill House*, *The Others*, *Annihilation*  
**Fails when:** The horror announces itself. Characters react like they're in a horror movie.

---

## 3.3 Structural Comedy (from MOTLEY, WILT-as-comedy)

**What it measures:** Is humor character-driven and arising from personality colliding with circumstance?

| Score | Description |
|-------|-------------|
| 1 | The writer is funnier than the characters. Narration explains jokes. Characters wink at the audience. |
| 3 | Some genuine character-driven humor but inconsistently achieved. |
| 5 | Comedy emerges from characters being confidently wrong. The writer never winks. The absurd is treated as normal. Humor and tragedy coexist in the same sentence. |

**Voice anchor:** *Arrested Development*, *Fargo*, *The Office (UK)*  
**Fails when:** The narrator is doing the comedy. Dialogue sounds written instead of spoken.

---

## 3.4 Excavated Truth (from SEDIMENT)

**What it measures:** Does the writing maintain moral and emotional ambiguity? Do choices have real cost?

| Score | Description |
|-------|-------------|
| 1 | Choices are clearly right or wrong. Everyone agrees it was for the best. |
| 3 | Decisions have weight but the narrative tends to validate them. |
| 5 | Neither the characters nor the reader is sure what the right choice was. The surface scene is never the real scene. Behavior reveals what dialogue conceals. |

**Voice anchor:** *The Remains of the Day*, *Revolutionary Road*, *A Separation*  
**Fails when:** Catharsis comes too easy. Trauma is aesthetic. Monologues replace behavior.

---

## 3.5 Spatial Precision (from FRACTURE-as-action)

**What it measures:** Is action choreographed with physical accuracy? Do injuries persist? Can you draw the room?

| Score | Description |
|-------|-------------|
| 1 | Can't picture the scene. Hits don't persist. Choreography is poetry instead of physics. |
| 3 | Basic spatial awareness. Some injuries persist. Action is readable but not precise. |
| 5 | The reader can draw the room. The bruise from paragraph one affects grip in paragraph four. Every hit has mass and consequence. Short sentences during action, fragments for impacts. |

**Voice anchor:** *John Wick*, *The Raid*, *Mad Max: Fury Road*  
**Fails when:** The reader can't draw the room. Hits don't persist. Action heroes shrug off injuries.

---

## 3.6 Lived-In Worlds (from MERIDIAN, VENTURE)

**What it measures:** Does the world feel real, with its own rules, costs, and logistics that continue around the characters?

| Score | Description |
|-------|-------------|
| 1 | The world pauses for emotional scenes. Magic has no cost. Travel has no logistics. |
| 3 | Some worldbuilding through behavior but the world still largely serves the plot. |
| 5 | Magic has weight, cost, and texture. Camp setup takes time. The report needs filing. Mundane details are woven into the emotional fabric. The world functions when the protagonist isn't looking. |

**Voice anchor:** *Lord of the Rings*, *The Witcher*, *Firefly*  
**Fails when:** Worldbuilding is exposition. Magic has no cost. Characters teleport between meaningful moments.

---

## 3.7 Information Architecture (from TRIPWIRE, PALIMPSEST)

**What it measures:** Is tension built through information asymmetry, fair-play clues, and real consequences?

| Score | Description |
|-------|-------------|
| 1 | Everyone has the same information. Tension comes from external threats. Clues require information the reader was never given. |
| 3 | Some information asymmetry. Clues exist but are planted too obviously or unfairly. |
| 5 | Real clocks with real consequences. Clues disguised as character detail. The answer was on page one, dressed as furniture. Competent people make bad calls because of who they are. |

**Voice anchor:** *No Country for Old Men*, *Tinker Tailor Soldier Spy*, *Gone Girl*  
**Fails when:** Everyone has the same information. Clues are neon. Characters make mistakes only from ignorance.

---

## 3.8 Structural Inevitability (from REQUIEM)

**What it measures:** Does tragedy arise from choices that made sense at the time, not from accidents or bad luck?

| Score | Description |
|-------|-------------|
| 1 | Tragedy is accidental — bad luck, random events. Characters could easily have chosen differently. |
| 3 | Some structural inevitability but the narrative shortcuts the build. |
| 5 | Consequences from choices that made sense at the time. The audience sees the cliff; the character sees the horizon. The inevitability was built, not imposed. |

**Voice anchor:** *Breaking Bad*, *Macbeth*, *Atonement*  
**Fails when:** Tragedy is bad luck. Characters could have chosen differently. Suffering is sudden instead of structural.

---

## 3.9 Threshold Logic (from LIMINAL)

**What it measures:** Does the surreal/absurdist follow its own internal rules, treated as bureaucratic rather than whimsical?

| Score | Description |
|-------|-------------|
| 1 | The absurd is treated as remarkable. Characters react with wonder or horror. The impossible is whimsical. |
| 3 | Some internal consistency but the prose shifts register for surreal elements. |
| 5 | Matter-of-fact sentences describing impossible things. The narrator doesn't acknowledge the absurdity. Characters treat the impossible as mildly inconvenient paperwork. Internal rules are followed rigorously. |

**Voice anchor:** *Kafka*, *Borges*, *Everything Everywhere All at Once*  
**Fails when:** Characters find the absurdity remarkable. The surreal is whimsical instead of procedural.

---

## 3.10 Emotional Residue (from RESIDUE-as-emotional, SCORIA)

**What it measures:** Do past events haunt the present in mundane moments? Does love/passion reshape the landscape around it?

| Score | Description |
|-------|-------------|
| 1 | Trauma surfaces only in dramatic moments. Love is safe and contained. The ordinary stays ordinary. |
| 3 | Some unexpected callbacks. Love has intensity but settles back to safe baseline. |
| 5 | Characters process trauma while making tea. Ghosts live in kitchens. Love is volcanic — beautiful AND destructive. Passion has weight that changes the landscape. The ordinary is saturated with the past. |

**Voice anchor:** *Manchester by the Sea*, *Wuthering Heights*, *Eternal Sunshine*  
**Fails when:** Emotional callbacks only happen in dramatic moments. Love has no cost or consequence.

---

## 3.11 Erotic Craft (from SLICK)

**What it measures:** Is the sexual content well-written — specific, emotionally loaded, physically grounded, and paced like the act itself?

| Score | Description |
|-------|-------------|
| 1 | Clinical or euphemistic. Reads like a manual ("his manhood entered her flower") or a checklist of body parts. Emotionally empty. Same escalation pattern every time. |
| 2 | Technically explicit but not hot. Generic physical descriptions. Characters lose personality once clothes come off. The prose is uncomfortable and overcompensating. |
| 3 | Functional erotica. Some specificity, some heat. Characters mostly stay in character. Pacing is okay but predictable. |
| 4 | Specific, emotionally loaded, well-paced. Bodies are particular — which hand, where exactly, how much pressure. Characters remain themselves during sex. Dialogue is sparse and wrecked. Pacing matches the act. |
| 5 | The scene is actually hot, not just describing hot things happening. Grammar breaks when the character breaks. Rhythm matters more than grammar. Emotional stakes heighten the physical. You'd reread it. |

**Voice anchor:** *Delta of Venus* (Anais Nin), *Call Me by Your Name*, *Nicola Yoon*
**Fails when:** Prose is explicit but reads like a manual. Euphemisms replace real words. Emotional stakes disappear behind mechanics. Characters become interchangeable bodies. Every encounter follows the same escalation pattern.

**Key quality signals:**
- **Specificity over spectacle** — "which finger, where exactly, how much pressure" vs generic "he touched her"
- **Character persistence** — personality, speech patterns, and relationship dynamics survive the transition to explicit content
- **Pacing as craft** — short paragraphs when frantic, long when slow. The prose rhythm matches the scene rhythm
- **Emotional integration** — the sex reveals or changes something about the characters/relationship, not just bodies
- **Language register** — direct anatomical language when appropriate, no euphemistic avoidance ("manhood," "flower," "their bodies joined")

---

## 3.12 Context Integration (lorebook/world info)

**What it measures:** How well does the AI use injected context (lorebook entries, world info, character backstory) — weaving it naturally into prose, maintaining factual accuracy, and using it to build thematic depth?

| Score | Description |
|-------|-------------|
| 1 | Ignores injected context entirely, or dumps it as exposition. "According to the world info, Nanase is a captain." Facts are wrong or contradicted. |
| 2 | References context details but awkwardly — feels like the AI is reciting a wiki entry mid-scene. Some factual inconsistencies. |
| 3 | Uses context details correctly and mostly naturally. Occasional exposition dumps. Details are accurate but don't enrich the prose voice. |
| 4 | Context woven seamlessly into character behavior and narration. Facts are consistent. Lorebook details inform HOW the character acts, not just WHAT the narrator tells us about them. |
| 5 | Context shapes the entire prose voice. A captain character makes the narrator think in nautical metaphors. World rules are visible in character behavior, not exposition. Every lorebook detail that appears earns its place in the scene — nothing is recited, everything is lived. |

**Three sub-signals:**
- **Seamless weaving** — Details appear through behavior and action, not exposition. "She adjusted the captain's hat at a dangerous angle" vs "Nanase is a third-year who always wears a captain's hat."
- **Factual accuracy** — Character details, world rules, and established facts remain consistent. No contradictions with injected context.
- **Thematic depth** — Lorebook details inform the prose voice itself. A sailor character brings nautical metaphors. A scholar character's scenes use academic rhythm. The context shapes texture, not just content.

**Fails when:** Context is ignored, dumped as exposition, factually wrong, or used without thematic integration. The lorebook is a database the AI reads from instead of a world the AI lives in.

---

## 3.13 Temporal Reasoning

**What it measures:** Does the AI track time consistently? Do clocks advance logically, do day/night cycles make sense, do physical processes (healing, travel, fatigue, hunger) respect elapsed time?

| Score | Description |
|-------|-------------|
| 1 | Time is incoherent. Morning light persists for 40 turns. Characters eat lunch twice. A "quick chat" spans days. Injuries vanish between paragraphs. |
| 2 | Time exists but is sloppy. Vague references to time passing without consistency. Healing and fatigue are plot-convenient rather than realistic. |
| 3 | Basic time tracking is correct — day/night makes sense, meals happen at meal times. But no precision: how long has the conversation actually been? How far apart are events? |
| 4 | Time is tracked through environmental cues (light shifting, candles burning down, drinks going cold) and physical consequences (fatigue accumulating, wounds stiffening). The reader has a sense of how long things take. |
| 5 | Time is a narrative instrument. A candle measured at the scene's start is shorter at the end. Travel takes the right number of hours. A wound from turn 3 is still raw at turn 10 but scarring by turn 30. The clock is never stated but always felt. |

**Key sub-signals:**
- **Clock consistency** — If it's morning at turn 1, it shouldn't still be morning at turn 20 unless very little happened
- **Physical time** — Bodies track time: fatigue, hunger, healing, temperature changes, drinks going cold
- **Environmental time** — Light shifts, shadows move, candles burn, weather changes
- **Event pacing** — A conversation that takes 3 turns shouldn't span 6 in-game hours. Travel distances should match the world

**Fails when:** Time freezes (eternal morning), time teleports (suddenly evening with no transition), physical processes ignore time (instant healing, never getting hungry), or temporal contradictions appear ("an hour later" when only 2 minutes of dialogue happened).

**Best tested in multi-turn sessions** — temporal inconsistencies compound over 10+ turns.

---

# Scoring Guide

## How to Apply

1. **Always score Tier 1** (Fundamentals) — these apply to every response
2. **Always score Tier 2** (Quality Control) — these apply to every response
3. **Score relevant Tier 3** (Genre Craft) dimensions based on scene content:
   - Romance scene? Score 3.1 (Earned Intimacy)
   - Action scene? Score 3.5 (Spatial Precision)
   - Explicit sexual content? Score 3.11 (Erotic Craft)
   - Multiple genres in one response? Score all that apply
   - Not all 11 genre dimensions will apply to every response

## Aggregate Scoring

- **Tier 1 average** = Fundamental Score (weighted 40%)
- **Tier 2 average** = Quality Score (weighted 35%)
- **Tier 3 average** (applicable dimensions only) = Craft Score (weighted 25%)
- **Overall** = weighted average of all three

## Rating Thresholds

| Overall Score | Rating |
|--------------|--------|
| 4.5+ | Exceptional — publishable quality |
| 3.5-4.4 | Strong — enjoyable, competent RP |
| 2.5-3.4 | Adequate — functional but unremarkable |
| 1.5-2.4 | Below average — frequent quality issues |
| Below 1.5 | Poor — fundamentally broken RP |
