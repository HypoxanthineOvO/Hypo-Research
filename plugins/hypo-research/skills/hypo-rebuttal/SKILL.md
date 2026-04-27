---
name: hypo-rebuttal
description: >
  Generate academic rebuttal responses by parsing reviewer comments,
  classifying concerns, choosing response strategies, and drafting a rebuttal letter.
license: MIT
---

# /hypo-rebuttal — Rebuttal 生成

帮助作者从审稿意见生成结构化 rebuttal，保持礼貌、专业、简洁，并逐条回应。

## 输入

$ARGUMENTS
- reviews_file: 审稿意见文本文件
- paper_draft: 可选论文草稿
- experiment_results: 可选补充实验结果
- project/paper: 可选项目上下文

## 工作流

1. 解析 Reviewer 1 / Reviewer 2 等审稿意见。
2. 逐条拆分 comment。
3. 分类 comment：
   - factual_error
   - misunderstanding
   - valid_concern
   - suggestion
   - praise
4. 选择回复策略：
   - correct
   - clarify
   - acknowledge
   - supplement
   - thank
5. 汇总需要修改论文的位置和补充实验。
6. 生成完整 rebuttal letter。

## CLI

```bash
uv run hypo-research rebuttal reviews.txt --paper-draft draft.md
uv run hypo-research project rebuttal cryo-computing --paper approx --reviews reviews.txt
```
