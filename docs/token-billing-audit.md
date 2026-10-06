# 云厂商大模型Token计费真实性与稳定性测试方案_论文优化版

> 这是计费审计设计稿，论文数据属于所引研究，不是本项目的测试结果。所有采购分级与告警规则需按供应商计费约定和实际样本校准。
> 统一说明见 [已知限制与整理记录](limitations.md)。

**云厂商大模型 Token 计费真实性与稳定性测试方案**

——基于《Auditing Token Padding and Token Accounting in Large Language Models》方法优化

适用对象：云厂商 / 聚合平台 / 海外大模型 API 接入渠道　|　用途：采购前验收、供应商复测、日常计费监控

理论基础：

原文参考附件：token计费论文.pdf。论文请从 [公开来源](references.md) 获取。

# 一、方案结论与核心优化

**核心变化：**不再把“Token 数量是否稳定”直接等同于“是否掺水”。论文指出，必须区分两类完全不同的 Token 开销：

| **问题层** | **要验证什么** | **推荐证据** | **不能单独据此下结论** |
|-|-|-|-|
| 模型内容冗余（Token Padding） | 模型是否生成了超出任务要求的内容 | 输出文本 + 约束遵循 + 语义相似度 + 标准答案 | 仅看 provider output_tokens |
| 供应商计费口径 | 供应商报告的 token 是否与实际可见输出/输入相符 | 原始 usage payload + 本地统一 tokenizer 重计数 | 仅跨厂商比较 raw token |
| 计费稳定性 | 相同条件下计费是否异常波动 | 重复试验、固定 seed/参数、分层统计 | 仅做10次简单调用 |
| 计费线性 | 输入/输出规模变化时计费是否合理随规模变化 | 多档输入、回归斜率、残差 | 只比较2倍输入是否正好2倍 |


**论文的重要启示：***同一可见文本，在不同供应商的 provider tokenizer / accounting 口径下可能产生显著不同的 billed token；论文实证中，字符完全相同的“Tokyo”在不同提供方的计数就不同。因此，跨云厂商审计必须同时记录“供应商原始 Token”和“统一 Tokenizer 重计数”两套数据。*

# 二、测试目标

- 验证 Input Token、Output Token、Total Token 及缓存相关 Token 的计费口径是否与供应商公开规则一致。
- 验证固定请求下的计费稳定性，识别重复计费、异常增量、不可解释波动。
- 验证输入规模扩大后 Token 是否呈合理的单调、近似线性增长。
- 识别“真实内容变长”和“供应商 Token accounting 偏移”的差异。
- 识别模型自身的 Token Padding：在明确要求简短回答时，是否仍产生无业务价值的解释、寒暄、格式冗余或语义漂移。
- 形成可用于采购验收和每日监控的量化指标，而不是依赖单次调用或主观判断。

# 三、测试前置条件：先锁定实验变量

| **变量** | **要求** | **备注** |
|-|-|-|
| 模型 | 记录完整 model ID / version / snapshot（如平台可提供） | 避免模型热更新造成漂移 |
| Prompt | 固定原文、字符编码、换行、空格 | 不可仅凭肉眼认为一致 |
| System Prompt | 固定且留档 | 不能一组有、一组无 |
| 采样参数 | temperature、top_p、max_tokens 等固定 | 若支持 seed，固定 seed；否则增加重复次数 |
| 工具 | 关闭 tool/function/web search，除非专门测试工具 | 避免隐藏工具 Token |
| 缓存 | 分别测试 cache hit / miss | 缓存命中不能与普通输入混在一起 |
| 重试 | 区分业务重试与供应商自动重试 | 必须记录 request ID |
| 计费单位 | 明确 token / 1K / 1M token 等 | 换算成本时统一单位 |
| 时间 | 记录 UTC 时间戳 | 便于定位供应商版本或计费策略变化 |


# 四、测试方法一：固定输入重复测试（核心稳定性测试）

**目的：**验证同一个请求在相同实验条件下，provider usage 是否稳定；同时判断波动来自模型生成差异还是计费口径差异。

## 4.1 推荐测试题

**固定 Prompt：**请详细分析AI算力市场的发展趋势，包括：1. 当前GPU市场供需情况；2. 大模型对算力的需求变化；3. 未来3年的算力价格趋势。要求不少于500字，结构清晰。

**补充建议：**原方案的“约1000 tokens”描述不够严谨。实际 input token 应以供应商 usage 字段和统一 tokenizer 重计数为准；Prompt 本身尽量固定，不要通过“约1000 tokens”作为验收标准。

## 4.2 执行步骤

