---
name: hypo-check
description: >
  Run the full writing-quality pipeline for a LaTeX paper project: lint,
  auto-fix preview or apply, citation verification, and aggregated reporting.
  Use this when the user wants a submission-readiness check, a one-command
  writing QA pass, or a structured report summarizing lint and bibliography
  health.
license: MIT
---

# /hypo-check — 论文一键检查

## 概述

对 LaTeX 论文项目执行完整的质量检查流水线：结构 lint → 自动修复 → 引用验证 → 聚合报告。

## 使用场景

- 论文提交前的全面检查
- CI/CD 中的论文质量 gate
- 快速了解论文项目的整体状态

## CLI 用法

### 基本检查（dry-run 预览修复）

```bash
uv run hypo-research check paper.tex
```

### 完整检查 + 自动修复

```bash
uv run hypo-research check --no-dry-run paper.tex
uv run hypo-research check --no-dry-run --backup paper.tex
```

### 只做 Lint

```bash
uv run hypo-research check --lint-only paper.tex
```

### 跳过修复，只看报告

```bash
uv run hypo-research check --no-fix paper.tex
```

### 跳过引用验证

```bash
uv run hypo-research check --no-verify paper.tex
```

### JSON 输出

```bash
uv run hypo-research check --json paper.tex
```

## Pipeline 阶段

| 阶段 | 工具 | 说明 |
|------|------|------|
| 1. Lint | `hypo-lint` | 结构检查，报告违规 |
| 2. Fix | `hypo-lint --fix` | 自动修复可修复的违规 |
| 3. Verify | `hypo-verify` | 验证 `.bib` 引用的正确性 |
| 4. Report | — | 聚合各阶段结果 |

## Agent 用法

Agent 读取 check 的 JSON 报告（`.hypo-research-report/check-*.json`），按优先级处理：

1. `Lint errors`：先修复无法自动修复的 lint error。
2. `Verify mismatch`：检查引用不匹配的条目，更正 bib 信息。
3. `Verify not_found`：搜索找不到的引用，补充完整信息。
4. `Polish`：基于 stats 中的章节统计进行润色。
5. `Translate`：检查中英对齐。
