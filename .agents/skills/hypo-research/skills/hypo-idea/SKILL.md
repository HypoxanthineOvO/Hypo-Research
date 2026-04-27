---
name: hypo-idea
description: >
  Generate research ideas from a direction, paper list, or survey output using
  quick-win and ambitious strategies with literature-grounded scoring.
license: MIT
---

# /hypo-idea — Research Idea 生成

从研究方向、候选文献或 hypo-survey 输出中生成 research ideas。默认同时输出 Quick Win 和 Ambitious 两组。

## 输入

$ARGUMENTS
- direction: 研究方向描述（必填）
- papers: 可选文献标题列表
- survey: 可选 `results.json`
- constraints: 可选资源、时间或方法约束
- mode: `quick_win` / `ambitious`，不填则两种都做

## 工作流

1. 理解研究方向和约束。
2. 如缺少文献上下文，调用 `hypo-search` 或内部 S2 检索补充相关工作。
3. 运行策略：
   - Quick Win：dataset_transfer、module_fusion、setting_shift、application
   - Ambitious：gap_analysis、method_transfer、problem_variant、contradiction、paradigm_challenge
   - Cross：combination
4. 对每个 idea 做 novelty、significance、feasibility、clarity 评分。
5. 输出两组候选 idea、相关论文、风险和改进建议。

## CLI

```bash
uv run hypo-research idea "<direction>" --num-ideas 5
uv run hypo-research idea "<direction>" --mode ambitious --output json
```
