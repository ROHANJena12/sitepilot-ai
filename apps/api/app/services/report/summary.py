"""Deterministic executive summary text (no AI)."""

from __future__ import annotations

from app.services.report.schemas import StatisticsDTO


def build_executive_summary(
    *,
    status: str,
    overall_score: int | None,
    overall_grade: str | None,
    stats: StatisticsDTO,
) -> str:
    """
    Build a fixed-pattern summary string from counts and scores.

    Example:
      Analysis completed successfully.
      42 findings detected.
      8 Critical
      15 High
      12 Medium
      7 Low
      Overall Health Score: 81 (B-)
    """
    if status == "complete_with_warnings":
        header = "Analysis completed with warnings."
    else:
        header = "Analysis completed successfully."

    sev = stats.findings_by_severity
    lines = [
        header,
        f"{stats.total_findings} findings detected.",
        f"{sev.get('critical', 0)} Critical",
        f"{sev.get('high', 0)} High",
        f"{sev.get('medium', 0)} Medium",
        f"{sev.get('low', 0)} Low",
    ]
    if sev.get("info", 0):
        lines.append(f"{sev['info']} Info")

    if overall_score is None:
        lines.append("Overall Health Score: unavailable")
    elif overall_grade:
        lines.append(f"Overall Health Score: {overall_score} ({overall_grade})")
    else:
        lines.append(f"Overall Health Score: {overall_score}")

    rec_total = stats.overall_counts.get("recommendations", 0)
    lines.append(f"{rec_total} recommendations generated.")
    return "\n".join(lines)
