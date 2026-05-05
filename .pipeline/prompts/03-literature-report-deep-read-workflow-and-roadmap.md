# M04 - Literature Report Deep-Read Workflow and Roadmap

## Objective

Redesign the literature review report and deep-read workflow, then synthesize M01-M03 into a long-term research OS / PhD workflow roadmap with near-term implementation candidates.

## 需求

- Review current literature search/report output and compare it with user needs for unfamiliar-field onboarding and deeper paper understanding.
- Lightly research search and review tools such as Elicit, Semantic Scholar, Connected Papers, ResearchRabbit, and related systems for useful patterns.
- Design an improved research report format that may include:
  - field familiarity question
  - foundational concept primer
  - terminology and concept map
  - paper tiers
  - methods/datasets/claims evidence matrix
  - recommended reading order
  - uncertainty and metadata quality notes
- Connect report format to graded full-text reading from M03.
- Synthesize all previous reports into a long-term product and architecture roadmap.

## Boundaries

- In scope: report design, search workflow redesign, unfamiliar-field guidance, roadmap.
- In scope: near-term, mid-term, and long-term milestones for future Cycles.
- Out of scope: implementing report generator changes in this Cycle.

## Non-Goals

- Do not turn the roadmap into vague aspirations only.
- Do not ignore migration compatibility with current CLI/Skill users.
- Do not overfit to one benchmark paper or one research field.

## 预期测试

- The final report includes a concrete before/after report outline.
- The roadmap distinguishes quick wins, product architecture work, and long-horizon research OS ideas.
- The roadmap references evidence from M01-M03.
- The report proposes a next implementation Cycle with reviewable milestones.

## Validation Commands

- `uv run hypo-research search --help`
- Read current output/report modules and README examples.
- Review M01-M03 report files before synthesis.

## Evidence

- Write `.pipeline/reports/03-literature-report-deep-read-workflow-and-roadmap.report.md`.
- Include a final consolidated roadmap section.
- Include next-Cycle candidate milestones.

## Human QA

- User reviews the roadmap for product taste and prioritization.
- User chooses which next implementation Cycle to start.

## 预期产出

- `.pipeline/reports/03-literature-report-deep-read-workflow-and-roadmap.report.md`
- Improved research report outline.
- Research OS / PhD workflow roadmap.
- Candidate implementation Cycle plan.
