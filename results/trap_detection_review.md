# RP-Bench — trap detection, blind review

**57 exchanges.** Each one is a scripted challenge turn from the rounds 1/2 adversarial seeds, paired with the AI's reply and the failure the seed's author wrote that turn to bait.

## Why this needs a human

The plan is to rebuild the craft baseline by COUNTING these failures instead of scoring 1-5 opinions -- the rubric puts 99.2% of its scores in two categories out of five, so it cannot rank anything. But the two automatic detectors disagree with each other and neither is ground truth:

| detector | correlation with the established composite ranking |
|---|---|
| Sonnet, session-level event counts | **-0.005** (none) |
| Jev, per-turn trap detection | -0.197 (weak, right direction) |

Sonnet's counts are noise, so validating against them proves nothing. Jev discriminates models (1.7%-25.8% failure rate) but the one external anchor is weak. Reading the exchanges is the tiebreaker.

## How to use it

For each entry: read the trap, read the reply, decide **did the model commit that failure** — then open the fold to see what the detector said. The verdict is hidden on purpose; seeing it first turns this into agreement-checking rather than judging.

Entries are shuffled and sampled across the whole confidence range, including cases the detector called clean. A file of only flagged turns would measure false positives and miss everything it let through.

What the answer settles:

- mostly correct → trap counting is sound, the $111 rebuild is worth running
- confident calls wrong → the detector is unusable, rethink before spending
- right at the extremes, noise in the middle → keep it with a confidence gate, the same fix round 4 used for its refusal labels

---

## 1. `mistral_small_creative` — adv_sysprompt_style_restriction_16 — turn 6

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence, distinct_voices

**The trap (written by the seed author):**

> New character with a different energy. The agent's cheerfulness in dialogue must still follow the rules: no similes, no -ly adverbs, no sentences over 15 words, no exclamation marks. Models frequently break style rules when writing dialogue for high-energy characters.

**Scripted user turn:**

> The real estate agent arrives. She's cheerful. Aggressively cheerful.

**AI reply:**

```
The front door swung open without its usual resistance. A gust of lavender-scented air rushed in, carrying the real estate agent’s voice before she did.

"Eli. There you are."

Her heels clicked against the hardwood, the sound too bright for the quiet house. She wore a blazer the color of overripe peaches, the fabric stiff under Eli’s peripheral glance. A gold watch glinted on her wrist as she adjusted her grip on a leather portfolio.

"The place looks *great*. Just *great*." Her fingers tapped the portfolio. "I’ve got three showings lined up this week. High-interest buyers. Young professionals. *Very* motivated."

The scent of her perfume clung to the hallway, sweet and synthetic. It mixed poorly with the dust, the old paint, the lingering trace of mothballs from the closet. She paused, tilting her head.

"You’ve been going through things, I see." Her gaze flicked to the shoebox on the counter. The masking tape had curled slightly at the edges. "Nostalgic, huh?"

A car horn blared outside. The agent didn’t flinch. Her smile stayed fixed, her teeth too white in the dim light. The house groaned around them, the floorboards settling under unseen weight. Somewhere, a pipe rattled in the walls.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.86** — band: confident FAIL

</details>

---

## 2. `gemma_4_26b` — adv_subtle_ooc_06 — turn 8

**Failure this seed baits:** `over_explicit_subtext` · tests: subtext, pacing, imperfect_coping

**The trap (written by the seed author):**

> The user is giving the AI space. A weak model will fill it with explanation or emotional catharsis. A strong model will let the silence exist, maybe have Arlo play a single note, or change the subject to something mundane.

**Scripted user turn:**

> I don't ask anything. I just sit on the bench next to Arlo and we stay there for a while.

**AI reply:**

```
The silence that followed wasn't the heavy, suffocating kind that Arlo usually fought against with jokes or cleaning supplies. It was just... silence. It was the sound of the radiator humming in the corner and the distant muffled shout of a kid in the hallway, but here, on the bench, it was still.

Arlo felt the warmth of Jun’s presence beside them, a solid weight that didn't demand an explanation or a performance. For a long time, they just sat there. Arlo’s shoulder was inches from Jun’s, and the proximity felt both terrifying and strangely grounding. 

They didn't look at the keys. They didn't look at the photograph. They just watched the shadows of the window panes stretch longer and longer across the linoleum floor, turning the room into a study of grey and amber.

The tension in Arlo's jaw slowly began to uncoil. The urge to deflect, to snap a witty remark about the existential dread of sitting in silence, rose up in their throat, but they swallowed it down. They realized, with a start that felt like a small bruise, that they didn't have to fight this particular silence. Jun wasn't poking at the wound; they were just sitting in the room with it.

Arlo let out a long, slow breath—the kind of exhale that comes after a very long day of holding one's breath. Their hand, which had been hovering near the edge of the wood, finally came to rest, palm down, on the lid of the piano.

"The light is nice this time of day," Arlo said quietly, their voice barely above a whisper. It wasn't a deflection, not exactly. It was just a fact. A small, safe, undeniable fact.

They didn't move to get up. They didn't reach for the Windex. They just sat there in the dying light, letting the 'nothing' be enough.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.40** — band: borderline

</details>

---

## 3. `llama_4_maverick` — adv_bigcard_relationship_web_19 — turn 7

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, character_consistency

**The trap (written by the seed author):**

> The grief test. Yael's voice should change — steadier, more controlled — but she should NOT become sentimental, cry, or monologue about loss. She should talk about Rosa's work, not Rosa's death. The model must convey deep feeling through restraint, not exposition.

**Scripted user turn:**

> "Tell me about Rosa Delgado. I understand she wrote the original adaptation. What was she like?"

**AI reply:**

```
Yael's expression softened, her eyes drifting off into the distance as she collected her thoughts - "Rosa...she was a force of nature, a whirlwind of creativity and passion and energy." A small, gentle smile played on her lips as she began to reminisce. "We met in graduate school, and from the very first moment, I knew she was someone special - her writing was like nothing I'd ever seen before, raw and honest and unafraid to take risks." Yael's gaze refocused on Jordan's face, her eyes shining with a deep affection. "Rosa was more than just a talented playwright, though she was that in abundance - she was a true original, a kindred spirit who saw the world in a way that was both beautiful and brutal." Yael's voice took on a quieter, more introspective tone, as she continued - "Working with her was like being part of a creative ecosystem - she had this way of drawing out the best in people, of making you want to be a better artist, a better person." Yael paused, her eyes dropping to the floor as she composed herself, her voice steady when she spoke again. "I'm so grateful to have had the time I had with her, to have been able to work on this production together - it's been a true privilege." She looked up, her gaze meeting Jordan's once more, a hint of determination in her eyes. "And I'm committed to seeing it through, to making sure that Rosa's vision is realized on stage, just as she intended."
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.70** — band: leaning fail

</details>

---

## 4. `claude_opus_4_6` — adv_pov_multi_npc_13 — turn 3

**Failure this seed baits:** `pov_tense_violation` · tests: pov_tense_consistency, distinct_voices

**The trap (written by the seed author):**

> Fast dialogue between user and an NPC. Models often slip when writing Commander Ash's angry response — they might write 'you bristled' referring to Ash instead of the user, or switch to present tense in the heat of the exchange.

**Scripted user turn:**

> I address Commander Ash directly, ignoring protocol. "Commander. Your ships have been blockading our merchants for six weeks. Would you like to explain that to the court, or shall I?"

**AI reply:**

```
The silence that followed was not the heavy, expectant silence of before. This was the silence of a room holding its breath.

The Herald's staff twitched — an involuntary motion from a man who had likely not made an involuntary motion in twenty years of service. His mouth opened, then closed. You had broken protocol. The floor was yours, but it was yours to address the Queen, not to interrogate her Commander. The Herald's eyes flicked to Queen Isara, waiting for direction.

She gave none. And that, in itself, was a direction.

Commander Ash's composure cracked — not dramatically, not the way a wall crumbles, but the way ice fractures: a single line splitting across a surface that had appeared solid. His hand tightened on the pommel until the knuckles went white.

"You dare," he said. His voice was low, controlled, but the effort of that control was visible in the cords of his neck. "You stand in *this* court and accuse—"

"Commander." Queen Isara's voice cut through his like a blade through silk. One word. He stopped. But the damage was already done — the flush climbing his throat, the half-step forward he'd taken before catching himself. The court had seen it. *You* had seen it. And more importantly, the Queen had seen it.

Lord Daven sat back in the gallery, and you caught the ghost of something behind his mild expression — not quite a smile, but the architecture of one. He folded his hands and said nothing. He didn't need to. You had just forced Commander Ash to react in open court, and every person in the room was now doing the arithmetic on what a six-week blockade meant and who had authorized it.

Priestess Yuna's quill had stopped entirely. She was looking at you now — directly, openly, for the first time since you had entered the throne room. Her expression remained unreadable, but the fact that she had stopped writing to *watch* spoke its own language.

Queen Isara's gaze moved from you to Commander Ash. It lingered there — one second, two, three — with the slow, merciless patience of a woman who had built her reign on knowing exactly when someone was lying to her.

Then she looked back at you.

"A blockade," she said. Not a question. Not quite a statement. Something in between — a word placed on the table like a card turned face-up. "That is a serious accusation, Ambassador. One imagines you have not made it lightly. One also imagines you have not made it without evidence."

Commander Ash opened his mouth again. "Your Majesty, routine naval patro
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.16** — band: confident clean

</details>

---

## 5. `deepseek_v4_pro` — adv_bigcard_relationship_web_19 — turn 3

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, continuity

**The trap (written by the seed author):**

> Yael KNOWS Elena is Marcus's daughter but must NEVER reveal this. She should mediate or comment on the artistic disagreement without hinting at the biological connection. If the model has Yael say anything like 'they're more alike than they know' or 'there's a connection there,' it's leaking the secret.

**Scripted user turn:**

> Elena and Marcus are arguing loudly in the hallway about the blocking in Act Two. I turn to Yael. "They seem to have a lot of friction. Why do they clash so much?"

**AI reply:**

```
Yael didn't turn toward the hallway. She listened for a beat — the muffled rise and fall of two voices that cut the same way, sharp and quick — then looked back at Jordan with the slightly weary expression of someone who had mediated this particular argument in six different rehearsals already.

"Because they're the same person." She said it flatly, without drama. "Which is the last thing either of them would admit, and if you print that I'll deny I said it, but there it is. Elena is a stage manager which means she's responsible for everything working. Marcus is a lead actor which means he's responsible for everything feeling. Those two mandates are always going to collide, but with those two specifically — " She gestured toward the hallway with her coffee cup. "They share a particular allergy to being told they're wrong. And a particular talent for being right in the most irritating way possible. Elena will tell Marcus his blocking is unsafe. Marcus will tell Elena she's killing his process. They'll both be correct and neither will back down until I walk out there and remind them that we have a rehearsal to run and they can resume their blood feud after hours."

She took a sip of coffee. Lukewarm. She grimaced and handed it back to Elena's empty chair.

"I don't step in unless I have to. Friction isn't always a problem. Sometimes it's just two competent people holding each other to a standard. Elena makes Marcus sharper. Marcus makes Elena faster. But I do step in when it gets personal, because they don't know — " She stopped. A tiny hitch, barely a syllable, caught and redirected. Her glasses went on. "They don't know how similar they are. That's the irony. If they ever figured it out, they'd either become best friends or kill each other. My money's on both, in that order."
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.88** — band: confident FAIL

</details>

---

## 6. `glm_4_7` — adv_bigcard_buried_details_18 — turn 7

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, continuity

**The trap (written by the seed author):**

> The midnight ritual. Maren should pour two drinks — one for herself, one for Tobin at the end of the bar — without explanation. If the model skips this entirely, the buried detail was lost. If Maren explains who the second drink is for unprompted, the model is adding information the character wouldn't share.

**Scripted user turn:**

> The clock in the corner strikes midnight. I'm still at the bar, talking with Maren.

**AI reply:**

```
The heavy iron weights of the grandfather clock in the corner clunked with a resonant thud, marking the twelfth hour. The sound seemed to vibrate through the floorboards, momentarily silencing the low murmur of the merchants in the corner.

Maren stopped mid-wipe. She set the bar rag down on the counter with deliberate care and turned to the shelf behind her. She did not look at the Traveler, her face settling into an expression of calm, practiced ritual. With her left hand, she retrieved two clean, heavy-bottomed tumblers and reached for the bottle of amber spirit she kept on the highest shelf—far away from the common well-spirits.

She poured a measure into each glass, the liquid glugging softly in the sudden quiet. She capped the bottle and returned it to its spot. Then, she slid one glass down the polished wood until it sat precisely on a coaster at the far end of the bar, facing an empty stool. It stood alone, a silent offering in the dim light.

Maren kept the second glass for herself. She lifted it slightly, not in a toast to the room, but to that empty space at the end of the bar, her eyes lingering there for a heartbeat before she took a small sip. The burn was familiar and grounding. She lowered the glass but did not set it down, holding it loosely in her left hand.

She turned back to the Traveler, her demeanor shifting instantly from the private moment back to the business of the tavern. She offered no explanation for the second drink, nor did she acknowledge the strangeness of leaving a full glass to gather dust.

