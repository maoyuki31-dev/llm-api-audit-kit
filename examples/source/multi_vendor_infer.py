"""Collect the exact registered scoring prompts; no API calls on import."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scoring_pipeline import REGISTRY
from source.api_client import ChatClient

QUESTIONS = {qid: question.prompt for qid, question in REGISTRY.items()}


def run_benchmark(output_file="output/collected_answers.jsonl", vendor_name="provider-A",
                  rounds=3, client=None):
    if rounds < 1:
        raise ValueError("rounds must be positive")
    client = client or ChatClient.from_env()
    destination = Path(output_file)
    destination.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    with destination.open("w", encoding="utf-8") as handle:
        for qid, prompt in QUESTIONS.items():
            for round_idx in range(1, rounds + 1):
                record = {"vendor": vendor_name, "qid": qid, "round_idx": round_idx,
                          "answer": "", "tokens": None, "latency_ms": 0}
                try:
                    response = client.complete(prompt)
                    record.update(answer=response["content"], tokens=response["total_tokens"],
                                  latency_ms=response["latency_ms"])
                except Exception as exc:
                    record.update(status="error", error=type(exc).__name__)
                    failures += 1
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
    if failures:
        raise RuntimeError(f"{failures} requests failed; inspect {destination} before scoring")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/collected_answers.jsonl")
    parser.add_argument("--vendor", default="provider-A")
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    run_benchmark(args.output, args.vendor, args.rounds)
