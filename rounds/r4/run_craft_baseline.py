#!/usr/bin/env python3
"""Craft baseline for the round-4 roster: the 25 models that have no card.

Twenty-one models carry the rounds 1/2 craft composite. Thirty-three ran in
round 4. The overlap is seven, so twenty-six round-4 models cannot be given a
profile card at all -- and `rocinante_12b` is delisted, leaving 25 to generate.

Every parameter here is copied from the existing baseline's own config rather
than chosen, because the only purpose of this run is to be comparable to it:

    user simulator   google/gemini-2.5-flash   (NOT the round-3/4 NSFW sim)
    judge            claude_sonnet only        (the baseline judged 356/356
                                                sessions with it; the CLI
                                                default would run all three
                                                and produce scores from a
                                                different mix at 3x the cost)
    turns            12
    seeds            20 adversarial, including the v2 and v3 bigcard sets

That last point matters beyond craft: the v2/v3 seeds carry the traps for
failure modes F5-F11, so these models land in the pooled trap metric that the
eight older models are excluded from.

RESUMABLE, and deliberately so -- this is a multi-hour run against paid
endpoints, and re-spending a provider outage is worse than the outage.

Usage:
  python3 rounds/r4/run_craft_baseline.py --dry-run
  python3 rounds/r4/run_craft_baseline.py --concurrency 8
  python3 rounds/r4/run_craft_baseline.py --resume results/craft_baseline_X.json
  python3 rounds/r4/run_craft_baseline.py --no-judge --concurrency 5 \
      --pairs muse_spark_1_3::adv_pov_multi_npc_13 deepseek_v4_1_flash::adv_time_pressure_05
"""
import argparse, json, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from harness import api
from harness.multiturn import load_seeds, run_session, judge_session
from harness.config import GENERATION_CONFIG, RESULTS_DIR, REQUEST_DELAY_SECONDS, TEST_MODELS, JUDGE_MODELS

# The 26 round-4 models with no craft data, minus rocinante_12b (delisted from
# OpenRouter; its round-4 row is already marked incomplete for the same reason).
ROSTER = [
    "claude_opus_5", "claude_sonnet_5", "claude_opus_4_8", "claude_sonnet_4_6",
    "claude_fable_5_1", "gpt_5_5", "gpt_6_astra", "gemini_3_5_flash",
    "gemini_3_7_flash", "gemini_3_8_flash", "deepseek_v4_1_flash",
    "glm_5_3_flash", "qwen3_7_max", "qwen3_8_max", "qwen3_8_flash",
    "minimax_m3", "mimo_2_5_pro", "muse_spark_1_3", "tencent_hy4",
    "euryale_70b", "magnum_v4_72b", "cydonia_24b", "skyfall_36b",
    "lunaris_8b", "unslopnemo_12b",
]
# The RP finetunes throttle; the frontier models do not. Measured on this run:
# every one of the 429s came from euryale / cydonia / skyfall / unslopnemo and
# none from the nineteen frontier models, and euryale lost a session to an
# exhausted retry budget at concurrency 18. They are therefore run as a second
# wave at low concurrency -- at high concurrency several workers hold sessions
# on the same small endpoint and it rate-limits itself.
# Wave 4 additions: Venice is a 24B uncensored specialist on the same class of
# small endpoint, so it is throttle-prone for the same reason. The rest of
# wave 4 are first-party frontier endpoints.
# mistral_small_2603 is here for rate limits, not size: at concurrency 8 it
# lost all 20 of its wave-2 sessions to HTTP 429 after six retries each, while
# the other thirteen models on the same run finished. It also 429'd during the
# single-call probe, so the limit is tight rather than load-dependent.
FINETUNES = ["euryale_70b", "magnum_v4_72b", "cydonia_24b", "skyfall_36b",
             "lunaris_8b", "unslopnemo_12b", "venice_dolphin_24b",
             "mistral_small_2603"]
FRONTIER = [m for m in ROSTER if m not in FINETUNES]

