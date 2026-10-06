"""Run a reviewed label/GT set against an explicitly configured endpoint."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source.api_client import ChatClient
from source.probability_score import validate_record


def infer_one(prompt, client=None, *, logprobs=False):
    response = (client or ChatClient.from_env()).complete(prompt, logprobs=logprobs)
    # Missing token data is None, never a guessed word or character.
    return response["content"], response["first_token"]


def run_all_infer(label_json_path, gt_json_path, out_infer_json, client=None, *, logprobs=False):
    label_map = json.loads(Path(label_json_path).read_text(encoding="utf-8-sig"))
    gt_whitelist = json.loads(Path(gt_json_path).read_text(encoding="utf-8-sig"))
    if not isinstance(label_map, dict) or not label_map:
        raise ValueError("Label map must be a nonempty object")
    if not isinstance(gt_whitelist, dict):
        raise ValueError("GT whitelist must be an object")
    records = []
    for pid, item in label_map.items():
        record = {"prompt_id": int(pid), "prompt": item["prompt"], "label": item["label"],
                  "gt_whitelist": gt_whitelist.get(pid, []), "full_output": ""}
        validate_record(record)  # Validate the entire set before any paid requests.
        records.append(record)
    client = client or ChatClient.from_env()
    destination = Path(out_infer_json)
    destination.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    for record in records:
        try:
            response = client.complete(record["prompt"], logprobs=logprobs)
            record.update(full_output=response["content"], first_token=response["first_token"],
                          usage=response["usage"], latency_ms=response["latency_ms"], status="ok")
        except Exception as exc:
            record.update(status="error", error=type(exc).__name__, first_token=None)
            failures += 1
    destination.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        raise RuntimeError(f"{failures} requests failed; partial results saved to {destination}")
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--gt", required=True)
    parser.add_argument("--output", default="output/raw_infer_result.json")
    parser.add_argument("--logprobs", action="store_true",
                        help="Request actual token data if supported by the endpoint")
    args = parser.parse_args()
    run_all_infer(args.labels, args.gt, args.output, logprobs=args.logprobs)
