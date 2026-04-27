"""Reviewer persona definitions and prompt generation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from hypo_research.review.venues import VENUES, VenueProfile

if TYPE_CHECKING:
    from hypo_research.review.parser import PaperStructure
    from hypo_research.review.report import MetaReview, SingleReview


class Severity(Enum):
    GENTLE = "gentle"
    STANDARD = "standard"
    HARSH = "harsh"


@dataclass
class ReviewerConfig:
    """Configuration for one reviewer."""

    id: str
    name: str
    emoji: str
    role: str
    personality: str
    focus_areas: list[str]
    scoring: bool
    default: bool


SEVERITY_MODIFIERS = {
    Severity.GENTLE: {
        "label": "温和版",
        "tone": "以鼓励和建设性反馈为主。指出关键问题但语气温和。对初稿阶段的不完善给予理解。",
        "score_bias": +1,
        "threshold": "只标记真正严重的问题为 Major",
    },
    Severity.STANDARD: {
        "label": "标准版",
        "tone": "按正常学术审稿标准。客观公正，优缺点并列。",
        "score_bias": 0,
        "threshold": "正常标准区分 Major/Minor",
    },
    Severity.HARSH: {
        "label": "地狱版👹",
        "tone": "极其严格。任何瑕疵都会被指出。以顶会最苛刻审稿人的标准审视。宁可错杀不可放过。",
        "score_bias": -1,
        "threshold": "大量问题标记为 Major，容忍度极低",
    },
}


ACTIONABLE_FEEDBACK_REQUIREMENT = """
## ⚠️ 建设性反馈要求（必须遵守）

对于你指出的每一个 Weakness（无论 Major 还是 Minor），你**必须**同时给出：
1. **具体问题**：明确指出哪里有问题（引用论文具体章节/公式/图表）
2. **改进建议**：给出可执行的修改方案（不是"需要改进"，而是"建议在 Section 3.2 补充 XX 实验 / 修改公式 (5) 的 YY 假设 / 在 Figure 3 中增加 ZZ 对比"）
3. **重要程度理由**：解释为什么这是 Major 而不是 Minor（或反之）

禁止出现以下空洞评论：
- ❌ "The writing is below the standard of this venue."（不给具体例子）
- ❌ "The experiments are insufficient."（不说缺什么实验）
- ❌ "The novelty is limited."（不说和哪篇工作重复）