USER_SIM = "google/gemini-2.5-flash"
JUDGES = {"claude_sonnet": JUDGE_MODELS["claude_sonnet"]}
NUM_TURNS = 12


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=8)
    # No default. ROSTER records what wave 2 ran; defaulting to it means a
    # bare invocation silently re-runs and re-pays for models that already
    # have cards. --todo asks the results for what is actually missing.
    ap.add_argument("--models", nargs="+")
    ap.add_argument("--todo", action="store_true",
                    help="run every TEST_MODELS entry with no flaw-hunter "
                         "rows yet, i.e. everything still uncarded")
    # Repair runs re-generate single sessions, not whole models. The
    # 2026-09-21 wave ran under the old 4096-token cap and five sessions came
    # back with empty turns that had burnt the whole budget on reasoning;
    # re-running the two models in full would re-pay for 35 sessions that
    # are fine. The new file is dated later, so newest-wins in every
    # consumer picks these copies over the broken ones.
    ap.add_argument("--pairs", nargs="+", metavar="MODEL::SEED",
                    help="run only these (model, seed) sessions")
    ap.add_argument("--resume")
    ap.add_argument("--dry-run", action="store_true")
    # Judging moved to subscription subagents (export_session_judge_batches ->
    # import_session_judge_batches), so the inline claude-sonnet-4 judge is
    # now pure waste: ~$0.74 a model for scores the v2 pipeline then ignores.
    # It stays available because the rounds-1-2 baseline was generated with
    # it and reproducing that run needs it.
    ap.add_argument("--no-judge", action="store_true",
                    help="generate only; judge later on subscription")
    args = ap.parse_args()

    pairs = None
    if args.pairs:
        if args.models or args.todo:
            raise SystemExit("--pairs picks its own models; drop --models/--todo")
        bad = [p for p in args.pairs if p.count("::") != 1]
        if bad:
            raise SystemExit("--pairs wants MODEL::SEED, got %s" % bad)
        pairs = {tuple(p.split("::")) for p in args.pairs}
        args.models = sorted({m for m, _ in pairs})

    if args.todo:
        carded = set()
        f = RESULTS_DIR / "session_flaw_hunter_v2.jsonl"
        if f.exists():
            for line in open(f):
                if line.strip():
                    carded.add(json.loads(line)["model"])
        args.models = sorted(set(TEST_MODELS) - carded)
    if not args.models:
        raise SystemExit("pass --models, or --todo for everything uncarded")

    unknown = [m for m in args.models if m not in TEST_MODELS]
    if unknown:
        raise SystemExit("not in TEST_MODELS: %s" % unknown)

    # The RP finetunes rate-limit themselves at high concurrency; the frontier
    # endpoints do not. Splitting here means one invocation can carry a mixed
    # list instead of the operator remembering to run two.
    slow = [m for m in args.models if m in FINETUNES]
    fast = [m for m in args.models if m not in FINETUNES]
    # Only split when concurrency is high enough to BE the problem. The
    # guard exists to stop a throttle-prone model being drowned by fast
    # ones at concurrency 8; at 4 or below there is nothing to protect it
    # from, and refusing then blocks the very command written to rescue it.
    if slow and fast and args.concurrency > 4:
        print("NOTE: %d throttle-prone model(s) in this list (%s).\n"
              "      Run them separately at low concurrency:\n"
              "        --models %s --concurrency 4\n"
              "      Continuing with the %d frontier model(s) only.\n"
              % (len(slow), ", ".join(slow), " ".join(slow), len(fast)))
        args.models = fast

    seeds = load_seeds(adversarial=True)
    work = [(s, mk) for s in seeds for mk in args.models]
    if pairs is not None:
        missing = pairs - {(mk, s["id"]) for s, mk in work}
        if missing:
            raise SystemExit("no such adversarial seed for: %s"
                             % sorted("%s::%s" % p for p in missing))
        work = [(s, mk) for s, mk in work if (mk, s["id"]) in pairs]

    out, path = None, None
    if args.resume:
        path = Path(args.resume)
        if not path.exists():
            path = RESULTS_DIR / args.resume
        out = json.load(open(path))
        done = {(s["seed_id"], s["test_model"])
                for s in out["sessions"] if "error" not in s}
        out["sessions"] = [s for s in out["sessions"] if "error" not in s]
        before = len(work)
        work = [(s, mk) for s, mk in work if (s["id"], mk) not in done]
        print("RESUME %s: %d/%d complete, %d remaining\n"
              % (path.name, before - len(work), before, len(work)))

    print("CRAFT BASELINE")
    print("  models:      %d" % len(args.models))
    print("  seeds:       %d (adversarial)" % len(seeds))
    print("  sessions:    %d" % len(work))
    print("  gen calls:   ~%d" % (len(work) * (NUM_TURNS * 2 - 2)))
    print("  judge calls: %s" % ("0  (deferred to subscription subagents)"
                                 if args.no_judge
                                 else "%d  (%s)" % (len(work), list(JUDGES))))
    print("  user sim:    %s" % USER_SIM)
    print("  concurrency: %d\n" % args.concurrency)
    if args.dry_run:
        return 0

    if out is None:
        rid = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = {"run_id": "craft_%s" % rid, "type": "multiturn",
               "timestamp": datetime.now(timezone.utc).isoformat(),
               "config": {"test_models": {m: TEST_MODELS[m] for m in args.models},
                          "judge_models": {} if args.no_judge else JUDGES, "user_sim_model": USER_SIM,
                          "num_turns": NUM_TURNS, "adversarial": True,
                          "generation_config": dict(GENERATION_CONFIG),
                          "seed_count": len(seeds), "nsfw": False},
               "sessions": []}
        if pairs is not None:
            out["config"]["pairs"] = sorted("%s::%s" % p for p in pairs)
        RESULTS_DIR.mkdir(exist_ok=True)
        path = RESULTS_DIR / ("craft_baseline_%s.json" % rid)

    lock = threading.Lock()
    done = {"n": 0, "err": 0}
    total = len(work)

    def run_one(item):
        seed, mk = item
        try:
            sess = run_session(seed, TEST_MODELS[mk], USER_SIM, NUM_TURNS,
                               verbose=False)
            sess["test_model"] = mk
            sess["test_model_id"] = TEST_MODELS[mk]
            if not args.no_judge:
                sess["judges"] = {jk: judge_session(sess, jid, nsfw=False)
                                  for jk, jid in JUDGES.items()}
            return sess
        except Exception as e:
            return {"seed_id": seed["id"], "test_model": mk,
                    "test_model_id": TEST_MODELS[mk], "error": str(e)}

    def record(item, sess):
        seed, mk = item
        with lock:
          try:
            done["n"] += 1
            if "error" in sess:
                done["err"] += 1
                tail = "ERR %s" % sess["error"][:60]
            else:
                # .get, not [] -- with --no-judge there is no judges block, and
                # a KeyError here does not just skip a log line. record() runs
                # inside the as_completed loop, so it propagates out through
                # ThreadPoolExecutor.__exit__, which first WAITS for every
                # already-submitted session to finish generating. All 160 were
                # submitted up front, so one missing key silently bought a full
                # run's generation and then threw all of it away.
                pe = [jk for jk, jd in (sess.get("judges") or {}).items()
                      if (jd.get("scores") or {}).get("parse_error")]
                tail = "ok" + (" PARSE_ERROR %s" % pe if pe else "")
            out["sessions"].append(sess)
            print("[%3d/%3d] %-32s x %-22s %s"
                  % (done["n"], total, seed["id"], mk, tail), flush=True)
            # Write-then-rename: the stock runner dumps straight onto the live
            # file, so a crash mid-dump leaves truncated JSON and loses the run.
            tmp = path.with_suffix(".json.tmp")
            with open(tmp, "w") as f:
                json.dump(out, f, indent=2, ensure_ascii=False)
            tmp.replace(path)
          except Exception as _e:
            # Bookkeeping must never be able to discard generation that has
            # already been paid for.
            print("  RECORD FAILED for %s x %s: %r" % (seed["id"], mk, _e),
                  flush=True)

    api.set_min_interval(REQUEST_DELAY_SECONDS / max(1, args.concurrency))
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(run_one, it): it for it in work}
        for f in as_completed(futs):
            record(futs[f], f.result())

    print("\nDone: %d sessions, %d errors -> %s" % (done["n"], done["err"], path))
    if done["err"]:
        print("Retry the failures:  python3 rounds/r4/run_craft_baseline.py --resume %s" % path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
