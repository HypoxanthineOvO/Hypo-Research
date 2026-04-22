# Hypo-Research 使用指南

## 在 Claude Code 中使用

### Slash Commands

| 命令 | 说明 | 示例 |
|------|------|------|
| `/survey` | 完整文献调研 | `/survey topic="cryogenic computing"` |
| `/quick-search` | 快速检索 | `/quick-search query="transformer architecture"` |
| `/review-results` | 审查已有结果 | `/review-results path="data/surveys/..."` |

### 自然语言调用

Claude Code 会自动识别文献调研意图：

- 帮我查一下低温计算方向的文献
- 搜索 transformer 架构最近的论文
- 做一个关于 RISC-V 安全的文献调研

## 在 Codex 中使用

Codex 通过 `AGENTS.md` 自动发现 Hypo-Research 能力。直接描述需求即可：

- 对 cryogenic computing 做一次文献调研，输出到 `data/surveys/cryo`
- 用 Semantic Scholar 和 arXiv 搜索 quantum error correction

## 输出说明

### results.json

结构化的论文列表，每篇包含：`title`, `authors`, `year`, `venue`, `doi`, `abstract`, `sources`, `verification`, `citation_count`, `matched_queries`

### meta.json

检索元数据：`query`, `expanded_queries`, `sources`, `statistics`, `timestamp`

### references.bib

可直接导入 LaTeX 的 BibTeX 文件。Citation key 格式：`<首作者姓><年份><标题首词>`

### results.md

人类可读报告，按验证状态分组，包含统计表和元数据质量汇总。

## 配合 LaTeX 使用

1. 调研完成后，将 `references.bib` 复制到 LaTeX 项目目录
2. 在 `.tex` 文件中 `\\bibliography{references}`
3. 使用 `\\cite{smith2023cryogenic}` 引用论文
4. citation key 可在 `references.bib` 中查找

## 常见问题

### Q: 结果太少怎么办？

- 添加更多扩展 query（`-eq`）
- 放宽年份范围（`--year-start`）
- 确认使用了所有数据源（`--source all`）

### Q: auto-verify 报了很多 warning？

- warning 是提醒，不代表论文不可信
- 重点关注 error（无作者、无效年份），这些论文需要人工核实
- single-source 且无 DOI 的论文最需谨慎

### Q: BibTeX 的 entry type 不准？

- 当前用简单规则判断，缩写型 venue 可能误判
- 可手动修正 `references.bib` 中的 entry type
