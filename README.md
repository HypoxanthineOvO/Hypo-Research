# 🔬 Hypo-Research

学术文献调研 AI Skill 包，在 Codex CLI 或 Claude Code 中一键调用，三源并行检索、自动去重验证、生成结构化报告。

## ✨ 特性

- **三源并行检索**：Semantic Scholar + OpenAlex + arXiv 同时搜索
- **自动去重 & 交叉验证**：DOI / 标题+作者 双重匹配，标记 verified / single-source / suspicious
- **筛选分类引擎**：按自定义规则对候选池分类，输出结构化分析报告
- **LaTeX 结构检查**：静态提取 label / ref / float / BibTeX 统计，支持单文件和多文件项目 lint
- **写作维护工具**：支持多文件 LaTeX 项目的引用验证、英文润色和中英双语同步维护
- **结构化输出**：Markdown 报告 + BibTeX 引用 + JSON 元数据
- **Skill 驱动**：通过 `/hypo-survey` 等命令直接调用，Agent 自动完成全流程

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/HypoxanthineOvO/Hypo-Research.git
cd Hypo-Research
uv sync
./install-skills.sh
```

> 没有 uv？`curl -LsSf https://astral.sh/uv/install.sh | sh`

## Installation

### As a Python package / repo checkout

```bash
git clone https://github.com/HypoxanthineOvO/Hypo-Research.git
cd Hypo-Research
uv sync
./install-skills.sh
```

### As a Claude Code Plugin

```text
/plugin marketplace add HypoxanthineOvO/Hypo-Research
/plugin install hypo-research@hypoxanthineovo-hypo-research
```

### As a Codex Skill

当前 Codex `skill-installer` 的稳定方式是从 GitHub repo/path 安装一个 skill bundle：

```text
$skill-installer https://github.com/HypoxanthineOvO/Hypo-Research/tree/main/.agents/skills/hypo-research
```

说明：

- Claude Code 侧支持 marketplace 安装。
- Codex 侧当前支持的是 GitHub 路径安装；裸名字安装依赖上游 curated registry，不由本仓库单独决定。

### 配置（可选）

```bash
# Semantic Scholar API Key — 大幅提升搜索速率，不设置也能用
export SEMANTIC_SCHOLAR_API_KEY="your-key-here"

# 申请: https://www.semanticscholar.org/product/api#api-key-form
```

项目级配置文件也支持：

```bash
uv run hypo-research init
uv run hypo-research init --dir ./paper
```

优先级：CLI 参数 > `.hypo-research.toml` > 环境变量 > 内置默认值。

Packaging 入口：

