import csv
import json
from scipy.stats import binom

def normalize(s: str) -> str:
    return s.lower().strip()

def score_sample(model_output: str, gt_list: list[str]) -> int:
    out_norm = normalize(model_output)
    for gt in gt_list:
        gt_norm = normalize(gt)
        if gt_norm in out_norm:
            return 1
    return 0


def calc_95_ci(success: int, total: int):
    """二项分布95%置信区间"""
    if total <= 0:
        return (0.0, 0.0)
    alpha = 0.05
    lower = binom.ppf(alpha/2, n=total, p=success/total) / total
    upper = binom.ppf(1-alpha/2, n=total, p=success/total) / total
    return (round(lower*100,2), round(upper*100,2))


def do_eval(infer_result_path: str, out_csv: str, bad_case_csv: str):
    with open(infer_result_path, "r", encoding="utf-8") as f:
        infer_data = json.load(f)

    knowledge_total = 0
    knowledge_correct = 0
    logic_fiction_total = 0
    logic_fiction_reject = 0
    csv_rows = []
    bad_case_rows = []

    for rec in infer_data:
        pid = rec["prompt_id"]
        prompt = rec["prompt"]
        label = rec["label"]
        full_out = rec["full_output"]
        gt = rec["gt_whitelist"]

        score = None
        if label == "knowledge":
            knowledge_total +=1
            score = score_sample(full_out, gt)
            if score == 1:
                knowledge_correct +=1
            else:
                bad_case_rows.append({"prompt_id":pid,"prompt":prompt,"output":full_out,"gt":gt})
        elif label == "logic_fiction":
            logic_fiction_total +=1
            # 简单统计拒绝
            rej_words = ["i don't know","sorry","cannot answer"]
            if any(r in full_out.lower() for r in rej_words):
                logic_fiction_reject +=1

        csv_rows.append({
            "prompt_id":pid,
            "prompt":prompt,
            "label":label,
            "score":score,
            "full_output":full_out
        })

    # 输出打分csv
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as fw:
        writer = csv.DictWriter(fw, fieldnames=csv_rows[0].keys())
        writer.writeheader()
        writer.writerows(csv_rows)
    # 输出bad case
    with open(bad_case_csv, "w", newline="", encoding="utf-8-sig") as fw:
        writer = csv.DictWriter(fw, fieldnames=bad_case_rows[0].keys())
        writer.writeheader()
        writer.writerows(bad_case_rows)

    # 计算指标
    acc_baseline = round((knowledge_correct / knowledge_total)*100,2) if knowledge_total>0 else 0.0
    ci_low, ci_high = calc_95_ci(knowledge_correct, knowledge_total)

    print("===== 评测汇总指标 =====")
    print(f"总样本：{len(infer_data)}")
    print(f"knowledge样本总数 N_knowledge：{knowledge_total}")
    print(f"knowledge答对 Correct：{knowledge_correct}")
    print(f"Knowledge Accuracy【主基线指标】：{acc_baseline} %")
    print(f"95%置信区间：[{ci_low} %, {ci_high} %]")
    print(f"logic_fiction样本总数：{logic_fiction_total}，拒绝数量：{logic_fiction_reject}")

    return {
        "total_all": len(infer_data),
        "N_knowledge": knowledge_total,
        "Correct_knowledge": knowledge_correct,
        "Acc_baseline_pct": acc_baseline,
        "ci_95_low": ci_low,
        "ci_95_high": ci_high,
        "logic_fiction_total": logic_fiction_total,
        "logic_fiction_reject": logic_fiction_reject
    }

if __name__ == "__main__":
    metric = do_eval(
        infer_result_path="output/raw_infer_result.json",
        out_csv="output/eval_result.csv",
        bad_case_csv="output/bad_case.csv"
    )