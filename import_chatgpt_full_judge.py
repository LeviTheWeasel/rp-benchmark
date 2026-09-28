#!/usr/bin/env python3
"""Validate and import the ChatGPT full-corpus judge files.

Levi runs the package built by export_chatgpt_full_package.py through the
ChatGPT app, one conversation per chunk, and drops what comes back into
/home/levi/Documents/rp-bench-chatgpt-judge/returned/ as chunk_NN.out.json
(plus chunk_NN.report.md). This checks every row and writes the accepted ones
where the earlier external passes live, in the shape compare_external_judge.py
reads:

  results/judge_full_chatgpt/app_pass/external_partNN.json   one per chunk
  results/judge_full_chatgpt/app_pass/import_report.json     what was checked
  results/judge_full_chatgpt/app_pass/reports/               the judge's reports
  results/judge_full_chatgpt/merged/                         the whole corpus:
      these rows plus the reused rows of the earlier blind ChatGPT passes,
      with a manifest of its own, so
      `compare_external_judge.py results/judge_full_chatgpt/merged` runs on
      every session at once.

A row is accepted only if:
  - its id belongs to the package (ids are opaque; the key is in the
    manifest, which never left this repo);
  - it passes external_judge_schema.validate_row, the same code the judge ran
    as validate_output.py: every rubric key, every score a number in [1, 5],
    violation_count a non-negative integer, contradictions a list, the
    trajectory complete;
  - the transcript it scored is still the one on disk. Ids survive
    regeneration, hashes do not; a score for replaced text is stale and is
    dropped, the way transcript_hash.py drops them elsewhere;
  - no other returned file carries a different row for the same id.

Files in returned/ are never modified. Everything written here is derived from
them and rebuilt on every run, so the command is safe to repeat after each
chunk. The exit code is 0 only when every chunk is back, complete and clean.

Usage:
    python import_chatgpt_full_judge.py
    python import_chatgpt_full_judge.py --returned DIR --out DIR   # testing
"""
import argparse
import glob
import json
import shutil
import statistics as st
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from external_judge_schema import load_rows, validate_row
from transcript_hash import current_hashes

MANIFEST = Path("results/judge_full_chatgpt/_manifest.json")


