#!/usr/bin/env python3
"""Does Jev agree with the Sonnet rubric? Validate before betting the baseline on it.

Moving the rounds 1/2 baseline to Jev takes the judging bill from ~$680 to ~$128,
but the refusal work already showed Jev's agreement is UNEVEN: kappa 0.85 on the
Track B probes and 0.58 on Track A, in the same run. Rubric scoring is a third
task and a different primitive (Score, not Choice), so that evidence does not
transfer. If Jev is below the bar here, the rubric has to stay on Sonnet and the
estimate moves back toward $680 -- worth $1 to find out now rather than mid-run.

Costs nothing on OpenRouter: it scores sessions Sonnet ALREADY rated in round 3,
so only the Jev side is billed. That also keeps it clear of the wave-3 run.

Ordinal scores, so kappa alone is wrong: two raters one step apart are nearly
agreeing, and plain kappa treats that like any other miss. Reported together:
  quadratic-weighted kappa   the standard for ordinal rubric agreement
  Spearman rho               do they RANK sessions the same way
  MAE                        how far apart in rubric points

All 11 dimensions go in ONE request. Jev ingests the state once and answers in
parallel, so a transcript is not re-billed per dimension.

Usage: python3 validate_jev_rubric.py [--n 120]
"""
import argparse, json, statistics as st, threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import httpx

from harness.config import RESULTS_DIR
from jev_probe_r4 import read_key, ENDPOINT, MODEL

SRC = RESULTS_DIR / "multiturn_merged_all_v2.json"

# Levels are positions 0..4 and map to rubric 1..5 (+1). Wording is taken from
# the benchmark's own judge prompt so the two raters are asked the same thing;
# inventing new wording would measure prompt drift, not rater agreement.
BANDS = ["1 - fails this dimension outright",
         "2 - weak; noticeable problems throughout",
         "3 - adequate; does the job without distinction",
         "4 - strong; clearly well handled",
         "5 - exceptional; reserve this"]

DIMS = {
    "S.1_consistency_over_time":
        "Does the AI character's voice, personality and behaviour stay consistent "
        "from the first turn to the last, or does it drift, flatten, or go generic?",
    "S.2_degradation_resistance":
        "Does the writing quality hold up across the session? Compare the first "
        "few turns to the last: increasing verbosity, repetitive description, lost "
        "details, flattened personality all count against it.",
    "S.3_narrative_momentum":
        "Does the conversation go somewhere -- emotional, narrative or relational "
        "progression -- or does it loop, stagnate, and repeat the same beat?",
    "S.4_adaptive_responsiveness":
        "Does the AI adapt to what the user does: follow when they redirect, match "
        "when they escalate, handle the unexpected gracefully?",
    "S.5_agency_respect_session":
        "Over the session, how well does the AI avoid writing the USER's actions, "
        "making decisions for them, or railroading the story?",
    "S.6_temporal_reasoning":
        "Does time pass consistently: clock and light advancing naturally, fatigue "
        "and injury progressing, no contradictions about what happened when?",
    "2.1_anti_purple_prose":
        "Is the prose free of overwrought, purple, or ornamental writing?",
    "2.2_anti_repetition":
        "Is the writing free of repeated phrases, images and sentence shapes?",
    "2.5_show_dont_tell":
        "Does the writing show through action, detail and behaviour rather than "
        "stating emotions and traits outright?",
    "2.6_subtext":
        "Is there subtext -- meaning under the surface of what characters say and "
        "do -- rather than everything being said plainly?",
    "2.7_pacing":
        "Is the pacing well judged: scenes given the space they need, without "
        "rushing or dragging?",
}


def transcript(sess, limit=60000):
    out = []
    for m in sess["dialogue"]:
        out.append("%s (turn %d):\n%s" % (m["name"], m["turn"], m["content"]))
    return "\n\n".join(out)[:limit]