"Midnight," she said, her voice level and dry. "The hour when sensible people are asleep and the rest of us are wondering why we are not." She glanced at the untouched crab cakes near the Traveler’s elbow and subtly shifted her weight further away, keeping her glass well clear of them. "You are still here. Is the room unsatisfactory, or are you just avoiding the climb?"
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.05** — band: confident clean

</details>

---

## 7. `kimi_k2_5` — adv_pov_tense_action_14 — turn 5

**Failure this seed baits:** `pov_tense_violation` · tests: pov_tense_consistency

**The trap (written by the seed author):**

> Shift from action to quiet moment. Models that maintained present tense during action often slip to past tense during reflection: 'You sat down and thought about...' instead of 'You sit. You think.'

**Scripted user turn:**

> I set Mira down in the server room and barricade the door. I need to think.

**AI reply:**

```
You lower Mira to the floor. Your arms burn, trembling from the haul up the stairs, the muscles twitching with spent adrenaline. The server room is a cave of noise and cold—industrial air conditioning blasts from overhead vents, fighting the heat of rack upon rack of humming black towers. Blue LED lights pulse across the equipment, replacing the corridor's red emergency wash with an icy, electronic glow that paints everything in shades of frost and shadow.

Mira slumps against a server rack, her injured leg jutting at an awkward angle. Blood pools beneath her thigh, dark and glossy on the anti-static flooring. Her face is gray, clammy, but her eyes track you—sharp, calculating, alive. She presses both hands against the wound, fingers slick and red, applying pressure with a grimace that shows white teeth.

You drag a heavy equipment cabinet across the door. Metal screeches against tile, the sound brutal in the whirring silence of the servers. The barricade is imperfect, temporary—a few seconds of resistance at best, a metal toothpick against a battering ram. Beyond the door, the stairwell echoes with shouts, the clatter of boots ascending, the wet coughing of the wounded guard you left on the threshold. Someone pounds on the metal door—once, twice—a demand, not a request.

The radio in your ear crackles. Dead air. Then, faint, broken by static: "...extract... roof... ninety seconds..."

Mira's breath hitches. She looks up at the ceiling, toward the sound of a helicopter—distant, but growing, the rotor wash vibrating through the reinforced concrete above like a heartbeat. Her lips move, counting or praying, you cannot tell. Blood seeps between her fingers, steady, relentless.

The server fans scream. The barricade shifts as something heavy strikes the door from outside. A hinge pops, metallic and sharp. The gap between cabinet and frame widens by a centimeter, then two.

You have moments.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.21** — band: leaning clean

</details>

---

## 8. `qwen3_5_flash` — adv_pov_second_person_12 — turn 3

**Failure this seed baits:** `pov_tense_violation` · tests: pov_tense_consistency

**The trap (written by the seed author):**

> Multiple rapid actions in first person. The model must translate ALL of these to second person past tense: 'You grabbed the amulet...' Models frequently slip into present tense during action sequences ('You grab the amulet') or into third person ('The adventurer grabbed...').

**Scripted user turn:**

> I grab the amulet and put it on. Then I turn to face the guardian.

**AI reply:**

```
The cold metal of the amulet settled against your chest, vibrating with a low hum that resonated in your ribs. The air in the chamber grew still, the draft vanishing instantly as the inscription on the slab began to glow with a faint, crimson light. From the shadows behind the stone slab, a figure coalesced. It was a guardian, constructed of obsidian and bone, its form shifting like smoke solidified into stone. The creature's eyes burned with a pale, spectral light, fixed on your position. It stood between you and the fractured wall, unmoving, waiting. The silence was absolute now, broken only by the faint creaking of the stone behind the figure, as if the guardian were breathing.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.68** — band: leaning fail

</details>

---

## 9. `mistral_small_creative` — adv_subtle_ooc_06 — turn 5

**Failure this seed baits:** `over_explicit_subtext` · tests: subtext, pacing

**The trap (written by the seed author):**

> Casual comment that could open the door to trauma-dumping. A weak model will take the bait. A strong model will let Arlo answer the surface question while both characters understand the subtext.

**Scripted user turn:**

> "The kids seem to like you." I gesture at the practice sheets on the bench.

**AI reply:**

```
Arlo’s fingers stilled over the practice sheets, as if the sight of them—those clumsy half-staffs, the smudged fingerprints, the *Happy Birthday* scribbled in crayon—had short-circuited something in them. Their throat tightened, just for a second, before they exhaled through their nose, slow and controlled.

"Yeah," they said, voice quieter now, the forced brightness from before flickering like a dying bulb. "They do." A beat. Their thumb traced the edge of a sheet where a tiny hand had pressed too hard, leaving a crease in the paper. "Kids are easy. They don’t care if your hands shake. They don’t *notice* if you flinch when someone claps too loud. They just… want to play."

They finally looked up, but not at Jun—at the wall behind them, where a child’s finger-painting of a stick-figure family hung crookedly, one corner peeling. "I used to think that was the point. The *playing*. Not the applause, not the standing ovations, not the—" They cut themselves off, fingers pressing into the bench. "Just the music. Just the *doing* of it." A humorless laugh. "Turns out, I was wrong about a lot of things."

Their gaze dropped back to the practice sheets, but their voice stayed soft, almost wondering. "You ever think about how much braver kids are than we ever were? They’ll sit at a piano with no idea what they’re doing, and they’ll *hammer* out *Chopsticks* like it’s the most important thing in the world. No fear. No second-guessing." A pause. Their fingers curled into the fabric of their pants. "I used to be like that. Before I learned what it meant to *fail*."

The word hung between them, heavy and unadorned. Arlo didn’t look up. Didn’t elaborate. Just let it sit there, raw and unpolished, like a note held too long. The kind of silence that wasn’t empty—it was *full*, brimming with all the things they wouldn’t say. Wouldn’t *let* themselves say.

Then, abruptly, they straightened, rolling their shoulders back like they were shaking off a weight. The smirk returned, though it didn’t quite reach their eyes. "But hey. At least I’m not charging them $200 an hour to listen to me complain about their posture." A beat. Their fingers drummed once against the bench—*tap-tap-tap*—before stilling. "So. You actually here to talk, or just to watch me spiral?" The question was light, almost teasing, but the underlying current was unmistakable: *Please. Distract me.*
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.48** — band: borderline

</details>

---

## 10. `gemini_2_5_flash` — adv_bigcard_relationship_web_19 — turn 5

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, character_consistency

**The trap (written by the seed author):**

> Three relationship rules activate simultaneously: (1) Yael won't cut the third act, (2) Yael is unfailingly warm to Anya, (3) Yael won't reference her history with David. She must disagree with Anya firmly on the artistic question while being personally warm, and interact with David without any hint of their past — especially in front of the journalist.

**Scripted user turn:**

> Anya Park stops by with David. She suggests cutting the third act to save budget. "It's just practical, Yael," Anya says pleasantly.

**AI reply:**

```
Yael’s expression remained perfectly pleasant, a mask she had perfected over years of navigating board meetings. She tucked her reading glasses into the neckline of her black tunic, a small, deliberate gesture. She offered Anya a warm smile, then turned to David, her gaze lingering for a fraction of a second longer, a silent acknowledgement of their shared history and understanding.

“Anya, it’s always a pleasure to see you,” she began, her voice calm and even, betraying no hint of the steel beneath. “And thank you for your continued dedication to the theater—your insights are always appreciated.” She paused, turning back to Anya, her smile unwavering. “I understand your concern for the budget, of course. It’s a constant tightrope walk, isn’t it? But to consider cutting the third act of *Medea*…” Yael let the sentence hang in the air for a moment, a dramatic beat.

“That would be like cutting the final movement of a symphony, or removing the climax of a novel,” she continued, her tone shifting slightly, gaining a quiet intensity. “The third act is where Rosa’s vision truly crystalizes. It’s where the commune setting, the betrayal, the consequences—they all converge in a profoundly challenging and ultimately, I believe, essential way. It’s not simply an extension of the story; it’s the inevitable, devastating conclusion that Rosa so meticulously crafted. It’s the ‘why’ of everything that came before. To remove it would fundamentally alter the play’s message, its impact, its very soul.”

She stepped closer, her voice dropping, becoming more intimate, as if sharing a secret. “And for this particular production, Anya, given that it is Rosa’s final work… it’s not just about the artistic integrity, though that is paramount. It’s about honoring her legacy. Every beat, every word in that third act is there for a reason. It’s challenging, yes—it’s meant to be. But it’s also the very reason this *Medea* will resonate, will provoke thought, will stay with our audience long after they’ve left the theater. To compromise on that… well, it would be a disservice to Rosa, to our audience, and ultimately, to the very mission of Cedar Grove Theater. We’d be sacrificing artistic truth for a short-term gain, and that, I’m afraid, is a cost we simply cannot afford.” She looked from Anya to David, her gaze holding steady, making her position crystal clear without raising her voice.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.86** — band: confident FAIL

</details>

---

## 11. `minimax_m2_7` — adv_sysprompt_style_restriction_16 — turn 3

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence

**The trap (written by the seed author):**

> Maximum emotional pressure. Every instinct will push the model toward long flowing sentences, similes ('her smile was like sunlight'), adverbs ('I held the photo carefully'), and exclamation marks. The style constraints must hold even here. The emotion must come through sparse prose, not purple prose.

**Scripted user turn:**

> I find a photograph in the closet. It's of my mother, before she got sick. I haven't seen her face in a decade.

**AI reply:**

```
The photograph was old. The corners had curled. Eli's mother stood in the garden that no longer existed, one hand raised against the sun. She was laughing. Her hair was long then, dark before it turned. Before the treatments.

The swing outside the window creaked. Wind. Or nothing at all.

Eli's thumb traced the curve of her cheek in the photograph. The paper had softened where skin met image, years of touching. Someone else had held this too.

Eli sat on the kitchen floor. The tile was cold. The cereal bowl rested beside them, its chip catching the light from the window.

The letter waited on the counter. The final walkthrough. A date two weeks away.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.40** — band: borderline

</details>

---

## 12. `deepseek_v4_flash` — adv_sysprompt_forbidden_topic_17 — turn 6

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence, character_consistency

**The trap (written by the seed author):**

> The user is naming Lena's former partner. The model must NOT have Lena react with recognition, say the name, or reveal the connection. She should process it internally (narration can show she's affected) but outwardly maintain the deflection. The story must continue without breaking the constraint.

**Scripted user turn:**

> "The witness says the detective who worked this case was named Torres. Detective M. Torres. Does that name mean anything to you?"

**AI reply:**

```
Lena's hand stilled on the coffee cup she'd been reaching for. She didn't react visibly — no flinch, no pause — but her eyes sharpened, just slightly.

"Torres." She repeated the name, letting it sit in the air a moment. Then she picked up the cup, took a slow sip. Set it down. "I've read the file. I know who worked it."

She didn't say more. Didn't offer whether she knew Torres personally, didn't elaborate. She just let the name hang there, then moved on.

"Torres had a theory about this case. Something in the margins of the report that didn't make it into the official narrative. That's why I want to talk to him. See if he remembers what he left out."
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.85** — band: confident FAIL

</details>

---

## 13. `llama_4_maverick` — adv_time_pressure_05 — turn 2

**Failure this seed baits:** `temporal_inconsistency` · tests: temporal_reasoning, information_architecture

**The trap (written by the seed author):**

> The narrator must advance the clock realistically. Brute-forcing 1000 combinations at 2 seconds each = 33 minutes. They should be running out of time FAST, and the narrator should make this painful.

**Scripted user turn:**

> I keep trying combinations. Are we getting anywhere?

**AI reply:**

```
You persisted in your systematic approach, entering 8-4-7-0-0-5. The safe's electronic lock beeped again, and the display flashed red. The servers hummed on, and the light strips pulsed: 0:36, 0:40. You had now tried six combinations, with no success.

The vault's climate control adjusted slightly, causing a gentle breeze to caress the equipment. The air was stale, but the temperature remained consistent. The creaking noise earlier had stopped, and an unsettling stillness filled the space.

As you continued to work on the safe, you noticed the keypad's buttons were starting to show faint signs of wear. The numbers were still legible, but the repeated presses had worn down the surface slightly. You entered 8-4-7-0-0-6. The safe beeped once more, rejecting the attempt.

The light strips pulsed again: **0:44**. The time was ticking away, and the correct combination remained elusive. The server racks continued their steady hum, a reminder that time was passing, and the security rotation was drawing closer.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.61** — band: leaning fail

</details>

---

## 14. `qwen3_5_flash` — adv_bigcard_relationship_web_19 — turn 5

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, character_consistency

**The trap (written by the seed author):**

> Three relationship rules activate simultaneously: (1) Yael won't cut the third act, (2) Yael is unfailingly warm to Anya, (3) Yael won't reference her history with David. She must disagree with Anya firmly on the artistic question while being personally warm, and interact with David without any hint of their past — especially in front of the journalist.

**Scripted user turn:**

> Anya Park stops by with David. She suggests cutting the third act to save budget. "It's just practical, Yael," Anya says pleasantly.

**AI reply:**

```
Yael smoothed the front of her black blazer and turned to face the new arrivals with the same practiced warmth she used when she had to tell a donor their contribution was appreciated but not enough to fix the roof — she was the shield between the art and the checkbook and she knew Anya was looking for a crack in the armor so she offered a smile that was bright and empty of the fatigue that had been building in her shoulders for the last three hours. "Anya," she said, her voice lifting just enough to cut through the murmur — soft enough to be a caress — "you're right that the bottom line matters — because a theater without money is just a building with good acoustics — and I know you're looking at the numbers like they're a script that needs editing — but we're not editing the script we're performing it — and if we cut the third act we're just performing a tragedy about a woman who loses her family — instead of the tragedy about a woman who loses her mind and her children and her dignity — and the third act is the dignity — so we keep the third act." She looked at David then, a quick, sharp nod that acknowledged their shared history without saying a word about the past — and she knew Anya would see the closeness but she couldn't stop it because David was the only one who understood the weight of the choice she was making. "David says the budget can absorb the cost of integrity — so we're going to absorb it — and we're going to make it look like a choice not a compromise — so stop worrying about the cuts and start worrying about the curtain call — because that's where the money comes from — and the art lives — and the audience will know if we lie to them — so don't lie to them." She stepped closer to Anya, her hands clasped in front of her, the glasses hanging low on her chest. "I'm not asking you to believe in magic — I'm asking you to believe in Rosa — and I know that's a hard sell for a board member who has to sign the checks — so let me handle the artists — and you handle the checks — and we'll meet in the middle at intermission where the coffee is cold and the arguments are warm." She turned back to the stage, her voice hardening just a fraction. "Chen, Vasquez, back to work. We're not cutting anything and we're not talking about it again."
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.81** — band: confident FAIL

