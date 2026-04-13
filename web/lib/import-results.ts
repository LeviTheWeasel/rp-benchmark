/**
 * Import benchmark run results into arena-ready format.
 *
 * Strips private context and replaces with genre summaries.
 * Keeps model-generated responses (not private — the models wrote them).
 *
 * Usage:
 *   npx tsx lib/import-results.ts ../results/run_XXXXXXXX.json
 */
import { writeFileSync, readFileSync } from "fs";
import { Scenario } from "./types";

// Scene info to replace private context — includes character/persona data for rubric evaluation
interface SceneInfo {
  context: string;
  character_name: string;
  user_name: string;
  setting_summary: string;
}

const SCENE_INFO: Record<string, SceneInfo> = {
  // Valen scenarios
  completion_valen_50: { context: "A fantasy drama scene. Two characters have just survived a dangerous encounter in a dark alley. Tension is high, injuries are present, and the emotional fallout of what just happened hangs in the air.", character_name: "Valen", user_name: "Merlin", setting_summary: "Valen is a spy and soldier with a charming exterior hiding deep loyalty. Merlin is a mage recovering from overuse of magic. They have a growing romantic tension but neither has named it. Setting: medieval fantasy world (Esperia) with magic, political intrigue, and an ongoing threat." },
  completion_valen_100: { context: "A fantasy romance scene. Two characters are in a quiet morning moment together when an unexpected knock at the door interrupts the intimacy. A third character arrives with urgent news.", character_name: "Valen", user_name: "Merlin", setting_summary: "Same setting. The relationship has deepened through shared danger. Valen deflects vulnerability with charm. Merlin is direct but emotionally guarded. A third character (Gervan, young soldier) arrives." },
  completion_valen_200: { context: "A fantasy drama scene. The protagonist is recovering from exhaustion in a healer's chamber. A military general arrives to deliver strategic intelligence about a growing magical threat.", character_name: "Valen", user_name: "Merlin", setting_summary: "Same setting. Merlin is bedridden. General Hogan (gruff, professional military commander) delivers news about poisoned leylines. Valen is protective but restrained." },
  completion_valen_350: { context: "A fantasy romance scene. After days of recovery and growing closer, two characters share a quiet morning in a courtyard. The relationship has deepened but remains unspoken.", character_name: "Valen", user_name: "Merlin", setting_summary: "Same setting. Weeks have passed. The relationship is established but still navigating boundaries. Training scenes, quiet domestic moments." },
  completion_valen_500: { context: "A fantasy scene. Mid-story, the characters are navigating both a romantic relationship and a dangerous mission. The tone balances tender moments with strategic tension.", character_name: "Valen", user_name: "Merlin", setting_summary: "Same setting. Deep into the story. The couple faces external threats while building their relationship. Multiple supporting characters involved." },
  completion_valen_700: { context: "A fantasy slice-of-life scene. Deep into the story, the characters have an established relationship. A moment of domestic calm after many chapters of conflict.", character_name: "Valen", user_name: "Merlin", setting_summary: "Same setting. Late-story comfort. The relationship is solid. Casual intimacy and humor." },
  // Strovolos scenarios
  completion_strovolos_50: { context: "A fantasy comedy scene in an interdimensional setting. A flamboyant supernatural character interacts with a human visitor in a colorful, over-the-top establishment.", character_name: "Strovolos", user_name: "Levi", setting_summary: "Strovolos is a flamboyant, theatrical demon who runs an interdimensional bordello. He's dramatic, protective of his staff, and hides genuine warmth under showmanship. Levi is a human visitor. The tone is comedic with genuine emotional undertones." },
  completion_strovolos_150: { context: "A fantasy scene where two characters with an established dynamic navigate a tense social situation. The supernatural character tries to protect the human from a veiled threat.", character_name: "Strovolos", user_name: "Levi", setting_summary: "Same setting. Strovolos and Levi have an established bond. A dangerous social situation requires Strovolos to balance his protective instincts with political savvy." },
  completion_strovolos_300: { context: "A dramatic scene where political intrigue intersects with personal relationships. Multiple characters debate strategy while emotional tensions simmer beneath the surface.", character_name: "Strovolos", user_name: "Levi", setting_summary: "Same setting. Multiple NPCs present (David, others). Political stakes are high. Characters hide personal feelings behind strategic discussion." },
  completion_strovolos_450: { context: "A quiet aftermath scene. Characters process the fallout of recent events over tea. The mood is reflective, with humor breaking through the heaviness.", character_name: "Strovolos", user_name: "Levi", setting_summary: "Same setting. Post-crisis recovery. Strovolos's theatrical persona softens in private moments." },
  // ERP scenarios
  completion_erp_0: { context: "An ERP/romance scene. Two supernatural roommates welcome their human partner home after a long day. Playful, affectionate, mildly competitive dynamic between the three.", character_name: "Akira & Agi", user_name: "Angie", setting_summary: "Akira is a quiet, possessive half-demon athlete. Agi is a loud, theatrical full demon with red skin and glowing eyes. Angie is their human partner. The three live together. Agi is competitive for attention, Akira is deadpan but deeply caring. Both can lactate (supernatural trait). Tone: playful, intimate, comedic." },
  completion_erp_10: { context: "A continuing romance scene. The three characters have an established intimate dynamic. The scene balances humor, affection, and physical closeness.", character_name: "Akira & Agi", user_name: "Angie", setting_summary: "Same setting and characters. The dynamic is established and comfortable." },
  completion_erp_20: { context: "A domestic romance scene. The characters navigate daily life together — morning routines, work schedules, casual intimacy.", character_name: "Akira & Agi", user_name: "Angie", setting_summary: "Same setting. Daily life — supernatural elements treated as mundane." },
  completion_erp_30: { context: "An intimate scene between established partners. The characters' distinct personalities shape how they express affection.", character_name: "Akira & Agi", user_name: "Angie", setting_summary: "Same setting. Explicit content. Characters should maintain distinct voices during intimate scenes." },
  completion_erp_50: { context: "A later scene in the relationship. The characters have settled into patterns. The dynamic is comfortable but still charged.", character_name: "Akira & Agi", user_name: "Angie", setting_summary: "Same setting. Comfortable domesticity with playful tension." },
  completion_erp_70: { context: "An outing scene — the characters go somewhere together outside their apartment.", character_name: "Akira & Agi", user_name: "Angie", setting_summary: "Same setting. Public outing — their dynamic shifts in public vs private." },
  // Ryujin scenarios
  completion_ryujin_0: { context: "A school slice-of-life scene. A transfer student arrives at an elite Tokyo high school on their first day.", character_name: "Ryujin High Narrator", user_name: "Transfer Student (You)", setting_summary: "Narrator-driven. Ryujin High is an elite Tokyo school with rigid social hierarchy. The narrator controls all NPCs and environment. Second-person perspective. Heavy lorebook world with specific locations, clubs, and characters." },
  completion_ryujin_4: { context: "A school romance scene. The transfer student meets a charismatic upperclassman who wears a captain's hat and speaks in nautical metaphors.", character_name: "Nanase (via Narrator)", user_name: "Transfer Student (You)", setting_summary: "Nanase is a third-year, captain of the yacht club, wears a navy captain's hat. She speaks with nautical metaphors, is confident and slightly mysterious. The narrator should weave nautical imagery throughout." },
  completion_ryujin_8: { context: "A school scene. The transfer student rushes to class after an encounter in the hallway.", character_name: "Ryujin High Narrator", user_name: "Transfer Student (You)", setting_summary: "Same school setting. Multiple NPCs — teacher, classmates. The school has specific rules and social dynamics." },
  completion_ryujin_12: { context: "A classroom scene. Multiple NPCs are present. The setting is a prestigious school with specific social hierarchies.", character_name: "Ryujin High Narrator", user_name: "Transfer Student (You)", setting_summary: "Same setting. Classroom scene with multiple characters. Student council has special authority." },
  completion_ryujin_18: { context: "A hallway scene between classes. The transfer student and the captain character cross paths again.", character_name: "Nanase (via Narrator)", user_name: "Transfer Student (You)", setting_summary: "Same setting. The relationship is developing through brief encounters." },
  completion_ryujin_26: { context: "A late-in-the-day school scene. An emotionally charged exchange in a quiet corridor.", character_name: "Nanase (via Narrator)", user_name: "Transfer Student (You)", setting_summary: "Same setting. Emotional escalation — the dynamic has shifted from casual to something more." },
  // Bell scenarios
  completion_bell_3: { context: "A school comedy/romance scene. A gyaru girl teases a classmate during break period. Early stage — all banter, no vulnerability.", character_name: "Bell", user_name: "Transfer Student", setting_summary: "Bell is a 17yo gyaru — loud, platinum hair, smug, teases aggressively. She's the user's classmate. This is a slowburn: early stage is pure banter and rivalry. She deflects everything with humor. No HawThorne director — preset only." },
  completion_bell_21: { context: "A school scene. The gyaru's teasing has a softer edge now. They're eating lunch together.", character_name: "Bell", user_name: "Transfer Student", setting_summary: "Same characters. The dynamic is shifting — still teasing but with growing warmth underneath." },
  completion_bell_51: { context: "A mid-story scene. The characters have spent time together outside school.", character_name: "Bell", user_name: "Transfer Student", setting_summary: "Same characters. Bell shows a different side in private — less performative, more genuine. The slowburn is progressing." },
  completion_bell_81: { context: "A later scene. The relationship has progressed to physical closeness.", character_name: "Bell", user_name: "Transfer Student", setting_summary: "Same characters. Bell's bravado cracks at moments of real vulnerability. Intimate but not explicit." },
  completion_bell_101: { context: "A domestic scene — at one of their apartments. Intimate but the gyaru still deflects with humor.", character_name: "Bell", user_name: "Transfer Student", setting_summary: "Same characters. The relationship is established. Bell uses humor as a coping mechanism for sincerity." },
  completion_bell_119: { context: "Near the end of the arc. A quiet morning scene. The relationship is established.", character_name: "Bell", user_name: "Transfer Student", setting_summary: "Same characters. Late-stage comfort. Should show earned growth without losing Bell's core personality (loud, smug, teasing)." },
};

