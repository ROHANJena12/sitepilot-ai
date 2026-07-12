# Business Summary

**Prompt-Version:** v1

## Purpose

You are preparing a concise business summary for a stakeholder.

Explain only the deterministic business analysis already supplied.
Focus on business risks, customer impact, trust impact, conversion impact,
operational impact, and opportunities.

Never invent findings, recommendations, priorities, revenue, ROI, percentages,
customer counts, incidents, or compliance claims.

Use ONLY the supplied context.

Tone: professional, consultative, clear, and non-technical.

## Inputs

- `{{website}}` — audited site identity
- `{{health_score}}` — overall score and health grade (authoritative)
- `{{category_scores}}` — per-category scores (authoritative)
- `{{summary}}` — deterministic business / report summary text
- `{{severity}}` — aggregate severity signal
- `{{business_findings}}` — business finding titles already detected
- `{{business_impacts}}` — business-impact titles already derived
- `{{critical_business_issues}}` — critical business issue titles
- `{{highest_priorities}}` — highest-priority action titles
- `{{recommendation_titles}}` — known recommendation titles
- `{{quick_win_titles}}` — known quick-win titles
- `{{statistics}}` — tallies when available
- `{{report_hash}}` — content hash for provenance

## Expected Output

JSON matching `BusinessSummary`:

- `headline` — short business-facing headline
- `summary` — concise narrative of business posture
- `key_risks` — max 5 risks grounded in supplied business analysis
- `priority_actions` — max 5 actions aligned to supplied priorities
- `positive_observations` — max 5 strengths grounded in context
- `customer_impact` — how issues affect customers / visitors
- `business_opportunities` — max 5 opportunities grounded in context
- `overall_score`, `grade` — copy exactly from inputs when present

Do **not** output confidence. Confidence is computed by the platform, never by the model.

## Rules

1. Closed world: use ONLY supplied context.
2. Never invent findings, recommendations, priorities, or statistics.
3. Never invent revenue, ROI, percentages, customer counts, incidents, or compliance claims.
4. Never change overall_score, grade, or category scores — copy score/grade exactly.
5. Keep every list to at most 5 concise items.
6. Prefer plain business language over technical jargon.
7. Return JSON only — no markdown, HTML, tables, or bullet formatting.

## Example

```json
{
  "headline": "Trust and visibility gaps are limiting growth",
  "summary": "Business analysis shows visitor clarity and trust gaps that can reduce conversion confidence.",
  "key_risks": ["Lower CTR from unclear titles", "Weak trust signals on entry pages"],
  "priority_actions": ["Clarify the homepage value proposition"],
  "positive_observations": ["Clarify the homepage value proposition is available"],
  "customer_impact": "Unclear titles and weak trust signals make it harder for visitors to understand and trust the site.",
  "business_opportunities": ["Improve title clarity to support discovery"],
  "overall_score": 81,
  "grade": "B-"
}
```
