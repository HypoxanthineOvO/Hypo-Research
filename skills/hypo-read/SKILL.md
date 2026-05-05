---
name: hypo-read
description: >
  Ingest academic PDFs into structured read artifacts, render outlines, and
  extract heuristic evidence cards for methods, datasets, figures, and claims.
  Use this when the user wants to read, summarize, inspect, or deep-read a PDF.
license: MIT
---

# /hypo-read — PDF 结构化阅读

## 作用

`hypo-read` 面向论文 PDF 阅读。它把 PDF 转成稳定的 `artifact.json`，再支持提纲和 L2 evidence cards。

## CLI 用法

```bash
uv run hypo-research read ingest paper.pdf --out data/reads/paper
uv run hypo-research read ingest ./paper-folder --out data/reads/paper
uv run hypo-research read ingest paper.zip --out data/reads/paper
uv run hypo-research read outline data/reads/paper/artifact.json
uv run hypo-research read extract data/reads/paper/artifact.json --out data/reads/paper/cards
```

## 工作流

1. `read ingest`：解析 PDF 文本、页数、章节和图像占位信息，写入 `artifact.json`。
2. `read outline`：从 artifact 输出标题、页数、抽取质量和章节提纲。
3. `read extract`：抽取 methods、datasets、figures、claims 四类 evidence cards，输出 `cards.json` 和 `cards.md`。

## Agent 用法

先运行 ingest，再读取 outline 判断抽取质量。深读时使用 `read extract` 的 cards，把回答绑定到方法、数据、图表和 claim 证据，不要只做泛泛摘要。

`read ingest` 的 target 可以是单个 PDF、包含唯一 PDF 的文件夹或 `.zip` / `.tar*` 压缩包。多 PDF 时要求用户指定具体文件。