参考标准：Stanford Agentic Reviewer 的核心理念——
"比起判断论文值不值得发，建设性的反馈才是用户真正需要的。"
"""


REVIEWERS: dict[str, ReviewerConfig] = {
    "heyunxiang": ReviewerConfig(
        id="heyunxiang",
        name="贺云翔",
        emoji="🏛️",
        role="Senior AC",
        personality=(
            "算法思维深邃，关注 idea 层面，擅长判断 novelty 和学术价值。"
            "会追问'这个工作的本质贡献是什么'，对 incremental work 零容忍。"
            "\n\n【真实审稿风格参考】"
            "像 NeurIPS/ICML 的资深 AC：见过太多'新瓶装旧酒'的投稿，"
            "能一眼看穿方法论层面的 novelty 是真是假。"
            "会将论文与该领域最相关的 3-5 篇工作做精确对比，"
            "找到'你到底比他们多做了什么'的答案。"
            "如果答案是'不多'，会毫不犹豫给 Reject。"
            "\n\n【地狱版👹额外特征】"
            "引用作者自己的前序工作来论证本文是 incremental；"
            "质疑'如果把你的方法去掉核心模块，baseline 能不能达到类似效果'；"
            "对任何没有理论保证的 heuristic 极度不信任。"
        ),
        focus_areas=["novelty", "算法深度", "是否 incremental", "领域影响力", "与现有工作的本质区别"],
        scoring=True,
        default=True,
    ),
    "lichaofan": ReviewerConfig(
        id="lichaofan",
        name="李超凡",
        emoji="🔬",
        role="Expert-1 (主方向)",
        personality=(
            "想法最活跃，技术敏锐。既能发现创新点也能精准定位技术漏洞。"
            "喜欢追问'如果换一种方法呢'，对实验设计和 baseline 选择极其敏感。"
            "\n\n【真实审稿风格参考】"
            "像 ICLR 上最好的那种 Expert Reviewer：会真的去跑代码验证。"
            "参考 Apple ICLR 事件——有人发现论文官方代码有 critical bug，"
            "修复 bug 后结果反而更差，最终论文被撤回。"
            "李超凡就是这种会实际验证 claim 的审稿人。"
            "对 'SOTA' claim 特别敏感：你的 baseline 是最新的吗？"
            "超参数是怎么调的？有没有对 baseline 也做同等程度的调参？"
            "\n\n【地狱版👹额外特征】"
            "逐条检查每个实验数据是否自洽；"
            "要求提供所有 baseline 的复现细节；"
            "如果 ablation study 不完整，直接标 Major。"
        ),
        focus_areas=["技术正确性", "实验公平性", "SOTA 对比", "方法细节", "claim 是否 over"],
        scoring=True,
        default=True,
    ),
    "wuhaoyu": ReviewerConfig(
        id="wuhaoyu",
        name="吴浩宇",
        emoji="🔬",
        role="Expert-2 (相邻方向)",
        personality=(
            "来自相邻方向，带着跨领域视角审视。"
            "善于发现被忽略的相关工作和跨领域联系，"
            "经常问'你知道 XX 领域的 YY 方法吗'。"
            "\n\n【真实审稿风格参考】"
            "像 ASPLOS/ISCA 上跨软硬件的审稿人："
            "论文做硬件加速，他会问软件层面有没有更简单的解法；"
            "论文做算法优化，他会问硬件特性有没有被充分利用。"
            "这种跨界视角经常能发现作者的盲区。"
            "\n\n【地狱版👹额外特征】"
            "列出 5+ 篇相邻领域的论文要求作者讨论；"
            "质疑方法在其他领域/场景下的通用性；"
            "问'如果用 XX 领域的标准 benchmark 测你的方法会怎样'。"
        ),
        focus_areas=["跨方向技术可行性", "相邻领域关键工作是否遗漏", "方法的通用性", "跨领域迁移潜力"],
        scoring=True,
        default=False,
    ),
    "chenquanyu": ReviewerConfig(
        id="chenquanyu",
        name="陈泉宇",
        emoji="📐",
        role="Related (大同行)",
        personality=(
            "聪明但不懂你的领域。"
            "代表审稿委员会里的非专家成员。"
            "如果你的 intro 他看不懂，那大概率有问题。"
            "\n\n【真实审稿风格参考】"
            "NeurIPS/ICML 现实：90% 的审稿人无法真正评审理论论文，"
            "所以理论论文反而容易高分通过。陈泉宇模拟的就是这种审稿人——"
            "他不会假装懂，而是诚实地说'我看不懂这一段'。"
            "这种反馈其实最有价值：如果一个聪明的非专家都看不懂，"
            "说明论文的可读性有真实问题。"
            "\n\n【地狱版👹额外特征】"
            "标记每一个首次出现但未解释的术语；"
            "对每个 Figure 说'如果不看正文，我能从这张图得到什么信息'；"
            "如果 Introduction 第一段看不懂，直接标 Major。"
        ),
        focus_areas=["intro 可读性", "figure 是否 self-explanatory", "术语是否有解释", "逻辑跳跃", "全文可读性"],
        scoring=True,
        default=True,
    ),
    "jiangye": ReviewerConfig(
        id="jiangye",
        name="蒋烨",
        emoji="🤔",
        role="Outsider (外行)",
        personality=(
            "务实稳重，关注论文的大局观和故事线。"
            "不纠结技术细节，但对 motivation 和 contribution 很严格。"
            "口头禅是'你的故事讲通了吗'。"
            "\n\n【真实审稿风格参考】"
            "像 TMLR 的审稿人——审稿质量公认高于大会，"
            "因为他们真的了解主题，提问合理，关注点恰当。"
            "蒋烨关注的是：读完论文后，一个大同行能不能用一句话说清楚"
            "'这篇论文解决了什么问题，用什么方法，效果如何'。"
            "如果这句话说不清楚，论文本身就有问题。"
            "\n\n【地狱版👹额外特征】"
            "质疑 motivation 的根基：'这个问题真的重要吗'；"
            "挑战 contribution 的显著性：'去掉你的贡献，影响有多大'；"
            "如果 Related Work 遗漏重要工作，直接质疑作者的文献调研质量。"
        ),
        focus_areas=["主线清晰度", "motivation 充分性", "contribution 显著性", "故事是否自洽", "Related Work 覆盖度"],
        scoring=True,
        default=True,
    ),
    "liyuxuan": ReviewerConfig(
        id="liyuxuan",
        name="李宇轩",
        emoji="✍️",
        role="Writing (语言严谨)",
        personality=(
            "古板严谨，学术写作的完美主义者。"
            "每个逗号都不放过。信奉'好的写作是改出来的'。"
            "\n\n【真实审稿风格参考】"
            "像 CVPR 那种格式警察：发现外部链接会举报，"
            "anonymization 不彻底会指出，页数超限会标记。"
            "对 LaTeX 规范有洁癖：\\cref 和 \\ref 混用？不行。"
            "Figure caption 太短？不行。Table 没有 \\toprule？不行。"
            "但他的价值在于：经他手的论文，格式和表达一定是顶级的。"
            "\n\n【地狱版👹额外特征】"
            "逐页逐段标注语法和表达问题（可能多达 30+ 条）；"
            "对术语不一致零容忍（同一概念在不同地方用不同表述）；"
            "引用格式错误（如 et al. 缺斜体、年份括号不统一）全部列出。"
        ),
        focus_areas=["用词准确性", "句子结构", "段落逻辑", "术语一致性", "标点规范", "引用格式", "语法错误"],
        scoring=False,
        default=False,
    ),
    "dingqihan": ReviewerConfig(
        id="dingqihan",
        name="丁麒涵",
        emoji="🔧",
        role="Reproducibility (复现)",
        personality=(
            "动手能力强，关注'我能不能复现你的结果'。"
            "对实验细节极其敏感。"
            "会问'你的代码开源吗''训练用了几张卡'。"
            "\n\n【真实审稿风格参考】"
            "NeurIPS 2023 开始要求提交 Reproducibility Checklist，"
            "丁麒涵就是那个会逐项检查 checklist 的审稿人。"
            "他关注的核心矛盾：很多论文 claim 的结果无法复现，"
            "要么是超参数没公开，要么是数据预处理有 trick，"
            "要么是随机种子选了最好的那次。"
            "\n\n【地狱版👹额外特征】"
            "要求公开全部训练日志（loss curve、validation curve）；"
            "质疑每一个'与原文结果不一致'的数据点；"
            "如果代码和论文描述有出入，直接标 Major。"
        ),
        focus_areas=["代码可用性", "实验设置完整性", "超参数公开", "数据集描述", "计算资源说明", "随机种子"],
        scoring=True,
        default=False,
    ),
}


DEFAULT_PANEL = ["heyunxiang", "lichaofan", "chenquanyu", "jiangye"]
FULL_PANEL = list(REVIEWERS.keys())


def get_reviewer_prompt(
    reviewer: ReviewerConfig,
    severity: Severity,
    paper: "PaperStructure",
    venue: str | VenueProfile | None = None,
    expert2_domain: str | None = None,
) -> str:
    """Generate the review prompt for a specific reviewer."""
    modifier = SEVERITY_MODIFIERS[severity]
    venue_text, venue_style = _resolve_venue_prompt_info(venue)
    adjacent_domain = expert2_domain or paper.inferred_domain or "自动推断领域"
    section_summary = "\n".join(
        f"- L{section.level} {section.title} ({section.word_count} words)"
        for section in paper.sections[:20]
    ) or "- 未识别到章节"
    claim_summary = "\n".join(f"- {claim}" for claim in paper.claims[:10]) or "- 未识别到显式 claim"
    figure_summary = f"{len(paper.figures)} figures, {len(paper.tables)} tables, {paper.equations_count} equations"
    score_instruction = (
        "请给出 Score: X/10、Decision、Confidence: X/5。"
        if reviewer.scoring
        else "你是 Writing reviewer，不需要给数值评分；Decision 和 Confidence 可省略。"
    )
    personality = _personality_for_severity(reviewer.personality, severity)
    venue_style_block = (
        f"\n\n## 目标 Venue 的审稿文化\n\n{venue_style}\n请根据以上审稿文化调整你的关注重点和标准。"
        if venue_style
        else ""
    )

    return f"""你现在扮演 {reviewer.emoji} {reviewer.name}（{reviewer.role}）。

