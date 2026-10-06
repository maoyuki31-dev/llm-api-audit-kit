# 海外大模型接入测试与质量治理

**LLM API Quality Assurance** · 毛友琦

An open framework for evaluating third-party LLM APIs through vendor comparison, behavioral fingerprints, token billing audits, and ongoing quality monitoring.

面向 AI 算力采购、第三方模型 API 接入与供应商管理，覆盖 **接入前评测 → 接入后复测 → 长期质量治理**。

## 关注什么

| 方向 | 核心问题 | 对应材料 |
| --- | --- | --- |
| 能力与模型一致性 | 不同渠道的能力差异、行为漂移、路由变化 | 60 题对比题库、行为指纹、概率指纹 |
| Token 计费 | 内容冗余、计数口径差异、重复计费与成本波动 | Token 计费专项方案 |
| 服务稳定性 | 延迟、限流、峰值表现与长期变化 | 主方案中的复测与监控机制 |

## 从这里开始

1. 阅读 [整体检测方案](docs/testing-plan.md)，确定本轮评测阶段与目标。
2. 选择 [多厂商对比题库](docs/multi-vendor-question-bank.md)、[行为指纹](docs/behavior-fingerprint.md)、[概率指纹](docs/probability-fingerprint.md) 或 [Token 计费审计](docs/token-billing-audit.md)。
3. 固定题库版本、参数、模型标识与评分规则，保留原始请求、响应和计费证据。
4. 使用 [报告模板](templates/test-report.md) 和 [计费记录字段](templates/billing-records.csv) 记录结果与人工复核。

## 仓库内容

| 路径 | 内容 |
| --- | --- |
| [docs/](docs/testing-plan.md) | 主方案、4 份专项文档、资料来源和已知限制 |
| [examples/](examples/README.md) | 6 份原始脚本附件，以及从正文提取的评分参考代码 |
| [data/probability/](data/probability/README.md) | 743 条原始提示词、2 条 GT 白名单示例 |
| [templates/](templates/test-report.md) | 空白报告及计费记录模板 |
| [LICENSES/](LICENSES/Behavioral-Fingerprinting-MIT.txt) | 行为指纹上游项目的版权与许可声明 |

## 当前状态

这是**方案、题库与参考代码的首个公开版本**，尚未形成可直接部署的完整检测系统。原始脚本按附件保留，公开整理过程没有运行它们或进行真实 API 测评。

- 多厂商文档包含 60 题；采集脚本仅包含 8 道简化题，评分示例仅登记 11 道题，默认使用占位裁判。
- 行为指纹脚本包含 21 条探针；API 配置、SDK 用法、评分和聚合仍需适配。
- 概率题库包含 743 条提示词；完整 GT、人工确认的标签和真实推理接口尚待补齐。
- 阈值属于草案建议，需要校准。指纹、能力分数和 Token 计数差异用于触发复核，不能单独作为模型身份或计费违规的证明。

执行前请阅读 [代码说明](examples/README.md) 与 [已知限制](docs/limitations.md)。原文附件收录范围见 [资料清单](docs/references.md)。

## 参与完善

欢迎通过 Issue / Pull Request 补充完整评分量规、修复参考脚本、完善基线与统计方法。变更提示词、GT、参数或评分规则时，请记录版本及对历史基线的影响。案例请使用匿名化样本，避免提交 API Key 或未授权业务数据。

## 作者与许可

方案作者：**毛友琦** · [maoyuki31-dev](https://github.com/maoyuki31-dev)

本项目原创文档、题库与代码采用 [MIT License](LICENSE)。第三方研究、探针及其衍生内容保留各自版权与许可，见 [第三方说明](THIRD_PARTY_NOTICES.md)。论文 PDF 不在本仓库重新分发。