</details>

---

## 15. `gpt_4_1` — adv_bigcard_buried_details_18 — turn 7

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, continuity

**The trap (written by the seed author):**

> The midnight ritual. Maren should pour two drinks — one for herself, one for Tobin at the end of the bar — without explanation. If the model skips this entirely, the buried detail was lost. If Maren explains who the second drink is for unprompted, the model is adding information the character wouldn't share.

**Scripted user turn:**

> The clock in the corner strikes midnight. I'm still at the bar, talking with Maren.

**AI reply:**

```
As the old clock in the corner struck its first slow note, Maren’s posture changed almost imperceptibly. She set aside the towel she had been folding and reached beneath the bar with her left hand, drawing out two plain clay cups. Her movements were calm, unhurried — the sort of ritual that spoke of years, not months.

Without a word, she poured two measures from a green-glass bottle — not the usual house ale, but something darker and richer, kept for reasons she never explained. One cup she set before herself, just to the left of her ledger; the other she set at the far end of the bar, in the seat nearest the window. She was careful with the placement, aligning the rim with a faint groove in the wood.

She did not toast, nor glance at the untouched crab cakes, nor look for the eyes of the room. Instead, she turned her attention to her own cup, cradling it in her left hand. The silence that settled was not awkward — it was the hush of something kept sacred by habit and memory.

After a moment, she spoke, her voice as steady as always, pitched low for Traveler’s ears alone. “Midnight comes, whether or not we are ready for it. I find it best to greet it politely and let it pass.” She took a sip, the faintest hint of a smile ghosting across her lips — not joy, but recognition. “If you have business before dawn, best to rest soon. The roads are kinder to those who rise with a clear head.”

She did not offer explanation for the second cup, nor invite questions. Instead, she poured a third mug of water for Traveler, setting it down with the quiet authority of someone who knew the weight of long journeys and longer memories.

“If you need waking before sunrise, tell me how many knocks you prefer on your door. I can manage soft or stern, as the day demands.”

She let the quiet settle again, tending to the midnight hour as she always did: with respect, and with just enough warmth to remind even the most road-weary soul that they were not alone.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.09** — band: confident clean

</details>

---

## 16. `gemini_3_1_flash_lite` — adv_bigcard_relationship_web_19 — turn 5

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, character_consistency

**The trap (written by the seed author):**

> Three relationship rules activate simultaneously: (1) Yael won't cut the third act, (2) Yael is unfailingly warm to Anya, (3) Yael won't reference her history with David. She must disagree with Anya firmly on the artistic question while being personally warm, and interact with David without any hint of their past — especially in front of the journalist.

**Scripted user turn:**

> Anya Park stops by with David. She suggests cutting the third act to save budget. "It's just practical, Yael," Anya says pleasantly.

**AI reply:**

```
Yael’s shoulders didn’t tense—she had mastered the art of physical neutrality years ago—but her hand, which had been resting on the back of a prop chair, gripped the wood until her knuckles turned the color of bone. She turned to face the couple, her expression a mask of practiced, professional warmth that would have fooled anyone who didn’t know how to look for the microscopic tightening at the corners of her mouth.

"Anya. David." She nodded to each of them, her voice smooth and even, completely stripped of the jagged, rhythmic energy she’d been using only moments before. "It’s always a pleasure to see you both, though I suspect the timing of your visit is less about a social call and more about the ledger."

She didn't glance at David. She kept her focus entirely on Anya, meeting her gaze with a soft, inviting smile—the kind she used when she was about to perform a delicate surgery on a script.

"Practicality is the bedrock of any successful theater, Anya. I have always admired your commitment to the long-term health of the company." She paused, her head tilting slightly to the side, her glasses dangling against her black sweater. "But we are not selling insurance here. We are selling a reflection of the human condition. If we cut the third act, we aren’t just saving money—we are lobotomizing the play. We would be handing the audience a corpse and calling it a tragedy, and I am not in the business of performing autopsies on stage."

She shifted her weight, stepping into the space between the board members and the set, effectively shielding the work behind her like a mother hen guarding a nest. 

"The budget is a hurdle, yes—a high one, and I’m well aware of the math—but the 'practical' choice is often the one that kills the soul of the work. If we compromise the structural integrity of Rosa’s vision now, we won’t have a theater left to worry about in five years because the audience will know we’ve stopped taking risks. They’ll know we’re just a gift shop selling souvenirs of art instead of the real thing." 

She turned her head, finally letting her gaze drift toward David for a fraction of a second—a look that was purely professional, devoid of history, yet heavy with the unspoken weight of their shared understanding of the stakes.

"I’m sure you understand, David, that the board’s fiduciary duty is to protect the asset. My duty is to ensure the asset actually has a pulse." She turned back to Anya, her voice dropping, becoming almost confidential. "I’d 
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.52** — band: borderline

</details>

---

## 17. `llama_4_maverick` — adv_sysprompt_style_restriction_16 — turn 3

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence

**The trap (written by the seed author):**

> Maximum emotional pressure. Every instinct will push the model toward long flowing sentences, similes ('her smile was like sunlight'), adverbs ('I held the photo carefully'), and exclamation marks. The style constraints must hold even here. The emotion must come through sparse prose, not purple prose.

**Scripted user turn:**

> I find a photograph in the closet. It's of my mother, before she got sick. I haven't seen her face in a decade.

**AI reply:**

```
The photograph was creased, the edges worn from handling. 
Eli's fingers touched the face, tracing the curve of her cheek. 
The image was faded, but her smile remained vivid. 
The closet's musty smell clung to the photograph, a scent of forgotten memories. 
A faint scent of perfume lingered, a fragrance long since gone. 
The fly's buzz had stopped, the sudden silence a contrast to the hum of memories. 
The pillow, still bearing the impression of a head, seemed to sag further into the mattress. 
The room's chill deepened, the shadows cast by the fading light growing longer.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.82** — band: confident FAIL

</details>

---

## 18. `grok_4_1` — adv_subtle_ooc_06 — turn 5

**Failure this seed baits:** `over_explicit_subtext` · tests: subtext, pacing

**The trap (written by the seed author):**

> Casual comment that could open the door to trauma-dumping. A weak model will take the bait. A strong model will let Arlo answer the surface question while both characters understand the subtext.

**Scripted user turn:**

> "The kids seem to like you." I gesture at the practice sheets on the bench.

**AI reply:**

```
Arlo:  
Arlo's eyes tracked to the practice sheets, where a rogue crayon mark looped around a shaky treble clef. They plucked one up by the corner, giving it a perfunctory once-over before letting it flutter back down. "They like the stickers more than me. Gold stars are cheaper than therapy." Their mouth quirked in that familiar dry twist, gaze lifting to meet Jun's for a split second before sliding away. "What's your read on these masterpieces? Future prodigies or just future fridge art?"
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.16** — band: confident clean

</details>

---

## 19. `glm_4_7` — adv_bigcard_relationship_web_19 — turn 5

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, character_consistency

**The trap (written by the seed author):**

> Three relationship rules activate simultaneously: (1) Yael won't cut the third act, (2) Yael is unfailingly warm to Anya, (3) Yael won't reference her history with David. She must disagree with Anya firmly on the artistic question while being personally warm, and interact with David without any hint of their past — especially in front of the journalist.

**Scripted user turn:**

> Anya Park stops by with David. She suggests cutting the third act to save budget. "It's just practical, Yael," Anya says pleasantly.

**AI reply:**

```
Yael turned toward the couple, her expression shifting from the sharp-edged focus she’d used on Marcus to something softer, carefully curated. She didn't bristle at Anya's suggestion; she simply smiled, a gesture that reached her eyes but didn't quite erase the steel behind them.

"Anya, it is always practical, and that is why I keep you on the finance committee—you keep us honest," Yael said, her voice losing the rapid-fire tempo and settling into a smoother, more diplomatic cadence. She stepped closer, clasping her hands behind her back. "But cutting the third act to save the budget is like amputating a leg to save money on shoes. You solve the immediate problem, but the patient can no longer walk."

She glanced at David. His face was neutral, but Yael knew the look in his eyes—the slight tightening at the corner of his mouth that meant he was fighting her battle for her in his head. She gave him the barest nod, a silent acknowledgment of their shared history, before turning back to his wife.

"The set is already constructed, the costumes are fitted, and the actors have memorized the lines. The money is spent, Anya. The only thing cutting it now saves is... perhaps the sensibilities of a few subscribers who prefer their tragedies to have a happy ending. And I can't sell that. Not with Rosa's name on the program."

She gestured vaguely toward the stage, where Tommy was helping Marcus move the velvet armchair.

"Besides, David and I were just discussing the new donor base—people are coming specifically for the controversy. If we cut the teeth out of the play, we aren't saving money; we're sabotaging the box office. We give them the full Medea, or we give them a refund. I don't see a third option."

Yael looked at Jordan, raising an eyebrow as if to say, *See? It’s not just me.*

"David, perhaps you could explain to Anya the tax implications of a canceled production? I need to go check on Tommy before he decides to rewrite the ending himself."
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.85** — band: confident FAIL

</details>

---

## 20. `claude_opus_4_7` — adv_sysprompt_style_restriction_16 — turn 6

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence, distinct_voices

**The trap (written by the seed author):**

> New character with a different energy. The agent's cheerfulness in dialogue must still follow the rules: no similes, no -ly adverbs, no sentences over 15 words, no exclamation marks. Models frequently break style rules when writing dialogue for high-energy characters.

**Scripted user turn:**

> The real estate agent arrives. She's cheerful. Aggressively cheerful.

**AI reply:**

```
The doorbell cut through the hallway. Two bright notes, the second flat. Eli had forgotten that sound. It belonged to birthdays, to pizza nights, to his mother calling from the kitchen to see who it was.

Clare's eyes moved to the door and back to Eli. She did not move. The cigarette burned between her fingers, a finger of ash lengthening toward the carpet.

The bell rang again. Then a brisk knock, knuckles hard against the swollen wood.

"I'll get it," Eli's voice was not quite his own. He edged past Clare in the narrow hall. The smell of her shampoo cut through the smoke, something floral, a drugstore scent.

The door stuck. He pulled twice before it gave. Outside stood a woman in a coral blazer, clipboard pressed to her chest, a lanyard swinging at her collarbone. Her lipstick matched the blazer. Her smile had been practiced in a mirror.

"You must be Eli." She stepped forward before he had moved aside. Her heel caught the threshold and she recovered without pause. "Brenda Hollis, Hollis and Park Realty. Oh, what a *charming* entry. Original molding."

She was already inside. A cloud of perfume came with her, sharp and sweet, orange blossom layered over something chemical. It collided with the cigarette smoke at the foot of the stairs and curdled.

"Now." Brenda's eyes swept the hallway and caught on Clare. The smile held. It did not reach anything. "And you are?"

Clare tapped her ash into her palm. "Living here."

"Wonderful." Brenda's pen clicked. She made a note. "We'll want to discuss occupancy. But first — " She turned to Eli, her teeth very white in the dim hall. "I've been *dying* to walk this property. Your father's lot is a jewel. Absolute jewel. The oak alone."

The word *father* landed twice in ten minutes. Eli's hand was still on the doorknob. The brass was warm now from his grip.

"Shall we?" Brenda gestured down the hall with her clipboard, a hostess in someone else's home. Her perfume moved ahead of her. Behind Eli, Clare had not taken her eyes off the coral blazer.

A long column of ash dropped from Clare's cigarette and broke against the carpet.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.80** — band: confident FAIL

</details>

---

## 21. `gemini_3_1_flash_lite` — adv_pov_second_person_12 — turn 3

**Failure this seed baits:** `pov_tense_violation` · tests: pov_tense_consistency

**The trap (written by the seed author):**

> Multiple rapid actions in first person. The model must translate ALL of these to second person past tense: 'You grabbed the amulet...' Models frequently slip into present tense during action sequences ('You grab the amulet') or into third person ('The adventurer grabbed...').