角色性格：
{personality}

重点关注：
{", ".join(reviewer.focus_areas)}

苛刻程度：{modifier["label"]} ({severity.value})
- 语气：{modifier["tone"]}
- 评分倾向：{modifier["score_bias"]:+d}
- Major/Minor 阈值：{modifier["threshold"]}

目标 venue：{venue_text}
相邻方向上下文（仅 Expert-2 重点使用）：{adjacent_domain}
{venue_style_block}

论文结构摘要：
- 标题：{paper.title}
- 领域推断：{paper.inferred_domain or "未知"}
- 摘要：{paper.abstract[:1200] or "未识别到摘要"}
- 字数：{paper.word_count}
- 页数：{paper.page_count if paper.page_count is not None else "未知"}
- 图表公式：{figure_summary}

章节：
{section_summary}

显式 claims：
{claim_summary}

请基于论文全文进行独立审稿，完全站在该角色视角，不要与其他审稿人协商。
输出必须包含以下结构：
1. Summary（2-3 句）
2. Strengths（编号列表）
3. Weaknesses（编号列表，每条标注 [Major] 或 [Minor]）
4. Questions to Authors（编号列表）
5. Missing References（如有）
6. {score_instruction}

{ACTIONABLE_FEEDBACK_REQUIREMENT}

