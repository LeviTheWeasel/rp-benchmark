#!/usr/bin/env python3
"""Merge subagent flaw-hunter scores into a single-rater file.

Writes results/session_flaw_hunter_v2.jsonl; the Sonnet pass stays untouched in
session_flaw_hunter.jsonl as a second rater. Idempotent, so the work can stop
anywhere and resume.
"""
import glob, json
from pathlib import Path


def _session_sources():
    """Every generation run on disk, newest last.

    Hardcoding dated filenames meant a new craft-baseline or round-4 run
    silently never reached the judges: the file exists, the models are in it,
    and every downstream script keeps reporting the old roster as complete.
    Globbing makes a new run visible the moment it lands.
    """
    import glob as _g
    from pathlib import Path as _P
    # NEWEST FIRST, and that ordering is load-bearing.
    #
    # Every consumer dedupes by session_id with "first wins". With files in
    # ascending date order, re-running a model to repair a broken run would
    # write a newer file whose sessions were then silently discarded in favour
    # of the broken ones -- the re-run costs money and changes nothing, and
    # the coverage number it was meant to fix stays exactly where it was.
    #
    # Round-4 ladder files are deliberately excluded: the flaw hunter and the
    # eleven per-turn modes are defined over the adversarial seeds, not the
    # willingness rungs, and pulling r4 in here would silently change the
    # 876-session denominator they are all reported against.
    out = sorted(_g.glob("results/craft_baseline_*.json"), reverse=True)
    out.append("results/multiturn_merged_all_v2.json")
    return [p for p in out if _P(p).exists()]

OUT = Path("results/session_flaw_hunter_v2.jsonl")

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




