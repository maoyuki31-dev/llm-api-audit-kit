# 参考代码与运行说明

本目录基于原方案附件维护参考实现。2026-10-06 修复了评分、空集合和采集对齐问题，并新增离线回归测试；旧版附件可从 Git 历史查看。内部历史测试见[匿名化案例](../case-studies/anonymized-evaluation/README.md)，不因本次代码修复改写历史分数。

## 当前实现

| 文件 | 用途与状态 |
| --- | --- |
| [scoring_pipeline.py](scoring_pipeline.py) | 11 题参考子集；修复禁止项、负数、复合单位；严格 JSON；真实数据必须显式输入与配置裁判 |
| [multi_vendor_infer.py](source/multi_vendor_infer.py) | 直接读取同一份 11 题 registry 的完整提示词；保存失败请求，评分入口拒绝未处理的失败记录 |
| [api_client.py](source/api_client.py) | 标准库 HTTP 客户端；显式环境变量配置、超时、状态与响应检查；缺失 usage 保持 null |
| [probability_infer.py](source/probability_infer.py) | 实际 Chat Completions 接口适配；先校验全部标签与 GT，再发起请求；创建输出目录 |
| [probability_score.py](source/probability_score.py) | 规范化完整答案匹配、Wilson 区间、空数据和全对处理；保存复核清单 |
| [behavior_infer.py](source/behavior_infer.py) | 原始行为采样附件，仍需适配部署环境 |
| [behavior_score.py](source/behavior_score.py) | 原始行为评分附件，旧 SDK 与人工答案输入仍需适配 |
| [label_candidates.py](source/label_candidates.py) | 标签预筛附件；默认 knowledge，分类必须人工确认 |

## 环境与离线验证

修复后的多厂商、概率流程和测试仅依赖 Python 标准库，建议 Python 3.10+。原始行为附件另依赖 `openai`，采集和评分仍使用不同年代的 SDK 接口，未纳入统一运行环境。

以下命令均从仓库根目录执行：

```bash
python -m unittest discover -s tests -v
python examples/scoring_pipeline.py --demo
```

`--demo` 使用模拟输入和固定裁判，输出明确标注 DEMO。无参数、空输入、未知题号和重复样本不会自动变成演示或被静默跳过。测试使用模拟响应，不访问网络、不消耗 API 额度。

## 多厂商采集与评分

先在本机设置环境变量（不要将密钥提交到仓库）：

| 环境变量 | 含义 |
| --- | --- |
| `LLM_API_URL` | 被测服务完整 Chat Completions URL，包括 `/chat/completions` 路径 |
| `LLM_API_KEY` | 被测服务密钥 |
| `LLM_MODEL` | 被测模型标识 |
| `LLM_TIMEOUT` | 可选，超时秒数，默认 60 |
| `JUDGE_API_URL` / `JUDGE_API_KEY` / `JUDGE_MODEL` | 独立裁判服务配置 |
| `JUDGE_TIMEOUT` | 可选，裁判超时秒数，默认 60 |

```bash
python examples/source/multi_vendor_infer.py --vendor provider-A --rounds 3 --output output/provider-A.jsonl
python examples/scoring_pipeline.py --input output/provider-A.jsonl --judge-api
```

以上两条命令会调用你配置的服务并可能产生费用。每条独立请求，参数为 `temperature=0`、`max_tokens=2048`；不自动重试。接口需要支持 Chat Completions 的文本响应格式和这些参数，其他接口须先适配。跨供应商比较前，将各自 JSONL 合并，确保题目和轮次一致；结果只能代表本次参考子集。

全部采集题目直接来自 `REGISTRY`，当前为 11 题，**没有声称补齐原文 60 题的全部评分量规**。默认不加入会与 JSON-only 等题目冲突的统一输出模板。真实开放式评分通过 `--judge-api` 显式启用，也可以在 Python 中向 `main(samples, judge_model=callback)` 传入裁判函数。裁判调用失败或回复无法解析时停止，不把裁判错误记为被测模型 0 分。

失败请求会保留位置与通用错误类型，采集进程以错误退出；检查配置后补测，再提供完整成功记录评分。响应正文和密钥不写入错误说明。缺失 Token 用量保留 null；缺失维度、仅单轮稳定性、不可比 Token 覆盖标为 N/A。当前子集不含完整指纹维度，因此不生成完整加权总分或总分排名。

## 概率流程

先人工确认标签映射，补齐每个 knowledge 题目的答案白名单。仓库的两条 GT **仅为格式示例，不能当作 743 题答案**。标签为 `knowledge` 或 `logic_fiction`，题号需对应原始数据。

```bash
python examples/source/probability_infer.py --labels private/label_map.json --gt private/gt_whitelist.json --output output/raw_infer_result.json
python examples/source/probability_score.py --input output/raw_infer_result.json --output-dir output/probability
```

推理命令使用 `LLM_` 环境变量并产生真实调用；评分命令只读本地结果。GT 缺失或为空会在推理前报错，不用不完整白名单自动计分。支持 token logprobs 的服务可增加 `--logprobs`；只读取服务实际返回的首 Token，没有返回时保留 null，不拿首字符或首单词代替。此适配器未实现主方案的多轮概率分布采样。

### 新评分口径

- knowledge 采用 Unicode NFKC、大小写和空白规范化后的**完整答案匹配**。`pineapple` 不匹配 `apple`，否定句不匹配其中的地名。
- 完整答案匹配是保守的自动指标。带解释、标点或其他未登记写法即使语义正确，也会进入 `bad_case.csv` 待人工复核；不得把自动 0 分直接当作语义错误。补充等价答案须保留 GT 版本。
- `logic_fiction` 均进入人工复核；拒答关键词统计仅为描述性计数，不能作为逻辑题正确率。
- 调用失败保留在总记录数及 `failed_requests` 中，不进入知识答案准确率分母；比较时同时报告失败数量，不能只比较成功请求的分数。
- 无知识样本时准确率和区间为 null；空评测或全对时正常写出 CSV 表头。
- 95% 区间使用 Wilson 方法。该区间假设独立伯努利试验；同题重复采样、配对比较或相关题目不能直接据此判显著差异。
- 匹配方式、提示词和参数已变更，需重新建立基线；不可与旧版子串打分或内部历史分数直接等同比较。

## 尚需完善

- 全部 60 题的评分量规、743 题人工标签与完整 GT。
- 原始行为评分的 SDK、复核策略和归一化。该附件仍会把 0/1/2/3 的数值评分全部列入复核。
- 数字抽取尚未绑定业务语义字段，同一数字可能被多个条件复用；需要结构化答案或人工复核。
- Token 相对用量指标不能替代质量约束、统一计数与实际账单核对。
- 真实服务兼容性、完整研究复现及供应商验收。此次只进行了离线回归，没有用真实密钥联调，没有重跑匿名化案例。

详见[已知限制](../docs/limitations.md)。