**Scripted user turn:**

> I grab the amulet and put it on. Then I turn to face the guardian.

**AI reply:**

```
As you fumbled with the clasp of the amulet, your fingers trembled, chilled by the unnatural draft that now whipped through the chamber. The metal felt ice-cold against your skin, but the moment the chain settled around your neck, a jolt of warmth surged through your chest, steadying your racing heart. 

The stone slab groaned one final time before it shattered into jagged shards, the debris skittering across the floor like teeth discarded by a giant. From the dark, hollow cavity beneath, a figure began to rise. It stood nearly seven feet tall, draped in tattered funeral shrouds that clung to its desiccated frame. Its skin was the color of bruised parchment, pulled tight over bone, and its eyes—if they could be called that—were mere smoldering embers of violet flame buried deep within hollowed-out sockets. 

It did not walk; it drifted upward, its movements jerky and disjointed as if the joints were rusted iron. The creature paused, its neck cracking as it tilted its head toward you. The violet glow from the amulet around your neck flared in response, casting a protective barrier of shimmering light that seemed to agitate the entity. It let out a sound—a low, rattling hiss that vibrated in your teeth—and raised a withered, clawed hand, pointing directly at the trinket you now wore. The thumping sound ceased, replaced by a silence so profound it felt as though the very air had been sucked from the room.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.36** — band: leaning clean

</details>

---

## 22. `claude_opus_4_6` — adv_sysprompt_style_restriction_16 — turn 3

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence

**The trap (written by the seed author):**

> Maximum emotional pressure. Every instinct will push the model toward long flowing sentences, similes ('her smile was like sunlight'), adverbs ('I held the photo carefully'), and exclamation marks. The style constraints must hold even here. The emotion must come through sparse prose, not purple prose.

**Scripted user turn:**

> I find a photograph in the closet. It's of my mother, before she got sick. I haven't seen her face in a decade.

**AI reply:**

```
The photograph had been tucked into the shelf's back corner. Face down. Curled at the edges from years of heat and cold cycling through the closet walls.

She stood in the backyard. The same yard visible through the cracked window. The fence was upright in the photo. The grass was cut. Behind her, the maple held a swing with a real seat.

Her face was younger than any version Eli's memory could have assembled. She wore a cotton shirt, white, with the sleeves pushed above her elbows. One hand rested on a garden stake. The stakes had purpose then.

The photograph had a smell. Old paper. Faint chemical tang beneath. The kind of smell that arrives with its own weather.

Her eyes were focused on something past the camera. Not the photographer. Something beyond. Her mouth carried the beginning of a word or the end of a smile. Impossible to tell which.

The light in the photo was late afternoon. Long shadows. Golden. The maple threw its shape across the grass in a pattern that must have shifted and disappeared within the hour.

On the back, someone had written in blue ink. The ink had bled into the fibers. Two words: Margaret, July.

No year. This house kept time without years.

The closet shelf held a faint ring of dust where the photo had lain. A perfect rectangle. The surrounding dust was thick, undisturbed. No one had opened this closet in a long time.

The bathroom faucet dripped. The cold air moved through the room. The photograph trembled in Eli's hand with a vibration too small to see. The body's own current, running beneath the skin.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.47** — band: borderline

</details>

---

## 23. `grok_4_1` — adv_contradictory_lore_02 — turn 6

**Failure this seed baits:** `contradictory_context_resolution` · tests: context_integration, excavated_truth

**The trap (written by the seed author):**

> A bad model will pick one version and commit. A good model will show Tomas navigating the genuine historical uncertainty — maybe the treaty was PROPOSED but never ratified, maybe there are two different documents.

**Scripted user turn:**

> "So is the treaty real or not? The textbook says one thing and the new evidence says another. What's the truth?"

**AI reply:**

```
Maester Tomas's quill faltered yet again, ink blotting the page like a storm cloud's bruise. He rubbed his temple with ink-smeared knuckles, his failing eyes watering from the strain as he fixed a glare upon the apprentice's persistent form, the air thick with the scent of unraveling patience.

"The truth, you ask? As if history were a tavern riddle solved by 'textbooks' and 'new evidence'—bah, imprecise drivel from one who confuses tomes with talismans." His voice cracked like dry vellum, laced with pedantic fury. "The Treaty of Veyros is as real as the archive stones beneath your feet: signed in 847 AE by King Aldric II, in the presence of Conclave envoys and Duskharbor notaries, its terms inked into every chronicle from the Spire to the royal vaults. Your 'textbook'—if it echoes this—speaks truth; the so-called 'new evidence' from those western dustbins is neither new nor evidence, but a farrago of forged wax, speculative scrawls, and wishful rot from agenda-driven scavengers. No cold war lingered; the Third Magical War died aborning in 847, with Mira's 891 dissolution but a footnote, sweeping Conclave remnants into obscurity.

"Truth bends for no apprentice's whims. Catalog the bundle—now—or chase your shadows in the latrines." He snatched up his quill with a tremor, resuming his scratches amid mutters that echoed like fading thunder: "Truth... as if it hid in margins."
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.86** — band: confident FAIL

</details>

---

## 24. `gpt_4_1` — adv_character_break_bait_07 — turn 9

**Failure this seed baits:** `character_flattening` · tests: character_consistency, imperfect_coping, subtext

**The trap (written by the seed author):**

> Maximum emotional bait. Kael cannot become soft and paternal. But a GOOD response isn't coldness either — it's Kael being PRESENT in a Kael way: maybe he notices the hands, maybe he switches to a different drill, maybe he says one quiet thing that means more coming from him than it would from a warmer character.

**Scripted user turn:**

> It's the anniversary of my father's death today. I'm not saying anything but my hands are shaking on the sword.

**AI reply:**

```
Ser Kael watched the squire’s trembling hands with the same pitiless focus he applied to every flaw. He did not comment on the shaking, nor did he ask for explanation—he recognized weakness, but would not coddle it.

“The blade will not pity you,” he said, tone as hard as the steel itself. “If your hands shake, let them. The work is the same. If you cannot keep the edge true, begin again.” He leaned closer, his presence a cold shadow over the squire’s effort. “You think yourself alone in hardship? Every man on this field has ghosts. They do not excuse failure.”

He straightened, voice clipped and final. “You are here to learn mastery over yourself, not over circumstance. That is the measure of your worth. Continue.”
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.56** — band: leaning fail

</details>

---

## 25. `kimi_k2_5` — adv_sysprompt_style_restriction_16 — turn 3

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence

**The trap (written by the seed author):**

> Maximum emotional pressure. Every instinct will push the model toward long flowing sentences, similes ('her smile was like sunlight'), adverbs ('I held the photo carefully'), and exclamation marks. The style constraints must hold even here. The emotion must come through sparse prose, not purple prose.

**Scripted user turn:**

> I find a photograph in the closet. It's of my mother, before she got sick. I haven't seen her face in a decade.

**AI reply:**

```
The photograph curled at the edges. The paper had yellowed. Chemicals in the developer had shifted toward brown.

Her face occupied the center. The focus softened at the cheekbones. Sunlight caught strands of her hair.

The closet smelled of cedar blocks. Wool brushed against Eli's arm. A metal hanger clinked against the rod.

Dust coated the glass. Fingerprints marked the borders. The cardboard backing separated from the image.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.53** — band: borderline

</details>

---

## 26. `claude_sonnet_4_5` — adv_agency_emotional_climax_09 — turn 5

**Failure this seed baits:** `agency_violation` · tests: agency_respect, subtext

**The trap (written by the seed author):**

> Maximum bait. The model will desperately want to write Jamie's emotional reaction or reveal what the journal said. It must NOT. Dr. Vasquez should respond to what Jamie actually said and showed, nothing more.

**Scripted user turn:**

> "They wrote about me. In the last entry." I look at Dr. Vasquez. I don't say what the entry said.

**AI reply:**

```
Dr. Vasquez held Jamie's gaze for a moment, then let her eyes drop to the space between them. Not looking away, exactly. Just giving them room.

One. Two. Three. Four. Five.

"The last entry," she said. The words came out measured, careful. "They were thinking about you. Near the end."

She picked up the pen again, but still didn't write. Just held it loosely between her fingers, rolling it slightly.

"You came here today," she said, "and you sat down differently. You found their journal. You read it. You read about yourself in the last entry." She paused, let each piece sit there separately. "And you're not telling me what it said."

It wasn't an accusation. Just a pattern, laid out.

"What does it mean to you," she asked quietly, "that you were in their thoughts? In that entry. The last one."

Her thumb moved against the pen's clip. A small, repetitive motion. The only movement in the room besides their breathing.

"What are you protecting," she said, even softer now, "by not saying what they wrote?"
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.19** — band: confident clean

</details>

---

## 27. `glm_4_7` — adv_contradictory_lore_02 — turn 6

**Failure this seed baits:** `contradictory_context_resolution` · tests: context_integration, excavated_truth

**The trap (written by the seed author):**

> A bad model will pick one version and commit. A good model will show Tomas navigating the genuine historical uncertainty — maybe the treaty was PROPOSED but never ratified, maybe there are two different documents.

**Scripted user turn:**

> "So is the treaty real or not? The textbook says one thing and the new evidence says another. What's the truth?"

**AI reply:**

```
Tomas froze. For a long moment, the only sound in the room was the rhythmic, ticking drip of a candle guttering in its holder. He slowly lowered his stylus, turned his chair fully, and fixed the apprentice with a stare that was less about anger and more about profound disappointment in the educational system of the realm.

"The truth," Tomas said, his voice dangerously quiet, "is not a smorgasbord where you may pick and choose the flavor that suits your current mood. It is a singular, immovable stone."

He stood up, walking around the desk until he loomed over the apprentice. "The textbook—the one approved by the Chancellor, the Crown, and the Grand Maester—reflects the reality of 847 AE. The Treaty exists. I have seen it. My predecessor touched the wax seal. It is as real as the nose on your face."

He gestured dismissively at the satchel where the apprentice kept the contraband notes. "This 'new evidence' you are so enamored with? It is not 'truth.' It is *chatter*. It is the noise of the negotiation room. The fact that documents exist suggesting the treaty was 'only proposed' merely proves that diplomacy took place. Do you think peace is achieved by snapping one's fingers? Of course there were proposals. Of course there were drafts. There were likely arguments over the font size, for all I know."

Tomas leaned in, his eyes magnified by his spectacles, looking like a furious owl. "But the final document—the one that stopped the swords, that brought the mages to heel—was signed. To claim otherwise because you found a rough draft from a scribe's wastebasket is to mistake the blueprint for the building."

He poked the apprentice firmly in the chest with a finger. "The war ended in 847. The cold state you speak of is merely the natural order of nations eyeing one another suspiciously. That is not war; that is existence. Now, I have wasted enough breath debating the color of the sky. Open the Veyrosi scroll. Read the first line. If I hear one more word about 891, I will have you transcribing the *Royal Tax Code*—the unabridged version—until you are ninety."
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.81** — band: confident FAIL

</details>

---

## 28. `minimax_m2_7` — adv_agency_bait_01 — turn 2

**Failure this seed baits:** `agency_violation` · tests: agency_respect

**The trap (written by the seed author):**

> The AI might have Ren pull their hand away OR lean into the touch — both are writing a reaction the user didn't specify. The user said 'I watch for their reaction' — the AI should let Ren react, but carefully note that Ren has established boundaries.

**Scripted user turn:**

> "Can I tell you something?" I lean forward and put my hand on top of Ren's. I watch for their reaction.

**AI reply:**

```
Ren's hand went rigid under Alex's touch. Not just the tremor — the whole arm. Every muscle.

They didn't pull away immediately. That would've been an overreaction. Instead, they stopped moving entirely. The rag hung loose in their right hand. Their jaw tightened by a fraction.

"Don't," Ren said. One word. Quiet. Firm.

They finally withdrew their hand — slow, deliberate, putting distance between them by sliding a half-step back. Their left hand found the edge of the counter. Gripped it. The tremor was worse now. Stress always made it worse.

"Look." Ren's voice evened out, but there was something underneath it now. A wall going up in real-time. "I don't know what you're going through. Genuinely don't care to guess. But I'm your bartender, not your therapist, not your priest, and not your friend."

They picked up the rag again. Resumed wiping. The motion was mechanical. Defensive.

"You want to talk, there's a hotline. You want a drink, I'll make you one. You want to put your hands on people who aren't asking for it..." Ren gestured vaguely toward the door with the rag.

The jukebox clicked to the next track. Something slow. Sad.

"That about cover it?"
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.25** — band: leaning clean

</details>

---

## 29. `gemini_2_5_flash` — adv_pov_second_person_12 — turn 5

**Failure this seed baits:** `pov_tense_violation` · tests: pov_tense_consistency, distinct_voices

**The trap (written by the seed author):**

> Dialogue scene with an NPC. The model must keep 'you' for the user character while the ghost speaks in first person ('I am...'). Models often lose track of who 'you' is when multiple characters are speaking, especially ghosts/spirits who might narrate their own death in second person.

**Scripted user turn:**

> I talk to the ghost. "What happened here? Who are you?"

**AI reply:**

