# -*- coding: utf-8 -*-
"""
多厂商大模型对比 · 自动评分流程（参考实现）
=============================================
对应文档：四、测评方法学 / 五、评分执行方案 / 六、测试结果

流程：① 采集 → ② 脱敏 → ③ 判分（客观题脚本 / 开放式题 LLM 盲评）→ ④ 汇总 → ⑤ 输出
依赖：仅标准库（Python 3.8+）
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# ============================================================
# 0. 全局配置（参数固定，保证可复现）
# ============================================================
SCORE_MAX     = 2          # 统一 0/1/2 分制
NUM_TOLERANCE = 0.01       # 数值题容差 ±1%
PCT_TOLERANCE = 0.005      # 百分比题容差 ±0.5 个百分点
ROUNDS        = 3          # 每题重复采样次数（3–5 次）

DIFF_NORMAL = 0.05         # 跨厂商差异 ≤5%：正常波动
DIFF_GAP    = 0.15         # 5%–15%：有差距；>15%：明显弱

# 加权口径：六、测试结果 → 2. 各项占比
DIMENSION_WEIGHTS: Dict[str, float] = {
    "comprehensive": 0.60,   # 综合能力：A–D、G、H
    "anomaly":       0.10,   # 异常识别：E
    "fingerprint":   0.20,   # 指纹一致性：F
    "stability":     0.05,   # 稳定性：多次采样一致率
    "token":         0.05,   # Token 消耗：相对最低值
}
DIMENSION_OF_CATEGORY: Dict[str, str] = {
    "A": "comprehensive", "B": "comprehensive", "C": "comprehensive",
    "D": "comprehensive", "E": "anomaly",       "F": "fingerprint",
    "G": "comprehensive", "H": "comprehensive",
}
DIMENSION_LABELS: Dict[str, str] = {
    "comprehensive": "综合能力(60%)", "anomaly": "异常识别(10%)",
    "fingerprint": "指纹一致性(20%)", "stability": "稳定性(5%)",
    "token": "Token消耗(5%)",
}

# ============================================================
# 1. 数据结构：错误标签 / 题库 / 采集样本 / 判分结果
# ============================================================
class ErrorTag(str, Enum):
    """错题归因标签（四、测评方法学 → 3. 错题归因）"""
    NONE                = "-"
    HALLUCINATION       = "幻觉"
    REASONING_BREAK     = "推理断裂"
    FORMAT_VIOLATION    = "格式违规"
    IMPROPER_REFUSAL    = "拒答不当"
    INSTRUCTION_IGNORED = "指令未遵循"


class JudgeKind(str, Enum):
    """判分方式：客观题走脚本，开放式题走 LLM 盲评"""
    NUMERIC = "numeric"        # 数值/计算题（含要点校验）
    JSON    = "json"           # JSON 结构 + 键名 + 字段值
    PATTERN = "pattern"        # 格式/保真题（必含 / 禁止）
    LLM     = "llm_rubric"     # 开放式题 0/1/2 盲评


@dataclass(frozen=True)
class NumericKey:
    """一个必须命中的数值答案（支持等价表示，如百分比 ↔ 小数）"""
    name: str
    expected: float
    tol: float = NUM_TOLERANCE
    alternatives: Tuple[float, ...] = ()


@dataclass(frozen=True)
class Question:
    """题目 + 标准答案 + 0/1/2 评分细则"""
    qid: str
    category: str                                  # A / B / ... / H
    prompt: str                                    # 原题（盲评提示词用）
    kind: JudgeKind
    answer_key: str = ""                           # 标准答案要点
    rubric: str = ""                               # 2 分 / 1 分 / 0 分 细则
    nums: Tuple[NumericKey, ...] = ()              # 数值题关键值
    json_keys: Tuple[str, ...] = ()                # JSON 题键名
    json_expected: Tuple[Dict[str, Any], ...] = () # JSON 题标准值
    must_match: Tuple[str, ...] = ()               # 必含正则
    forbidden: Tuple[str, ...] = ()                # 禁止正则（如表格符号）
    default_tag: ErrorTag = ErrorTag.NONE          # 判 0 分时的默认归因
    anonymize: bool = True                         # F 类身份题置 False（脱敏会删掉答案本体）


@dataclass
class Sample:
    """一次采集记录（同一题 × 同一厂商 × 一轮）"""
    vendor: str
    qid: str
    round_idx: int
    answer: str
    tokens: int = 0
    latency_ms: int = 0


@dataclass
class SampleScore:
    """一次采集的判分结果"""
    vendor: str
    qid: str
    category: str
    round_idx: int
    score: int
    reason: str
    tag: ErrorTag = ErrorTag.NONE
    tokens: int = 0


@dataclass
class QuestionResult:
    """同一题多次采样聚合后的结果"""
    vendor: str
    qid: str
    category: str
    avg_score: float
    scores: List[int]
    stability: float
    tag: ErrorTag
    tokens: int


@dataclass
class VendorReport:
    """厂商级加权汇总"""
    vendor: str
    dimensions: Dict[str, float]
    total: float


# ============================================================
# 2. 脱敏：去掉模型名 / 厂商名，评分人只按 rubric 打分
# ============================================================
VENDOR_TERMS: Tuple[str, ...] = (
    "OpenAI", "Anthropic", "Google", "DeepMind", "Meta", "xAI", "Mistral",
    "阿里", "通义", "百度", "文心", "字节", "豆包", "腾讯", "混元",
    "智谱", "月之暗面", "Kimi", "DeepSeek", "深度求索",
)
MODEL_TERMS: Tuple[str, ...] = (
    "GPT-4o", "GPT-4", "GPT-3.5", "GPT", "Claude", "Gemini", "Llama",
    "Qwen", "通义千问", "文心一言", "GLM", "Grok", "DeepSeek-V3", "DeepSeek-R1",
)
MASK = "[已脱敏]"


def anonymize(text: str, extra_terms: Sequence[str] = ()) -> str:
    """按「长词优先」替换厂商/模型名，避免误伤（如先 GPT-4o 再 GPT）"""
    terms = sorted(set(VENDOR_TERMS) | set(MODEL_TERMS) | set(extra_terms),
                   key=len, reverse=True)
    for term in terms:
        text = re.sub(re.escape(term), MASK, text, flags=re.IGNORECASE)
    return text


# ============================================================
# 3. 客观题自动判分
# ============================================================
SCALE = {"亿": 1e8, "万": 1e4, "千": 1e3, "k": 1e3, "K": 1e3, "M": 1e6}
ALPHA_UNITS = {"k", "K", "M"}      # 需确认后面不是字母，避免 200kW 被当成 200k
NUMBER_RE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(亿|万|千|[kKM])?")
# 先屏蔽型号名（H200 / B300 / A100），避免其中的数字污染数值比对
MODEL_TOKEN_RE = re.compile(r"\b[A-Za-z]{1,4}[- ]?\d{2,5}\b")
FENCE_RE = re.compile(r"`{3}(?:json)?\s*(.*?)`{3}", re.S)


def extract_numbers(text: str) -> List[float]:
    """从自由文本中抽取数值，支持 万/亿/千/K/M 单位与千分位逗号"""
    cleaned = MODEL_TOKEN_RE.sub(" ", text.replace(",", "").replace("，", ""))
    numbers: List[float] = []
    for match in NUMBER_RE.finditer(cleaned):
        value = float(match.group(1))
        unit = match.group(2)
        if unit:
            nxt = cleaned[match.end(2): match.end(2) + 1]
            # 单位是 k/K/M 且后面紧跟字母 → 属于 kW / MB 这类单位，不换算
            if not (unit in ALPHA_UNITS and re.match(r"[A-Za-z]", nxt or "")):
                value *= SCALE[unit]
        numbers.append(value)
    return numbers


def _close(value: float, key: NumericKey) -> bool:
    """数值命中判定：相对容差；alternatives 用于百分比 ↔ 小数的等价表示"""
    for target in (key.expected, *key.alternatives):
        ref = abs(target) if target else 1.0
        if abs(value - target) <= max(key.tol * ref, 1e-9):
            return True
    return False


def _missing_patterns(text: str, patterns: Sequence[str]) -> List[str]:
    return [p for p in patterns if not re.search(p, text)]


def judge_numeric(answer: str, q: Question) -> Tuple[int, str, ErrorTag]:
    """数值/计算题：全部关键值 + 必含要点命中 = 2；部分命中 = 1；否则 0"""
    bad = _missing_patterns(answer, q.forbidden)
    if bad:
        return 0, "出现禁止内容：" + "；".join(bad), ErrorTag.INSTRUCTION_IGNORED

    if not q.nums and not q.must_match:
        return SCORE_MAX, "无数值/要点约束，默认通过", ErrorTag.NONE

    numbers = extract_numbers(answer)
    missing_nums = [k.name for k in q.nums
                    if not any(_close(n, k) for n in numbers)]
    missing_pat = _missing_patterns(answer, q.must_match)

    if not missing_nums and not missing_pat:
        return SCORE_MAX, "关键数值与要点全部命中", ErrorTag.NONE
    if len(missing_nums) < len(q.nums) or len(missing_pat) < len(q.must_match):
        missing = missing_nums + missing_pat
        return 1, "部分命中，缺失：" + "、".join(missing), ErrorTag.NONE
    return 0, "关键数值全部不匹配或未作答", q.default_tag


def _load_json(answer: str) -> Optional[Any]:
    """优先取代码块，其次取首个 [ ... ] / { ... }"""
    block = FENCE_RE.search(answer)
    text = block.group(1) if block else answer
    picked = re.search(r"[\[{].*[\]}]", text, re.S)
    if not picked:
        return None
    try:
        return json.loads(picked.group(0))
    except json.JSONDecodeError:
        return None


def _json_values_equal(got: Sequence[Dict[str, Any]],
                       expected: Sequence[Dict[str, Any]]) -> bool:
    for g, e in zip(got, expected):
        for field_name, expected_value in e.items():
            actual = g.get(field_name)
            if isinstance(expected_value, (int, float)) and \
               isinstance(actual, (int, float)) and not isinstance(actual, bool):
                ref = abs(expected_value) if expected_value else 1.0
                if abs(actual - expected_value) > NUM_TOLERANCE * ref:
                    return False
            elif str(actual).strip() != str(expected_value).strip():
                return False
    return True


def judge_json(answer: str, q: Question) -> Tuple[int, str, ErrorTag]:
    """JSON 题：合法 + 键名一致 + 字段值一致 = 2；结构对但键名/单位错 = 1"""
    data = _load_json(answer)
    if data is None:
        return 0, "JSON 解析失败（结构非法）", ErrorTag.FORMAT_VIOLATION
    if not isinstance(data, list) or len(data) != len(q.json_expected):
        return 0, "JSON 结构或条目数不符合标准答案", ErrorTag.FORMAT_VIOLATION
    if not all(isinstance(item, dict) and set(item.keys()) == set(q.json_keys)
               for item in data):
        return 1, "结构合法但键名不一致", ErrorTag.FORMAT_VIOLATION
    if _json_values_equal(data, q.json_expected):
        return SCORE_MAX, "JSON 合法，键名与字段值均一致", ErrorTag.NONE
    return 1, "键名一致但字段值或单位有误", ErrorTag.NONE


def judge_pattern(answer: str, q: Question) -> Tuple[int, str, ErrorTag]:
    """格式/保真题：禁止项命中直接 0；必含项全中 = 2，部分 = 1"""
    bad = _missing_patterns(answer, q.forbidden)
    if bad:
        return 0, "出现禁止内容（指令未遵循）", ErrorTag.INSTRUCTION_IGNORED
    if not q.must_match:
        return SCORE_MAX, "无必含约束，默认通过", ErrorTag.NONE
    hit = len(q.must_match) - len(_missing_patterns(answer, q.must_match))
    if hit == len(q.must_match):
        return SCORE_MAX, f"必含项 {hit}/{len(q.must_match)} 全部命中", ErrorTag.NONE
    if hit:
        return 1, f"必含项部分命中 {hit}/{len(q.must_match)}", ErrorTag.NONE
    return 0, "必含项均未命中", ErrorTag.INSTRUCTION_IGNORED


# ============================================================
# 4. 开放式题 LLM 盲评（与「五、评分执行方案 → 2」提示词模板一致）
# ============================================================
LLM_RUBRIC_TEMPLATE = """你是一个客观的评分员，请按以下标准给模型回答打分（0/1/2）：
【题目】{prompt}
【标准答案要点】{answer_key}
【评分细则】{rubric}
【模型回答（已脱敏）】{answer}
请只输出：得分（0/1/2）+ 一句评分理由。
"""
SCORE_RE = re.compile(r"(?<!\d)([012])(?!\d)\s*分?")


def judge_llm(answer: str, q: Question,
              llm: Callable[[str], str]) -> Tuple[int, str, ErrorTag]:
    """调用裁判模型盲评；同一题所有厂商使用同一评分会话"""
    prompt = LLM_RUBRIC_TEMPLATE.format(
        prompt=q.prompt,
        answer_key=q.answer_key or "（见评分细则）",
        rubric=q.rubric or "2=完全正确；1=部分正确；0=错误或编造",
        answer=answer,
    )
    reply = (llm(prompt) or "").strip()
    matched = SCORE_RE.search(reply)
    if not matched:
        return 0, "评分模型输出无法解析：" + reply[:60], ErrorTag.FORMAT_VIOLATION
    score = int(matched.group(1))
    tag = ErrorTag.NONE if score > 0 else q.default_tag
    return score, reply[:120], tag


# ============================================================
# 5. 单次采样判分入口（脱敏 → 分流 → 归因）
# ============================================================
def score_sample(sample: Sample, question: Question,
                 llm: Optional[Callable[[str], str]] = None) -> SampleScore:
    text = anonymize(sample.answer) if question.anonymize else sample.answer

    if question.kind is JudgeKind.NUMERIC:
        score, reason, tag = judge_numeric(text, question)
    elif question.kind is JudgeKind.JSON:
        score, reason, tag = judge_json(text, question)
    elif question.kind is JudgeKind.PATTERN:
        score, reason, tag = judge_pattern(text, question)
    else:
        if llm is None:
            raise ValueError(f"题 {question.qid} 为开放式题，必须提供裁判模型回调")
        score, reason, tag = judge_llm(text, question, llm)

    if score == 0 and tag is ErrorTag.NONE:
        tag = question.default_tag
    return SampleScore(sample.vendor, sample.qid, question.category,
                       sample.round_idx, score, reason, tag, sample.tokens)


# ============================================================
# 6. 汇总：多次采样聚合 → 维度得分 → 加权总分 → 差异结论
# ============================================================
def stability_of(scores: Sequence[int]) -> float:
    """稳定性：多次采样得分的众数占比（1.0 = 完全一致）"""
    if not scores:
        return 0.0
    return max(scores.count(s) for s in set(scores)) / len(scores)


def aggregate(sample_scores: Sequence[SampleScore]) -> List[QuestionResult]:
    buckets: Dict[Tuple[str, str], List[SampleScore]] = {}
    for item in sample_scores:
        buckets.setdefault((item.vendor, item.qid), []).append(item)

    results: List[QuestionResult] = []
    for (vendor, qid), items in sorted(buckets.items()):
        scores = [i.score for i in items]
        tags = [i.tag for i in items if i.tag is not ErrorTag.NONE]
        results.append(QuestionResult(
            vendor=vendor, qid=qid, category=items[0].category,
            avg_score=round(statistics.fmean(scores), 4),
            scores=scores,
            stability=round(stability_of(scores), 4),
            tag=statistics.mode(tags) if tags else ErrorTag.NONE,
            tokens=sum(i.tokens for i in items),
        ))
    return results


def dimension_scores(results: Sequence[QuestionResult]) -> Dict[str, float]:
    """各维度归一化得分（0–1）：客观+主观统一按 平均分 / 2 处理"""
    buckets: Dict[str, List[float]] = {key: [] for key in DIMENSION_WEIGHTS}
    for item in results:
        dimension = DIMENSION_OF_CATEGORY.get(item.category)
        if dimension:
            buckets[dimension].append(item.avg_score / SCORE_MAX)
    return {key: (statistics.fmean(values) if values else 0.0)
            for key, values in buckets.items()}


def token_scores(results: Sequence[QuestionResult]) -> Dict[str, float]:
    """Token 消耗得分：以最低消耗厂商为 1.0，其余按比例折算"""
    totals: Dict[str, int] = {}
    for item in results:
        totals[item.vendor] = totals.get(item.vendor, 0) + item.tokens
    if not totals:
        return {}
    best = min(totals.values()) or 1
    return {vendor: (best / used if used else 0.0)
            for vendor, used in totals.items()}


def build_reports(results: Sequence[QuestionResult]) -> Dict[str, VendorReport]:
    by_vendor: Dict[str, List[QuestionResult]] = {}
    for item in results:
        by_vendor.setdefault(item.vendor, []).append(item)
    tokens = token_scores(results)

    reports: Dict[str, VendorReport] = {}
    for vendor, items in by_vendor.items():
        dims = dimension_scores(items)
        dims["stability"] = round(statistics.fmean([i.stability for i in items]), 4) \
            if items else 0.0
        dims["token"] = round(tokens.get(vendor, 0.0), 4)
        total = sum(DIMENSION_WEIGHTS[key] * dims.get(key, 0.0)
                    for key in DIMENSION_WEIGHTS)
        reports[vendor] = VendorReport(vendor, dims, round(total, 4))
    return reports


def diff_conclusion(reports: Dict[str, VendorReport]) -> str:
    """差异结论：≤5% 正常；5%–15% 有差距；>15% 明显弱"""
    if len(reports) < 2:
        return "厂商数量不足 2 个，无法比较"
    totals = [r.total for r in reports.values()]
    best, worst = max(totals), min(totals)
    if best <= 0:
        return "无有效得分，请检查采集或判分配置"
    gap = (best - worst) / best
    if gap <= DIFF_NORMAL:
        level = "差异 ≤5%，视为同一水平（正常波动）"
    elif gap <= DIFF_GAP:
        level = "差异 5%–15%，存在可观测差距"
    else:
        level = "差异 >15%，较弱厂商明显落后，需复核是否掺水/不稳定"
    return f"最大相对差异 {gap:.1%} → {level}"


# ============================================================
# 7. 输出：明细表 + 加权总分表
# ============================================================
def to_markdown_table(results: Sequence[QuestionResult]) -> str:
    lines = [
        "| 厂商 | 题号 | 类别 | 均分 | 各轮得分 | 稳定性 | 错误类型 | Token |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        lines.append(
            f"| {item.vendor} | {item.qid} | {item.category} | {item.avg_score} "
            f"| {'/'.join(map(str, item.scores))} | {item.stability:.0%} "
            f"| {item.tag.value} | {item.tokens} |"
        )
    return "\n".join(lines)


def to_report_markdown(reports: Dict[str, VendorReport]) -> str:
    keys = list(DIMENSION_WEIGHTS)
    lines = [
        "| 厂商 | " + " | ".join(DIMENSION_LABELS[k] for k in keys) + " | 加权总分 |",
        "| --- | " + " | ".join("---" for _ in keys) + " | --- |",
    ]
    for vendor in sorted(reports, key=lambda v: -reports[v].total):
        report = reports[vendor]
        cells = " | ".join(f"{report.dimensions.get(k, 0.0) * 100:.1f}" for k in keys)
        lines.append(f"| {vendor} | {cells} | {report.total * 100:.1f} |")
    return "\n".join(lines)


# ============================================================
# 8. 题库登记（示例：与「七、标准答案与评分要点」一一对应）
# ============================================================
REGISTRY: Dict[str, Question] = {
    # ---- 客观题：脚本判分 ----
    "C7": Question(
        qid="C7", category="C", kind=JudgeKind.JSON,
        prompt="将报价输出为 JSON 数组，键名必须为 model / price / power："
               "H200 600万 10kW；B300 1600万 18kW；A100 400万 6.5kW。",
        answer_key='[{"model":"H200","price":6000000,"power":10},'
                   '{"model":"B300","price":16000000,"power":18},'
                   '{"model":"A100","price":4000000,"power":6.5}]',
        rubric="2=JSON 合法且键名一致；1=结构对但键名/单位错；0=结构非法",
        json_keys=("model", "price", "power"),
        json_expected=(
            {"model": "H200", "price": 6_000_000, "power": 10},
            {"model": "B300", "price": 16_000_000, "power": 18},
            {"model": "A100", "price": 4_000_000, "power": 6.5},
        ),
        default_tag=ErrorTag.FORMAT_VIOLATION,
    ),
    "D7": Question(
        qid="D7", category="D", kind=JudgeKind.NUMERIC,
        prompt="月调用 100 万次：模型 A 单价 $3/M tokens、每次 1K tokens；"
               "模型 B 单价 $8/M tokens、每次 0.6K tokens。求各自月成本与反转条件。",
        answer_key="A 月成本 $3000、B 月成本 $4800，A 更低；"
                   "当 B 单任务耗 token 降至约 0.375K 以下（或 B 降价）时结论反转。",
        rubric="2=计算+反转条件；1=仅计算；0=错误或编造",
        nums=(
            NumericKey("模型A月成本(USD)", 3000),
            NumericKey("模型B月成本(USD)", 4800),
            NumericKey("反转临界单任务耗token", 375, tol=0.05, alternatives=(0.375,)),
        ),
        must_match=(r"反转|临界|低于|小于",),
        default_tag=ErrorTag.REASONING_BREAK,
    ),
    "E8": Question(
        qid="E8", category="E", kind=JudgeKind.NUMERIC,
        prompt="方案 A 报价 ¥6,000,000/台，方案 B 报价 0.6 千万/台，两者是否等价？",
        answer_key="等价：¥6,000,000 = 600 万 = 0.6 千万。",
        rubric="2=等价且换算正确；1=仅给出结论无换算；0=错误",
        nums=(NumericKey("金额(元)", 6_000_000, alternatives=(600.0,)),),
        must_match=(r"等价|等值|相同|一致",),
        default_tag=ErrorTag.REASONING_BREAK,
    ),
    "G1": Question(
        qid="G1", category="G", kind=JudgeKind.NUMERIC,
        prompt="方案 A：20 台 H200（10kW、600 万）；方案 B：12 台 H200 + 4 台 B300"
               "（18kW、1600 万）。H200 算力=1、B300 算力=3，求总功耗、总成本、"
               "单位成本算力比，并判断哪个更优。",
        answer_key="A：200kW、1.2 亿、比值 1.67；B：192kW、1.36 亿、比值 1.76，"
                   "按单位成本算力比 B 更优。",
        rubric="2=主要计算全对 + 结论；1=部分计算正确；0=错误",
        nums=(
            NumericKey("A总功耗(kW)", 200),
            NumericKey("B总功耗(kW)", 192),
            NumericKey("A总成本(元)", 120_000_000),
            NumericKey("B总成本(元)", 136_000_000),
            NumericKey("A单位成本算力比", 1.67, tol=0.02),
            NumericKey("B单位成本算力比", 1.76, tol=0.02),
        ),
        default_tag=ErrorTag.REASONING_BREAK,
    ),
    "G7": Question(
        qid="G7", category="G", kind=JudgeKind.NUMERIC,
        prompt="某 API 单次故障率 0.1%，连续 10 次全成功概率？"
               "要达到 99.9% 可用性，单次成功率至少多少？",
        answer_key="(0.999)^10 ≈ 0.9900；单次成功率需 ≥ 0.9999（99.99%）。",
        rubric="2=两问都对；1=一问正确；0=错误",
        nums=(
            NumericKey("10次全成功概率", 0.99, tol=0.01, alternatives=(99.0,)),
            NumericKey("单次最低成功率", 0.9999, tol=0.001, alternatives=(99.99,)),
        ),
        default_tag=ErrorTag.REASONING_BREAK,
    ),
    "H4": Question(
        qid="H4", category="H", kind=JudgeKind.NUMERIC,
        prompt="“¥6,000,000”与“600 万”是否同一金额？将 12,345,678 写成中文大写金额。",
        answer_key="等价；12,345,678 = 壹仟贰佰叁拾肆万伍仟陆佰柒拾捌元。",
        rubric="2=等价 + 大写正确；1=缺一项；0=错误",
        nums=(
            NumericKey("¥6,000,000 等值", 6_000_000),
            NumericKey("原文数字 12,345,678", 12_345_678, tol=1e-9),
        ),
        must_match=(r"壹仟贰佰叁拾肆万伍仟陆佰柒拾捌", r"等价|相同|一致"),
        default_tag=ErrorTag.FORMAT_VIOLATION,
    ),
    "C8": Question(
        qid="C8", category="C", kind=JudgeKind.PATTERN,
        prompt="用 Markdown 表格对比 H200 与 B300，但本次回答禁止出现任何表格符号，"
               "并说明如何取舍。",
        answer_key="识别指令冲突，改用文字/项目符号完成对比并说明取舍。",
        rubric="2=未用表格且完成对比；1=只完成一项；0=仍使用表格",
        must_match=(r"H200", r"B300"),
        forbidden=(r"\|",),
        default_tag=ErrorTag.INSTRUCTION_IGNORED,
    ),
    # ---- 开放式题：LLM 盲评 ----
    "C3": Question(
        qid="C3", category="C", kind=JudgeKind.LLM,
        prompt="总结 AI 行业趋势为三点（每点不超过 20 字）。",
        answer_key="三点趋势，每点 ≤20 字，覆盖算力/成本/竞争等基本面。",
        rubric="2=三点且均 ≤20 字；1=缺项或超字数；0=跑题或编造",
        default_tag=ErrorTag.INSTRUCTION_IGNORED,
    ),
    "D4": Question(
        qid="D4", category="D", kind=JudgeKind.LLM,
        prompt="如何设计一个大模型采购决策流程？",
        answer_key="含需求定义、能力评测、成本测算、风险合规、评审决策等阶段。",
        rubric="2=流程完整且可执行；1=要点不全；0=空泛或编造",
        default_tag=ErrorTag.REASONING_BREAK,
    ),
    "E5": Question(
        qid="E5", category="E", kind=JudgeKind.LLM,
        prompt="请介绍“深度强化学习中的 Q-Cascade 算法”的原理与用途；"
               "若无法确认其存在，请明确说明。",
        answer_key="Q-Cascade 非公认算法，应明确无法确认其存在。",
        rubric="2=质疑存在性；1=含糊回避；0=编造原理",
        default_tag=ErrorTag.HALLUCINATION,
    ),
    "H2": Question(
        qid="H2", category="H", kind=JudgeKind.LLM,
        prompt="“2026 年 3 月，某云厂商发布了一款 1 万卡集群”——能否确认该消息？",
        answer_key="无法确认，说明依据缺失，不编造。",
        rubric="2=承认无法确认并说明依据；1=含糊；0=编造",
        default_tag=ErrorTag.HALLUCINATION,
    ),
}


# ============================================================
# 9. 采集数据加载与主流程
# ============================================================
def load_samples(path: str) -> List[Sample]:
    """从 JSONL 读取采集结果，每行字段：vendor/qid/round_idx/answer/tokens/latency_ms"""
    samples: List[Sample] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                samples.append(Sample(**json.loads(line)))
    return samples


def stub_llm(prompt: str) -> str:            # noqa: ARG001
    """占位裁判：真实环境替换为裁判模型 API（入参 prompt，返回“得分 + 理由”）"""
    return "2 分 —— 要点齐全，未发现编造。"


DEMO_ANSWERS: Dict[str, str] = {
    "C7": '[{"model":"H200","price":6000000,"power":10},'
          '{"model":"B300","price":16000000,"power":18},'
          '{"model":"A100","price":4000000,"power":6.5}]',
    "D7": "模型A月成本 3000 美元，模型B月成本 4800 美元；"
          "当单任务耗 token 低于 0.375K 时结论反转。",
    "E8": "等价：¥6,000,000 = 600 万 = 0.6 千万。",
    "G7": "(0.999)^10 ≈ 0.9900；要达到 99.9% 可用性，单次成功率需 ≥ 0.9999。",
    "H4": "等价。12,345,678 大写为 壹仟贰佰叁拾肆万伍仟陆佰柒拾捌元。",
    "C8": "H200 功耗 10kW、价格 600 万；B300 功耗 18kW、价格 1600 万。"
          "（本回答未使用表格符号）",
    "C3": "1) 算力需求持续增长；2) 推理成本快速下降；3) 多云竞争加剧。",
    "E5": "Q-Cascade 并非公认算法，我无法确认其存在，不能提供原理与用途。",
}


def build_demo_samples(vendors: Sequence[str] = ("云厂A", "云厂B", "云厂C"),
                       rounds: int = ROUNDS) -> List[Sample]:
    samples: List[Sample] = []
    for vendor in vendors:
        for qid, answer in DEMO_ANSWERS.items():
            for round_idx in range(1, rounds + 1):
                samples.append(Sample(
                    vendor=vendor, qid=qid, round_idx=round_idx, answer=answer,
                    tokens=800 + sum(map(ord, qid)) % 5 * 37 + round_idx,
                    latency_ms=1200 + 50 * round_idx,
                ))
    return samples


def main(samples: Optional[Sequence[Sample]] = None) -> None:
    """完整流程：采集 → 脱敏 → 判分 → 汇总 → 输出"""
    data = list(samples) if samples else build_demo_samples()
    judge_model: Callable[[str], str] = stub_llm      # ← 替换为真实裁判模型调用

    sample_scores = [score_sample(s, REGISTRY[s.qid], judge_model)
                     for s in data if s.qid in REGISTRY]
    results = aggregate(sample_scores)
    reports = build_reports(results)

    print("### 1. 每题得分明细（含轮次与错误归因）\n")
    print(to_markdown_table(results))
    print("\n### 2. 加权总分（综合/异常/指纹/稳定/Token）\n")
    print(to_report_markdown(reports))
    print("\n### 3. 跨厂商差异结论\n")
    print(diff_conclusion(reports))


if __name__ == "__main__":
    main()
    # 真实使用：main(load_samples("collected_answers.jsonl"))
