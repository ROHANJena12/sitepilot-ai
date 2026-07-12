# Entity: Website

## Responsibility

Represents the **Website** business domain object — identity, URL, ownership metadata, and relationships to audits/reports. Provides entity-level types, mappers, and optional entity UI cards used across features.

## Boundaries

- **In scope:** Website model contracts, selectors/mappers, and reusable entity presentation.
- **Out of scope:** Audit job orchestration (`features/audit`), dashboard aggregation (`features/dashboard`), and HTTP transport (`shared/services`).

## Consumers

`features/audit`, `features/dashboard`, `features/report`, and related widgets.

## Status

Scaffold only. Implementation pending.
