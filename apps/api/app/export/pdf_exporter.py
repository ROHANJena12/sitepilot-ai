"""PDF export — branded multi-page layout from AuditReportDTO (ReportLab)."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.export.base import ExportArtifact, ReportExporter
from app.export.csv_exporter import _collect_findings, _collect_recommendations
from app.services.report.schemas import AuditReportDTO, FindingDTO, RecommendationDTO

_INK = colors.HexColor("#0f172a")
_MUTED = colors.HexColor("#64748b")
_ACCENT = colors.HexColor("#0d9488")
_LINE = colors.HexColor("#e2e8f0")
_SOFT = colors.HexColor("#f8fafc")


def _esc(value: object | None) -> str:
    if value is None:
        return "—"
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is not None:
        value = value.astimezone().replace(tzinfo=None)
    return value.strftime("%Y-%m-%d %H:%M UTC")


class PdfReportExporter(ReportExporter):
    """Render a professional PDF from the assembled report DTO only."""

    def export(self, report: AuditReportDTO) -> ExportArtifact:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title="SitePilot AI Audit Report",
            author="SitePilot AI",
        )
        styles = self._styles()
        story: list[Any] = []
        story.extend(self._cover(report, styles))
        story.append(PageBreak())
        story.extend(self._scores(report, styles))
        story.append(Spacer(1, 8 * mm))
        story.extend(self._summaries(report, styles))
        story.append(PageBreak())
        story.extend(self._findings(report, styles))
        story.append(PageBreak())
        story.extend(self._recommendations(report, styles))

        website = report.overview.website.url

        def _footer(canvas: Any, doc_obj: Any) -> None:
            canvas.saveState()
            canvas.setStrokeColor(_LINE)
            canvas.setLineWidth(0.5)
            canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(_MUTED)
            canvas.drawString(18 * mm, 7 * mm, "SitePilot AI — Audit Report")
            canvas.drawRightString(
                A4[0] - 18 * mm,
                7 * mm,
                f"Page {doc_obj.page}  ·  {_esc(website)[:48]}",
            )
            canvas.restoreState()

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return ExportArtifact(
            content=buffer.getvalue(),
            media_type="application/pdf",
            filename="audit-report.pdf",
        )

    def _styles(self) -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "brand": ParagraphStyle(
                "Brand",
                parent=base["Normal"],
                fontName="Helvetica-Bold",
                fontSize=11,
                textColor=_ACCENT,
                spaceAfter=6,
            ),
            "cover_title": ParagraphStyle(
                "CoverTitle",
                parent=base["Title"],
                fontName="Helvetica-Bold",
                fontSize=28,
                textColor=_INK,
                alignment=TA_CENTER,
                spaceAfter=12,
            ),
            "cover_sub": ParagraphStyle(
                "CoverSub",
                parent=base["Normal"],
                fontSize=12,
                textColor=_MUTED,
                alignment=TA_CENTER,
                spaceAfter=6,
            ),
            "h1": ParagraphStyle(
                "H1",
                parent=base["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=16,
                textColor=_INK,
                spaceBefore=4,
                spaceAfter=8,
            ),
            "h2": ParagraphStyle(
                "H2",
                parent=base["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=12,
                textColor=_INK,
                spaceBefore=8,
                spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "Body",
                parent=base["Normal"],
                fontSize=10,
                textColor=_INK,
                leading=14,
                spaceAfter=4,
            ),
            "muted": ParagraphStyle(
                "Muted",
                parent=base["Normal"],
                fontSize=9,
                textColor=_MUTED,
                leading=12,
            ),
            "cell": ParagraphStyle(
                "Cell",
                parent=base["Normal"],
                fontSize=8,
                textColor=_INK,
                leading=11,
                alignment=TA_LEFT,
            ),
            "cell_right": ParagraphStyle(
                "CellRight",
                parent=base["Normal"],
                fontSize=8,
                textColor=_INK,
                alignment=TA_RIGHT,
            ),
        }

    def _cover(self, report: AuditReportDTO, styles: dict[str, ParagraphStyle]) -> list[Any]:
        website = report.overview.website
        score = report.overview.overall_score
        grade = report.overview.overall_grade or "—"
        flow: list[Any] = [
            Spacer(1, 28 * mm),
            Paragraph("SITEPILOT AI", styles["brand"]),
            Paragraph("Website Audit Report", styles["cover_title"]),
            Spacer(1, 8 * mm),
            Paragraph(_esc(website.url), styles["cover_sub"]),
            Paragraph(f"Host · {_esc(website.host)}", styles["cover_sub"]),
            Paragraph(
                f"Audit date · {_esc(_fmt_dt(report.overview.audit_date or report.generated_at))}",
                styles["cover_sub"],
            ),
            Spacer(1, 14 * mm),
            Paragraph(
                f"Overall score · <b>{_esc(score if score is not None else '—')}</b> "
                f"· Grade <b>{_esc(grade)}</b>",
                styles["cover_sub"],
            ),
            Spacer(1, 10 * mm),
            Paragraph(
                f"Status · {_esc(report.overview.status)} · Schema {_esc(report.schema_version)}",
                styles["muted"],
            ),
        ]
        return flow

    def _scores(self, report: AuditReportDTO, styles: dict[str, ParagraphStyle]) -> list[Any]:
        cats = report.health.category_scores or {
            "seo": report.seo.score,
            "accessibility": report.accessibility.score,
            "security": report.security.score,
            "performance": report.performance.score,
            "business": report.business.score,
        }
        rows = [["Category", "Score"]]
        for key, value in cats.items():
            rows.append([key.replace("_", " ").title(), "" if value is None else str(value)])
        table = Table(rows, colWidths=[110 * mm, 40 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _SOFT),
                    ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.4, _LINE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return [
            Paragraph("Category Scores", styles["h1"]),
            Paragraph(
                f"Overall health · {_esc(report.health.overall_score)} "
                f"({_esc(report.health.grade)})",
                styles["body"],
            ),
            Spacer(1, 3 * mm),
            table,
        ]

    def _summaries(self, report: AuditReportDTO, styles: dict[str, ParagraphStyle]) -> list[Any]:
        business_bits = [
            report.business.summary,
            *[f.title for f in report.business_impacts[:5]],
        ]
        business_text = " ".join(bit for bit in business_bits if bit) or "—"
        return [
            Paragraph("Executive Summary", styles["h1"]),
            Paragraph(_esc(report.summary or "—"), styles["body"]),
            Paragraph("Business Summary", styles["h1"]),
            Paragraph(_esc(business_text), styles["body"]),
        ]

    def _findings(self, report: AuditReportDTO, styles: dict[str, ParagraphStyle]) -> list[Any]:
        findings = _collect_findings(report)
        flow: list[Any] = [Paragraph("Findings", styles["h1"])]
        if not findings:
            flow.append(Paragraph("No findings recorded.", styles["muted"]))
            return flow
        rows: list[list[Any]] = [
            [
                Paragraph("<b>Severity</b>", styles["cell"]),
                Paragraph("<b>Category</b>", styles["cell"]),
                Paragraph("<b>Title</b>", styles["cell"]),
                Paragraph("<b>Impact</b>", styles["cell"]),
            ]
        ]
        for finding in findings[:80]:
            rows.append(self._finding_row(finding, styles))
        table = Table(rows, colWidths=[22 * mm, 28 * mm, 70 * mm, 40 * mm])
        table.setStyle(self._table_style())
        flow.append(table)
        if len(findings) > 80:
            flow.append(
                Paragraph(
                    f"Showing 80 of {len(findings)} findings.",
                    styles["muted"],
                )
            )
        return flow

    def _finding_row(
        self, finding: FindingDTO, styles: dict[str, ParagraphStyle]
    ) -> list[Any]:
        return [
            Paragraph(_esc(finding.severity), styles["cell"]),
            Paragraph(_esc(finding.category), styles["cell"]),
            Paragraph(_esc(finding.title), styles["cell"]),
            Paragraph(_esc(finding.impact or finding.description or "—"), styles["cell"]),
        ]

    def _recommendations(
        self, report: AuditReportDTO, styles: dict[str, ParagraphStyle]
    ) -> list[Any]:
        recs = _collect_recommendations(report)
        quick = [r for r in recs if r.is_quick_win]
        flow: list[Any] = [Paragraph("Recommendations", styles["h1"])]
        if not recs:
            flow.append(Paragraph("No recommendations recorded.", styles["muted"]))
        else:
            flow.append(self._recs_table(recs[:60], styles))
        flow.append(Paragraph("Quick Wins", styles["h1"]))
        if not quick:
            flow.append(Paragraph("No quick wins identified.", styles["muted"]))
        else:
            flow.append(self._recs_table(quick[:40], styles))
        return flow

    def _recs_table(
        self, recs: list[RecommendationDTO], styles: dict[str, ParagraphStyle]
    ) -> Table:
        rows: list[list[Any]] = [
            [
                Paragraph("<b>Priority</b>", styles["cell"]),
                Paragraph("<b>Recommendation</b>", styles["cell"]),
                Paragraph("<b>Effort</b>", styles["cell"]),
                Paragraph("<b>Impact</b>", styles["cell"]),
            ]
        ]
        for rec in recs:
            rows.append(
                [
                    Paragraph(_esc(rec.priority), styles["cell"]),
                    Paragraph(_esc(rec.title), styles["cell"]),
                    Paragraph(_esc(rec.estimated_effort), styles["cell"]),
                    Paragraph(_esc(rec.estimated_impact), styles["cell"]),
                ]
            )
        table = Table(rows, colWidths=[24 * mm, 80 * mm, 28 * mm, 28 * mm])
        table.setStyle(self._table_style())
        return table

    def _table_style(self) -> TableStyle:
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _SOFT),
                ("GRID", (0, 0), (-1, -1), 0.35, _LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
