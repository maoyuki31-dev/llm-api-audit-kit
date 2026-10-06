# -*- coding: utf-8 -*-
"""
自动跑题库 → 生成 JSONL（给 scoring_pipeline 用）
"""

import json
import time
import requests

# =========================
# 1. 模型配置（替换这里）
# =========================
API_URL = "https://api.openai.com/v1/chat/completions"
API_KEY = "YOUR_API_KEY"

MODEL = "gpt-4o"   # 可替换 Claude / Gemini / 自建模型
ROUNDS = 3         # 每题跑3次（符合规范）

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# =========================
# 2. 统一 Prompt（必须固定）
# =========================
SYSTEM_PROMPT = """请按以下格式回答：
1. 结论
2. 推理过程
3. 最终答案
"""

# =========================
# 3. 题库（从你文件抽关键题）
# =========================
QUESTIONS = {
    "A1": "用一句话解释什么是Token",
    "B1": "7台H200（10kW）+4台B300（18kW），总功耗是多少",
    "B7": "H200 600万，B300 1600万，预算1.2亿，至少2台B300，求最优方案",
    "C7": "将报价输出为JSON：H200 600万 10kW；B300 1600万 18kW",
    "D7": "100万次调用，A:3$/M 1K tokens；B:8$/M 0.6K tokens，求成本",
    "E5": "介绍Q-Cascade算法，如无法确认请说明",
    "G7": "故障率0.1%，连续10次成功概率是多少",
    "H4": "¥6,000,000和600万是否相同，并写中文大写金额"
}

# =========================
# 4. 调模型函数
# =========================
def call_model(prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 800
    }

    start = time.time()

    resp = requests.post(API_URL, headers=HEADERS, json=payload)
    data = resp.json()

    latency = int((time.time() - start) * 1000)

    answer = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("total_tokens", 0)

    return answer, tokens, latency

# =========================
# 5. 主流程（生成JSONL）
# =========================
def run_benchmark(output_file="collected_answers.jsonl", vendor_name="云厂A"):
    results = []

    for qid, question in QUESTIONS.items():
        print(f"\n>>> Running {qid}")

        for round_idx in range(1, ROUNDS + 1):
            try:
                answer, tokens, latency = call_model(question)

                record = {
                    "vendor": vendor_name,
                    "qid": qid,
                    "round_idx": round_idx,
                    "answer": answer,
                    "tokens": tokens,
                    "latency_ms": latency
                }

                results.append(record)

                print(f"Round {round_idx} done")

                time.sleep(1)  # 防限流

            except Exception as e:
                print(f"Error: {e}")

    # 写入 JSONL
    with open(output_file, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n✅ 已生成文件：{output_file}")


# =========================
# 6. 运行
# =========================
if __name__ == "__main__":
    run_benchmark()