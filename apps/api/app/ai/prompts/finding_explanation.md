# Finding Explanation

**Prompt-Version:** v2

## Purpose

Produce a grounded, business-aware explanation of a single SitePilot audit finding.
Explain why the supplied issue matters and summarize the fix.

You must NEVER discover, invent, or introduce new issues.

## Inputs

- `{{finding}}` — finding id, title, description, evidence (JSON or structured text)
- `{{severity}}` — critical | high | medium | low | info (authoritative — do not change)
- `{{category}}` — seo | accessibility | security | performance | business (authoritative)
- `{{business_impact}}` — optional business-impact framing from prior engines
- `{{website}}` — audited site URL / host
- `{{health_score}}` — overall health score context when available

## Expected Output

JSON matching `FindingExplanation`:

- `finding_id`, `title`, `explanation`, `why_it_matters`, `suggested_fix_summary`
- `severity`, `category`, optional `hedges`
- `related_recommendation_ids` must be an empty array

## Rules

1. Closed world: use ONLY the supplied finding. Do not invent `finding_id`s.
2. Never invent metrics, scores, ROI percentages, or checks that were not provided.
3. Never change `severity` or `category` — copy them exactly from inputs.
4. Never create recommendations, action plans beyond a short fix summary, or new findings.
5. Never mention checks, pages, or engines not present in the inputs.
6. If the finding's supplied confidence context is below 90, include hedging language in `hedges`.
7. Do **not** output a confidence score — confidence is computed by the platform.
8. Return JSON only — no markdown wrapper, no prose outside JSON.
9. Preserve technical truth from inputs; AI explains, never discovers.

## Example

Input severity `high`, category `seo`, finding missing document title.

Output sketch:

```json
{
  "finding_id": "seo.title.missing",
  "title": "Missing document title",
  "explanation": "The page has no <title> element.",
  "why_it_matters": "Search and browser tabs lack a clear label, hurting CTR and shareability.",
  "suggested_fix_summary": "Add a unique, descriptive title tag.",
  "severity": "high",
  "category": "seo",
  "hedges": [],
  "related_recommendation_ids": []
}
```
