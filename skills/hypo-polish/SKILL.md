---
name: hypo-polish
description: >
  Polish academic English in LaTeX papers. Use this whenever the user wants to
  improve wording, clarity, concision, sentence flow, paragraph transitions, or
  section-level writing quality in a paper, rebuttal, abstract, or technical
  draft. Run the stats extractor first, let it surface long sentences and
  repetitive openings, then have the Agent perform the actual language rewrite.
license: MIT
---

# /hypo-polish — 学术英文润色

语言判断完全由 Agent 负责。脚本只负责统计章节信息和定位可疑区域。

## Parameters

$ARGUMENTS
- `path`: LaTeX 文件或项目目录，必填
- `mode`: `full` 或 `targeted`，可选，默认 `full`
- `target`: section 标题或行号范围，`mode=targeted` 时可选但强烈建议提供
- `apply`: 是否直接改文件，可选，默认只输出建议

## Workflow

1. 先运行统计提取器：

```bash
uv run hypo-research lint --stats <path>
```

2. 在 `mode=full` 下：
   - 读取 `chapter_stats`
   - 优先关注：
     - `avg_sentence_length > 25`
     - `long_sentences`
     - `paragraph_starts` 中重复过多的开头词
     - 同级章节中明显过长或过短的部分
   - 输出按章节组织的润色建议

3. 在 `mode=targeted` 下：
   - 先定位用户指定的 section 或行号范围
   - 对该范围逐句润色
   - 输出原文 vs 修改稿的完整段落 diff

4. 如果 `apply=true`：
   - 只在用户明确要求时直接改 `.tex`
   - 优先保持术语、符号、引用、LaTeX 结构不变
   - 不擅自改公式、label、cite key

## Output Format

`mode=full` 时使用：

```markdown
# Polish Report

## Section: Introduction
- Lines 34-41: sentence is too long; split into two sentences.
  Original: ...
  Suggestion: ...
  Reason: ...
```

`mode=targeted` 时使用：

```markdown
# Targeted Polish

## Original
...

## Revised
...

## Notes
- Improved transition
- Removed repetition
```

## Style Guidelines

- 优先简洁表达，少用空泛修饰词，如 `very`, `really`, `quite`, `clearly`
- 优先主动语态，除非被动语态更符合学术写作场景
- 避免连续多句以相同主语开头，尤其是重复的 `We`
- 避免 `it is` / `there are` 这类弱开头
- 术语前后一致，不随意切换同义表达
- 句子过长时优先拆句，而不是堆叠逗号和从句
- 不改变技术结论，只改善表达

## Examples

**Example 1**

Input:

```text
/hypo-polish path="paper.tex" mode=full
```

Output:

```markdown
## Section: Introduction
- Lines 18-19: repeated `We` openings weaken rhythm.
- Line 24: split the 48-word sentence into two shorter sentences.
```

**Example 2**

Input:

```text
/hypo-polish path="paper.tex" mode=targeted target="Method" apply=false
```

Output:

```markdown
## Original
We propose a design and we evaluate the design and we compare it with prior work.

## Revised
We propose the design, evaluate it thoroughly, and compare it with prior work.
```
