---
name: hypo-challenge
description: >
  Stress-test a research idea with Socratic questioning across novelty,
  feasibility, significance, methodology, and assumptions.
license: MIT
---

# /hypo-challenge — Idea 拷打

对一个 research idea 做严格但建设性的苏格拉底式追问，帮助提前暴露审稿风险。

## 输入

$ARGUMENTS
- idea_file: JSON 或文本格式的 idea 描述
- severity: `gentle` / `standard` / `harsh`，默认 `harsh`

## 工作流

1. 读取 idea 文件。
2. 自动检索潜在撞车工作。
3. 从 5 个维度追问：
   - 新颖性
   - 可行性
   - 重要性
   - 方法论
   - 隐含假设
4. 总结 Top 3 致命风险。
5. 给出加固策略、verdict 和拷打后评分。

## CLI

```bash
uv run hypo-research challenge idea.json --severity harsh
```
