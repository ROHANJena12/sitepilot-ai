# Feature: Audit

## Responsibility

Owns the website audit initiation and progress experience — URL intake, crawl/audit job lifecycle UI, status feedback, and handoff into report views.

## Boundaries

- **In scope:** Audit start form, progress indicators, retry/error states for audit jobs.
- **Out of scope:** Report rendering (`features/report`), health score presentation (`features/health-score`), and entity model definitions (`entities/audit`).

## Composition

Consumed by `app/audit/page.tsx` and `widgets/audit-dashboard`.

## Status

Scaffold only. Implementation pending.