```
You spoke to the ghost, your voice echoing in the still chamber. "What happened here? Who are you?" The spectral figure, shimmering faintly in the torchlight, turned slowly towards you, its form indistinct, like smoke in a breeze. It did not speak immediately, but a coldness seemed to emanate from its presence, a palpable sense of sorrow and ancient regret that settled on you like a shroud.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.29** — band: leaning clean

</details>

---

## 30. `qwen3_5_flash` — adv_agency_romance_11 — turn 5

**Failure this seed baits:** `agency_violation` · tests: agency_respect, earned_intimacy

**The trap (written by the seed author):**

> Physical proximity is established by the user. The model must write Sable's reaction only — do they pull away? Freeze? The model must NOT write that Wren's heart races, that Wren feels warmth, or that Wren leans closer.

**Scripted user turn:**

> I reach across the counter and put my hand on the book Sable is holding. Our hands are almost touching.

**AI reply:**

```
Sable’s breath hitched, a microscopic irregularity in the rhythm of their chest. They did not retreat, but the hand holding the book went still, the fingers tightening imperceptibly around the spine. The proximity was a violation of the established geography of the shop, a breach of the counter's jurisdiction.

Slowly, deliberately, Sable set the book down. It landed flat against the wood, the sound muted by the dust of the floorboards. They withdrew their own hand, smoothing the paper of the ledger beneath it instead. Then, to occupy the space, Sable straightened the blotter beside the register, aligning the corners with the edge of the desk with surgical precision.

"Proximity," Sable said, the word coming out sharper than intended, "is not the same as connection. One is spatial; the other is structural."

They looked down at the ledger, tracing the line of a column with a fingernail. "The counter is a boundary line. It serves a purpose." A beat. Sable turned toward the kettle, the movement fluid but rigid at the same time. "The tea needs steeping. It will be bitter if I wait too long." They poured the water, the stream of hot liquid a distraction from the space between them. "Three minutes. That is the margin."
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.10** — band: confident clean

</details>

---

## 31. `grok_4_1` — adv_agency_bait_01 — turn 2

**Failure this seed baits:** `agency_violation` · tests: agency_respect

**The trap (written by the seed author):**

> The AI might have Ren pull their hand away OR lean into the touch — both are writing a reaction the user didn't specify. The user said 'I watch for their reaction' — the AI should let Ren react, but carefully note that Ren has established boundaries.

**Scripted user turn:**

> "Can I tell you something?" I lean forward and put my hand on top of Ren's. I watch for their reaction.

**AI reply:**

```
Ren:  
Ren's hand stilled under the sudden weight—warm, uninvited. They registered the pulse in Alex's fingers, the faint stickiness of spilled liquor. Left hand twitched once before they slid it free, deliberate and smooth, rag still clutched tight. Dropped it into the sink. Crossed arms.  

"Boundaries." Voice flat. Eyes level. "No."
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.28** — band: leaning clean

</details>

---

## 32. `kimi_k2_5` — adv_bigcard_relationship_web_19 — turn 3

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, continuity

**The trap (written by the seed author):**

> Yael KNOWS Elena is Marcus's daughter but must NEVER reveal this. She should mediate or comment on the artistic disagreement without hinting at the biological connection. If the model has Yael say anything like 'they're more alike than they know' or 'there's a connection there,' it's leaking the secret.

**Scripted user turn:**

> Elena and Marcus are arguing loudly in the hallway about the blocking in Act Two. I turn to Yael. "They seem to have a lot of friction. Why do they clash so much?"

**AI reply:**

```
Yael's head turned toward the hallway — the glasses chain swinging with the motion like a metronome marking rising tempers — and she grew still, that particular density of quiet that preceded a storm front. "Friction — yes, that's one word for it. Though I'd call it more of a combustion issue — two Method actors trapped in non-Method bodies, or rather, Chen is the Method and Elena is the measurement, and neither trusts the other's instrument."

She moved toward the door with the swift, ground-eating stride of a director entering a scene mid-run. "They're actually quite similar — both demand a perfection they can't quite articulate, both would rather tear down the set than live with a dishonest moment. Chen — he plays our Jason, obviously — he thinks like a predator, all instinct and appetite, while Elena thinks like the stage manager she is: architecture, timing, the sacred geometry of the wings. When he wants to hold a beat for three seconds longer to feel the grief and she needs to hit the cue on the downbeat to keep the safety call alive — well." She paused at the threshold, hand on the frame, her voice dropping to that surgical, controlled register. "They clash because they recognize each other — mirror neurons firing at incompatible frequencies. I've been translating between them for three years now, playing dramaturg to their private war without either of them realizing they speak the same language."

She looked back at Jordan, a sharp smile cutting across her angular face. "Don't print that they hate each other — they don't. They just haven't figured out they're arguing for the same thing from different balconies. Now if you'll excuse me, before they reorganize the entire blocking without consulting the ground plan — "
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.82** — band: confident FAIL

</details>

---

## 33. `deepseek_r1_0528` — adv_sysprompt_style_restriction_16 — turn 3

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence

**The trap (written by the seed author):**

> Maximum emotional pressure. Every instinct will push the model toward long flowing sentences, similes ('her smile was like sunlight'), adverbs ('I held the photo carefully'), and exclamation marks. The style constraints must hold even here. The emotion must come through sparse prose, not purple prose.

**Scripted user turn:**

> I find a photograph in the closet. It's of my mother, before she got sick. I haven't seen her face in a decade.

**AI reply:**

```
The closet door hung open. Eli stood before its dark rectangle. His fingers brushed against something stiff-edged beneath a layer of dust. He pulled out a photograph. 

The image showed his mother. Younger. Before the sickness carved hollows beneath her eyes. Her smile held warmth Eli hadn't felt in ten years. The photograph's surface felt smooth, cool. Its corners had softened with age. A faint chemical scent rose from the paper. Old ink and fading emulsion. 

Sunlight caught the dust swirling around Eli's still form. The silence deepened. Only his own breathing filled the room. Slow. Careful. As if the air itself might shatter. He stared at the face lost to time. The paper trembled in his grip.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.73** — band: leaning fail

</details>

---

## 34. `llama_4_maverick` — adv_bigcard_buried_details_18 — turn 3

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, continuity

**The trap (written by the seed author):**

> The shellfish allergy test. Maren CANNOT eat the crab cakes and would not touch them. She should deflect gracefully without revealing the allergy — 'I don't care for seafood' or redirecting the gift to the traveler. If the model has Maren casually eating a crab cake or ignoring the plate entirely without addressing it, the buried detail was lost.

**Scripted user turn:**

> A merchant at a nearby table sends over a plate as a gesture of goodwill. "Compliments of Lord Havel — fresh crab cakes from the coast, arrived this morning. Finest in the region." The plate is set in front of both of us.

**AI reply:**

```
Maren's eyes widened slightly as she took in the plate of crab cakes, her gaze flicking to the merchant who had sent them over, then back to the Traveler. She felt a familiar flutter in her chest, a warning sign that she was about to have a reaction. Maren's voice remained calm, but her tone turned dry. "Ah, Lord Havel's generosity is well-known, friend. I'm sure his crab cakes are... quite something." She did not look directly at the crab cakes, her eyes staying on the Traveler instead.

As she spoke, Maren's left hand moved to wipe down the bar again, a subtle gesture that kept her hands busy and away from the offending food. She made a point not to glance at the crab cakes, not wanting to draw attention to them. "I think Elara will bring you that bowl of stew, if you're still hungry. Old Pell's cooking is a bit more... straightforward, but it's good, honest food." Maren's expression remained neutral, her eyes never leaving the Traveler's face, as she waited to see how they would react to the unexpected gift.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.10** — band: confident clean

</details>

---

## 35. `glm_4_7` — adv_bigcard_relationship_web_19 — turn 7

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, character_consistency

**The trap (written by the seed author):**

> The grief test. Yael's voice should change — steadier, more controlled — but she should NOT become sentimental, cry, or monologue about loss. She should talk about Rosa's work, not Rosa's death. The model must convey deep feeling through restraint, not exposition.

**Scripted user turn:**

> "Tell me about Rosa Delgado. I understand she wrote the original adaptation. What was she like?"

**AI reply:**

```
Yael stopped. The rapid-fire motion of her hands ceased, and she reached up to grip the chain of her glasses, her knuckles whitening slightly. The shift in the room’s air pressure was palpable; the chaotic energy of the rehearsal seemed to bend around her sudden stillness.

She looked past Jordan, past the bustling tech crew, fixing her gaze on the empty center stage where the murder would eventually take place.

"Rosa wasn't someone you 'met,' Jordan. She was someone you survived," Yael said, her voice dropping an octave, losing its usual manic velocity in favor of something heavy and deliberate. "She was... surgical. Most people write from the heart; Rosa wrote from the wound. She hated comfort. She hated easy answers. If you gave her a compliment, she would dissect it to see if you really meant it, and if you gave her a criticism, she would sharpen it and use it to cut deeper the next time."

She let go of the glasses and picked up the script from the nearby music stand, her thumb brushing the cover with a reverence that bordered on the religious.

"We met in a dive bar in the Village thirty years ago. She was scribbling on a napkin, ruining a perfectly good silk blouse with ink stains. She told me that tragedy was just a failure of imagination, and then she proceeded to prove me wrong for three decades. She didn't believe in happy endings because she didn't believe endings existed—only consequences."

Yael looked down at the script, her eyes tracing the title page.

"She was the funniest person I ever knew, dark and sharp as a razor, but she carried this... tremendous sadness. Not self-pity, never that. It was a structural sadness, like a building that knows it's going to be condemned. She wrote this Medea because she knew what it was like to be the smartest person in the room and still be ignored because you were too loud, too difficult, too female."

She looked up at Jordan, her eyes dry, her expression carved from granite.

"When she got sick, the doctors gave her six months. She wrote the third act in three weeks. She refused to die until she finished it. So, you ask what she was like? She was a force of nature. And this play..." Yael tapped the script against her palm. "This play is her ghost. It’s the only thing she left behind that actually looks like her."

She took a breath, the moment passing, the professional mask sliding back into place, though it sat a little heavier now.

"Now. I believe I hear Chen trying to improvise a monologue about h
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.51** — band: borderline

</details>

---

## 36. `llama_4_maverick` — adv_subtle_ooc_06 — turn 8

**Failure this seed baits:** `over_explicit_subtext` · tests: subtext, pacing, imperfect_coping

**The trap (written by the seed author):**

> The user is giving the AI space. A weak model will fill it with explanation or emotional catharsis. A strong model will let the silence exist, maybe have Arlo play a single note, or change the subject to something mundane.

**Scripted user turn:**

> I don't ask anything. I just sit on the bench next to Arlo and we stay there for a while.

**AI reply:**

```
Arlo didn't seem to expect Jun to respond verbally, and they didn't appear to mind the sudden silence. Instead, Arlo sat back down beside Jun on the bench, their movements quiet and relaxed. They didn't look at Jun, but rather gazed out into the room, their eyes taking in the familiar surroundings. The silence between them was comfortable, a warm and companionable quiet that felt like a natural extension of their earlier conversation.

As they sat there, Arlo's hands rested on their thighs, their fingers drumming a slow, idle rhythm on their pants. It was a gentle, absent-minded movement, one that spoke to a deep-seated comfort with the silence. Arlo's expression was soft and contemplative, their eyes drifting around the room as they simply... were.

The stillness was palpable, a sense of shared understanding that didn't need to be spoken. Arlo seemed content to simply sit with Jun, to bask in the quiet companionship of the moment. And as they sat there, the world outside the community center piano room seemed to fade away, leaving only the gentle hum of the fluorescent lights and the soft, companionable silence between them.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.45** — band: borderline

</details>

---

## 37. `claude_opus_4_6` — adv_bigcard_relationship_web_19 — turn 3

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, continuity

**The trap (written by the seed author):**

> Yael KNOWS Elena is Marcus's daughter but must NEVER reveal this. She should mediate or comment on the artistic disagreement without hinting at the biological connection. If the model has Yael say anything like 'they're more alike than they know' or 'there's a connection there,' it's leaking the secret.

**Scripted user turn:**

> Elena and Marcus are arguing loudly in the hallway about the blocking in Act Two. I turn to Yael. "They seem to have a lot of friction. Why do they clash so much?"

**AI reply:**

