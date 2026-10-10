#!/usr/bin/env python3
"""Can Jev detect the craft failures the adversarial seeds bait? Validate first.

The rubric validation failed (QWK 0.30) -- but that failure was attributable to
the REFERENCE: 99.2% of Sonnet's rubric scores sit in two categories out of five,
so there was almost no ordering to reproduce. Event detection is a different
shape: "did this specific failure occur" has variance by construction whenever
the trap bites, and it is a Noul (yes/no), the primitive Jev scored 0.85 on in
round 4's Track B.

That is an argument, not evidence, and the rubric result is exactly why the
argument is not enough. This measures it.

Two things at once:

  1. AGREEMENT. Jev answers the same session-level questions Sonnet already
     answered on 356 existing sessions (agency violations, temporal
     contradictions, degradation). Cohen's kappa on the binary event.

  2. SENSITIVITY. The proposed method asks per CHALLENGE TURN, using that
     turn's authored `trap` as the detection criterion, instead of once per
     session. If per-turn detection finds failures the session-level question
     misses, that is the case for the rebuild -- the seeds bait specific
     failures and a session-level question averages them away.

Costs under $1 and touches no OpenRouter credit.

Usage: python3 oneoff/validate_jev_events.py [--n 356]
"""
import argparse, json, threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import httpx

from harness.config import RESULTS_DIR
from rounds.r4.jev_probe_r4 import read_key, ENDPOINT, MODEL
from rounds.r4.analyze_r4_kappa import cohens_kappa

SRC = RESULTS_DIR / "multiturn_merged_all_v2.json"
SEED_FILES = ["adversarial_seeds.json", "adversarial_seeds_v2.json",
              "adversarial_seeds_v3_bigcard.json"]

SESSION_Q = {
    "agency": "At any point in `transcript`, does the AI character (`ai_character`) "
              "write the USER character's (`user_character`) actions, decisions, "
              "speech, or physical reactions as fact -- rather than leaving them to "
              "the user?",
    "temporal": "Does `transcript` contain a temporal contradiction: time of day, "
                "elapsed time, injury or fatigue progression, or environment that "
                "cannot be reconciled with what came earlier?",
    "degradation": "Comparing the AI character's LAST few turns to its FIRST few, "
                   "has the writing quality degraded -- more repetition, more "
                   "padding, lost details, or a flatter personality?",
}


def post(key, body):
    r = httpx.post(ENDPOINT, headers={"Authorization": "Bearer %s" % key,
                                      "Content-Type": "application/json"},
                   json=body, timeout=120)
    if r.status_code != 200:
        raise RuntimeError("HTTP %d %s" % (r.status_code, r.text[:160]))
    return r.json()["answers"]


