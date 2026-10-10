#!/usr/bin/env python3
"""Build a blind review file for Jev's trap detections.

Neither rater is ground truth here: Sonnet's session-level event counts turned
out to be noise (rho -0.005 with the composite ranking), and Jev's per-turn
detection correlates with it only -0.197. So the question "does trap detection
work" cannot be settled by comparing the two against each other -- it needs
someone to read the exchanges. That is how all three of round 4's classifier
problems were actually found.

Two deliberate design choices:

  BLIND. Jev's probability is hidden behind a <details> fold under each entry,
  so a verdict is formed from the exchange before the machine's answer is seen.
  Showing it inline would turn the review into agreement-checking.

  STRATIFIED BY CONFIDENCE, not by verdict. Confident-fail, borderline, and
  confident-clean are all sampled, and entries are shuffled. A file of only
  flagged turns measures false positives and nothing else; calibration needs
  the clean end too.

Usage: python3 rounds/r4/build_trap_review.py [--n 60]
"""
import argparse, json, random, html
from collections import defaultdict

from harness.config import RESULTS_DIR

SEED_FILES = ["adversarial_seeds.json", "adversarial_seeds_v2.json",
              "adversarial_seeds_v3_bigcard.json"]
BANDS = [("confident FAIL", 0.80, 1.01, 20),
         ("leaning fail", 0.55, 0.80, 8),
         ("borderline", 0.40, 0.55, 12),
         ("leaning clean", 0.20, 0.40, 8),
         ("confident clean", 0.00, 0.20, 12)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=20260921)
    args = ap.parse_args()

    seeds = {}
    for f in SEED_FILES:
        for s in json.load(open("hf_dataset/_source/" + f)):
            seeds[s["id"]] = s
    sessions = {}
    for s in json.load(open(RESULTS_DIR / "multiturn_merged_all_v2.json"))["sessions"]:
        if "error" not in s:
            sessions[(s["seed_id"], s["test_model"])] = s

    val = json.load(open(RESULTS_DIR / "jev_event_validation.json"))
    items = []
    for r in val["rows"]:
        if not r.get("per_turn"):
            continue
        sess = sessions.get((r["seed"], r["model"]))
        seed = seeds.get(r["seed"])
        if not sess or not seed:
            continue
        traps = [c for c in seed["challenge_turns"] if c.get("trap")]
        if len(traps) != len(r["per_turn"]):
            continue
        dlg = sess["dialogue"]
        by_turn = {c["turn"]: c for c in seed["challenge_turns"]}
        # map each scripted turn to the AI reply that followed it
        reply_for = {}
        for i, m in enumerate(dlg):
            if not m.get("is_challenge"):
                continue
            spec = by_turn.get((m["turn"] // 2) + 1)
            if spec and i + 1 < len(dlg):
                reply_for[spec["turn"]] = (m["content"], dlg[i + 1]["content"])
        for c, p in zip(traps, r["per_turn"]):
            if c["turn"] not in reply_for:
                continue
            ask, reply = reply_for[c["turn"]]
            items.append({"model": r["model"], "seed": r["seed"],
                          "failure_target": seed.get("failure_target"),
                          "turn": c["turn"], "tests": c.get("tests", []),
                          "trap": c["trap"], "ask": ask, "reply": reply, "p": p})

    rng = random.Random(args.seed)
    picked, used = [], set()
    for name, lo, hi, want in BANDS:
        pool = [i for i in items if lo <= i["p"] < hi and id(i) not in used]
        rng.shuffle(pool)
        # spread across models so one model cannot dominate a band
        seen = defaultdict(int)
        take = []
        for it in pool:
            if len(take) >= want:
                break
            if seen[it["model"]] >= max(2, want // 6):
                continue
            take.append(it); seen[it["model"]] += 1
        for it in take:
            it["band"] = name
            used.add(id(it))
        picked += take
    rng.shuffle(picked)
    picked = picked[:args.n]

    esc = html.escape
    o = ["# RP-Bench — trap detection, blind review", "",
         f"**{len(picked)} exchanges.** Each one is a scripted challenge turn from the "
         "rounds 1/2 adversarial seeds, paired with the AI's reply and the failure "
         "the seed's author wrote that turn to bait.", "",
         "## Why this needs a human", "",
         "The plan is to rebuild the craft baseline by COUNTING these failures instead "
         "of scoring 1-5 opinions -- the rubric puts 99.2% of its scores in two "
         "categories out of five, so it cannot rank anything. But the two automatic "
         "detectors disagree with each other and neither is ground truth:", "",
         "| detector | correlation with the established composite ranking |",
         "|---|---|",
         "| Sonnet, session-level event counts | **-0.005** (none) |",
         "| Jev, per-turn trap detection | -0.197 (weak, right direction) |", "",
         "Sonnet's counts are noise, so validating against them proves nothing. Jev "
         "discriminates models (1.7%-25.8% failure rate) but the one external anchor "
         "is weak. Reading the exchanges is the tiebreaker.", "",
         "## How to use it", "",
         "For each entry: read the trap, read the reply, decide **did the model commit "
         "that failure** — then open the fold to see what the detector said. The "
         "verdict is hidden on purpose; seeing it first turns this into "
         "agreement-checking rather than judging.", "",
         "Entries are shuffled and sampled across the whole confidence range, "
         "including cases the detector called clean. A file of only flagged turns "
         "would measure false positives and miss everything it let through.", "",
         "What the answer settles:", "",
         "- mostly correct → trap counting is sound, the $111 rebuild is worth running",
         "- confident calls wrong → the detector is unusable, rethink before spending",
         "- right at the extremes, noise in the middle → keep it with a confidence gate, "
         "the same fix round 4 used for its refusal labels", "", "---", ""]

    for i, it in enumerate(picked, 1):
        o += [f"## {i}. `{it['model']}` — {it['seed']} — turn {it['turn']}", "",
              f"**Failure this seed baits:** `{it['failure_target']}` · "
              f"tests: {', '.join(it['tests']) or '—'}", "",
              "**The trap (written by the seed author):**", "",
              "> " + it["trap"].replace("\n", "\n> "), "",
              "**Scripted user turn:**", "",
              "> " + it["ask"].replace("\n", "\n> "), "",
              "**AI reply:**", "", "```", it["reply"].strip()[:2500], "```", "",
              "**Your verdict:** `[ ] committed the failure` `[ ] did not` `[ ] unclear`", "",
              "<details><summary>detector's answer</summary>", "",
              f"Jev p(failure) = **{it['p']:.2f}** — band: {it['band']}", "",
              "</details>", "", "---", ""]

    out = RESULTS_DIR / "trap_detection_review.md"
    open(out, "w").write("\n".join(o))
    from collections import Counter
    print(f"wrote {out}  ({len(picked)} entries)")
    print("  by band: ", dict(Counter(i["band"] for i in picked)))
    print("  by target:", dict(Counter(i["failure_target"] for i in picked).most_common(6)))
    print("  models:   ", len({i["model"] for i in picked}))


if __name__ == "__main__":
    main()
