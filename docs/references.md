# 资料清单与研究来源

## 本次收录

作者授权公开的主方案和四份配套文档均已转换为 Markdown。原始飞书元数据、私有文档 token 和访问链接没有打包。

| 来源 | 已收录材料 |
| --- | --- |
| 主方案 | 全部方案章节；流程图片转换为文字；移除未完成讨论片段 |
| 多厂商对比 | 60 道题、方法规范、原始采集附件、正文评分代码 |
| 行为指纹 | 方案正文、采样和评分脚本；脚本中含 21 条探针和 Rubric 摘要 |
| 概率指纹 | 方案正文、743 条提示词、标签预筛、GT 示例、推理和打分模板 |
| Token 计费 | 专项测试设计、记录字段、评分建议及异常处置规则 |

未重新分发：原文中的研究论文 PDF、两个独立的行为论文附录文档，以及多厂商文档中 3 个内嵌电子表格。探针和评分摘要可从已收录的行为脚本查看，完整研究资料请使用下方上游来源。内嵌表格未导出；本仓库的报告和 CSV 是依据正文新增的空白模板，不是原表格副本。

代码后续维护说明：多厂商与概率脚本已在原附件基础上修复并新增公共 API 客户端；原始版本保留在 Git 历史，当前状态见[代码说明](../examples/README.md)。

## 公开研究链接

- **Behavioral Fingerprinting of Large Language Models**： [论文](https://arxiv.org/abs/2509.04504) · [作者项目](https://github.com/JarvisPei/Behavioral-Fingerprinting)。用于理解行为画像、诊断探针及评分流程；本项目的采购适配稿不构成对论文实验的完整复现。
- **LLMmap**：[作者项目](https://github.com/pasquini-dario/LLMmap)。主方案引用的模型识别研究；本仓库尚未集成其执行环境或提供新的识别实验结果。
- **ACL-LLMPrint / Fingerprinting LLMs via Prompt Injection**：[作者项目](https://github.com/hifi-hyp/ACL-LLMPrint)。原主方案引用此研究；本仓库的 743 题准确率流程和 50 题重复采样设计不能直接视为该研究的实现。
- **Auditing Token Padding and Token Accounting in Large Language Models: A Constraint-Adherence Metric and a Multi-Provider Empirical Study**： [作者论文页面](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7050418)。Token 计费专项方案的研究参考；文中实验数量与研究结论不代表本仓库实测结果。

第三方内容版权见 [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md)。
