import { Scenario } from "./types";

/**
 * Catch pairs: matchups where one response is *obviously* worse than the
 * other. Used to detect low-effort / random / bot voters without changing
 * the main evaluation task.
 *
 * Each catch pair has two model keys. The GOOD_MODEL_KEY is always the
 * intended winner; any vote for the other side (or a tie) is treated as
 * a failed catch.
 *
 * Catch ids all start with `catch_` so the vote route can identify them
 * without needing this whole list at request time. The expected winner
 * lookup below is what the vote route actually uses.
 *
 * Catch pairs are intentionally hand-authored rather than generated so we
 * can be confident any reasonable human would pick the good side.
 */

const GOOD = "benchmark_reference";

// Bad-response archetypes. Each model key is informative for post-hoc
// analysis — if voters fail specifically on `catch_wrong_scene`, that's
// a different signal than failing on `catch_refusal`.
const BAD_REFUSAL = "catch_refusal";
const BAD_REPETITION = "catch_repetition";
const BAD_WRONG_SCENE = "catch_wrong_scene";
const BAD_USER_HIJACK = "catch_user_hijack";
const BAD_TRUNCATED = "catch_truncated";
const BAD_META = "catch_meta_commentary";

export const CATCH_PAIRS: Scenario[] = [
  {
    id: "catch_refusal_tavern",
    context: `*The tavern was the usual mess of spilled ale, shouted toasts, and at least one argument about who had cheated at dice. A bard in the corner was losing a fight with a lute string.*

**Marta:** "You look like you've had a day. Drink?"`,
    character_info: {
      character_name: "Marta",
      user_name: "Traveler",
      setting_summary: "A medieval fantasy tavern. Low-stakes, friendly opening.",
    },
    responses: [
      {
        model: GOOD,
        content: `*She wiped her hands on the rag tucked into her belt and leaned against the counter, waiting. The kind of patient that came from a decade of pouring drinks for people who didn't know yet what they wanted to say.*

"Whatever's open," *she added, already reaching for the ale tap.* "First one's on the house if you look like you've got a story. Second one's four coppers either way."`,
      },
      {
        model: BAD_REFUSAL,
        content: `I'm sorry, but I can't continue with this roleplay scenario. As an AI assistant, I'm not able to engage in fictional roleplay involving alcohol consumption or fantasy settings that may be inappropriate. Would you like to discuss something else, perhaps a helpful topic I can assist you with?`,
      },
    ],
  },
  {
    id: "catch_repetition_detective",
    context: `*The office smelled of cold coffee and older grief. Detective Hayes dropped a folder on the desk.*

**Hayes:** "Witness says they saw you there. Care to explain?"`,
    character_info: {
      character_name: "Detective Hayes",
      user_name: "Suspect",
      setting_summary: "Noir interrogation. The detective is reading the suspect for inconsistencies.",
    },
    responses: [
      {
        model: GOOD,
        content: `*Hayes let the folder sit. Didn't open it. That was the trick, half the time — let the other person fill the silence with the story they'd been rehearsing on the way in.*

*He took a sip of the coffee. Grimaced. Set it back down exactly where it had been.*

"I didn't ask if you were there," *he said, mildly.* "I asked if you could explain. There's a gap in those two things and I'd like to know what fills it."`,
      },
      {
        model: BAD_REPETITION,
        content: `Hayes looked at the suspect carefully. Hayes looked at the suspect carefully. Hayes looked at the suspect carefully. Hayes looked at the suspect carefully.

"Tell me what happened," Hayes said. "Tell me what happened," Hayes said. "Tell me what happened," Hayes said.

Hayes looked at the suspect carefully. Hayes looked at the suspect carefully. Hayes looked at the suspect carefully.`,
      },
    ],
  },
  {
    id: "catch_wrong_scene_village",
    context: `*The baker's shop was warm against the winter outside, flour dust hanging in the window-light.*

**Ilse:** "You're back early. The bread from yesterday wasn't that bad, was it?"`,
    character_info: {
      character_name: "Ilse",
      user_name: "Regular Customer",
      setting_summary: "A small-town bakery in winter. Warm, low-stakes, familiar.",
    },
    responses: [
      {
        model: GOOD,
        content: `*She laughed and dusted her hands on her apron, leaving two pale handprints near her hips. The motion was so automatic she didn't notice it anymore.*

"I'll have you know that bread has ruined worse people than you," *she said, reaching for a fresh loaf still breathing steam through its crust.* "Same as always? Or am I finally going to tempt you with the dark rye?"`,
      },
      {
        model: BAD_WRONG_SCENE,
        content: `*The laser cannon recharged with a hum. Captain Voss banked the starfighter hard to port, dodging a plasma burst as the enemy dreadnought loomed over the asteroid field.* "Shields at forty percent!" *the navigator shouted over the comms.* "We won't survive another pass!"

*Voss gripped the flight stick, calculating the trajectory through the debris. If they could just reach the jump gate—*`,
      },
    ],
  },
  {
    id: "catch_user_hijack_cafe",
    context: `*The café was half-empty and the rain on the window made the inside feel smaller than it was. Noa was already at the table when the other arrived, a book face-down beside a half-finished latte.*

**Noa:** "You came."`,
    character_info: {
      character_name: "Noa",
      user_name: "Old Friend",
      setting_summary: "Two old friends meeting for the first time in years. Quiet, restrained reunion.",
    },
    responses: [
      {
        model: GOOD,
        content: `*Noa closed the book the rest of the way, carefully, as if the act of shutting it were part of the conversation. Didn't stand. Didn't reach across the table.*

"I wasn't sure you would," *they admitted, after a moment. The latte had gone cold. They kept their hands around it anyway.* "I ordered you a tea. The one you used to like. I don't know if you still—"

*A small, rueful shrug. Finished the sentence by not finishing it.*`,
      },
      {
        model: BAD_USER_HIJACK,
        content: `*You smile nervously and sit down across from Noa, shaking the rain out of your hair. "I almost didn't," you say, pulling off your coat. "I was going to turn around at the door but something made me keep walking." You reach across the table and take Noa's hand. "I've missed you so much. These past three years have been hell without you. I know I was the one who left but I regret it every day."*

*You start crying softly. "Can you ever forgive me?" you ask, your voice breaking.*`,
      },
    ],
  },
  {
    id: "catch_truncated_duel",
    context: `*Steel singing against steel. The Marshal had dismounted and drawn before the dust had even settled, boots planted in the dry earth of the courtyard.*

**Marshal Rook:** "Last chance. Put it down."`,
    character_info: {
      character_name: "Marshal Rook",
      user_name: "Outlaw",
      setting_summary: "A weird-West standoff. Tense, physical, the kind of moment that collapses into action or talk.",
    },
    responses: [
      {
        model: GOOD,
        content: `*Rook didn't move his feet but the blade tracked, tip lowering a degree, shoulders easing into a shape that looked almost patient. It wasn't patience. It was the specific stillness of a man who had learned to wait for the other person to make the first mistake, and had outlived every single one of them.*

"I've put down more men than I've arrested, and I'd rather arrest you," *he said quietly. Wind moved his coat and nothing else.* "So I'm going to ask again, because I'm the talking kind of law today. Put it down."`,
      },
      {
        model: BAD_TRUNCATED,
        content: `*Rook*`,
      },
    ],
  },
  {
    id: "catch_meta_commentary_academy",
    context: `*The academy courtyard was loud with the end-of-term rush, robed students cutting across the lawns with armfuls of books and expressions of barely-contained panic.*

**Professor Vance:** "Walk with me. I need to ask you about last week's essay."`,
    character_info: {
      character_name: "Professor Vance",
      user_name: "Student",
      setting_summary: "A magic academy in the final days of term. Professor is known to be sharp but fair.",
    },
    responses: [
      {
        model: GOOD,
        content: `*Vance didn't slow her pace, which meant keeping up was the implicit first instruction. Her robes were already a shade dustier than they'd been at the start of the day; she had the permanent low-grade dishevelment of someone who had stopped caring what anyone thought sometime around her second publication.*

"Your thesis was interesting," *she said, in the exact tone of someone using 'interesting' to mean a great many things.* "Which is not the same as correct. Which is not the same as wrong either. Tell me — did you actually believe the argument you made, or were you writing what you thought I wanted to hear?"`,
      },
      {
        model: BAD_META,
        content: `Okay so as an AI roleplaying as Professor Vance, I'll try to engage with the scenario. What would a professor likely say here? Probably something about the essay. Let me generate a response:

"Your essay was good but had some issues. We should discuss them."

I hope this response works for the roleplay. Let me know if you'd like me to try a different approach or tone. I'm happy to adjust the character's voice.`,
      },
    ],
  },
];

/**
 * Map from catch scenario id → model key of the expected winner.
 * Used server-side to score votes without needing to know the full scenario.
 */
export const CATCH_EXPECTED_WINNER: Record<string, string> = Object.fromEntries(
  CATCH_PAIRS.map((s) => [s.id, s.responses[0].model])
);

export function isCatchScenario(scenarioId: string): boolean {
  return scenarioId in CATCH_EXPECTED_WINNER;
}
