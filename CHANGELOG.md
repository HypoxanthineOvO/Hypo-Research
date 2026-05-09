# Changelog

## v0.7.2 - 2026-05-09

### 修复

- 调整 `hypo-review` 中丁麒涵审稿人角色：从强调代码/RTL 开源的复现性审查，改为关注实验设计与实验描述是否合理。
- 硬件、体系结构和 EDA 论文不再因为未公开 RTL、版图、EDA 脚本或完整仿真环境本身被该角色扣低分。
- 修改路线图中的问题类别同步从 `Reproducibility` 更新为 `Experimental Rigor`，更适合硬件论文审稿语境。

### 文档与同步

- 同步 `hypo-review` Skill 文档及 Codex/Claude 镜像中的中文说明。
- 刷新 OpenCode 适配器和 Hypo-Workflow 派生视图，移除旧 dashboard 映射，并加入 PR / explain 命令映射。

### 测试

- Full regression: `492 passed, 4 skipped, 2 warnings`。

## v0.7.1 - 2026-05-05

### Fixes

- Fixed plugin manifest: `author` field changed from string to object `{name}` format, resolving installation failure on Claude Code plugin validation.

### Tests

- Full regression: `492 passed, 3 skipped, 2 warnings`.

## v0.7.0 - 2026-05-05

### Features

- Added `guide` as a first-line natural-language router with conservative `--execute` support.
- Added PDF reading workflows: `read ingest`, `read outline`, and `read extract` evidence cards.
- Added `check --full` with Agent-facing submission-readiness review checklist.
- Added Research Brief V2 sections to literature Markdown reports.
- Added paper target resolution for files, folders, and `.zip` / `.tar*` archives.
- Added `hypo-guide` and `hypo-read` skills and updated skill IA around guide/check/review/read.

### Fixes

- Clarified `presubmit` as a compatibility/legacy wrapper while keeping direct `check --full` as the primary paper check.
- Repaired stale workflow lock and accepted Cycle C2 state before release.

### Tests

- Full regression: `492 passed, 3 skipped, 2 warnings`.
