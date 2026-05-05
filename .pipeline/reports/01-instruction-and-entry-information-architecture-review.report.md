# M02 报告：指令与入口信息架构审查

## 结论

当前最大问题不是功能少，而是入口太像“命令清单”。README 和 Skill 体系强调 19 个 `$hypo-xxx`，适合作者和专家用户，却不适合真实研究场景中的自然表达。

推荐把顶层用户入口收敛为 **5 个固定场景 + 1 个项目入口**：

1. `调研方向`
2. `读论文`
3. `写论文`
4. `审论文`
5. `想 idea / 做实验计划`
6. `管理研究项目`

底层 19 个 Skill 继续存在，但默认作为 router 选择的子能力，而不是让用户记忆的主入口。

## 当前入口问题

| 问题 | 证据 | 影响 |
|---|---|---|
| 顶层 Skill 太多 | 当前有 19 个 `skills/*/SKILL.md` | 用户需要记名字，入口反人类 |
| CLI 与 Skill 分类不完全同构 | `hypo-polish`、`hypo-translate` 是 Skill 文档驱动，CLI 没有同名顶层命令 | 用户难以判断该用 CLI 还是 Agent |
| 文献检索拆成 search/survey/cite/screen | 对 Agent 内部合理，对用户入口过细 | “我想了解一个方向”需要先知道策略 |
| 写作能力拆得细 | lint/check/presubmit/verify/polish/translate | 对提交前 workflow 应该自动编排 |
| 项目管理有强潜力但不是主入口 | `project` 模块有 paper、meeting、idea、challenge、experiment、plan、rebuttal | 应成为 research OS 的骨架 |

## 推荐顶层 IA

```text
Hypo-Research Guide
  调研方向
    快速扫盲
    系统检索
    引文扩展
    筛选分类
    调研报告
  读论文
    PDF/LaTeX 导入
    摘要级理解
    方法/数据/图表/claim 深读
    多篇对比
  写论文
    结构检查
    引用验证
    英文润色
    中英同步
    提交前检查
  审论文
    结构解析
    多角色 review
    meta-review
    revision roadmap
  想 idea / 做实验计划
    idea 生成
    challenge
    experiment
    plan
    pilot
  管理研究项目
    项目/论文/里程碑
    会议
    决策
    rebuttal
    dashboard
```

## 当前 Skill 到新入口映射

| 新入口 | 主能力 | 子能力 |
|---|---|---|
| 调研方向 | `hypo-survey`、`hypo-search` | `hypo-cite`、`hypo-screen` |
| 读论文 | 新增 `hypo-read` | PDF/LaTeX parse、deep-read、figure/claim notes |
| 写论文 | `hypo-check`、`hypo-presubmit` | `hypo-lint`、`hypo-verify`、`hypo-polish`、`hypo-translate` |
| 审论文 | `hypo-review` | literature context、roadmap |
| 想 idea / 做实验计划 | `hypo-pilot` | `hypo-idea`、`hypo-challenge`、`hypo-experiment`、`hypo-plan` |
| 管理研究项目 | `hypo-project` | `hypo-meeting`、project rebuttal/import/status |

## 路由追问树

### 调研方向

1. 你熟悉这个领域吗？
2. 你要快速入门、找最新论文、系统综述，还是找 related work 缺口？
3. 需要输出 BibTeX、阅读顺序、证据矩阵、还是项目知识库？

### 读论文

1. 输入是 PDF、LaTeX、arXiv 链接，还是检索结果里的论文？
2. 你想快速判断是否值得读，还是要深读方法/数据/图表/claim？
3. 是否要和其他论文横向对比？

### 写论文

1. 当前阶段是初稿、投稿前、rebuttal 后修改，还是 camera-ready？
2. 目标 venue 是什么？
3. 需要自动修复、只报告问题，还是生成修改建议？

### 审论文

1. 目标 venue 和严厉度是什么？
2. 只要结构化 review，还是要 meta-review 和 revision roadmap？
3. 是否需要先补 related work context？

### 项目管理

1. 是新建方向、管理某篇 paper，还是整理会议/决策？
2. 是否需要把检索、idea、实验计划导入项目？
3. 下一步是执行、复盘，还是准备汇报？

## 示例对话

用户：帮我调研一下 cryogenic CMOS 加速器，我不太熟。  
Guide：这是陌生领域调研。我会先给 5 分钟概念 primer，再做多源检索和阅读顺序。你要偏架构、器件、还是 EDA？  
路由：`调研方向 -> 快速扫盲 -> 系统检索 -> 调研报告`

用户：这两篇 PDF 帮我看方法和数据集差异。  
Guide：这是读论文/多篇对比。我会先抽取章节、图表和实验表，再回答方法、数据、claim 支撑。  
路由：`读论文 -> L2 深读 -> L4 对比`

用户：我论文快投了，帮我查一下。  
Guide：这是写论文/提交前检查。我会先跑结构 lint、BibTeX verify、venue profile，再生成修复建议。  
路由：`写论文 -> presubmit -> check/lint/verify`

## 兼容策略

- 保留所有 `$hypo-xxx` 作为专家快捷入口。
- 新增 `hypo-guide` 或 `hypo-research guide` 作为默认推荐入口。
- README 首屏从“19 个 Skill”改成“6 个研究场景”。
- Skill frontmatter 的 description 应围绕用户意图，而不是只列内部动作。

## 下一步实现候选

1. 新增 `skills/hypo-guide/SKILL.md`，负责路由。
2. 新增 `src/hypo_research/guide/`，定义 intent schema、entry scenario、routing questions。
3. README 重写 Quick Start：以场景开始，命令表后置。
4. 新增 `hypo-read` 规划入口，承接 M03 的 PDF/full-text 能力。
