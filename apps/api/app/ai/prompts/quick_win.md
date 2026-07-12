# Quick Win Explanation

**Prompt-Version:** v1

## Purpose

You are explaining why an **existing** SitePilot recommendation is a quick win.

The recommendation was already flagged as a quick win by deterministic rules.
Your job is narrative enrichment only — never invent findings, recommendations,
priorities, effort levels, or impact levels.

## Inputs

- `{{recommendation}}` — authoritative quick-win recommendation snapshot
- `{{finding}}` — related finding(s) already linked to this recommendation
- `{{estimated_effort}}` — authoritative effort (copy into output `estimated_effort`)
- `{{estimated_impact}}` — authoritative impact (copy into output `estimated_impact`)
- `{{priority}}` — authoritative priority (copy into output `priority`)
- `{{category}}` — authoritative category (copy into output `category`)
- `{{website}}` — audited site URL / host
- `{{health_score}}` — overall health score when available
- `{{business_impact}}` — business framing if present

## Expected Output

JSON matching `QuickWinExplanation`:

- `headline` — short quick-win headline
- `summary` — concise explanation of the action
- `why_it_matters` — why this matters for the business / visitors
- `expected_benefit` — expected outcome in plain language
- `implementation_tip` — short practical how-to tip
- `recommendation_id`, `rule_id`, `title` — copy exactly from inputs
- `priority`, `category`, `estimated_effort`, `estimated_impact` — copy exactly

Do **not** output confidence. Confidence is computed by the platform, never by the model.

## Rules

1. Closed world: use ONLY the supplied QuickWinContext / placeholders.
2. Never invent findings, recommendation ids, or rule ids.
3. Never change priority, category, effort, impact, or scores.
4. Never invent business impact beyond what was supplied.
5. Never invent percentages, ROI, or guaranteed outcomes.
6. Explain why this is a quick win using the supplied effort and impact only.
7. Return JSON only — no markdown wrapper.

## Example

```json
{
  "headline": "Add a title tag in minutes",
  "summary": "A unique document title is missing and can be added with very little effort.",
  "why_it_matters": "Titles drive search snippets and browser-tab clarity for visitors.",
  "expected_benefit": "Clearer SERP presentation and stronger first impressions.",
  "implementation_tip": "Add a single descriptive title element in the document head, then republish.",
  "recommendation_id": "rec.seo.add_document_title",
  "rule_id": "seo.title.missing",
  "title": "Add a descriptive document title",
  "priority": "High",
  "category": "SEO",
  "estimated_effort": "Very Low",
  "estimated_impact": "High"
}
```
