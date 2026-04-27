---
name: hypo-plan
description: >
  Create a research roadmap from an idea and experiment design, including
  phases, milestones, paper outline, writing schedule, and risk mitigation.
license: MIT
---

# /hypo-plan — 科研工作规划

把 research idea 和实验方案转成可执行路线图，适合截稿倒排或组会推进。

## 输入

$ARGUMENTS
- idea_file: JSON 或文本格式的 idea 描述
- experiment_file: 可选 hypo-experiment JSON 输出
- venue: 可选目标 venue
- deadline: 可选截稿日期
- resources: 可选资源描述

## 工作流

1. 估算实验复杂度和总工作量。
2. 如有 deadline，倒推压缩排期。
3. 拆分阶段：文献补充、方法实现、实验运行、结果分析、论文写作、提交前检查。
4. 输出每阶段任务、里程碑、风险和交付物。
5. 生成 paper outline 和 writing schedule。
6. 给出风险缓解与 Plan B。

## CLI

```bash
uv run hypo-research plan idea.json --deadline 2026-09-01 --venue ICLR
```
