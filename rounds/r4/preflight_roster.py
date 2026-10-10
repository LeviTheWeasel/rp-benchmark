#!/usr/bin/env python3
"""Check every roster id against OpenRouter before a paid run starts.

Two roster entries (openrouter/owl-alpha, thedrummer/rocinante-12b) were
silently delisted and a third lost its :free tier. A delisted id does not skip
the model -- it fails the call, and on a long run that surfaces hours in, after
the budget for the models before it is already spent. This is a few seconds at
the start instead.

Also refuses "~vendor/model-latest" aliases: the model behind one changes
without notice, so a card built on it cannot be attributed to anything.

Usage:
    python3 rounds/r4/preflight_roster.py                # check the whole roster
    python3 rounds/r4/preflight_roster.py --only a b c   # check specific keys
    python3 rounds/r4/preflight_roster.py --quote        # add a cost estimate
"""
import argparse
import json
import urllib.request

from harness.config import TEST_MODELS

API = "https://openrouter.ai/api/v1/models"

# Measured on the 25-model craft baseline and the 33-model round-4 run. Input
# dominates because every turn re-sends the transcript before it.
CRAFT_IN, CRAFT_OUT = 1.42e6, 0.29e6
R4_IN, R4_OUT = 1.40e6, 0.27e6
JUDGE_FIXED = 0.74 + 0.30 + 0.15      # craft judge + per-turn judge + user sim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--quote", action="store_true")
    args = ap.parse_args()

    roster = {k: v for k, v in TEST_MODELS.items()
              if not args.only or k in args.only}
    if args.only:
        unknown = set(args.only) - set(TEST_MODELS)
        if unknown:
            raise SystemExit("not in TEST_MODELS: %s" % ", ".join(sorted(unknown)))

    live = {m["id"]: m for m in json.loads(
        urllib.request.urlopen(API, timeout=30).read())["data"]}

    ok, bad, local, aliases = [], [], [], []
    total = 0.0
    for key, mid in sorted(roster.items()):
        if mid.startswith("remote/") or mid.startswith("local/"):
            local.append((key, mid))
            continue
        if mid.startswith("~") or mid.endswith("-latest"):
            aliases.append((key, mid))
            continue
        m = live.get(mid)
        if not m:
            bad.append((key, mid))
            continue
        p = m.get("pricing", {})
        pin = float(p.get("prompt") or 0) * 1e6
        pout = float(p.get("completion") or 0) * 1e6
        cost = ((CRAFT_IN + R4_IN) / 1e6) * pin \
            + ((CRAFT_OUT + R4_OUT) / 1e6) * pout + JUDGE_FIXED
        total += cost
        ok.append((key, mid, pin, pout, cost, m.get("context_length")))

    print("ROSTER PREFLIGHT  -- %d entries" % len(roster))
    print("  servable on OpenRouter : %d" % len(ok))
    print("  self-hosted / remote   : %d" % len(local))
    if aliases:
        print("  REFUSED (moving alias)  : %d" % len(aliases))
        for k, v in aliases:
            print("      %-24s %s" % (k, v))
    if bad:
        print("  NOT SERVED             : %d" % len(bad))
        for k, v in bad:
            print("      %-24s %s" % (k, v))

    if args.quote:
        print("\n  %-24s %7s %7s %9s %10s"
              % ("model", "$/M in", "$/M out", "est. cost", "ctx"))
        for k, mid, pin, pout, cost, ctx in sorted(ok, key=lambda r: -r[4]):
            print("  %-24s %7.2f %7.2f %9.2f %10s"
                  % (k, pin, pout, cost, ctx or "?"))
        print("  %-24s %7s %7s %9.2f" % ("TOTAL", "", "", total))
        print("\n  Estimate covers craft baseline + round 4 + judging. Flaw")
        print("  hunter runs on subscription subagents and costs nothing here.")

    if bad or aliases:
        raise SystemExit(1)
    print("\n  clean -- safe to start a paid run")


if __name__ == "__main__":
    main()