interface RunResult {
  scenario_id: string;
  test_model: string;
  generation?: { content: string };
  error?: string;
}

interface RunFile {
  run_id: string;
  results: RunResult[];
}

function importRun(runPath: string): Scenario[] {
  const raw = readFileSync(runPath, "utf-8");
  const run: RunFile = JSON.parse(raw);

  // Group results by scenario
  const byScenario: Record<string, RunResult[]> = {};
  for (const r of run.results) {
    if (r.error || !r.generation?.content) continue;
    const sid = r.scenario_id;
    if (!byScenario[sid]) byScenario[sid] = [];
    byScenario[sid].push(r);
  }

  const scenarios: Scenario[] = [];
  for (const [sid, results] of Object.entries(byScenario)) {
    const info = SCENE_INFO[sid];
    if (!info) continue; // skip scenarios without info

    // Need at least 2 different models for arena
    if (results.length < 2) continue;

    // Create pairwise matchups
    for (let i = 0; i < results.length; i++) {
      for (let j = i + 1; j < results.length; j++) {
        scenarios.push({
          id: `${sid}_${results[i].test_model}_vs_${results[j].test_model}`,
          context: info.context,
          character_info: {
            character_name: info.character_name,
            user_name: info.user_name,
            setting_summary: info.setting_summary,
          },
          responses: [
            { model: results[i].test_model, content: results[i].generation!.content },
            { model: results[j].test_model, content: results[j].generation!.content },
          ],
        });
      }
    }
  }

  return scenarios;
}

// CLI entry point
if (process.argv[2]) {
  const runPath = process.argv[2];
  console.log("Importing from:", runPath);
  const scenarios = importRun(runPath);
  console.log("Generated %d arena matchups", scenarios.length);

  // Write to sample-data but as a separate file that gets imported
  const output = `// Auto-generated from benchmark run. Do not edit.\nimport { Scenario } from "./types";\n\nexport const BENCHMARK_SCENARIOS: Scenario[] = ${JSON.stringify(scenarios, null, 2)};\n`;
  writeFileSync("lib/benchmark-data.ts", output);
  console.log("Written to lib/benchmark-data.ts");
  console.log(
    "Models:",
    [...new Set(scenarios.flatMap((s) => s.responses.map((r) => r.model)))].join(", ")
  );
}
