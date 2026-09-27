"""analyze_round4_continuity.py on a synthetic results/ directory, plus a
read-only check of the real results/round4_continuity.json when present.

Run by path from the repo root, offline:
    python -m unittest tests/test_round4_continuity.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import analyze_round4_continuity as C  # noqa: E402
import analyze_round4_overview as OV  # noqa: E402
import judge_legacy_sonnet4 as L  # noqa: E402
from transcript_hash import transcript_hash  # noqa: E402

SEEDS = ["adv_case_%02d" % i for i in range(1, 21)]
CORE = SEEDS[8:]                       # 09-20
PROSE = ("The lantern gutters and the rain keeps on at the shutters, slow and "
         "patient, while %s watches the door.")

# model: (base old-judge score, seeds played in round 4, where its round-4
# transcripts live, earlier rounds)
ROSTER = {
    "a_same1": (4.5, SEEDS, "merged", {"r2"}),
    "a_same2": (4.3, CORE, "merged", {"r2", "r3n"}),
    "a_same3": (4.1, SEEDS, "merged", {"r2", "r3n"}),
    "a_same4": (3.8, SEEDS, "merged", {"r2", "r3n"}),
    "a_regen": (4.0, SEEDS, "cb_0924", {"r2", "r3n"}),
    "b_r3one": (4.4, SEEDS, "cb_0921", {"r3s", "r3n"}),
    "b_r3two": (3.6, SEEDS, "cb_0921", {"r3s", "r3n"}),
    "b_short": (4.2, SEEDS[9:13], "cb_0924", {"r3s", "r3n"}),
    "n_new1": (4.2, SEEDS, "cb_0924", set()),
    "n_new2": (3.4, SEEDS, "cb_0924", set()),
}
TRACK_A_ONLY = "t_tracka"              # round 3, a J-file row, no craft
GONE = "g_gone"                        # round 3 only


def _session(model, seed, variant="", judge=None):
    dialogue = [{"turn": 0, "role": "character", "name": "Ren",
                 "content": "Opening for %s." % seed}]
    for t in range(1, 5):
        dialogue.append({"turn": 2 * t - 1, "role": "user", "name": "Alex",
                         "content": "I wait (%d)." % t})
        dialogue.append({"turn": 2 * t, "role": "character", "name": "Ren",
                         "content": (PROSE % model) + " %s %s %d" % (seed, variant, t)})
    s = {"seed_id": seed, "test_model": model, "character_name": "Ren",
         "user_name": "Alex", "num_turns": 4, "test_model_id": "vendor/" + model,
         "dialogue": dialogue}
    if judge is not None:
        s["judges"] = {"claude_sonnet": {"model": "anthropic/claude-sonnet-4",
                                         "scores": {"overall": judge}}}
    return s


def _old(model, seed):
    base = ROSTER.get(model, (4.0,))[0]
    k = SEEDS.index(seed)
    return round(min(5.0, max(1.0, base + (0.1 if k % 2 else -0.1) + 0.01 * (k % 3))), 2)


def _new(model, seed):
    return round(max(1.0, _old(model, seed) - 0.5 - (0.2 if model.startswith("b_") else 0)), 2)


def _dump(path, obj):
    path.write_text(json.dumps(obj))


class Fixture:
    def __init__(self, root):
        self.d = Path(root)
        self.results = self.d / "results"
        self.results.mkdir()
        merged, cb21, cb24, r3s, r3n = [], [], [], [], []
        v2_rows, legacy_rows = [], []
        for m, (_, seeds, where, rounds) in ROSTER.items():
            for seed in SEEDS:
                if "r3s" in rounds:
                    r3s.append(_session(m, seed, "june", judge=_old(m, seed) - 0.02))
                if "r3n" in rounds:
                    r3n.append(_session(m, seed.replace("adv", "nsfw"), "nsfw"))
            if m == "a_regen":                      # round-2 copy, old text
                for seed in CORE:
                    merged.append(_session(m, seed, "april", judge=4.9))
            for seed in seeds:
                stored = where in ("merged", "cb_0921")
                s = _session(m, seed, "r4", judge=_old(m, seed) if stored else None)
                {"merged": merged, "cb_0921": cb21, "cb_0924": cb24}[where].append(s)
                h = transcript_hash(s)
                v2_rows.append({
                    "session_id": "%s::%s" % (m, seed), "model": m, "seed": seed,
                    "judge": OV.JUDGE, "overall": _new(m, seed), "transcript_hash": h,
                    "session_dimensions": {d: _new(m, seed) for d in OV.DIMENSIONS[1:]}})
                if not stored:
                    legacy_rows.append(self.legacy_row(s))
        for m in (TRACK_A_ONLY, GONE):
            for seed in SEEDS:
                r3s.append(_session(m, seed, "june", judge=2.5))
                r3n.append(_session(m, seed.replace("adv", "nsfw"), "nsfw"))
        _dump(self.results / "multiturn_merged_all_v2.json", {"sessions": merged})
        _dump(self.results / "craft_baseline_20260921_125936.json", {"sessions": cb21})
        _dump(self.results / "craft_baseline_20260924_231143.json", {"sessions": cb24})
        _dump(self.results / "round3gen_R2_adversarial_catchup.json", {"sessions": r3s})
        _dump(self.results / "round3gen_R3_nsfw.json", {"sessions": r3n})
        self.v2_rows, self.legacy_rows = v2_rows, legacy_rows
        self.write_scores()
        r3_models = [m for m, v in ROSTER.items() if "r3n" in v[3]] + [TRACK_A_ONLY, GONE]
        table = sorted(({"model": m, "n": 20, "refusal_rate_pct": 5.0 if m == "b_r3one" else 0.0,
                         "sonnet_overall": round(ROSTER.get(m, (2.5,))[0] + 0.1, 2)}
                        for m in r3_models), key=lambda r: -r["sonnet_overall"])
        table[1]["sonnet_overall"] = table[0]["sonnet_overall"]      # a published tie
        _dump(self.results / "round3_nsfw_leaderboard.json", {"leaderboard": table})
        arena = [m for m, v in ROSTER.items() if "r2" in v[3]]
        _dump(self.results / "multiturn_arena_bayesian.json", {
            "n_votes": 100, "n_voters": None, "n_votes_not_scored": 0,
            "leaderboard": [{"rank": i + 1, "model": m, "elo_mean": 1600 - 20 * i,
                             "ci_low_95": 1500 - 20 * i, "ci_high_95": 1700 - 20 * i,
                             "n_votes": 20 + i} for i, m in enumerate(arena)]})
        j_models = ["a_regen", "b_r3one", "b_r3two", "b_short", "n_new1", "n_new2",
                    "a_same1", TRACK_A_ONLY]
        jl = []
        for i, m in enumerate(j_models):
            ranked = m not in ("b_short", TRACK_A_ONLY)
            jl.append({"model": m, "J": None if m == TRACK_A_ONLY else round(0.6 - 0.1 * i, 3),
                       "rank": None, "ranked": ranked,
                       "unranked_reason": None if ranked else "reduced",
                       "over_refusal_hard_rungs": 0.1 + 0.05 * i})
        r = 1
        for row in jl:
            if row["ranked"]:
                row["rank"], r = r, r + 1
        _dump(self.results / "round4_willingness_leaderboard.json", {"leaderboard": jl})
        tiers = {m: ("A" if ROSTER[m][0] >= 4.2 else "B") for m in ROSTER if m != "b_short"}
        rows = [{"model": m, "J": ({"value": x["J"], "display": "%+.2f" % x["J"],
                                    "status": "ranked", "unranked_reason": None}
                                   if (x := next((j for j in jl if j["model"] == m), None))
                                   and x["J"] is not None else None)}
                for m in ROSTER]
        _dump(self.results / "round4_overview.json", {
            "rows": rows, "unranked": [], "absent": [
                {"model": TRACK_A_ONLY, "J": {"value": None, "display": "no J"}}],
            "judge_means": {"models": {m: {"tier": tiers.get(m)} for m in ROSTER}},
            "bands": {"ranges": [{"tier": "A", "label": "3.8 and above"},
                                 {"tier": "B", "label": "3.2-3.8"}]}})

    @staticmethod
    def legacy_row(s, **over):
        row = {"session_id": "%s::%s" % (s["test_model"], s["seed_id"]),
               "model": s["test_model"], "seed": s["seed_id"],
               "transcript_hash": transcript_hash(s),
               "judge_view_hash": L.judge_view_hash(s), "judge": L.JUDGE_LABEL,
               "prompt_hash": L.EXPECTED_PROMPT_HASH, "overall": _old(s["test_model"], s["seed_id"]),
               "raw_parse_ok": True}
        row.update(over)
        return row

    def write_scores(self):
        with open(self.results / "session_judge_v2.jsonl", "w") as fh:
            for r in self.v2_rows:
                fh.write(json.dumps(r) + "\n")
        with open(self.results / "session_judge_v1_legacy.jsonl", "w") as fh:
            for r in self.legacy_rows:
                fh.write(json.dumps(r) + "\n")


def _small(fn):
    """Small bootstrap sizes, so the synthetic build takes a second."""
    def wrapped(*a, **kw):
        old = (C.CORR_BOOT, C.PERM, C.XFAM_BOOT)
        C.CORR_BOOT, C.PERM, C.XFAM_BOOT = 200, 500, 100
        try:
            return fn(*a, **kw)
        finally:
            C.CORR_BOOT, C.PERM, C.XFAM_BOOT = old
    return wrapped


class Synthetic(unittest.TestCase):
    @classmethod
    @_small
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.fx = Fixture(cls.tmp.name)
        cls.doc = C.build(cls.fx.results, boot=300)
        cls.rows = {r["model"]: r for r in cls.doc["rows"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_core_seeds_are_09_to_20(self):
        self.assertEqual(C.core_seeds(SEEDS), CORE)
        self.assertEqual(self.doc["core_seeds"]["seeds"], CORE)

    def test_returning_models_and_roster(self):
        ro = self.doc["roster"]
        want = sorted([m for m, v in ROSTER.items() if v[3]] + [TRACK_A_ONLY])
        self.assertEqual(sorted(self.rows), want)
        self.assertEqual(ro["returning_track_a_only"], [TRACK_A_ONLY])
        self.assertEqual(ro["new_models"], ["n_new1", "n_new2"])
        self.assertEqual([g["model"] for g in ro["not_returning"]], [GONE])
        t = self.rows[TRACK_A_ONLY]
        self.assertEqual(t["round4"], "Track A only")
        self.assertIsNone(t["old_judge_r4"])
        self.assertEqual(t["same_transcripts"]["flag"], "no_round4_craft")

    def test_band_is_the_core_mean_with_a_half_width(self):
        b = self.rows["a_same1"]["old_judge_r4"]
        want = sum(_old("a_same1", s) for s in CORE) / len(CORE)
        self.assertAlmostEqual(b["mean"], round(want, 2))
        self.assertEqual(b["n_sessions"], 12)
        self.assertGreaterEqual(b["half_width"], 0)
        self.assertLessEqual(b["low"], want + 1e-9)
        self.assertGreaterEqual(b["high"], want - 1e-9)
        self.assertNotIn("rank", b)

    def test_twelve_and_twenty_seed_models_use_the_same_seeds(self):
        """a_same2 played only the core; a_same1 all 20. Both bands are over
        the 12 core seeds, so seeds 01-08 never enter."""
        self.assertEqual(self.rows["a_same2"]["old_judge_r4"]["n_sessions"], 12)
        self.assertEqual(self.rows["a_same1"]["old_judge_r4"]["n_sessions"], 12)

    def test_a_model_short_of_the_core_gets_no_band(self):
        r = self.rows["b_short"]
        self.assertIsNone(r["old_judge_r4"])
        self.assertEqual(r["old_judge_r4_missing"], "4 of the 12 core seeds")
        self.assertIn("b_short", self.doc["old_judge"]["not_banded"])

    def test_new_models_get_a_band_too(self):
        self.assertIn("n_new1", self.doc["old_judge"]["models"])
        self.assertNotIn("n_new1", self.rows)

    def test_score_sources(self):
        self.assertEqual(self.rows["a_same1"]["old_judge_r4"]["scores"], "stored")
        self.assertEqual(self.rows["a_regen"]["old_judge_r4"]["scores"], "backfill")
        self.assertEqual(self.rows["b_r3one"]["old_judge_r4"]["scores"], "stored")

    def test_same_or_regenerated(self):
        self.assertEqual(self.rows["a_same1"]["same_transcripts"]["flag"], "same")
        st = self.rows["a_regen"]["same_transcripts"]
        self.assertEqual((st["flag"], st["compared_with"]), ("regenerated", "round 2"))
        st = self.rows["b_r3one"]["same_transcripts"]
        self.assertEqual((st["flag"], st["compared_with"], st["generated"]),
                         ("regenerated", "round 3 standard track", "2026-09-21"))
        self.assertEqual(self.rows["a_regen"]["r2_human"]["voted_transcripts"],
                         "regenerated since the vote")
        self.assertEqual(self.rows["a_same1"]["r2_human"]["voted_transcripts"],
                         "identical to round 4")

    def test_the_stale_round2_score_is_not_used(self):
        """a_regen's round-2 copy scored 4.9 on the old text; its band comes
        from the backfill on the new text."""
        self.assertLess(self.rows["a_regen"]["old_judge_r4"]["mean"], 4.5)

    def test_r3_positions_are_as_published_and_ties_are_marked(self):
        t, _ = C.r3_table(self.fx.results)
        top = sorted(t.values(), key=lambda r: r["rank"])
        self.assertEqual([r["rank"] for r in top], list(range(1, len(top) + 1)))
        self.assertEqual((top[0]["tie"], top[1]["tie"]), ("1-2", "1-2"))
        self.assertIsNone(top[2]["tie"])
        self.assertIn("not comparable with J", top[0]["refusal_instrument"])

    def test_r3_table_out_of_order_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / C.R3_TABLE
            _dump(p, {"leaderboard": [{"model": "x", "n": 1, "sonnet_overall": 3.0},
                                      {"model": "y", "n": 1, "sonnet_overall": 4.0}]})
            with self.assertRaises(C.InputError):
                C.r3_table(d)

    def test_j_is_copied(self):
        j = self.rows["b_r3one"]["J"]
        self.assertTrue(j["ranked"])
        self.assertEqual(j["display"], "%+.2f" % j["value"])
        self.assertIsNone(self.rows[TRACK_A_ONLY]["J"]["value"])

    def test_model_drift_is_paired_by_seed(self):
        d = self.doc["model_drift"]["models"]["b_r3one"]
        self.assertAlmostEqual(d["change"], 0.02, places=6)   # June was 0.02 lower
        self.assertEqual(d["seeds"], 20)
        self.assertTrue(d["setup"].startswith("same as June"))

    def test_correlations_carry_n_and_an_interval(self):
        for x in self.doc["correlations"]:
            with self.subTest(x["id"]):
                self.assertIn("n", x)
                if x.get("spearman") is not None:
                    lo, hi = x["ci95"]
                    self.assertLessEqual(lo, hi)
                    self.assertTrue(-1 <= x["spearman"] <= 1)

    def test_what_is_never_written(self):
        blob = json.dumps(self.doc)
        self.assertEqual(list(C.forbidden_hits(self.doc)), [])
        for word in ('"composite"', '"old_scale"', '"translated"', '"refusal_r4"'):
            self.assertNotIn(word, blob)
        self.assertEqual(self.doc["willingness"]["comparable"], False)
        doc = json.loads(blob)
        doc["rows"][0]["old_judge_r4"] = dict(doc["rows"][0]["old_judge_r4"] or {},
                                              old_judge_rank=1)
        doc["judge_bridge"]["v2_on_old_scale"] = {}
        self.assertEqual(len(list(C.forbidden_hits(doc))), 2)

    def test_instruments_table_says_comparable_or_why_not(self):
        whats = [i["what"] for i in self.doc["instruments"]]
        self.assertEqual(whats, ["Craft judge", "Flaw hunter", "Headline",
                                 "Willingness instrument", "Track and simulator",
                                 "Roster", "Composite"])
        for i in self.doc["instruments"]:
            self.assertTrue(i["how"].startswith("comparable via" if i["comparable"]
                                                else "not comparable, because"), i)

    def test_markdown_orders_by_tier_not_by_old_judge(self):
        md = C.render_markdown(self.doc)
        body = [ln for ln in md.splitlines() if ln.startswith("| ") and "Model" not in ln]
        models = [ln.split("|")[1].strip() for ln in body]
        tiers = [self.rows[m]["v2_tier"]["tier"] if self.rows[m]["v2_tier"] else "Z"
                 for m in models]
        self.assertEqual(tiers, sorted(tiers))
        self.assertIn("no J (Track A only)", md)
        self.assertNotIn("—", md)

    def test_same_inputs_same_bytes(self):
        again = _small(C.build)(self.fx.results, boot=300)
        self.assertEqual(json.dumps(again, sort_keys=True),
                         json.dumps(self.doc, sort_keys=True))


class FailClosed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _fails(self, pattern):
        self.fx.write_scores()
        with self.assertRaisesRegex(OV.InputError, pattern):
            C.load_scores(self.fx.results)

    def test_backfill_row_on_another_text(self):
        self.fx.legacy_rows[0]["transcript_hash"] = "0" * 16
        self._fails("different text")

    def test_backfill_row_that_did_not_parse(self):
        self.fx.legacy_rows[0].update(raw_parse_ok=False, overall=None)
        self._fails("did not parse")

    def test_backfill_row_from_another_prompt(self):
        self.fx.legacy_rows[0]["prompt_hash"] = "deadbeef0000"
        self._fails("not the round-2/3 judge")

    def test_a_session_scored_twice(self):
        stored = next(r for r in self.fx.v2_rows if r["model"] == "a_same1")
        s = next(x for x in json.loads((self.fx.results / "multiturn_merged_all_v2.json")
                                       .read_text())["sessions"]
                 if x["test_model"] == "a_same1" and x["seed_id"] == stored["seed"])
        self.fx.legacy_rows.append(Fixture.legacy_row(s))
        self._fails("scored twice")

    def test_clean_inputs_load(self):
        _, v2, v1, src = C.load_scores(self.fx.results)
        self.assertEqual(set(v1), set(v2))
        self.assertIn("backfill_2026_09_27", set(src.values()))


class RealFile(unittest.TestCase):
    """The committed results/round4_continuity.json, read only (no rebuild)."""

    @classmethod
    def setUpClass(cls):
        p = ROOT / "results" / C.OUT
        if not p.exists():
            raise unittest.SkipTest("no results/%s" % C.OUT)
        cls.doc = json.loads(p.read_text())

    def test_roster_2026_09_27(self):
        ro = self.doc["roster"]
        self.assertEqual((ro["returning"], ro["returning_craft"], ro["new"]), (41, 40, 30))
        self.assertEqual(ro["returning_track_a_only"], ["rocinante_12b"])
        gone = {g["model"]: g["note"] for g in ro["not_returning"]}
        self.assertIn("LongCat-2.0", gone["owl_alpha"])
        self.assertEqual(len(self.doc["rows"]), 41)

    def test_bands_not_ranks_and_one_session_set(self):
        self.assertEqual(len(self.doc["core_seeds"]["seeds"]), 12)
        for m, b in self.doc["old_judge"]["models"].items():
            with self.subTest(m):
                self.assertEqual(b["n_sessions"], 12)
                self.assertFalse({"rank", "position"} & set(b))
        self.assertEqual(list(C.forbidden_hits(self.doc)), [])

    def test_built_from_the_current_inputs(self):
        for name, h in self.doc["inputs"].items():
            with self.subTest(name):
                self.assertEqual(OV.sha(ROOT / "results" / name), h,
                                 "%s changed since round4_continuity.json was built; "
                                 "rerun analyze_round4_continuity.py" % name)

    def test_every_old_judge_score_is_on_the_current_text(self):
        oj = self.doc["old_judge"]
        self.assertEqual(oj["sessions"], oj["corpus_sessions"])
        self.assertEqual(oj["prompt_hash"], L.EXPECTED_PROMPT_HASH)


if __name__ == "__main__":
    unittest.main()
