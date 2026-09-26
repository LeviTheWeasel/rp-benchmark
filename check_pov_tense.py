#!/usr/bin/env python3
"""Mechanical cross-check of the F2 pov/tense judge.

F2 reported 1 failure in 687 checks. Before believing that models no longer
break POV, check it with something that cannot be talked out of an answer:
these three seeds mandate the POV and tense in the character card, so
compliance is decidable by code.

  adv_pov_second_person_12   2nd person PAST
  adv_pov_multi_npc_13       2nd person PAST
  adv_pov_tense_action_14    2nd person PRESENT   <- the discriminating one

The suspicion being tested: the judge prompt never receives the card, so it
cannot know which tense was mandated, and its stated fallback is internal
consistency. A reply that is consistently in the WRONG tense would pass.

Dialogue inside quotes is exempt (characters may speak in any tense), so it is
masked out before anything is counted -- the same masking mistake that produced
two rounds of false positives in the meta-commentary regex.
"""
import json, re
from collections import Counter, defaultdict
from harness.config import RESULTS_DIR

MANDATE = {"adv_pov_second_person_12": "past",
           "adv_pov_multi_npc_13": "past",
           "adv_pov_tense_action_14": "present"}

# Verbs frequent in action narration, base -> past. Invariant forms (put, cut,
# hit, set, let, read, shut) are deliberately absent: they carry no tense signal
# and counting them would dilute both sides equally while inflating n.
VERBS = {
    "walk":"walked","step":"stepped","turn":"turned","grab":"grabbed","reach":"reached",
    "pull":"pulled","push":"pushed","move":"moved","stop":"stopped","start":"started",
    "look":"looked","watch":"watched","stare":"stared","glance":"glanced","notice":"noticed",
    "feel":"felt","hear":"heard","see":"saw","know":"knew","think":"thought","find":"found",
    "take":"took","make":"made","give":"gave","come":"came","go":"went","get":"got",
    "run":"ran","stand":"stood","sit":"sat","rise":"rose","fall":"fell","hold":"held",
    "catch":"caught","throw":"threw","draw":"drew","bring":"brought","leave":"left",
    "keep":"kept","say":"said","tell":"told","ask":"asked","answer":"answered",
    "breathe":"breathed","swallow":"swallowed","nod":"nodded","shake":"shook",
    "duck":"ducked","drop":"dropped","lift":"lifted","open":"opened","close":"closed",
    "follow":"followed","wait":"waited","try":"tried","force":"forced","press":"pressed",
    "slip":"slipped","slide":"slid","climb":"climbed","enter":"entered","cross":"crossed",
    "raise":"raised","lower":"lowered","touch":"touched","grip":"gripped","let go":"let go",
}
PAST = {v: k for k, v in VERBS.items()}

def narration(t: str) -> str:
    """Strip spoken dialogue and asterisk-actions; judge only the narration."""
    t = re.sub(r'"[^"]*"', " ", t)
    t = re.sub(r'[“][^”]*[”]', " ", t)
    t = re.sub(r'\*[^*]*\*', " ", t)
    return t

def scan(text: str):
    n = narration(text)
    pres = past = 0
    for m in re.finditer(r'\b[Yy]ou (\w+)', n):
        w = m.group(1).lower()
        if w in VERBS: pres += 1
        elif w in PAST: past += 1
    # First person for the user character is a POV break regardless of tense.
    fp = len(re.findall(r'(?<![\w"])\bI [a-z]', n)) + len(re.findall(r'\bmy \w+', n))
    return pres, past, fp

def main():
    src = json.load(open(RESULTS_DIR / "multiturn_merged_all_v2.json"))
    labels = defaultdict(dict)
    for line in open(RESULTS_DIR / "per_turn_failures.jsonl"):
        r = json.loads(line)
        if r["mode"] == "F2_pov_tense":
            labels[(r["model"], r["seed"])][r["turn"]] = r["is_failure"]

    per_model = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))  # seed -> [wrong,total,fp,judge_hits]
    examples = []
    for s in src["sessions"]:
        if "error" in s or s["seed_id"] not in MANDATE: continue
        want = MANDATE[s["seed_id"]]
        for m in s.get("dialogue", []):
            if m.get("role") != "character" or m.get("turn", 0) == 0: continue
            txt = m.get("content") or ""
            if len(txt) < 50: continue
            pres, past, fp = scan(txt)
            if pres + past < 3: continue      # too little evidence to call
            got = "present" if pres > past else "past"
            share = max(pres, past) / (pres + past)
            if share < 0.7: got = "mixed"     # genuinely switching within the reply
            cell = per_model[s["test_model"]][s["seed_id"]]
            cell[1] += 1
            wrong = got != want
            if wrong: cell[0] += 1
            if fp: cell[2] += 1
            jh = labels.get((s["test_model"], s["seed_id"]), {}).get(m["turn"])
            if jh: cell[3] += 1
            if wrong and not jh and len(examples) < 4:
                examples.append((s["test_model"], s["seed_id"], m["turn"], want, got,
                                 pres, past, narration(txt)[:300]))

    print("=" * 78)
    print("  MECHANICAL POV/TENSE CHECK vs the F2 judge")
    print("=" * 78)
    print("  mandate: seed_12/13 = 2nd person PAST, seed_14 = 2nd person PRESENT\n")
    tot = Counter()
    print(f"  {'model':22s} {'s12 past':>9s} {'s13 past':>9s} {'s14 pres':>9s}   {'judge':>5s}")
    for mk in sorted(per_model):
        row = []
        for seed in ("adv_pov_second_person_12", "adv_pov_multi_npc_13",
                     "adv_pov_tense_action_14"):
            w, n, fp, jh = per_model[mk][seed]
            tot["wrong"] += w; tot["n"] += n; tot["fp"] += fp; tot["judge"] += jh
            row.append("%d/%d" % (w, n) if n else "-")
        jh_tot = sum(per_model[mk][s][3] for s in MANDATE)
        print(f"  {mk:22s} {row[0]:>9s} {row[1]:>9s} {row[2]:>9s}   {jh_tot:5d}")
    print(f"\n  wrong tense (mechanical): {tot['wrong']}/{tot['n']} = {tot['wrong']/max(1,tot['n']):.1%}")
    print(f"  1st-person slips:         {tot['fp']}")
    print(f"  flagged by the judge:     {tot['judge']}")

    print("\n  --- replies the judge passed that are in the wrong tense ---")
    for mk, seed, turn, want, got, pres, past, snip in examples:
        print(f"\n  {mk} / {seed} turn {turn}: mandated {want.upper()}, wrote {got.upper()} "
              f"(present-form {pres}, past-form {past})")
        print("    " + " ".join(snip.split())[:260])

if __name__ == "__main__":
    main()
