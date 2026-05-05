# M04 报告：文献调研报告、深读流程与长期路线图

## 总结建议

Hypo-Research 下一阶段应从“19 个科研 Skill 工具箱”升级为 **PhD/独立研究者的研究工作台**。核心体验不是让用户选择命令，而是围绕少数固定场景完成端到端研究动作：

- 调研方向
- 读论文
- 写论文
- 审论文
- 想 idea / 做实验计划
- 管理研究项目

技术上不建议把 Hypo-Research 合并进 Hypo-Workflow 核心；建议作为 research vertical plugin/package，复用 Hypo-Workflow 的计划、状态、报告和知识账本。

## 当前调研报告的短板

当前 `output/markdown_report.py` 和 `output/summary.py` 已有：

- 检索摘要
- verified/single-source/unverified 分组
- 综合排序、引用排序、时间线
- 高引和必读论文推荐
- abstract brief

缺少：

- 领域熟悉度判断
- 新领域 primer
- 概念/术语图谱
- 方法、数据、claim、figure 级证据
- 多篇论文的横向矩阵
- “为什么推荐这篇先读”的证据
- 不确定性和抽取质量标注

换句话说，现在报告是“候选论文列表增强版”，还不是“研究者读完能开题/写 related work 的报告”。

## 参考工具启发

- Elicit 把入口拆成 Research Report、Systematic Review、Find Papers、Paper Chat、Extract Data、Agents；这验证了“少数场景入口”比工具名列表更自然。其 Find Papers 支持自然语言问题和表格列分析，Report 直接输出带引用的研究回答：https://support.elicit.com/en/articles/1418881
- Elicit 近期强调 Scaled Systematic Reviews 和 Report Templates，说明报告格式模板化和大规模筛选/抽取是一条产品主线：https://support.elicit.com/en/articles/10639553
- Semantic Scholar API 提供 Academic Graph、Recommendations、Datasets，适合作为 Hypo-Research 的检索和推荐基础设施：https://www.semanticscholar.org/product/api
- ResearchRabbit 强调从 endless lists 转向 connections、collections、adaptive recommendations 和 interactive maps，这启发 Hypo-Research 报告应输出“阅读路径”和“关系图谱”，不只是排序列表：https://www.researchrabbit.ai/features

## 改进后的调研报告结构

```markdown
# Research Brief: <topic>

## 0. 领域熟悉度与任务设定
- 用户熟悉度：陌生 / 半熟 / 专家
- 本次目标：入门 / related work / 找 gap / 找 baseline / 找实验设计
- 检索策略：query、source、year、seed、扩展路径

## 1. 五分钟概念 Primer
- 核心问题
- 基础术语
- 典型方法族
- 常见数据/benchmark
- 领域里“好结果”通常怎么定义

## 2. 论文地图
- 经典基础
- 最新进展
- 方法代表
- 实验/benchmark 代表
- 争议或失败方向

## 3. 候选池质量
- source 覆盖
- verified/single-source
- 元数据风险
- 缺口和偏差

## 4. 阅读顺序
- 先读 3 篇建立坐标
- 再读 3 篇补方法族
- 最后读 3 篇看最新/高引/争议

## 5. 方法/数据/Claim 矩阵
| Paper | Method | Dataset/Benchmark | Key Claim | Evidence | Confidence |

## 6. 关键图表索引
| Paper | Figure/Table | What it shows | Supports which claim | Notes |

## 7. Related Work 写作素材
- 可直接转成 related work 的聚类段落
- 每类的代表论文和差异

## 8. 下一步
- 需要深读的论文
- 需要验证的 claim
- 需要补检索的 query
```

## 陌生领域引导

第一轮不要直接搜论文，应先问：

1. 你熟悉这个领域吗？
2. 你要做入门、开题、写 related work、找 gap，还是找实验 baseline？
3. 你更关心方法、应用、数据、硬件/系统、理论，还是写作素材？

如果用户说陌生：

- 先给概念 primer。
- 检索 query 自动扩展为“基础概念 + 代表方法 + survey/review + 最新论文”。
- 报告默认加入阅读顺序和术语表。

如果用户说熟悉：

- 直接进入精确检索、citation expansion、screening 和 evidence matrix。

## 深读流程与报告衔接

M03 的 L0-L4 应成为报告内部的 evidence acquisition 层：

- L0/L1 支撑候选池快速筛选。
- L2 生成 method/dataset/figure/claim cards。
- L3 生成单篇结构化笔记。
- L4 生成多篇对比矩阵。

报告不应假装所有论文都深读。每个结论应标注证据深度：

| Evidence Depth | 含义 |
|---|---|
| Abstract-only | 只读 metadata/abstract |
| Section-read | 读了 intro/conclusion 或指定章节 |
| Evidence-card | 抽取了 method/dataset/figure/claim |
| Full-note | 已生成全文结构化笔记 |
| Cross-paper | 已进入多篇对比矩阵 |

## Research OS 长期蓝图

### 近期：1 到 2 周

1. 新增 `hypo-guide`：少数固定场景入口和 intent router。
2. 改 README：首屏从 19 Skill 改成 6 场景。
3. 改调研报告模板：加入领域熟悉度、primer、阅读顺序、证据深度字段。
4. 新增 PDF fallback extractor：`pdftotext/pdfimages` 或 PyMuPDF optional。

### 中期：1 到 2 个月

1. 新增 `hypo-read`：PDF/LaTeX/arXiv ingestion、L0-L2 深读、figure/claim cards。
2. 引入 `PaperReadArtifact` schema。
3. 项目管理对接：调研结果、读论文笔记、idea、实验计划进入同一 project context。
4. 将 report artifacts 写入 Hypo-Workflow compatible reports/knowledge ledger。

### 长期：Research OS

1. Project memory：方向、论文、会议、决策、idea、实验、rebuttal 全部可追踪。
2. Evidence-first writing：related work、method comparison、claim support 自动回链到 paper evidence。
3. Advisor mode：定期复盘、提出下一步、识别风险和文献缺口。
4. Research workflow kind：作为 Hypo-Workflow 的 vertical optional workflow，不污染默认 coding workflow。

## 推荐下一轮实现 Cycle

建议下一轮不要一口气做 PDF 大系统，先做最小可用纵切：

1. M1：新增 `hypo-guide` 场景入口和 routing schema。
2. M2：README 与 Skill IA 重排，保留旧 Skill 兼容。
3. M3：调研报告 v2 模板，加入 familiar-field question、primer、evidence depth、method/dataset/claim matrix 空槽。
4. M4：PDF fallback ingestion 和 `PaperReadArtifact` v0。
5. M5：`hypo-read` L0-L2 原型，支持方法、数据、关键图表、claim 支撑四类问题。

## 最终判断

Hypo-Research 的方向是对的，但现在太像“作者知道所有工具名的工具箱”。下一步最有价值的不是多加一个检索 API，而是重构入口和证据模型：让用户从自然研究场景进入，让系统按证据深度逐步读论文，并把每次调研沉淀到项目记忆中。
