# Report Composer & Export

## Purpose

`ReportComposer` (`apps/api/app/services/report/`) assembles **persisted** audit artifacts into one UI-ready `AuditReportDTO` for:

```http
GET  /api/v1/audits/{audit_id}/report
POST /api/v1/audits/{audit_id}/report/regenerate
```

Detailed composition rules live in `apps/api/app/services/report/RULES.md`.

## Constraints

- Not an Engine; not registered in `AuditPipeline`
- Reads repositories only; writes projection to `reports.report_json`
- Deterministic summary — **no AI**
- Frontend must not re-filter, re-sort, or re-score the DTO

## Sprint 30 — Report Export

Export is a **read-only presentation layer** over the assembled report:

```
API /audits/{id}/export/{pdf|json|csv}
        ↓
Export*UseCase (application/export)
        ↓
GetAuditReportUseCase → ReportComposer
        ↓
AuditReportDTO
        ↓
PdfReportExporter | JsonReportExporter | CsvReportExporter
        ↓
File Response (Content-Disposition: attachment)
```

| Format | Module | Notes |
|---|---|---|
| PDF | `app/export/pdf_exporter.py` | ReportLab; cover, scores, summaries, findings, recommendations, footer |
| JSON | `app/export/json_exporter.py` | Exact DTO serialization |
| CSV | `app/export/csv_exporter.py` | Findings + Recommendations tables, UTF-8 |

**Must not:** regenerate reports, rerun engines, call AI, mutate the composer, or change the database schema.
