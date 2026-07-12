# Feature: Dashboard

## Responsibility

Owns the authenticated product home — overview of recent audits, website portfolio summary, and navigation into audit/report workflows.

## Boundaries

- **In scope:** Dashboard summary modules, empty states, and quick actions.
- **Out of scope:** Individual audit flows (`features/audit`), report detail (`features/report`), and global chrome (`widgets/navbar`, `widgets/footer`).

## Composition

Consumed by `app/dashboard/page.tsx`.

## Status

Scaffold only. Implementation pending.