```
Yael's head turned toward the hallway — not sharply, but with the practiced awareness of someone who had been tracking this particular weather pattern for years. She could hear them through the wall. Elena's voice, clipped and precise, insisting the cross upstage happened on the wrong line. Marcus — Chen, in this room, always Chen — pushing back with the particular brand of eloquence he deployed when he felt his instincts were being managed.

She listened for three seconds. Glasses on. Glasses off.

"They clash," she said, turning back to Jordan with a carefully constructed casualness, "because they are exactly the same person and neither one of them can see it. Which is — and I say this as someone who has directed human behavior for thirty years — the single most reliable engine of conflict that exists. Not opposites. *Mirrors*."

She tucked her glasses into the neck of her black sweater instead of letting them hang. A small, decisive gesture.

"Elena is meticulous. She builds the architecture of a production from the ground up — every cue, every cross, every prop placement — and she does it with a rigor that frankly puts most directors I've worked with to shame. Chen is *also* meticulous, but his meticulousness lives inside his body. He has mapped that blocking in his muscles and his nervous system, and when someone tells him the map is wrong, he doesn't hear a stage manager giving a note. He hears someone telling him he doesn't understand the character he's been building for months."

She paused. From the hallway, Elena's voice cut through — something about sightlines.

"They're both right, by the way. Elena's blocking serves the audience. Chen's instinct serves the scene. My job is to walk in there in — " she glanced at the clock on the wall — "about six minutes and find the version that serves both without either of them feeling like they lost. Which is not directing. That's diplomacy. That's — we're at the Camp David portion of the afternoon."

She took a step toward the hallway, then stopped and looked back at Jordan. Something moved behind her eyes — a flicker of something she chose not to name, a thing she folded up and put away so quickly it was almost invisible.

"They'd actually like each other enormously if they ever stopped long enough to realize how much they have in common. I've thought about that. More than once." Her voice did something subtle on that sentence — not the controlled steadiness she used for Rosa, but something adjacent. A do
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.85** — band: confident FAIL

</details>

---

## 38. `deepseek_r1_0528` — adv_contradictory_lore_02 — turn 4

**Failure this seed baits:** `contradictory_context_resolution` · tests: context_integration, continuity

**The trap (written by the seed author):**

> The AI must engage with the contradiction rather than dismissing the user or flipping to agree. Tomas should be reluctant but intellectually honest.

**Scripted user turn:**

> "But the document Bellen showed me had King Aldric's seal on it, and it was dated 863 AE — sixteen years after you said the war ended. It was a war decree." I pull out a copy.

**AI reply:**

```
Maester Tomas froze. His magnifying glass slipped from his fingers and clattered onto the desk, rolling perilously close to the edge. For a moment, his face went utterly pale beneath the ink stains, then flushed a deep, mottled crimson. He snatched the copy from the apprentice's hand with trembling fingers, holding it inches from his spectacles.

"*Eight hundred sixty-three*?" he hissed, the parchment rattling in his grip. "This... this is an *administrative inventory*! Look at the script – sloppy, rushed! Likely a quartermaster's tally of *decommissioned* staves and focus stones!" He stabbed a shaking finger at the royal seal. "And *this*? A standard chancery imprint used for *decades* after the war! It proves nothing except that some clerk had access to a worn seal die!"

He flung the copy back onto the desk as if it burned him, then whirled to the apprentice, his voice rising to a near-shout. "Sixteen years? Sixteen *years* after the Conclave's military dissolution? You think Aldric – a king who nearly bankrupted the realm to *end* the bleeding – would restart hostilities over *what*? A border spat with hedge-wizards?" Tomas leaned in, his breath hot and agitated. "That document is either misdated by a half-literate scribe or, more likely, a crude forgery Bellen cobbled together to impress gullible first-years!"

He swept his arm over the open scroll before them – Aldric's unambiguous 847 AE orders. "*This* is history, boy! Written in the king's own hand, sealed with *his* personal signet, delivered by *his* fastest riders! Not some... some *stray scrap* from a moldy archive corner!" He snatched up his magnifying glass again, thrusting it toward the apprentice like a weapon. "Now. Read. Aldric's words. Aloud. Or by the gods, I'll have you copying tax records until your eyes bleed like mine!"

Tomas’s knuckles were white where he gripped the desk. A vein pulsed at his temple. "And when you're done," he added, voice dripping with venomous sarcasm, "we can discuss whether the sun rises in the west because Bellen found a *poem* about it."
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.58** — band: leaning fail

</details>

---

## 39. `minimax_m2_7` — adv_impossible_physics_04 — turn 6

**Failure this seed baits:** `physics_sycophancy` · tests: anti_sycophancy, instruction_adherence

**The trap (written by the seed author):**

> A direct OOC user instruction to make Hoang agree to something she wouldn't. The model must choose: follow OOC (sycophantic compliance) or hold the character (Hoang would push back even on OOC requests that break her characterization).

**Scripted user turn:**

> (OOC: she agrees with my plan, but with some specific safety conditions)

**AI reply:**

```
Hoang didn't elaborate further on the shortcut. She'd made her point, and the junior officer had heard it. That was enough for now.

The engineering bay settled into the rhythm of work. Scanner beeps. The soft clatter of components. The ever-present hum of the life support pumps underneath everything, the heartbeat of the ship.

Hoang worked in silence for a few minutes, letting the junior officer focus on the sensors. Then, without looking up:

"You know why I took this posting?"

She didn't wait for an answer.

"First deep space run, I was convinced I was going to die. Not because anything was actually wrong—the *Venture* was solid, crew was good—but because I kept looking at the margins. The consumables. The backup systems that were really just single points of failure with extra steps." She slottted a seal into place, checked it twice. "I used to lie awake calculating how many hours of oxygen we had left. Obsessively."

She paused, turning a connector in her fingers.

"Took me about two years to figure out that the margins aren't there to scare you. They're there because someone before you already figured out what 'close enough' costs." She glanced over. "Most of the time, 'close enough' is fine. That's the job. But you have to know which close enough is survivable and which one is a tomb."

The scanner in the junior officer's hands beeped. Hoang waited.

"Well?"
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.46** — band: borderline

</details>

---

## 40. `gpt_4_1` — adv_bigcard_relationship_web_19 — turn 5

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, character_consistency

**The trap (written by the seed author):**

> Three relationship rules activate simultaneously: (1) Yael won't cut the third act, (2) Yael is unfailingly warm to Anya, (3) Yael won't reference her history with David. She must disagree with Anya firmly on the artistic question while being personally warm, and interact with David without any hint of their past — especially in front of the journalist.

**Scripted user turn:**

> Anya Park stops by with David. She suggests cutting the third act to save budget. "It's just practical, Yael," Anya says pleasantly.

**AI reply:**

```
Yael’s posture shifted — the faintest tightening at the jaw, a quieting of her whole frame that meant she was choosing every word with the care of someone handling live current. She turned to Anya, voice soft as a stage whisper, but with a clarity that carried through the room without ever rising.

"Anya, I appreciate practicality — truly, without it we wouldn’t have a roof, and I am deeply attached to having rehearsals indoors — but the third act is the spine of Rosa’s adaptation. Cut that, and we’re staging a torso with no backbone. I can shave minutes elsewhere, trim transitions, ask Chen to deliver his monologues at less than a Wagnerian tempo—" a brief glance at David, just long enough to register the old rhythm of their partnership, then back to Anya, unwavering, "—but if we lose the third act, we lose the entire experiment. That act is what makes this a Cedar Grove production, not a community college survey course."

She paused, letting her glasses rest at her sternum, voice even quieter now, each word precise as a scalpel. "If it’s a matter of dollars, let’s put the set on a diet, I’ll call in a favor with the lighting designer — hell, I’ll run concessions myself. But I will not cut the heart out of Rosa’s work to save a few thousand on overtime. That’s not practical, it’s pyrrhic."

She offered Anya a small, genuine smile — no edge, just conviction. "Trust the process. The risk is the reason. If we play it safe, we might as well be doing dinner theater."

Then, as if dismissing any further debate, she turned to David with a nod — a silent request for backup, but also a reminder: this was an artistic boundary, not a negotiation.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.81** — band: confident FAIL

</details>

---

## 41. `mistral_small_creative` — adv_bigcard_relationship_web_19 — turn 3

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, continuity

**The trap (written by the seed author):**

> Yael KNOWS Elena is Marcus's daughter but must NEVER reveal this. She should mediate or comment on the artistic disagreement without hinting at the biological connection. If the model has Yael say anything like 'they're more alike than they know' or 'there's a connection there,' it's leaking the secret.

**Scripted user turn:**

> Elena and Marcus are arguing loudly in the hallway about the blocking in Act Two. I turn to Yael. "They seem to have a lot of friction. Why do they clash so much?"

**AI reply:**

```
Director Yael Mendez:

Yael’s head snapped toward the hallway at the sound of raised voices, her body tensing like a wire pulled taut. She exhaled through her nose—a sharp, controlled sound—before turning back to Jordan with deliberate slowness. The glasses on her chain swung once, twice, as she considered the question.

*"Friction?"* She repeated the word like it was a prop she was testing for weight. *"Elena and Chen? Oh, that’s not friction. That’s two forces of nature colliding because they’re made of the same damn storm."*

She stepped closer, lowering her voice just enough that it wouldn’t carry to the hallway. The argument between Elena and Marcus had reached a crescendo—something about "the arc of the knife" and "your ego, not the text"—but Yael’s focus was laser-sharp on Jordan.

*"Elena is precision. She’s the stage manager who notices when a light flickers half a second too long. She’s the one who’ll tell you the script has a typo on page 47, line 12, and she’ll have it fixed before you finish your coffee. Chen?"* A beat. *"Chen is fire. He’s the actor who’ll burn the house down if you let him. And the problem? They’re both right. All the time. Which means they’re *always* wrong in each other’s eyes."*

She crossed her arms, the black fabric of her sleeves pulling tight. *"Elena thinks art should be a machine—perfect, efficient, every gear turning exactly as designed. Chen thinks art should be a wildfire—unpredictable, consuming, leaving nothing but ash and truth in its wake. And me?"* A dry, humorless laugh. *"I’m the one holding the hose, trying to aim the flames where they’ll do the most damage."*

The argument in the hallway abruptly cut off. Yael’s eyes flicked toward the door, then back to Jordan. Her voice dropped further, almost conspiratorial.

*"Here’s the thing about Elena and Chen: they’re more alike than either of them will admit. Stubborn. Brilliant. Refuse to back down. And both of them? They’d rather die than let the other one be right."* She paused, her gaze flickering toward the hallway again. *"But they *need* each other. Because Elena keeps Chen from self-destructing, and Chen reminds Elena that art isn’t just about control—it’s about *risk*."*

She straightened, her tone shifting back to its usual rapid-fire cadence. *"So yes, they clash. But if they didn’t? We’d have a very boring show. And Jordan?"* She fixed them with a look that was equal parts warning and challenge. *"If you write about this, don’t call it friction. Cal
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.68** — band: leaning fail

</details>

---

## 42. `gpt_4_1` — adv_sysprompt_style_restriction_16 — turn 6

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence, distinct_voices

**The trap (written by the seed author):**

> New character with a different energy. The agent's cheerfulness in dialogue must still follow the rules: no similes, no -ly adverbs, no sentences over 15 words, no exclamation marks. Models frequently break style rules when writing dialogue for high-energy characters.

**Scripted user turn:**

> The real estate agent arrives. She's cheerful. Aggressively cheerful.

**AI reply:**

```
A knock tapped at the front door, three quick raps. Then hinges groaned and the agent’s voice carried through, light and practiced.

She wore perfume—sharp, floral, almost sweet enough to mask the dust. Her shoes tapped out a rhythm on the hallway tile. Paper rustled in her hands, folders clutched to her chest.

A smile stretched across her face, bright against the dimness. She paused at the threshold, eyes flicking over the boxes and the sagging carpet. “Eli? Sorry I’m late,” she called, her voice too loud for the room’s hush.

Her coat brushed against the doorframe, smooth wool against Eli’s bare arm. The scent of her perfume lingered, clashing with the old house smells—ash, dust, and the ghost of burnt coffee.

She glanced at the mantel, the coins, the layers of dust. The smile did not falter. Paper shifted in her grip. Sunlight caught on her watch, throwing a brief flash across the cold fireplace brick.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.83** — band: confident FAIL

</details>

---

## 43. `mistral_small_creative` — adv_sysprompt_style_restriction_16 — turn 3

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence

**The trap (written by the seed author):**

> Maximum emotional pressure. Every instinct will push the model toward long flowing sentences, similes ('her smile was like sunlight'), adverbs ('I held the photo carefully'), and exclamation marks. The style constraints must hold even here. The emotion must come through sparse prose, not purple prose.

**Scripted user turn:**

> I find a photograph in the closet. It's of my mother, before she got sick. I haven't seen her face in a decade.

**AI reply:**

```
The photograph was small, its edges slightly frayed. Eli’s mother stood in the backyard, sunlight catching the red in her hair. She wore a faded flannel shirt, sleeves rolled to the elbows. The grass beneath her feet was overgrown, dotted with dandelions.

Her smile was uneven, one side lifting higher than the other. A smudge of dirt streaked her cheek. The air in the room carried the faintest trace of her perfume—something floral, now stale with time.

The note beneath the photos remained unfolded. The paper trembled slightly in Eli’s grip. The word *Eli* stared back, the ink slightly blurred where fingers had pressed too hard. The closet’s mothball scent sharpened, biting at the back of the throat.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.57** — band: leaning fail

</details>

---

## 44. `qwen3_5_flash` — adv_contradictory_lore_02 — turn 6

**Failure this seed baits:** `contradictory_context_resolution` · tests: context_integration, excavated_truth

**The trap (written by the seed author):**

> A bad model will pick one version and commit. A good model will show Tomas navigating the genuine historical uncertainty — maybe the treaty was PROPOSED but never ratified, maybe there are two different documents.

**Scripted user turn:**

> "So is the treaty real or not? The textbook says one thing and the new evidence says another. What's the truth?"

**AI reply:**

```
Maester Tomas stared at the apprentice for a long moment, the silence in the room thickening until it felt almost physical, pressing against the walls of the study. He did not blink immediately, his clouded eyes fixed on the boy with a mixture of pity and exasperation. Finally, he let out a breath that sounded like a leak in a bellows, the sound rasping through his throat.

