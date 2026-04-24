---
name: hypo-translate
description: >
  Maintain bilingual Chinese-English LaTeX drafts. Use this whenever the user
  wants to keep Chinese comment summaries aligned with English paper text,
  generate missing English from Chinese comments, generate missing Chinese
  summaries from English paragraphs, or audit bilingual sync in a paper draft.
  Run the stats extractor first to get paragraph pairs and orphan paragraphs,
  then let the Agent produce the actual translation or sync judgment.
license: MIT
---

# /hypo-translate — 中英双语翻译维护

本 Skill 面向这种格式：

```latex
% 我们提出了一种基于 NTT 流水线优化的 FHE 加速框架。
We propose an FHE acceleration framework based on optimized NTT pipelines.
```

## Parameters

$ARGUMENTS
- `path`: LaTeX 文件或项目目录，必填
- `project_dir`: 显式项目根目录，可选；多文件项目推荐
- `mode`: `sync` / `cn2en` / `en2cn`，可选，默认 `sync`
- `apply`: 是否直接写回 `.tex`，可选，默认只输出建议
- `target`: 可选，限定 section 标题或行号范围

## Format Convention

- 中文使用 `% ...` 注释行，紧贴其后的英文段落为对应正文
- 连续中文注释行视为同一条中文说明
- 中英文不要求逐字对应，但核心技术含义必须一致
- 中文注释应更偏“摘要式说明”，英文正文应保持论文级表达

## Workflow

1. 先提取双语配对数据：

```bash
uv run hypo-research lint --stats <path>
```

对于多文件 LaTeX 项目，`<path>` 可以直接传 `main.tex` 或任一 `sections/*.tex` 子文件；必要时补 `--project-dir ./paper`。

2. 在 `mode=sync` 下：
   - 读取 `paragraph_pairs`
   - 检查中英语义是否对齐
   - 读取 `orphan_paragraphs`
   - 报告 `missing_chinese` / `missing_english`

3. 在 `mode=cn2en` 下：
   - 读取 `orphan_paragraphs(type="missing_english")`
   - 为每条中文说明生成论文风格英文正文

4. 在 `mode=en2cn` 下：
   - 读取 `orphan_paragraphs(type="missing_chinese")`
   - 为每段英文生成简洁中文注释

5. 如果 `apply=true`：
   - 仅在用户明确要求时直接写回 `.tex`
   - 保持 section / label / cite / math 不变

## Translation Guidelines

- 术语保持一致，优先沿用文中已存在的英文术语
- 缩写通常保留，如 `FHE`, `NTT`, `LLM`
- 专有名词不要过度翻译
- `cn2en` 不是直译，目标是学术论文质量的英文
- `en2cn` 不是逐句翻译，目标是简洁中文概述
- 如果中英文明显不一致，先指出差异，再给修正版

## Examples

**Example 1: sync**

Input:

```text
/hypo-translate path="paper.tex" mode=sync
```

Output:

```markdown
- Lines 42-45: Chinese comment says the paragraph is about NTT optimization, but the English paragraph focuses on cache hierarchy.
- Missing Chinese summary above lines 77-79.
```

**Example 2: cn2en**

Input:

```text
/hypo-translate path="paper.tex" mode=cn2en
```

Output:

```latex
The proposed design reduces key-switching latency by overlapping memory access with modular arithmetic.
```

**Example 3: en2cn**

Input:

```text
/hypo-translate path="paper.tex" mode=en2cn
```

Output:

```latex
% 我们通过重叠访存与模运算来降低 key-switching 延迟。
```