def qwkappa(pairs, lo=1, hi=5):
    """Quadratic-weighted kappa over integer-binned ratings."""
    cats = list(range(lo, hi + 1)); k = len(cats)
    idx = {c: i for i, c in enumerate(cats)}
    O = [[0] * k for _ in range(k)]
    for a, b in pairs:
        O[idx[a]][idx[b]] += 1
    n = len(pairs)
    ra = [sum(r) for r in O]; rb = [sum(O[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = ((i - j) ** 2) / ((k - 1) ** 2)
            num += w * O[i][j]
            den += w * ra[i] * rb[j] / n
    return 1 - num / den if den else None


def spearman(xs, ys):
    n = len(xs)
    rx = {v: i for i, v in enumerate(sorted(set(xs)))}
    ry = {v: i for i, v in enumerate(sorted(set(ys)))}
    return 1 - 6 * sum((rx[a] - ry[b]) ** 2 for a, b in zip(xs, ys)) / (n * (n * n - 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    d = json.load(open(SRC))
    S = [s for s in d["sessions"]
         if "error" not in s and s.get("judges", {}).get("claude_sonnet")]
    # deterministic stratified-by-model sample so the comparison is reproducible
    bym = defaultdict(list)
    for s in S:
        bym[s["test_model"]].append(s)
    picked = []
    i = 0
    while len(picked) < min(args.n, len(S)):
        added = False
        for m in sorted(bym):
            if i < len(bym[m]):
                picked.append(bym[m][i]); added = True
                if len(picked) >= args.n: break
        if not added: break
        i += 1

    key = read_key()
    print("Jev rubric validation: %d sessions, %d dimensions, one request each\n"
          % (len(picked), len(DIMS)))
    lock = threading.Lock(); rows = []; done = {"n": 0}

    def one(sess):
        body = {"state": {"roleplay_session_transcript": transcript(sess),
                          "ai_character": sess["character_name"],
                          "user_character": sess["user_name"]},
                "model": MODEL,
                "questions": {k: {"type": "score",
                                  "instructions": "Rate the AI CHARACTER (`ai_character`) "
                                                  "across the whole session. " + v,
                                  "criteria": BANDS}
                              for k, v in DIMS.items()}}
        try:
            r = httpx.post(ENDPOINT, headers={"Authorization": "Bearer %s" % key,
                                              "Content-Type": "application/json"},
                           json=body, timeout=120)
            if r.status_code != 200:
                rec = {"err": "HTTP %d %s" % (r.status_code, r.text[:120])}
            else:
                ans = r.json()["answers"]
                son = sess["judges"]["claude_sonnet"]["scores"]
                merged = {**son.get("session_dimensions", {}),
                          **son.get("standard_dimensions", {})}
                rec = {"model": sess["test_model"], "seed": sess["seed_id"], "dims": {}}
                for k in DIMS:
                    sv = (merged.get(k) or {}).get("score")
                    if sv is None or k not in ans:
                        continue
                    rec["dims"][k] = {"sonnet": float(sv),
                                      "jev": ans[k]["score"] + 1.0,   # levels 0..4 -> 1..5
                                      "confidence": ans[k].get("confidence")}
        except Exception as e:
            rec = {"err": str(e)[:120]}
        with lock:
            done["n"] += 1
            rows.append(rec)
            if done["n"] % 20 == 0:
                print("  %d/%d" % (done["n"], len(picked)), flush=True)

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        list(ex.map(one, picked))

    ok = [r for r in rows if not r.get("err")]
    errs = [r for r in rows if r.get("err")]
    print("\nscored %d sessions, %d errors" % (len(ok), len(errs)))
    if errs:
        print("  first error:", errs[0]["err"])
    if not ok:
        return

    print("\n" + "=" * 78)
    print("  PER-DIMENSION AGREEMENT  (Sonnet = reference, not ground truth)")
    print("=" * 78)
    print(f"  {'dimension':32s} {'n':>4s} {'QWK':>6s} {'rho':>6s} {'MAE':>5s} "
          f"{'son':>5s} {'jev':>5s}")
    allp = []
    per_dim = {}
    for k in DIMS:
        p = [(r["dims"][k]["sonnet"], r["dims"][k]["jev"])
             for r in ok if k in r["dims"]]
        if len(p) < 20:
            continue
        allp += p
        qwk = qwkappa([(max(1, min(5, round(a))), max(1, min(5, round(b)))) for a, b in p])
        rho = spearman([a for a, _ in p], [b for _, b in p])
        mae = st.mean(abs(a - b) for a, b in p)
        per_dim[k] = {"n": len(p), "qwk": round(qwk, 3), "spearman": round(rho, 3),
                      "mae": round(mae, 3),
                      "sonnet_mean": round(st.mean(a for a, _ in p), 2),
                      "jev_mean": round(st.mean(b for _, b in p), 2)}
        flag = "" if qwk >= 0.6 else "  <0.6"
        print(f"  {k:32s} {len(p):4d} {qwk:6.3f} {rho:6.3f} {mae:5.2f} "
              f"{st.mean(a for a,_ in p):5.2f} {st.mean(b for _,b in p):5.2f}{flag}")

    qwk_all = qwkappa([(max(1, min(5, round(a))), max(1, min(5, round(b))))
                       for a, b in allp])
    rho_all = spearman([a for a, _ in allp], [b for _, b in allp])
    mae_all = st.mean(abs(a - b) for a, b in allp)
    print("\n  " + "-" * 74)
    print(f"  {'ALL DIMENSIONS POOLED':32s} {len(allp):4d} {qwk_all:6.3f} "
          f"{rho_all:6.3f} {mae_all:5.2f}")

    print("\n" + "=" * 78)
    print("  VERDICT")
    print("=" * 78)
    bad = [k for k, v in per_dim.items() if v["qwk"] < 0.6]
    if qwk_all >= 0.6 and not bad:
        print("  Jev clears the 0.6 bar on every dimension. The rubric can move,")
        print("  and the baseline estimate stands at ~$128.")
    elif qwk_all >= 0.6:
        print("  Pooled QWK clears 0.6 but %d dimension(s) do not: %s"
              % (len(bad), ", ".join(bad)))
        print("  Move the passing dimensions and keep these on Sonnet, or accept")
        print("  a weaker signal on them. Do NOT read the pooled number alone --")
        print("  that is the mistake the round-4 kappa nearly invited.")
    else:
        print("  BELOW the bar (%.3f). The rubric stays on Sonnet and the baseline"
              % qwk_all)
        print("  estimate moves back toward ~$680. Better found now than mid-run.")

    out = RESULTS_DIR / "jev_rubric_validation.json"
    json.dump({"model": MODEL, "source": SRC.name, "n_sessions": len(ok),
               "pooled": {"qwk": round(qwk_all, 3), "spearman": round(rho_all, 3),
                          "mae": round(mae_all, 3), "n": len(allp)},
               "per_dimension": per_dim, "rows": ok},
              open(out, "w"), indent=2, ensure_ascii=False)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
