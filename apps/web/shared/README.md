# Shared

Cross-cutting building blocks reused by `entities/`, `features/`, `widgets/`, and `app/`.

## Structure

| Path | Responsibility |
|------|----------------|
| `ui/` | Design-system primitives and presentational atoms (no feature logic). |
| `hooks/` | Reusable React hooks (data, theme, storage). |
| `services/` | API service modules calling backend endpoints. |
| `lib/` | Low-level libraries (HTTP client, validators, helpers). |
| `config/` | Runtime/site configuration. |
| `constants/` | Route maps, color tokens, animation tokens. |
| `providers/` | App-level React context providers. |
| `utils/` | Pure utilities (formatters, calculations, validators). |
| `types/` | Shared TypeScript contracts for the web app. |

## Rules

- Do not import from `features/`, `widgets/`, or `app/`.
- Prefer promoting code here only after reuse across two or more slices.
- Keep modules as TODO stubs until implementation begins.

## Status

Scaffold only. Implementation pending.
