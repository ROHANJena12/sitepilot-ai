# Entity: Audit

## Responsibility

Represents the **Audit** business domain object — job identity, status lifecycle, target website reference, timestamps, and summary metrics. Provides entity-level types, mappers, and reusable audit chips/cards.

## Boundaries

- **In scope:** Audit model contracts, status enums, and entity presentation.
- **Out of scope:** Starting/polling audits (`features/audit`), health score feature UI (`features/health-score`), and API clients (`shared/services/audit.service.ts`).

## Consumers

`features/audit`, `features/dashboard`, `widgets/audit-dashboard`.

## Status

Scaffold only. Implementation pending.
