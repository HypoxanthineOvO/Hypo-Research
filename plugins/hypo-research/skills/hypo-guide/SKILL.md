---
name: hypo-guide
description: >
  Route a natural-language research request to the right Hypo-Research workflow.
  Use this when the user is unsure whether they need check, review, read, search,
  ideation, project management, or another expert skill. Can execute conservative
  safe paths with explicit inputs.
license: MIT
---

# /hypo-guide — 自然语言入口

## 作用

`hypo-guide` 是 first-use 入口。它不替代直接命令，而是把自然语言请求路由到稳定的大类：

- `check`：论文快投、submission readiness、LaTeX/BibTeX 质量检查。
- `read`：PDF ingest、outline、方法/数据/图表/claim evidence cards。
- `review`：多角色模拟审稿、AC meta-review、revision roadmap。
- `search` / `survey`：文献检索和 related work 调研。
- 其他 expert skills：idea、pilot、project、meeting、rebuttal 等。

## CLI 用法

只路由并给建议：

```bash
uv run hypo-research guide "我论文快投了，帮我检查一下"
```

安全执行：

```bash
uv run hypo-research guide "我论文快投了，帮我检查一下" \
  --execute --target paper.tex

uv run hypo-research guide "读一下这篇 PDF 的方法" \
  --execute --target paper.pdf --out data/reads/paper

uv run hypo-research guide "search transformer architecture literature" \
  --execute --query "transformer architecture"
```

## Execute 边界

`--execute` 只执行保守路径：

- `check`：需要 `--target <paper.tex>`，运行 full check。
- `read`：需要 `--target <paper.pdf>`，运行 `read ingest` 和 `read outline`。
- `review`：需要 `--target <paper>` 和 `--venue <venue>`；缺参数时只建议命令。
- `search`：需要显式 `--query`，避免把整句自然语言误当检索词。

不要用 guide 隐式执行 destructive 操作。直接子命令始终是一等入口。

## Target 支持

`--target` 可以是单个文件、文件夹或压缩包：

- check/review 路线：`.tex`、LaTeX 项目文件夹、`.pdf`、`.zip`、`.tar*`。
- read 路线：`.pdf`、包含唯一 PDF 的文件夹、`.zip`、`.tar*`。

如果目录或压缩包中存在多个候选，guide 会停止并要求指定确切文件。
