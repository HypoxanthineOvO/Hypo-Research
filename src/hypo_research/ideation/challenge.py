"""Socratic challenge workflow for research ideas."""

from __future__ import annotations

from dataclasses import replace

from hypo_research.ideation.models import ChallengeQuestion, ChallengeResult, ChallengeSeverity, ResearchIdea
from hypo_research.ideation.scoring import score_idea
from hypo_research.review.literature import search_literature


CHALLENGE_DIMENSIONS = {
    "novelty": ("新颖性挑战", "这个 idea 真的新吗？"),
    "feasibility": ("可行性挑战", "这个 idea 能做出来吗？"),
    "significance": ("重要性挑战", "这个 idea 值得做吗？"),
    "methodology": ("方法论挑战", "方法选择合理吗？"),
    "assumption": ("假设挑战", "隐含假设合理吗？"),
}

SEVERITY_PERSONAS = {
    "gentle": "建设性的科研顾问，用温和的方式提出问题并给出改进建议",
    "standard": "严格但公平的科研导师，不客气但有道理",
    "harsh": "极其严厉的答辩委员会主席（别名“娄萌萌”），会追问“你到底想解决什么问题”和“这个工作的 novelty 在哪里”。",
}


def challenge_idea(
    idea: ResearchIdea,
    severity: ChallengeSeverity = ChallengeSeverity.HARSH,
) -> ChallengeResult:
    """Challenge an idea across novelty, feasibility, significance, methodology, and assumptions."""
    literature = _find_collision_work(idea)
    similar_work = literature[0]["title"] if literature else (idea.related_papers[0] if idea.related_papers else None)
    questions = _build_questions(idea, severity, similar_work)
    fatal_risks = _fatal_risks(idea, similar_work)
    reinforcement_plan = [
        "用最近 3 年的直接竞争工作重写 novelty 边界。",
        "先跑一个最小可行实验，确认主效应存在后再扩展实验矩阵。",
        "准备强 baseline、简单 baseline 和 ablation，避免贡献被认为只是工程调参。",
    ]
    adjusted_idea = replace(
        idea,
        risk_factors=list(dict.fromkeys([*idea.risk_factors, *fatal_risks])),
        related_papers=list(dict.fromkeys([*idea.related_papers, *([similar_work] if similar_work else [])])),
    )
    score_after = score_idea(adjusted_idea, literature)
    verdict = _verdict(score_after.total_score, fatal_risks)
    return ChallengeResult(
        idea_title=idea.title,
        severity=severity,
        questions=questions,
        fatal_risks=fatal_risks[:3],
        reinforcement_plan=reinforcement_plan,
        verdict=verdict,
        score_after_challenge=score_after,
    )


def build_challenge_prompt(idea: ResearchIdea, severity: ChallengeSeverity) -> str:
    """Build challenge prompt for tests and CLI traceability."""
    return (
        f"你是一个{SEVERITY_PERSONAS[severity.value]}。\n"
        f"标题：{idea.title}\n"
        f"研究问题：{idea.research_question}\n"
        "请从新颖性、可行性、重要性、方法论、假设五个维度进行苏格拉底式拷打。"
    )


def _build_questions(
    idea: ResearchIdea,
    severity: ChallengeSeverity,
    similar_work: str | None,
) -> list[ChallengeQuestion]:
    level = "critical" if severity == ChallengeSeverity.HARSH else ("major" if severity == ChallengeSeverity.STANDARD else "minor")
    prefix = {
        ChallengeSeverity.GENTLE: "请你进一步说明",
        ChallengeSeverity.STANDARD: "你需要正面回答",
        ChallengeSeverity.HARSH: "你到底想解决什么问题？",
    }[severity]
    templates = {
        "novelty": f"{prefix}：你和 {similar_work or '已有最相近工作'} 的区别到底在哪里？如果只是换数据集，这不叫 novelty。",
        "feasibility": f"{prefix}：实验需要多少计算资源和数据标注？如果资源不够，你的 plan B 是什么？",
        "significance": f"{prefix}：谁会 care 这个结果？做出来以后对领域判断有什么改变？",
        "methodology": f"{prefix}：为什么用当前方法而不是更简单的 baseline？你的实验能排除混淆因素吗？",
        "assumption": f"{prefix}：你的方法隐含了哪些数据分布和任务假设？边界条件下会不会失效？",
    }
    questions: list[ChallengeQuestion] = []
    for dimension, (name, context) in CHALLENGE_DIMENSIONS.items():
        questions.append(
            ChallengeQuestion(
                dimension=dimension,
                question=templates[dimension],
                severity=level,
                context=f"{name}：{context}",
                similar_work=similar_work if dimension == "novelty" else None,
                suggested_response=_suggested_response(dimension),
            )
        )
    return questions


def _suggested_response(dimension: str) -> str:
    responses = {
        "novelty": "列出最相近工作的 claim、方法和实验设定，并用表格说明你的不可替代差异。",
        "feasibility": "给出最小实验、资源预算和失败时可降级的实验版本。",
        "significance": "明确受影响的任务、用户或理论判断，避免只汇报小幅指标提升。",
        "methodology": "补充简单 baseline、强 baseline、替代方法和关键 ablation。",
        "assumption": "把假设写成可检验命题，并设计边界条件实验。",
    }
    return responses[dimension]


def _find_collision_work(idea: ResearchIdea) -> list[dict]:
    try:
        context = search_literature(idea.title, idea.research_question, max_results=3, queries=[idea.title])
    except Exception:
        return []
    if context is None:
        return []
    return [{"title": ref.title, "abstract": ref.abstract_snippet, "year": ref.year} for ref in context.references]


def _fatal_risks(idea: ResearchIdea, similar_work: str | None) -> list[str]:
    risks = []
    if similar_work:
        risks.append(f"可能与已有工作“{similar_work}”撞车，novelty 边界必须重写。")
    risks.extend(
        [
            "核心贡献可能被审稿人认为只是 incremental engineering。",
            "如果只在单一数据集有效，significance 会被严重削弱。",
        ]
    )
    return risks[:3]


def _verdict(total_score: float, fatal_risks: list[str]) -> str:
    if total_score >= 0.68 and len(fatal_risks) <= 2:
        return "值得做"
    if total_score >= 0.45:
        return "需要重大修改"
    return "建议放弃"
