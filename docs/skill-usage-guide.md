# Hypo-Research 使用指南

## 环境要求

本项目强制使用 [uv](https://github.com/astral-sh/uv) 管理环境和依赖，不使用 pip / virtualenv / conda。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/HypoxanthineOvO/Hypo-Research.git
cd Hypo-Research
uv sync
./install-skills.sh
```

## Skills

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/hypo-survey` | 综合文献调研 | 发散式扩池，尽可能做大候选集 |
| `/hypo-cite` | 引文图扩展 | 从已知核心论文沿引用 / 被引关系发现相关工作 |
| `/hypo-screen` | 文献筛选分类 | 按自定义规则收敛、分类、出分析报告 |
| `/hypo-search` | 快速文献检索 | 单次点查、补检、精确查找 |
| `/hypo-lint` | LaTeX 结构检查 | 检查 label / ref / float / BibTeX 结构问题并辅助修复 |
| `/hypo-verify` | 引用验证 | 联网验证 `.bib` 引用是否真实存在并检查元数据错误 |
| `/hypo-polish` | 学术英文润色 | 基于章节统计做全文扫描或定向润色 |
| `/hypo-translate` | 双语翻译维护 | 维护中文注释与英文正文的同步 |
| `/hypo-check` | 一键检查流水线 | 串联 lint、fix、verify 并输出聚合报告 |
| `/hypo-presubmit` | 提交前检查 | 串联 check、lint、verify 并输出 PASS/WARNING/FAIL 报告 |
| `/hypo-meeting` | 会议纪要 | 从 ASR 转写生成结构化学术会议纪要，并维护术语知识库 |

## 在 Claude Code 中使用

- `/hypo-survey topic="cryogenic computing for GPU" year_range=2020-2026`
- `/hypo-cite seeds="Cinnamon, CraterLake, F1" depth=1 direction=both`
- `/hypo-screen path="data/surveys/2026-04-22_cryo_gpu/" rules="A: cryo-CMOS; B: superconducting control"`
- `/hypo-search query="TFHE bootstrapping accelerator"`
- `/hypo-lint path="docs/" fix=true`
- `/hypo-verify bib="refs.bib" tex="docs/"`
- `/hypo-polish path="paper.tex" mode=full`
- `/hypo-translate path="paper.tex" mode=sync`
- `/hypo-check path="paper.tex"`
- `/hypo-presubmit path="paper.tex" venue=ieee_journal`
- `/hypo-meeting transcript="meeting_asr.txt" type=group_meeting`

多文件 LaTeX 项目也支持：

- `/hypo-lint path="main.tex"`
- `/hypo-lint path="sections/intro.tex"`
- `/hypo-lint path="paper.tex" fix=true`
- `/hypo-verify tex="main.tex"`
- `/hypo-verify project_dir="./paper"`
- `/hypo-polish path="main.tex" mode=targeted target="Method"`
- `/hypo-translate path="main.tex" mode=sync`

对应 CLI：

- `uv run hypo-research lint --fix paper.tex`
- `uv run hypo-research lint --fix --no-dry-run paper.tex`
- `uv run hypo-research lint --fix --no-dry-run --backup paper.tex`
- `uv run hypo-research lint --fix --rules L01,L04 paper.tex`
- `uv run hypo-research check paper.tex`
- `uv run hypo-research check --no-dry-run --backup paper.tex`
- `uv run hypo-research check --json --no-save paper.tex`

## 项目配置文件

Hypo-Research 支持项目根目录下的 `.hypo-research.toml`。

初始化：

```bash
uv run hypo-research init
uv run hypo-research init --dir ./paper
```

优先级：

- CLI 参数
- `.hypo-research.toml`
- 环境变量
- 内置默认值

常见字段：

- `[project] main_file / bib_files / src_dir`
- `[lint] disabled_rules / fix_rules`
- `[verify] timeout / skip_keys / max_concurrent`
- `[survey] default_topic / max_results / sources`

## 项目配置文件

Hypo-Research 支持项目根目录下的 `.hypo-research.toml`。

初始化：

```bash
uv run hypo-research init
uv run hypo-research init --dir ./paper
```

优先级：

- CLI 参数
- `.hypo-research.toml`
- 环境变量
- 内置默认值

常见字段：

- `[project] main_file / bib_files / src_dir`
- `[lint] disabled_rules / fix_rules`
- `[verify] timeout / skip_keys / max_concurrent`
- `[survey] default_topic / max_results / sources`

## 在 Codex CLI 中使用

执行 `./install-skills.sh` 后，可直接使用：

- `/hypo-survey` 或 `/prompts:hypo-survey`
- `/hypo-cite` 或 `/prompts:hypo-cite`
- `/hypo-screen` 或 `/prompts:hypo-screen`
- `/hypo-search` 或 `/prompts:hypo-search`
- `/hypo-lint` 或 `/prompts:hypo-lint`
- `/hypo-verify` 或 `/prompts:hypo-verify`
- `/hypo-polish` 或 `/prompts:hypo-polish`
- `/hypo-translate` 或 `/prompts:hypo-translate`
- `/hypo-check` 或 `/prompts:hypo-check`
- `/hypo-presubmit` 或 `/prompts:hypo-presubmit`
- `/hypo-meeting` 或 `/prompts:hypo-meeting`

也可以直接用自然语言描述需求，让 Agent 结合 `AGENTS.md` 自动路由。

## 典型工作流

1. 用 `/hypo-survey` 对主题做多 query、多源并行检索，建立候选池。
2. 用 `/hypo-cite` 从已知核心论文沿引用图扩展候选池。
3. 用 `/hypo-screen` 按你的分类规则收敛结果，并检查 recall checklist。
4. 用 `/hypo-search` 对薄弱方向做补充点查。
5. 重新筛选，输出最终分类报告和 BibTeX。
6. 写作阶段用 `/hypo-lint` 对 LaTeX 结构做静态检查和规范化修复。
7. 定稿前用 `/hypo-verify` 联网检查 `.bib` 是否混入幻觉论文或错误年份/DOI。
8. 用 `/hypo-polish` 做全文或局部英文润色。
9. 用 `/hypo-translate` 维护中文注释与英文正文同步。
10. 提交前用 `/hypo-presubmit` 运行 check / lint / verify 统一 gate。
11. 组会、论文讨论和导师沟通后，用 `/hypo-meeting` 将 ASR 转写整理成纪要。

## 输出文件

- `results.json`：结构化论文列表
- `meta.json`：检索元数据和统计
- `references.bib`：BibTeX 引用文件
- `results.md`：人类可读调研报告
- `classified_papers.json`：筛选分类结果
- `analysis_report.md`：分类分析报告

## 配置 Semantic Scholar API Key（可选）

```bash
export SEMANTIC_SCHOLAR_API_KEY="your-key-here"
```

申请地址：https://www.semanticscholar.org/product/api#api-key-form

不设置时仍可使用，但大批量搜索可能触发 rate limit。