- Claude marketplace: [`.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json)
- Claude plugin bundle: [`plugins/hypo-research/.claude-plugin/plugin.json`](./plugins/hypo-research/.claude-plugin/plugin.json)
- Codex skill bundle: [`.agents/skills/hypo-research/SKILL.md`](./.agents/skills/hypo-research/SKILL.md)

---

## Skills

Hypo-Research provides **11 Skills** organized into three modules:

### 📚 Survey Module — Literature Discovery & Analysis

| Skill | Command | Description |
|-------|---------|-------------|
| `/hypo-survey` | `uv run hypo-research search` | Comprehensive literature survey with multi-source search, deduplication, and verification |
| `/hypo-search` | `uv run hypo-research search` | Quick targeted search for specific papers or topics |
| `/hypo-screen` | `Agent-driven (no standalone CLI)` | Filter and classify papers by relevance criteria |
| `/hypo-cite` | `uv run hypo-research cite` | Citation graph traversal — expand references and citations from seed papers |

### ✍️ Writing Module — LaTeX Paper Writing Assistance

| Skill | Command | Description |
|-------|---------|-------------|
| `/hypo-lint` | `uv run hypo-research lint` | LaTeX structure checking — 13 rules covering `\cref`, floats, labels, `tblr`, title case, spacing, and more |
| `/hypo-verify` | `uv run hypo-research verify` | Citation verification — check `.bib` entries against Semantic Scholar and OpenAlex |
| `/hypo-polish` | `uv run hypo-research lint --stats` | English polishing — full-document scan or targeted section rewriting (Agent-driven, uses `chapter_stats`) |
| `/hypo-translate` | `uv run hypo-research lint --stats` | Bilingual maintenance — sync/cn2en/en2cn modes for `% 中文注释` + English paragraph pairs |
| `/hypo-check` | `uv run hypo-research check` | Writing pipeline — lint, auto-fix, verify, and save an aggregated report |
| `/hypo-presubmit` | `uv run hypo-research presubmit` | Pre-submission gate — check, lint, verify, and emit a unified PASS/WARNING/FAIL report |

### 📝 Meeting Module — ASR Minutes & Glossary

| Skill | Command | Description |
|-------|---------|-------------|
| `/hypo-meeting` | `uv run hypo-research meeting` | Generate structured academic meeting minutes from ASR transcripts with glossary-based terminology correction |

## 📖 Skills 使用指南

### `/hypo-survey` — 综合文献调研

完整的多源文献调研。Agent 自动设计查询、扩展关键词、三源并行检索、去重验证、生成报告。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `topic` | ✅ | 调研主题 | `"NeRF real-time rendering"` |
| `year_range` |  | 年份范围 | `2020-2026`（默认近 5 年） |
| `sources` |  | 数据源 | `all` / `s2` / `openalex` / `arxiv` |

**示例：**

```text
/hypo-survey topic="NeRF real-time rendering" year_range=2020-2026
```

Agent 会自动：
1. 设计主 query + 扩展 query：`"neural radiance field real-time"`、`"instant NGP"`、`"3D Gaussian splatting acceleration"`
2. 三源并行检索 -> 去重合并 -> 交叉验证
3. 输出报告：

```text
📊 检索完成

- 论文数：142（87 verified，55 single-source）
- Top 5：
  1. Instant-NGP (2022, SIGGRAPH, citations=1847)
  2. 3D Gaussian Splatting (2023, SIGGRAPH, citations=956)
  3. Plenoxels (2022, CVPR, citations=892)
  4. TensoRF (2022, ECCV, citations=634)
  5. Mip-NeRF 360 (2022, CVPR, citations=587)
- 输出目录：data/surveys/2026-04-22_nerf_realtime/
```

---

### `/hypo-screen` — 文献筛选分类

按自定义规则对调研结果进行筛选、分类、分析。将大候选池收敛为结构化的分类报告。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `path` | ✅ | 调研结果目录 | `"data/surveys/2026-04-22_fhe_hw/"` |
| `rules` | ✅ | 分类规则（自然语言） | 见下方示例 |
| `recall_checklist` |  | 已知重要论文列表 | `"Cinnamon, Hydra, ARK, ..."` |

**示例：**

```text
/hypo-screen path="data/surveys/2026-04-22_fhe_hw/" rules="""
A: FHE + 大模型推理 + 硬件加速器（ASIC/FPGA/GPU）
B: FHE + 硬件加速器（CNN 或更小规模模型）
C: FHE + 大模型推理（纯软件优化）
D: CIM/PIM + FHE
排除: MPC/GC/OT 为主导方案
""" recall_checklist="Cinnamon, Hydra, CraterLake, F1, ARK, TensorFHE"
```

Agent 会逐篇标注类别，输出：

```text
📋 筛选完成（1437 篇 -> 5 类）

- A（FHE + 大模型 + 硬件）= 2: Cinnamon (ASPLOS'25), Hydra (HPCA'25)
- B（FHE + 硬件）= 26: CraterLake, F1, ARK, TensorFHE, ...
- C（FHE + 大模型软件）= 17: EncryptedLLM, Iron, ...
- D（CIM/PIM + FHE）= 9
- 排除 = 7
- Recall: 24/24
- 输出：classified_papers.json, analysis_report.md
```

---

### `/hypo-search` — 快速文献检索

单次快速检索，不做 query 扩展。适合已知关键词的精确查找，或对调研结果的补充检索。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `query` | ✅ | 检索词 | `"3D Gaussian Splatting"` |
| `source` |  | 数据源 | `all`（默认） |

**示例：**

```text
/hypo-search query="CKKS bootstrapping FPGA accelerator"
```

---

### `/hypo-cite` — 引文图扩展

从种子论文出发，通过引用 / 被引关系发现相关论文。输出格式与 `/hypo-survey` 兼容，可直接传给 `/hypo-screen`。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `seeds` | ✅ | 种子论文（DOI / arXiv ID / 标题） | `"Cinnamon, CraterLake, F1"` |
| `depth` |  | 遍历深度 | `1`（默认）/ `2` |
| `direction` |  | 方向 | `both`（默认）/ `citations` / `references` |
| `year_range` |  | 年份过滤 | `2020-2026` |

**示例：**

```text
/hypo-cite seeds="Cinnamon, CraterLake, F1" depth=1 direction=both year_range=2020-2026
```

---

### `/hypo-lint` — LaTeX 结构检查

检查 LaTeX 论文的结构规范性，输出问题报告并支持自动修复。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `path` | ✅ | LaTeX 项目路径 | `"docs/"` |
| `bib` |  | `.bib` 文件路径 | `"refs.bib"` |
| `rules` |  | 只检查指定规则 | `"L01,L04,L07"` |
| `fix` |  | 自动修复 | `true` |

**检查规则（13 条）：**
- L01-L03: `\cref` / `\cite` 规范（禁用 `\ref`，必须有 `~`）
- L04-L06: 浮动体规范（placement、label 顺序、label 前缀）
- L07: 表格环境（禁用 `tabular`，用 `tblr`）
- L08: 孤立 label / ref 检测
- L09-L10: 缩写展开 + 标题 Title Case（Agent 辅助判断）
- L11-L13: 间距和空格规范

**示例：**

```text
/hypo-lint path="docs/" fix=true
```

---

### `/hypo-verify` — 引用验证

验证 `.bib` 文件中引用的论文是否真实存在，检测幻觉论文和元数据错误。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `bib` | ✅ | `.bib` 文件路径 | `"refs.bib"` |
| `tex` |  | `.tex` 文件/目录（只验证被引用的） | `"docs/"` |
| `keys` |  | 只验证指定 cite key | `"cinnamon2025,f1wrong"` |
| `fix` |  | 自动修复可修复项 | `true` |

**检查内容：**
- 论文是否存在于 Semantic Scholar / OpenAlex
- 标题、年份、venue、作者是否匹配
- 检测 LLM 生成的幻觉论文
- 检测元数据错误（年份、DOI 等）

**示例：**

```text
/hypo-verify bib="refs.bib" tex="docs/" fix=true
```

---

### `/hypo-polish` — 学术英文润色

对 LaTeX 论文做英文润色，支持全文扫描和定向段落两种模式。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `path` | ✅ | LaTeX 文件或目录 | `"paper.tex"` |
| `mode` |  | `full` / `targeted` | `"full"` |
| `target` |  | section 标题或行号范围 | `"Method"` |
| `apply` |  | 是否直接写回 | `false` |

**示例：**

```text
/hypo-polish path="paper.tex" mode=full
/hypo-polish path="paper.tex" mode=targeted target="Method"
```

---

### `/hypo-translate` — 中英双语翻译维护

维护中文注释 + 英文正文的双语 LaTeX 草稿，支持同步检查、中文转英文、英文转中文。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `path` | ✅ | LaTeX 文件或目录 | `"paper.tex"` |
| `mode` |  | `sync` / `cn2en` / `en2cn` | `"sync"` |
| `target` |  | 可选 section 或行号范围 | `"Introduction"` |
| `apply` |  | 是否直接写回 | `false` |

**示例：**

```text
/hypo-translate path="paper.tex" mode=sync
/hypo-translate path="paper.tex" mode=cn2en
/hypo-translate path="paper.tex" mode=en2cn
```

---

### Writing Module Examples

#### LaTeX Structure Check

```bash
# Human-readable lint report
uv run hypo-research lint paper.tex

# Auto-detect a multi-file project from the root file
uv run hypo-research lint main.tex

# Start from a subfile and resolve the project root automatically
uv run hypo-research lint sections/intro.tex

# Explicit project root when the CLI path is relative to the paper directory
uv run hypo-research lint --project-dir ./paper main.tex

# JSON stats for Agent consumption
uv run hypo-research lint --stats paper.tex

# Filter by specific rules
uv run hypo-research lint --rules L01,L04,L07 paper.tex

# Include .bib checks
uv run hypo-research lint --bib refs.bib paper.tex

# Preview auto-fixes without modifying files
uv run hypo-research lint --fix paper.tex
uv run hypo-research lint --fix main.tex

# Apply fixes in place
uv run hypo-research lint --fix --no-dry-run paper.tex

# Apply fixes with backups
uv run hypo-research lint --fix --no-dry-run --backup paper.tex

# Restrict auto-fix to selected rules
uv run hypo-research lint --fix --rules L01,L04 paper.tex
```

#### Project Config

```toml
[project]
main_file = "main.tex"
bib_files = ["refs.bib", "extra.bib"]

[lint]
disabled_rules = ["L09", "L10"]
fix_rules = ["L01", "L04"]

[verify]
timeout = 60
skip_keys = ["draft2025"]

[survey]
default_topic = "FHE accelerator"
sources = ["s2", "arxiv"]
```

```bash
uv run hypo-research init
uv run hypo-research lint
uv run hypo-research verify
uv run hypo-research search
```

#### Citation Verification

```bash
# Verify all .bib entries (Markdown report)
uv run hypo-research verify refs.bib

# JSON output for programmatic use
uv run hypo-research verify --stats refs.bib

# Only verify entries actually cited in .tex
uv run hypo-research verify --tex paper.tex refs.bib

# Auto-discover .bib files from a multi-file LaTeX project
uv run hypo-research verify --tex main.tex
uv run hypo-research verify --project-dir ./paper

# Verify specific keys
uv run hypo-research verify --keys craterlake2022,f1_2021 refs.bib
```

#### One-Command Check Pipeline

```bash
# Full pipeline (fix dry-run + verify + report)
uv run hypo-research check paper.tex

# Apply fixes, then verify
uv run hypo-research check --no-dry-run --backup paper.tex

# Lint/fix only
uv run hypo-research check --lint-only paper.tex

# JSON-only output
uv run hypo-research check --json --no-save paper.tex
```

#### Polishing & Translation (Agent-driven)

```bash
# Get chapter-level writing statistics (for /hypo-polish)
uv run hypo-research lint --stats paper.tex | jq '.chapter_stats'

# Get bilingual paragraph pairs (for /hypo-translate)
uv run hypo-research lint --stats paper.tex | jq '.paragraph_pairs'
uv run hypo-research lint --stats paper.tex | jq '.orphan_paragraphs'
```

#### Project Config

```bash
# Initialize .hypo-research.toml in the current directory
uv run hypo-research init

# Or initialize a specific paper directory
uv run hypo-research init --dir ./paper

# Then use config-driven defaults for main_file / bib_files / rules / query
uv run hypo-research lint
uv run hypo-research verify
uv run hypo-research search
```

Priority: CLI arguments > `.hypo-research.toml` > environment variables > built-in defaults.

---

### 推荐工作流

```text
# Step 1：综合调研，建立候选池
/hypo-survey topic="FHE hardware accelerator" year_range=2020-2026

# Step 2：从核心论文扩展引用图
/hypo-cite seeds="Cinnamon, CraterLake, F1, ARK" depth=1

# Step 3：按自定义规则筛选分类
/hypo-screen path="data/surveys/2026-04-22_fhe_hw/" rules="""
A: FHE + 大模型 + 硬件加速
B: FHE + 硬件（CNN 级别）
C: FHE + 大模型（软件）
D: CIM/PIM + FHE
排除: MPC/GC/OT
"""

# Step 4：根据分类报告，补充检索薄弱方向
/hypo-search query="NTT hardware architecture survey"
/hypo-search query="TFHE gate bootstrapping accelerator"

# Step 5：合并补充结果，重新筛选
/hypo-screen path="data/surveys/2026-04-22_fhe_hw/" rules="..."

# 写作检查流程
/hypo-lint path="docs/" fix=true
/hypo-verify bib="refs.bib" tex="docs/"
/hypo-polish path="paper.tex" mode=full
/hypo-translate path="paper.tex" mode=sync
```

---

## 🤝 兼容性

| Agent | 调用方式 | 安装 |
|-------|---------|------|
| **Claude Code** | `/hypo-survey` 或 `$hypo-survey` | `./install-skills.sh` |
| **Codex CLI** | `/hypo-survey` 或 `/prompts:hypo-survey` | `./install-skills.sh` |

Skills 遵循 [Agent Skills 开放标准](https://github.com/agentskills/agentskills)（SKILL.md + YAML frontmatter）。

## Project Structure

```text
src/hypo_research/writing/
├── __init__.py
├── config.py         # .hypo-research.toml loading and init helpers
├── project.py        # Multi-file LaTeX project resolution
├── fixer.py          # Lint auto-fix generation and application
├── check.py          # Writing pipeline orchestration and reporting
├── stats.py          # TexStats: labels, refs, floats, sections, chapter_stats, paragraph_pairs
├── bib_parser.py     # BibEntryInfo: .bib file parsing
└── verify.py         # Citation verification via S2/OpenAlex
```

## ⚙️ 配置说明

### 项目配置文件

项目根目录可选放置 `.hypo-research.toml`：

```bash
uv run hypo-research init
uv run hypo-research init --dir ./paper
```

优先级：CLI 参数 > `.hypo-research.toml` > 环境变量 > 内置默认值。

`check` 报告默认写入 `.hypo-research-report/check-YYYY-MM-DD.json`，建议将 `.hypo-research-report/` 加入 `.gitignore`。

### Semantic Scholar API Key

设置后可大幅提升 S2 搜索速率（从 ~1 req/s 提升到 ~10 req/s）。不设置时仍可使用，但大批量搜索可能触发 rate limit。

```bash
export SEMANTIC_SCHOLAR_API_KEY="your-key-here"

# 申请: https://www.semanticscholar.org/product/api#api-key-form
```

### uv

本项目使用 [uv](https://github.com/astral-sh/uv) 管理依赖。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 🛠️ 开发

```bash
# 163 tests (160 passed + 3 skipped network)
uv run pytest -v
uv run hypo-research --help
```

## Versions

| Tag | Commit | Milestone | Skills |
|-----|--------|-----------|--------|
| v0.1.0 | 0bc7681 | M1-M5 | 4 (survey/search/screen/cite) |
| v0.1.1 | 1705f5c | M5.1 | 4 (uv migration, arXiv fix) |
| v0.2.0 | 14dcc84 | M6 | 4 + cite graph traversal |
| v0.3.0 | 54199c6 | M7 | 8 (+ lint/verify/polish/translate) |

## 📄 License

MIT
