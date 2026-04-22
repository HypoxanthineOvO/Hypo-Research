# Hypo-Research

文献调研 Skill，辅助学术科研中的文献检索、交叉验证和结果整理。

详细工作流见 [targeted_search.md](/home/heyx/Hypo-Research/src/hypo_research/prompts/targeted_search.md)。

## 能力概览

| 能力 | 说明 | 命令 |
|------|------|------|
| 定向文献检索 | 多源并行检索（S2 + OpenAlex + arXiv），跨源去重，交叉验证 | `hypo-research search` |
| 多 query 批量检索 | 主 query + 扩展 query 组合检索，自动合并去重 | `hypo-research search -eq` |
| 自动输出 | JSON + BibTeX + Markdown 报告，auto-verify 元数据质量检查 | 内置 hook，默认启用 |

## 何时使用

当用户要求以下任务时，应调用 Hypo-Research：

- 帮我查一下 XXX 方向的文献
- 搜一下 XXX 相关的论文
- 做一个关于 XXX 的文献调研
- 找 XXX 领域最近几年的论文

## 快速使用

### 单 query 检索

```bash
hypo-research search "<query>" --output-dir data/surveys/<name>
```

### 多 query 检索（推荐）

```bash
hypo-research search "<main query>" \
  -eq "<expanded query 1>" \
  -eq "<expanded query 2>" \
  --output-dir data/surveys/<name>
```

### 指定源

```bash
hypo-research search "<query>" --source s2 --source arxiv
```

可选源：`s2`、`openalex`、`arxiv`、`all`（默认）

### Hook 控制

- `--no-hooks`：禁用所有 hook
- `--no-bib`：不生成 BibTeX
- `--no-report`：不生成 Markdown 报告
- `--no-auto-verify`：不做元数据质量检查

## 输出文件

每次检索在 `--output-dir` 下生成：

| 文件 | 说明 |
|------|------|
| `results.json` | 结构化检索结果（机器可读） |
| `meta.json` | 检索元数据（query、源、统计） |
| `references.bib` | BibTeX（可直接导入 LaTeX） |
| `results.md` | 人类可读调研报告 |

## 推荐工作流

1. 理解用户需求，确定 1 个主 query 和 2-3 个扩展 query。
2. 执行 `hypo-research search`，优先使用多 query + 全源。
3. 审查 `results.md`，关注 auto-verify 标记的问题。
4. 将 `references.bib` 提供给用户用于 LaTeX / Zotero。
5. 向用户汇报检索结果摘要、验证状态和数据质量。

## 重要注意事项

- 检索完成后，必须查看 auto-verify 的输出。标记为 `error` 的论文可能不可信。
- 对 single-source 且无 DOI 的论文保持谨慎。
- arXiv 不提供 citation/reference graph；如需引用网络分析，依赖 S2 和 OpenAlex。
- 输出目录命名建议：`data/surveys/<日期>_<slug>`，如 `data/surveys/2026-04-22_cryogenic_gpu`

## 项目结构

```text
src/hypo_research/
├── core/models.py, rate_limiter.py, dedup.py, verifier.py
├── core/sources/{base.py, semantic_scholar.py, openalex.py, arxiv.py}
├── hooks/{base.py, auto_verify.py, auto_bib.py, auto_report.py}
├── survey/targeted.py
├── output/{json_output.py, bibtex.py, markdown_report.py}
├── prompts/targeted_search.md
└── cli.py
```

## 文件路由

- Skill Prompt：`src/hypo_research/prompts/targeted_search.md`
- Slash commands：`.claude/commands/`
- 用户指南：`docs/skill-usage-guide.md`
- 测试：`tests/`