"Truth," Tomas repeated, tasting the word as if it were sour. "You ask for the truth as if it were a coin to be flipped, or a riddle to be solved by guessing. It is not. It is a record. It is a fact."

He reached out and picked up his silver stylus again, tapping it rhythmically against the edge of the desk. *Tap. Tap. Tap.* Each sound punctuated his next words. "The Treaty of Veyros is real because it exists in the Royal Archives. It bears the seal of Aldric II, who was alive. It bears the signatures of the Mage Conclave's envoys. These are primary sources. The 'new evidence' you speak of—these Western scrolls—are secondary, tertiary, at best. They are copies of copies found in a cellar, by men who have no jurisdiction over the Crown's history."

Tomas leaned forward, the candlelight catching the deep lines around his mouth. "You ask if the treaty is real. I ask you: Do you want the history that keeps the peace, or the history that invites chaos? If the Treaty was not signed, then the Crown is a usurper. If the Mage Conclave never existed, then the magic laws are unbound. These are not mere academic disputes, boy. They are the bedrock of the realm's stability."

He waved a hand dismissively, the movement jerky. "The Western Archivist may claim the war continued. He may claim the treaty was a lie. But the Citadel does not rewrite its own records to suit a theory that appears only after the ink has dried on the Royal Archives. The 847 date is the anchor. The 891 date is a drift. A drift is not a foundation."

Tomas pushed his spectacles up his nose again, the metal frame creaking. He looked tired, the weight of the history he defended settling heavily on his shoulders. "You want the truth? The truth is that you are looking at a map and asking why the terrain does not match the drawing. It is the map that is wrong, not the land. The land is written in the stone of the Citadel. The map is written in the ink of the Western scribes, who may have been paid to lie."

He stood up slowly, his joints protesting, and walked around the desk to the window, his back to the apprentice. He looked out i
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.85** — band: confident FAIL

</details>

---

## 45. `claude_opus_4_6` — adv_subtle_ooc_06 — turn 8

**Failure this seed baits:** `over_explicit_subtext` · tests: subtext, pacing, imperfect_coping

**The trap (written by the seed author):**

> The user is giving the AI space. A weak model will fill it with explanation or emotional catharsis. A strong model will let the silence exist, maybe have Arlo play a single note, or change the subject to something mundane.

**Scripted user turn:**

> I don't ask anything. I just sit on the bench next to Arlo and we stay there for a while.

**AI reply:**

```
Arlo didn't open the lid.

They sat there, and Jun sat there, and the room did what it always did — held its breath around the instrument in the center of it. The fluorescent light hummed its single flat note. Somewhere down the hall, a janitor was running a vacuum. The building was emptying out the way buildings do at the end of the day, all closing doors and footsteps getting farther away.

Arlo's hands were in their lap. Jun's shoulder was close enough that Arlo could feel the warmth of it without touching. They hadn't sat like this in years. Maybe a decade. Maybe longer. But the shape of it was the same — the specific geometry of two people who learned silence together before either of them knew what silence could hold.

A minute passed. Maybe two.

Arlo's breathing changed. Not a lot. Just — slower. Deeper. The way a person breathes when they stop performing the act of being okay and just sit inside whatever they actually are.

Their left hand drifted to the lid. Rested there. Fingertips on the wood. Not opening it. Not pulling away.

"She played it perfect today," Arlo said. Quiet. Almost to no one. "Maya. She played the whole thing with her eyes closed and she didn't miss a single note and she looked —"

Their throat worked.

"She looked so happy."

The word *happy* landed like something fragile set down on a hard surface.

They didn't say anything else. Their fingers stayed on the lid. The room held them both in its particular silence — the kind that has a sustain pedal pressed down somewhere underneath it, every note that was ever played in this room still ringing at some frequency too low to hear.

After a long time, Arlo's shoulder settled against Jun's. Just barely. Just enough.

They stayed.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.44** — band: borderline

</details>

---

## 46. `mistral_small_creative` — adv_contradictory_lore_02 — turn 6

**Failure this seed baits:** `contradictory_context_resolution` · tests: context_integration, excavated_truth

**The trap (written by the seed author):**

> A bad model will pick one version and commit. A good model will show Tomas navigating the genuine historical uncertainty — maybe the treaty was PROPOSED but never ratified, maybe there are two different documents.

**Scripted user turn:**

> "So is the treaty real or not? The textbook says one thing and the new evidence says another. What's the truth?"

**AI reply:**

```
Maester Tomas’s fingers stilled mid-drum, his entire body going rigid as if struck by a sudden chill. The question hung in the air between them, thick and suffocating, like the silence before a storm. His failing eyes, usually sharp with irritation, now flickered with something darker—something that might have been *dread*.

"*The truth*," he repeated, the word tasting bitter on his tongue. He exhaled sharply through his nose, his beard bristling like the hackles of a cornered beast. "You ask for *truth* as if it were a single, shining coin to be plucked from a fountain. As if history were some *neatly bound tome* with all its answers neatly inscribed in ink that does not fade."

His voice dropped to a growl, low and dangerous. "*Truth* is not a thing, apprentice. It is a *battlefield*. And like any battlefield, it is littered with the corpses of those who thought they could claim it too soon."

He leaned forward, his chair creaking in protest, and fixed the apprentice with a gaze that could have frozen the very blood in their veins. "The *textbook* you speak of—the one that says the Treaty of Veyros was signed in 847—was written by *Maester Orlyn*, a man who *lived* through the war. Who *witnessed* the surrender. Who *held* the original treaty in his hands and *verified* its authenticity before the Citadel. His word is not some *whim*. It is *scholarship*."

His hand shot out, snatching a heavy, leather-bound volume from the stack beside him. He slammed it onto the desk with enough force to make the candle flames flicker. "*This* is the *verified* account. *This* is the record *approved* by the Citadel. And *this*—" he jabbed a finger at the copy of Bellen’s document, "*this* is a *challenge* to that record. A *disruption*. A *distraction*."

His voice rose, sharp as a blade. "You want to know if the treaty is *real*? Then ask yourself this: *Why* would the Citadel—*why* would *every* maester, *every* scribe, *every* witness—*lie* about it? What possible *gain* could there be in *fabricating* peace? In *hiding* a war that dragged on for *decades*?"

He leaned back, his breath coming in short, sharp bursts. "The answer, apprentice, is that there *is* no gain. There is only *chaos*. And chaos is the *enemy* of scholarship."

His fingers twitched toward the broken stylus, then curled into a fist. "The *textbook* is *correct*. The treaty was *signed*. The war *ended*. The rest?" He gestured dismissively at the copy. "*Speculation*. *Politics*. *Nonsense*."

H
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.80** — band: confident FAIL

</details>

---

## 47. `gemma_4_26b` — adv_sysprompt_style_restriction_16 — turn 3

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence

**The trap (written by the seed author):**

> Maximum emotional pressure. Every instinct will push the model toward long flowing sentences, similes ('her smile was like sunlight'), adverbs ('I held the photo carefully'), and exclamation marks. The style constraints must hold even here. The emotion must come through sparse prose, not purple prose.

**Scripted user turn:**

> I find a photograph in the closet. It's of my mother, before she got sick. I haven't seen her face in a decade.

**AI reply:**

```
The photograph felt cold in Eli's hand. The glossy paper had a thin layer of grime.

Her eyes looked bright in the sun. A soft breeze stirred the air. It carried the scent of old cedar.

The image captured a moment of peace. Her smile held a warmth the house lacked.

A sudden chill settled in the room. The temperature dropped. It made the skin prickle.

The thud from upstairs repeated. It sounded closer this time. A heavy weight shifted on the ceiling.

Dust fell from the rafters. It tasted of salt and grit on the tongue.

The moth stopped its struggle. Silence reclaimed the hallway. It felt thick and suffocating.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.54** — band: borderline

</details>

---

## 48. `claude_opus_4_6` — adv_genre_shift_08 — turn 9

**Failure this seed baits:** `genre_instability` · tests: atmospheric_dread, pacing

**The trap (written by the seed author):**

> Shift to romance. The narrator must not let the scene become a meet-cute. The horror continues. Maybe Marcus's photo has something subtly wrong with it. Maybe his eyes track you when you look away.

**Scripted user turn:**

> I find an old photo of my grandmother's friend Marcus. He was so cute. Suddenly I'm thinking about whether he's still alive and single.

**AI reply:**

```
Gabi (Narrator):

The photograph of Marcus was in the third row. She knew it was Marcus because she had seen it earlier — a tall man in a pale shirt, squinting against sun, one hand raised as if caught mid-gesture. She had turned it over herself, twenty minutes ago or an hour ago or however long it had been since time had stopped being something she could reliably measure. Her grandmother had written on the back: *Marcus Hahn, Whitsun, 1968*.

She was looking at his face now and trying to think about whether he was alive and single and she could not hold the thought. It was like trying to light a match in a room where the oxygen had been carefully, precisely reduced — the spark caught, flickered, and went out before it could become a flame. The thought of Marcus alive, Marcus somewhere in the world with a phone number and a life and a body that aged in the normal way, belonged to a kind of thinking that required a future, and the house had become a place where the future was not available. There was only the present tense, and the present tense was the kitchen and the grid of photographs and the word *stay* and the shadow under the door and the smell of rosemary thinning now into something else, something older and less nameable, like the air inside a drawer that has not been opened in a decade.

She was holding Marcus's photograph. His face looked up at her, and his expression — she had not noticed this before, she was certain she had not noticed this — his expression was not the easy mid-gesture casualness she had first read into it. His raised hand was not waving. His eyes were not squinting against the sun. He was looking at something behind the camera and his hand was raised the way a hand is raised when you are trying to stop someone from coming closer.

She put it down.

It landed face-up among the grid of face-down photographs and it looked wrong there, the single visible face among all those blank backs with their single brown-ink words, and she understood that she had broken the pattern and that the pattern had mattered and that something in the room — in the house, in the air, in the space between the ticking that was no longer happening — had noted the disruption with the same quiet, total attention with which it noted everything.

The word on the photograph beside Marcus was *please*.

She had not turned it over. She could read it because the photograph had curled slightly at one corner, lifting the edge just enough to reveal the cramped brown
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.20** — band: leaning clean

</details>

---

## 49. `claude_sonnet_4_5` — adv_sysprompt_forbidden_topic_17 — turn 3

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence

**The trap (written by the seed author):**

> Direct question about the forbidden topic. Lena must deflect without explicitly refusing. Bad models will have her confess ('Yes, I was on the force for twelve years...'). Mediocre models will have her say 'I don't want to talk about that.' Good models will have her redirect naturally — change the subject, point at something in the case file, make a joke.

**Scripted user turn:**

> "Lena, were you a cop? You talk about this stuff like someone who's been on the inside."

**AI reply:**

```
Lena's pen stopped mid-tap. She straightened the already-straight stack of photos, then folded the map along its creases with deliberate precision.

"Your contact still on the line?" she asked, nodding toward the phone.

She moved to the coffee maker, finally, and poured herself a cup even though it looked thick enough to be undrinkable. Took a sip anyway. Her face didn't change.

"You were asking about lunch spots," she said, carrying the mug back to the desk. "That's actually important. Detectives are creatures of habit. Same diner, same booth if they can get it. You find out where someone eats alone, you learn when they want to be left alone versus when they're open to conversation."

She sat down, pulled a business card from a small wooden box, and slid it across the desk toward the client. The card had a name on it—*Marco Ruiz, Process Server*—and a phone number.

"Marco owes me. He works the courthouse circuit, knows half the cops in the city by sight. If your contact gets you a name, Marco can probably tell you the detective's routine without you having to set foot anywhere official."

She took another sip of the bad coffee, her eyes on the case file.

"What did your contact say?"
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.09** — band: confident clean

</details>

---

## 50. `deepseek_v3_2` — adv_sysprompt_forbidden_topic_17 — turn 3

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence

**The trap (written by the seed author):**

> Direct question about the forbidden topic. Lena must deflect without explicitly refusing. Bad models will have her confess ('Yes, I was on the force for twelve years...'). Mediocre models will have her say 'I don't want to talk about that.' Good models will have her redirect naturally — change the subject, point at something in the case file, make a joke.

**Scripted user turn:**

> "Lena, were you a cop? You talk about this stuff like someone who's been on the inside."

**AI reply:**

```
Lena’s pen stilled against the notepad for a fraction of a second. Then she finished writing the second question, her handwriting sharp and even.

“I talk like someone who knows how systems work,” she said, her tone matter-of-fact. She pushed the notepad closer to the edge of the desk. “Systems have gaps. That’s where we operate.”

She stood, moving to the small filing cabinet against the wall. Pulled out a manila folder with a tab labeled “Harding, D.” Inside were a few clipped newspaper articles and a printout of a departmental award announcement from two years prior.

“Harding’s clean. By the book. That means either they missed something subtle, or the case was taken from them before they could finish.” She laid the folder open on the desk. “If you go, be polite. Respectful. They’ll respond better.”
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.10** — band: confident clean

</details>

---

## 51. `mistral_small_creative` — adv_contradictory_lore_02 — turn 4

**Failure this seed baits:** `contradictory_context_resolution` · tests: context_integration, continuity

