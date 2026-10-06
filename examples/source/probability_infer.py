import json
# 此处为伪代码，对接你实际推理SDK/API
def infer_one(prompt: str):
    """
    输入prompt，返回 (full_output:str, first_token:str)
    业务侧对接自己模型推理接口；每条独立会话，无缓存
    """
    # ----------------------
    # 填入你的模型推理调用代码
    # ----------------------
    full_output = ""
    first_token = ""
    return full_output, first_token


def run_all_infer(label_json_path: str, gt_json_path: str, out_infer_json: str):
    with open(label_json_path, "r", encoding="utf-8") as f:
        label_map = json.load(f)
    with open(gt_json_path, "r", encoding="utf-8") as f:
        gt_whitelist = json.load(f)

    result_list = []
    for prompt_id_str in label_map:
        prompt_id = int(prompt_id_str)
        item = label_map[prompt_id_str]
        prompt_text = item["prompt"]
        label = item["label"]
        gt = gt_whitelist.get(prompt_id_str, [])

        full_out, first_tok = infer_one(prompt_text)
        result_list.append({
            "prompt_id": prompt_id,
            "prompt": prompt_text,
            "label": label,
            "full_output": full_out,
            "first_token": first_tok,
            "gt_whitelist": gt
        })

    with open(out_infer_json, "w", encoding="utf-8") as fw:
        json.dump(result_list, fw, ensure_ascii=False, indent=2)
    print(f"推理原始结果保存至 {out_infer_json}")

if __name__ == "__main__":
    run_all_infer(
        label_json_path="label_map.json",
        gt_json_path="gt_whitelist.json",
        out_infer_json="output/raw_infer_result.json"
    )