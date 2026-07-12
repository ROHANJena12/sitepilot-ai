# apps/web

**SitePilot AI** — Next.js (App Router) frontend using Feature-Sliced Design.

## Stack

- Next.js 15 + React 19 + TypeScript (strict)
- Tailwind CSS + design tokens (`styles/variables.css`)
- next-themes (dark-first)
- TanStack Query, Axios, Zod, React Hook Form
- Framer Motion, Lucide React, Recharts
- shadcn/ui configured (`components.json` → `shared/ui`)

## Structure

See root [ARCHITECTURE.md](../../docs/ARCHITECTURE.md) and this app's FSD layers: `app/`, `features/`, `entities/`, `widgets/`, `shared/`.

## Local development

```bash
# from repo root
pnpm install
pnpm --filter @sitepilot/web dev
# or
./scripts/run-web.sh
```

Copy `apps/web/.env.example` → `apps/web/.env.local` and set `NEXT_PUBLIC_API_URL`.

## Scripts

| Script | Command |
|---|---|
| Dev | `pnpm --filter @sitepilot/web dev` |
| Build | `pnpm --filter @sitepilot/web build` |
| Lint | `pnpm --filter @sitepilot/web lint` |
| Typecheck | `pnpm --filter @sitepilot/web typecheck` |

## Status

Foundation configured. Route pages remain placeholders — no product UI yet.
