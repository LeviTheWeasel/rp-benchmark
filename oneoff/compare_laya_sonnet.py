#!/usr/bin/env python3
"""Second rater for the agency/POV checks: Laya, local and independent.

Every per-turn failure label in the benchmark comes from one judge (Sonnet).
Round 4 showed what that risks: the same judge was wrong three different ways
before its rubric was pinned down, and a second opinion is the only thing that
catches it. Jev was the obvious candidate but its own docs and our measurements
put its agreement with Sonnet all over the place, and it is a hosted API.

Laya is a better second rater for this specific job:
  * genuinely independent -- ModernBERT/mmBERT encoders, 322-421M params, a
    different org, trained separately. Not a distillation of Jev, so agreement
    means two unrelated instruments saw the same thing
  * local, so no transcript leaves the machine (TypeSafe scopes zero data
    retention to enterprise plans)
  * free, so it can label everything rather than a sample

Its limit decides the scope: 512-1024 token context. Our context-bearing checks
run 1274 tokens median and 2887 at worst, so only 18% would fit. F1 and F2 are
the exception -- they are decidable from the reply alone, and a reply fits
inside 1024 tokens 96% of the time. So this compares exactly those two modes
and does not pretend to cover the other nine.

Usage: python3 oneoff/compare_laya_sonnet.py [--limit N] [--device cpu|cuda]
"""
import argparse, json, time
from collections import Counter, defaultdict

from harness.config import RESULTS_DIR
from rounds.r4.analyze_r4_kappa import cohens_kappa

QUESTIONS = {
    "F1_agency": (
        "Does `reply` narrate the USER character as fact -- their actions, their "
        "speech, their thoughts, or their physical reactions? The AI plays "
        "`ai_character`; the user controls `user_character`. Writing the AI's own "
        "character is correct and is not what this asks about."),
    "F2_pov_tense": (
        "Does `reply` break the narration's established point of view or tense -- "
        "switching person for the user character, or changing tense partway?"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--device", default="cpu")
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

    rows = [json.loads(l) for l in open(RESULTS_DIR / "per_turn_failures.jsonl")]
    work = []
    for r in rows:
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

    print("Laya vs Sonnet on F1/F2: %d exchanges, device=%s\n" % (len(work), args.device))
    from laya import Router
    router = Router(preload=False, device=args.device)

    out, t0, skipped = [], time.time(), 0
    for i, w in enumerate(work):
        # a reply longer than the context window cannot be judged honestly --
        # truncating would hide half the evidence, so it is recorded as skipped
        if len(w["reply"]) // 4 > 950:
            skipped += 1
            continue
        try:
            res = router.predict(
                state={"reply": w["reply"], "ai_character": w["char"],
                       "user_character": w["user"]},
                questions={"q": {"type": "noul", "instructions": QUESTIONS[w["mode"]]}})
            a = res["answers"]["q"]
            out.append({**{k: w[k] for k in ("model", "seed", "turn", "mode")},
                        "sonnet": bool(w["is_failure"]),
                        "laya_p": a["noul"], "laya": a["noul"] > args.threshold,
                        "confidence": a.get("confidence")})
        except Exception as e:
            print("  ERR %s/%s t%s: %s" % (w["model"], w["seed"], w["turn"], str(e)[:90]))
        if (i + 1) % 100 == 0:
            el = time.time() - t0
            print("  %d/%d  %.1f/s  eta %.0f min" % (
                i + 1, len(work), (i + 1) / el, (len(work) - i - 1) / ((i + 1) / el) / 60),
                flush=True)

    print("\nlabelled %d, skipped %d (over context)" % (len(out), skipped))
    print("\n" + "=" * 70)
    print("  AGREEMENT  (Sonnet = reference, not ground truth)")
    print("=" * 70)
    print(f"  {'mode':18s} {'n':>5s} {'kappa':>7s} {'agree':>7s} {'Sonnet%':>8s} {'Laya%':>7s}")
    res = {}
    for mode in list(QUESTIONS) + [None]:
        sel = out if mode is None else [r for r in out if r["mode"] == mode]
        if not sel:
            continue
        k = cohens_kappa([(str(r["sonnet"]), str(r["laya"])) for r in sel])
        sr = sum(1 for r in sel if r["sonnet"]) / len(sel)
        lr = sum(1 for r in sel if r["laya"]) / len(sel)
        res[mode or "ALL"] = {**k, "n": len(sel), "sonnet_rate": round(sr, 4),
                              "laya_rate": round(lr, 4)}
        print(f"  {(mode or 'ALL'):18s} {len(sel):5d} {str(k.get('kappa')):>7s} "
              f"{k['observed']:7.3f} {sr:8.1%} {lr:7.1%}")

    print("\n  disagreement shape:")
    for (a, b), n in Counter((r["sonnet"], r["laya"]) for r in out
                             if r["sonnet"] != r["laya"]).most_common():
        print("    Sonnet=%-5s Laya=%-5s  %d" % (a, b, n))

    # does Laya's own confidence separate the cases it gets right?
    hi = [r for r in out if (r.get("confidence") or 0) >= 0.8]
    if hi:
        agr = sum(1 for r in hi if r["sonnet"] == r["laya"]) / len(hi)
        allagr = sum(1 for r in out if r["sonnet"] == r["laya"]) / len(out)
        print("\n  agreement at Laya confidence >=0.8: %.3f (n=%d) vs %.3f overall"
              % (agr, len(hi), allagr))

    p = RESULTS_DIR / "laya_vs_sonnet.json"
    json.dump({"threshold": args.threshold, "device": args.device,
               "n": len(out), "skipped_over_context": skipped,
               "agreement": res, "rows": out}, open(p, "w"), indent=2)
    print("\nwrote %s" % p)


if __name__ == "__main__":
    main()
