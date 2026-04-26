# Hypo-Research

文献调研 Skill，辅助学术科研中的文献检索、交叉验证和结果整理。

详细工作流见 [targeted_search.md](/home/heyx/Hypo-Research/src/hypo_research/prompts/targeted_search.md)。

## 环境管理规范

**本项目强制使用 uv 管理依赖和虚拟环境，严禁使用 pip / virtualenv / conda。**

- 安装依赖：`uv add <package>`
- 运行命令：`uv run <command>`
- 同步环境：`uv sync`
- 运行测试：`uv run pytest`

如果你看到代码或文档里有旧的 pip 安装命令、`requirements.txt` 等残留，视为需要修复的 bug。

## Skills

本项目的 Skills 位于 `skills/` 目录，遵循 Agent Skills 开放标准（SKILL.md + YAML frontmatter）。

可用 Skills：
- `hypo-survey` — 综合文献调研（发散式扩池，多源检索 + 去重 + 验证 + 报告生成）
- `hypo-cite` — 从种子论文沿引用 / 被引关系扩展候选池
- `hypo-search` — 快速单次检索（点查 / 补充）
- `hypo-screen` — 按自定义规则筛选、分类、生成分析报告
- `hypo-lint` — 检查单文件或多文件 LaTeX 项目的结构规范，支持 dry-run / backup 的自动修复
- `hypo-verify` — 联网验证单/多 `.bib` 引用是否真实存在并检查元数据错误
- `hypo-polish` — 基于章节写作统计做英文润色建议或定向改写，支持 `\input`/`\include` 项目
- `hypo-translate` — 维护中文注释与英文正文的双语同步，支持多文件 LaTeX 项目
- `hypo-check` — 一键执行 lint → fix → verify → 聚合报告的 writing pipeline
- `hypo-meeting` — 从 ASR 转写生成结构化会议纪要，并维护全局术语知识库

调用方式：
- Claude Code：`/hypo-survey` 或 `$hypo-survey`
- Codex CLI：运行 `./install-skills.sh` 后，`/hypo-survey` 或 `/prompts:hypo-survey`

首次使用前运行 `./install-skills.sh` 安装 Skills 到各 Agent 的约定位置。

## Plugin / Skill 安装

本仓库同时提供两种分发入口：

- Claude Code marketplace：`.claude-plugin/marketplace.json`
- Codex skill bundle：`.agents/skills/hypo-research/`

注意：当前 Codex `skill-installer` 的稳定能力是从 GitHub repo/path 安装 skill bundle；裸名字安装依赖上游 curated registry，不由本仓库单独决定。

## 能力概览

| 能力 | 说明 | 命令 |
|------|------|------|
| 定向文献检索 | 多源并行检索（S2 + OpenAlex + arXiv），跨源去重，交叉验证 | `hypo-research search` |
| 多 query 批量检索 | 主 query + 扩展 query 组合检索，自动合并去重 | `hypo-research search -eq` |
| 自动输出 | JSON + BibTeX + Markdown 报告，auto-verify 元数据质量检查 | 内置 hook，默认启用 |
| 会议纪要 | ASR 转写术语纠正、模板上下文生成、全局 glossary 管理 | `hypo-research meeting` / `hypo-research glossary` |

## 何时使用

当用户要求以下任务时，应调用 Hypo-Research：

- 帮我查一下 XXX 方向的文献
- 搜一下 XXX 相关的论文
- 做一个关于 XXX 的文献调研
- 找 XXX 领域最近几年的论文
- 从已知核心论文出发扩展相关工作 / 引文网络
- 按规则筛选 / 分类已有调研结果
- 检查某个候选池是否漏掉关键论文
- 检查单文件或多文件 LaTeX 论文的 label / ref / float / BibTeX 结构问题
- 对论文项目执行一键全面检查（lint + fix + verify + report）
- 检查 `.bib` 中是否存在幻觉论文或错误元数据
- 对论文英文做润色或定向改写
- 维护中英双语草稿的一致性
- 从 ASR 转写生成组会、论文讨论、课题讨论、请教或导师沟通纪要
- 添加、查询、删除会议转写术语知识库条目

## 快速使用

### 初始化项目配置

```bash
uv run hypo-research init
uv run hypo-research init --dir ./paper
```

配置文件名固定为 `.hypo-research.toml`，优先级为：CLI 参数 > 配置文件 > 环境变量 > 内置默认值。

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

### 配置 Semantic Scholar API Key（可选）

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
├── writing/{config.py, project.py, fixer.py, check.py, stats.py, bib_parser.py, verify.py}
├── core/sources/{base.py, semantic_scholar.py, openalex.py, arxiv.py}
├── hooks/{base.py, auto_verify.py, auto_bib.py, auto_report.py}
├── survey/targeted.py
├── output/{json_output.py, bibtex.py, markdown_report.py}
├── prompts/targeted_search.md
└── cli.py
```

## 文件路由

- Skill Prompt：`src/hypo_research/prompts/targeted_search.md`
- Skills：`skills/`
- 安装脚本：`install-skills.sh`
- 用户指南：`docs/skill-usage-guide.md`
- 测试：`tests/`