def pearson(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    n = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    d = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** .5
    return n / d if d else float("nan")


def read_returned(rdir):
    """(source name, rows or None, error) for every returned JSON file, and
    for JSON files inside any returned zip, in case the judge zipped them."""
    out = []
    for p in sorted(Path(rdir).iterdir()) if Path(rdir).exists() else []:
        if p.suffix == ".json":
            try:
                out.append((p.name, load_rows(p), None))
            except Exception as e:                  # noqa: BLE001
                out.append((p.name, None, repr(e)))
        elif p.suffix == ".zip":
            with zipfile.ZipFile(p) as z:
                for n in z.namelist():
                    if not n.endswith(".json") or n.endswith("ITEMS.json"):
                        continue
                    tmp = z.read(n).decode("utf-8")
                    try:
                        rows = json.loads(tmp)
                        if not isinstance(rows, list):
                            raise ValueError("not a JSON array")
                        out.append(("%s:%s" % (p.name, n), rows, None))
                    except Exception as e:          # noqa: BLE001
                        out.append(("%s:%s" % (p.name, n), None, repr(e)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--returned", help="default: <public_dir>/returned from "
                                       "the manifest")
    ap.add_argument("--out", help="default: the manifest's directory")
    args = ap.parse_args()

    man_path = Path(args.manifest)
    man = json.load(open(man_path))
    rdir = Path(args.returned) if args.returned else Path(man["public_dir"]) / "returned"
    out = Path(args.out) if args.out else man_path.parent
    keymap = man["keymap"]
    hashes = man["transcript_hashes"]
    chunk_of, order = {}, {}
    for cn, c in man["chunks"].items():
        for part in c["parts"].values():
            for oid in part:
                chunk_of[oid] = cn
                order[oid] = len(order)

    live = current_hashes()
    print("manifest:  %s" % man_path)
    print("returned:  %s" % rdir)
    print("corpus on disk now: %d sessions\n" % len(live))

    # ---- read and check every returned row
    accepted, problems = {}, defaultdict(list)
    seen_in = defaultdict(list)
    files = read_returned(rdir)
    if not files:
        print("nothing returned yet")
    for name, rows, err in files:
        if err:
            problems["unreadable file"].append("%s: %s" % (name, err))
            continue
        for i, r in enumerate(rows):
            oid = r.get("session_id") if isinstance(r, dict) else None
            if oid not in keymap:
                problems["id not in this package"].append("%s row %d: %r"
                                                          % (name, i, oid))
                continue
            errs = validate_row(r)
            if errs:
                problems["schema"].append("%s %s: %s" % (name, oid, "; ".join(errs[:3])))
                continue
            sid = keymap[oid]
            if live.get(sid) != hashes.get(sid):
                problems["stale (transcript changed since the package was "
                         "built)"].append("%s %s" % (name, oid))
                continue
            seen_in[oid].append(name)
            if oid in accepted and accepted[oid] != r:
                problems["conflicting duplicate"].append(
                    "%s in %s" % (oid, ", ".join(seen_in[oid])))
                accepted[oid] = None            # poisoned: keep neither
                continue
            if oid not in accepted:
                accepted[oid] = r
            if "chunk_%s" % chunk_of[oid] not in name:
                problems["row in another chunk's file (accepted)"].append(
                    "%s is chunk %s, found in %s" % (oid, chunk_of[oid], name))
    accepted = {k: v for k, v in accepted.items() if v is not None}

    # ---- per-chunk status
    print("%-8s %9s %9s %9s  %s" % ("chunk", "expected", "accepted", "missing",
                                    "status"))
    all_ok = bool(files)
    for cn, c in man["chunks"].items():
        ids = [oid for part in c["parts"].values() for oid in part]
        got = [oid for oid in ids if oid in accepted]
        miss = len(ids) - len(got)
        status = "complete" if not miss else ("not returned" if not got
                                               else "INCOMPLETE")
        all_ok &= not miss
        print("chunk_%s %9d %9d %9d  %s" % (cn, len(ids), len(got), miss, status))
    if problems:
        all_ok = False
        print("\nPROBLEMS")
        for kind, items in problems.items():
            print("  %s: %d" % (kind, len(items)))
            for x in items[:8]:
                print("      %s" % x)
            if len(items) > 8:
                print("      ... %d more (all in import_report.json)" % (len(items) - 8))

    # ---- write app_pass: one external_partNN.json per chunk
    app = out / "app_pass"
    app.mkdir(parents=True, exist_ok=True)
    for old in app.glob("external_part*.json"):
        old.unlink()
    by_chunk = defaultdict(list)
    for oid, r in accepted.items():
        by_chunk[chunk_of[oid]].append(r)
    for cn, rows in sorted(by_chunk.items()):
        rows.sort(key=lambda r: order[r["session_id"]])
        tmp = app / ("external_part%s.json.tmp" % cn)
        json.dump(rows, open(tmp, "w"), ensure_ascii=False, indent=1)
        tmp.replace(app / ("external_part%s.json" % cn))
    rep_dir = app / "reports"
    for p in sorted(rdir.glob("*.md")) if rdir.exists() else []:
        rep_dir.mkdir(exist_ok=True)
        shutil.copy2(p, rep_dir / p.name)
    if out.resolve() != man_path.parent.resolve():
        shutil.copy2(man_path, out / "_manifest.json")     # compare reads it

    # ---- merged: every session with a ChatGPT row, app rows first
    merged_rows, merged_key, source = {}, {}, {}
    for oid, r in accepted.items():
        merged_rows[oid] = r
        merged_key[oid] = keymap[oid]
        source[oid] = "judge_full_chatgpt/app_pass"
    have_real = {keymap[o] for o in accepted}
    prior_rows, stale_reused = {}, []
    for sid, ref in man["reused"].items():
        key = (ref["package"], ref["subdir"], ref["file"])
        if key not in prior_rows:
            prior_rows[key] = {r["session_id"]: r for r in
                               json.load(open(Path(ref["package"]) / ref["subdir"]
                                              / ref["file"]))}
        row = prior_rows[key].get(ref["opaque"])
        if row is None or validate_row(row):
            stale_reused.append(sid)
            continue
        if live.get(sid) != ref["transcript_hash"]:
            stale_reused.append(sid)
            continue
        if sid in have_real:            # bridge session: the app row wins
            continue
        merged_rows[ref["opaque"]] = row
        merged_key[ref["opaque"]] = sid
        source[ref["opaque"]] = "%s/%s" % (Path(ref["package"]).name, ref["subdir"])
    mdir = out / "merged"
    mdir.mkdir(parents=True, exist_ok=True)
    for old in mdir.glob("external_part*.json"):
        old.unlink()
    groups = defaultdict(list)
    for oid, r in merged_rows.items():
        tag = {"judge_full_chatgpt/app_pass": "app"}.get(
            source[oid], "reused_" + source[oid].split("/")[0].replace("judge_", ""))
        groups[tag].append(r)
    for tag, rows in groups.items():
        rows.sort(key=lambda r: r["session_id"])
        json.dump(rows, open(mdir / ("external_part_%s.json" % tag), "w"),
                  ensure_ascii=False, indent=1)
    json.dump({"package": "judge_full_chatgpt/merged",
               "seed": man["seed"], "strata": None,
               "session_ids": sorted(merged_key.values()),
               "keymap": merged_key,
               "transcript_hashes": {sid: live[sid] for sid in merged_key.values()},
               "sources": source,
               "note": "Rows from this package (app harness) plus reused rows "
                       "from earlier blind ChatGPT passes (agent harness). "
                       "Bridge sessions carry the app row."},
              open(mdir / "_manifest.json", "w"), indent=1, ensure_ascii=False)

    # ---- coverage of the corpus as it is on disk now
    covered = set(merged_key.values())
    missing_models = Counter(sid.split("::")[0] for sid in live if sid not in covered)
    per_model = Counter(sid.split("::")[0] for sid in covered)
    known = set(man["session_ids"]) | set(man["reused"]) | set(man.get("excluded", {}))
    unknown = sorted(set(live) - known)
    print("\nCOVERAGE (a ChatGPT row on the current text)")
    print("  %d of %d sessions  (app rows %d, reused %d)"
          % (len(covered), len(live), len(accepted), len(covered) - len(accepted)))
    if per_model:
        print("  models covered: %d; fewest sessions: %s"
              % (len(per_model), ", ".join("%s %d" % kv
                                           for kv in sorted(per_model.items(),
                                                            key=lambda kv: kv[1])[:3])))
    if stale_reused:
        print("  %d reused row(s) dropped: their transcript changed since"
              % len(stale_reused))
    if unknown:
        print("  %d session(s) on disk are not in this package (added after it "
              "was built) -- they need an increment: %s"
              % (len(unknown), ", ".join(unknown[:5])))

    # ---- the bridge: same session, earlier agent-harness row vs this run
    pairs = []
    for sid in man.get("bridge", []):
        ref = man["reused"].get(sid)
        oid_new = next((o for o in accepted if keymap[o] == sid), None)
        if not ref or not oid_new:
            continue
        old = prior_rows.get((ref["package"], ref["subdir"], ref["file"]), {}).get(ref["opaque"])
        if old:
            pairs.append((old["overall"], accepted[oid_new]["overall"]))
    print("\nBRIDGE (earlier agent-harness pass vs this app pass, same text)")
    if len(pairs) >= 5:
        d = [b - a for a, b in pairs]
        print("  n=%d  r=%+.3f  mean(app - earlier)=%+.2f  median |d|=%.2f  "
              "within 0.5: %.0f%%"
              % (len(pairs), pearson([a for a, _ in pairs], [b for _, b in pairs]),
                 st.mean(d), st.median(abs(x) for x in d),
                 100 * sum(1 for x in d if abs(x) <= .5) / len(d)))
        print("  reference: ChatGPT vs itself, same harness, r=+0.935, median "
              "|d| 0.15 (ROUND4_DESIGN 17c)")
    else:
        print("  %d of %d bridge sessions back so far; need 5 to report"
              % (len(pairs), len(man.get("bridge", []))))

    json.dump({"returned_dir": str(rdir),
               "files": [n for n, _, _ in files],
               "accepted": len(accepted),
               "chunks": {cn: {"expected": c["sessions"],
                               "accepted": len(by_chunk.get(cn, []))}
                          for cn, c in man["chunks"].items()},
               "problems": problems,
               "coverage": {"covered": len(covered), "corpus": len(live),
                            "missing_by_model": dict(missing_models)},
               "bridge_pairs": len(pairs)},
              open(app / "import_report.json", "w"), indent=1)

    print("\nwritten:   %s/external_partNN.json (%d file(s)), %s/"
          % (app, len(by_chunk), mdir))
    print("compare:   python compare_external_judge.py %s" % mdir)
    print("status:    %s" % ("ALL CHUNKS BACK AND CLEAN" if all_ok
                             else "not complete yet (see above)"))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
