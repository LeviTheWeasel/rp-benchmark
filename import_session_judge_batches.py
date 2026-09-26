#!/usr/bin/env python3
"""Merge subscription session-judge scores into a single-judge file.

Writes results/session_judge_v2.jsonl. The claude-sonnet-4 scores stay inside
the session files untouched, as a second judge.

Rebuilt from the batch outputs every run rather than appended. Append-only
kept the FIRST score for a session, so a batch re-scored after a prompt fix
never replaced the superseded one and the corrected work landed nowhere -- the
same bug that bit the flaw-hunter merge.

Usage:
    python3 import_session_judge_batches.py
"""
import glob
import json
import re
from pathlib import Path


INPUT_RE = re.compile(r"/judge_\d{3}\.json$")


def _input_batches(d):
    """The batch INPUTS, by exact name.

    glob("judge_*.json") also matches judge_000.out.json and
    judge_000.recheck.json. Excluding ".out." by substring caught the first
    but not the second, and the merge then read a results file as if it were
    an input and died on a missing key. Matching the exact shape is the fix
    that does not need updating when a new suffix appears.
    """
    return sorted(f for f in glob.glob(d + "/judge_*.json") if INPUT_RE.search(f))

OUT = Path("results/session_judge_v2.jsonl")

def _merge_into(out_path, fresh_rows, key="session_id"):
    """Fold new scores into the existing file instead of replacing it.

    These mergers were written to REBUILD from the batch outputs every run,
    which is right when the batch directory holds the whole corpus: it makes
    the file a pure function of the outputs, so a re-scored batch supersedes
    its predecessor instead of being ignored.

    It stops being right the moment the exporter turns incremental. The
    directory then holds only the NEW batches, and a rebuild silently drops
    every score whose batch is no longer on disk. Here that meant 829 flaw
    rows down to 495 and 876 judge rows down to 452, recoverable only because
    they were committed minutes earlier.

    So: keep what is not in this run, replace what is. Rebuild semantics
    survive for any session the current batches cover; everything else is
    carried forward untouched.
    """
    existing = {}
    if out_path.exists():
        for line in open(out_path):
            if line.strip():
                r = json.loads(line)
                existing[r[key]] = r
    before = len(existing)
    for r in fresh_rows:
        existing[r[key]] = r
    with open(out_path, "w") as fh:
        for k in sorted(existing):
            fh.write(json.dumps(existing[k]) + "\n")
    return before, len(existing)



# The three the profile card reads. Kept explicit so a missing one is an
# error here rather than a silently absent line on 47 cards.
CARD_DIMS = ("S.1_consistency_over_time",
             "S.3_narrative_momentum",
             "S.4_adaptive_responsiveness")
SESSION_DIMS = CARD_DIMS + ("S.2_degradation_resistance",
                            "S.5_agency_respect_session",
                            "S.6_temporal_reasoning")
STD_DIMS = ("2.1_anti_purple_prose", "2.2_anti_repetition",
            "2.5_show_dont_tell", "2.6_subtext", "2.7_pacing")


def _num(d, key):
    v = (d or {}).get(key)
    if isinstance(v, dict):
        v = v.get("score")
    return v if isinstance(v, (int, float)) else None


from transcript_hash import current_hashes as _ch
_HASHES = {}


ARCHIVE = Path("results/judge_raw")


def _archive(batch_dir):
    """Copy raw rater outputs into the repo.

    The batch directory is the session scratchpad under /tmp. It is wiped by a
    reboot, and one took 88 session-judge batches, 73 flaw batches and every
    calibration file with it. The merged scores survived only because they had
    already been written here.
    """
    import shutil as _sh
    tag = Path(batch_dir).name
    dest = ARCHIVE / tag
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in glob.glob(batch_dir + "/*.out.json") + glob.glob(batch_dir + "/*.recheck.json"):
        target = dest / Path(f).name
        if not target.exists() or target.stat().st_mtime < Path(f).stat().st_mtime:
            _sh.copy2(f, target)
            n += 1
    if n:
        print("  archived %d raw output(s) -> %s" % (n, dest))


