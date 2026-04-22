# Hypo-Research

学术文献调研工具，支持多源并行检索、跨源去重、交叉验证和自动化输出。

## 功能特性

- 多源检索：Semantic Scholar、OpenAlex、arXiv 并行检索
- 跨源去重：DOI / 标题+作者+年份 / Jaccard fuzzy 三层去重
- 交叉验证：自动标记被多个源确认的论文
- 多格式输出：JSON（结构化）、BibTeX（LaTeX 可用）、Markdown（人类可读报告）
- 元数据质量检查：自动检测缺 DOI、缺作者等问题
- Hook 系统：可扩展的流水线后处理机制
- Skill 集成：可作为 Claude Code / Codex 的 Skill 使用

## 安装

本项目使用 [uv](https://github.com/astral-sh/uv) 管理环境和依赖。

### 从源码安装（推荐）

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone git@gitlab.vsplab.cn:heyx/hypo-research.git
cd Hypo-Research
uv sync
```

### 验证安装

```bash
uv run hypo-research --help
```

### 依赖

- Python >= 3.11
- httpx, click, pydantic, rich, feedparser

## 快速开始

### 基本检索

```bash
uv run hypo-research search "你的检索词" --output-dir data/surveys/my_survey
```

### 多 query 检索（推荐，覆盖更广）

```bash
uv run hypo-research search "main query" \
  -eq "expanded query 1" \
  -eq "expanded query 2" \
  --output-dir data/surveys/my_survey
```

### 指定数据源

```bash
uv run hypo-research search "query" --source s2 --source arxiv
```

可选源：`s2`（Semantic Scholar）、`openalex`、`arxiv`、`all`（默认）

### 控制年份范围

```bash
uv run hypo-research search "query" --year-start 2020 --year-end 2026
```

## 配置 Semantic Scholar API Key（可选）

申请地址：https://www.semanticscholar.org/product/api#api-key-form

设置环境变量后可大幅提高搜索速率：

```bash
export SEMANTIC_SCHOLAR_API_KEY="your-key-here"
```

不设置时仍可使用（free tier，约 1 req/sec），大批量搜索可能触发 rate limit。

## 输出文件

每次检索在 `--output-dir` 下生成：

| 文件 | 说明 |
|------|------|
| `results.json` | 结构化检索结果 |
| `meta.json` | 检索元数据和统计 |
| `references.bib` | BibTeX（可导入 LaTeX） |
| `results.md` | 人类可读调研报告 |

## 配合 LaTeX 使用

1. 将 `references.bib` 复制到 LaTeX 项目
2. 在 `.tex` 中 `\bibliography{references}`
3. 用 `\cite{smith2023xxx}` 引用

## 作为 Skill 使用

Hypo-Research 可以作为 Claude Code / Codex 的 Skill 自动调用：

- Claude Code：运行 `./install-skills.sh` 后，使用 `/survey`、`/quick-search`、`/review-results`
- Codex：运行 `./install-skills.sh` 后，通过 `/prompts:survey` 或自然语言描述调研需求，由 `AGENTS.md` 自动调度

详见 [docs/skill-usage-guide.md](/home/heyx/Hypo-Research/docs/skill-usage-guide.md)。

## 开发

### 运行测试

```bash
uv run pytest -v
uv run pytest -m e2e -v
uv run pytest -m "not e2e" -v
```

## License

MIT