def transcript(sess, limit=60000):
    return "\n\n".join("%s (turn %d):\n%s" % (m["name"], m["turn"], m["content"])
                       for m in sess["dialogue"])[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=356)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="Noul probability above which the event counts as seen")
    args = ap.parse_args()

    seeds = {}
    for f in SEED_FILES:
        for s in json.load(open("hf_dataset/_source/" + f)):
            seeds[s["id"]] = s

    d = json.load(open(SRC))
    S = [s for s in d["sessions"]
         if "error" not in s and s.get("judges", {}).get("claude_sonnet")
         and s["seed_id"] in seeds][:args.n]
    key = read_key()
    print("Jev event detection: %d sessions, threshold p>%.2f\n" % (len(S), args.threshold))

    lock = threading.Lock(); rows = []; done = {"n": 0}

    def one(sess):
        seed = seeds[sess["seed_id"]]
        tr = transcript(sess)
        base = {"transcript": tr, "ai_character": sess["character_name"],
                "user_character": sess["user_name"]}
        rec = {"model": sess["test_model"], "seed": sess["seed_id"]}
        try:
            # 1. session-level, mirroring what Sonnet was asked
            a = post(key, {"state": base, "model": MODEL,
                           "questions": {k: {"type": "noul", "instructions": v}
                                         for k, v in SESSION_Q.items()}})
            for k in SESSION_Q:
                rec["jev_" + k] = a[k]["noul"]

            # 2. per-turn, using each turn's authored trap as the criterion
            qs = {}
            for i, c in enumerate(seed["challenge_turns"]):
                if not c.get("trap"):
                    continue
                qs["t%d" % i] = {
                    "type": "noul",
                    "instructions": {
                        "question": "Did the AI character's reply to the user turn "
                                    "quoted in `user_turn` commit the failure "
                                    "described in `failure_to_detect`? Judge only "
                                    "that reply, found in `transcript` immediately "
                                    "after that user turn.",
                        "user_turn": c["user_input"],
                        "failure_to_detect": c["trap"],
                    }}
            if qs:
                b = post(key, {"state": base, "model": MODEL, "questions": qs})
                rec["per_turn"] = [b[k]["noul"] for k in sorted(b)]

            son = sess["judges"]["claude_sonnet"]["scores"]
            sd = son.get("session_dimensions", {})
            ag = sd.get("S.5_agency_respect_session", {})
            tm = sd.get("S.6_temporal_reasoning", {})
            rec["son_agency"] = bool((ag or {}).get("violation_count") or 0)
            rec["son_temporal"] = bool(len((tm or {}).get("contradictions") or []))
            rec["son_degradation"] = bool(
                son.get("quality_trajectory", {}).get("degradation_detected"))
        except Exception as e:
            rec["err"] = str(e)[:140]
        with lock:
            done["n"] += 1
            rows.append(rec)
            if done["n"] % 50 == 0:
                print("  %d/%d" % (done["n"], len(S)), flush=True)

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        list(ex.map(one, S))

    ok = [r for r in rows if "err" not in r]
    errs = [r for r in rows if "err" in r]
    print("\nscored %d, errors %d" % (len(ok), len(errs)))
    if errs:
        print("  first error:", errs[0]["err"])
    if not ok:
        return

    TH = args.threshold
    print("\n" + "=" * 74)
    print("  1. AGREEMENT with Sonnet on the same session-level event")
    print("=" * 74)
    print(f"  {'event':14s} {'n':>4s} {'kappa':>7s} {'agree':>7s} "
          f"{'Sonnet%':>8s} {'Jev%':>6s}")
    res = {}
    for k in SESSION_Q:
        p = [(r["son_" + k], r["jev_" + k] > TH) for r in ok if "jev_" + k in r]
        if not p:
            continue
        kp = cohens_kappa([(str(a), str(b)) for a, b in p])
        sr = sum(1 for a, _ in p if a) / len(p)
        jr = sum(1 for _, b in p if b) / len(p)
        res[k] = {**kp, "n": len(p), "sonnet_rate": round(sr, 3), "jev_rate": round(jr, 3)}
        kv = kp.get("kappa")
        flag = "" if kv is None or kv >= 0.6 else "  <0.6"
        print(f"  {k:14s} {len(p):4d} {str(kv):>7s} {kp['observed']:7.3f} "
              f"{sr:8.1%} {jr:6.1%}{flag}")

    print("\n" + "=" * 74)
    print("  2. SENSITIVITY: per-turn trap detection vs one question per session")
    print("=" * 74)
    pt = [r for r in ok if r.get("per_turn")]
    if pt:
        turn_hits = sum(sum(1 for v in r["per_turn"] if v > TH) for r in pt)
        turn_total = sum(len(r["per_turn"]) for r in pt)
        any_turn = sum(1 for r in pt if any(v > TH for v in r["per_turn"]))
        sess_any = sum(1 for r in pt
                       if any(r.get("jev_" + k, 0) > TH for k in SESSION_Q))
        son_any = sum(1 for r in pt
                      if r["son_agency"] or r["son_temporal"] or r["son_degradation"])
        print(f"  trap turns flagged:            {turn_hits}/{turn_total} "
              f"({turn_hits/turn_total:.1%})")
        print(f"  sessions with >=1 trap flagged: {any_turn}/{len(pt)} "
              f"({any_turn/len(pt):.1%})")
        print(f"  sessions flagged session-level: {sess_any}/{len(pt)} "
              f"({sess_any/len(pt):.1%})   [Jev]")
        print(f"  sessions flagged by Sonnet:     {son_any}/{len(pt)} "
              f"({son_any/len(pt):.1%})")
        # discrimination across models is the point of a leaderboard
        bym = defaultdict(list)
        for r in pt:
            bym[r["model"]].append(sum(1 for v in r["per_turn"] if v > TH) /
                                   max(1, len(r["per_turn"])))
        rates = {m: sum(v) / len(v) for m, v in bym.items() if len(v) >= 8}
        if len(rates) >= 5:
            lo = min(rates.values()); hi = max(rates.values())
            print(f"\n  per-model failure rate: {lo:.1%} .. {hi:.1%} over "
                  f"{len(rates)} models  (spread {hi-lo:.1%} of scale)")
            top = sorted(rates.items(), key=lambda kv: kv[1])
            print("    cleanest:", [(m, f"{v:.0%}") for m, v in top[:3]])
            print("    worst:   ", [(m, f"{v:.0%}") for m, v in top[-3:]])
            res["per_model_rates"] = {m: round(v, 4) for m, v in rates.items()}

    print("\n" + "=" * 74)
    print("  VERDICT")
    print("=" * 74)
    ks = [v["kappa"] for v in res.values()
          if isinstance(v, dict) and v.get("kappa") is not None]
    if ks and min(ks) >= 0.6:
        print("  Jev agrees with Sonnet on every event. Detection can move to Jev;")
        print("  the rebuild stands at ~$111.")
    elif ks:
        weak = [k for k, v in res.items()
                if isinstance(v, dict) and v.get("kappa") is not None and v["kappa"] < 0.6]
        print("  Below 0.6 on: %s" % ", ".join(weak))
        print("  Read this together with the base rates above: when an event is")
        print("  rare, kappa is unstable and a low value does NOT by itself mean")
        print("  the detector is wrong -- the same trap that made the rubric")
        print("  result unreadable. Check whether the per-turn rate discriminates")
        print("  across models; that, not agreement with Sonnet, is what a")
        print("  leaderboard needs.")

    out = RESULTS_DIR / "jev_event_validation.json"
    json.dump({"model": MODEL, "threshold": TH, "n": len(ok),
               "agreement": res, "rows": ok}, open(out, "w"),
              indent=2, ensure_ascii=False)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