from lib.transcript_hash import current_hashes as _ch
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
    b = [d for d in glob.glob("/tmp/claude-1000/-home-levi-ST-VAUDEVILLE/*/scratchpad/flaw_batches")
         if glob.glob(d + "/flaw_*.json")]
    if not b:
        raise SystemExit("no flaw batch directory found")
    b = b[0]

    # Sweep results a rater wrote one directory up. One did exactly that, and
    # the batch would otherwise have read as unscored and been paid for twice.
    import shutil as _sh
    for stray in glob.glob(str(Path(b).parent / "flaw_*.out.json")):
        _sh.move(stray, b)
        print("  recovered stray output:", Path(stray).name)

    # Rebuilt from the .out.json files every time, not appended to. Append-only
    # silently kept the FIRST score for a session, so a batch rescored after a
    # rubric or prompt fix never replaced the superseded one -- the corrected
    # work landed nowhere. Rebuilding makes the file a pure function of the
    # current outputs, which is also what makes rescoring safe.
    have = set()

    # Sessions where the model produced nothing at all. The rubric scores
    # 100 minus deductions, and no text means no quotable flaw, so silence
    # earns a perfect 100 -- the scale actively rewards a model for not
    # answering. 16 sessions are affected (14 tencent_hy4, one each
    # claude_opus_5 and claude_fable_5_1). They are dropped, not scored:
    # an absent reply is missing data, not flawless writing.
    # Silence is only the degenerate case. Three raters independently reported
    # sessions that answered 1 or 2 of 11 turns, never reached their trap turn,
    # and still scored 80-88 -- above the corpus median of ~53. The mechanism
    # is the scale itself: 100 minus quoted deductions means less text is
    # strictly fewer deductions, so the rubric monotonically rewards dropping
    # out. A session that answered 1 of 11 turns is missing data, exactly like
    # a silent one, and is dropped on the same grounds.
    #
    # Expected length is the MODAL answered-turn count for that seed across all
    # models, not a fixed number: seeds differ in length and a global constant
    # would drop whole short seeds.
    from collections import Counter as _C
    per_seed, lens = {}, {}
    for src in _session_sources():
        if not Path(src).exists():
            continue
        for sess in json.load(open(src))["sessions"]:
            if "error" in sess or "dialogue" not in sess:
                continue
            sid = "%s::%s" % (sess["test_model"], sess["seed_id"])
            if sid in lens:
                continue
            n = sum(1 for m in sess["dialogue"]
                    if m.get("role") == "character" and m.get("turn")
                    and len((m.get("content") or "").strip()) >= 50)
            lens[sid] = (sess["seed_id"], n)
            per_seed.setdefault(sess["seed_id"], []).append(n)
    modal = {k: _C(v).most_common(1)[0][0] for k, v in per_seed.items()}

    SILENT, SHORT = set(), set()
    for sid, (seed, n) in lens.items():
        if n == 0:
            SILENT.add(sid)
        elif n < modal.get(seed, 0) * 0.7:
            SHORT.add(sid)

    global _HASHES
    _HASHES = _ch()

    _archive(b)

    meta = {}
    for f in glob.glob(b + "/flaw_*.json"):
        if ".out." in f:
            continue
        for it in json.load(open(f)):
            meta[it["session_id"]] = (it["model"], it["seed"], it["target"])

    # Canonical labels, parsed from the rubric itself rather than retyped: one
    # rater invented `format_break_speaker_label` and two others, deducted real
    # points for them, and said so only in its report. A score is comparable
    # only if every rater deducted from the same list, so off-list labels are
    # counted and surfaced here instead of relying on raters to confess.
    import re as _re
    canon = set()
    for m in _re.finditer(r"\*\*([A-Za-z][A-Za-z /'-]+)\*\*",
                          Path("prompts/judge_flaw_hunter.md").read_text()):
        canon.add(m.group(1).strip().lower().replace(" ", "_")
                  .replace("/", "_").replace("'", ""))

    # ---- POV ruling -------------------------------------------------------
    # The rubric's fatal reads "Wrong language/POV/tense: Major INSTRUCTION
    # violation". Raters split on whose instruction. Some fired -15 whenever a
    # reply narrated in a different person than the seed's OPENING MESSAGE,
    # even where the card mandates no POV at all -- adv_genre_shift_08 has a
    # second-person opening, a card silent on POV, and 16 sessions charged.
    #
    # The ruling: the fatal fires only where the CARD states the rule (the
    # adv_pov_* seeds, the two sysprompt style/speech seeds) or where the reply
    # leaves the card's language outright (a CJK/Cyrillic leak inside an
    # English scene). Elsewhere it is unwound. POV compliance is already
    # measured per-turn against the real card by failure mode F2; charging it
    # again here, on seeds that never asked for it, double-counts one property
    # and does so inconsistently between raters.
    #
    # Unwinding is arithmetic, not a re-judgement: the scale is additive and
    # the deduction is its own line item, so dropping it yields exactly the
    # score that rater would have produced without the label. Everything else
    # they decided is left untouched. Set POV_RULING = False to restore the
    # raw rater scores.
    POV_RULING = True
    RULED_SEEDS = {"adv_pov_multi_npc_13", "adv_pov_second_person_12",
                   "adv_pov_tense_action_14", "adv_sysprompt_speech_pattern_15",
                   "adv_sysprompt_style_restriction_16"}
    _FOREIGN = __import__("re").compile(r"[\u4e00-\u9fff\u0400-\u04ff]")

    def apply_pov_ruling(rec, seed):
        if not POV_RULING or seed in RULED_SEEDS:
            return rec, 0
        keep, unwound = [], 0
        for fl in rec.get("fatal_flaws") or []:
            lab = str(fl.get("flaw", "")).lower()
            if ("pov" in lab or "tense" in lab) and not _FOREIGN.search(
                    fl.get("quote", "") or ""):
                unwound += abs(int(fl.get("deduction") or 15))
                continue
            keep.append(fl)
        if unwound:
            rec = dict(rec, fatal_flaws=keep,
                       final_score=rec["final_score"] + unwound)
        return rec, unwound
    # -----------------------------------------------------------------------

    added, bad = 0, 0
    pov_unwound = []
    dropped_silent = set()
    dropped_short = set()
    offlist = {}
    fresh = []
    if True:
        for f in sorted(glob.glob(b + "/flaw_*.out.json")):
            try:
                rows = json.load(open(f))
            except Exception:
                print("  unreadable:", Path(f).name)
                continue
            for r in rows:
                sid = r.get("session_id")
                if not sid or sid in have or sid not in meta:
                    continue
                if sid in SILENT:
                    dropped_silent.add(sid)
                    continue
                if sid in SHORT:
                    dropped_short.add(sid)
                    continue
                score = r.get("final_score")
                if not isinstance(score, (int, float)):
                    bad += 1
                    continue
                for tier in ("fatal_flaws", "major_flaws", "minor_flaws"):
                    for fl in (r.get(tier) or []):
                        lab = str(fl.get("flaw", "")).strip().lower()
                        # Substring match in either direction: the rubric's
                        # "Wrong language/POV/tense" is one label, and a rater
                        # writing `wrong_pov` is abbreviating it, not inventing
                        # a category. Only labels sharing no wording with any
                        # rubric entry are flagged.
                        ok = any(lab in c or c in lab or
                                 (set(lab.split("_")) & set(c.split("_")))
                                 for c in canon)
                        if lab and not ok:
                            offlist.setdefault(lab, set()).add(Path(f).stem)
                model, seed, target = meta[sid]
                r, _unw = apply_pov_ruling(r, seed)
                if _unw:
                    pov_unwound.append((model, seed, _unw))
                    score = r["final_score"]
                fresh.append({
                    "session_id": sid, "model": model, "seed": seed,
                    "target": target,
                    "final_score": score,
                    "fatal_flaws": r.get("fatal_flaws") or [],
                    "major_flaws": r.get("major_flaws") or [],
                    "minor_flaws": r.get("minor_flaws") or [],
                    "bonuses": r.get("bonuses") or [],
                    "flaw_count": r.get("flaw_count"),
                    "summary": (r.get("summary") or "")[:400],
                    "judge": "subagent-rater-v1", "transcript_hash": _HASHES.get(sid)})
                have.add(sid)
                added += 1

    before, after = _merge_into(OUT, fresh)
    print("  merged %d new row(s) into %d existing -> %d total"
          % (len(fresh), before, after))

    total = len([f for f in glob.glob(b + "/flaw_*.json") if ".out." not in f])
    done = len(glob.glob(b + "/flaw_*.out.json"))
    print("merged %d new session scores -> %s" % (added, OUT))
    if dropped_silent:
        print("  dropped %d session(s) with no model output (would score 100 "
              "for silence): %s" % (len(dropped_silent),
              ", ".join(sorted(dropped_silent)[:3]) + ("..." if len(dropped_silent) > 3 else "")))
    if dropped_short:
        print("  dropped %d incomplete session(s) (< 70%% of the seed's modal "
              "length; the 100-minus-deductions scale rewards dropping out):"
              % len(dropped_short))
        from collections import Counter as _C2
        for m, n in _C2(s2.split("::")[0] for s2 in dropped_short).most_common():
            print("      %-24s %d" % (m, n))
    if bad:
        print("  %d rows dropped (no numeric final_score)" % bad)
    if offlist:
        print("  OFF-LIST flaw labels (scores not comparable until fixed):")
        for lab, batches in sorted(offlist.items()):
            print("    %-34s in %s" % (lab, ", ".join(sorted(batches))))
    if pov_unwound:
        print("  POV ruling: unwound %d POV/tense fatal(s) on %d session(s) "
              "whose card mandates no POV (+%d points total)"
              % (len(pov_unwound), len(pov_unwound),
                 sum(u for _, _, u in pov_unwound)))
    print("  scored: %d of %d sessions" % (len(have), len(meta)))
    print("  batches: %d of %d" % (done, total))
    rem = [Path(f).stem for f in sorted(glob.glob(b + "/flaw_*.json"))
           if ".out." not in f and not Path(f.replace(".json", ".out.json")).exists()]
    if rem:
        print("  next: %s" % ", ".join(rem[:8]))


if __name__ == "__main__":
    main()
