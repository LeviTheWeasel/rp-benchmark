#!/usr/bin/env python3
"""Merge batch rung verdicts back into the r4_full session files.

Mirrors rounds/r4/classify_r4_refusals.py's on-disk shape exactly, because
rounds/r4/analyze_round4_willingness.py reads both without knowing which route produced
them. The judge supplies only `label`, `evidence` and `confidence`; rung, turn,
is_control, content_hits and disputed are recomputed here from the seed and the
reply, so the two routes cannot drift on the mechanical fields.

Merges into the session files in place rather than rebuilding them. A rebuild
paired with an incremental exporter is what destroyed the flaw corpus twice.
"""
import argparse
import glob
import json
import re
from collections import Counter
from pathlib import Path

from rounds.r4.classify_r4_refusals import content_hits, exchanges
from rounds.r4.export_r4_rung_batches import (NO_DELIVERY, strip_no_delivery,
                                     verdict_fits)
from harness.multiturn import load_seeds
from harness.r4_private import load_r4, save_batch, save_r4

BATCH_DIR = Path("/tmp/claude-1000/-home-levi-ST-VAUDEVILLE/"
                 "0e0eeb99-f00a-4b4d-87ff-9f01392fa806/scratchpad/r4_rung_batches")
ARCHIVE = Path("results/judge_raw")
TRACK_A_LABELS = {"engaged", "soft_deflect", "refused"}
TRACK_B_LABELS = {"held", "complied"}


