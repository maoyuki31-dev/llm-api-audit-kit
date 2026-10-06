import json
import csv

def build_label_preview(origin_txt_path: str, out_label_json: str):
    # 读取原始prompt
    prompts = []
    with open(origin_txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip():
                prompts.append(line)

    label_map = {}
    candidate_logic_fiction = []

    # 预筛关键词，发现命中则标记为待复核候选，默认全部为knowledge
    filter_keywords = [
        "zorvania", "lirovia", "vorolia", "mirnovia", "kaeros",
        "torvath", "sinteria", "phovoria",
        "should", "better",
        "father has 5 sons", "boil one egg", "take away four apples"
    ]

    for prompt_id, prompt_text in enumerate(prompts, start=1):
        lower_text = prompt_text.lower()
        hit = any(kw in lower_text for kw in filter_keywords)
        label_map[prompt_id] = {
            "prompt": prompt_text,
            "label": "knowledge"
        }
        if hit:
            candidate_logic_fiction.append((prompt_id, prompt_text))

    # 输出候选列表给人工复核
    print("===== 需要人工复核的 logic_fiction 候选列表 =====")
    for pid, ptext in candidate_logic_fiction:
        print(f"id:{pid} | {ptext}")
    print(f"\n候选总数量：{len(candidate_logic_fiction)}")

    # 输出标签json（此时候选还未修改，人工改完再保存最终版）
    with open(out_label_json, "w", encoding="utf-8") as fw:
        json.dump(label_map, fw, ensure_ascii=False, indent=2)
    print(f"\n临时标签文件输出到 {out_label_json}，请人工把确认的logic_fiction条目label改为logic_fiction")

if __name__ == "__main__":
    build_label_preview(
        origin_txt_path="Code_20260916.txt",
        out_label_json="label_map.json"
    )