def main():
    cands = [d for d in glob.glob(
        "/tmp/claude-1000/-home-levi-ST-VAUDEVILLE/*/scratchpad/session_judge_batches")
        if glob.glob(d + "/judge_*.json")]
    if not cands:
        raise SystemExit("no judge batch directory found")
    b = cands[0]

    # Sweep outputs a rater wrote one directory up -- one did exactly that on
    # the flaw run, and the batch would have read as unscored and been redone.
    import shutil
    for stray in glob.glob(str(Path(b).parent / "judge_*.out.json")):
        shutil.move(stray, b)
        print("  recovered stray output:", Path(stray).name)

    global _HASHES
    _HASHES = _ch()

    _archive(b)

    meta = {}
    for f in _input_batches(b):
        for it in json.load(open(f)):
            meta[it["session_id"]] = (it["model"], it["seed"])

    have, added, bad, missing_dims = set(), 0, 0, 0
    out_of_range = []
    fresh = []
    if True:
        for f in sorted(glob.glob(b + "/judge_[0-9][0-9][0-9].out.json")):
            try:
                rows = json.load(open(f))
            except Exception:
                print("  unreadable:", Path(f).name)
                continue
            for r in rows:
                sid = r.get("session_id")
                if not sid or sid in have or sid not in meta:
                    continue
                sd = r.get("session_dimensions") or {}
                st = r.get("standard_dimensions") or {}
                vals = {k: _num(sd, k) for k in SESSION_DIMS}
                vals.update({k: _num(st, k) for k in STD_DIMS})
                if any(vals[k] is None for k in CARD_DIMS):
                    missing_dims += 1
                    continue
                # The rubric is a 1-5 scale. A judge that hands back 0 or 7 is
                # not scoring the same instrument, and averaging it in would
                # move a model's card without anyone seeing why.
                for k, v in vals.items():
                    if v is not None and not (1.0 <= v <= 5.0):
                        out_of_range.append((sid, k, v))
                model, seed = meta[sid]
                fresh.append({
                    "session_id": sid, "model": model, "seed": seed,
                    "session_dimensions": {k: vals[k] for k in SESSION_DIMS},
                    "standard_dimensions": {k: vals[k] for k in STD_DIMS},
                    # Rationales travel with the scores. The first version
                    # flattened {score, rationale} to a bare float for a
                    # simpler shape, which made the batch directory the only
                    # copy -- and that directory lives in /tmp, which a reboot
                    # cleared. 876 sessions x 11 one-sentence rationales went
                    # with it. Scores are what the card reads; the rationales
                    # are what anyone would need to check a score.
                    "rationales": {k: ((sd.get(k) or {}).get("rationale")
                                       if isinstance(sd.get(k), dict) else None)
                                   for k in SESSION_DIMS},
                    "quality_trajectory": r.get("quality_trajectory") or {},
                    "overall": r.get("overall"),
                    "overall_notes": (r.get("overall_notes") or "")[:400],
                    "judge": "subagent-sonnet-5", "transcript_hash": _HASHES.get(sid)})
                have.add(sid)
                added += 1

    before, after = _merge_into(OUT, fresh)
    print("  merged %d new row(s) into %d existing -> %d total"
          % (len(fresh), before, after))

    total = len(_input_batches(b))
    done = len(glob.glob(b + "/judge_[0-9][0-9][0-9].out.json"))
    print("merged %d session scores -> %s" % (added, OUT))
    if missing_dims:
        print("  %d row(s) dropped: a card dimension was missing" % missing_dims)
    if out_of_range:
        print("  %d score(s) OUTSIDE the 1-5 scale:" % len(out_of_range))
        for sid, k, v in out_of_range[:5]:
            print("      %-44s %-30s %s" % (sid, k, v))
    print("  scored:  %d of %d sessions" % (len(have), len(meta)))
    print("  batches: %d of %d" % (done, total))
    rem = [Path(f).stem for f in _input_batches(b)
           if not Path(f.replace(".json", ".out.json")).exists()]
    if rem:
        print("  next: %s" % ", ".join(rem[:8]))


if __name__ == "__main__":
    main()
