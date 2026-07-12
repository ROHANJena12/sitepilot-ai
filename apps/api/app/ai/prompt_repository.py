"""Prompt repository — load versioned markdown templates (never hardcode bodies)."""

from __future__ import annotations

from pathlib import Path

from app.ai.constants import PROMPT_IDS
from app.ai.exceptions import PromptNotFound, PromptValidationError
from app.ai.models import PromptTemplate, RenderedPrompt
from app.ai.validators import (
    extract_placeholders,
    extract_prompt_version,
    render_prompt,
    validate_prompt_document,
)

_DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class PromptRepository:
    """
    Load and validate prompt templates from disk.

    Supports:
    - prompt versioning via ``Prompt-Version`` header
    - placeholder validation
    - future localization (``prompts/<locale>/`` then fallback to root)
    - optional hot reload (bypass in-memory cache)
    """

    def __init__(
        self,
        *,
        prompts_dir: Path | None = None,
        locale: str = "en",
        hot_reload: bool = False,
        validate_on_load: bool = True,
    ) -> None:
        self._prompts_dir = prompts_dir or _DEFAULT_PROMPTS_DIR
        self._locale = locale
        self._hot_reload = hot_reload
        self._validate_on_load = validate_on_load
        self._cache: dict[tuple[str, str], PromptTemplate] = {}

    @property
    def prompts_dir(self) -> Path:
        return self._prompts_dir

    def list_prompt_ids(self) -> list[str]:
        """Return available prompt ids (bundled defaults + any extra .md files)."""
        found = {path.stem for path in self._prompts_dir.glob("*.md")}
        locale_dir = self._prompts_dir / self._locale
        if locale_dir.is_dir():
            found |= {path.stem for path in locale_dir.glob("*.md")}
        # Prefer known order, then extras.
        ordered = [pid for pid in PROMPT_IDS if pid in found]
        ordered.extend(sorted(found - set(PROMPT_IDS)))
        return ordered

    def get(self, prompt_id: str, *, locale: str | None = None) -> PromptTemplate:
        loc = locale or self._locale
        cache_key = (prompt_id, loc)
        if not self._hot_reload and cache_key in self._cache:
            return self._cache[cache_key]

        path = self._resolve_path(prompt_id, loc)
        if path is None:
            raise PromptNotFound(
                f"Prompt '{prompt_id}' not found (locale='{loc}', "
                f"dir='{self._prompts_dir}')."
            )

        text = path.read_text(encoding="utf-8")
        if self._validate_on_load:
            placeholders = validate_prompt_document(text, prompt_id=prompt_id)
            version = extract_prompt_version(text)
        else:
            placeholders = extract_placeholders(text)
            try:
                version = extract_prompt_version(text)
            except PromptValidationError:
                version = "v0"

        template = PromptTemplate(
            prompt_id=prompt_id,
            version=version,
            body=text,
            placeholders=placeholders,
            locale=loc,
            path=str(path),
        )
        self._cache[cache_key] = template
        return template

    def render(
        self,
        prompt_id: str,
        variables: dict[str, str],
        *,
        locale: str | None = None,
    ) -> RenderedPrompt:
        template = self.get(prompt_id, locale=locale)
        text = render_prompt(template.body, variables)
        return RenderedPrompt(
            prompt_id=template.prompt_id,
            version=template.version,
            text=text,
            variables=dict(variables),
        )

    def reload(self) -> None:
        """Clear cached templates (explicit hot reload)."""
        self._cache.clear()

    def _resolve_path(self, prompt_id: str, locale: str) -> Path | None:
        locale_path = self._prompts_dir / locale / f"{prompt_id}.md"
        if locale_path.is_file():
            return locale_path
        root_path = self._prompts_dir / f"{prompt_id}.md"
        if root_path.is_file():
            return root_path
        return None
