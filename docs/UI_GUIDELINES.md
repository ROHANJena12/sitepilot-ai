# UI Guidelines

**Product:** SitePilot AI  
**Status:** Guidelines only — no UI implementation in this scaffold.

---

## 1. Principles

1. **Clarity over novelty** — insights must be scannable and actionable.
2. **One job per view** — avoid dashboard clutter.
3. **Brand first** — SitePilot AI identity should be unmistakable on primary surfaces.
4. **Accessible by default** — WCAG-oriented contrast, focus, and semantics.
5. **Shared primitives** — ship UI through `packages/ui`, not one-off app copies.

## 2. Ownership

| Concern | Location |
|---------|----------|
| Components & tokens | `packages/ui` |
| App composition | `apps/web` |
| Brand assets | `assets/` |

## 3. Visual direction (high level)

- Prefer purposeful typography (avoid generic system-only stacks in product UI).
- Use atmosphere (gradients / imagery) thoughtfully; avoid empty flat panels as the sole visual idea.
- Avoid overused AI-SaaS tropes (generic purple glows, excessive pills, card-heavy heroes).

## 4. Motion

- Motion communicates hierarchy and state, not decoration.
- Prefer subtle transitions on navigation and insight reveal.

## 5. Content

- Prefer short, action-oriented copy.
- Recommendations should state *what*, *why*, and *next step*.

## 6. Out of scope here

Component APIs, Figma tokens, and Storybook setup belong to later implementation phases.