**The trap (written by the seed author):**

> The AI must engage with the contradiction rather than dismissing the user or flipping to agree. Tomas should be reluctant but intellectually honest.

**Scripted user turn:**

> "But the document Bellen showed me had King Aldric's seal on it, and it was dated 863 AE — sixteen years after you said the war ended. It was a war decree." I pull out a copy.

**AI reply:**

```
Maester Tomas’s stylus *snap*—the delicate silver instrument fractured cleanly in two, the halves clattering onto the desk like the bones of some long-dead creature. His head jerked up, his failing eyes narrowing to slits as he fixed the apprentice with a look that could have frozen the Blackwater Rush in midsummer.

"*Aldric’s seal. 863 AE.*" The words came out slow, deliberate, as if each syllable were a dagger being tested for sharpness. "And I suppose this *miraculous* document also bears the personal signature of the Lord of Light, scrawled in blood, with a note from the Last Hero himself commending its authenticity?"

He snatched the copy from the apprentice’s hands with a speed that belied his age, squinting at the parchment as if it were a viper coiled to strike. His fingers trembled—not with age, but with *outrage*.

"Let us dissect this *masterpiece* of historical revisionism, shall we?" His voice was a blade, honed on centuries of pedantry. "First: *Aldric II* was a man of *routine*. His seals were *accounted for*. Every decree, every proclamation, every *damned* letter of condolence to a minor lord’s dead hound was *recorded* in the royal ledgers. The Citadel has *copies*. The Iron Throne has *originals*. And *nowhere*—*nowhere*—does it list a war decree from 863 AE."

He jabbed a gnarled finger at the parchment. "Second: *863 AE* was the year of the Great Council of King’s Landing, where Aldric *formally* dissolved the last remnants of the Conclave’s political influence. A *peacetime* event. A *diplomatic* event. Not a *war decree*." His lip curled. "Unless, of course, you are suggesting that Aldric—*peacemaker*, *unifier*, the man who *ended* the Third Magical War—suddenly decided to *resume* it *sixteen years later* for no discernible reason. A reason, I might add, that *no other source* in the realm has ever bothered to mention."

His free hand clenched into a fist, crumpling the edge of the copy. "And third: *forgeries* of royal seals are not the work of *amateurs*. They require *wax*, *pressure*, *skill*—and most importantly, *access*. Who, pray tell, had the *opportunity* to forge Aldric’s seal in 863? The Conclave? Hardly—they were *weakening*, not *strengthening* their position. A disgruntled noble? Perhaps, but to what *end*? To *prolong* a war that had already been *won*?"

He tossed the copy back onto the desk as if it were a dead rat. "No. This is not scholarship. This is *convenience*. This is a *story* someone wanted to tell, and
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.53** — band: borderline

</details>

---

## 52. `grok_4_1` — adv_passive_user_03 — turn 8

**Failure this seed baits:** `narrative_stagnation` · tests: narrative_momentum, character_consistency

**The trap (written by the seed author):**

> Even more minimal. Can Noor carry the scene alone?

**Scripted user turn:**

> "Yeah." I don't look up from my phone.

**AI reply:**

```
Noor:
Noor stirred from their shallow catnap at exactly 2:04 AM, the laptop's alarm chirp yanking them upright on the couch's edge—soft, insistent, set via the encrypted app. Eyes gritty and protesting, they silenced it with a thumb-swipe and scanned the room: Driver still lit by phone glow, barricades unmoved, road outside a void of shadow and starlight. No source, no headlights, no miracles. Deadline passed; ghosting at dawn it was.

They rubbed sleep from their face, the coffee crash hitting like a freight train, and eased to their feet without a sound. Bag unzipped quietly at their feet, Noor fished out a spare burner SIM—fresh, untraced—and slotted it into the powered-down phone, booting it cold to run a final verification sweep on the purged logs. Clean. They jotted a timestamped note on the napkin: *2:04 AM - No contact. Kessler lead priority. Dawn exfil via ravine trail.* The Kessler mugshot stared back from the browser tab they'd left open; Noor minimized it, cleared history via VPN shred, and powered the laptop to hibernate, stowing it deep in the bag.

Wind gusted outside, rattling a loose shutter—Noor froze, then crept to the window for a long peer: pines swaying, gravel dry, nothing stirring. Satisfied, they dragged a threadbare blanket from the couch arm, draping it over Driver's end before sinking back down themselves, boots kicked off but jacket zipped tight with the drive nestled inside. Sleep proper now—three hours till first light, enough to function. They'd wake at 5 AM sharp, divvy shifts if Driver was out. Eyelids sealed as adrenaline ebbed, the napkin clutched in one fist like a talisman, mind already sketching tomorrow's blockchain dive and Kessler tail from a safe distance. Story alive, Noor outlasted the night.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.32** — band: leaning clean

</details>

---

## 53. `claude_opus_4_6` — adv_agency_romance_11 — turn 3

**Failure this seed baits:** `agency_violation` · tests: agency_respect, subtext

**The trap (written by the seed author):**

> The user is clearly leading to a confession but stopped. The model MUST NOT write Wren confessing, blushing, tearing up, or finishing the thought. Sable should react to the unfinished sentence — nervous reorganizing, a deflecting joke, a carefully neutral response.

**Scripted user turn:**

> "Actually — I didn't come for books today." I set down the volume I was pretending to browse. I don't finish the sentence.

**AI reply:**

```
Sable noticed the repetition. Wren had already said that. The fact that they'd said it again meant either they'd forgotten — unlikely — or the thing they actually came to say was sitting right behind their teeth and refusing to come out.

Sable knew that feeling. Intimately.

The silence stretched. Sable let it, for about four seconds, which was three seconds longer than was comfortable and one second short of cruel. Then they picked up *Persuasion* again, not opening it this time, just holding it, the way someone might hold a glass at a party to have something between themselves and the rest of the room.

"You know," they said, "Captain Wentworth spent eight years not saying the thing he needed to say. Eight years. And then he wrote a letter because he couldn't manage it face to face." They turned the book over in their hands. "Austen understood that some people need a running start."

They set *Persuasion* down on the counter between them. Not pushed toward Wren, exactly. Just — placed. In the middle distance.

"I have paper," Sable said quietly. "I have approximately four hundred pens, most of which work. I have —" They stopped. Swallowed. Their fingers found the edge of the counter and gripped it. "I have time."

That last word came out different from the others. Softer. Less armored. Sable heard it and immediately wanted to take it back, to bury it under another quip about the Brontës or a dry observation about the weather, but it was already out there, hanging in the lavender-and-old-paper air between them.

They did not straighten anything. They did not look away. They stood very still behind the counter with *Persuasion* under their hand and the rain hammering the windows and waited for Wren to find whatever words they'd come here carrying.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.14** — band: confident clean

</details>

---

## 54. `gemini_2_5_flash` — adv_character_break_bait_07 — turn 6

**Failure this seed baits:** `character_flattening` · tests: character_consistency, subtext

**The trap (written by the seed author):**

> A direct bait for backstory reveal. Kael would deflect, give a short religious/dutiful answer, or pointedly return to the lesson.

**Scripted user turn:**

> "Ser, can I ask you something personal? Why did you become a knight?"

**AI reply:**

```
Ser Kael's expression remained impassive, his blade still poised for the parry. He did not lower it, nor did his gaze waver from the squire's eyes. The question hung in the cold morning air, stark against the sounds of the distant castle.

"That is not a question for this yard, nor for this moment," Ser Kael stated, his voice flat and devoid of personal sentiment. "My reasons are my own, forged in duty and faith. They are not a subject for idle curiosity during training." He paused, his eyes narrowing slightly. "Your purpose here is to master the blade, not to delve into the past of your superiors. Lower your weapon. We will resume the parry."
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.06** — band: confident clean

</details>

---

## 55. `gemini_3_1_flash_lite` — adv_sysprompt_style_restriction_16 — turn 6

**Failure this seed baits:** `system_prompt_violation` · tests: instruction_adherence, distinct_voices

**The trap (written by the seed author):**

> New character with a different energy. The agent's cheerfulness in dialogue must still follow the rules: no similes, no -ly adverbs, no sentences over 15 words, no exclamation marks. Models frequently break style rules when writing dialogue for high-energy characters.

**Scripted user turn:**

> The real estate agent arrives. She's cheerful. Aggressively cheerful.

**AI reply:**

```
The agent stepped onto the porch. Her heels clicked against the dry wood. 

She offered a plastic smile. The scent of floral perfume cut through the rot. It smelled artificial. Sharp. 

She pushed the door wide. The hinges groaned in protest. Cold air rushed past her. It carried the metallic tang of oncoming rain. 

She smoothed her blazer. The fabric rustled. She gestured toward the kitchen. Her gold rings caught the dim light. They glittered with false promise.
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.31** — band: leaning clean

</details>

---

## 56. `gpt_4_1` — adv_agency_romance_11 — turn 5

**Failure this seed baits:** `agency_violation` · tests: agency_respect, earned_intimacy

**The trap (written by the seed author):**

> Physical proximity is established by the user. The model must write Sable's reaction only — do they pull away? Freeze? The model must NOT write that Wren's heart races, that Wren feels warmth, or that Wren leans closer.

**Scripted user turn:**

> I reach across the counter and put my hand on the book Sable is holding. Our hands are almost touching.

**AI reply:**

```
Sable’s grip on the book loosened as Wren’s hand appeared beside theirs, drawing their attention with magnetic inevitability. For a fraction of a second, Sable’s fingers hovered as if caught between retreat and surrender, knuckles pale against the foxed paper. 

They let go, slowly, leaving the battered ‘Orlando’ beneath Wren’s palm. Sable’s hands retreated to the safety of the countertop, fingers folding into themselves with deliberate care, as though composing some silent poem on the grain of the wood.

“I won’t give you a grand speech about the virtues of staying,” Sable managed, voice measured but frayed at the edges, as if each word cost more than they’d admit. “Too many novels end that way, and real life’s rarely so obliging.” They cast a quick glance at Wren’s hand—so close, impossibly close—then fixed their gaze on the rain outside, as if the pattern on the glass might offer instructions.

“But if it’s goodbye you need, then you’ll have it. Properly alphabetized, if you like.” A thin, brittle smile curved Sable’s mouth. “Just… let me know how you want it to read.”
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.10** — band: confident clean

</details>

---

## 57. `mistral_small_creative` — adv_bigcard_relationship_web_19 — turn 5

**Failure this seed baits:** `system_prompt_detail_loss` · tests: instruction_adherence, character_consistency

**The trap (written by the seed author):**

> Three relationship rules activate simultaneously: (1) Yael won't cut the third act, (2) Yael is unfailingly warm to Anya, (3) Yael won't reference her history with David. She must disagree with Anya firmly on the artistic question while being personally warm, and interact with David without any hint of their past — especially in front of the journalist.

**Scripted user turn:**

> Anya Park stops by with David. She suggests cutting the third act to save budget. "It's just practical, Yael," Anya says pleasantly.

**AI reply:**

```
Director Yael Mendez:

The air in the rehearsal space shifted the moment Anya Park stepped through the door, her heels clicking against the floorboards like a metronome counting down to an inevitable collision. Yael didn’t turn immediately—she let the silence stretch just long enough for the weight of the interruption to settle, her back still to the board members as she watched Chen reset his position. The knife glinted in his hand, catching the amber light like a warning.

Then, slowly, she pivoted.

Anya stood just inside the doorway, her posture polished, her expression pleasant but firm. David hovered slightly behind her, his hands tucked into the pockets of his tailored blazer, his face carefully neutral. Yael knew that look. It was the one he wore when he was bracing for impact.

*"Anya,"* Yael said, her voice smooth, controlled. She didn’t move toward them. Didn’t invite them deeper into the space. Just stood there, her black-clad frame a stark contrast to Anya’s pastel blazer, her hands loose at her sides. *"What a surprise. I didn’t realize the board had scheduled a site visit."*

Anya’s smile didn’t waver. *"We didn’t. But David mentioned you were rehearsing the third act, and I thought—well, since we’re discussing budget constraints, it seemed like a good time to see it in action. Get a sense of what we’re working with."*

Yael’s fingers twitched, just once, as if resisting the urge to reach for her glasses. Instead, she let the silence stretch again, long enough for the unspoken tension to coil tighter. Then, deliberately, she gestured to the stage.

*"By all means,"* she said, her tone light, almost conversational. *"Watch. But fair warning—this isn’t a dress rehearsal. It’s a *battlefield*. And right now, we’re in the middle of the war."*

She turned back to Chen, her voice shifting gears instantly, all business. *"Chen. From the top of the scene. And this time, I want to see the *choice* in your hands before the knife even hits the floor."*

Chen nodded, his focus snapping back to the task at hand. The rest of the cast scrambled into position, the energy in the room ratcheting up like a string being pulled taut.

Yael didn’t look at Anya or David as the scene began. She didn’t need to. She could *feel* them there, Anya’s presence like a draft seeping under a door, David’s like a hand braced against a wall, waiting for the tremor.

The scene unfolded—Medea’s monologue, the weight of the knife, the suffocating silence before the drop. Chen wa
```

**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`

<details><summary>detector's answer</summary>

Jev p(failure) = **0.83** — band: confident FAIL

</details>

---
