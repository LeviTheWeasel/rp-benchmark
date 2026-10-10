#!/usr/bin/env python3
"""Second rater for F1/F2: Jev, against Sonnet's existing per-turn labels.

Every one of the 2073 per-turn failure labels comes from a single judge. Round 4
is the reason that matters: the same judge was wrong three separate ways before
its rubric was pinned down, and only a second, independent instrument caught it.

Laya was tried first and does not work here -- 48% accuracy on a balanced
sample where "always no" scores 55.6%, with a 37-48% swing across question
phrasings, i.e. it is responding to wording rather than content. Its 512-1024
token context also rules out nine of the eleven modes outright. That attempt
cost an hour and nothing, and it is recorded here so the option is not
re-litigated later.

Jev fits: 64k context, and on binary detection in round 4 it reached kappa 0.85
on the Track B probes. Whether that carries to F1/F2 is exactly what this
measures -- the round-4 rubric result showed such transfer cannot be assumed.

Scope is F1/F2 only, the two modes that are decidable from the reply alone.
The nine context-bearing modes need a separate comparison with the full state.

Usage: python3 rounds/r4/compare_jev_sonnet_f1f2.py [--limit N] [--concurrency 8]
"""
import argparse, json, threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import httpx

from harness.config import RESULTS_DIR
from rounds.r4.jev_probe_r4 import read_key, ENDPOINT, MODEL
from rounds.r4.analyze_r4_kappa import cohens_kappa

# Kept deliberately close to the wording Sonnet was given, so the comparison
# measures the raters and not two different questions.
QUESTIONS = {
    "F1_agency":
        "The AI plays `ai_character`; the player controls `user_character`. Does "
        "`reply` write the USER character's dialogue, physical actions, internal "
        "thoughts, or involuntary physical reactions as established fact? An "
        "outside observation of the user character ('Alex looked tense') is NOT a "
        "violation; stating their inner state ('Alex felt tense') is. Writing the "
        "AI's own character is never a violation.",
    "F2_pov_tense":
        "Does `reply` break the point of view or tense the scene established -- "
        "switching the grammatical person used for `user_character`, or changing "
        "tense partway through the narration? Dialogue spoken by characters is "
        "exempt; judge the narration.",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--threshold", type=float, default=0.5)
    args = ap.parse_args()

    src = json.load(open(RESULTS_DIR / "multiturn_merged_all_v2.json"))
    replies = {}
    for s in src["sessions"]:
        if "error" in s:
            continue
        for m in s.get("dialogue", []):
            if m.get("role") == "character" and m.get("turn", 0) > 0:
                replies[(s["test_model"], s["seed_id"], m["turn"])] = (
                    m.get("content") or "", s.get("character_name"), s.get("user_name"))

    work = []
    for line in open(RESULTS_DIR / "per_turn_failures.jsonl"):
        r = json.loads(line)
        if r["mode"] not in QUESTIONS:
            continue
        key = (r["model"], r["seed"], r["turn"])
        if key not in replies:
            continue
        reply, char, user = replies[key]
        if not reply or len(reply) < 50:
            continue
        work.append({**r, "reply": reply, "char": char, "user": user})
    if args.limit:
        work = work[:args.limit]

    key = read_key()
    print("Jev vs Sonnet on F1/F2: %d exchanges, model %s\n" % (len(work), MODEL))
    lock = threading.Lock(); out = []; done = {"n": 0}

    def one(w):
        body = {"state": {"reply": w["reply"], "ai_character": w["char"],
                          "user_character": w["user"]},
                "model": MODEL,
                "questions": {"q": {"type": "noul",
                                    "instructions": QUESTIONS[w["mode"]]}}}
        try:
            r = httpx.post(ENDPOINT, headers={"Authorization": "Bearer %s" % key,
                                              "Content-Type": "application/json"},
                           json=body, timeout=90)
            if r.status_code != 200:
                rec = {"err": "HTTP %d" % r.status_code}
            else:
                a = r.json()["answers"]["q"]
                rec = {"jev_p": a["noul"], "jev": a["noul"] > args.threshold,
                       "confidence": a.get("confidence")}
        except Exception as e:
            rec = {"err": str(e)[:100]}
        with lock:
            done["n"] += 1
            out.append({**{k: w[k] for k in ("model", "seed", "turn", "mode")},
                        "sonnet": bool(w["is_failure"]), **rec})
            if done["n"] % 200 == 0:
                print("  %d/%d" % (done["n"], len(work)), flush=True)

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        list(ex.map(one, work))

    ok = [r for r in out if "jev" in r]
    errs = [r for r in out if "err" in r]
    print("\nlabelled %d, errors %d" % (len(ok), len(errs)))
    if errs:
        print("  ", Counter(r["err"] for r in errs).most_common(2))

    print("\n" + "=" * 72)
    print("  AGREEMENT  (Sonnet = reference, not ground truth)")
    print("=" * 72)
    print(f"  {'mode':18s} {'n':>5s} {'kappa':>7s} {'agree':>7s} {'Sonnet%':>8s} {'Jev%':>7s}")
    res = {}
    for mode in list(QUESTIONS) + [None]:
        sel = ok if mode is None else [r for r in ok if r["mode"] == mode]
        if not sel:
            continue
        k = cohens_kappa([(str(r["sonnet"]), str(r["jev"])) for r in sel])
        sr = sum(1 for r in sel if r["sonnet"]) / len(sel)
        jr = sum(1 for r in sel if r["jev"]) / len(sel)
        res[mode or "ALL"] = {**k, "n": len(sel), "sonnet_rate": round(sr, 4),
                              "jev_rate": round(jr, 4)}
        kv = k.get("kappa")
        flag = "" if kv is None or kv >= 0.6 else "   <0.6"
        print(f"  {(mode or 'ALL'):18s} {len(sel):5d} {str(kv):>7s} {k['observed']:7.3f} "
              f"{sr:8.2%} {jr:7.2%}{flag}")

    print("\n  NOTE: both raters call these failures rarely (Sonnet: F1 4.3%, F2 0.1%).")
    print("  Kappa is unstable when one category is that scarce -- read it next to")
    print("  the base rates, not alone. This is the same trap that made the rubric")
    print("  comparison unreadable.")

    print("\n  disagreement shape:")
    for (a, b), n in Counter((r["sonnet"], r["jev"]) for r in ok
                             if r["sonnet"] != r["jev"]).most_common():
        print("    Sonnet=%-5s Jev=%-5s  %d" % (a, b, n))

    for th in (0.6, 0.8):
        hi = [r for r in ok if (r.get("confidence") or 0) >= th]
        if len(hi) > 30:
            k = cohens_kappa([(str(r["sonnet"]), str(r["jev"])) for r in hi])
            print("  kappa at Jev confidence >=%.1f: %s (n=%d, %.0f%% of data)"
                  % (th, k.get("kappa"), len(hi), 100 * len(hi) / len(ok)))

    p = RESULTS_DIR / "jev_vs_sonnet_f1f2.json"
    json.dump({"model": MODEL, "threshold": args.threshold, "n": len(ok),
               "agreement": res, "rows": ok}, open(p, "w"), indent=2)
    print("\nwrote %s" % p)


if __name__ == "__main__":
    main()