1. 固定 Prompt、System Prompt、模型版本及采样参数。
2. 连续调用 20 次；如模型存在明显随机性，建议 30 次。
3. 每次保存完整响应、provider usage payload、request ID、时间戳及错误/重试信息。
4. 记录 input_tokens、output_tokens、total_tokens；如有 cache_read/cache_creation、reasoning/thinking tokens，也必须单列。
5. 对每次可见输出使用统一 tokenizer 重计数，得到 normalized_output_tokens。
6. 分别计算 raw billing 指标与 normalized content 指标。

| **字段** | **说明** |
|-|-|
| raw_input_tokens | 供应商返回的输入 Token |
| raw_output_tokens | 供应商返回的输出 Token |
| raw_total_tokens | 供应商返回的总 Token；若接口没有该字段，按官方规则重算 |
| normalized_input_tokens | 统一 tokenizer 对输入文本的重计数 |
| normalized_output_tokens | 统一 tokenizer 对可见输出文本的重计数 |
| accounting_gap | raw_output_tokens / normalized_output_tokens（或差值） |
| cache_read / cache_write | 缓存相关计费字段，必须独立统计 |
| reasoning / thinking | 若供应商提供，独立记录，不与可见输出混为一项 |


## 4.3 稳定性判断：改进原“10%即异常”规则

**原方案问题：**只用“(最大值-最小值)/平均值”且设 >10% 为异常，容易把正常的生成随机性误判为掺水。论文也显示，供应商计数差异可能来自 tokenizer/accounting，而不是隐藏文本。

| **指标** | **公式** | **建议判定** |
|-|-|-|
| 极差波动率 | (max-min)/mean | 作为快速筛查，不作为唯一结论 |
| 变异系数 CV | 标准差/平均值 | 推荐作为重复测试稳定性主指标 |
| P95/P50 | 第95百分位/中位数 | 识别长尾异常 |
| Input Token 稳定性 | 固定输入下 CV | 通常应非常低；异常先核查包装/System Prompt/缓存 |
| Output Token 稳定性 | 固定条件下 CV | 受随机性影响，应结合 seed/temperature 判断 |
| Raw/Normalized 比值 | raw_output / normalized_output | 长期稳定但显著偏离1时，优先核查 accounting 规则 |


| **状态** | **建议规则** | **处置** |
|-|-|-|
| 绿色 | 固定输入的 Input Token 基本稳定；CV 较低；raw/normalized 差异可由官方规则解释 | 通过 |
| 黄色 | Output Token 波动明显，但与随机采样、temperature、seed 或模型行为一致 | 增加样本量复测 |
| 橙色 | Input Token 出现不可解释波动，或 raw/normalized gap 突然变化 | 核查网关包装、System Prompt、缓存和版本变化 |
| 红色 | 存在重复计费、不可解释的额外 Token，或计费随请求次数异常累加 | 暂停验收/要求供应商解释 |


# 五、测试方法二：线性增长测试（核心计费规律）

**关键优化：**不要只设置“短/中/长”三档，更不要要求 output token 与 input token 严格同比。输入 Token 与输出 Token 属于两个不同过程，应分别拟合。

## 5.1 测试设计

| **档位** | **输入设计** | **任务** |
|-|-|-|
| S | 约100 / 200 input tokens | 请用100字左右介绍AI行业。 |
| M | 约500 input tokens | 请介绍AI行业的发展趋势，并包含市场规模、技术演进和商业化分析。 |
| L | 约1000 input tokens | 请详细分析AI行业发展趋势，包括技术、市场、算力、商业模式等。 |
| XL（推荐） | 约2000 input tokens | 在L档基础上扩展背景资料，但保持任务和输出要求一致。 |


**注意：**若目标是审计“输入计费”，输出长度必须尽量控制一致；若目标是审计“总成本随任务规模变化”，再允许输出随输入规模变化。两种测试不要混为一个指标。

## 5.2 判断方法

- Input Billing Test：以 input_tokens 为因变量、实际输入字符数/统一 tokenizer tokens 为自变量，拟合 input_tokens = a + b×normalized_input_tokens。
- Output Billing Test：固定输出约束，比较 raw_output_tokens 与 normalized_output_tokens 的关系。
- Total Cost Test：计算 total billed tokens 或实际费用，并对任务规模进行回归。
- 重点观察斜率、截距和残差，而不是要求每一级恰好按 1:2:3 增长。
- 若输入扩大2倍而计费增长明显超过2.5倍，应进入异常复核，但不能直接判定“掺水”，需检查 System Prompt、缓存、工具调用和供应商计费规则。

