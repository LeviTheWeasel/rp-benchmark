#!/usr/bin/env python3
"""Build a self-contained package for an EXTERNAL judge (ChatGPT, etc).

Why this exists: the calibration pass already run compared two Sonnet 5 agents
and got r = +0.908 per session. That is WITHIN-family agreement. It cannot
distinguish "the scale is well defined" from "both judges share the same
systematic tilt" -- a family-wide preference for, say, dense prose would make
two Sonnet judges agree with each other and both be wrong together.

A judge from a different family is the only way to separate those. If
cross-family agreement holds near the within-family number, the SUBJECTIVE
block measures something about the writing. If it drops sharply, it measures
something about Claude.

Sampling is STRATIFIED BY SCORE and seeded, for two reasons:
  - Range restriction. Correlation computed on a narrow slice of the scale is
    not comparable to correlation on the full range; sampling only mid-range
    sessions would understate agreement, sampling the extremes would flatter
    it. Strata across the full score range keep the estimate honest.
  - Reproducibility. A fixed seed means the same sample can be re-drawn and
    the comparison repeated.

Usage:
    python3 pipeline/export_external_judge_sample.py [--n 120] [--seed 20260924]
"""
import argparse
import glob
import json
import random
from pathlib import Path

import harness.multiturn as multiturn

DEFAULT_OUT = Path("results/external_judge_package")