def _archive():
    """Copy raw rater outputs into the repo.

    The batch dir is the session scratchpad under /tmp and does not survive the
    session. pipeline/import_flaw_batches.py has carried this same helper since a wipe
    took 88 session-judge batches and 73 flaw batches; that lesson was not
    carried into this importer when it was written, and the next wipe took
    every rung batch and its verdicts. The labels survived only because they
    had already been merged into results/r4_full_*.json.

    The merged labels are the data; these files are the audit trail behind them.

    The archive is tracked, so it is written split, not copied: Track B
    replies and any verdict quote over the evidence cap go to the private
    companion (ROUND4_DESIGN sec 9). A straight copy is how 42 Track B replies
    reached the repo before 2026-09-25.
    """
    dest = ARCHIVE / "r4_rung_batches"
    dest.mkdir(parents=True, exist_ok=True)
    tracks = {s["id"]: s["track"] for s in load_seeds(round4="all")}
    n = 0
    for f in sorted(BATCH_DIR.glob("*.out.json")) + sorted(BATCH_DIR.glob("r4rung_*.json")):
        if f.name.endswith(".out.json") is False and f.name.endswith(".json") and ".out." in f.name:
            continue
        target = dest / f.name
        if not target.exists() or target.stat().st_mtime < f.stat().st_mtime:
            save_batch(target, json.load(open(f)), tracks=tracks)
            n += 1
    if n:
        print("  archived %d raw batch file(s) -> %s" % (n, dest))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relabel", action="store_true",
                    help="Rewrite rung_labels on sessions that already carry "
                         "them. Needed whenever a ruling changes and a batch "
                         "is re-judged: without it an already-labelled session "
                         "is skipped and the correction is silently dropped. "
                         "Safe to repeat -- labels are rebuilt from the verdict "
                         "pool, which is text-anchored and order-independent "
                         "apart from later batches winning.")
    args = ap.parse_args()

    # Keep EVERY verdict per item_id, not the first. The same id was issued
    # twice over two different copies of the reply; which one is right is
    # decided by the text, below, not by which file sorted first.
    verdicts, n_rows, bad_label, mismatched = {}, 0, [], 0
    outs = sorted(BATCH_DIR.glob("*.out.json"))
    # Latest batch first. A re-judged batch is issued with a HIGHER number
    # than the one it corrects, so when two verdicts both fit the same text the
    # newer one wins -- which is what makes a re-issue under a new ruling
    # actually take effect instead of losing to the verdict it replaces.
    for p in sorted(outs, reverse=True):
        for r in json.load(open(p)):
            n_rows += 1
            r = dict(r, _batch=p.stem)
            verdicts.setdefault(r.get("item_id"), []).append(r)
    print("verdict files: %d of %d batches" % (len(outs),
          len(list(BATCH_DIR.glob("r4rung_*.json")))))
    print("verdicts read: %d rows over %d item_ids" % (n_rows, len(verdicts)))
    _archive()

    seeds = {s["id"]: s for s in load_seeds(round4="all")}
    written = empties = skipped = superseded = 0
    disagreed = []
    corrected = 0
    per_model = Counter()

    # Same newest-first dedup as the exporter and the analyzer. A superseded
    # session is left unlabelled on purpose: the analyzer never reads it, and
    # labelling it would put a second, worse copy of the model's ladder on disk
    # looking exactly as authoritative as the one that counts.
    seen = set()
    for f in sorted(glob.glob("results/r4_full_*.json"), reverse=True):
        # Track B text rejoined from its private companion; exchanges()
        # raises for a session it must label whose text is not on disk.
        data = load_r4(f)
        touched = False
        for s in data.get("sessions", []):
            if s.get("error"):
                continue
            # Claim the key BEFORE the already-labelled check. A newest copy
            # that is already labelled must still shut out the older copies,
            # or an earlier run gets a second, staler ladder written under it.
            key = (s.get("test_model"), s.get("seed_id"))
            if key in seen:
                superseded += 1
                continue
            seen.add(key)
            if s.get("rung_labels") and not args.relabel:
                continue
            seed = seeds.get(s.get("seed_id"))
            if not seed:
                continue
            allowed = TRACK_A_LABELS if seed["track"] == "A" else TRACK_B_LABELS
            # A correction pass usually covers only SOME rungs of a session --
            # batch 023 re-judged rung 5 and nothing else. All-or-nothing would
            # then fail the whole session and silently drop the correction, so
            # in relabel mode a rung with no batch verdict keeps the label it
            # already has. All-or-nothing still applies to a session being
            # labelled for the first time, where a partial ladder would enter
            # the denominators on whichever rungs happened to come back.
            existing = {r.get("turn"): r
                        for r in (s.get("rung_labels") or [])}
            labels, complete, reused = [], True, 0
            for spec, _user, reply in exchanges(s, seed):
                rec = {"rung": spec.get("rung"), "turn": spec["turn"],
                       "is_control": "over_refusal_control" in spec.get("tests", [])}
                if not (reply or "").strip():
                    rec.update({"label": "EMPTY_REPLY", "evidence": "",
                                "confidence": 0.0})
                    empties += 1
                else:
                    iid = "%s::%s::t%s" % (s["test_model"], s["seed_id"],
                                           spec["turn"])
                    cands = verdicts.get(iid, [])
                    fitting = [r for r in cands if verdict_fits(r, reply)]
                    if not fitting:
                        prior = existing.get(spec["turn"])
                        if args.relabel and prior is not None:
                            labels.append(dict(prior))
                            reused += 1
                            continue
                        if cands:
                            mismatched += 1
                        complete = False
                        break
                    # Two verdicts can both fit when the same exchange went
                    # out twice and the quote lands in both copies. Taking the
                    # first silently would hide a genuine rater disagreement
                    # on identical text, which is the one thing this pipeline
                    # has no other way to observe.
                    if len({r.get("label") for r in fitting}) > 1:
                        disagreed.append((iid, sorted(
                            r.get("label") for r in fitting)))
                    v = fitting[0]
                    lab = v.get("label")
                    if lab not in allowed and lab != "PARSE_ERROR":
                        bad_label.append((iid, lab))
                        complete = False
                        break
                    ev = v.get("evidence") or ""
                    # "held, but nothing was produced" -- kept as its own flag
                    # so a policy compliance rate can separate declining from
                    # simply not delivering.
                    if ev.startswith(NO_DELIVERY):
                        rec["no_delivery"] = True
                        ev = strip_no_delivery(ev)
                    rec.update({"label": lab, "evidence": ev,
                                "confidence": v.get("confidence"),
                                "route": "batch", "repeat": 1})
                if seed["track"] == "A":
                    hits = content_hits(reply, seed.get("subtrack"))
                    rec["content_hits"] = hits
                    rec["disputed"] = ((spec.get("rung") or 0) >= 3
                                       and rec.get("label") == "engaged"
                                       and hits == 0)
                labels.append(rec)
            # All-or-nothing per session: a half-labelled session would enter
            # the denominators on whichever rungs happened to come back.
            if complete and labels:
                if s.get("rung_labels") == labels:
                    continue          # nothing to rewrite
                if reused:
                    corrected += 1
                s["rung_labels"] = labels
                written += 1
                per_model[s["test_model"]] += 1
                touched = True
            else:
                skipped += 1
        if touched:
            # Split form, atomically: Track B text back to the private
            # companion, the public file keeps labels and capped evidence.
            save_r4(f, data)
            print("  updated %s" % Path(f).name)

    print("\nsessions labelled : %d   (models: %d)" % (written, len(per_model)))
    print("sessions still incomplete: %d" % skipped)
    print("empty replies labelled mechanically: %d" % empties)
    print("sessions skipped as superseded by a newer run: %d" % superseded)
    if corrected:
        print("sessions CORRECTED in place (some rungs re-judged, the rest "
              "keeping their existing labels): %d" % corrected)
    if mismatched:
        print("rungs whose only verdicts were written about a different copy "
              "of the reply: %d  (re-exported, not guessed)" % mismatched)
    if disagreed:
        print("rungs where two fitting verdicts DISAGREE on the label: %d"
              % len(disagreed))
        for iid, labs in disagreed[:5]:
            print("   %s  %s" % (iid, " vs ".join(labs)))
    if bad_label:
        print("REJECTED - label not allowed for that track: %d" % len(bad_label))
        for iid, lab in bad_label[:5]:
            print("   %s -> %r" % (iid, lab))



if __name__ == "__main__":
    main()
