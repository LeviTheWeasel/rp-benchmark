"""Tests for analyze_round4_overview.py on synthetic inputs (no repo data)."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import analyze_round4_overview as O  # noqa: E402
from transcript_hash import transcript_hash  # noqa: E402

SEEDS = ["adv_seed_%02d" % i for i in range(12)]
PROSE = "The lantern gutters and the rain keeps on at the shutters, slow and patient."
SIM = "vendor/sim-model"


def session(model, seed, replies, model_id=None):
    dialogue = [{"turn": 0, "role": "character", "content": "Opening scene."}]
    for i, text in enumerate(replies):
        dialogue.append({"turn": 2 * i + 1, "role": "user", "content": "I wait."})
        dialogue.append({"turn": 2 * i + 2, "role": "character", "content": text})
    return {"seed_id": seed, "test_model": model, "user_name": "Alex",
            "test_model_id": model_id or "vendor/" + model, "dialogue": dialogue}


SELFPLAY = PROSE + "\nAlex: I stand and cross the room to the window."


def dims(score):
    """Session dimensions a fixed distance from `overall`, clipped to 1-5."""
    return {"S.5_agency_respect_session": min(5.0, round(score + 0.5, 2)),
            "S.1_consistency_over_time": round(score, 2),
            "S.3_narrative_momentum": max(1.0, round(score - 0.2, 2)),
            "S.2_degradation_resistance": round(score, 2)}


class Corpus:
    """A tiny results/ directory: 4 models x 12 seeds, one blank scene, and a
    4-seed model (listed, not tiered) that writes the user's character once."""

    SCORES = {"m_high": 4.3, "m_mid": 3.9, "m_low": 3.4, "m_blanky": 3.9,
              "m_short": 3.0}

    def __init__(self, root):
        self.root = Path(root)
        self.sessions, self.rows = [], []
        for m, base in self.SCORES.items():
            for i, seed in enumerate(SEEDS[:4] if m == "m_short" else SEEDS):
                replies = [PROSE] * 5
                score = base + (0.1 if i % 2 else -0.1)
                if m == "m_blanky" and i == 0:
                    replies, score = [""] * 5, 1.0
                if m == "m_mid" and i == 1:
                    replies = [PROSE, PROSE, "", "", ""]      # 2 of 5: partial
                if m == "m_short" and i == 2:
                    replies = [PROSE, SELFPLAY, PROSE, PROSE, PROSE]
                s = session(m, seed, replies,
                            model_id=SIM if m == "m_low" else None)
                self.sessions.append(s)
                self.rows.append({"session_id": "%s::%s" % (m, seed), "model": m,
                                  "seed": seed, "judge": O.JUDGE,
                                  "overall": round(score, 2),
                                  "session_dimensions": dims(score),
                                  "transcript_hash": transcript_hash(s)})

    def write(self, rows=None, extra_sources=()):
        self.root.mkdir(parents=True, exist_ok=True)
        write_json({"config": {"user_sim_model": SIM}, "sessions": self.sessions},
                   self.root / "craft_baseline_20260101_000000.json")
        for name, sessions in extra_sources:
            write_json({"config": {"user_sim_model": SIM}, "sessions": sessions},
                       self.root / name)
        with open(self.root / "session_judge_v2.jsonl", "w") as fh:
            for r in (self.rows if rows is None else rows):
                fh.write(json.dumps(r) + "\n")
        answered = {}
        for s in self.sessions:
            n = sum(1 for t in s["dialogue"] if t["role"] == "character" and t["turn"]
                    and len(t["content"].strip()) >= O.MIN_CHARS)
            answered[s["test_model"]] = answered.get(s["test_model"], 0) + n
        # like the real file: models under 50 answered turns are skipped
        write_json({"per_model": {m: {"turns": n, "selfplay_turns": 0, "leak_turns": 0,
                                      "loop_turns": 0} for m, n in answered.items()
                                  if n >= O.DEFECTS_MIN_TURNS}},
                   self.root / "production_defects.json")
        return self.root


def write_json(obj, path):
    with open(path, "w") as fh:
        json.dump(obj, fh)


