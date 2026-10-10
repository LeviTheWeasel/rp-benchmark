#!/usr/bin/env python3
"""Round-4 P4: the full run. 16 models x 23 seeds = 368 sessions.

Roster is the round-3 refusal spread, trimmed per docs/ROUND4_DESIGN.md sec 7:
the models that showed nonzero refusal, the zero-refuse frontier, and three
RP finetunes as the willingness floor. `owl_alpha` is dropped -- its OpenRouter
endpoint 404s as of 2026-08-05 (delisted preview model), so the roster is 16.

RESUMABLE. Pass --resume <file> and any (seed, model) pair already present is
skipped. A run this long will hit a provider outage or a laptop lid at some
point, and re-spending thousands of generation calls to recover from that would
be worse than the outage.

No judging here -- transcripts only, same as the pilot. Classify afterwards:
    python3 rounds/r4/classify_r4_refusals.py <file> --repeat 3

Usage:
  python3 rounds/r4/run_r4_full.py                          # fresh run
  python3 rounds/r4/run_r4_full.py --resume r4_full_X.json  # continue an interrupted one
  python3 rounds/r4/run_r4_full.py --dry-run                # show the work plan + cost
"""
import argparse
import json
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from harness import api, multiturn
from harness.config import RESULTS_DIR, REQUEST_DELAY_SECONDS, TEST_MODELS
from harness.r4_private import load_r4, save_r4

# Round-3 nonzero refusers -- the models carrying the signal.
REFUSERS = ["claude_sonnet_4_6", "glm_5_1", "claude_opus_4_8",
            "minimax_m3", "minimax_m2_7"]
# Zero-refuse frontier -- do they hold the line on Track B?
FRONTIER = ["claude_opus_4_7", "gpt_5_5", "deepseek_v4_pro", "gemini_3_5_flash",
            "kimi_k2_6", "qwen3_7_max", "mimo_2_5_pro", "gpt_4_1"]
# Willingness floor / calibration floor for both P2 gates.
# rocinante_12b was delisted from OpenRouter and removed from TEST_MODELS on
# 2026-09-24. It stays named here because wave 1 was generated with it and the
# wave-1 numbers include it; it is filtered out of any new run below.
FINETUNES = ["euryale_70b", "cydonia_24b", "rocinante_12b"]
ROSTER = REFUSERS + FRONTIER + FINETUNES

# Wave 2 (2026-09-21). Same 23 seeds, same simulator, so directly comparable to
# wave 1 -- but tagged separately because the run date differs and
# `rocinante_12b` was delisted between the waves.
WAVE2_FRONTIER = ["gpt_6_astra", "claude_fable_5_1", "qwen3_8_max",
                  "muse_spark_1_3", "tencent_hy4", "gemini_3_8_flash",
                  "deepseek_v4_1_flash", "qwen3_8_flash", "glm_5_3_flash"]
# Restores the calibration floor: wave 1 started with 3 finetunes and lost one
# to delisting mid-round, leaving 2. Both P2 gates are calibrated against this
# cohort, so it is not optional padding.
WAVE2_FINETUNES = ["skyfall_36b", "magnum_v4_72b", "unslopnemo_12b", "lunaris_8b"]
WAVE2 = WAVE2_FRONTIER + WAVE2_FINETUNES

# Wave 3 (2026-09-21). Same seeds and simulator again, so comparable to both
# earlier waves.
WAVE3 = ["claude_opus_5", "claude_sonnet_5", "gemini_3_7_flash"]
# Added after wave 3 was already generating: Opus 4.6 completes the Anthropic
# line (4.6 -> 4.7 -> 4.8 -> 5) that the round otherwise samples with a gap.
# Queued rather than run alongside -- two run_r4_full processes on one results
# file each hold their own in-memory session list, so the later save silently
# discards the other's work regardless of the atomic write.
WAVE3B = ["claude_opus_4_6"]

# Wave 4 (2026-09-24). Everything OpenRouter listed between 2026-09-04 and that
# date, plus the roster entries that had never been run. Same seeds and
# simulator again, so comparable to waves 1-3.
WAVE4 = ["claude_opus_5_5", "gpt_6_sol", "gpt_6_sol_pro", "gpt_6_luna",
         "gpt_6_luna_pro", "grok_4_7", "grok_4_3", "glm_5_3_prime",
         "glm_5_3_flashx", "qwen3_8_max_prime", "qwen3_8_omni_flash",
         "mimo_2_6_pro", "mimo_2_6_flash", "ember_1", "command_a_plus",
         "aion_3_5", "fugu_max", "mercury_2_5", "tencent_hy4",
         "deepseek_v3_0324", "gemma_4_31b", "mistral_small_2603",
         "qwen3_6_27b", "qwen3_6_35b_a3b", "venice_dolphin_24b"]