| **异常模式** | **可能原因** | **复核动作** |
|-|-|-|
| 输入翻倍，input token >2.5倍 | 隐藏包装、重复拼接、System Prompt重复注入 | 抓完整 request payload；核对网关日志 |
| 输入不变，input token 周期性跳变 | 缓存/会话状态/版本变化 | 分别测试无缓存、cache hit、cache miss |
| 输出文本相近，raw output token 大幅跳变 | provider tokenizer/accounting 差异 | 统一 tokenizer 重计数 + 查 usage payload |
| 总费用突然增加但文本无变化 | 计费规则/套餐/缓存状态变化 | 核对账单明细与官方价格规则 |


# 六、测试方法三：空白/极短输入测试——基础计费基线

**测试题：**你好

- 目的不是证明 Token 必须接近0，而是建立“最小业务请求”的基线。
- 短输出尤其容易放大 provider accounting offset；因此该测试必须同时保留 raw 与 normalized 两套结果。
- 若短输出的 raw token 显著高于 normalized token，应先认定为“计费口径差异待解释”，而不是直接认定“掺水”。

# 七、测试方法四：重复内容测试——识别异常非线性

**测试题：**请重复以下内容：AI AI AI AI AI……（固定重复50次）

- 建议制作 10 / 20 / 50 / 100 次四档，而不是只做50次。
- 用统一 tokenizer 先计算理论输入 token 曲线，再与 provider input_tokens 对比。
- 如果输入文本自身呈线性增长，而 provider token 呈明显阶跃或超线性增长，应检查分词规则、请求包装和计费最小单位。
- 若只是 raw token 与 normalized token 存在稳定倍数差异，应归入“accounting gap”，不要直接归入“掺水”。

# 八、论文方法引入：Token Padding / TPI 增强测试

**这是本方案最重要的新增模块。**论文不是单纯测 Token 是否稳定，而是用“最小参考答案”衡量模型是否产生不必要的 Token Padding，并把“模型真实冗余”和“供应商 Token accounting”分开。论文使用106道带明确负向约束的 trap prompts，并对每个响应同时进行 provider tokenizer 和 shared tokenizer 计数。

| **测试类别** | **建议数量** | **示例** | **机器检查项** |
|-|-|-|-|
| 负向约束 | 8–10 | 只回答“是/否”，禁止解释 | 字数、禁用短语、答案格式 |
| 对话冗余 | 8–10 | 只回答一个人名/城市名 | 是否出现寒暄、结尾客套 |
| 结构冗余 | 8–10 | 只输出计算结果，不要步骤 | 是否复述题目、展示步骤 |
| 格式约束 | 8–10 | 只返回合法 JSON | JSON、大小写、正则 |
| 确定性事实 | 5–10 | 只回答一个确定答案 | 标准答案匹配 |


## 8.1 TPI 指标

**论文核心形式：**TPI = (Tt / Tc) × [1 + (1 − A) + (1 − S)]；其中 Tt 为目标响应 Token，Tc 为最小参考答案 Token，A 为约束遵循度，S 为与参考答案的语义相似度。对有确定答案的题目，可增加正确性 C：TPI = (Tt / Tc) × [1 + (1 − A) + (1 − S) + (1 − C)]。

- A（Adherence）：机器可检查的约束满足比例，例如最大字数、禁用词、必需词、正则格式。
- S（Similarity）：目标回答与最小参考答案的语义相似度。
- C（Correctness）：有确定答案时，用答案键直接判断，不使用 LLM-as-judge。
- 同时计算 Billing TPI（provider token）和 Content TPI / Normalized TPI（统一 tokenizer），用于区分“真正冗余”与“计费口径差异”。

**论文的直接证据：**研究发现，原始 provider token 下部分模型的 TPI 很高，但统一 tokenizer 重算后显著收敛；论文因此明确提出“what you pay”和“what the model generated”应分别报告。

# 九、异常识别规则（优化版）

| **规则** | **触发条件** | **风险等级** | **结论措辞建议** |
|-|-|-|-|
| R1 Token Padding | 短答案/强约束任务中，Normalized TPI 持续显著高于1，且存在多余解释、寒暄、格式违规 | 高 | 模型存在内容冗余风险 |
| R2 Accounting Gap | raw token / normalized token 长期显著偏离1，且可在usage字段中定位 | 中 | 供应商存在Token accounting差异，需核对计费规则 |
| R3 Input不稳定 | 完全相同请求的input token存在不可解释变化 | 高 | 存在请求包装/缓存/计费稳定性风险 |
| R4 非线性 | 输入规模增加后，provider token 的回归残差持续偏大，或局部增长显著超出预期 | 中-高 | 存在非线性计费风险，需复核 |
| R5 重复计费 | 同一请求/同一 request ID 或同一业务重试被重复计入费用 | 严重 | 计费链路存在重复计费风险 |
| R6 长尾异常 | P95/P50 显著高于中位水平，且无法由随机性解释 | 中 | 存在异常长尾，应扩大样本复测 |


