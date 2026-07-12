# Contributing

Thank you for contributing to SitePilot AI.

---

## Ground rules

1. Keep changes scoped — prefer small, reviewable PRs.
2. Do not commit secrets (use `.env.example` as the template).
3. Follow the monorepo boundaries described in [ARCHITECTURE.md](./ARCHITECTURE.md).
4. Update docs when behavior or structure changes.

## Repository layout

- `apps/*` — deployable applications
- `packages/*` — shared libraries
- `docs/*` — product & engineering docs
- `infrastructure/*` — deployment & IaC
- `scripts/*` — developer helpers

## Development setup (when apps exist)

```bash
cp .env.example .env
# pnpm install   # after package manifests are filled in
./scripts/setup.sh
```

## Code review

- CI must pass (see `.github/workflows/ci.yml`).
- Prefer clear commit messages that explain *why*.
- Link related issues / docs in the PR description.

## Reporting issues

Include reproduction steps, expected vs actual behavior, and environment details (OS, Node/Python versions).

## Security

Do not open public issues for vulnerabilities. See [SECURITY.md](./SECURITY.md).
