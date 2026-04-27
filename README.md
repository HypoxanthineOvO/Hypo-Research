# 🔬 Hypo-Research

> 学术科研全流程辅助工具包：从文献调研、创意生成、论文写作检查、模拟审稿到 rebuttal，一站式串联科研工作流。
> 支持作为 Codex / Claude Skill 调用（`$hypo-xxx`），也可作为独立 CLI 使用。

[![Tests](https://img.shields.io/badge/tests-468%20total-brightgreen)]()
[![Skills](https://img.shields.io/badge/skills-19-blue)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## ✨ Features

- **19 个 Skill** 覆盖科研全流程，每个 Skill 独立可用
- **项目级管理**：多论文追踪、进度仪表盘、会议纪要、上下文自动串联
- **多源文献检索**：Semantic Scholar / arXiv / OpenAlex，自动去重、排序和元数据质量检查
- **模拟审稿**：7 个审稿人角色 + AC Meta-Review + 文献对比审稿
- **科研创意系统**：10 种生成策略 + 苏格拉底式拷打 + 评分框架
- **全流程串联**：`hypo-pilot` 一键串联 idea → challenge → experiment → plan
- **Rebuttal 生成**：审稿意见自动拆分、分类、策略匹配、回复信生成
- **结构化输出**：Markdown 报告 / BibTeX / JSON，可直接进入论文项目

---

## 📦 Installation

> ⚠️ 本项目强制使用 [uv](https://github.com/astral-sh/uv) 管理依赖和虚拟环境，不支持 pip / virtualenv / conda 工作流。

```bash
git clone https://github.com/HypoxanthineOvO/Hypo-Research.git
cd Hypo-Research
uv sync
uv run hypo-research --help
```

### Skill 安装（用于 Codex / Claude）

```bash
bash install-skills.sh
```

安装后 Skill 会出现在以下位置：

- `.agents/skills/hypo-research/skills/`：Codex Skill bundle 镜像
- `plugins/hypo-research/skills/`：Claude Plugin skill 镜像
- `~/.codex/prompts/`：Codex CLI prompt 副本
- `.claude/skills/`：Claude Code 本地链接

Codex 也可以从 GitHub path 安装整个 bundle：

```text
$skill-installer https://github.com/HypoxanthineOvO/Hypo-Research/tree/main/.agents/skills/hypo-research
```

---

## 🚀 Quick Start

```bash
# 定向检索论文，默认启用 BibTeX、Markdown 报告和 auto-verify hook
uv run hypo-research search "LLM for code generation" --max-results 10

# 多 query 扩展检索
uv run hypo-research search "LLM for code generation" \
  -eq "large language models program synthesis" \
  -eq "code generation benchmark evaluation"

# 检查论文 LaTeX 项目
uv run hypo-research check paper.tex

# 模拟审稿（ICML/NeurIPS/ACL 等 venue id 可按 --list-venues 查看）
uv run hypo-research review paper.tex --venue icml --panel full --severity standard

# 生成科研创意：默认同时输出 Quick Win 和 Ambitious
uv run hypo-research idea "LLM-assisted literature review" --num-ideas 3

# 运行完整 idea → challenge → experiment → plan 流程
uv run hypo-research pilot "LLM-assisted literature review" --auto-select --venue ACL

# 创建项目并查看仪表盘
uv run hypo-research project create "Cryo Computing" --direction "低温 CMOS 架构加速"
uv run hypo-research project status cryo-computing
```

---

## 🛠️ Skills 一览

### 📚 文献调研（4 个）

| Skill | CLI 入口 | 功能 |
|---|---|---|
| `hypo-survey` | `search` | 多源文献检索、自动去重、排序、报告生成 |
| `hypo-search` | `search` | 快速定向检索，支持 `-eq/--extra-query` Query Expansion |
| `hypo-screen` | Skill 文档 | 按规则筛选和分类已有调研结果 |
| `hypo-cite` | `cite` | 从种子论文沿引用 / 被引关系扩展候选池 |

### ✍️ 论文写作与检查（6 个）

| Skill | CLI 入口 | 功能 |
|---|---|---|
| `hypo-lint` | `lint` | LaTeX label / ref / float / BibTeX 结构检查 |
| `hypo-verify` | `verify` | BibTeX 引用真实性和元数据交叉验证 |
| `hypo-check` | `check` | 一键 writing pipeline：lint / fix / verify / report |
| `hypo-presubmit` | `presubmit` | 提交前统一检查，输出 PASS / WARNING / FAIL |
| `hypo-polish` | Skill 文档 | 学术英文润色和定向改写 |
| `hypo-translate` | Skill 文档 | 中英双语 LaTeX 草稿同步维护 |

### 🔍 审稿与回复（2 个）

| Skill | CLI 入口 | 功能 |
|---|---|---|
| `hypo-review` | `review` | 模拟审稿（7 角色 + AC Meta-Review + 修改路线图 + 一致性检查） |
| `hypo-rebuttal` | `rebuttal` | 审稿意见拆分 → 分类 → 回复策略 → Rebuttal Letter |

### 🧠 科研创意与规划（5 个）

| Skill | CLI 入口 | 功能 |
|---|---|---|
| `hypo-idea` | `idea` | 科研创意生成（Quick Win / Ambitious 双模式） |
| `hypo-challenge` | `challenge` | 苏格拉底式拷打（5 维度 × 3 严厉度） |
| `hypo-experiment` | `experiment` | 实验方案设计（baseline / dataset / metric / ablation） |
| `hypo-plan` | `plan` | 工作规划、论文大纲、时间表和风险缓解 |
| `hypo-pilot` | `pilot` | 全流程串联：idea → challenge → refine → experiment → plan |

### 📂 项目与会议（2 个）

| Skill | CLI 入口 | 功能 |
|---|---|---|
| `hypo-project` | `project` | 项目级科研管理（多论文、进度、仪表盘、会议、上下文串联） |
| `hypo-meeting` | `meeting` / `glossary` | ASR 转写会议纪要整理、术语纠正、全局 glossary 管理 |

---

## 💡 作为 Codex / Claude Skill 使用

这是 Hypo-Research 的推荐使用方式。在 Codex 或 Claude 中通过 `$hypo-xxx` 调用：

```text
$hypo-survey 帮我检索 "transformer architecture" 相关的最新论文，限定 2024 年以后
```

```text
$hypo-review 审一下 paper.tex，按 NeurIPS 标准，full panel，standard 严厉度
```

```text
$hypo-idea 方向是 "low-rank adaptation for vision models"，给我 Quick Win 和 Ambitious 各 3 个
```

```text
$hypo-rebuttal 帮我处理 reviews.md 里的审稿意见，目标会议 ICML
```

### 多 Skill 串联

```text
$hypo-pilot 方向 "LLM-assisted scientific literature review"，目标 ACL，跑全流程
```

`hypo-pilot` 会自动串联：创意生成 → 拷打验证 → 实验设计 → 工作规划，并给出导师式综合评语。

### 项目管理 Skill

```text
$hypo-project 创建项目 "Cryo Computing"，方向 "低温 CMOS 架构加速"
```

```text
$hypo-project 查看 cryo-computing 的项目仪表盘
```

---

## 🖥️ 作为 CLI 独立使用

所有已接入 CLI 的功能可直接调用：

```bash
uv run hypo-research --help

uv run hypo-research search      # 文献检索
uv run hypo-research cite        # 引用图扩展
uv run hypo-research lint        # LaTeX 结构检查
uv run hypo-research verify      # BibTeX 元数据验证
uv run hypo-research check       # 写作质量一键检查
uv run hypo-research presubmit   # 提交前检查
uv run hypo-research review      # 模拟审稿
uv run hypo-research idea        # 创意生成
uv run hypo-research challenge   # Idea 拷打
uv run hypo-research experiment  # 实验设计
uv run hypo-research plan        # 工作规划
uv run hypo-research pilot       # 创意全流程串联
uv run hypo-research project     # 项目管理
uv run hypo-research rebuttal    # 审稿回复
uv run hypo-research meeting     # 会议纪要
uv run hypo-research glossary    # 会议术语表
uv run hypo-research init        # 初始化 .hypo-research.toml
```

---

## 📂 Project Manager

`hypo-project` 提供项目级科研管理，支持多论文追踪、进度可视化、会议纪要集成和上下文自动注入。

项目默认保存在：

```text
~/.hypo-research/projects/
```

也可以用环境变量覆盖：

```bash
export HYPO_RESEARCH_PROJECTS_DIR=/path/to/projects
```

### 完整工作流

```bash
# 1. 创建研究项目
uv run hypo-research project create "Cryo Computing" \
  --direction "低温 CMOS 架构加速" \
  --description "探索低温计算中的架构与近似计算机会"

# 2. 添加论文
uv run hypo-research project paper add cryo-computing \
  "基于低温特性的近似计算框架" \
  --slug approx-framework \
  --venue ISCA \
  --deadline 2027-01-15

# 3. 导入已有 survey 输出
uv run hypo-research project import survey cryo-computing data/surveys/cryo/results.json

# 4. 记录会议纪要
uv run hypo-research project meeting add cryo-computing \
  --text "导师说：近似计算方向OK，注意精度损失
TODO: 下周前完成 ablation
决定：baseline 要加上常温 CMOS 对照" \
  --tag advisor \
  --paper approx-framework

# 5. 添加里程碑
uv run hypo-research project milestone add cryo-computing \
  "完成 ablation 实验" \
  --due 2026-05-02 \
  --paper approx-framework

# 6. 查看仪表盘
uv run hypo-research project status cryo-computing
```

### 仪表盘输出示例

```text
项目：Cryo Computing
方向：低温 CMOS 架构加速
阶段：active

论文：基于低温特性的近似计算框架 (approx-framework)
目标：ISCA | 截稿：2027-01-15 | 阶段：survey
进度：░░░░░░░░░░ 2%
距离截稿：263 天

近期里程碑
- [待办] 完成 ablation 实验 | due=2026-05-02 | paper=approx-framework

最近会议决策
- [2026-04-27 advisor] 导师说：近似计算方向OK，注意精度损失
- [2026-04-27 advisor] baseline 要加上常温 CMOS 对照
```

### 上下文自动串联

项目管理器会自动将已有调研、已否决创意、导师决策注入到其他 Skill 中：

```bash
uv run hypo-research project idea cryo-computing --paper approx-framework
```

注入的上下文示例：

```text
项目上下文（注入到 hypo-idea）
- 研究方向：低温 CMOS 架构加速
- 已有 survey：survey.json: Cryogenic CMOS Approximate Computing, FHE Acceleration under Low Temperature
- 避免重复的已否决 ideas：无
- 导师/组会决策：近似计算方向OK，注意精度损失；baseline 要加上常温 CMOS 对照
- 约束：deadline=2027-01-15; venue=ISCA
```

---

## ✉️ Rebuttal 生成

`hypo-rebuttal` 处理审稿意见的完整流程：

```bash
uv run hypo-research rebuttal reviews.md --paper-draft draft.md
uv run hypo-research rebuttal reviews.md --project cryo-computing --paper approx-framework --output json
uv run hypo-research project rebuttal cryo-computing --paper approx-framework --reviews reviews.md
```

处理流程：

1. 拆分：将审稿意见自动拆分为独立 comment
2. 分类：标记为 `factual_error` / `misunderstanding` / `valid_concern` / `suggestion` / `praise`
3. 策略：匹配 `correct` / `clarify` / `acknowledge` / `supplement` / `thank`
4. 生成：输出结构化 `RebuttalResult` 和 Rebuttal Letter

输出示例：

```text
Dear Area Chair and Reviewers,

We thank the reviewers for their careful reading and constructive feedback.

Reviewer 1, Comment c001. The paper lacks a strong baseline experiment.

Response. We agree this is an important concern. We will add a focused
comparison and report the result in the revised experiment section.
```

---

## ⚙️ 自定义配置

### 项目配置

```bash
uv run hypo-research init
uv run hypo-research init --dir ./paper
```

配置文件名固定为 `.hypo-research.toml`。优先级：

```text
CLI 参数 > 配置文件 > 环境变量 > 内置默认值
```

### Semantic Scholar API Key（可选）

不设置 API Key 也可使用公共端点；设置后可以提高搜索速率。

```bash
export SEMANTIC_SCHOLAR_API_KEY="your-key-here"
```

申请地址：https://www.semanticscholar.org/product/api#api-key-form

### 审稿人角色

`hypo-review` 内置 7 个审稿人角色，可通过 CLI 查看：

```bash
uv run hypo-research review --list-reviewers
uv run hypo-research review --list-venues
```

核心角色配置位于：

```text
src/hypo_research/review/reviewers.py
src/hypo_research/review/venues.py
```

### 娄萌萌人设

`hypo-pilot` 的导师人设位于：

```text
src/hypo_research/ideation/pilot.py
```

### 评分权重

创意评分权重位于：

```text
src/hypo_research/ideation/scoring.py
```

当前默认：

```python
# Ambitious
{"novelty": 0.35, "significance": 0.30, "feasibility": 0.20, "clarity": 0.15}

# Quick Win
{"novelty": 0.15, "significance": 0.20, "feasibility": 0.40, "clarity": 0.25}
```

### 拷打严厉度

```bash
uv run hypo-research challenge idea.json --severity gentle
uv run hypo-research challenge idea.json --severity standard
uv run hypo-research challenge idea.json --severity harsh
```

### 进度阶段权重

项目进度按研究阶段加权计算，默认位于 `src/hypo_research/project/progress.py`：

```python
STAGE_WEIGHTS = {
    "survey": 10,
    "ideation": 15,
    "experiment": 35,
    "writing": 25,
    "review": 10,
    "rebuttal": 5,
}
```

---

## 🏗️ Architecture

```text
Hypo-Research/
├── src/hypo_research/
│   ├── core/              # 基础设施：多源检索、去重、验证、限速
│   ├── core/sources/      # Semantic Scholar / OpenAlex / arXiv
│   ├── survey/            # 定向文献检索
│   ├── cite/              # 引用图扩展
│   ├── writing/           # LaTeX lint、检查、引用验证、写作统计
│   ├── review/            # 多角色模拟审稿
│   ├── meeting/           # 会议纪要与 glossary
│   ├── ideation/          # 创意生成、评分、拷打、实验、规划、pilot
│   ├── project/           # 项目管理、进度、仪表盘、会议上下文、rebuttal
│   ├── output/            # Markdown / BibTeX / JSON 输出
│   └── cli.py             # CLI 入口
├── skills/                # Skill 指令文件（19 个）
├── .agents/skills/        # Codex Skill bundle 镜像
├── plugins/               # Claude Plugin 镜像
├── tests/                 # 测试（468 total）
├── data/                  # 本地输出数据（可 gitignore）
└── install-skills.sh      # Skill 一键安装脚本
```

### 数据存储

- 调研数据：`data/surveys/`，或 `--output-dir` 指定目录
- 项目数据：`~/.hypo-research/projects/`，本地文件系统持久化，git friendly
- 输出文件：当前目录或 CLI 参数指定路径

### 支持的文献源

| 文献源 | API | 备注 |
|---|---|---|
| Semantic Scholar | 公共端点，可选 API Key | 论文检索、引用信息、引用验证 |
| arXiv | 公共 API | 预印本检索 |
| OpenAlex | 公共 API | 开放学术图谱和交叉验证 |

---

## 🤝 Contributing

欢迎贡献新的 Skill：

1. 在 `skills/` 下创建 `hypo-yourskill/SKILL.md`
2. 在 `src/hypo_research/` 下实现逻辑
3. 同步 `.agents/skills/hypo-research/skills/` 与 `plugins/hypo-research/skills/`
4. 运行 `bash install-skills.sh`
5. 添加测试到 `tests/`
6. 运行 `uv run pytest`

参考现有 Skill 的 `SKILL.md` 文件作为模板。

---

## 📄 License

MIT License
