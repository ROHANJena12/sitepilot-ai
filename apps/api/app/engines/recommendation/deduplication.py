"""Deduplicate findings that map to the same recommendation_id."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engines.common.findings import Finding
from app.engines.recommendation.templates import FINDING_TO_TEMPLATE, RecommendationTemplate, resolve_template


@dataclass
class RecommendationGroup:
    """Merged findings sharing one recommendation template."""

    recommendation_id: str
    template: RecommendationTemplate
    findings: list[Finding] = field(default_factory=list)
    mapped_exact: bool = True

    def add(self, finding: Finding, *, exact: bool) -> None:
        self.findings.append(finding)
        if not exact:
            self.mapped_exact = False


def group_findings_by_recommendation(
    findings: tuple[Finding, ...],
) -> list[RecommendationGroup]:
    """
    Map each finding to a template and merge by recommendation_id.

    Fallback templates use unique ids per finding (`rec.*.generic_issue:<id>`),
    so they do not incorrectly merge unrelated issues.
    Specialized templates share one id across related finding variants.
    """
    groups: dict[str, RecommendationGroup] = {}
    for finding in findings:
        template = resolve_template(finding.id)
        exact = finding.id in FINDING_TO_TEMPLATE
        key = template.recommendation_id
        if key not in groups:
            groups[key] = RecommendationGroup(
                recommendation_id=key,
                template=template,
                mapped_exact=exact,
            )
        groups[key].add(finding, exact=exact)
    return list(groups.values())
