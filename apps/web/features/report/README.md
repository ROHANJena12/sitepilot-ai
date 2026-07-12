# Feature: Report

## Responsibility

Owns the audit report experience — loading report data, structuring sections, and presenting findings ready for user review and export.

## Boundaries

- **In scope:** Report section layout, finding lists, export/share entry points.
- **Out of scope:** Chart primitives (`widgets/charts`), recommendations logic (`features/recommendations`), and report entity contracts (`entities/report`).

## Composition

Consumed by `app/report/page.tsx` and `widgets/report-view`.

## Status

Scaffold only. Implementation pending.
