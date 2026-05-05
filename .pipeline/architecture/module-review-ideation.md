# Review, Rebuttal, And Ideation Modules

## 职责

审稿模块模拟学术评审流程，创意模块生成、挑战、细化和计划研究 idea，rebuttal 相关能力处理审稿意见分类和回复策略。

## 主要文件

- `review/parser.py`：解析论文结构。
- `review/reviewers.py`：审稿 persona、严重度和 prompt 生成。
- `review/report.py`：单审稿、meta-review、revision roadmap 的结构化报告。
- `review/literature.py`：审稿时的相关文献上下文检索。
- `review/venues.py`：会议/期刊评审 profile。
- `ideation/strategies.py`、`ideation/scoring.py`、`ideation/models.py`：idea 生成策略、评分和结构。
- `ideation/challenge.py`、`experiment.py`、`planning.py`、`pilot.py`：challenge、实验设计、路线规划和一键串联。
- `project/rebuttal.py`：项目上下文中的 rebuttal 支持。

## 数据流

论文或研究方向经解析/规范化后进入 persona prompt 或 ideation strategy，模型输出被组织成结构化 review、roadmap、experiment plan 或 idea report。需要文献上下文时，通过 literature search 模块获取补充材料。

## 设计约束

Persona 文案可以有强风格，但结构化输出模型应保持稳定。新的 venue、reviewer 或 ideation strategy 应通过配置/注册表扩展，而不是硬编码到 CLI 分支。