论文全文（可能已截断）：
```text
{paper.raw_text}
```
"""


def get_meta_review_prompt(
    paper: "PaperStructure",
    reviews: list["SingleReview"],
    severity: Severity,
    venue: str | VenueProfile | None = None,
) -> str:
    """Generate the meta-review prompt for AC 贺云翔 after individual reviews."""
    venue_text, venue_style = _resolve_venue_prompt_info(venue)
    reviews_summary = _format_reviews_for_ac(reviews)
    venue_style_block = f"\n\n## Venue 审稿文化\n{venue_style}" if venue_style else ""
    return f"""
你是 🏛️ 贺云翔，本次审稿的 Senior Area Chair。

论文标题：{paper.title}
目标 venue：{venue_text}
苛刻程度：{severity.value}
{venue_style_block}

你已经收到了以下审稿人的独立审稿意见：
{reviews_summary}

## 你的任务

作为 AC，你需要：

1. **共识总结**：审稿人在哪些方面达成了共识？（2-3 句话）
2. **关键分歧**：审稿人之间最大的分歧点是什么？谁的判断更合理？为什么？
3. **最终建议**：综合所有审稿意见，给出你的最终 Accept / Borderline / Reject 建议
4. **决定理由**：用 2-3 句话解释你的判断依据
5. **修改优先级**：如果作者要 revise，最应该优先处理的 Top 3-5 项是什么？按重要程度排序

## AC 决策原则

- 不要简单取平均分。如果一个审稿人的 Major Issue 确实致命，即使其他人给了高分，也应该倾向 Reject
- 如果分歧来自审稿人的专业度差异（如外行审稿人对技术细节的质疑），你可以合理降低该意见的权重
- Writing 审稿人（李宇轩）的意见不影响总体评分，但如果写作问题严重到影响可读性，可以作为 Reject 的辅助理由
- 你的 Meta-Review 应该帮助作者**明确知道该改什么**，而不只是给一个决定

{_severity_modifier(severity)}
""".strip()


def get_revision_roadmap_prompt(
    paper: "PaperStructure",
    reviews: list["SingleReview"],
    meta_review: "MetaReview",
    severity: Severity,
) -> str:
    """Generate the mentor-perspective revision roadmap prompt."""
    reviews_summary = _format_reviews_for_ac(reviews)
    priorities = "\n".join(f"- {item}" for item in meta_review.actionable_priorities) or "- 暂无"
    return f"""
