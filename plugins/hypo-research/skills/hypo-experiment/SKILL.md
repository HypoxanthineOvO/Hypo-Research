---
name: hypo-experiment
description: >
  Design experiments for a research idea, including baselines, datasets,
  metrics, ablation studies, experiment matrix, and venue requirements.
license: MIT
---

# /hypo-experiment — 实验设计

为 research idea 生成完整实验方案，重点回答“如何证明这个 idea 成立”。

## 输入

$ARGUMENTS
- idea_file: JSON 或文本格式的 idea 描述
- venue: 可选目标会议或期刊
- constraints: 可选资源约束

## 工作流

1. 检索同领域实验设置作为参考。
2. 提炼 idea 中需要验证的 claim。
3. 选择 baseline：简单 baseline、经典 baseline、最新 SOTA。
4. 选择至少两个数据集。
5. 设计主指标、辅助指标和效率指标。
6. 设计核心组件 ablation。
7. 输出完整实验矩阵和预期趋势。

## CLI

```bash
uv run hypo-research experiment idea.json --venue ICLR
```
