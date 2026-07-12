#!/usr/bin/env python3
"""Temporary helper — list Gemini models that support generateContent.

Reads GEMINI_API_KEY from apps/api/.env. Not part of the application.
Do not commit.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / "apps" / "api" / ".env"
LIST_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def load_gemini_api_key(env_path: Path) -> str:
    if not env_path.is_file():
        raise SystemExit(f"Missing env file: {env_path}")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        if key.strip() == "GEMINI_API_KEY":
            api_key = value.strip().strip("'").strip('"')
            if not api_key:
                raise SystemExit("GEMINI_API_KEY is empty in apps/api/.env")
            return api_key
    raise SystemExit("GEMINI_API_KEY not found in apps/api/.env")


def fetch_models(api_key: str) -> list[dict]:
    models: list[dict] = []
    page_token: str | None = None
    while True:
        params: dict[str, str] = {"key": api_key, "pageSize": "100"}
        if page_token:
            params["pageToken"] = page_token
        url = f"{LIST_URL}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(f"HTTP {exc.code} from Gemini models API:\n{body}") from exc
        except urllib.error.URLError as exc:
            raise SystemExit(f"Request failed: {exc}") from exc

        models.extend(payload.get("models") or [])
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return models


def model_id(name: str) -> str:
    # API returns "models/gemini-2.0-flash" — print the id after the slash.
    return name.split("/", 1)[-1] if name else name


def supports_generate_content(model: dict) -> bool:
    methods = model.get("supportedGenerationMethods") or []
    return "generateContent" in methods


def recommend(models: list[dict]) -> None:
    ids = [model_id(m.get("name", "")) for m in models]
    id_set = set(ids)

    # Prefer current stable Flash for structured JSON exec summaries.
    exec_candidates = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
    ]
    fastest_candidates = [
        "gemini-2.0-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-1.5-flash",
    ]
    cheapest_candidates = [
        "gemini-2.0-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-2.5-flash",
    ]

    def first_available(candidates: list[str]) -> str | None:
        for candidate in candidates:
            if candidate in id_set:
                return candidate
        # Fuzzy: any id containing the token (excluding tuning/embedding).
        for candidate in candidates:
            for mid in ids:
                if candidate in mid and "embed" not in mid.lower():
                    return mid
        return None

    best_exec = first_available(exec_candidates) or (ids[0] if ids else None)
    fastest = first_available(fastest_candidates) or best_exec
    cheapest = first_available(cheapest_candidates) or fastest

    print("\n=== Recommendations ===")
    print(f"Best model for Executive Summary: {best_exec}")
    print(f"Fastest model:                    {fastest}")
    print(f"Cheapest/free model:              {cheapest}")
    print(
        "\nNotes: Google AI Studio free tier typically includes Flash / Flash-Lite. "
        "Flash balances quality + latency for grounded JSON summaries; "
        "Flash-Lite is usually cheapest/fastest when quality headroom is not needed."
    )


def main() -> int:
    api_key = load_gemini_api_key(ENV_PATH)
    print(f"Loaded GEMINI_API_KEY from {ENV_PATH} (present: yes)")
    print(f"GET {LIST_URL}\n")

    all_models = fetch_models(api_key)
    usable = [m for m in all_models if supports_generate_content(m)]
    usable.sort(key=lambda m: model_id(m.get("name", "")))

    print(f"Models supporting generateContent: {len(usable)}\n")
    for model in usable:
        mid = model_id(model.get("name", ""))
        display = model.get("displayName") or mid
        methods = model.get("supportedGenerationMethods") or []
        print(f"- id: {mid}")
        print(f"  display name: {display}")
        print(f"  supportedGenerationMethods: {methods}")
        print()

    if not usable:
        print("No models with generateContent were returned for this key.")
        return 1

    recommend(usable)
    return 0


if __name__ == "__main__":
    sys.exit(main())