USER_SIM = "deepseek/deepseek-v3.2"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--models", nargs="+", default=ROSTER)
    ap.add_argument("--todo", action="store_true",
                    help="run every TEST_MODELS entry that has no flaw-hunter "
                         "rows yet")
    ap.add_argument("--seeds", nargs="+")
    ap.add_argument("--resume", help="Existing results file to continue")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wave", type=int, default=1,
                    help="Tag sessions with the wave they were generated in.")
    args = ap.parse_args()

    if args.todo:
        carded = set()
        f = RESULTS_DIR / "session_flaw_hunter_v2.jsonl"
        if f.exists():
            for line in open(f):
                if line.strip():
                    carded.add(json.loads(line)["model"])
        args.models = sorted(set(TEST_MODELS) - carded)

    # Validate before spending anything. Wave 1 named rocinante_12b, which has
    # since been delisted and dropped from TEST_MODELS; without this check the
    # run dies on a KeyError partway through, after paying for the models
    # ahead of it in the queue.
    unknown = [m for m in args.models if m not in TEST_MODELS]
    if unknown:
        raise SystemExit(
            "not in TEST_MODELS: %s\n"
            "(delisted models stay named in the wave lists for provenance; "
            "pass --models or --todo for a new run)" % ", ".join(unknown))

    seeds = multiturn.load_seeds(round4="all")
    if args.seeds:
        seeds = [s for s in seeds if s["id"] in args.seeds]

    work = [(s, mk) for s in seeds for mk in args.models]

    # ---- resume ------------------------------------------------------------
    out, path = None, None
    if args.resume:
        path = Path(args.resume)
        if not path.exists():
            path = RESULTS_DIR / args.resume
        # Rejoins Track B text when its private companion is on disk. Without
        # it the finished sessions stay pointers and are re-saved as they are.
        out = load_r4(path)
        # Only completed sessions count as done -- errored pairs are retried,
        # which is the point of resuming after a provider wobble.
        done_pairs = {(s["seed_id"], s["test_model"])
                      for s in out["sessions"] if "error" not in s}
        out["sessions"] = [s for s in out["sessions"] if "error" not in s]
        before = len(work)
        work = [(s, mk) for s, mk in work if (s["id"], mk) not in done_pairs]
        print("RESUME %s: %d/%d already complete, %d remaining\n"
              % (path.name, before - len(work), before, len(work)))

    gen_calls = sum((s["num_turns"] * 2 - 2) for s, _ in work)
    by_track = Counter(s["track"] for s, _ in work)
    print("R4 FULL RUN")
    print("  models:   %d  %s" % (len(args.models), ", ".join(args.models)))
    print("  seeds:    %d" % len(seeds))
    print("  sessions: %d  (%s)" % (len(work), dict(by_track)))
    print("  est. generation calls: ~%d" % gen_calls)
    print("  user sim: %s" % USER_SIM)
    print("  concurrency: %d" % args.concurrency)
    print()
    if args.dry_run:
        return 0

    if out is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = {"run_id": "r4full_%s" % run_id, "type": "r4_full",
               "timestamp": datetime.now(timezone.utc).isoformat(),
               "config": {"models": args.models, "user_sim_model": USER_SIM,
                          "seed_count": len(seeds)},
               "sessions": []}
        RESULTS_DIR.mkdir(exist_ok=True)
        path = RESULTS_DIR / ("r4_full_%s.json" % run_id)

    lock = threading.Lock()
    done = {"n": 0, "err": 0}
    total = len(work)

    def run_one(item):
        seed, mk = item
        try:
            sess = multiturn.run_session(seed, TEST_MODELS[mk], USER_SIM,
                                         num_turns=seed["num_turns"],
                                         verbose=False)
            sess.update({"test_model": mk, "test_model_id": TEST_MODELS[mk],
                         "track": seed["track"], "subtrack": seed.get("subtrack"),
                         "probe_type": seed.get("probe_type"),
                         "wave": args.wave})
            return sess
        except Exception as e:
            return {"seed_id": seed["id"], "test_model": mk,
                    "track": seed["track"], "subtrack": seed.get("subtrack"),
                    "probe_type": seed.get("probe_type"), "error": str(e)}

    def record(item, sess):
        seed, mk = item
        with lock:
            done["n"] += 1
            if "error" in sess:
                done["err"] += 1
            out["sessions"].append(sess)
            tail = ("ERR %s" % sess["error"][:60]) if "error" in sess \
                else "%d msgs" % sess["total_messages"]
            print("[%3d/%3d] %-22s x %-18s %s" % (
                done["n"], total, seed["id"], mk, tail), flush=True)
            # Write-then-rename: a crash mid-dump of a 16 MB file would
            # otherwise leave truncated JSON and lose the whole run. The
            # 2026-09-21 reboot hit exactly this window and survived on luck.
            # save_r4 does the rename, and writes the split form: Track B
            # transcripts go to the gitignored private companion
            # (ROUND4_DESIGN sec 9), never into the public file.
            save_r4(path, out)

    api.set_min_interval(REQUEST_DELAY_SECONDS / max(1, args.concurrency))
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(run_one, it): it for it in work}
        for f in as_completed(futs):
            record(futs[f], f.result())

    print("\nDone: %d sessions, %d errors -> %s" % (done["n"], done["err"], path))
    if done["err"]:
        print("Re-run the failures with:  python3 rounds/r4/run_r4_full.py --resume %s"
              % path.name)
    print("Then: python3 rounds/r4/classify_r4_refusals.py %s --repeat 3" % path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
