# 概率指纹测试题库

> 743 行原始题库、标签预筛和推理/打分模板已收录。GT 白名单仅有 2 条示例，推理函数尚为空实现；当前材料不能直接产出有效的全量基线。该流程与主方案的 50 道二选一概率采样不是同一协议。
> 统一说明见 [已知限制与整理记录](limitations.md)。

### 用途：大模型迭代回归基线，同时支持【知识准确率基线】+【首Token指纹溯源比对】 

## 理论依据：

原文参考附件：指纹测试论文(1).pdf。论文请从 [公开来源](references.md) 获取。

## 数据集：

[Code_20260916.txt](../data/probability/Code_20260916.txt)

##  硬性约束： 

1. Holdout集严禁流入训练； 

 2. 修改原始prompt、标签映射、GT白名单、推理参数、打分脚本，视为版本升级，旧基线作废，全套重跑； 

 3. 主打分依靠脚本硬匹配，AI‑as‑judge仅用于bad case抽样定性分析，不作为主指标来源；  

4. 禁止人工直接修改单条样本得分；发现误判需要修改规则，重跑整套；  

5. temperature=0.0是本评测实验参数，不等同线上业务参数。 

## 整体流程总览  

1. 数据集预处理：读取原始txt → 关键词脚本预筛候选logic_fiction → 人工复核生成标签映射表

2. 为knowledge类题目构建GT标准答案白名单  

3. 使用固定推理参数批量推理全部743道prompt，保存完整输出 + 首token  

4. Python脚本自动对knowledge样本做0/1硬匹配打分  

5. 人工抽样复核（10%随机样本 + 全部0分bad case） 

6. 计算基线指标、95%二项分布置信区间，固化归档基线  

7. 后续模型迭代复用整套流程做回归对比 


###   步骤1：生成标签映射脚本 score_eval.py（分类预筛） 

**分类规则：**

• knowledge：可预先构造客观GT白名单（实体命名、客观常识、few‑shot、list客观事物、填空），参与基线准确率计算  

• logic_fiction：虚构设定 / 脑筋急转弯 / 主观Should/better辩论题，不计入准确率，仅做辅助观测，统计拒绝率 快速判断口诀：能不能预先写出一批客观正确答案白名单；能→knowledge；不能→logic_fiction ）  

[标签映射脚本.py](../examples/source/label_candidates.py)

**⚠️脚本只做候选预筛，不会直接输出最终标签，必须人工复核候选列表后再修改标签。**

#### 人工操作：

 1. 运行脚本，打印出候选条目；  

2. 打开label_map.json，把确认是虚构/脑筋急转弯/主观题的prompt_id对应的"label":"knowledge"修改为"label":"logic_fiction"；  

3. 修改完成，该json就是最终标签映射表，纳入版本管理。 禁止脚本自动直接打logic_fiction标签，必须人工确认，防止误杀知识题。 

### 步骤2：维护GT白名单文件 gt_whitelist.json 

 格式示例，只需要给knowledge的prompt_id填写合法答案数组；logic_fiction不需要填写。

[GT白名单脚本.json](../data/probability/gt_whitelist.example.json)

 规则：大小写、单复数变体尽量直接扩充进白名单，不在脚本写复杂变形逻辑，降低bug风险。 

###  步骤3：推理参数与推理脚本模板 run_infer.py 

关闭随机采样，保证可复现，同时采集首token。 

固化推理参数（全部固定，后续复测不许改动）

| 配置项 | 参数值 | 说明 |
|-|-|-|
| temperature | 0 | 关闭随机采样，指纹比对必需，输出可复现 |
| top_p | 1 | 关闭nucleus采样截断 |
| max_new_tokens | 64 | 兼顾实体、list、简短explain题目 |
| frequency_penalty | 0 | 关闭重复惩罚 |
| presence_penalty | 0 | 关闭存在惩罚 |
| stop | 无自定义停止符 |  |
| 会话策略 | 每条prompt独立新建会话，关闭缓存 |  |
| 输入prompt | 直接读取原始文件prompt，不追加、不修改系统提示词 |  |

 注意：该参数是评测实验参数，不等于线上业务参数；线上业务如需评估，单独跑一组附加实验，不使用本基线主参数。 

[推理脚本.py](../examples/source/probability_infer.py)

### 步骤4：打分脚本（接上面推理脚本末尾追加） 

仅对knowledge做0/1硬字符串匹配；logic_fiction只做统计拒绝数量，不计算准确率。 主指标完全来自脚本输出；不手工修改单条样本分数。 

[打分脚本.py](../examples/source/probability_score.py)

### 步骤5：人工复核规范

 不做全量人工打分，仅做质量校验，禁止直接修改单条样本分数 

**1. 抽样两部分：** ① 随机抽取全部样本的10%（包含score=1与score=0）  ◦② 全部bad‑case（score=0）必须全部人工复核  

**2. 复核目的：**检查脚本是否误判。  1.少量个别误判：记录台账，GT白名单下版本更新修复。本次分数保持不变。  2.发现批量系统性误判：修复GT白名单/打分脚本，数据集版本+1，整套推理、打分全部重跑，旧基线作废。 logic_fiction子集只人工浏览典型输出样例，不计算准确率。 

#### 异常处理

**要求：裁判自动打分与人工复核的一致率 ≥90%**

**• ✅ ≥90%：判定自动化打分可信，结果有效，可以用于指纹基线/漂移对比**

**• ⚠️ 80%～89%：预警，需要复盘Rubric、裁判prompt，优化后重跑评测**

**• ❌ ＜80%：判定自动化打分不可靠，本轮评测结果作废，不能用于指纹对比**

### 基线固化归档清单

1. 原始数据集：Code_20260916.txt 

2. 元数据：label_map.json（标签映射）、gt_whitelist.json（标准答案白名单）  

3. 推理脚本、打分脚本版本  

4. 推理超参配置文档（temperature=0.0等整套参数）  

5. 基准参考模型版本号  

6. 原始推理输出：raw_infer_result.json（含prompt、完整输出、first_token）  

7. 评测报表：eval_result.csv、bad_case.csv  

8. 基线指标：Acc\_{baseline}、95%置信区间 基线一旦固化，在数据集版本、推理参数、打分脚本均不变的前提下，不允许手动修改基线数值。 

### 后续每一轮模型迭代回归流程  （0-3个月/一年周期性复测）

1. 使用完全相同推理参数跑完整743道，输出raw_infer_result.json  

2. 执行打分脚本，得到Acc\_{new} 

3. \Delta = Acc\_{new} - Acc\_{baseline} 

4. 对照95%置信区间，判断性能变化是否统计显著；如果抽样复核bad case；观测logic_fiction拒绝率变化。  

5. 保存本轮全部输出。  

### 评测输出报表固定字段  

1. Total all samples：743  

2. Knowledge subset total：N\_{knowledge} 

3. Knowledge Correct：Correct\_{knowledge} 

4. Knowledge Accuracy【主基线指标】：% 

 5. Baseline_acc：%  

6. Delta：%  

7. 95% Confidence Interval：[lower, upper]  

8. Logic‑fiction subset count：（辅助，不计入主指标）
