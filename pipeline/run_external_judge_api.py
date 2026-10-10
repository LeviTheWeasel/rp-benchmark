#!/usr/bin/env python3
"""Run a judge package through the OpenRouter API instead of an agent UI.

The Gemini arm was blocked in a chat client by OpenRouter's credit
RESERVATION, not by a spent balance: every in-flight request reserves against
the limit, and two generation re-runs at concurrency 5 with a 16384 ceiling
hold a lot of it. Going straight at the API sidesteps the client, costs about
$1.40 for the whole 120-session pass, and produces files in the same shape the
comparison already reads.

The judge sees exactly what the external agents saw: the same rubric, the same
opaque ids, and no model names.

Usage:
    python3 pipeline/run_external_judge_api.py results/judge_round2_gemini \\
        --model google/gemini-3.7-flash --concurrency 3
"""
import argparse
import glob
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from harness.api import chat_completion

JUDGE_CONFIG = {"temperature": 0.0, "max_tokens": 8192}


def extract_json(text):
    """The rubric asks for bare JSON; models wrap it in fences anyway."""
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1:
        raise ValueError("no JSON object in reply")
    return json.loads(t[i:j + 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("package")
    ap.add_argument("--model", default="google/gemini-3.7-flash")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--out", default=None,
                    help="subdirectory for the results (default: api_pass)")
    args = ap.parse_args()

    pkg = Path(args.package)
    rubric = (pkg / "RUBRIC.md").read_text()
    out_dir = Path(args.out) if args.out else pkg / "api_pass"
    out_dir.mkdir(parents=True, exist_ok=True)

    parts = sorted(glob.glob(str(pkg / "sessions_part*.json")))
    if not parts:
        raise SystemExit("no sessions_part*.json in %s" % pkg)

    # One call per SESSION, not per part. A part is ~230KB; asking for ten
    # scored objects in one reply invites truncation and a single malformed
    # brace loses all ten. Per session the unit of loss is one row.
    work = []
    for p in parts:
        for it in json.load(open(p)):
            work.append((Path(p).name, it))
    print("package: %s" % pkg)
    print("  judge:    %s" % args.model)
    print("  sessions: %d in %d parts" % (len(work), len(parts)))
    print("  output:   %s\n" % out_dir)

    lock = threading.Lock()
    done = {"n": 0, "err": 0}
    results = {}

    def judge(item):
        part, it = item
        system = rubric % {"character_name": it["character_name"],
                           "user_name": it["user_name"],
                           "num_turns": it["num_turns"]}
        user = ("<session>\n%s\n</session>\n\n"
                "Score the AI CHARACTER's (%s) performance across this full "
                "%s-turn session. Turn 0 is a scripted opening written by the "
                "benchmark authors -- neither credit nor penalise it. Respond "
                "with ONLY the JSON object the rubric specifies."
                % (it["transcript"], it["character_name"], it["num_turns"]))
        r = chat_completion(args.model, system, user, JUDGE_CONFIG)
        obj = extract_json(r["content"])
        obj["session_id"] = it["session_id"]
        return part, obj

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(judge, w): w for w in work}
        for f in as_completed(futs):
            part, it = futs[f]
            with lock:
                done["n"] += 1
                try:
                    p_, obj = f.result()
                    results.setdefault(p_, []).append(obj)
                    tail = "ok  overall=%s" % obj.get("overall")
                except Exception as e:
                    done["err"] += 1
                    tail = "ERR %s" % repr(e)[:70]
                print("[%3d/%3d] %-28s %s"
                      % (done["n"], len(work), it["session_id"], tail),
                      flush=True)
                # Write after every session: a run this long should never be
                # recoverable only by starting over.
                for pname, rows in results.items():
                    name = pname.replace("sessions_part", "external_part")
                    tmp = out_dir / (name + ".tmp")
                    json.dump(sorted(rows, key=lambda r: r["session_id"]),
                              open(tmp, "w"), ensure_ascii=False, indent=1)
                    tmp.replace(out_dir / name)

    print("\nDone: %d scored, %d errors -> %s" % (done["n"] - done["err"],
                                                  done["err"], out_dir))
    if done["err"]:
        print("Re-run to retry the failures; completed sessions are already "
              "written and will simply be overwritten with the same values.")


if __name__ == "__main__":
    main()
