"""Conservative whole-answer scoring with Wilson intervals (standard library only)."""
import argparse
import csv
import json
import math
from pathlib import Path
import unicodedata


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def score_sample(model_output, gt_list):
    """Exact normalized answer only; explanations/nonmatches need human review."""
    if not isinstance(model_output, str):
        raise ValueError("model_output must be text")
    if not isinstance(gt_list, list) or not gt_list or any(
            not isinstance(gt, str) or not normalize(gt) for gt in gt_list):
        raise ValueError("A nonempty, reviewed GT whitelist is required")
    return int(normalize(model_output) in {normalize(gt) for gt in gt_list})


def calc_95_ci(success, total):
    """Wilson score interval for independent Bernoulli trials; percentages."""
    if type(success) is not int or type(total) is not int or not 0 <= success <= total:
        raise ValueError("Require integers with 0 <= success <= total")
    if total == 0:
        return (None, None)
    z = 1.959963984540054
    p = success / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return (round(max(0, center - margin) * 100, 2),
            round(min(1, center + margin) * 100, 2))


def validate_record(record):
    if not isinstance(record, dict) or not {"prompt_id", "prompt", "label", "full_output"} <= record.keys():
        raise ValueError("Record missing required fields")
    if not isinstance(record["prompt"], str) or not record["prompt"].strip():
        raise ValueError("Prompt must be nonempty text")
    if not isinstance(record["full_output"], str):
        raise ValueError("full_output must be text")
    if record["label"] not in {"knowledge", "logic_fiction"}:
        raise ValueError("Label must be knowledge or logic_fiction")
    if record.get("status", "ok") not in {"ok", "error"}:
        raise ValueError("Unsupported request status")
    if record["label"] == "knowledge":
        score_sample("", record.get("gt_whitelist"))


def write_csv(path, rows, fields):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def do_eval(infer_result_path, out_csv, bad_case_csv):
    records = json.loads(Path(infer_result_path).read_text(encoding="utf-8-sig"))
    if not isinstance(records, list):
        raise ValueError("Input must be a list of inference records")
    for record in records:
        validate_record(record)
    rows, bad_rows = [], []
    knowledge_total = knowledge_correct = fiction_total = refusal = failures = 0
    for rec in records:
        score, reason = None, ""
        if rec.get("status", "ok") == "error":
            failures += 1
            reason = "request_failed_not_scored"
        elif rec["label"] == "knowledge":
            knowledge_total += 1
            score = score_sample(rec["full_output"], rec["gt_whitelist"])
            knowledge_correct += score
            reason = "exact_match" if score else "no_exact_match_review_required"
        else:
            fiction_total += 1
            refusal += int(any(word in rec["full_output"].casefold()
                               for word in ("i don't know", "sorry", "cannot answer")))
            reason = "logic_fiction_requires_manual_review"
        row = {key: rec[key] for key in ("prompt_id", "prompt", "label", "full_output")}
        row.update(score=score, reason=reason)
        rows.append(row)
        if score != 1:
            bad_rows.append(dict(row, gt=json.dumps(rec.get("gt_whitelist", []), ensure_ascii=False)))
    fields = ["prompt_id", "prompt", "label", "score", "full_output", "reason"]
    write_csv(out_csv, rows, fields)
    write_csv(bad_case_csv, bad_rows, fields + ["gt"])
    low, high = calc_95_ci(knowledge_correct, knowledge_total)
    metrics = {"total_all": len(records), "failed_requests": failures,
               "N_knowledge": knowledge_total, "Correct_knowledge": knowledge_correct,
               "Acc_baseline_pct": round(knowledge_correct / knowledge_total * 100, 2) if knowledge_total else None,
               "ci_95_low": low, "ci_95_high": high, "ci_method": "wilson",
               "scoring_method": "normalized_whole_answer_exact_match",
               "logic_fiction_total": fiction_total, "logic_fiction_reject": refusal}
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()
    folder = Path(args.output_dir)
    do_eval(args.input, folder / "eval_result.csv", folder / "bad_case.csv")
