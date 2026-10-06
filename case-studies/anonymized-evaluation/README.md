# 匿名化实测案例

本目录收录方案作者提供的历史测试结果。覆盖 28 个工作表、6 个匿名测试对象，包含验收总览、逐题调用指标、异常记录、最终复核和 LLMmap 结果。**这是既有结果的匿名化发布，本次整理没有重新调用模型或重跑测试。**

## 结果摘要

下表转述原表；以最终复核的适用边界为准，不把“请求成功”“评分通过”和“完整验收通过”混为同一指标。

| 测试对象 | 行为评分（原表） | 主测试覆盖 | 需要保留的结论边界 |
| --- | --- | --- | --- |
| 对象A | 39/39 | 21 + 743 + 29 | 最终复核为条件通过；历史 6 条输入 Token 异常仍保留，现场复测未复现 |
| 对象B | 38/39 | 21 + 743 + 29 | 条件通过；概率记录 741/743、计费记录 7/29 的 usage 完整；截断路径存在计量缺口 |
| 对象C | 37/39 | 21 + 743 + 29 | 最终复核为条件通过；工具编排能力未验收 |
| 对象D | 39/39 | 21 + 743 + 29 | 最终复核为条件通过；工具编排能力未验收 |
| 对象E | 38/39 | 21 + 743 + 29 | 供应商 API 直连基线通过；测试平台端到端验证待配置 |
| 对象F | 38/39 | 21 + 743 + 29 | 供应商 API 直连；793 条正式记录齐全；不能等同于平台端到端验收 |

六组各 793 条正式主记录，共 4,758 条，另有异常/补测、工具及身份探测记录。这个数量是覆盖统计，不代表全部题目答对或全部验收项通过；异常页也不等于独立失败请求数。

## 阅读顺序

1. 阅读各对象总览，以及 [最终复核](tables/sheet-22.csv)。
2. 对照行为、概率与计费用量的逐行数据，关注 usage 缺失、截断与历史异常。
3. 查看 [LLMmap 身份指纹](tables/sheet-23.csv) 和 [调用指标](tables/sheet-24.csv)。最近邻模板与距离只能作为特定参考库下的观测，不能独立认证底层模型身份。

## 匿名化方式

- 组织、公司、平台、渠道与内部模型代号统一替换为通用代号；同类标识在本目录内保持一致。
- 原始请求/会话标识、接口地址、精确时间、内部路径、分支和环境引用做隐藏处理。
- 原始题目、完整应答、推理内容、工具参数/返回、错误原文和执行过程等自由文本字段以占位符保留位置，避免内部信息随长文本公开；保留题目 ID、状态、评分、用量、时延及复核结论。可在主仓库题库中查阅公开题目。
- 不发布原名对照表、私有表格链接和元数据。空值保持为空；`[原始文本已隐藏]` / `[标识已隐藏]` 等代表发布时遮盖，不代表源数据缺失。
- 保留原表指标值与历史判断，不修补缺失 usage，不把异常值改成正常值。CSV 第一列是原工作表行号，用于关联匿名化表内说明。

## 数据格式与限制

CSV 是 UTF-8 BOM 编码的单元格值快照，每行第一项为 `source_row`，其余依次对应原表各列；由于部分工作表采用多段标题布局，不另行插入统一表头。格式、合并、批注及公式表达式未打包。来源中的科学计数法和日期序列文本按导出值保留；这些内容不应误读为重新计算或精度补全。

本公开版保留量化结果与复核记录，但隐藏了原始应答和身份信息，因此无法仅凭本目录独立重判全部主观分数。原表中“通过”“官方”“实测”等词语属于作者历史记录，不构成本次整理的独立认证。

原表最终复核指出：743 题单次采样尚不满足主方案的多轮概率指纹设计；工具测试覆盖不一致；识别参考库也有适用范围限制。具体事实以各表与最终复核的口径共同解释，避免直接据此排列通用模型能力榜单。

## 工作表目录

| 文件 | 内容 | 原表有效行数（含表头/说明） |
| --- | --- | --- |
| [tables/sheet-01.csv](tables/sheet-01.csv) | 对象A总览 | 35 |
| [tables/sheet-02.csv](tables/sheet-02.csv) | 对象A行为指纹 | 22 |
| [tables/sheet-03.csv](tables/sheet-03.csv) | 对象A概率指纹 | 744 |
| [tables/sheet-04.csv](tables/sheet-04.csv) | 对象A计费用量 | 30 |
| [tables/sheet-05.csv](tables/sheet-05.csv) | 对象A异常记录 | 250 |
| [tables/sheet-06.csv](tables/sheet-06.csv) | 对象A验收交付 | 37 |
| [tables/sheet-07.csv](tables/sheet-07.csv) | 对象B验收交付 | 66 |
| [tables/sheet-08.csv](tables/sheet-08.csv) | 对象B行为指纹 | 22 |
| [tables/sheet-09.csv](tables/sheet-09.csv) | 对象B概率指纹 | 744 |
| [tables/sheet-10.csv](tables/sheet-10.csv) | 对象B计费用量 | 30 |
| [tables/sheet-11.csv](tables/sheet-11.csv) | 对象B工具调用 | 35 |
| [tables/sheet-12.csv](tables/sheet-12.csv) | 对象B异常记录 | 133 |
| [tables/sheet-13.csv](tables/sheet-13.csv) | 对象C及D验收总览 | 39 |
| [tables/sheet-14.csv](tables/sheet-14.csv) | 对象C及D行为指纹 | 43 |
| [tables/sheet-15.csv](tables/sheet-15.csv) | 对象C及D概率指纹 | 1487 |
| [tables/sheet-16.csv](tables/sheet-16.csv) | 对象C及D计费用量 | 59 |
| [tables/sheet-17.csv](tables/sheet-17.csv) | 对象E行为指纹 | 22 |
| [tables/sheet-18.csv](tables/sheet-18.csv) | 对象C及D异常记录 | 181 |
| [tables/sheet-19.csv](tables/sheet-19.csv) | 对象E概率指纹 | 744 |
| [tables/sheet-20.csv](tables/sheet-20.csv) | 对象E计费用量 | 30 |
| [tables/sheet-21.csv](tables/sheet-21.csv) | 对象E验收总览 | 35 |
| [tables/sheet-22.csv](tables/sheet-22.csv) | 最终复核 | 19 |
| [tables/sheet-23.csv](tables/sheet-23.csv) | LLMmap身份指纹 | 6 |
| [tables/sheet-24.csv](tables/sheet-24.csv) | LLMmap调用指标 | 41 |
| [tables/sheet-25.csv](tables/sheet-25.csv) | 对象F行为指纹 | 22 |
| [tables/sheet-26.csv](tables/sheet-26.csv) | 对象F概率指纹 | 744 |
| [tables/sheet-27.csv](tables/sheet-27.csv) | 对象F计费用量 | 30 |
| [tables/sheet-28.csv](tables/sheet-28.csv) | 对象F总览 | 18 |

文件校验值见 [manifest.json](manifest.json)。