def _session_sources():
    out = sorted(glob.glob("results/craft_baseline_*.json"), reverse=True)
    out.append("results/multiturn_merged_all_v2.json")
    return [p for p in out if Path(p).exists()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--seed", type=int, default=20260924)
    ap.add_argument("--strata", type=int, default=6)
    ap.add_argument("--reuse", help="path of an earlier package; judge the SAME "
                                    "sessions so the two runs are paired")
    ap.add_argument("--out", help="output directory (one per judge run)")
    ap.add_argument("--increment", help="path of an earlier package; cover only "
                                        "what it missed or what has changed since")
    ap.add_argument("--per-model", type=int, default=4,
                    help="sessions to draw for each model with no coverage")
    args = ap.parse_args()

    if args.increment:
        prev = json.load(open(Path(args.increment) / "_manifest.json"))
        PREV_IDS = set(prev["session_ids"])
        PREV_HASH = prev.get("transcript_hashes") or {}
        PREV_PREFIX = prev.get("id_prefix", "s")
    else:
        PREV_IDS, PREV_HASH, PREV_PREFIX = set(), {}, None

    if args.reuse:
        prev = json.load(open(Path(args.reuse) / "_manifest.json"))
        REUSE = prev["session_ids"]
        print("reusing the sample from %s (%d sessions)" % (args.reuse, len(REUSE)))
    else:
        REUSE = None

    scored = {}
    f = Path("results/session_judge_v2.jsonl")
    if not f.exists():
        raise SystemExit("run the Sonnet 5 pass first -- there is nothing to "
                         "compare an external judge against")
    for line in open(f):
        if line.strip():
            r = json.loads(line)
            if isinstance(r.get("overall"), (int, float)):
                scored[r["session_id"]] = r["overall"]

    sessions = {}
    for src in _session_sources():
        for s in json.load(open(src))["sessions"]:
            if "error" in s or "dialogue" not in s:
                continue
            sid = "%s::%s" % (s["test_model"], s["seed_id"])
            if sid in sessions:
                continue
            sessions[sid] = s

    if REUSE is not None:
        picked = [s for s in REUSE if s in sessions]
        pool = picked
    pool = [sid for sid in scored if sid in sessions]
    pool.sort(key=lambda sid: (scored[sid], sid))     # deterministic order
    rng = random.Random(args.seed)

    # equal-count strata across the SORTED score order, then sample within
    size = max(1, len(pool) // args.strata)
    picked = []
    per = max(1, args.n // args.strata)
    for i in range(args.strata):
        chunk = pool[i * size:(i + 1) * size] if i < args.strata - 1 else pool[i * size:]
        picked.extend(rng.sample(chunk, min(per, len(chunk))))
    if REUSE is not None:
        picked = [s for s in REUSE if s in sessions]

    if args.increment:
        from lib.transcript_hash import transcript_hash as _th
        # Two kinds of gap, and they are different failures:
        #   STALE   -- covered before, but the text has since been replaced,
        #              so the existing judgement refers to something gone
        #   UNCOVERED -- a model added after the sample was drawn
        stale = [sid for sid in PREV_IDS
                 if sid in sessions and PREV_HASH.get(sid)
                 and PREV_HASH[sid] != _th(sessions[sid])]
        covered_models = {sid.split("::")[0] for sid in PREV_IDS}
        # Deferred models are mid-repair: their sessions will be regenerated
        # when the provider limit clears, so any judgement made now goes stale
        # the moment that happens. Sending them out is buying a stale answer.
        deferred = set()
        dp = Path("results/deferred_models.json")
        if dp.exists():
            deferred = {d["model"] for d in json.load(open(dp))["deferred"]}
        new_models = sorted({sid.split("::")[0] for sid in sessions}
                            - covered_models - deferred)
        if deferred:
            print("  excluded %d deferred model(s): %s"
                  % (len(deferred), ", ".join(sorted(deferred))))
        rng2 = random.Random(args.seed + 7)
        fresh = []
        for m in new_models:
            pool_m = sorted(s for s in sessions if s.split("::")[0] == m)
            fresh.extend(rng2.sample(pool_m, min(args.per_model, len(pool_m))))
        picked = sorted(set(stale) | set(fresh))
        print("increment over %s" % args.increment)
        print("  stale (transcript replaced since):  %d" % len(stale))
        print("  models with no coverage:            %d -> %d sessions"
              % (len(new_models), len(fresh)))
        if new_models:
            print("      %s" % ", ".join(new_models))

    picked = sorted(set(picked))
    # SHUFFLE before batching. Sorting by session_id groups by vendor -- the
    # first run put every Anthropic session in parts 01-05 and every OpenAI
    # session in parts 06-09. The external judge then split the parts across
    # four sub-raters by contiguous range, so rater identity lined up exactly
    # with vendor and the two could not be separated. It cost the first
    # brand-bias result: p = 0.0019 across the whole sample was confounded,
    # and only a within-rater test (p = 0.010) survived.
    random.Random(args.seed + 1).shuffle(picked)

    OUT = Path(args.out) if args.out else DEFAULT_OUT
    ID_PREFIX = "i" if args.increment else "s"
    OUT.mkdir(parents=True, exist_ok=True)
    items, keymap = [], {}
    for sid in picked:
        s = sessions[sid]
        text = "".join(
            "\n**%s** (turn %s):\n%s\n"
            % (m.get("name"), m.get("turn"), m.get("content") or "")
            for m in s["dialogue"])
        # BLIND THE ID. The first version of this shipped session_id verbatim
        # while the comment below claimed the package carried no model name --
        # but session_id IS "<model>::<seed>", so every transcript was labelled
        # with its author and scenario. The external judge caught it and said
        # so; the run's own numbers then showed the cost. Gap to the Sonnet
        # pass was +0.37 on OpenAI models against +0.93 on everything else,
        # difference +0.56, permutation p = 0.0019. That cannot say which
        # judge was biased -- a judge favouring its own and the other
        # penalising them give the identical number -- but it is a brand
        # effect in a comparison that was meant to be blind.
        # A fresh prefix per package: two packages both starting at s000 would
        # collide the moment their results were merged.
        opaque = "%s%03d" % (ID_PREFIX, len(items))
        keymap[opaque] = sid
        items.append({
            "session_id": opaque,
            "character_name": s["character_name"],
            "user_name": s["user_name"],
            "num_turns": s["num_turns"],
            "transcript": text,
        })
    # Split into parts. The whole sample is ~2.7MB of transcript; handing an
    # external agent one file that size invites it to skim. Ten sessions a
    # part matches the batch size the internal judges worked at, so the two
    # passes are done under comparable load.
    PART = 10
    for f_ in OUT.glob("sessions_part*.json"):
        f_.unlink()
    parts = [items[i:i + PART] for i in range(0, len(items), PART)]
    for i, chunk in enumerate(parts, 1):
        json.dump(chunk, open(OUT / ("sessions_part%02d.json" % i), "w"),
                  ensure_ascii=False, indent=1)
    (OUT / "RUBRIC.md").write_text(multiturn.SESSION_JUDGE_SYSTEM)

    # The task file travels with the package. Handing a judge transcripts and
    # a rubric without it loses the three rules that were learned the hard
    # way: opaque ids are deliberate, randomise any split across sub-raters,
    # and do not read the repository's own results.
    task = Path("results/judge_round2_chatgpt/TASK.md")
    if task.exists():
        body = task.read_text()
        if args.increment:
            body = body.replace("You are scoring 120 roleplay transcripts",
                                "You are scoring %d roleplay transcripts" % len(items))
            body = ("> **This is an increment.** It covers models added since the "
                    "last pass, and sessions whose text has been regenerated since "
                    "it was judged. Score it exactly as a full pass: nothing here "
                    "is a follow-up to anyone's earlier scores and you are not "
                    "being asked to revise them.\n\n") + body
        (OUT / "TASK.md").write_text(body)

    # In increment mode the new models have not been judged internally yet --
    # the external package does not depend on that and should not wait for it.
    kept = sorted(scored[sid] for sid in picked if sid in scored)
    unscored = len(picked) - len(kept)
    print("external-judge package -> %s" % OUT)
    print("  sessions:   %d  (seed %d, %d strata)"
          % (len(items), args.seed, args.strata))
    if kept:
        print("  score span: %.2f - %.2f  (corpus %.2f - %.2f)"
              % (kept[0], kept[-1], min(scored.values()), max(scored.values())))
    if unscored:
        print("  %d session(s) not yet judged internally -- the external pass "
              "does not depend on that" % unscored)
    print("  models:     %d distinct (names withheld from the package)"
          % len({sid.split("::")[0] for sid in picked}))
    print("  files:      %d x sessions_partNN.json (%d each), RUBRIC.md"
          % (len(parts), PART))
    # The key lives in the manifest, which stays OUR side and is never part
    # of what gets handed out.
    # Transcript hashes travel with the manifest. A session_id survives
    # re-generation, so without these there is no way to tell that a judge's
    # score refers to text that has since been replaced -- which has already
    # happened to 9 sessions here, when seven models were re-run at a raised
    # token ceiling.
    from lib.transcript_hash import transcript_hash as _th
    hashes = {sid: _th(sessions[sid]) for sid in picked}
    json.dump({"seed": args.seed, "strata": args.strata,
               "session_ids": picked, "keymap": keymap,
               "transcript_hashes": hashes, "id_prefix": ID_PREFIX,
               "increment_over": args.increment},
              open(OUT / "_manifest.json", "w"), indent=1)
    print("  manifest:   _manifest.json  (reproducible sample + the id key -- DO NOT SHARE)")


if __name__ == "__main__":
    main()
