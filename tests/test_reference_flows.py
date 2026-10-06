"""Offline regressions only: no model calls, credentials, or third-party packages."""
import contextlib
import csv
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import scoring_pipeline as scoring
from source import api_client, multi_vendor_infer, probability_infer, probability_score


class ScoringTests(unittest.TestCase):
    def test_forbidden_pattern_direction(self):
        q = scoring.REGISTRY["C8"]
        self.assertEqual(scoring.judge_pattern("H200 与 B300 文字对比", q)[0], 2)
        self.assertEqual(scoring.judge_pattern("| H200 | B300 |", q)[0], 0)

    def test_forbidden_numeric_direction(self):
        q = scoring.Question("T", "G", "test", scoring.JudgeKind.NUMERIC,
                             nums=(scoring.NumericKey("value", 42),), forbidden=(r"\|",))
        self.assertEqual(scoring.judge_numeric("42", q)[0], 2)
        self.assertEqual(scoring.judge_numeric("|42|", q)[0], 0)

    def test_signed_and_compound_numbers(self):
        cases = {"-3000": [-3000], "−3000": [-3000], "0.6 千万": [6000000],
                 "600 万": [6000000], "¥6,000,000": [6000000],
                 "-0.6 千万": [-6000000], ".6千万": [6000000],
                 "H200 10kW B300 18kW": [10, 18], "1.2e3": [1200]}
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(scoring.extract_numbers(text), expected)

    def test_strict_json(self):
        q = scoring.REGISTRY["C7"]
        self.assertEqual(scoring.judge_json(q.answer_key, q)[0], 2)
        for answer in ("Explanation: " + q.answer_key, "```json\n" + q.answer_key + "\n```"):
            self.assertEqual(scoring.judge_json(answer, q)[0], 0)

    def test_empty_llm_answer(self):
        def forbidden_call(prompt):
            self.fail("Empty answer must not invoke a judge")
        self.assertEqual(scoring.judge_llm("", scoring.REGISTRY["C3"], forbidden_call)[0], 0)

    def test_invalid_judge_reply(self):
        with self.assertRaises(ValueError):
            scoring.judge_llm("answer", scoring.REGISTRY["C3"], lambda p: "invalid")

    def test_empty_input_never_becomes_demo(self):
        for samples in (None, []):
            with self.assertRaises(ValueError):
                scoring.main(samples)

    def test_unknown_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "未登记"):
            scoring.main([scoring.Sample("A", "UNKNOWN", 1, "answer")])

    def test_real_input_requires_real_judge(self):
        sample = scoring.Sample("A", "C3", 1, "answer")
        for callback in (None, scoring.stub_llm):
            with self.assertRaises(ValueError):
                scoring.main([sample], callback)

    def test_duplicate_sample(self):
        sample = scoring.Sample("A", "C8", 1, "H200 B300")
        with self.assertRaises(ValueError):
            scoring.main([sample, sample])

    def test_demo_is_explicit_and_missing_dimensions_are_na(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            scoring.main(demo=True)
        self.assertIn("DEMO", out.getvalue())
        self.assertIn("N/A", out.getvalue())
        self.assertNotIn("最大相对差异", out.getvalue())

    def test_missing_usage_does_not_become_zero_cost(self):
        result = scoring.aggregate([scoring.score_sample(
            scoring.Sample("A", "C8", 1, "H200 B300"), scoring.REGISTRY["C8"])])
        report = scoring.build_reports(result)["A"]
        self.assertIsNone(report.dimensions["token"])
        self.assertIsNone(report.total)

    def test_collector_matches_registry(self):
        self.assertEqual(multi_vendor_infer.QUESTIONS,
                         {qid: q.prompt for qid, q in scoring.REGISTRY.items()})


class ProbabilityTests(unittest.TestCase):
    def test_exact_match(self):
        self.assertEqual(probability_score.score_sample("  PARIS  ", ["paris"]), 1)
        self.assertEqual(probability_score.score_sample("ＰＡＲＩＳ", ["paris"]), 1)

    def test_substring_and_negation_do_not_match(self):
        for answer, gt in [("pineapple", "apple"), ("not Paris", "paris"),
                           ("The answer is not Paris.", "paris"), ("巴黎不是答案", "巴黎")]:
            self.assertEqual(probability_score.score_sample(answer, [gt]), 0)

    def test_missing_gt_is_rejected(self):
        for gt in ([], [""], [" "], None, "paris"):
            with self.assertRaises(ValueError):
                probability_score.score_sample("Paris", gt)

    def test_wilson_boundaries(self):
        self.assertEqual(probability_score.calc_95_ci(10, 10), (72.25, 100))
        self.assertEqual(probability_score.calc_95_ci(0, 10), (0, 27.75))
        self.assertEqual(probability_score.calc_95_ci(5, 10), (23.66, 76.34))
        self.assertEqual(probability_score.calc_95_ci(0, 0), (None, None))
        with self.assertRaises(ValueError):
            probability_score.calc_95_ci(11, 10)

    def evaluate(self, records):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "input.json"
            source.write_text(json.dumps(records), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                result = probability_score.do_eval(source, folder / "new/eval.csv", folder / "new/bad.csv")
            with (folder / "new/bad.csv").open(encoding="utf-8-sig") as handle:
                bad = list(csv.DictReader(handle))
            return result, bad

    def record(self, **kwargs):
        return dict({"prompt_id": 1, "prompt": "Capital?", "label": "knowledge",
                     "full_output": "Paris", "gt_whitelist": ["paris"]}, **kwargs)

    def test_all_correct_writes_empty_bad_case_header(self):
        result, bad = self.evaluate([self.record()])
        self.assertEqual(result["Acc_baseline_pct"], 100)
        self.assertEqual(bad, [])

    def test_empty_data_has_no_fabricated_accuracy(self):
        result, bad = self.evaluate([])
        self.assertIsNone(result["Acc_baseline_pct"])
        self.assertIsNone(result["ci_95_low"])
        self.assertEqual(bad, [])

    def test_failed_request_not_in_accuracy_denominator(self):
        failed = self.record(status="error")
        result, bad = self.evaluate([failed])
        self.assertEqual(result["failed_requests"], 1)
        self.assertEqual(result["N_knowledge"], 0)
        self.assertEqual(len(bad), 1)

    def test_logic_only_requires_review(self):
        record = self.record()
        record.update(label="logic_fiction", gt_whitelist=[], full_output="I don't know")
        result, bad = self.evaluate([record])
        self.assertIsNone(result["Acc_baseline_pct"])
        self.assertEqual(result["logic_fiction_reject"], 1)
        self.assertEqual(len(bad), 1)


class ClientTests(unittest.TestCase):
    def response(self, **choice_fields):
        choice = {"message": {"content": "Paris"}, "finish_reason": "stop"}
        choice.update(choice_fields)
        return {"choices": [choice]}

    def client(self):
        return api_client.ChatClient("https://example.invalid/v1/chat/completions", "test-placeholder", "test-model")

    def test_unconfigured_client_does_not_call_network(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(api_client, "urlopen") as request:
            with self.assertRaises(ValueError):
                api_client.ChatClient.from_env()
            request.assert_not_called()

    def test_missing_usage_and_token_stay_unknown(self):
        with patch.object(api_client, "urlopen", return_value=io.BytesIO(json.dumps(self.response()).encode())) as call:
            result = self.client().complete("test")
        self.assertIsNone(result["total_tokens"])
        self.assertIsNone(result["first_token"])
        self.assertEqual(call.call_args.kwargs["timeout"], 60)

    def test_actual_first_token(self):
        data = self.response(logprobs={"content": [{"token": "Par"}]})
        with patch.object(api_client, "urlopen", return_value=io.BytesIO(json.dumps(data).encode())):
            self.assertEqual(self.client().complete("test", logprobs=True)["first_token"], "Par")

    def test_truncated_empty_and_malformed_responses(self):
        for data in (self.response(finish_reason="length"), self.response(message={"content": ""}), {}):
            with patch.object(api_client, "urlopen", return_value=io.BytesIO(json.dumps(data).encode())):
                with self.assertRaises(RuntimeError):
                    self.client().complete("test")

    def test_http_error_hides_body(self):
        error = HTTPError("https://example.invalid", 401, "private-detail", {}, None)
        with patch.object(api_client, "urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "^API HTTP error 401$"):
                self.client().complete("test")


class IntegrationTests(unittest.TestCase):
    class FakeClient:
        def complete(self, prompt, **kwargs):
            return {"content": "Paris", "first_token": None, "total_tokens": None,
                    "usage": {}, "latency_ms": 1}

    def test_collection_loads_all_registered_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = multi_vendor_infer.run_benchmark(Path(directory) / "new/samples.jsonl",
                                                           rounds=1, client=self.FakeClient())
            samples = scoring.load_samples(destination)
            self.assertEqual({s.qid for s in samples}, set(scoring.REGISTRY))
            self.assertEqual(len(samples), 11)

    def test_failed_collection_is_preserved_and_rejected(self):
        class FailedClient:
            def complete(self, prompt):
                raise RuntimeError("private details")
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "samples.jsonl"
            with self.assertRaises(RuntimeError):
                multi_vendor_infer.run_benchmark(destination, rounds=1, client=FailedClient())
            self.assertEqual(len(destination.read_text().splitlines()), 11)
            self.assertNotIn("private details", destination.read_text())
            with self.assertRaises(ValueError):
                scoring.load_samples(destination)

    def test_probability_inference_and_scoring(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            labels, gt = folder / "labels.json", folder / "gt.json"
            labels.write_text(json.dumps({"1": {"prompt": "Capital?", "label": "knowledge"}}))
            gt.write_text(json.dumps({"1": ["paris"]}))
            records = probability_infer.run_all_infer(labels, gt, folder / "new/raw.json", self.FakeClient())
            self.assertEqual(records[0]["full_output"], "Paris")
            self.assertIsNone(records[0]["first_token"])
            with contextlib.redirect_stdout(io.StringIO()):
                result = probability_score.do_eval(folder / "new/raw.json", folder / "score.csv", folder / "bad.csv")
            self.assertEqual(result["Acc_baseline_pct"], 100)

    def test_inference_validates_all_gt_before_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            labels, gt = folder / "labels.json", folder / "gt.json"
            labels.write_text(json.dumps({"1": {"prompt": "Capital?", "label": "knowledge"}}))
            gt.write_text("{}")
            client = self.FakeClient()
            with patch.object(client, "complete") as call:
                with self.assertRaises(ValueError):
                    probability_infer.run_all_infer(labels, gt, folder / "out.json", client)
                call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
