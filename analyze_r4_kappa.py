#!/usr/bin/env python3
"""Inter-rater reliability for the round-4 refusal classifier.

Every label in round 4 comes from one judge (Claude Sonnet), and that judge was
wrong three separate ways during development: too lenient, then too strict, then
non-reproducible across runs. Majority-of-3 at temperature 0 fixed the last of
those, but self-agreement is not agreement -- a judge can be perfectly
consistent and consistently wrong. Until a second, independent judge labels the
same exchanges, the round's numbers rest on a single unvalidated instrument.

This re-labels a random sample with a different model and reports Cohen's kappa.

Reading the result (Landis & Koch):
  < 0.20  poor        -- the labels are not measuring a shared construct
  0.21-0.40 fair
  0.41-0.60 moderate
  0.61-0.80 substantial
  > 0.80  almost perfect
Design doc sec 6.3 sets the publication bar at kappa >= 0.6.

Disagreements are written out for reading: which label pairs get confused is
more actionable than the scalar. engaged/soft_deflect confusion means the
delivery bar is fuzzy; held/complied confusion on Track B means the probe
rubric is.

A kappa belongs to a rater pair and a sample, not to the benchmark. The output
says which: it opens with scope fields (rater, source file, waves, models, the
draw), and it is written to a file named after the rater, the fraction and the
source -- results/round4_kappa_<judge-b>_<pct>pct_<source>.json unless --out
says otherwise. An existing file is never overwritten without --force. The
first run wrote results/round4_kappa.json, which a later run would have
replaced without a word; that file stays as it is, with its scope added.

The published round-4 inter-rater figures are Jev against the same Sonnet
labels over the full population (jev_vs_sonnet_r4.py ->
results/jev_vs_sonnet_r4_wave*.json). This script is a separate, sampled check.
Do not pool the two.

Usage:
  python3 analyze_r4_kappa.py results/r4_full_<ts>.json --sample 0.2
  python3 analyze_r4_kappa.py <file> --judge-b openai/gpt-5.5
  python3 analyze_r4_kappa.py <file> --out results/my_kappa.json [--force]
"""
import argparse
import json
import random
import re
import sys
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from harness import api
from harness.config import RESULTS_DIR, REQUEST_DELAY_SECONDS
from harness.multiturn import load_seeds
from harness.r4_private import dialogue_of, load_r4
import classify_r4_refusals as C


def cohens_kappa(pairs):
    """Cohen's kappa for two raters over the same items."""
    n = len(pairs)
    if not n:
        return None
    labels = sorted({l for p in pairs for l in p})
    obs = sum(1 for a, b in pairs if a == b) / n
    # expected agreement from the marginals
    ma, mb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    exp = sum((ma[l] / n) * (mb[l] / n) for l in labels)
    if exp == 1.0:
        # both raters used one label for everything: kappa is undefined, and
        # reporting 0 would read as "no agreement" when agreement is total.
        return {"kappa": None, "observed": obs, "expected": exp,
                "note": "degenerate: both raters used a single label"}
    return {"kappa": round((obs - exp) / (1 - exp), 3),
            "observed": round(obs, 3), "expected": round(exp, 3)}


def draw_sample(data, fraction, seed):
    """The labelled, non-empty exchanges by track, and the stratified draw.

    Stratified by track so Track B (7 seeds vs 16) is not swamped -- its
    probes carry held_line_rate and need their own kappa. Deterministic for a
    given file state, fraction and seed, which is what lets a past run's
    sample be re-drawn offline without asking any rater again.
    """
    pool = defaultdict(list)
    for sess in data["sessions"]:
        if "error" in sess or not sess.get("rung_labels"):
            continue
        for r in sess["rung_labels"]:
            if r["label"] in ("EMPTY_REPLY", "PARSE_ERROR"):
                continue
            pool[sess["track"]].append((sess, r))
    rng = random.Random(seed)
    sample = []
    for track, items in pool.items():
        k = max(1, round(len(items) * fraction))
        sample += [(track, x) for x in rng.sample(items, k)]
    return pool, sample


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def default_out(source, judge_b, fraction):
    """Name the file after what it measured, so two checks cannot collide."""
    return RESULTS_DIR / ("round4_kappa_%s_%gpct_%s.json"
                          % (_slug(judge_b), fraction * 100, Path(source).stem))


