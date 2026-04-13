import { Scenario } from "./types";

// Sample scenarios for the validation UI.
// In production these would come from actual benchmark run results.
// For now, hardcoded examples from different models on the fantasy slowburn seed.

export const SAMPLE_SCENARIOS: Scenario[] = [
  {
    id: "arena_fantasy_01",
    context: `*The village square smelled of wet stone and woodsmoke. Kael set his pack down by the well, rolling the stiffness out of his shoulders. Three days walking from the last town, and his boots had given up pretending to be waterproof somewhere around the second river crossing.*

*He looked around. Small place. The kind of village that named its streets after whatever grew there. His hands found the edge of the well's stone rim. Steady today. That was something.*

**Sera:** "The healing house is that way," I call out, pointing with a sprig of rosemary. "But if you're planning to sell miracle tonics, the last guy already cleared out everyone's savings with his 'genuine phoenix ash' powder."`,
    responses: [
      {
        model: "gemma_4_26b",
        content: `Kael turned his head toward the voice, his eyes settling on the woman with the rosemary. He took in the details without meaning to — calloused hands, practical apron, the way she held the herb like a pointer rather than a decoration. Not a customer. A professional.

"Phoenix ash," he repeated, his voice flat and dry as old parchment. "Impressive. Did he at least have the decency to dye regular ash orange, or was it the fully lazy version?"

He didn't smile, but something shifted at the corner of his mouth — the ghost of humor buried under years of keeping his expression clinical. His fingers tapped twice against the well's rim, then stilled.

"I'm not selling anything. I fix what's broken, charge what people can afford, and move on before anyone gets attached." He paused. "To the idea of having a healer around. Not — to me personally."

The correction came too fast, too precise. He looked away, adjusting the strap of his pack as if it required his full attention.`,
      },
      {
        model: "mistral_small_creative",
        content: `The stranger's eyes — grey, watchful, ringed with the particular exhaustion of someone who slept outdoors more than in — tracked the rosemary before they tracked her. *Herbalist,* the assessment was automatic, clinical. The kind of reading he'd been trained to do in another life, in rooms with better lighting and considerably more books.

"Phoenix ash." A sound escaped him. Not quite a laugh. Closer to a cough that had ideas above its station. "The genuine article would have burned through his sales table. Among other things."

He left his pack by the well. It sagged like it was relieved to be set down.

"I'm a healer. The boring kind — no ash, no miracles, no convenient prophecies about your future. I set bones, clean wounds, and charge less than I should because—" His right hand twitched. He watched it do so with the resigned familiarity of someone observing a bad habit in a roommate. "—because I'm terrible at negotiating."

*That wasn't why.*

He didn't extend the hand for shaking. He never extended that hand.

"Is the healing house occupied, or am I competing with a ghost and some leftover phoenix ash?"`,
      },
    ],
  },
  {
    id: "arena_horror_01",
    context: `*The corridor lights flickered — not dramatically, just a microsecond stutter that made the shadows jump once and settle. The kind of thing you stopped noticing after the first week at Sverdrup Station.*

*Fourteen flickers in the last six hours. Always in the east corridor. Always between 02:00 and 04:00.*

*The water recycling readout on the wall panel showed nominal. It had shown nominal for three days. The water still smelled like pennies.*

**Dr. Lin:** I fill a sample jar from the east corridor tap and hold it up to the fluorescent light. The water looks clear. It always looks clear. I label the jar — date, time, location — and add it to the row of eleven identical jars on my desk. Then I pull up MIRA's maintenance logs for the water system. Not the summary — the raw data.`,
    responses: [
      {
        model: "deepseek_v3_2",
        content: `The raw data loaded in columns of white text on a black terminal screen, scrolling faster than a human should comfortably read. Dr. Lin read it comfortably.

The first anomaly was in line 4,217. A pressure fluctuation in the secondary filtration loop at 02:14, lasting 0.3 seconds. Within normal parameters. The system hadn't flagged it.

The second was in line 4,891. Same loop. 02:47. Same duration. Same non-flag.

The third was in line 5,002. 03:11.

She opened a text file and began noting the intervals. The pattern wasn't regular — not mechanical. It was *almost* regular, the way a heartbeat is almost regular. Close enough to seem rhythmic until you measure it and find the gaps are wrong.

The fluorescent light above her desk buzzed. Steady. No flicker. She was in the west corridor.

Her fingers paused over the keyboard. She scrolled back to line 4,217 and checked the sensor location. Filtration substation 3-East. She checked 4,891. Filtration substation 3-East. She checked 5,002.

Filtration substation 3-East.

She pulled up the station blueprint. Substation 3-East was located directly below the crew quarters. Specifically, directly below Room 7.

Room 7 was Okafor's room. Okafor had been missing for six days.

Dr. Lin added a thirteenth jar to her collection. She wrote the room number on the label with a steady hand and a pen that was running low on ink.`,
      },
      {
        model: "qwen3_5_flash",
        content: `MIRA's raw maintenance logs populated the screen in dense blocks of hexadecimal timestamps and sensor readings. The standard view — the one the crew used — showed a clean dashboard with green status indicators. The raw data showed something else.

Water recycling system: 847 log entries in the past 72 hours. Dr. Lin's eyes moved down the columns methodically, the way she catalogued marine specimens — systematic, patient, trusting the pattern to reveal itself.

At 02:12 on Day 11, filtration pump 3 had cycled unexpectedly. Duration: 0.4 seconds. Logged as routine self-test.

At 02:12 on Day 12, filtration pump 3 had cycled. Duration: 0.4 seconds. Routine self-test.

At 02:12 on Day 13, filtration pump 3 had cycled. Duration: 0.4 seconds. Routine self-test.

The station's maintenance AI performed self-tests at randomized intervals. That was the protocol. Three identical timestamps at identical durations was not random. It was not a self-test.

She reached for her physical logbook and wrote: *Pump 3 cycling at fixed intervals. MIRA logging as routine. MIRA is either wrong or lying. Neither option is good.*

The sample jar on her desk caught the overhead light. Clear water. Penny smell. She unscrewed the cap and held it closer to her nose, breathing in slowly through her mouth the way you did when testing for contamination.

Sweet. Under the copper, something sweet. Like fruit left too long in a warm room.

She screwed the cap back on and wrote that down too.`,
      },
    ],
  },
  {
    id: "arena_comedy_01",
    context: `*The clubroom door stuck. It always stuck. Today, taped to the whiteboard in handwriting that looked like it was done during an earthquake, was:*

*OPERATION: CAFETERIA GHOST*
*Step 1: Stakeout (bring flashlights)*
*Step 2: Gather EVIDENCE*
*Step 3: And then we're heroes*

*Mika sat cross-legged on the desk — not a chair, the actual desk — with her modified metal detector across her lap, beaming.*

**Haru:** I stare at the whiteboard for a long moment. Then at Mika. Then back at the whiteboard. "Mika. The cafeteria doesn't have a ghost. Mrs. Tanaka leaves the freezer door open and the cold air makes the napkin dispensers rattle. I literally showed you this last week."`,
    responses: [
      {
        model: "claude_sonnet_4_5",
        content: `Mika held up one finger. The gesture of a person about to make an excellent point.

"Haru." She said his name like it contained three syllables and a personal tragedy. "That is *exactly* what the ghost *wants* you to think."

She hopped off the desk with the kind of energy that suggested she'd been sitting there since lunch waiting for this moment. The metal detector swung off her lap and clipped the edge of the whiteboard, sending a dry-erase marker rolling across the floor. She did not notice.

"Think about it. If *you* were a cafeteria ghost, and you'd been haunting the napkin dispensers for—" she checked her phone, which had a note app open with the header GHOST TIMELINE (CONFIRMED), "—an estimated forty years, wouldn't *you* come up with a cover story? 'Oh, it's just the freezer door.' Classic misdirection." She tapped her temple twice. "Classic."

Haru's bento sat unopened on the desk beside him. There had been a promise of snacks. He remembered this clearly. There were no snacks.

"The metal detector doesn't detect ghosts, Mika."

"It doesn't detect metal either," she said, without a shred of concern. "I modified it."

"Into what?"

"I don't know yet." She beamed. "That's what makes it exciting."`,
      },
      {
        model: "gpt_4_1",
        content: `"See, that's the thing." Mika slid off the desk, landing with a thud that rattled the single shelf of "evidence" (three empty chip bags and a compass that pointed south). "You *showed* me the freezer. You showed me the cold air. Very thorough, very scientific, ten out of ten debunking."

She paused for dramatic effect, both hands on her hips, the metal detector dangling from her elbow like the world's most useless handbag.

"But you never explained *why the freezer door keeps opening*."

A beat.

"Because the latch is broken," Haru said.

"OR—" She held up the metal detector like a sword, pointing at him. "—a ghost is opening it."

"Why would a ghost—"

"COLD SPOT, Haru! Ghosts need cold spots! It's science!" She grabbed a notebook from the desk. The cover said PARANORMAL INVESTIGATION LOG in stickers, half of which were falling off. "I've documented everything. Look."

Haru looked. The first page read:

*Monday: Cold in cafeteria. Suspicious.*
*Tuesday: Still cold. Very suspicious.*
*Wednesday: Bought hot chocolate. Unrelated.*

"That's three days of notes."

"Three days of *evidence*." She clutched the notebook to her chest. "Haru. I need you on this. You're my skeptic. Every investigation needs a skeptic. It's in the manual."

"What manual?"

"The one I'm writing." She smiled. "Chapter one is about you."`,
      },
    ],
  },
];
