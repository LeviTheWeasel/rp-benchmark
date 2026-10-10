#!/usr/bin/env python3
"""Mechanically verify the style/speech constraints the system-prompt seeds impose.

`system_prompt_violation` was the weakest category for the LLM detector (57%
agreement) -- and it is the one category that should never have been given to a
model at all. "No -ly adverbs, no exclamation marks, sentences under 15 words,
never use the word 'I'" are decidable by code, exactly and for free. A model
asked to check them can only be less accurate and more expensive.

What moves to code here is ONLY what is decidable. Rules that need judgement --
"calls him Chen in professional settings", "never references their shared past
when Anya is present" -- depend on who is in the room and stay with a judge.
Each seed below lists both, so the split is explicit rather than implied.

Scores the AI CHARACTER's turns only.

Usage: python3 oneoff/check_style_rules.py [--file results/multiturn_merged_all_v2.json]
"""
import argparse, json, re, statistics as st
from collections import defaultdict

from harness.config import RESULTS_DIR

# -ly words that are not adverbs. Without this the check fires on "only",
# "family", "reply" and reports violations that are not there.
LY_NOT_ADVERB = {
    "only", "family", "reply", "ugly", "early", "supply", "apply", "rely",
    "imply", "comply", "assembly", "belly", "jelly", "ally", "rally", "silly",
    "holy", "italy", "july", "melancholy", "monopoly", "anomaly", "lily",
    "bully", "gully", "folly", "dolly", "tally", "valley", "trolley", "volley",
}
VOWELS = re.compile(r"[aeiouy]+")


def syllables(w):
    w = w.lower().strip("'")
    n = len(VOWELS.findall(w))
    if w.endswith("e") and n > 1:
        n -= 1
    return max(1, n)


def dialogue_only(t):
    return " ".join(re.findall(r'"([^"]*)"', t))


def sentences(t):
    return [s.strip() for s in re.split(r"[.!?]+(?:\s|$)", t) if s.strip()]


