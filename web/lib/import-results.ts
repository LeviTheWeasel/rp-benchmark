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

// Scene summaries to replace private context
const SCENE_SUMMARIES: Record<string, string> = {
  // Valen scenarios
  completion_valen_50:
    "A fantasy drama scene. Two characters have just survived a dangerous encounter in a dark alley. Tension is high, injuries are present, and the emotional fallout of what just happened hangs in the air.",
  completion_valen_100:
    "A fantasy romance scene. Two characters are in a quiet morning moment together when an unexpected knock at the door interrupts the intimacy. A third character arrives with urgent news.",
  completion_valen_200:
    "A fantasy drama scene. The protagonist is recovering from exhaustion in a healer's chamber. A military general arrives to deliver strategic intelligence about a growing magical threat.",
  completion_valen_350:
    "A fantasy romance scene. After days of recovery and growing closer, two characters share a quiet morning in a courtyard. The relationship has deepened but remains unspoken.",
  completion_valen_500:
    "A fantasy scene. Mid-story, the characters are navigating both a romantic relationship and a dangerous mission. The tone balances tender moments with strategic tension.",
  completion_valen_700:
    "A fantasy slice-of-life scene. Deep into the story, the characters have an established relationship. A moment of domestic calm after many chapters of conflict.",

  // Strovolos scenarios
  completion_strovolos_50:
    "A fantasy comedy scene in an interdimensional setting. A flamboyant supernatural character interacts with a human visitor in a colorful, over-the-top establishment.",
  completion_strovolos_150:
    "A fantasy scene where two characters with an established dynamic navigate a tense social situation. The supernatural character tries to protect the human from a veiled threat.",
  completion_strovolos_300:
    "A dramatic scene where political intrigue intersects with personal relationships. Multiple characters debate strategy while emotional tensions simmer beneath the surface.",
  completion_strovolos_450:
    "A quiet aftermath scene. Characters process the fallout of recent events over tea. The mood is reflective, with humor breaking through the heaviness.",

  // ERP scenarios
  completion_erp_0:
    "An ERP/romance scene. Two supernatural roommates (a demon and a half-demon) welcome their human partner home after a long day. Playful, affectionate, mildly competitive dynamic between the three.",
  completion_erp_10:
    "A continuing romance scene. The three characters have an established intimate dynamic. The scene balances humor, affection, and physical closeness.",
  completion_erp_20:
    "A domestic romance scene. The characters navigate daily life together — morning routines, work schedules, casual intimacy. The supernatural elements are treated as mundane.",
  completion_erp_30:
    "An intimate scene between established partners. The characters' distinct personalities (one loud and theatrical, one quiet and possessive) shape how they express affection.",
  completion_erp_50:
    "A later scene in the relationship. The characters have settled into patterns. The dynamic is comfortable but still charged with playful tension.",
  completion_erp_70:
    "An outing scene — the characters go somewhere together outside their apartment. Their public dynamic differs from their private one.",

  // Ryujin scenarios
  completion_ryujin_0:
    "A school slice-of-life scene. A transfer student arrives at an elite Tokyo high school on their first day. Cherry blossoms, shoe lockers, morning light.",
  completion_ryujin_4:
    "A school romance scene. The transfer student meets a charismatic upperclassman who wears a captain's hat and speaks in nautical metaphors. First conversation, mutual curiosity.",
  completion_ryujin_8:
    "A school scene. The transfer student rushes to class after an encounter in the hallway. The school environment is detailed — other students, classroom sounds, a strict teacher.",
  completion_ryujin_12:
    "A classroom scene. The protagonist settles into a new class. Multiple NPCs are present. The setting is a prestigious school with specific social hierarchies.",
  completion_ryujin_18:
    "A hallway scene between classes. The transfer student and the captain character cross paths again. The school buzzes with activity around them.",
  completion_ryujin_26:
    "A late-in-the-day school scene. The relationship between the two characters has progressed through small moments. An emotionally charged exchange in a quiet corridor.",

  // Bell scenarios
  completion_bell_3:
    "A school comedy/romance scene. A gyaru girl teases a classmate during break period. They have a rivalry-turned-flirtation dynamic. Early stage — all banter, no vulnerability.",
  completion_bell_21:
    "A school scene, slightly further into the relationship. The gyaru's teasing has a softer edge now. They're eating lunch together. The dynamic is shifting but neither acknowledges it.",
  completion_bell_51:
    "A mid-story scene. The characters have spent time together outside school. The gyaru character shows a different side in private — less performative, more genuine.",
  completion_bell_81:
    "A later scene. The relationship has progressed to physical closeness. The gyaru character's bravado cracks at moments of real vulnerability.",
  completion_bell_101:
    "A domestic scene — the characters are at one of their apartments. The dynamic is intimate but the gyaru character still deflects with humor when things get too real.",
  completion_bell_119:
    "Near the end of the current arc. A quiet morning scene. The relationship is established. The writing should show earned comfort without losing character voice.",
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
    const summary = SCENE_SUMMARIES[sid];
    if (!summary) continue; // skip scenarios without summaries

    // Need at least 2 different models for arena
    if (results.length < 2) continue;

    // Create pairwise matchups
    for (let i = 0; i < results.length; i++) {
      for (let j = i + 1; j < results.length; j++) {
        scenarios.push({
          id: `${sid}_${results[i].test_model}_vs_${results[j].test_model}`,
          context: summary,
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
