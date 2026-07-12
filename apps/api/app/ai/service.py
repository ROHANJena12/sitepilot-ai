"""AI service layer — creates sessions; never owns telemetry/cache state."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.ai.builders import (
    BuiltPrompt,
    BusinessSummaryBuilder,
    ExecutiveSummaryBuilder,
    FindingExplanationBuilder,
    PromptBuilder,
    QuickWinBuilder,
    RecommendationExplanationBuilder,
)
from app.ai.cache import AICache, NullAICache, build_cache_key
from app.ai.config import AISettings, get_ai_settings
from app.ai.context import AIContext, cache_entity_id
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    BuilderNotFound,
    CapabilityNotSupported,
    ProviderNotFound,
    ServiceNotReady,
)
from app.ai.factory import ProviderFactory
from app.ai.features import AIFeature, resolve_feature
from app.ai.generation import GenerationOptions, GenerationRequest
from app.ai.grounding import get_grounding_validator
from app.ai.models import PromptTemplate
from app.ai.prompt_repository import PromptRepository
from app.ai.provider_routing import (
    PROVIDER_FALLBACK_CHAIN,
    classify_provider_failure,
    is_provider_available,
)
from app.ai.providers.base import LLMProvider
from app.ai.registry import ProviderRegistry, get_provider_registry
from app.ai.response import AIQualityMetadata, AIResponse
from app.ai.schemas import (
    BusinessSummary,
    ExecutiveSummary,
    FindingExplanation,
    QuickWinExplanation,
    RecommendationExplanation,
)
from app.ai.session import GenerationSession

T = TypeVar("T")


class AIService:
    """
    Provider-agnostic AI orchestration.

    Flow:
        Builder → GenerationRequest[T] → GenerationSession
        → (cache) → Provider (parse) → GroundingValidator → AIResponse[T]
    """

    def __init__(
        self,
        *,
        settings: AISettings | None = None,
        registry: ProviderRegistry | None = None,
        factory: ProviderFactory | None = None,
        prompts: PromptRepository | None = None,
        cache: AICache | None = None,
    ) -> None:
        self._settings = settings or get_ai_settings()
        self._factory = factory or ProviderFactory(self._settings)
        self._registry = registry or get_provider_registry()
        if not self._registry.list():
            self._factory.populate_registry(self._registry)
        self._prompts = prompts or PromptRepository(
            locale=self._settings.prompts_locale,
            hot_reload=self._settings.prompts_hot_reload,
        )
        if cache is not None:
            self._cache = cache
        elif self._settings.cache_enabled:
            # Process-local until Redis is wired; Null when explicitly disabled.
            from app.ai.cache import InMemoryAICache

            self._cache = InMemoryAICache()
        else:
            self._cache = NullAICache()

        self._builders: dict[AIFeature, PromptBuilder] = {
            AIFeature.FINDING: FindingExplanationBuilder(self._prompts),
            AIFeature.RECOMMENDATION: RecommendationExplanationBuilder(self._prompts),
            AIFeature.EXECUTIVE_SUMMARY: ExecutiveSummaryBuilder(self._prompts),
            AIFeature.BUSINESS_SUMMARY: BusinessSummaryBuilder(self._prompts),
            AIFeature.QUICK_WIN: QuickWinBuilder(self._prompts),
        }

    @property
    def settings(self) -> AISettings:
        return self._settings

    @property
    def prompts(self) -> PromptRepository:
        return self._prompts

    @property
    def cache(self) -> AICache:
        return self._cache

    def resolve_provider(self, name: str | None = None) -> LLMProvider:
        try:
            return self._registry.get(name)
        except ProviderNotFound:
            return self._factory.create(name)

    def resolve_provider_for_feature(
        self,
        feature: AIFeature | str | None = None,
        name: str | None = None,
    ) -> LLMProvider:
        """
        Resolve provider for a feature.

        Explicit ``name`` always wins. Otherwise walk
        Gemini → OpenRouter → OpenAI and return the first available hop.
        """
        if name is not None:
            return self.resolve_provider(name)

        for candidate_name in PROVIDER_FALLBACK_CHAIN:
            try:
                candidate = self.resolve_provider(candidate_name.value)
            except (ProviderNotFound, AIConfigurationError):
                continue
            if is_provider_available(candidate):
                return candidate

        # Last resort: configured default (may raise if missing).
        return self.resolve_provider(None)

    def _provider_candidates_for_generate(
        self,
        *,
        feature: AIFeature | str,
        provider: str | None,
    ) -> list[LLMProvider]:
        """
        Ordered providers to attempt for a generation.

        Explicit ``provider`` → single provider (no cross-provider fallback).
        Auto route → full Gemini → OpenRouter → OpenAI chain (available only).
        """
        if provider is not None:
            return [self.resolve_provider(provider)]

        candidates: list[LLMProvider] = []
        for name in PROVIDER_FALLBACK_CHAIN:
            try:
                candidate = self.resolve_provider(name.value)
            except (ProviderNotFound, AIConfigurationError):
                continue
            if is_provider_available(candidate):
                candidates.append(candidate)
        if candidates:
            return candidates
        return [self.resolve_provider(None)]

    def get_builder(self, feature: AIFeature | str) -> PromptBuilder:
        try:
            key = resolve_feature(feature)
        except KeyError as exc:
            raise BuilderNotFound(str(exc)) from exc
        try:
            return self._builders[key]
        except KeyError as exc:
            raise BuilderNotFound(
                f"Unknown AI feature '{feature}'. "
                f"Available: {', '.join(sorted(f.value for f in self._builders))}"
            ) from exc

    def load_prompt(self, prompt_id: str) -> PromptTemplate:
        return self._prompts.get(prompt_id)

    def default_options(self) -> GenerationOptions:
        return GenerationOptions(
            temperature=self._settings.temperature,
            max_output_tokens=self._settings.max_tokens,
            json_mode=True,
            stream=False,
        )

    def validate_capabilities(
        self,
        provider: LLMProvider,
        options: GenerationOptions,
    ) -> None:
        caps = provider.capabilities
        if options.json_mode and not caps.supports_json:
            raise CapabilityNotSupported(
                f"Provider '{provider.name()}' does not support JSON mode."
            )
        if options.stream and not caps.supports_streaming:
            raise CapabilityNotSupported(
                f"Provider '{provider.name()}' does not support streaming."
            )
        if options.system_prompt is not None and not caps.supports_system_messages:
            raise CapabilityNotSupported(
                f"Provider '{provider.name()}' does not support system messages."
            )
        if options.temperature is not None and not caps.supports_temperature:
            raise CapabilityNotSupported(
                f"Provider '{provider.name()}' does not support temperature."
            )
        if options.seed is not None and not caps.supports_seed:
            raise CapabilityNotSupported(
                f"Provider '{provider.name()}' does not support seed."
            )
        if options.response_schema is not None and not caps.supports_response_schema:
            raise CapabilityNotSupported(
                f"Provider '{provider.name()}' does not support response schemas."
            )
        if (
            options.max_output_tokens is not None
            and caps.max_output_tokens is not None
            and options.max_output_tokens > caps.max_output_tokens
        ):
            raise CapabilityNotSupported(
                f"Requested max_output_tokens={options.max_output_tokens} exceeds "
                f"provider '{provider.name()}' limit of {caps.max_output_tokens}."
            )

    def ensure_ready(
        self,
        *,
        feature: AIFeature | str | None = None,
        builder_key: AIFeature | str | None = None,
        provider_name: str | None = None,
        options: GenerationOptions | None = None,
    ) -> tuple[PromptBuilder, LLMProvider, GenerationOptions]:
        key = feature if feature is not None else builder_key
        if key is None:
            raise ServiceNotReady("ensure_ready requires feature= or builder_key=.")
        try:
            builder = self.get_builder(key)
        except BuilderNotFound as exc:
            raise ServiceNotReady(str(exc)) from exc

        try:
            provider = self.resolve_provider_for_feature(
                feature=key, name=provider_name
            )
        except ProviderNotFound as exc:
            raise ServiceNotReady(str(exc)) from exc
        except AIConfigurationError as exc:
            raise ServiceNotReady(str(exc)) from exc

        opts = options or self.default_options()
        try:
            self.validate_capabilities(provider, opts)
        except CapabilityNotSupported as exc:
            raise ServiceNotReady(str(exc)) from exc

        return builder, provider, opts

    def build_finding_prompt(self, context: AIContext) -> BuiltPrompt:
        return self.get_builder(AIFeature.FINDING).build(context)

    def build_recommendation_prompt(self, context: AIContext) -> BuiltPrompt:
        return self.get_builder(AIFeature.RECOMMENDATION).build(context)

    def build_executive_summary_prompt(self, context: AIContext) -> BuiltPrompt:
        return self.get_builder(AIFeature.EXECUTIVE_SUMMARY).build(context)

    def build_business_summary_prompt(self, context: AIContext) -> BuiltPrompt:
        return self.get_builder(AIFeature.BUSINESS_SUMMARY).build(context)

    def build_quick_win_prompt(self, context: AIContext) -> BuiltPrompt:
        return self.get_builder(AIFeature.QUICK_WIN).build(context)

    def build_cache_key_for(
        self,
        built: BuiltPrompt,
        *,
        context: AIContext | None = None,
        report_hash: str = "",
        provider: str | None = None,
        locale: str = "",
        entity_id: str = "",
        recommendation_id: str = "",
    ) -> str:
        """
        Build a cache key from a BuiltPrompt + already-mapped AIContext.

        AIService does not construct feature contexts — callers / mappers do.
        """
        prov = self.resolve_provider(provider)
        resolved_locale = locale or (context.locale if context is not None else "en")
        resolved_entity = entity_id or recommendation_id
        if not resolved_entity and context is not None:
            resolved_entity = cache_entity_id(context)
        resolved_report = report_hash or (
            (context.report_hash or "") if context is not None else ""
        )
        return build_cache_key(
            provider=prov.name(),
            model=prov.model(),
            schema_version=built.schema_version,
            builder_version=built.builder_version,
            prompt_version=f"{built.prompt_id}@{built.prompt_version}",
            locale=resolved_locale,
            report_hash=resolved_report,
            entity_id=resolved_entity,
            input_hash=built.input_hash,
        )

    def build_generation_request(
        self,
        context: AIContext,
        built: BuiltPrompt,
        *,
        expected_output_type: type[T],
        options: GenerationOptions | None = None,
        provider: str | None = None,
    ) -> GenerationRequest[T]:
        opts = options or self.default_options()
        _builder, prov, opts = self.ensure_ready(
            feature=built.diagnostics.feature,
            provider_name=provider,
            options=opts,
        )
        cache_key = self.build_cache_key_for(
            built,
            context=context,
            provider=prov.name(),
        )
        return GenerationRequest[T](
            context=context,
            built_prompt=built,
            options=opts,
            expected_output_type=expected_output_type,
            provider=prov.name(),
            model=prov.model(),
            cache_key=cache_key,
        )

    def create_session(
        self,
        request: GenerationRequest[T],
        *,
        provider: LLMProvider | None = None,
    ) -> GenerationSession[T]:
        """Create a runtime session; does not start it."""
        resolved = provider or self.resolve_provider(request.provider)
        return GenerationSession(
            request=request,
            provider=resolved,
            cache=self._cache,
        )

    def _prepare_session(
        self,
        *,
        feature: AIFeature | str,
        context: AIContext,
        expected_output_type: type[T],
        provider: str | None,
        options: GenerationOptions | None,
    ) -> GenerationSession[T]:
        builder, prov, opts = self.ensure_ready(
            feature=feature,
            provider_name=provider,
            options=options,
        )
        built = builder.build(context)
        request = self.build_generation_request(
            context,
            built,
            expected_output_type=expected_output_type,
            options=opts,
            provider=prov.name(),
        )
        return self.create_session(request, provider=prov)

    def apply_grounding(
        self,
        *,
        result: T,
        context: AIContext,
        expected_output_type: type[T],
    ) -> T:
        """Run the registered GroundingValidator for ``expected_output_type``."""
        validator = get_grounding_validator(expected_output_type)
        return validator.validate(result, context)

    def _stamp_provenance(self, result: T, *, prompt_version: str, provider: str, model: str) -> T:
        if isinstance(result, BaseModel):
            fields = type(result).model_fields
            updates: dict[str, object] = {}
            if "prompt_version" in fields:
                updates["prompt_version"] = prompt_version
            if "provider" in fields:
                updates["provider"] = provider
            if "model" in fields:
                updates["model"] = model
            if updates:
                return result.model_copy(update=updates)  # type: ignore[return-value]
        return result

    async def _generate(
        self,
        *,
        feature: AIFeature | str,
        context: AIContext,
        expected_output_type: type[T],
        provider: str | None = None,
        options: GenerationOptions | None = None,
    ) -> AIResponse[T]:
        """
        Shared orchestration: builder → cache → provider → grounding → AIResponse.

        Auto-routed calls walk Gemini → OpenRouter → OpenAI. Explicit
        ``provider=`` pins a single provider (same-provider retries only).
        """
        feature_key = resolve_feature(feature)
        allow_cross_provider = provider is None
        candidates = self._provider_candidates_for_generate(
            feature=feature, provider=provider
        )
        preferred = PROVIDER_FALLBACK_CHAIN[0]
        skipped_reasons: list[str] = []
        if allow_cross_provider:
            available_names = {c.name() for c in candidates}
            for hop in PROVIDER_FALLBACK_CHAIN:
                if hop not in available_names:
                    skipped_reasons.append(f"{hop.value}_unavailable")

        last_error: Exception | None = None
        for index, candidate in enumerate(candidates):
            session = self._prepare_session(
                feature=feature,
                context=context,
                expected_output_type=expected_output_type,
                provider=candidate.name(),
                options=options,
            )
            session.start()
            fallback_used = False
            fallback_reason: str | None = None
            if allow_cross_provider and (
                candidate.name() != preferred or skipped_reasons or index > 0
            ):
                fallback_used = candidate.name() != preferred or bool(skipped_reasons)
                if index > 0 and last_error is not None:
                    kind = classify_provider_failure(last_error)
                    prev = candidates[index - 1].name()
                    fallback_reason = (
                        f"{prev.value}_{kind}: {last_error}"
                    )
                elif skipped_reasons and candidate.name() != preferred:
                    fallback_reason = "; ".join(skipped_reasons)
                elif candidate.name() != preferred:
                    fallback_used = True
                    fallback_reason = fallback_reason or "preferred_unavailable"

            try:
                cached = await session.cache.get(session.request.cache_key)
                if isinstance(cached, AIResponse):
                    session.mark_cache_hit()
                    quality = AIQualityMetadata(
                        grounded=True,
                        validation_passed=True,
                        cache_hit=True,
                        provider=cached.provider_metadata.provider,
                        model=cached.provider_metadata.model,
                        prompt_version=session.request.prompt_version,
                        builder_version=session.request.builder_version,
                        schema_version=session.request.schema_version,
                        prompt_hash=session.request.built_prompt.prompt_hash,
                        feature=feature_key,
                    )
                    cached_meta = cached.provider_metadata.model_copy(
                        update={
                            "generation_id": session.generation_id,
                            "feature": feature_key,
                            "cached": True,
                            "generation_status": "cached",
                            "request_id": str(session.generation_id),
                            "fallback_used": cached.provider_metadata.fallback_used,
                            "fallback_reason": cached.provider_metadata.fallback_reason,
                        }
                    )
                    bound = cached.model_copy(
                        update={
                            "generation_id": session.generation_id,
                            "session_id": session.session_id,
                            "quality": quality,
                            "provider_metadata": cached_meta,
                            "telemetry": (
                                cached.telemetry.model_copy(
                                    update={
                                        "generation_id": session.generation_id,
                                        "feature": feature_key,
                                        "cache_hit": True,
                                        "status": "cached",
                                        "generation_status": "cached",
                                        "request_id": str(session.generation_id),
                                        "fallback_used": (
                                            cached.telemetry.fallback_used
                                            if cached.telemetry is not None
                                            else False
                                        ),
                                        "fallback_reason": (
                                            cached.telemetry.fallback_reason
                                            if cached.telemetry is not None
                                            else None
                                        ),
                                    }
                                )
                                if cached.telemetry is not None
                                else session.telemetry
                            ),
                        }
                    )
                    if bound.telemetry is not None:
                        session.telemetry = bound.telemetry
                    session.attach_response(bound)
                    session.finish()
                    return bound

                max_attempts = max(1, self._settings.retry_count + 1)
                response: AIResponse[T] | None = None
                provider_error: Exception | None = None
                for attempt in range(max_attempts):
                    try:
                        response = await session.provider.generate(session.request)
                        break
                    except (AIProviderError, AIConfigurationError) as exc:
                        provider_error = exc
                        last_error = exc
                        if attempt + 1 >= max_attempts:
                            break
                        session.mark_retry()

                if response is None:
                    if (
                        allow_cross_provider
                        and index + 1 < len(candidates)
                        and provider_error is not None
                    ):
                        if session.finished_at is None and session.started_at is not None:
                            session.finish()
                        continue
                    assert provider_error is not None or last_error is not None
                    raise provider_error or last_error  # type: ignore[misc]

                grounded = self.apply_grounding(
                    result=response.result,
                    context=context,
                    expected_output_type=expected_output_type,
                )
                grounded = self._stamp_provenance(
                    grounded,
                    prompt_version=session.request.prompt_version,
                    provider=response.provider_metadata.provider,
                    model=response.provider_metadata.model,
                )
                provider_metadata = response.provider_metadata.model_copy(
                    update={
                        "generation_id": session.generation_id,
                        "feature": feature_key,
                        "request_id": str(session.generation_id),
                        "retry_count": session.retry_count,
                        "fallback_used": fallback_used,
                        "fallback_reason": fallback_reason,
                    }
                )
                quality = AIQualityMetadata(
                    grounded=True,
                    validation_passed=True,
                    cache_hit=False,
                    provider=provider_metadata.provider,
                    model=provider_metadata.model,
                    prompt_version=session.request.prompt_version,
                    builder_version=session.request.builder_version,
                    schema_version=session.request.schema_version,
                    prompt_hash=session.request.built_prompt.prompt_hash,
                    feature=feature_key,
                )
                telemetry = (
                    response.telemetry.model_copy(
                        update={
                            "generation_id": session.generation_id,
                            "feature": feature_key,
                            "request_id": str(session.generation_id),
                            "retry_count": session.retry_count,
                            "fallback_used": fallback_used,
                            "fallback_reason": fallback_reason,
                        }
                    )
                    if response.telemetry is not None
                    else session.telemetry
                )
                bound = response.model_copy(
                    update={
                        "result": grounded,
                        "generation_id": session.generation_id,
                        "quality": quality,
                        "provider_metadata": provider_metadata,
                        "session_id": session.session_id,
                        "telemetry": telemetry,
                    }
                )
                if bound.telemetry is not None:
                    session.telemetry = bound.telemetry
                session.attach_response(bound)
                session.finish()
                if session.telemetry is not None:
                    session.telemetry = session.telemetry.model_copy(
                        update={
                            "latency_ms": session.duration_ms,
                            "status": "success",
                            "generation_status": "success",
                            "retry_count": session.retry_count,
                            "generation_id": session.generation_id,
                            "feature": feature_key,
                            "fallback_used": fallback_used,
                            "fallback_reason": fallback_reason,
                        }
                    )
                final = bound.model_copy(
                    update={
                        "provider_metadata": bound.provider_metadata.model_copy(
                            update={
                                "latency_ms": session.duration_ms,
                                "retry_count": session.retry_count,
                                "generation_id": session.generation_id,
                                "feature": feature_key,
                                "fallback_used": fallback_used,
                                "fallback_reason": fallback_reason,
                            }
                        ),
                        "telemetry": session.telemetry,
                    }
                )
                await session.cache.set(session.request.cache_key, final)
                return final
            except (AIProviderError, AIConfigurationError):
                raise
            except Exception as exc:
                if session.telemetry is not None:
                    session.telemetry = session.telemetry.model_copy(
                        update={
                            "status": "error",
                            "generation_status": "error",
                            "error": str(exc),
                            "retry_count": session.retry_count,
                            "generation_id": session.generation_id,
                            "feature": feature_key,
                            "fallback_used": fallback_used,
                            "fallback_reason": fallback_reason,
                        }
                    )
                if session.finished_at is None and session.started_at is not None:
                    session.finish()
                raise

        assert last_error is not None
        raise last_error

    async def get_cached(self, key: str) -> object | None:
        return await self._cache.get(key)

    async def explain_finding(
        self,
        context: AIContext,
        *,
        provider: str | None = None,
        options: GenerationOptions | None = None,
    ) -> AIResponse[FindingExplanation]:
        return await self._generate(
            feature=AIFeature.FINDING,
            context=context,
            expected_output_type=FindingExplanation,
            provider=provider,
            options=options,
        )

    async def explain_recommendation(
        self,
        context: AIContext,
        *,
        provider: str | None = None,
        options: GenerationOptions | None = None,
    ) -> AIResponse[RecommendationExplanation]:
        return await self._generate(
            feature=AIFeature.RECOMMENDATION,
            context=context,
            expected_output_type=RecommendationExplanation,
            provider=provider,
            options=options,
        )

    async def generate_executive_summary(
        self,
        context: AIContext,
        *,
        provider: str | None = None,
        options: GenerationOptions | None = None,
    ) -> AIResponse[ExecutiveSummary]:
        return await self._generate(
            feature=AIFeature.EXECUTIVE_SUMMARY,
            context=context,
            expected_output_type=ExecutiveSummary,
            provider=provider,
            options=options,
        )

    async def generate_business_summary(
        self,
        context: AIContext,
        *,
        provider: str | None = None,
        options: GenerationOptions | None = None,
    ) -> AIResponse[BusinessSummary]:
        return await self._generate(
            feature=AIFeature.BUSINESS_SUMMARY,
            context=context,
            expected_output_type=BusinessSummary,
            provider=provider,
            options=options,
        )

    async def generate_quick_win(
        self,
        context: AIContext,
        *,
        provider: str | None = None,
        options: GenerationOptions | None = None,
    ) -> AIResponse[QuickWinExplanation]:
        return await self._generate(
            feature=AIFeature.QUICK_WIN,
            context=context,
            expected_output_type=QuickWinExplanation,
            provider=provider,
            options=options,
        )

    async def explain_quick_win(
        self,
        context: AIContext,
        *,
        provider: str | None = None,
        options: GenerationOptions | None = None,
    ) -> AIResponse[QuickWinExplanation]:
        """Alias for ``generate_quick_win`` (backward-compatible name)."""
        return await self.generate_quick_win(
            context, provider=provider, options=options
        )
