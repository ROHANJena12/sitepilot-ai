"""CSV export — findings and recommendations tables."""

from __future__ import annotations

import csv
import io

from app.export.base import ExportArtifact, ReportExporter
from app.services.report.schemas import AuditReportDTO, FindingDTO, RecommendationDTO


def _collect_findings(report: AuditReportDTO) -> list[FindingDTO]:
    seen: set[str] = set()
    ordered: list[FindingDTO] = []
    sections = (
        report.critical_issues,
        report.seo.findings,
        report.accessibility.findings,
        report.security.findings,
        report.performance.findings,
        report.business.findings,
        report.business_impacts,
    )
    for group in sections:
        for finding in group:
            key = finding.id or f"{finding.category}:{finding.title}"
            if key in seen:
                continue
            seen.add(key)
            ordered.append(finding)
    return ordered


def _collect_recommendations(report: AuditReportDTO) -> list[RecommendationDTO]:
    seen: set[str] = set()
    ordered: list[RecommendationDTO] = []
    for rec in (*report.recommendations, *report.quick_wins):
        key = rec.recommendation_id or rec.title
        if key in seen:
            continue
        seen.add(key)
        ordered.append(rec)
    return ordered


class CsvReportExporter(ReportExporter):
    """
    UTF-8 CSV with two sections:

    Findings — Category, Severity, Title, Description, Impact, Score
    Recommendations — Priority, Recommendation, Difficulty, Expected Impact, Quick Win
    """

    def export(self, report: AuditReportDTO) -> ExportArtifact:
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["Findings"])
        writer.writerow(
            ["Category", "Severity", "Title", "Description", "Impact", "Score"]
        )
        for finding in _collect_findings(report):
            writer.writerow(
                [
                    finding.category,
                    finding.severity,
                    finding.title,
                    finding.description or "",
                    finding.impact or "",
                    "" if finding.confidence is None else str(finding.confidence),
                ]
            )

        writer.writerow([])
        writer.writerow(["Recommendations"])
        writer.writerow(
            [
                "Priority",
                "Recommendation",
                "Difficulty",
                "Expected Impact",
                "Quick Win",
            ]
        )
        for rec in _collect_recommendations(report):
            writer.writerow(
                [
                    rec.priority,
                    rec.title,
                    rec.estimated_effort,
                    rec.estimated_impact,
                    "yes" if rec.is_quick_win else "no",
                ]
            )

        # BOM helps Excel open UTF-8 correctly.
        content = ("\ufeff" + buffer.getvalue()).encode("utf-8")
        return ExportArtifact(
            content=content,
            media_type="text/csv; charset=utf-8",
            filename="audit-report.csv",
        )
