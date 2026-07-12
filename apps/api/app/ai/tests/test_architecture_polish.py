"""Architecture polish — mappers, feature contexts, locale cache isolation."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.ai.cache import build_cache_key
from app.ai.constants import (
    SCHEMA_VERSION_FINDING_EXPLANATION,
    SCHEMA_VERSION_RECOMMENDATION,
)
from app.ai.context import (
    AIContext,
    BusinessSummaryContext,
    BusinessSummaryInputs,
    ExecutiveSummaryContext,
    ExecutiveSummaryInputs,
    FindingAIContext,
    FindingContext,
    FindingExplanationContext,
    RecommendationAIContext,
    RecommendationContext,
    RecommendationExplanationContext,
    WebsiteContext,
    cache_entity_id,
)
from app.ai.mappers import (
    AIContextMapper,
    FindingMapInput,
    FindingMapper,
    RecommendationMapInput,
    RecommendationMapper,
    finding_to_ai_context,
    recommendation_to_ai_context,
)


def _finding_snap() -> SimpleNamespace:
    return SimpleNamespace(
        finding_id="seo.title.missing",
        title="Missing title",
        description="No title tag",
        severity="high",
        category="seo",
        status="fail",
        evidence_summary=None,
        business_impact="Lower CTR",
        location=None,
        confidence=95,
        engine="seo",
    )


def _rec_snap() -> SimpleNamespace:
    return SimpleNamespace(
        recommendation_id="rec.seo.add_document_title",
        title="Add a descriptive document title",
        description="Set a unique title.",
        category="SEO",
        priority="High",
        estimated_effort="Very Low",
        estimated_impact="High",
        affected_findings=("seo.title.missing",),
        related_rules=("seo.title.missing",),
        technical_reason="Missing title element.",
        business_reason="Improves CTR.",
        is_quick_win=True,
        confidence=95,
    )


class TestContextHierarchyAndAliases:
    def test_finding_explanation_context_alias(self) -> None:
        ctx = FindingExplanationContext(
            finding_id="seo.title.missing",
            title="Missing title",
            severity="high",
            category="seo",
        )
        assert FindingContext is FindingExplanationContext
        assert FindingAIContext is FindingExplanationContext
        assert isinstance(ctx, FindingContext)

    def test_recommendation_explanation_context_alias(self) -> None:
        ctx = RecommendationExplanationContext(
            recommendation_id="rec.seo.add_document_title",
            rule_id="seo.title.missing",
            title="Add title",
            description="Add it",
            category="SEO",
            priority="High",
            effort="Very Low",
            impact="High",
        )
        assert RecommendationAIContext is RecommendationExplanationContext
        assert RecommendationContext is RecommendationExplanationContext
        assert isinstance(ctx, RecommendationAIContext)

    def test_summary_context_aliases(self) -> None:
        assert ExecutiveSummaryInputs is ExecutiveSummaryContext
        assert BusinessSummaryInputs is BusinessSummaryContext
        exec_ctx = ExecutiveSummaryContext(summary="S")
        biz_ctx = BusinessSummaryContext(summary="B")
        assert isinstance(exec_ctx, ExecutiveSummaryInputs)
        assert isinstance(biz_ctx, BusinessSummaryInputs)

    def test_cache_entity_id_finding_vs_recommendation(self) -> None:
        finding_only = AIContext(
            schema_version=SCHEMA_VERSION_FINDING_EXPLANATION,
            finding=FindingExplanationContext(
                finding_id="seo.title.missing",
                title="t",
                severity="high",
                category="seo",
            ),
        )
        assert cache_entity_id(finding_only) == "seo.title.missing"

        rec = AIContext(
            schema_version=SCHEMA_VERSION_RECOMMENDATION,
            finding=FindingExplanationContext(
                finding_id="seo.title.missing",
                title="t",
                severity="high",
                category="seo",
            ),
            recommendation=RecommendationExplanationContext(
                recommendation_id="rec.seo.add_document_title",
                rule_id="seo.title.missing",
                title="Add title",
                description="Add it",
                category="SEO",
                priority="High",
                effort="Very Low",
                impact="High",
            ),
        )
        # Recommendation wins when both present.
        assert cache_entity_id(rec) == "rec.seo.add_document_title"


class TestAIContextMapperHierarchy:
    def test_finding_mapper_is_ai_context_mapper(self) -> None:
        mapper = FindingMapper()
        assert isinstance(mapper, AIContextMapper)
        ctx = mapper.map(
            FindingMapInput(
                finding=_finding_snap(),
                website=WebsiteContext(url="https://example.com"),
                health_score=80,
                report_hash="rh1",
                audit_id=uuid4(),
                locale="en",
            )
        )
        assert ctx.finding is not None
        assert ctx.finding.finding_id == "seo.title.missing"
        assert ctx.locale == "en"
        assert ctx.schema_version == SCHEMA_VERSION_FINDING_EXPLANATION

    def test_recommendation_mapper_is_ai_context_mapper(self) -> None:
        mapper = RecommendationMapper()
        assert isinstance(mapper, AIContextMapper)
        finding = FindingExplanationContext(
            finding_id="seo.title.missing",
            title="Missing title",
            severity="high",
            category="seo",
        )
        ctx = mapper.map(
            RecommendationMapInput(
                recommendation=_rec_snap(),
                related_findings=(finding,),
                website=WebsiteContext(url="https://example.com"),
                health_score=81,
                locale="es",
                report_hash="rh-rec",
            )
        )
        assert ctx.recommendation is not None
        assert ctx.recommendation.recommendation_id == "rec.seo.add_document_title"
        assert ctx.locale == "es"
        assert ctx.finding is not None

    def test_convenience_wrappers(self) -> None:
        fctx = finding_to_ai_context(_finding_snap(), locale="fr")
        assert fctx.locale == "fr"
        rctx = recommendation_to_ai_context(_rec_snap(), locale="de")
        assert rctx.locale == "de"


class TestLocaleCacheIsolation:
    def test_locale_changes_cache_key(self) -> None:
        base = dict(
            provider="openai",
            model="gpt-5.5",
            schema_version="ai.finding_explanation.v1",
            builder_version=1,
            prompt_version="finding_explanation@v2",
            report_hash="rh",
            entity_id="seo.title.missing",
            input_hash="abc",
        )
        en = build_cache_key(**base, locale="en")
        es = build_cache_key(**base, locale="es")
        assert en != es

    def test_entity_id_finding_vs_recommendation(self) -> None:
        base = dict(
            provider="openai",
            model="gpt-5.5",
            schema_version="ai.x.v1",
            builder_version=1,
            prompt_version="v1",
            locale="en",
            report_hash="rh",
            input_hash="i",
        )
        finding_key = build_cache_key(**base, entity_id="seo.title.missing")
        rec_key = build_cache_key(**base, entity_id="rec.seo.add_document_title")
        assert finding_key != rec_key

    def test_recommendation_id_alias_still_works(self) -> None:
        via_alias = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version="ai.recommendation.v2",
            builder_version=1,
            prompt_version="recommendation@v1",
            locale="en",
            report_hash="rh",
            input_hash="i",
            recommendation_id="rec.seo.add_document_title",
        )
        via_entity = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version="ai.recommendation.v2",
            builder_version=1,
            prompt_version="recommendation@v1",
            locale="en",
            report_hash="rh",
            input_hash="i",
            entity_id="rec.seo.add_document_title",
        )
        assert via_alias == via_entity
