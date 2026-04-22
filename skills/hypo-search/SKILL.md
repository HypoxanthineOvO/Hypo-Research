---
name: hypo-search
description: >
  Run a fast literature lookup for a single query across the configured sources
  and summarize the top results for the agent.
license: MIT
---

# /hypo-search — 快速文献检索

快速检索单个 query，不做 query 扩展。适合已知关键词的精确查找、或对 /hypo-survey 结果的补充检索。

## 参数

$ARGUMENTS
- query: 检索词（必填）
- source: 数据源（可选，默认 all）

## 工作流

1. 直接执行：

```bash
uv run hypo-research search "<query>" \
  --output-dir data/surveys/quick_<timestamp>
```

2. 读取 `results.md`，向用户汇报：
   - 找到 X 篇论文
   - 列出 Top 5（标题 + 年份 + venue）
   - 如果有 auto-verify 问题，简要提及
