# Repo map

The root held 111 scripts with no way to tell which round a file belonged to.
They are now grouped. The grouping is the only change: no measured value moved,
and the four result files this touched differ only in the provenance strings
that name a script's path.

| folder | what lives there | n |
|---|---|---|
| *(root)* | `run.py` (legacy CLI) and `add_model.py` (the add-a-model driver) | 2 |
| `lib/` | helpers with no entry point of their own | 6 |
| `pipeline/` | the cross-round machinery still run: coverage, defects, behavioral metrics, the flaw and session judges, profile cards, cost, latency, composite | 27 |
| `rounds/r4/` | round 4 — willingness, the rung classifier, Jev, the craft baseline, the overview/continuity/second-judge columns, the charts | 26 |
| `rounds/r3/` | round 3 — NSFW generation and judging | 8 |
| `rounds/r1_r2/` | the early single-turn and adversarial multi-turn work, seed and rubric validation | 19 |
| `arena/` | the human arenas and every ELO derived from votes | 9 |
| `oneoff/` | probes, dry runs and one-shot checks that already served their purpose. Kept for reproducibility, not to run again | 14 |

Every folder is a package (`__init__.py`), so cross-script imports are
qualified: `from pipeline.generate_profile_cards_v2 import format_verdict`.

Only 6 scripts had no entry point and belong in `lib/`. The other 26 that other
code imports are ordinary leaf scripts whose *functions* get reused — normal in
a research repo, and the reason the folders are packages rather than a flat
`lib/` holding everything imported.

## How to run anything

**From the repo root, with `PYTHONPATH=.`:**

```bash
PYTHONPATH=. .venv/bin/python pipeline/compute_coverage.py
PYTHONPATH=. .venv/bin/python rounds/r4/analyze_round4_willingness.py
```

It has to be the root. Every `results/...` path is relative to the working
directory, and a package-qualified import only resolves with the root on
`sys.path`.

## Three ways a script can depend on another, and all three were live here

Worth writing down, because the import graph shows only the first and the move
broke the other two in turn:

1. **Imports.** 84 statements in 45 files, now package-qualified.
2. **`subprocess` by path.** Scripts shell out to each other, and README and
   the docs publish commands by path. 89 files carried such a reference.
   `pipeline/generate_profile_cards_v2.py` shelling out to
   `analyze_round4_willingness.py` is what failed on the first chain run.
3. **Data paths built from `__file__`.** 28 scripts resolved `results/`
   relative to their own file, so after the move they looked in
   `rounds/r4/results/`. Fixed per file by depth —
   `Path(__file__).resolve().parents[1]` under `pipeline/`, `parents[2]` under
   `rounds/r4/`.

Channel 3 split into two idioms that are **syntactically identical and mean
opposite things**: `Path(__file__).resolve().parent` is the repo root in the
five round-4 scripts and "the directory I am shipped in" in
`lib/external_judge_schema.py`, which reads `ITEMS.json` from the judge package
it travels inside. Only what the path is then used for tells them apart, so
those were decided one at a time.

## The card generator takes no redirect

`pipeline/generate_profile_cards_v2.py` writes `results/profile_cards_v2.md`
itself, as `### model` sections with fenced bodies, because `hf_space/app.py`
slices per-model cards on that needle. Its stdout is a separate unwrapped dump
for reading in a terminal. Redirecting stdout into that path clobbers the
wrapped file the script just wrote. Just run it.

## Verification

The 9 `tests/` files are the safety net, run as
`PYTHONPATH=. .venv/bin/python tests/test_x.py` (unittest, no pytest needed).
Baseline on `main` before the move: 8 pass, 1 fails. After: the same 8 pass and
the same 1 fails — `test_plotpoints_export.py`, whose guard refuses a
`--review-out` path inside a git checkout and gets a temp dir under `/tmp`,
which is itself a git checkout on this machine. Unrelated to the move.

The whole analysis chain was also rerun from the new paths: coverage, defects,
behavioral metrics, the correlation matrix, willingness, the craft proxy, the
flaw summary, profiles, all 70 cards, and the overview/second-judge/continuity
trio.

## The rebuild order, and how it is enforced

Four round-4 artifacts record a hash of every input they read, and three of
them read each other: `round4_continuity.json` records `round4_overview.json`,
so the overview is rebuilt first and continuity last.

That order used to live nowhere. Getting it wrong surfaced only later, as
`tests/test_round4_continuity.py` failing and naming one stale input at a time
-- which is how it was found at all.

It is now derived rather than declared:

```bash
PYTHONPATH=. .venv/bin/python pipeline/check_freshness.py          # gate
PYTHONPATH=. .venv/bin/python pipeline/check_freshness.py --order  # just show it
```

The script reads the recorded hash maps, topologically sorts the artifacts by
which one appears as another's input, compares each recorded hash to the file on
disk, and exits 1 naming the scripts to re-run in order. Because the relation is
read out of the artifacts, a change in what they read updates the order instead
of leaving a constant to go stale.

`add_model.py` runs the three in that order and then runs the check as a gate,
so a wrong order or a skipped step fails the refresh rather than the next
publish.
