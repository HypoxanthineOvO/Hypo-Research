"""Rebuttal generation for reviewer comments."""

from __future__ import annotations

import re
from pathlib import Path

from hypo_research.project.models import RebuttalResponse, RebuttalResult, ReviewComment


REBUTTAL_PROMPT = """
你是一个学术 rebuttal 写作专家。请逐条分析审稿意见，分类、制定回复策略，并生成礼貌、专业、简洁的 rebuttal letter。
"""


def generate_rebuttal(
    review_text: str,
    paper_draft: str | None = None,
    experiment_results: str | None = None,
    project_context: dict | None = None,
) -> RebuttalResult:
    """Generate a structured rebuttal from review text."""
    text = _read_if_file(review_text)
    draft = _read_if_file(paper_draft) if paper_draft else None
    experiments = _read_if_file(experiment_results) if experiment_results else None
    comments = parse_reviews(text)
    responses = [build_response(comment, draft, experiments, project_context) for comment in comments]
    additional = [item.additional_experiment for item in responses if item.additional_experiment]
    paper_title = _infer_paper_title(draft, project_context)
    venue = _infer_venue(project_context)
    return RebuttalResult(
        paper_title=paper_title,
        venue=venue,
        reviews=comments,
        responses=responses,
        summary_of_changes=_summary_of_changes(responses),
        additional_experiments=additional,
        rebuttal_letter=_render_rebuttal_letter(comments, responses),
        tone="respectful",
    )


def parse_reviews(review_text: str) -> list[ReviewComment]:
    """Split raw review text into individual comments."""
    blocks = _reviewer_blocks(review_text)
    comments: list[ReviewComment] = []
    counter = 1
    for reviewer, content in blocks:
        items = _split_comment_items(content)
        for item in items:
            classification = classify_comment(item)
            comments.append(
                ReviewComment(
                    id=f"c{counter:03d}",
                    reviewer=reviewer,
                    category=_category_for(item),
                    content=item,
                    classification=classification,
                )
            )
            counter += 1
    if not comments and review_text.strip():
        comments.append(
            ReviewComment(
                id="c001",
                reviewer="Reviewer 1",
                category=_category_for(review_text),
                content=review_text.strip(),
                classification=classify_comment(review_text),
            )
        )
    return comments


def classify_comment(content: str) -> str:
    """Classify one reviewer comment."""
    lower = content.lower()
    if any(word in lower for word in ["unclear", "confusing", "clarify"]) or "不清楚" in content or "误解" in content:
        return "misunderstanding"
    if any(word in lower for word in ["wrong", "incorrect", "not true"]) or "错误" in content:
        return "factual_error"
    if any(word in lower for word in ["experiment", "baseline", "ablation", "evaluation"]) or any(word in content for word in ["实验", "baseline", "消融"]):
        return "valid_concern"
    if any(word in lower for word in ["excellent", "strong contribution", "well-written", "good"]) or "优点" in content:
        return "praise"
    if any(word in lower for word in ["suggest", "would be nice", "consider"]) or "建议" in content:
        return "suggestion"
    return "valid_concern"


def choose_strategy(classification: str) -> str:
    """Choose response strategy."""
    return {
        "factual_error": "correct",
        "misunderstanding": "clarify",
        "valid_concern": "supplement",
        "suggestion": "acknowledge",
        "praise": "thank",
    }.get(classification, "acknowledge")


def build_response(
    comment: ReviewComment,
    paper_draft: str | None = None,
    experiment_results: str | None = None,
    project_context: dict | None = None,
) -> RebuttalResponse:
    """Build a response for one comment."""
    strategy = choose_strategy(comment.classification)
    additional = None
    changes = []
    if strategy == "thank":
        response = "We thank the reviewer for the positive feedback and will keep the presentation concise in the revision."
        changes.append("保留并强化审稿人认可的贡献表述。")
    elif strategy == "correct":
        response = "We respectfully clarify that this point is already addressed in the paper, and we will make the relevant statement more explicit in the revision."
        changes.append("在相关段落补充更明确的事实说明。")
    elif strategy == "clarify":
        response = "We agree that the current writing may have caused confusion. We will revise the explanation and add a clearer definition before the method description."
        changes.append("重写问题定义和方法前置说明。")
    elif strategy == "supplement":
        response = "We agree this is an important concern. We will add a focused comparison and report the result in the revised experiment section."
        additional = "补充最小化 baseline/ablation 实验，优先验证审稿人指出的核心变量。"
        changes.append("增加补充实验和对应分析。")
    else:
        response = "We appreciate the suggestion and will incorporate it where it improves clarity without changing the main claim."
        changes.append("按建议补充说明或限制讨论。")
    if experiment_results:
        response += " We will also cite the additional experimental evidence now available."
    if project_context and project_context.get("meetings", {}).get("key_decisions"):
        response += " This response is consistent with the project decisions recorded during prior discussions."
    return RebuttalResponse(
        comment_id=comment.id,
        strategy=strategy,
        response=response,
        paper_changes=changes,
        additional_experiment=additional,
    )


def _reviewer_blocks(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"(Reviewer\s*\d+|R\d+)\s*[:：]?", re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if not matches:
        return [("Reviewer 1", text)]
    blocks = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        reviewer = match.group(1)
        if re.fullmatch(r"R\d+", reviewer, flags=re.IGNORECASE):
            reviewer = f"Reviewer {reviewer[1:]}"
        blocks.append((reviewer, text[start:end].strip()))
    return blocks


def _split_comment_items(content: str) -> list[str]:
    lines = [line.strip(" -\t") for line in content.splitlines() if line.strip()]
    items = [re.sub(r"^\d+[\).\s]+", "", line) for line in lines]
    return [item for item in items if len(item) > 3]


def _category_for(content: str) -> str:
    lower = content.lower()
    if "typo" in lower or "拼写" in content:
        return "typo"
    if "?" in content or "？" in content:
        return "question"
    if any(word in lower for word in ["major", "baseline", "experiment"]) or any(word in content for word in ["实验", "重大"]):
        return "major"
    return "minor"


def _summary_of_changes(responses: list[RebuttalResponse]) -> str:
    changes = [change for response in responses for change in response.paper_changes]
    return "；".join(dict.fromkeys(changes)) or "无需实质性修改。"


def _render_rebuttal_letter(comments: list[ReviewComment], responses: list[RebuttalResponse]) -> str:
    response_map = {response.comment_id: response for response in responses}
    lines = [
        "Dear Area Chair and Reviewers,",
        "",
        "We thank the reviewers for their careful reading and constructive feedback. We respond to each point below.",
        "",
    ]
    for comment in comments:
        response = response_map[comment.id]
        lines.extend(
            [
                f"**{comment.reviewer}, Comment {comment.id}.** {comment.content}",
                "",
                f"**Response.** {response.response}",
                "",
            ]
        )
    lines.extend(["Sincerely,", "The Authors"])
    return "\n".join(lines)


def _infer_paper_title(paper_draft: str | None, project_context: dict | None) -> str:
    if project_context and project_context.get("paper_title"):
        return str(project_context["paper_title"])
    if paper_draft:
        for line in paper_draft.splitlines():
            if line.strip():
                return line.strip("# ")[:120]
    return "Untitled Paper"


def _infer_venue(project_context: dict | None) -> str:
    if project_context and project_context.get("venue"):
        return str(project_context["venue"])
    return "Unknown Venue"


def _read_if_file(value: str | None) -> str:
    if value is None:
        return ""
    path = Path(value)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"[二进制或非文本文件：{path.as_posix()}]"
    return value