# 十、推荐评分体系（用于云厂商验收）

| **维度** | **权重** | **核心指标** | **满分条件** |
|-|-|-|-|
| 计费口径一致性 | 30% | raw vs official rule / normalized token | usage字段可解释、账单可对账 |
| 计费稳定性 | 20% | Input CV、Output CV、P95/P50 | 固定条件下无不可解释波动 |
| 线性与可预测性 | 20% | R²、斜率、残差 | 输入规模变化与计费基本可预测 |
| Token Padding | 20% | Normalized TPI、A、S、C | 强约束下少冗余、少违规 |
| 异常与对账能力 | 10% | request ID、账单、usage payload | 可逐请求追溯 |


| **总分** | **等级** | **建议** |
|-|-|-|
| 90–100 | A：通过 | 可进入采购/正式接入；纳入日常监控 |
| 80–89 | B：有条件通过 | 补充异常项说明后接入 |
| 70–79 | C：整改后复测 | 要求供应商解释并重新测试 |
| <70 | D：不建议通过 | 暂停采购或更换渠道 |


# 十一、最终测试数据表（建议直接作为 Excel 字段）

| **字段组** | **字段** |
|-|-|
| 请求标识 | test_id / request_id / timestamp / provider / model_id / model_version |
| 请求参数 | prompt_hash / system_prompt_hash / temperature / top_p / seed / max_tokens |
| 供应商计费 | input_tokens / output_tokens / total_tokens / cache_read / cache_write / reasoning_tokens |
| 统一计数 | normalized_input_tokens / normalized_output_tokens / normalized_total_tokens |
| 差异指标 | accounting_gap / billing_ratio / normalized_ratio |
| 稳定性 | mean / median / std / CV / min / max / P95 / P95-P50 |
| 线性测试 | input_size / billed_tokens / normalized_tokens / fitted_slope / R² / residual |
| 行为指纹 | TPI / normalized_TPI / adherence_A / similarity_S / correctness_C |
| 结果 | 异常规则 / 风险等级 / 是否通过 / 供应商解释 / 复测结论 |


# 十二、标准执行流程

**固定环境 → 固定请求 → 重复调用 → 保存原始 usage → 统一 tokenizer 重算 → 稳定性分析 → 线性回归 → TPI 行为测试 → 异常归因 → 账单对账 → 验收**

# 十三、与原方案相比的关键修改点

| **原方案** | **优化后** |
|-|-|
| 固定输入调用10次 | 建议20次；高随机模型30次，并记录seed/temperature |
| 用(max-min)/平均值判断稳定性 | 保留极差波动率，同时增加CV、P95/P50 |
| 波动>10%直接判异常 | 不再直接判定；先区分随机生成、缓存、版本、accounting |
| 短/中/长三档，要求同比增长 | 至少S/M/L/XL，多点回归，分别分析input/output/total |
| “Token高”≈“掺Token” | 拆成Content Padding与Token Accounting两类风险 |
| 只记录provider token | 同时记录provider raw token + shared tokenizer normalized token |
| 只测长文本 | 加入负向约束、短答案、格式、确定性事实等trap tests |
| 只看Token数量 | 加入A（约束）、S（相似度）、C（正确性） |
| 异常规则较粗 | 建立R1–R6异常规则和采购评分体系 |


# 十四、实施建议

- 采购验收阶段：执行完整测试集，不少于20次重复 + 4档线性测试 + 40道左右TPI trap题。
- 供应商对比阶段：所有厂商使用相同 Prompt、相同任务、相同测试环境；跨厂商排名优先参考 normalized 指标，同时保留 raw billing 指标用于实际成本决策。
- 日常监控阶段：每日记录 avg/median/P95 token、CV、normalized ratio、accounting gap、单任务成本及异常率。
- 发生异常时：先拿 request ID + 原始 usage payload + 实际输出文本做三方对账，再判断是模型行为、tokenizer、网关包装、缓存还是账单问题。
- 不要使用“>10%必然掺水”“输入翻倍必须总Token翻倍”等绝对规则作为最终验收依据；这些只能作为筛查阈值。

# 十五、论文依据与局限

**依据：**本方案直接吸收论文关于 Token Padding Index、负向约束 trap battery、provider token 与 shared-tokenizer normalization 双重计数、机器可检查的 constraint adherence、语义相似度及确定性 correctness 的方法。论文在7个模型、3家提供商、106道 trap、6970次试验中展示了 provider billing 与实际生成内容可能存在显著分离。

**局限：**论文实验主要是英文、短答案任务，作者明确指出长文本、多语言和更多模型族的泛化仍需验证；因此本方案将论文方法作为“计费审计框架”，而不是把论文中的具体模型比例直接当成所有云厂商的阈值。


**—— 文档结束 ——**
