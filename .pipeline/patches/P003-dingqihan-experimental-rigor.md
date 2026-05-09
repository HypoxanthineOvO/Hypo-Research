# P003: 丁麒涵改为实验设计与描述审稿人
- 严重级: normal
- 状态: closed
- 发现于: C2 post-release (v0.7.0)
- 创建时间: 2026-05-09T18:40:26+08:00
- 修复时间: 2026-05-09T18:44:26+08:00
- 改动: 将丁麒涵从 Reproducibility persona 调整为 Experimental Rigor persona；强调实验设计、baseline/ablation、公平性、指标定义、workload、仿真/测量设置和 claim 支撑力度；同步 hypo-review skill 文档和镜像。
- 测试: ✅ `uv run pytest tests/test_review_reviewers.py tests/test_review_roadmap.py tests/test_review_cli.py` 通过（21 passed）
- commit: see commit containing P003 closure
- 关联: review persona calibration
- resolved_by: null
- related: []
- supersedes: []

## 描述

当前丁麒涵 persona 以“复现性/代码开源/训练日志/随机种子”为核心，不适合很多硬件论文。硬件工作通常不会公开 RTL，很多工作最多开放模拟器或实验脚本，因此不能因为未公开 RTL/代码本身给低分。

需要将丁麒涵调整为关注实验设计与实验描述合理性的审稿人：

- 评估实验设计是否能支撑 claim。
- 检查 baseline、ablation、指标、workload、仿真/测量设置是否合理。
- 要求描述足够清楚，但不因硬件论文没有开源 RTL/完整代码而直接扣分。
- 对不合理的开源要求在 revision roadmap 中应归为可忽略或可解释。

## 结果

丁麒涵现在不再因为硬件论文未公开 RTL、EDA 脚本或完整代码本身给低分；他会检查实验设计与描述是否足以让读者判断结果可信。修改未使用 subagent：本 Patch 范围是 persona 文案、prompt 文案、两处测试和 skill 镜像同步，属于小范围本地修复。