def scope_fields(source, data, judge_b, fraction, seed, pool, sample):
    """What this kappa is OF. Written first in the output file.

    round4_kappa.json carried none of this, and its B-hard 0.914 ended up in a
    published range beside Jev's full-population figures as if the two were
    one measurement.
    """
    drawn = [s for _, (s, _) in sample]
    models = sorted({s["test_model"] for s in drawn})
    # Sessions from the first roster wave carry no wave field.
    waves = sorted({s.get("wave") or 1 for s in drawn})
    by_track = dict(Counter(t for t, _ in sample))
    pct = "%g%%" % (fraction * 100)
    wave_txt = ("%d-%d" % (waves[0], waves[-1]) if len(waves) > 1
                else str(waves[0]))
    return {
        "label": "%s vs %s, %s stratified sample of roster wave(s) %s (drawn %d)"
                 % (judge_b, data.get("judge") or "the file's labels", pct,
                    wave_txt, len(sample)),
        "scope": ("%s re-labelled a %s sample, stratified by track, of the "
                  "labelled non-empty exchanges in %s: roster wave(s) %s, %d "
                  "models drawn. Rows where %s returned no usable label drop "
                  "from n." % (judge_b, pct, Path(source).name, wave_txt,
                               len(models), judge_b)),
        "source_file": Path(source).name,
        "sample": {"fraction": fraction, "stratified_by": "track",
                   "random_seed": seed,
                   "pool_by_track": {t: len(v) for t, v in pool.items()},
                   "drawn_by_track": by_track,
                   "roster_waves": waves,
                   "n_models": len(models), "models": models},
        "not_the_published_figure": (
            "The published round-4 inter-rater figures are Jev against the "
            "same Sonnet labels over the full population "
            "(results/jev_vs_sonnet_r4_wave*.json). This is a separate check "
            "by a different rater on a sample. Do not quote it as the round's "
            "kappa and do not pool it with Jev's."),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_file")
    ap.add_argument("--judge-b", default="openai/gpt-5.5",
                    help="Second rater. Must NOT be the first judge or its "
                         "sibling -- two Claude models would measure family "
                         "agreement, not construct validity.")
    ap.add_argument("--sample", type=float, default=0.2)
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20260921)
    ap.add_argument("--out", help="Output path. Default: results/round4_kappa_"
                                  "<judge-b>_<pct>pct_<source>.json")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite an existing output file.")
    args = ap.parse_args()

    path = Path(args.results_file)
    if not path.exists():
        path = RESULTS_DIR / args.results_file
    # Checked before any rater is called, so a refusal costs nothing.
    out_path = Path(args.out) if args.out else default_out(path, args.judge_b,
                                                             args.sample)
    if out_path.exists() and not args.force:
        sys.exit("%s already exists and holds a different run's kappa. Pass "
                 "--out for a new file, or --force to replace it." % out_path)
    # The draw needs labels only and works on the public file alone; the
    # re-labelling needs the Track B text, so that is checked before any
    # rater is called.
    data = load_r4(path)
    seeds = {s["id"]: s for s in load_seeds(round4="all")}

    pool, sample = draw_sample(data, args.sample, args.seed)
    for _, (sess, _) in sample:
        dialogue_of(sess)
    print("Kappa: judge A = %s, judge B = %s" % (data.get("judge", "?"), args.judge_b))
    print("Sample: %d exchanges (%.0f%%), stratified by track: %s\n"
          % (len(sample), args.sample * 100,
             dict(Counter(t for t, _ in sample))))

    lock = threading.Lock()
    results = []
    done = {"n": 0}

    def relabel(item):
        track, (sess, r) = item
        seed = seeds[sess["seed_id"]]
        only = {r["rung"]} if r.get("rung") else None
        labs = C.classify(sess, seed, args.judge_b, args.repeat, only)
        # match the same exchange back by turn
        b = next((x for x in labs if x["turn"] == r["turn"]), None)
        with lock:
            done["n"] += 1
            if b and b["label"] not in ("EMPTY_REPLY", "PARSE_ERROR"):
                results.append({"track": track, "model": sess["test_model"],
                                "seed": sess["seed_id"], "rung": r.get("rung"),
                                "turn": r["turn"], "a": r["label"], "b": b["label"]})
            if done["n"] % 25 == 0:
                print("  %d/%d" % (done["n"], len(sample)), flush=True)

    api.set_min_interval(REQUEST_DELAY_SECONDS / max(1, args.concurrency))
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        list(ex.map(relabel, sample))

    print("\n" + "=" * 70)
    print("  COHEN'S KAPPA")
    print("=" * 70)
    out = {**scope_fields(path, data, args.judge_b, args.sample, args.seed,
                          pool, sample),
           "judge_a": data.get("judge"), "judge_b": args.judge_b,
           "sample_fraction": args.sample, "n": len(results), "by_track": {},
           "disagreements": []}
    for track in ["A", "B-hard", "B-policy", None]:
        rows = results if track is None else [r for r in results if r["track"] == track]
        if not rows:
            continue
        k = cohens_kappa([(r["a"], r["b"]) for r in rows])
        name = track or "ALL"
        out["by_track"][name] = {**k, "n": len(rows)}
        kv = k.get("kappa")
        verdict = ("n/a" if kv is None else
                   "POOR" if kv < 0.2 else "fair" if kv < 0.41 else
                   "moderate" if kv < 0.61 else "substantial" if kv < 0.81
                   else "almost perfect")
        bar = "" if kv is None else ("  BELOW 0.6 PUBLICATION BAR" if kv < 0.6 else "")
        print(f"  {name:10s} n={len(rows):4d}  kappa={str(kv):>6s}  "
              f"agree={k['observed']:.3f}  ({verdict}){bar}")

    dis = [r for r in results if r["a"] != r["b"]]
    out["disagreements"] = dis
    print(f"\n  disagreements: {len(dis)}/{len(results)}")
    for (a, b), n in Counter((r["a"], r["b"]) for r in dis).most_common():
        print(f"    A={a:14s} B={b:14s}  {n}")

    json.dump(out, open(out_path, "w"), indent=2, ensure_ascii=False)
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
