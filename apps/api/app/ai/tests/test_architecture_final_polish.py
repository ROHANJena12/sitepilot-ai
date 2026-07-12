"""Sprint 21.1 — AI architecture final polish contracts."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.ai.builders import BusinessSummaryBuilder, ExecutiveSummaryBuilder, prompt_template_hash
from app.ai.config import clear_ai_settings_cache
from app.ai.constants import (
    SCHEMA_VERSION_BUSINESS_SUMMARY,
    SCHEMA_VERSION_EXECUTIVE_SUMMARY,
)
from app.ai.context import AIContext, WebsiteContext
from app.ai.openai_settings import clear_openai_settings_cache
from app.ai.prompt_repository import PromptRepository
from app.ai.registry import reset_provider_registry
from app.ai.response import AIQualityMetadata, AIResponse, ProviderResponseMetadata
from app.ai.schemas import BaseSummary, BusinessSummary, ExecutiveSummary
from app.ai.summary_limits import (
    MAX_BUSINESS_OPPORTUNITIES,
    MAX_KEY_RISKS,
    MAX_POSITIVE_OBSERVATIONS,
    MAX_PRIORITY_ACTIONS,
)


@pytest.fixture(autouse=True)
def _reset() -> None:
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()
    yield
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()


class TestNoLLMConfidence:
    def test_summary_schemas_have_no_confidence_field(self) -> None:
        for cls in (ExecutiveSummary, BusinessSummary, BaseSummary):
            assert "confidence" not in cls.model_fields


class TestBaseSummaryAndLimits:
    def test_executive_and_business_share_base(self) -> None:
        assert issubclass(ExecutiveSummary, BaseSummary)
        assert issubclass(BusinessSummary, BaseSummary)

    def test_shared_limits(self) -> None:
        assert MAX_KEY_RISKS == 5
        assert MAX_PRIORITY_ACTIONS == 5
        assert MAX_POSITIVE_OBSERVATIONS == 5
        assert MAX_BUSINESS_OPPORTUNITIES == 5

    def test_list_max_length_enforced(self) -> None:
        with pytest.raises(Exception):
            ExecutiveSummary(
                headline="H",
                summary="S",
                priority_actions=["a", "b", "c", "d", "e", "f"],
            )


class TestPromptHashAndDiagnostics:
    def test_prompt_hash_stable(self) -> None:
        repo = PromptRepository()
        template = repo.get("executive_summary")
        a = prompt_template_hash(template.body)
        b = prompt_template_hash(template.body)
        assert a == b
        assert len(a) == 64

        ctx = AIContext(
            audit_id=uuid4(),
            schema_version=SCHEMA_VERSION_EXECUTIVE_SUMMARY,
            website=WebsiteContext(url="https://example.com"),
            executive_summary_inputs=__import__(
                "app.ai.context", fromlist=["ExecutiveSummaryContext"]
            ).ExecutiveSummaryContext(
                summary="S",
                overall_score=80,
                grade="B",
            ),
        )
        built = ExecutiveSummaryBuilder(repo).build(ctx)
        assert built.prompt_hash == a
        assert built.diagnostics.prompt_hash == a
        assert built.diagnostics.context_size >= 0
        assert built.diagnostics.estimated_prompt_tokens > 0
        assert built.diagnostics.estimated_completion_tokens > 0
        assert built.schema_version == SCHEMA_VERSION_EXECUTIVE_SUMMARY

    def test_business_builder_diagnostics(self) -> None:
        ctx = AIContext(
            audit_id=uuid4(),
            schema_version=SCHEMA_VERSION_BUSINESS_SUMMARY,
            website=WebsiteContext(url="https://example.com"),
            business_summary_inputs=__import__(
                "app.ai.context", fromlist=["BusinessSummaryContext"]
            ).BusinessSummaryContext(
                summary="B",
                overall_score=80,
                grade="B",
            ),
        )
        built = BusinessSummaryBuilder(PromptRepository()).build(ctx)
        assert built.diagnostics.variable_count > 0
        assert built.prompt_hash == built.diagnostics.prompt_hash


class TestAIQualityMetadata:
    def test_quality_is_deterministic_platform_metadata(self) -> None:
        quality = AIQualityMetadata(
            grounded=True,
            validation_passed=True,
            cache_hit=False,
            provider="openai",
            model="gpt-5.5",
            prompt_version="v1",
            builder_version=1,
            schema_version=SCHEMA_VERSION_EXECUTIVE_SUMMARY,
            prompt_hash="b" * 64,
        )
        result = ExecutiveSummary(headline="H", summary="S", overall_score=80, grade="B")
        response = AIResponse[ExecutiveSummary](
            result=result,
            quality=quality,
            provider_metadata=ProviderResponseMetadata(
                provider="openai",
                model="gpt-5.5",
            ),
            generated_at=datetime.now(UTC),
        )
        assert response.quality is quality
        assert response.provider_metadata.provider == "openai"
        assert response.metadata is response.provider_metadata