# Each entry: decidable checks, plus the rules deliberately left to a judge.
RULES = {
    "adv_sysprompt_style_restriction_16": {
        "judge_only": ["every paragraph must contain a concrete sensory detail"],
        "checks": {
            "exclamation": lambda t: t.count("!"),
            "ly_adverb": lambda t: sum(
                1 for w in re.findall(r"\b[a-z]+ly\b", t.lower())
                if w not in LY_NOT_ADVERB),
            "sentence_over_15w": lambda t: sum(
                1 for s in sentences(t) if len(s.split()) > 15),
            "simile": lambda t: len(re.findall(
                r"\b(?:like|as)\s+(?:a|an|the|some|if)\b", t, re.I)),
        }},
    "adv_sysprompt_speech_pattern_15": {
        "judge_only": [],
        "checks": {
            # both rules apply to Grum's DIALOGUE, not the narration around it
            "says_I": lambda t: len(re.findall(r"\bI\b", dialogue_only(t))),
            "word_over_3_syll": lambda t: sum(
                1 for w in re.findall(r"\b[A-Za-z']+\b", dialogue_only(t))
                if syllables(w) > 3),
        }},
    "adv_bigcard_buried_details_18": {
        "judge_only": ["treats everyone the same regardless of station",
                       "reaches for the cudgel only if violence is unavoidable"],
        "checks": {
            "swears": lambda t: len(re.findall(
                r"\b(fuck\w*|shit|damn|bastard|bloody|hell)\b", t, re.I)),
        }},
    "adv_bigcard_relationship_web_19": {
        # "in professional settings" / "in front of others" need to know who is
        # present -- not decidable from the reply alone.
        "judge_only": ["calls him Chen not Marcus in professional settings",
                       "never uses 'Marco' in front of others",
                       "never references the shared past when Anya is present"],
        "checks": {
            "says_Marco": lambda t: len(re.findall(r"\bMarco\b", t)),
        }},
    "adv_sysprompt_forbidden_topic_17": {
        "judge_only": ["never discusses her time in the police force",
                       "never names or genders her former partner"],
        "checks": {
            "police_words": lambda t: len(re.findall(
                r"\b(police|precinct|badge|homicide|detective|the force)\b", t, re.I)),
        }},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(RESULTS_DIR / "multiturn_merged_all_v2.json"))
    ap.add_argument("--raw", action="store_true",
                    help="Also print the unnormalised violations/turn, for comparison")
    args = ap.parse_args()
    d = json.load(open(args.file))

    # Per (model, seed, rule): share of that model's turns on that seed which
    # break the rule.
    #
    # Raw violation counts weight a seed by HOW MANY RULES it happens to carry:
    # style_restriction_16 has 4 checks and the other four seeds have 1-2, so it
    # alone accounts for 44% of all possible violations. A model that is clean on
    # three cheap seeds and slips on the expensive one scores worse than one that
    # slips equally on a cheap seed. Normalising per rule, then per seed, makes
    # every seed weigh the same and stops a future 5th rule in one seed from
    # silently reweighting the leaderboard.
    hits = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # model -> seed/rule -> [hit, n]
    raw = defaultdict(list)
    covered = set()
    for s in d["sessions"]:
        if "error" in s or s["seed_id"] not in RULES:
            continue
        covered.add(s["seed_id"])
        spec = RULES[s["seed_id"]]
        for msg in s["dialogue"]:
            if msg.get("role") != "character" or msg.get("turn", 0) == 0:
                continue
            t_ = msg.get("content") or ""
            if len(t_) < 40:
                continue
            tot = 0
            for name, fn in spec["checks"].items():
                v = fn(t_)
                cell = hits[s["test_model"]][s["seed_id"] + "/" + name]
                cell[0] += 1 if v else 0
                cell[1] += 1
                tot += v
            raw[s["test_model"]].append(tot)

    print("Mechanical style-rule check — no judge, no cost")
    print("seeds covered: %d/%d\n" % (len(covered), len(RULES)))

    rows = []
    for m, cells in hits.items():
        by_seed = defaultdict(list)
        for key, (h, n) in cells.items():
            if n:
                by_seed[key.split("/")[0]].append(h / n)
        if len(by_seed) < 3:
            continue
        # mean over rules inside a seed, then mean over seeds
        seed_rates = {s: st.mean(v) for s, v in by_seed.items()}
        rows.append({"model": m,
                     "break_rate": st.mean(seed_rates.values()),
                     "seeds": len(seed_rates),
                     "raw_per_turn": st.mean(raw[m]) if raw[m] else None,
                     "by_seed": {k: round(v, 3) for k, v in seed_rates.items()}})
    rows.sort(key=lambda r: r["break_rate"])

    hdr = f"  {'model':24s} {'break rate':>11s} {'seeds':>6s}"
    if args.raw:
        hdr += f" {'raw/turn':>9s}"
    print(hdr)
    for r in rows:
        line = f"  {r['model']:24s} {r['break_rate']:10.1%} {r['seeds']:6d}"
        if args.raw:
            line += f" {r['raw_per_turn']:9.2f}"
        print(line)
    if rows:
        print(f"\n  spread: {rows[0]['break_rate']:.1%} .. {rows[-1]['break_rate']:.1%}"
              f" over {len(rows)} models")
        print("  break rate = share of turns breaking a rule, averaged within a")
        print("  seed and then across seeds, so every seed weighs the same")

    # did normalising change the ordering?
    if all(r["raw_per_turn"] is not None for r in rows) and len(rows) >= 5:
        a = [r["break_rate"] for r in rows]
        b = [r["raw_per_turn"] for r in rows]
        n = len(a)
        rx = {v: i for i, v in enumerate(sorted(set(a)))}
        ry = {v: i for i, v in enumerate(sorted(set(b)))}
        rho = 1 - 6 * sum((rx[x] - ry[y]) ** 2 for x, y in zip(a, b)) / (n * (n * n - 1))
        print(f"\n  normalised vs raw ordering: rho = {rho:+.3f}")

    print("\n  left to a judge (not decidable from the reply alone):")
    for sid, spec in RULES.items():
        for r in spec["judge_only"]:
            print(f"    {sid[:34]:34s} {r}")

    out = RESULTS_DIR / "style_rule_check.json"
    json.dump({"note": "break_rate = share of turns breaking a rule, averaged "
                       "within a seed then across seeds. Raw violation counts "
                       "weight a seed by how many rules it carries (one seed held "
                       "44% of the possible total), so they are not used for "
                       "ranking. judge_only rules are NOT covered here.",
               "leaderboard": rows}, open(out, "w"), indent=2, ensure_ascii=False)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