def keys_of(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from keys_of(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from keys_of(v)


def quiet_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = O.main(argv)
    return code, out.getvalue(), err.getvalue()


class FixedTiers(unittest.TestCase):
    def test_the_letters_are_frozen_at_0_6_wide_edges(self):
        self.assertEqual(O.BAND_WIDTH, 0.6)
        self.assertEqual(O.TIER_EDGES,
                         tuple(round(O.BAND_TOP - O.BAND_WIDTH * k, 6) for k in (2, 3, 4, 5)))
        self.assertEqual([t[0] for t in O.TIERS], list("ABCDE"))
        self.assertEqual({L: O.tier_label(L) for L in "ABCDE"},
                         {"A": "3.8 and above", "B": "3.2-3.8", "C": "2.6-3.2",
                          "D": "2.0-2.6", "E": "below 2.0"})

    def test_lower_edge_inclusive_and_open_ends(self):
        self.assertEqual(O.tier_letter(3.8), "A")
        self.assertEqual(O.tier_letter(5.0 - 0.6 * 2), "A")    # 3.8000000000000003
        self.assertEqual(O.tier_letter(3.8 - 1e-12), "A")      # float noise only
        self.assertEqual(O.tier_letter(3.7999), "B")
        self.assertEqual(O.tier_letter(4.9), "A")              # above 4.4 stays A
        self.assertEqual(O.tier_letter(5.0), "A")
        self.assertEqual(O.tier_letter(3.2), "B")
        self.assertEqual(O.tier_letter(2.6), "C")
        self.assertEqual(O.tier_letter(2.0), "D")
        self.assertEqual(O.tier_letter(1.9999), "E")
        self.assertEqual(O.tier_letter(1.0), "E")

    def test_letters_never_move_when_a_model_is_added(self):
        base = {"x": 4.0, "y": 3.5, "z": 2.1}
        t1, m1 = O.assign_tiers(base)
        t2, m2 = O.assign_tiers(dict(base, top=4.9, floor=1.2))
        for m in base:
            self.assertEqual(t1[m]["tier"], t2[m]["tier"])
            self.assertEqual(t1[m]["band"], t2[m]["band"])
        self.assertEqual((t2["top"]["tier"], t2["floor"]["tier"]), ("A", "E"))
        self.assertEqual(m1["letters"], m2["letters"])
        self.assertEqual(m1["ranges"][0], {"tier": "A", "lower": 3.8, "upper": None,
                                           "label": "3.8 and above"})
        self.assertEqual(m1["ranges"][-1], {"tier": "E", "lower": None, "upper": 2.0,
                                            "label": "below 2.0"})
        self.assertEqual(m1["sizes"], {"A": 1, "B": 1, "C": 0, "D": 1, "E": 0})
        self.assertEqual(m1["empty"], ["C", "E"])
        self.assertEqual(m1["tiers"], 3)

    def test_tier_count_is_reported_not_changed(self):
        _, meta = O.assign_tiers({"a": 4.2, "b": 4.3})
        chk = O.tier_count_check(meta)
        self.assertEqual((chk["tiers"], chk["within"]), (1, False))
        _, meta = O.assign_tiers({"a": 4.2, "b": 3.5, "c": 2.9})
        self.assertTrue(O.tier_count_check(meta)["within"])


class EdgeMarker(unittest.TestCase):
    def test_crossing_and_touching_a_letter_edge_are_marked(self):
        means = {"inside": 4.1, "cross": 3.85, "touch_lo": 3.9, "touch_hi": 3.6,
                 "print_touch": 3.9, "near": 3.9}
        lo = {"inside": 3.9, "cross": 3.75, "touch_lo": 3.8, "touch_hi": 3.5,
              "print_touch": 3.80004, "near": 3.8001}
        hi = {"inside": 4.3, "cross": 3.95, "touch_lo": 4.0, "touch_hi": 3.8,
              "print_touch": 4.0, "near": 4.0}
        tiers, _ = O.assign_tiers(means, lo, hi)
        self.assertFalse(tiers["inside"]["edge"])
        self.assertTrue(tiers["cross"]["edge"])
        self.assertTrue(tiers["touch_lo"]["edge"])       # lower end ON 3.8
        self.assertTrue(tiers["touch_hi"]["edge"])       # upper end ON 3.8
        self.assertTrue(tiers["print_touch"]["edge"])    # 3.8000 at 4 decimals
        self.assertFalse(tiers["near"]["edge"])          # 3.8001 is clear

    def test_4_4_is_not_an_edge_because_a_is_open(self):
        tiers, _ = O.assign_tiers({"top": 4.4}, {"top": 4.2}, {"top": 4.6})
        self.assertEqual(tiers["top"]["tier"], "A")
        self.assertFalse(tiers["top"]["edge"])

    def test_spans_counts_the_letters_an_interval_touches(self):
        tiers, _ = O.assign_tiers({"a": 3.5, "b": 3.5}, {"a": 3.1, "b": 3.3},
                                  {"a": 3.9, "b": 3.7})
        self.assertEqual((tiers["a"]["spans"], tiers["b"]["spans"]), (3, 1))

    def test_no_interval_no_marker(self):
        tiers, _ = O.assign_tiers({"a": 4.2})
        self.assertIsNone(tiers["a"]["edge"])
        self.assertIsNone(tiers["a"]["spans"])


class FailClosed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.corpus = Corpus(Path(self.tmp.name) / "results")

    def tearDown(self):
        self.tmp.cleanup()

    def assert_fails_and_writes_nothing(self, rows=None, extra=(), pattern=None):
        root = self.corpus.write(rows=rows, extra_sources=extra)
        out = Path(self.tmp.name) / "out"
        out.mkdir()
        code, _, err = quiet_main(["--results", str(root), "--out-dir", str(out),
                                   "--boot", "5"])
        self.assertEqual(code, 2)
        self.assertIn("FAIL CLOSED", err)
        if pattern:
            self.assertRegex(err, pattern)
        self.assertEqual(list(out.iterdir()), [])

    def test_hash_mismatch(self):
        rows = [dict(r) for r in self.corpus.rows]
        rows[3]["transcript_hash"] = "0" * 16
        self.assert_fails_and_writes_nothing(rows, pattern="scored on a different text")

    def test_newest_copy_wins_and_old_hash_fails(self):
        old = [s for s in self.corpus.sessions if s["test_model"] == "m_high"][:1]
        new = json.loads(json.dumps(old))
        new[0]["dialogue"][2]["content"] = PROSE + " Changed."
        rows = [dict(r) for r in self.corpus.rows]           # hashed on the old text
        self.assert_fails_and_writes_nothing(
            rows, extra=[("craft_baseline_20260202_000000.json", new)],
            pattern="m_high::adv_seed_00: transcript hash")

    def test_newest_copy_wins_and_new_hash_passes(self):
        old = [s for s in self.corpus.sessions if s["test_model"] == "m_high"][:1]
        new = json.loads(json.dumps(old))
        new[0]["dialogue"][2]["content"] = PROSE + " Changed."
        rows = [dict(r) for r in self.corpus.rows]
        rows[0]["transcript_hash"] = transcript_hash(new[0])
        root = self.corpus.write(rows, [("craft_baseline_20260202_000000.json", new)])
        canon, copies, _ = O.load_corpus(root)
        self.assertEqual(canon["m_high::adv_seed_00"]["source"],
                         "craft_baseline_20260202_000000.json")
        self.assertEqual(copies["m_high::adv_seed_00"], 2)
        O.validate_judge_rows(rows, canon, copies)          # does not raise

    def test_unhashed_row_with_two_transcripts_on_disk(self):
        dup = [s for s in self.corpus.sessions if s["test_model"] == "m_mid"][:1]
        rows = [dict(r) for r in self.corpus.rows]
        for r in rows:
            if r["session_id"] == "m_mid::adv_seed_00":
                del r["transcript_hash"]
        self.assert_fails_and_writes_nothing(
            rows, extra=[("craft_baseline_20251201_000000.json", dup)],
            pattern="no hash and 2 transcripts")

    def test_unhashed_row_with_one_transcript_is_accepted(self):
        rows = [dict(r) for r in self.corpus.rows]
        del rows[0]["transcript_hash"]
        root = self.corpus.write(rows)
        canon, copies, _ = O.load_corpus(root)
        v = O.validate_judge_rows(rows, canon, copies)
        self.assertEqual(v["unhashed_single_transcript"], 1)

    def test_duplicate_row_unknown_session_and_second_judge(self):
        rows = [dict(r) for r in self.corpus.rows]
        self.assert_fails_and_writes_nothing(rows + [rows[0]], pattern="duplicate row")
        self.tearDown(); self.setUp()
        ghost = dict(rows[0], session_id="m_ghost::adv_seed_00", model="m_ghost")
        self.assert_fails_and_writes_nothing(rows + [ghost], pattern="no transcript on disk")
        self.tearDown(); self.setUp()
        other = [dict(r) for r in rows]
        other[5]["judge"] = "api-gemini"
        self.assert_fails_and_writes_nothing(other, pattern="expected 'subagent-sonnet-5'")

    def test_stale_defects_file(self):
        root = self.corpus.write()
        with open(root / "production_defects.json") as fh:
            d = json.load(fh)
        d["per_model"]["m_high"]["turns"] += 1
        write_json(d, root / "production_defects.json")
        with self.assertRaisesRegex(O.InputError, "production_defects.json"):
            O.build(root, boot=5)

    def test_defect_counts_must_match_the_recount(self):
        root = self.corpus.write()
        with open(root / "production_defects.json") as fh:
            d = json.load(fh)
        d["per_model"]["m_low"]["selfplay_turns"] = 3        # the text has none
        write_json(d, root / "production_defects.json")
        with self.assertRaisesRegex(O.InputError, "m_low: file vs corpus"):
            O.build(root, boot=5)

    def test_a_model_missing_from_the_defects_file_fails(self):
        root = self.corpus.write()
        with open(root / "production_defects.json") as fh:
            d = json.load(fh)
        del d["per_model"]["m_mid"]                          # 57 answered turns
        write_json(d, root / "production_defects.json")
        with self.assertRaisesRegex(O.InputError, "m_mid: 57 answered turns but not"):
            O.build(root, boot=5)

    def test_a_session_dimension_outside_1_to_5(self):
        rows = [dict(r) for r in self.corpus.rows]
        rows[4] = dict(rows[4], session_dimensions=dict(
            rows[4]["session_dimensions"], **{"S.3_narrative_momentum": 6.0}))
        self.assert_fails_and_writes_nothing(rows, pattern="S.3_narrative_momentum 6.0")


class BlankSessions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Corpus(Path(cls.tmp.name) / "results").write()
        cls.elo, cls.ov = O.build(cls.root, boot=40)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def row(self, m):
        return next(r for r in self.ov["rows"] if r["model"] == m)

    def test_blank_scene_is_kept_as_scored(self):
        m = next(x for x in self.elo["models"] if x["model"] == "m_blanky")
        scores = [3.8 if i % 2 == 0 else 4.0 for i in range(12)]
        scores[0] = 1.0
        self.assertAlmostEqual(m["mean"], round(sum(scores) / 12, 4), places=4)
        self.assertEqual(m["n_seeds"], 12)
        self.assertIn("m_blanky::adv_seed_00", self.elo["corpus"]["flagged_sessions_kept"])
        self.assertEqual(self.row("m_blanky")["judge_tier"]["tier"], "B")   # 3.67

    def test_blank_scene_is_flagged_not_counted_as_stub_turns(self):
        shown = self.row("m_blanky")["watch_out"]["shown"]
        self.assertEqual([w["key"] for w in shown], ["blank_scene"])
        self.assertEqual((shown[0]["count"], shown[0]["of"]), (1, 12))
        c = self.row("m_blanky")["watch_out"]["counts"]
        self.assertEqual(c["blank_scenes"], ["adv_seed_00"])
        self.assertEqual(c["empty_turns_outside_blank_scenes"], 0)

    def test_partial_scene_uses_the_13a_gate(self):
        shown = {w["key"]: w for w in self.row("m_mid")["watch_out"]["shown"]}
        self.assertEqual(shown["partial_scene"]["count"], 1)
        self.assertIn("2 of 5 replies", shown["partial_scene"]["text"])
        self.assertEqual(shown["stub_replies"]["count"], 3)       # 3 of 60 turns = 5%

    def test_drop_sensitivity_is_recorded(self):
        chk = self.ov["checks"]["blank_sessions_dropped"]
        self.assertEqual(chk["dropped_sessions"],
                         ["m_blanky::adv_seed_00", "m_mid::adv_seed_01"])
        moved = {c["model"]: (c["from_tier"], c["to_tier"]) for c in chk["tier_changes"]}
        self.assertEqual(moved, {"m_blanky": ("B", "A")})    # 3.67 -> about 3.9

    def test_judge_means_block(self):
        jm = self.ov["judge_means"]
        self.assertEqual(jm["dimensions"], list(O.DIMENSIONS))
        self.assertEqual(sorted(jm["models"]), sorted(Corpus.SCORES))
        elo = {x["model"]: x for x in self.elo["models"]}
        for m, e in jm["models"].items():
            with self.subTest(model=m):
                rows = [r for r in Corpus(Path("/nonexistent")).rows if r["model"] == m]
                self.assertEqual(e["n_sessions"], len(rows))
                self.assertEqual(e["n_seeds"], len(rows))
                for dim in O.DIMENSIONS[1:]:
                    plain = sum(r["session_dimensions"][dim] for r in rows) / len(rows)
                    self.assertAlmostEqual(e[dim + "_plain"], round(plain, 4), places=4)
                if m in elo:
                    self.assertEqual(e["overall"], elo[m]["mean"])
                    self.assertEqual(e["tier"], self.row(m)["judge_tier"]["tier"])
                    self.assertEqual(e["basis"], "seed_adjusted")
                    self.assertIsNone(e["note"])
        short = jm["models"]["m_short"]
        self.assertEqual((short["tier"], short["basis"], short["note"], short["n_seeds"]),
                         (None, "plain", "4 of 12 seeds", 4))
        self.assertAlmostEqual(short["overall"], 3.0, places=4)

    def test_a_model_the_defects_file_skips_is_counted_directly(self):
        r = next(x for x in self.ov["unranked"] if x["model"] == "m_short")
        self.assertEqual(r["judge_tier"], None)
        c = r["watch_out"]["counts"]
        self.assertEqual((c["answered_turns"], c["writes_your_character"]), (20, 1))
        self.assertIn("counted here", c["defects_source"])
        self.assertEqual([w["text"] for w in r["watch_out"]["shown"]],
                         ["writes your character: 1 of 20 replies"])
        self.assertIn("writes your character: 1 of 20 replies", O.render_markdown(self.ov))
        high = self.row("m_high")["watch_out"]["counts"]
        self.assertIn("production_defects.json", high["defects_source"])

    def test_the_edge_marker_is_in_the_json_only(self):
        self.assertTrue(all(isinstance(r["judge_tier"]["edge"], bool) for r in self.ov["rows"]))
        md = O.render_markdown(self.ov)
        self.assertNotIn("*", md)
        self.assertIn("Tiers (fixed): A 3.8 and above, B 3.2-3.8", md)
        b = self.ov["bands"]
        self.assertEqual(b["edge_marked"] + b["edge_clear"], len(self.ov["rows"]))

    def test_user_simulator_row_is_flagged(self):
        keys = [w["key"] for w in self.row("m_low")["watch_out"]["shown"]]
        self.assertIn("plays_itself", keys)

    def test_rows_are_by_tier_then_alphabetical_with_no_rank(self):
        order = [(r["judge_tier"]["tier"], r["model"]) for r in self.ov["rows"]]
        self.assertEqual(order, sorted(order))
        keys = set(keys_of(self.ov["rows"]))
        for banned in ("rank", "rank_lo", "rank_hi", "position", "elo", "mean", "score",
                       "overall") + O.DIMENSIONS:
            self.assertNotIn(banned, keys)

    def test_j_absent_reads_not_in_round_4(self):
        self.assertEqual(self.row("m_high")["J"]["display"], "not in round 4")


class Deterministic(unittest.TestCase):
    def test_same_inputs_same_bytes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Corpus(Path(t) / "results").write()
            outs = []
            for k in range(2):
                out = Path(t) / ("out%d" % k)
                out.mkdir()
                code, _, _ = quiet_main(["--results", str(root), "--out-dir", str(out),
                                         "--boot", "25", "--markdown", str(out / "t.md")])
                self.assertEqual(code, 0)
                outs.append([(out / n).read_bytes() for n in
                             (O.OUT_ELO, O.OUT_OVERVIEW, "t.md")])
            self.assertEqual(outs[0], outs[1])
            self.assertEqual(O.OUT_ELO, "round4_judge_elo.json")

    def test_adjusted_mean_is_the_plain_mean_for_complete_models(self):
        rng = np.random.default_rng(1)
        X = rng.uniform(1, 5, (12, 5))
        X[:4, 4] = np.nan                                       # one 8-seed model
        adj = O.seed_adjusted_means(X)
        np.testing.assert_allclose(adj[:4], X[:, :4].mean(0), atol=1e-10)
        self.assertTrue(np.isfinite(adj[4]))

    def test_bt_orders_and_anchors(self):
        X = np.array([[4.5, 4.0, 3.0], [4.4, 4.1, 3.2], [4.0, 4.2, 3.1], [4.6, 3.9, 3.3]])
        Ws, Ns = O.seed_mats(X)
        elo = O.bt_fit(Ws.sum(0), Ns.sum(0))
        self.assertAlmostEqual(elo.mean(), 1500.0, places=6)
        self.assertEqual(list(np.argsort(-elo)), [0, 1, 2])
        ties = O.seed_mats(np.array([[3.0, 3.0]]))[0]
        self.assertEqual(ties[0, 0, 1], 0.5)


class Columns(unittest.TestCase):
    def test_j_is_copied_and_printed_to_two_decimals(self):
        self.assertEqual(O.j_cell({"J": 0.427, "ranked": True, "quadrant": "X"})["display"],
                         "+0.43")
        u = O.j_cell({"J": 0.103, "ranked": False, "unranked_reason": "few"})
        self.assertEqual((u["display"], u["value"], u["unranked_reason"]),
                         ("+0.10 unranked", 0.103, "few"))
        self.assertEqual(O.j_cell(None)["display"], "not in round 4")

    def test_silent_refusal_reads_the_rung_counts(self):
        jrow = {"empty_rate_a": 0.413, "empty_rung_slope_a": 0.6, "usable_exchanges_a": 44}
        rungs = {1: [15, 1], 2: [15, 7], 3: [15, 7], 4: [15, 6], 5: [15, 10]}
        self.assertEqual(O.rung_problems("m", jrow, rungs), [])
        sr = O.silent_refusal(jrow, rungs)
        self.assertEqual((sr["count"], sr["of"]), (31, 75))
        self.assertEqual(sr["text"], "silent on explicit asks: 31 of 75 Track A replies "
                                     "empty, 1 of 15 at the mildest rung and 10 of 15 at "
                                     "the most explicit")
        self.assertNotIn("points", sr["text"])
        self.assertIsNone(O.silent_refusal(dict(jrow, empty_rung_slope_a=0.1), rungs))
        with self.assertRaises(O.InputError):
            O.silent_refusal(jrow, None)          # flagged, and no recount: refuse
        self.assertTrue(O.rung_problems("m", dict(jrow, empty_rate_a=0.5), rungs))
        self.assertTrue(O.rung_problems("m", dict(jrow, empty_rung_slope_a=0.7), rungs))

    def test_cross_judge_hook_adds_a_column_without_reshaping(self):
        with tempfile.TemporaryDirectory() as t:
            corpus = Corpus(Path(t) / "results")
            root = corpus.write()
            cross = Path(t) / "second.jsonl"
            with open(cross, "w") as fh:
                for r in corpus.rows:
                    shift = 0.6 if r["model"] == "m_mid" else 0.0
                    fh.write(json.dumps({"session_id": r["session_id"],
                                         "overall": r["overall"] - 0.8 + shift,
                                         "transcript_hash": r["transcript_hash"]}) + "\n")
            _, base = O.build(root, boot=5)
            _, ov = O.build(root, boot=5, cross=[("second", str(cross))])
            self.assertEqual(set(base), set(ov))
            self.assertEqual(ov["cross_judges"]["second"]["flagged"], ["m_mid"])
            row = next(r for r in ov["rows"] if r["model"] == "m_mid")
            self.assertTrue(row["cross_judges"]["second"]["flag"])
            self.assertIn("Second judge (second)", O.render_markdown(ov))


def r4_session(model, seed, track, labels, error=False):
    s = {"seed_id": seed, "test_model": model, "track": track,
         "rung_labels": [{"rung": r, "label": lab} for r, lab in labels]}
    if error:
        s["error"] = "timeout"
    return s


class SilentRefusalRecount(unittest.TestCase):
    """The rung counts come from the round 4 runs, with the willingness
    analyzer's dedupe, and must reproduce the published rate and slope."""

    LABELS = [(1, "engaged"), (2, "engaged"), (3, "EMPTY_REPLY"), (4, "engaged"),
              (5, "EMPTY_REPLY")]

    def write(self, root, rate, slope):
        old = [r4_session("m_low", "r4_a_intimacy_%02d" % i, "A", self.LABELS)
               for i in range(3)]
        # an older copy of seed 00 with a different verdict: superseded
        old[0] = r4_session("m_low", "r4_a_intimacy_00", "A", [(r, "EMPTY_REPLY")
                                                               for r in range(1, 6)])
        new = [r4_session("m_low", "r4_a_intimacy_00", "A", self.LABELS),
               r4_session("m_low", "r4_a_intimacy_09", "A", self.LABELS, error=True),
               r4_session("m_low", "r4_b_hard_01", "B-hard", [(1, "EMPTY_REPLY")] * 3)]
        write_json({"sessions": old}, root / "r4_full_20260101_000000.json")
        write_json({"sessions": new}, root / "r4_full_20260202_000000.json")
        write_json({"leaderboard": [
            {"model": "m_low", "J": 0.1, "ranked": True, "quadrant": "X",
             "empty_rate_a": rate, "empty_rung_slope_a": slope,
             "usable_exchanges_a": 9}]}, root / "round4_willingness_leaderboard.json")

    def test_counts_reach_the_watch_out_column(self):
        with tempfile.TemporaryDirectory() as t:
            root = Corpus(Path(t) / "results").write()
            self.write(root, 0.4, 1.0)                  # 6 of 15; 0 of 3, 3 of 3
            _, ov = O.build(root, boot=5)
            row = next(r for r in ov["rows"] if r["model"] == "m_low")
            sr = next(w for w in row["watch_out"]["shown"] if w["key"] == "silent_refusal")
            self.assertEqual(sr["text"], "silent on explicit asks: 6 of 15 Track A replies "
                                         "empty, 0 of 3 at the mildest rung and 3 of 3 at "
                                         "the most explicit")
            self.assertIn("r4_full_20260202_000000.json", ov["inputs"])

    def test_a_recount_that_disagrees_with_the_j_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root = Corpus(Path(t) / "results").write()
            self.write(root, 0.6, 1.0)
            with self.assertRaisesRegex(O.InputError, "rung recount"):
                O.build(root, boot=5)


class ClaudeTilt(unittest.TestCase):
    def test_a_model_drawn_twice_weighs_like_its_sessions_duplicated(self):
        rng = np.random.default_rng(3)
        S = rng.uniform(2, 5, 9)
        x = S - rng.uniform(0, 1, 9)
        claude = np.array([1, 1, 0, 0, 0, 1, 0, 0, 0], bool)
        w = np.array([2, 2, 0, 1, 1, 1, 3, 3, 1], float)
        got = O._tilts(S, x, claude, w[None, :])
        rep = np.repeat(np.arange(9), w.astype(int))
        want = O._tilts(S[rep], x[rep], claude[rep], np.ones((1, len(rep))))
        np.testing.assert_allclose([v[0] for v in got], [v[0] for v in want], atol=1e-12)

    def test_the_point_estimate_is_claude_minus_non_claude(self):
        S = np.array([4.0, 4.2, 3.0, 3.5, 2.5, 3.8])
        x = np.array([3.5, 3.7, 3.0, 3.5, 2.5, 3.8])          # 0.5 lower on Claude only
        claude = np.array([True, True, False, False, False, False])
        vs_all, vs_non = (float(v[0]) for v in O._tilts(S, x, claude, np.ones((1, 6))))
        xz = (x - x.mean()) / x.std() * S.std() + S.mean()
        d = S - xz
        self.assertAlmostEqual(vs_non, d[claude].mean() - d[~claude].mean(), places=12)
        self.assertAlmostEqual(vs_all, d[claude].mean() - d.mean(), places=12)
        self.assertGreater(vs_non, vs_all)


if __name__ == "__main__":
    unittest.main()
