# Entity: Report

## Responsibility

Represents the **Report** business domain object — report identity, linked audit, section payloads, finding collections, and export metadata. Provides entity-level types, mappers, and reusable report summary presentation.

## Boundaries

- **In scope:** Report model contracts and entity presentation.
- **Out of scope:** Full report page composition (`features/report`, `widgets/report-view`), recommendations UX (`features/recommendations`), and API clients (`shared/services/report.service.ts`).

## Consumers

`features/report`, `features/recommendations`, `widgets/report-view`.

## Status

Scaffold only. Implementation pending.
