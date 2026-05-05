# M01 - Positioning and Hypo-Workflow Relationship Review

## Objective

Decide which relationship model should guide Hypo-Research and Hypo-Workflow: merge into Hypo-Workflow, ship as a Hypo-Workflow plugin, depend on Hypo-Workflow as a lower layer, or remain independent.

## 需求

- Read the current Hypo-Research architecture baseline and relevant Hypo-Workflow architecture/config concepts.
- Compare the four relationship presets:
  - merge Hypo-Research into Hypo-Workflow
  - keep Hypo-Research as a Hypo-Workflow plugin or vertical package
  - keep Hypo-Research independent but depend on Hypo-Workflow state/project/report primitives
  - keep the projects separate except for documentation/instruction-level integration
- Treat "pollution for non-research Hypo-Workflow users" as a high-priority decision factor.
- Evaluate UX consistency, code reuse, maintenance cost, migration risk, research workflow expressiveness, plugin ecosystem fit, and future extensibility.

## Boundaries

- In scope: repository reading, architecture comparison, decision matrix, strategic recommendation.
- In scope: identifying which Hypo-Research concepts could generalize into Hypo-Workflow and which should stay vertical.
- Out of scope: code migration, package restructuring, plugin implementation.

## Non-Goals

- Do not make irreversible source changes.
- Do not assume Hypo-Workflow should become research-specific.
- Do not produce a single answer without explaining rejected alternatives.

## 预期测试

- The report includes a decision matrix covering all four presets.
- The recommendation explicitly addresses non-research user pollution risk.
- The report separates immediate recommendation from long-term optional convergence.
- The report identifies concrete reusable primitives, if any.

## Validation Commands

- `find .pipeline/architecture -maxdepth 1 -type f -print | sort`
- `find src/hypo_research -maxdepth 2 -type d | sort`
- Read relevant Hypo-Workflow skill/config/architecture files from the installed skill directory as needed.

## Evidence

- Write `.pipeline/reports/00-positioning-and-hypo-workflow-relationship-review.report.md`.
- Include file references and source observations for each major conclusion.
- Record unanswered questions and assumptions explicitly.

## Human QA

- User reviews whether the preferred relationship model matches product instinct.
- User may override weighting if the pollution/maintenance tradeoff feels wrong.

## 预期产出

- `.pipeline/reports/00-positioning-and-hypo-workflow-relationship-review.report.md`
- A recommended relationship model and fallback model.
- A list of follow-up architecture decisions for the final roadmap.
