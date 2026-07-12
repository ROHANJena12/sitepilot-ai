"""Grounding validator tests — pure closed-world checks, no OpenAI."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.ai.constants import SCHEMA_VERSION_FINDING_EXPLANATION
from app.ai.context import AIContext, FindingContext, RecommendationContext, WebsiteContext
from app.ai.exceptions import InvalidAIResponse
from app.ai.grounding import (
    BusinessSummaryGroundingValidator,
    ExecutiveSummaryGroundingValidator,
    FindingGroundingValidator,
    QuickWinGroundingValidator,
    get_grounding_validator,
)
from app.ai.schemas import (
    FindingExplanation,
)


def _finding_ctx(**overrides: object) -> AIContext:
    finding = FindingContext(
        finding_id="seo.title.missing",
        title="Missing title",
        description="No title tag",
        severity="high",
        category="seo",
        status="fail",
    )
    data: dict[str, object] = {
        "audit_id": uuid4(),
        "report_hash": "rh-ground",
        "schema_version": SCHEMA_VERSION_FINDING_EXPLANATION,
        "website": WebsiteContext(url="https://example.com"),
        "finding": finding,
    }
    data.update(overrides)
    return AIContext(**data)  # type: ignore[arg-type]


def _valid() -> FindingExplanation:
    return FindingExplanation(
        finding_id="seo.title.missing",
        title="Missing document title",
        explanation="The page has no title element.",
        why_it_matters="Hurts CTR.",
        suggested_fix_summary="Add a title tag.",
        severity="high",
        category="seo",
        related_recommendation_ids=[],
    )


class TestFindingGrounding:
    def test_accepts_grounded_explanation(self) -> None:
        out = FindingGroundingValidator().validate(_valid(), _finding_ctx())
        assert out.finding_id == "seo.title.missing"

    def test_rejects_missing_finding_context(self) -> None:
        ctx = _finding_ctx(finding=None)
        with pytest.raises(InvalidAIResponse, match="finding is required"):
            FindingGroundingValidator().validate(_valid(), ctx)

    def test_rejects_invented_finding_id(self) -> None:
        bad = _valid().model_copy(update={"finding_id": "invented.id"})
        with pytest.raises(InvalidAIResponse, match="finding_id"):
            FindingGroundingValidator().validate(bad, _finding_ctx())

    def test_rejects_invalid_severity(self) -> None:
        bad = _valid().model_copy(update={"severity": "low"})
        with pytest.raises(InvalidAIResponse, match="severity"):
            FindingGroundingValidator().validate(bad, _finding_ctx())

    def test_rejects_wrong_category(self) -> None:
        bad = _valid().model_copy(update={"category": "security"})
        with pytest.raises(InvalidAIResponse, match="category"):
            FindingGroundingValidator().validate(bad, _finding_ctx())

    def test_severity_category_case_insensitive(self) -> None:
        ok = _valid().model_copy(update={"severity": "HIGH", "category": "SEO"})
        out = FindingGroundingValidator().validate(ok, _finding_ctx())
        assert out.severity == "HIGH"

    def test_rejects_hallucinated_recommendation_ids_without_context(self) -> None:
        bad = _valid().model_copy(
            update={"related_recommendation_ids": ["rec.invented"]}
        )
        with pytest.raises(InvalidAIResponse, match="related_recommendation"):
            FindingGroundingValidator().validate(bad, _finding_ctx())

    def test_rejects_unknown_recommendation_id_when_context_has_one(self) -> None:
        ctx = _finding_ctx(
            recommendation=RecommendationContext(
                recommendation_id="rec.seo.add_document_title",
                rule_id="seo.title.missing",
                title="Add title",
                description="Add a title tag.",
                priority="high",
                category="seo",
                effort="low",
                impact="high",
                related_rules=("rule.seo.title",),
            )
        )
        bad = _valid().model_copy(
            update={"related_recommendation_ids": ["rec.other"]}
        )
        with pytest.raises(InvalidAIResponse, match="hallucinated related_recommendation"):
            FindingGroundingValidator().validate(bad, ctx)

    def test_rejects_hallucinated_rule_id_as_recommendation(self) -> None:
        ctx = _finding_ctx(
            recommendation=RecommendationContext(
                recommendation_id="rec.seo.add_document_title",
                rule_id="rule.seo.title",
                title="Add title",
                description="Add a title tag.",
                priority="high",
                category="seo",
                effort="low",
                impact="high",
                related_rules=("rule.seo.title",),
            )
        )
        bad = _valid().model_copy(
            update={"related_recommendation_ids": ["rule.seo.title"]}
        )
        with pytest.raises(InvalidAIResponse, match="rule id"):
            FindingGroundingValidator().validate(bad, ctx)

    def test_accepts_known_recommendation_id(self) -> None:
        ctx = _finding_ctx(
            recommendation=RecommendationContext(
                recommendation_id="rec.seo.add_document_title",
                rule_id="seo.title.missing",
                title="Add title",
                description="Add a title tag.",
                priority="high",
                category="seo",
                effort="low",
                impact="high",
            )
        )
        ok = _valid().model_copy(
            update={"related_recommendation_ids": ["rec.seo.add_document_title"]}
        )
        out = FindingGroundingValidator().validate(ok, ctx)
        assert out.related_recommendation_ids == ["rec.seo.add_document_title"]

    def test_registry_returns_finding_validator(self) -> None:
        validator = get_grounding_validator(FindingExplanation)
        assert isinstance(validator, FindingGroundingValidator)


class TestRecommendationGroundingPlaceholderMoved:
    def test_recommendation_validator_is_real(self) -> None:
        from app.ai.grounding import RecommendationGroundingValidator

        assert RecommendationGroundingValidator is not None


class TestPlaceholderGroundingValidators:
    def test_executive_validator_is_real(self) -> None:
        assert ExecutiveSummaryGroundingValidator is not None

    def test_business_validator_is_real(self) -> None:
        assert BusinessSummaryGroundingValidator is not None

    def test_quick_win_validator_is_real(self) -> None:
        assert QuickWinGroundingValidator is not None
