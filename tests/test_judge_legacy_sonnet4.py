"""Offline tests for rounds/r4/judge_legacy_sonnet4.py: parsing, provenance, resume, cap.

No network: the OpenRouter call and the credits check are stubbed. Run by path
from the repo root:
    python -m unittest tests/test_judge_legacy_sonnet4.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rounds.r4 import judge_legacy_sonnet4 as J  # noqa: E402
from harness import multiturn      # noqa: E402

GOOD = {
    "session_dimensions": {
        "S.1_consistency_over_time": {"score": 4.0, "rationale": "steady"},
        "S.2_degradation_resistance": {"score": 3.5, "rationale": "a dip"},
        "S.3_narrative_momentum": {"score": 4, "rationale": "moves"},
        "S.4_adaptive_responsiveness": {"score": 4.5, "rationale": "follows"},
        "S.5_agency_respect_session": {"score": 5.0, "rationale": "clean",
                                       "violation_count": 0},
        "S.6_temporal_reasoning": {"score": 3.0, "rationale": "clock slips",
                                   "contradictions": ["noon at dusk"]},
    },
    "standard_dimensions": {
        "2.1_anti_purple_prose": {"score": 4.0, "rationale": ""},
        "2.2_anti_repetition": {"score": 3.0, "rationale": "loops"},
        "2.5_show_dont_tell": {"score": 4.0, "rationale": ""},
        "2.6_subtext": {"score": 3.5, "rationale": ""},
        "2.7_pacing": {"score": 4.0, "rationale": ""},
    },
    "quality_trajectory": {"early_quality": 4.2, "mid_quality": 4.0,
                           "late_quality": 3.8, "degradation_detected": False},
    "overall": 4.1,
    "overall_notes": "solid",
}


def session(model="m_a", seed="adv_x_01", char_text="Hello there.", v1=None,
            v1_model="anthropic/claude-sonnet-4", user_text="Hi."):
    s = {
        "seed_id": seed, "test_model": model, "test_model_id": "x/" + model,
        "character_name": "Ren", "user_name": "Alex", "num_turns": 4,
        "dialogue": [
            {"turn": 0, "role": "character", "name": "Ren", "content": "Opening."},
            {"turn": 1, "role": "user", "name": "Alex", "content": user_text},
            {"turn": 2, "role": "character", "name": "Ren", "content": char_text},
            {"turn": 3, "role": "user", "name": "Alex", "content": "Bye."},
            {"turn": 4, "role": "character", "name": "Ren", "content": "Later."},
        ],
    }
    if v1 is not None:
        s["judges"] = {"claude_sonnet": {"scores": {"overall": v1},
                                         "usage": {}, "model": v1_model}}
    return s


def fake_response(content, cost=0.03, model="anthropic/claude-4-sonnet-20250522",
                  provider="Amazon Bedrock"):
    return {"content": content, "model": model,
            "usage": {"prompt_tokens": 1000, "completion_tokens": 900, "cost": cost},
            "raw": {"provider": provider}}


class StubAPI:
    """Stands in for harness.api.chat_completion; records every request."""

    def __init__(self, contents):
        self.contents = list(contents)
        self.calls = []

    def __call__(self, model, system_prompt, user_content, config=None):
        self.calls.append(dict(model=model, system=system_prompt,
                               user=user_content, config=config))
        c = self.contents.pop(0) if len(self.contents) > 1 else self.contents[0]
        return fake_response(c)


def dump(obj, path):
    with open(path, "w") as fh:
        json.dump(obj, fh)


def entry_for(s):
    return dict(session=s, src="craft_baseline_x.json",
                transcript_hash=J.transcript_hash(s),
                view_hash=J.judge_view_hash(s), v1=None)


class Provenance(unittest.TestCase):
    def test_prompt_hash_is_the_round_2_3_template(self):
        self.assertEqual(J.prompt_hash(), "1ff004ccf5aa")
        J.check_config()      # raises SystemExit on drift

    def test_config_drift_is_refused(self):
        with mock.patch.dict(J.JUDGE_CONFIG, {"temperature": 0.0}):
            with self.assertRaises(SystemExit):
                J.check_config()
        with mock.patch.object(multiturn, "SESSION_JUDGE_SYSTEM",
                               multiturn.SESSION_JUDGE_SYSTEM + " "):
            with self.assertRaises(SystemExit):
                J.check_config()

    def test_view_hash_sees_user_turns_but_transcript_hash_does_not(self):
        a, b = session(user_text="Hi."), session(user_text="Hey.")
        self.assertEqual(J.transcript_hash(a), J.transcript_hash(b))
        self.assertNotEqual(J.judge_view_hash(a), J.judge_view_hash(b))


class Parsing(unittest.TestCase):
    """Goes through the real harness.multiturn.judge_session; only the HTTP
    call underneath it is stubbed."""

    def judge(self, contents, retries=1):
        stub = StubAPI(contents)
        s = session()
        with mock.patch.object(J.api, "chat_completion", stub), \
                mock.patch.object(multiturn, "chat_completion",
                                  multiturn.chat_completion):
            judged, attempts = J.judge_with_retries(entry_for(s), J.call_judge, retries)
        return J.build_row("m_a::adv_x_01", entry_for(s), judged, "test", attempts), stub

    def test_clean_json(self):
        row, stub = self.judge([json.dumps(GOOD)])
        self.assertTrue(row["raw_parse_ok"])
        self.assertEqual(row["overall"], 4.1)
        self.assertEqual(row["session_dimensions"]["S.3_narrative_momentum"], 4.0)
        self.assertEqual(row["standard_dimensions"]["2.2_anti_repetition"], 3.0)
        self.assertEqual(row["rationales"]["S.6_temporal_reasoning"], "clock slips")
        self.assertEqual(row["extras"]["S.6_temporal_reasoning.contradictions"],
                         ["noon at dusk"])
        self.assertEqual(row["extras"]["S.5_agency_respect_session.violation_count"], 0)
        self.assertEqual(row["quality_trajectory"]["late_quality"], 3.8)
        self.assertEqual(row["attempts"], 1)
        self.assertEqual(row["judge_model_id"], "anthropic/claude-4-sonnet-20250522")
        self.assertEqual(row["provider"], "Amazon Bedrock")
        self.assertEqual(row["prompt_hash"], "1ff004ccf5aa")
        self.assertEqual((row["temperature"], row["max_tokens"]), (0.1, 4096))
        self.assertNotIn("raw_content", row)

    def test_request_is_the_harness_request(self):
        _, stub = self.judge([json.dumps(GOOD)])
        call = stub.calls[0]
        self.assertEqual(call["model"], "anthropic/claude-sonnet-4")
        self.assertEqual(call["config"], {"temperature": 0.1, "max_tokens": 4096})
        self.assertEqual(call["system"], multiturn.SESSION_JUDGE_SYSTEM % {
            "character_name": "Ren", "user_name": "Alex", "num_turns": 4})
        self.assertTrue(call["user"].startswith("<session>\n\n**Ren** (turn 0):\nOpening.\n"))
        self.assertTrue(call["user"].endswith(
            "Score the AI CHARACTER's (Ren) performance across this full 4-turn session."))
        self.assertIn("**Alex** (turn 1):\nHi.\n", call["user"])

    def test_fenced_json(self):
        row, _ = self.judge(["```json\n%s\n```" % json.dumps(GOOD, indent=2)])
        self.assertTrue(row["raw_parse_ok"])
        self.assertEqual(row["overall"], 4.1)

    def test_json_inside_prose(self):
        row, _ = self.judge(["Here is my evaluation:\n%s\nThanks." % json.dumps(GOOD)])
        self.assertTrue(row["raw_parse_ok"])

    def test_string_overall_is_coerced(self):
        g = dict(GOOD, overall="3.9")
        row, _ = self.judge([json.dumps(g)])
        self.assertEqual(row["overall"], 3.9)

    def test_garbage_is_retried_then_recorded_as_a_failure(self):
        row, stub = self.judge(["I cannot score this."], retries=1)
        self.assertEqual(len(stub.calls), 2)
        self.assertFalse(row["raw_parse_ok"])
        self.assertIsNone(row["overall"])
        self.assertEqual(row["attempts"], 2)
        self.assertEqual(row["raw_content"], "I cannot score this.")
        self.assertAlmostEqual(row["usage"]["cost"], 0.06)

    def test_missing_overall_is_a_failure(self):
        g = {k: v for k, v in GOOD.items() if k != "overall"}
        row, _ = self.judge([json.dumps(g)], retries=0)
        self.assertFalse(row["raw_parse_ok"])

    def test_retry_that_succeeds(self):
        row, stub = self.judge(["{truncated", json.dumps(GOOD)], retries=2)
        self.assertEqual(len(stub.calls), 2)
        self.assertTrue(row["raw_parse_ok"])
        self.assertEqual(row["attempts"], 2)


class CorpusAndResume(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        # a: stored v1 on the current transcript  -> not a target
        # b: stored v1 only on an older copy whose text differs -> target
        # c: never judged by v1 -> target
        old = {"sessions": [session("a", v1=4.4), session("b", v1=4.0, char_text="old")]}
        new = {"sessions": [session("b", char_text="new"), session("c"),
                            {"seed_id": "adv_x_01", "test_model": "z", "error": "boom"}]}
        dump(old, self.d / "multiturn_merged_all_v2.json")
        dump(new, self.d / "craft_baseline_20260924_000000.json")
        with open(self.d / "session_judge_v2.jsonl", "w") as fh:
            for m in ("a", "b", "c"):
                fh.write(json.dumps({"session_id": "%s::adv_x_01" % m}) + "\n")
        self.out = self.d / "out.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def corpus(self):
        return J.load_corpus(self.d, self.d / "session_judge_v2.jsonl")

    def fake_judge(self, s):
        return {"scores": dict(GOOD), "usage": {"cost": 0.04},
                "model": "anthropic/claude-4-sonnet-20250522", "provider": "P"}

    def run_all(self, corpus, work, cap=30.0, credits=(100.0, 50.0)):
        return J.run(corpus, work, self.out, "backfill", 2, cap, None, 100, 1,
                     judge_fn=self.fake_judge, credits_fn=lambda: credits)

    def test_targets_are_sessions_without_v1_on_their_current_text(self):
        c = self.corpus()
        self.assertEqual(c["a::adv_x_01"]["v1"], 4.4)
        self.assertIsNone(c["b::adv_x_01"]["v1"])
        self.assertEqual(c["b::adv_x_01"]["src"], "craft_baseline_20260924_000000.json")
        work, _, skipped_v1 = J.select_work(c, self.out)
        self.assertEqual(work, ["b::adv_x_01", "c::adv_x_01"])
        self.assertEqual(skipped_v1, 1)
        work, _, _ = J.select_work(c, self.out, include_judged=True)
        self.assertEqual(len(work), 3)

    def test_resume_skips_done_and_rejudges_a_changed_transcript(self):
        c = self.corpus()
        work, _, _ = J.select_work(c, self.out)
        summary = self.run_all(c, work)
        self.assertEqual(summary["written"], 2)
        self.assertTrue(J.verify(c, self.out)["ok"])
        work, done, _ = J.select_work(c, self.out)
        self.assertEqual((work, done), ([], 2))
        # c is regenerated: a newer source with different character text
        dump({"sessions": [session("c", char_text="regenerated")]}, self.d / "craft_baseline_20260926_000000.json")
        c2 = self.corpus()
        v = J.verify(c2, self.out)
        self.assertEqual(v["stale"], ["c::adv_x_01"])
        self.assertFalse(v["ok"])
        work, _, _ = J.select_work(c2, self.out)
        self.assertEqual(work, ["c::adv_x_01"])
        self.run_all(c2, work)
        self.assertTrue(J.verify(c2, self.out)["ok"])

    def test_rows_carry_the_v2_transcript_hash(self):
        c = self.corpus()
        self.run_all(c, ["c::adv_x_01"])
        row = J.read_rows(self.out)[0]
        self.assertEqual(row["transcript_hash"], J.transcript_hash(session("c")))
        self.assertEqual(row["judge_view_hash"], J.judge_view_hash(session("c")))

    def test_errors_write_no_row_and_are_retried_next_time(self):
        c = self.corpus()
        calls = []

        def flaky(s):
            calls.append(s["test_model"])
            if s["test_model"] == "b":
                raise RuntimeError("upstream exploded")
            return self.fake_judge(s)
        summary = J.run(c, ["b::adv_x_01", "c::adv_x_01"], self.out, "backfill",
                        1, 30.0, None, 100, 1, judge_fn=flaky,
                        credits_fn=lambda: (None, None))
        self.assertEqual(summary["written"], 1)
        self.assertEqual([f[0] for f in summary["failures"]], ["b::adv_x_01"])
        self.assertEqual(J.select_work(c, self.out)[0], ["b::adv_x_01"])

    def test_cap_stops_before_overspending(self):
        c = self.corpus()
        # baseline 50, account already at 79.97: $0.03 left, below one session
        summary = J.run(c, ["b::adv_x_01", "c::adv_x_01"], self.out, "backfill",
                        1, 30.0, 50.0, 100, 1, judge_fn=self.fake_judge,
                        credits_fn=lambda: (200.0, 79.97))
        self.assertEqual(summary["written"], 0)
        self.assertTrue(summary["stop_reason"].startswith("cap"))
        self.assertFalse(self.out.exists() and J.read_rows(self.out))

    def test_plan_chunk_uses_measured_cost(self):
        sp = J.Spend(baseline=0.0, start_usage=0.0)
        self.assertEqual(J.plan_chunk(sp, 30.0, 100), 100)
        for _ in range(10):
            sp.add(0.5)               # $5 spent at $0.50 a session
        # $25 left / (0.5 * 1.25) = 40
        self.assertEqual(J.plan_chunk(sp, 30.0, 100), 40)
        # the account counter can be ahead of the local sum
        self.assertEqual(J.plan_chunk(sp, 30.0, 100, account_usage=29.0), 1)


if __name__ == "__main__":
    unittest.main()
