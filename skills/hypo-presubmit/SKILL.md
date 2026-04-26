---
name: hypo-presubmit
description: >
  Run a unified pre-submission check pipeline for LaTeX papers, combining
  structure/format checks, LaTeX lint, and bibliography verification into one
  PASS/WARNING/FAIL report. Use when the user is preparing a paper submission,
  wants CI-friendly preflight checks, or asks for a complete submission-readiness
  report.
license: MIT
---

# /hypo-presubmit — 论文提交前检查

## 功能

在用户准备提交论文时，运行全面的提交前检查 pipeline，包括：

1. **结构/格式检查** (`check`)：LaTeX 结构问题、图表引用、重复标签、venue-aware severity 等。
2. **语法检查** (`lint`)：LaTeX 语法和风格问题。
3. **引用验证** (`verify`)：检查参考文献的完整性和正确性。

## 使用方法

用户给出论文主 `.tex` 文件路径后，运行：

```bash
uv run hypo-research presubmit <main.tex> [--venue <venue>] [--bib <refs.bib>]
```

常用选项：

```bash
uv run hypo-research presubmit paper.tex --venue ieee_journal
uv run hypo-research presubmit paper.tex --skip lint --skip verify
uv run hypo-research presubmit paper.tex --bib refs.bib --json
uv run hypo-research presubmit paper.tex --output presubmit-report.md
```

## 结果解读

- **✅ PASS**：可以提交。
- **⚠️ WARNING**：建议修复，但不是致命问题。
- **❌ FAIL**：有严重问题，强烈建议修复。

返回码适合 CI 集成：

- `0`：PASS
- `1`：FAIL
- `2`：WARNING

## 工作流程

1. 运行 `uv run hypo-research presubmit <main.tex>`。
2. 展示汇总报告给用户，先说明总体判定，再列出 error 和 warning。
3. 如果有 FAIL 或 WARNING：
   - 按严重程度列出问题。
   - 对每个问题给出修复建议。
   - 如果用户同意，可以手动修复，或调用 `hypo-polish` / `hypo-lint` / `hypo-verify` 做后续处理。
4. 修复后重新运行 presubmit 确认。

## 注意事项

- 如果用户指定目标会议或期刊，传入 `--venue` 参数以启用 venue-specific 规则。
- 如果用户指定 `.bib` 文件，传入 `--bib`；否则工具会从 LaTeX 项目解析引用文件。
- `warning` 不代表一定要修，需要结合论文上下文判断。
- 不要绕过 `uv`；本项目统一使用 `uv run hypo-research ...`。