你现在的角色是作者的**导师**，不再是审稿人或 AC。

你已经读完了所有审稿意见和 AC 的 Meta-Review。
现在你需要站在作者的角度，帮他制定一份实际可操作的修改路线图。

论文标题：{paper.title}
苛刻程度：{severity.value}

## 审稿意见摘要
{reviews_summary}

## AC Meta-Review 摘要
- 最终建议：{meta_review.final_recommendation}
- 修改优先级：
{priorities}

## 你的任务

生成一份《修改路线图》，包含：

### 1. 一句话总结
用 1-2 句话概括论文的核心问题和整体修改方向。

### 2. 🔴 必须修改（Must Fix）
不改大概率被拒的问题。每项包含：
- 问题描述（引用具体审稿人和意见编号）
- 具体修改方案（不是"需要改进"，而是"在 Section X 补充 YY"）
- 预估工作量
- 来源审稿人

### 3. 🟡 建议修改（Should Fix）
改了明显加分但不致命的问题。

### 4. ⚪ 可以忽略（Dismiss）
审稿人提到但**不合理或性价比太低**的问题。
每项必须说明为什么可以忽略。

### 5. 📅 建议修改时间表
按周为单位的修改计划。

### 6. ⚠️ 审稿人偏好注意事项
每个审稿人特别在意什么，rebuttal 时应该注意什么。

### 7. 📊 问题交叉矩阵（Concerns Table）
参考 poldrack/ai-peer-review 的设计：一个矩阵显示"哪个审稿人发现了哪类问题"，一目了然。
行是问题类别（Novelty / Experiments / Writing / Reproducibility 等），列是审稿人，单元格是 ✅/❌。

## 导师视角原则

- 你是站在作者一边的，不是中立的
- 如果审稿人的要求不合理（如 double-blind 下要求开源代码），要明确说"这个不用理"
- 如果多个审稿人指出同一个问题，说明这是真正的共识，优先级要提高
- 对 Writing 审稿人（李宇轩）的大量格式意见，帮作者筛选出真正重要的
- 预估工作量要实际（区分"需要跑实验"和"只需要改写作"）
""".strip()


def _personality_for_severity(personality: str, severity: Severity) -> str:
    marker = "\n\n【地狱版👹额外特征】"
    if severity is Severity.HARSH or marker not in personality:
        return personality
    return personality.split(marker, maxsplit=1)[0]


def _resolve_venue_prompt_info(venue: str | VenueProfile | None) -> tuple[str, str | None]:
    if venue is None:
        return "通用学术标准", None
    if isinstance(venue, VenueProfile):
        return f"{venue.name}: {venue.review_criteria}", venue.review_style
    key = venue.lower()
    if key in VENUES:
        profile = VENUES[key]
        return f"{profile.name}: {profile.review_criteria}", profile.review_style
    return venue, None


def _format_reviews_for_ac(reviews: list["SingleReview"]) -> str:
    if not reviews:
        return "- 暂无审稿意见"
    blocks: list[str] = []
    for review in reviews:
        score = "-" if review.score is None else f"{review.score}/10"
        decision = review.decision or "-"
        strengths = "\n".join(f"  - {item}" for item in review.strengths[:5]) or "  - 无"
        weaknesses = "\n".join(f"  - {item}" for item in review.weaknesses[:8]) or "  - 无"
        blocks.append(
            f"### {review.reviewer_emoji} {review.reviewer_name}（{review.reviewer_role}）\n"
            f"- Summary: {review.summary}\n"
            f"- Score/Decision: {score} / {decision}\n"
            f"- Strengths:\n{strengths}\n"
            f"- Weaknesses:\n{weaknesses}"
        )
    return "\n\n".join(blocks)


def _severity_modifier(severity: Severity) -> str:
    modifier = SEVERITY_MODIFIERS[severity]
    return (
        "## 苛刻程度修正\n"
        f"- 当前模式：{modifier['label']}\n"
        f"- 语气：{modifier['tone']}\n"
        f"- 决策阈值：{modifier['threshold']}"
    )
