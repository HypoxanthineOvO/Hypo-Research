---
name: hypo-lint
description: >
  Check the structural quality of a LaTeX paper project. Use this whenever the
  user wants to lint, review, normalize, or auto-fix LaTeX structure issues:
  labels, refs, floats, citations, table environments, spacing, BibTeX fields,
  title case, or abbreviation expansion. Run the stats extractor first, let the
  script collect objective facts, then apply Agent judgment for abbreviation and
  title-case recommendations, and optionally patch auto-fixable issues.
license: MIT
---

# /hypo-lint — LaTeX 结构检查

脚本负责事实提取，Agent 负责判断。先运行统计提取器得到结构 JSON，再根据规则输出检查报告；如果用户要求修复，则只自动修改明确可修复项。

## 参数

$ARGUMENTS
- path: LaTeX 项目路径（必填）
- bib: `.bib` 文件路径（可选）
- rules: 只检查指定规则（可选，如 `L01,L04,L07`）
- fix: 是否自动修复可修复项（可选，布尔值）

## 工作流

1. 运行统计脚本：

```bash
uv run hypo-research lint --stats <path>
```

如果用户显式给了 `.bib` 文件：

```bash
uv run hypo-research lint --stats --bib <bib> <path>
```

2. 读取 JSON 中的 `issues` 数组，逐项报告 L01-L08、L11-L13 的客观违规项。

3. 对 Agent 判断类规则做人工判断：
   - L09：读取 `abbreviations` 中 `has_expansion=false` 的条目，结合 `context_before` / `context_after` 判断首次出现是否缺全称展开。
   - L10：读取 `sections` 标题，按 AP Style Title Case 给出修正建议。

4. 如果 `fix=true`：
   - 自动修复 L01/L02/L03/L04/L05/L06/L11/L13。
   - 修复 L06 时，同步替换全文对应 `\cref{old_label}` / `\ref{old_label}` / `\autoref{old_label}`。
   - 对 L09/L10 仅输出建议 diff，不自动应用。
   - 对 L07/L08/L12 只报告，不修复。

5. 输出最终报告：
   - 问题摘要（errors / warnings / info）
   - 每条问题的位置和修复建议
   - 如有修复，给出已应用的 patch 概要

## 规则表

| ID  | 规则 | 自动修复 |
|-----|------|----------|
| L01 | 禁用 `\ref` / `\autoref`，必须用 `\cref` | ✅ |
| L02 | `\cref` 前必须有 `~`（除非在句首） | ✅ |
| L03 | `\cite` 前必须有 `~`（除非在句首） | ✅ |
| L04 | 浮动体 `figure/table` 必须带 `[htbp]` | ✅ |
| L05 | `\label` 必须在 `\caption` 之后 | ✅ |
| L06 | label 必须有规范前缀 `fig:` / `tab:` / `sec:` / `eq:` | ✅ |
| L07 | 禁用 `tabular` / `tabularx`，优先 `tblr` | ❌ 报告 |
| L08 | 未引用的 label / 未定义的 ref | ❌ 报告 |
| L09 | 缩写首次引用必须有全称展开 | ⚠️ 建议 |
| L10 | 标题 Title Case（AP Style） | ⚠️ 建议 |
| L11 | `Fig.` / `Tab.` / `Eq.` / `et al.` 后正确间距 | ✅ |
| L12 | BibTeX 必填字段缺失 | ❌ 报告 |
| L13 | 连续多空格 / 行尾空格 | ✅ |

## 输出要求

- 默认先基于 `uv run hypo-research lint --stats ...` 的 JSON 输出结论，不要先凭感觉读全文。
- 报告 findings 时按严重性排序，优先列出 `error`。
- 如果用户要求修复，只修明确的结构问题；涉及学术判断的 L09/L10 只给建议，不擅自改写。
