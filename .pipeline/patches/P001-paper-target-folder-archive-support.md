# P001: Paper target folder/archive support
- 严重级: normal
- 状态: closed
- 发现于: C2 follow-up
- 创建时间: 2026-05-05T13:28:04+08:00
- 修复时间: 2026-05-05T13:35:00+08:00
- 改动: Added `src/hypo_research/paper_target.py`; wired folder/archive target resolution into `check`, `review`, `read ingest`, and `guide --execute`; updated README and skill docs.
- 测试: ✅ `uv run pytest` passed: 492 passed, 3 skipped, 2 warnings.
- commit: skipped (dirty worktree contains prior Cycle C2 changes)
- 关联: C2/M06 guide execute mode
- resolved_by: null
- related: []
- supersedes: []

## 描述

当前 `check` 和 `review` 对 LaTeX 文件夹已有部分支持，但 `guide --execute` / `read` 的 target 语义不完整，且压缩包没有自动解包路径。需要补一个统一 paper target resolver：

- 文件夹：自动找 LaTeX 主文件或唯一 PDF。
- 压缩包：安全解压到临时目录后走同一套 resolver。
- 多候选：给清晰错误，列出候选。
- read：目录或压缩包里唯一 PDF 时可直接 ingest。

## 结果

已支持 `.tex`、LaTeX 文件夹、`.pdf`、包含唯一 PDF 的文件夹，以及 `.zip` / `.tar*` 压缩包。压缩包解包包含路径穿越检查；多候选会输出候选并要求用户指定具体文件。
