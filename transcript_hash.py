#!/usr/bin/env python3
"""Content hash for a session's transcript, so a score can be tied to the text
it was given.

A session_id is "<model>::<seed>" and survives re-generation unchanged. When
seven models were re-run after the max_tokens ceiling was raised, every one of
them kept its ids -- so the scores computed on the truncated transcripts would
have merged cleanly onto the repaired ones, and every downstream file would
have looked complete while pairing old judgements with new text.

Nothing in the score records could detect that: they carry session_id, model,
seed and the judge's name, and all four match. The hash is the missing field.

Usage:
    python3 transcript_hash.py            # report stale scores
    python3 transcript_hash.py --prune    # drop them from the score files
"""
import argparse
import glob
import hashlib
import json
from pathlib import Path

SCORE_FILES = ("results/session_judge_v2.jsonl",
               "results/session_flaw_hunter_v2.jsonl",
               "results/per_turn_failures_v2.jsonl")


def _sources():
    out = sorted(glob.glob("results/craft_baseline_*.json"), reverse=True)
    out.append("results/multiturn_merged_all_v2.json")
    return [p for p in out if Path(p).exists()]


def transcript_hash(session):
    """Hash of the model's own turns only.

    The user simulator is re-run too, and its turns differ between runs even
    when the model's do not. Hashing everything would mark sessions stale that
    are not.
    """
    body = "\n".join((m.get("content") or "")
                     for m in session.get("dialogue", [])
                     if m.get("role") == "character" and m.get("turn"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def current_hashes():
    out, seen = {}, set()
    for src in _sources():
        for s in json.load(open(src))["sessions"]:
            if "error" in s or "dialogue" not in s:
                continue
            sid = "%s::%s" % (s["test_model"], s["seed_id"])
            if sid in seen:        # newest source wins, same rule as elsewhere
                continue
            seen.add(sid)
            out[sid] = transcript_hash(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prune", action="store_true",
                    help="rewrite the score files without the stale rows")
    args = ap.parse_args()

    live = current_hashes()
    print("sessions on disk: %d\n" % len(live))

    for f in SCORE_FILES:
        p = Path(f)
        if not p.exists():
            continue
        rows = [json.loads(l) for l in open(p) if l.strip()]
        stale, unknown, untagged, keep = [], [], 0, []
        for r in rows:
            sid = r.get("session_id")
            h = r.get("transcript_hash")
            if sid not in live:
                unknown.append(sid)
                keep.append(r)
            elif h is None:
                untagged += 1
                keep.append(r)          # cannot judge; left alone
            elif h != live[sid]:
                stale.append(sid)
            else:
                keep.append(r)
        print("%-42s %5d rows" % (p.name, len(rows)))
        if untagged:
            print("      %5d with no hash -- written before this check existed;"
                  " re-judge to tag them" % untagged)
        if unknown:
            print("      %5d scoring a session not on disk" % len(unknown))
        if stale:
            print("      %5d STALE: the transcript changed since scoring"
                  % len(stale))
            from collections import Counter
            for m, n in Counter(s.split("::")[0] for s in stale).most_common(8):
                print("            %-24s %d" % (m, n))
            if args.prune:
                with open(p, "w") as fh:
                    for r in keep:
                        fh.write(json.dumps(r) + "\n")
                print("      pruned -> %d rows remain" % len(keep))
        elif not untagged:
            print("      all rows match their transcript")


if __name__ == "__main__":
    main()
