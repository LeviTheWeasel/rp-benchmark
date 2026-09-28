"""analyze_round4_second_judge.py on a synthetic results/ directory, plus a
read-only check of the real results/round4_second_judge.json when present.

Run by path from the repo root, offline:
    python -m unittest tests/test_round4_second_judge.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import analyze_round4_overview as OV  # noqa: E402
import analyze_round4_second_judge as SJ  # noqa: E402
import publication_guards as PG  # noqa: E402
from external_judge_schema import SESSION_KEYS, STANDARD_KEYS  # noqa: E402
from transcript_hash import transcript_hash  # noqa: E402

SEEDS = ["adv_case_%02d" % i for i in range(1, 21)]
PROSE = ("The lantern gutters and the rain keeps on at the shutters, slow and "
         "patient, while %s watches the door and counts the steps outside.")
# model: Sonnet's base score; the second judge sees Sonnet minus 0.8, less
# 0.3 on Claude sessions and plus 0.5 on OpenAI ones (planted vendor terms).
BASES = {"claude_a": 4.35, "claude_b": 4.05, "gpt_x": 3.95, "m_top": 4.25,
         "m_mid": 3.55, "m_low": 2.95, "m_floor": 2.35, "m_b": 3.35,
         "m_c": 3.75, "m_d": 2.75}
SHORT = "m_short"                     # 4 seeds: listed, never tiered
BLANK = ("m_low", SEEDS[4])           # a whole blank scene, 1.0 from both
BRIDGE = [("m_mid", SEEDS[i]) for i in range(6)]
REUSED = [("m_b", SEEDS[i]) for i in range(3)]


def _session(model, seed, blank=False):
    dialogue = [{"turn": 0, "role": "character", "content": "Opening for %s." % seed}]
    for t in range(1, 5):
        dialogue.append({"turn": 2 * t - 1, "role": "user", "content": "I wait (%d)." % t})
        dialogue.append({"turn": 2 * t, "role": "character",
                         "content": "" if blank else (PROSE % model) + " %s %d" % (seed, t)})
    return {"seed_id": seed, "test_model": model, "user_name": "Alex",
            "test_model_id": "vendor/" + model, "dialogue": dialogue}


def _sonnet(model, seed):
    k = SEEDS.index(seed)
    v = BASES.get(model, 3.1) + (0.1 if k % 2 else -0.1) + 0.03 * (k % 3) - 0.03
    return round(min(5.0, max(1.0, v)), 2)


def _chatgpt(model, seed, harness="app"):
    k = SEEDS.index(seed)
    v = _sonnet(model, seed) - 0.8 + 0.04 * ((k * 7) % 5 - 2)
    if model.startswith("claude_"):
        v -= 0.3
    if model.startswith("gpt_"):
        v += 0.5
    if harness == "agent":
        v += 0.05
    return round(min(5.0, max(1.0, v)), 2)


def _row(oid, overall):
    dims = {k: {"score": overall, "rationale": "r"} for k in SESSION_KEYS}
    dims["S.5_agency_respect_session"]["violation_count"] = 0
    dims["S.6_temporal_reasoning"]["contradictions"] = []
    return {"session_id": oid, "session_dimensions": dims,
            "standard_dimensions": {k: {"score": overall, "rationale": "r"}
                                    for k in STANDARD_KEYS},
            "quality_trajectory": {"early_quality": overall, "mid_quality": overall,
                                   "late_quality": overall, "degradation_detected": False},
            "overall": overall, "overall_notes": "n"}


def _dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


class Fixture:
    def __init__(self, root):
        self.results = Path(root) / "results"
        self.results.mkdir()
        sessions, v2 = [], []
        plan = [(m, s) for m in BASES for s in SEEDS] + [(SHORT, s) for s in SEEDS[:4]]
        for m, seed in plan:
            blank = (m, seed) == BLANK
            s = _session(m, seed, blank)
            sessions.append(s)
            sc = 1.0 if blank else _sonnet(m, seed)
            v2.append({"session_id": "%s::%s" % (m, seed), "model": m, "seed": seed,
                       "judge": OV.JUDGE, "overall": sc, "transcript_hash": transcript_hash(s),
                       "session_dimensions": {d: sc for d in OV.DIMENSIONS[1:]}})
        self.sessions, self.v2 = sessions, v2
        _dump(self.results / "craft_baseline_20260101_000000.json",
              {"config": {"user_sim_model": "vendor/sim"}, "sessions": sessions})
        with open(self.results / "session_judge_v2.jsonl", "w") as fh:
            for r in v2:
                fh.write(json.dumps(r) + "\n")
        answered = {}
        for s in sessions:
            n = sum(1 for t in s["dialogue"] if t["role"] == "character" and t["turn"]
                    and len(t["content"].strip()) >= OV.MIN_CHARS)
            answered[s["test_model"]] = answered.get(s["test_model"], 0) + n
        _dump(self.results / "production_defects.json",
              {"per_model": {m: {"turns": n, "selfplay_turns": 0, "leak_turns": 0,
                                 "loop_turns": 0} for m, n in answered.items()
                             if n >= OV.DEFECTS_MIN_TURNS}})
        self.write_package()

    def write_package(self, mutate=None):
        keymap, hashes, sources, app, reused = {}, {}, {}, [], []
        agent_rows, refs = [], {}
        for i, r in enumerate(self.v2):
            sid, m, seed = r["session_id"], r["model"], r["seed"]
            blank = (m, seed) == BLANK
            score = 1.0 if blank else _chatgpt(m, seed)
            hashes[sid] = r["transcript_hash"]
            if (m, seed) in REUSED:
                oid = "s%03d" % len(agent_rows)
                agent_rows.append(_row(oid, _chatgpt(m, seed, "agent")))
                refs[sid] = {"package": "results/judge_prior_chatgpt",
                             "subdir": "external_blind_pass", "opaque": oid,
                             "file": "external_part01.json",
                             "transcript_hash": r["transcript_hash"]}
                keymap[oid], sources[oid] = sid, "judge_prior_chatgpt/external_blind_pass"
                reused.append(agent_rows[-1])
                continue
            oid = "f%04d" % i
            keymap[oid], sources[oid] = sid, SJ.APP_SOURCE
            app.append(_row(oid, score))
            if (m, seed) in BRIDGE:
                aoid = "s%03d" % len(agent_rows)
                agent_rows.append(_row(aoid, _chatgpt(m, seed, "agent")))
                refs[sid] = {"package": "results/judge_prior_chatgpt",
                             "subdir": "external_blind_pass", "opaque": aoid,
                             "file": "external_part01.json",
                             "transcript_hash": r["transcript_hash"]}
        if mutate:
            mutate(app, keymap, hashes)
        merged = self.results / "judge_full_chatgpt" / "merged"
        _dump(merged / "external_part_app.json", app)
        _dump(merged / "external_part_reused_prior_chatgpt.json", reused)
        _dump(merged / "_manifest.json", {"package": "judge_full_chatgpt/merged",
                                          "session_ids": sorted(keymap.values()),
                                          "keymap": keymap, "transcript_hashes": hashes,
                                          "sources": sources})
        _dump(self.results / "judge_prior_chatgpt" / "external_blind_pass"
              / "external_part01.json", agent_rows)
        _dump(self.results / "judge_full_chatgpt" / "_manifest.json",
              {"package": "judge_full_chatgpt", "keymap": {},
               "bridge": sorted("%s::%s" % b for b in BRIDGE), "reused": refs})
        return merged


def _build(results, **kw):
    kw.setdefault("seed_boot", 200)
    kw.setdefault("model_boot", 150)
    return SJ.build(results, **kw)


class Synthetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.fx = Fixture(cls.tmp.name)
        cls.doc = _build(cls.fx.results)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_coverage_and_sources(self):
        cov = self.doc["coverage"]
        self.assertEqual(cov["corpus_sessions"], len(self.fx.v2))
        self.assertEqual(cov["sessions_with_both"], len(self.fx.v2))
        self.assertEqual(cov["tiered_models"], len(BASES))
        self.assertEqual([u["model"] for u in cov["untiered"]], [SHORT])
        self.assertEqual(cov["bridge_sessions"], len(BRIDGE))
        src = self.doc["judges"]["second"]["rows_by_source"]
        self.assertEqual(src["judge_prior_chatgpt/external_blind_pass"], len(REUSED))

    def test_the_floor_session_is_left_out_of_agreement_only(self):
        sa = self.doc["session_agreement"]
        self.assertEqual(sa["excluded_both_at_floor"], ["%s::%s" % BLANK])
        self.assertEqual(sa["sessions"], len(self.fx.v2) - 1)
        for d in OV.DIMENSIONS:
            blk = sa["dimensions"][d]
            self.assertEqual(blk["n"], len(self.fx.v2) - 1)
            self.assertEqual(len(blk["pearson_ci95"]), 2)
            self.assertLessEqual(blk["pearson_ci95"][0], blk["pearson_ci95"][1])

    def test_offset_is_the_mean_model_difference(self):
        m = self.doc["models"]
        tiered = [k for k, r in m.items() if r["basis"] == "seed_adjusted"]
        want = np.mean([m[k]["sonnet"]["overall"] - m[k]["chatgpt"]["overall"]
                        for k in tiered])
        self.assertAlmostEqual(self.doc["scale"]["offset"]["value"], want, places=2)
        # planted: 0.8 for everyone, 1.1 for 2 Claude models, 0.3 for 1 OpenAI
        self.assertAlmostEqual(want, 0.8 + (2 * 0.3 - 0.5) / len(BASES), places=1)

    def test_letters_raw_after_offset_and_moves(self):
        t = self.doc["tiers"]
        self.assertEqual(t["models"], len(BASES))
        m = self.doc["models"]
        for k, r in m.items():
            if r["basis"] != "seed_adjusted":
                self.assertIsNone(r["tier_depends_on_judge"])
                continue
            self.assertEqual(r["chatgpt"]["tier"], OV.tier_letter(r["chatgpt"]["overall"]))
            self.assertEqual(r["chatgpt"]["tier_after_offset"],
                             OV.tier_letter(r["chatgpt"]["overall_after_offset"]))
            self.assertEqual(r["tier_depends_on_judge"],
                             r["chatgpt"]["tier_after_offset"] != r["sonnet"]["tier"])
        moved = {x["model"] for x in t["after_offset"]["moves"]}
        self.assertEqual(moved, set(t["after_offset"]["tier_depends_on_judge"]))
        self.assertEqual(t["after_offset"]["same_letter"] + len(moved), len(BASES))
        # the planted +0.5 lifts gpt_x under ChatGPT: positive difference
        self.assertGreater(m["gpt_x"]["difference_after_offset"], 0.3)
        self.assertTrue(m["gpt_x"]["beyond_band"])

    def test_vendor_terms_recover_what_was_planted(self):
        p = self.doc["vendor_premiums"]
        c = p["claude_sonnet_over_chatgpt"]
        self.assertGreater(c["regression"]["coefficient"], 0.15)
        self.assertGreater(c["rescaled_difference"]["vs_rest"], 0.1)
        self.assertLess(c["reverse_regression"]["coefficient"], 0)
        o = p["openai_chatgpt_over_sonnet"]
        self.assertGreater(o["regression"]["coefficient"], 0.3)
        self.assertEqual(o["group_models"], 1)
        self.assertIsNone(o["regression"]["ci95_model_resampled"])   # one model
        self.assertEqual(c["group_models"], 2)
        self.assertEqual(len(c["regression"]["ci95_model_resampled"]), 2)
        self.assertIn("regression", p["claude_letter_check"])

    def test_bridge_block(self):
        b = self.doc["bridge"]
        self.assertEqual(b["n"], len(BRIDGE))
        self.assertAlmostEqual(b["app_vs_agent"]["mean_diff_app_minus_agent"], -0.05,
                               places=2)

    def test_sensitivity_variants(self):
        sens = self.doc["sensitivity"]
        self.assertEqual(set(sens), {"all_rows", "without_reused_rows",
                                     "without_bridge_sessions", "app_rows_without_bridge",
                                     "bridge_on_agent_rows"})
        self.assertEqual(sens["all_rows"]["sessions"], len(self.fx.v2))
        self.assertEqual(sens["without_reused_rows"]["sessions"],
                         len(self.fx.v2) - len(REUSED))
        self.assertEqual(sens["app_rows_without_bridge"]["sessions"],
                         len(self.fx.v2) - len(REUSED) - len(BRIDGE))
        self.assertEqual(sens["all_rows"]["tier_depends_changes_vs_all_rows"],
                         {"added": [], "removed": []})

    def test_the_overview_column_is_the_same_computation(self):
        merged = self.fx.results / SJ.MERGED
        _, ov = OV.build(self.fx.results, boot=5, cross=[("chatgpt", str(merged))])
        top = ov["cross_judges"]["chatgpt"]
        self.assertEqual(top["label"], SJ.LABEL)
        self.assertAlmostEqual(top["scale_offset"]["value"],
                               self.doc["scale"]["offset"]["value"], places=3)
        self.assertEqual(top["tier_depends_on_judge"],
                         self.doc["tiers"]["after_offset"]["tier_depends_on_judge"])
        for r in ov["rows"] + ov["unranked"]:
            c = r["cross_judges"]["chatgpt"]
            mine = self.doc["models"][r["model"]]
            with self.subTest(model=r["model"]):
                self.assertAlmostEqual(c["mean"], mine["chatgpt"]["overall"], places=4)
                self.assertEqual(c["tier"], mine["chatgpt"]["tier"])
                self.assertEqual(c["tier_depends_on_judge"], mine["tier_depends_on_judge"])
        self.assertIn("Two judge families", ov["columns"]["judge_tier"]["caveats"][0])

    def test_seed_bootstrap_replays_the_overviews_draws(self):
        elo, _ = OV.build(self.fx.results, boot=200)
        want = {r["model"]: (r["mean_lo"], r["mean_hi"]) for r in elo["models"]}
        for m, r in self.doc["models"].items():
            if r["basis"] == "seed_adjusted":
                with self.subTest(model=m):
                    self.assertAlmostEqual(r["sonnet"]["ci95"][0], want[m][0], places=4)
                    self.assertAlmostEqual(r["sonnet"]["ci95"][1], want[m][1], places=4)

    def test_no_keymap_in_the_output(self):
        PG._guard_keymap(self.doc, SJ.OUT)
        self.assertNotIn('"keymap"', json.dumps(self.doc))

    def test_same_inputs_same_bytes(self):
        a = json.dumps(_build(self.fx.results), sort_keys=True)
        self.assertEqual(a, json.dumps(self.doc, sort_keys=True))

    def test_reading_is_written_from_the_numbers(self):
        r = self.doc["reading"]
        self.assertTrue(r["can_establish"] and r["cannot_establish"] and r["round4_tiers"])
        blob = json.dumps(r)
        self.assertIn("Which judge is right", blob)
        self.assertNotIn("—", blob)


class FailClosed(unittest.TestCase):
    def _fx(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        return Fixture(self.tmp.name)

    def test_a_row_that_fails_the_schema(self):
        fx = self._fx()
        fx.write_package(lambda app, km, h: app[0].pop("overall_notes"))
        with self.assertRaisesRegex(SJ.InputError, "overall_notes"):
            _build(fx.results)

    def test_an_id_not_in_the_keymap(self):
        fx = self._fx()
        fx.write_package(lambda app, km, h: app[0].update(session_id="zz_unknown"))
        with self.assertRaisesRegex(SJ.InputError, "not in the keymap"):
            _build(fx.results)

    def test_two_rows_for_one_session(self):
        fx = self._fx()
        fx.write_package(lambda app, km, h: app.append(dict(app[1], session_id="f9999"))
                         or km.update(f9999=km[app[1]["session_id"]]))
        with self.assertRaisesRegex(SJ.InputError, "a second row"):
            _build(fx.results)

    def test_a_stale_row_is_dropped_and_counted(self):
        fx = self._fx()

        def stale(app, km, h):
            h[km[app[0]["session_id"]]] = "0" * 16
        fx.write_package(stale)
        doc = _build(fx.results)
        self.assertEqual(doc["judges"]["second"]["stale_dropped"], 1)
        self.assertEqual(doc["coverage"]["sessions_with_both"], len(fx.v2) - 1)


class Helpers(unittest.TestCase):
    def test_avg_ranks_share_ties(self):
        np.testing.assert_allclose(SJ.avg_ranks([3, 1, 3, 2]), [2.5, 0, 2.5, 1])

    def test_ols_recovers_a_planted_group_term(self):
        rng = np.random.default_rng(1)
        ref = rng.uniform(1, 5, 400)
        g = rng.random(400) < 0.3
        y = 0.5 + 0.9 * ref + 0.25 * g + rng.normal(0, 0.01, 400)
        coef, se = SJ.ols_group(y, ref, g)
        self.assertAlmostEqual(coef, 0.25, places=2)
        self.assertLess(se, 0.01)

    def test_tier_index_array_matches_the_letters(self):
        v = np.array([4.5, 3.8, 3.79, 3.2, 2.0, 1.99])
        self.assertEqual([SJ.letter(i) for i in SJ.tier_index_array(v)],
                         [OV.tier_letter(x) for x in v])


class RealFile(unittest.TestCase):
    """The committed results/round4_second_judge.json, read only (no rebuild)."""

    @classmethod
    def setUpClass(cls):
        p = ROOT / "results" / SJ.OUT
        if not p.exists():
            raise unittest.SkipTest("no results/%s" % SJ.OUT)
        cls.doc = json.loads(p.read_text())
        ov = ROOT / "results" / "round4_overview.json"
        cls.ov = json.loads(ov.read_text()) if ov.exists() else None

    def test_built_from_the_current_inputs(self):
        for name, h in self.doc["inputs"].items():
            with self.subTest(name):
                self.assertEqual(OV.sha(ROOT / "results" / name), h,
                                 "%s changed since round4_second_judge.json was built; "
                                 "rerun analyze_round4_second_judge.py" % name)

    def test_every_session_scored_by_both(self):
        cov = self.doc["coverage"]
        self.assertEqual(cov["sessions_with_both"], cov["corpus_sessions"])
        self.assertEqual(self.doc["judges"]["second"]["label"],
                         "ChatGPT via Codex (subscription, blind)")
        self.assertEqual(self.doc["judges"]["second"]["stale_dropped"], 0)

    def test_agrees_with_the_overview_column(self):
        if not self.ov or "chatgpt" not in (self.ov.get("cross_judges") or {}):
            self.skipTest("the overview has no chatgpt column")
        top = self.ov["cross_judges"]["chatgpt"]
        self.assertEqual(top["tier_depends_on_judge"],
                         self.doc["tiers"]["after_offset"]["tier_depends_on_judge"])
        self.assertAlmostEqual(top["scale_offset"]["value"],
                               self.doc["scale"]["offset"]["value"], places=3)
        for r in self.ov["rows"]:
            c = r["cross_judges"]["chatgpt"]
            with self.subTest(r["model"]):
                self.assertAlmostEqual(c["mean"],
                                       self.doc["models"][r["model"]]["chatgpt"]["overall"],
                                       places=4)
        edges = {m for m, r in self.doc["models"].items()
                 if r["sonnet"].get("interval_reaches_edge")}
        self.assertEqual(edges, set(self.ov["bands"]["edge_models"]))

    def test_no_keymap_and_no_published_letter_change(self):
        PG._guard_keymap(self.doc, SJ.OUT)
        for m, r in self.doc["models"].items():
            if self.ov and r["basis"] == "seed_adjusted":
                jm = self.ov["judge_means"]["models"][m]
                self.assertEqual(r["sonnet"]["tier"], jm["tier"])


if __name__ == "__main__":
    unittest.main()
