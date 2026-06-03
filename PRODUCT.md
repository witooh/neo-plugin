# Product

> Scope: the **"Design Docs" HTML site** that the `neo-team` skill generates into a project's
> `docs/design/` — i.e. the shared design system in `skills/neo-team/assets/` (styles.css +
> components + page shell). Not the plugin tooling itself.

## Register

product

## Users

Internal engineering team using the neo-team skill — Business Analysts, Architects, QA, developers — plus AI tools/agents that read the generated HTML. They open the site to read, review, and trace acceptance criteria, system designs, API contracts, test cases, and traceability for a feature. Context: reviewing dense spec content on a laptop, switching between docs, comparing status (ready/blocked/pending) across many items. Thai-language content with English technical terms.

## Product Purpose

The human-facing render of design docs that neo-team specialists generate. It exists because dense markdown specs don't get read; the HTML turns them into a scannable, interactive site (collapsible cards, sortable tables, status filters, trace matrices, mermaid diagrams, light/dark). Success = a reviewer finds and judges a spec item in seconds, and the raw HTML stays lean enough that an AI/tool reads only content, not styling (CSS/JS external; token cost ≈ markdown). Hard constraints: **offline, zero-build, framework-free, external CSS/JS**.

## Brand Personality

Clean, precise, calm — an engineer's reference tool, not a product pitch. Three words: **precise, quiet, trustworthy**. Target feel: Linear / Stripe docs / Vercel — confident restraint, generous breathing room, depth from craft (light, hairlines, subtle elevation) rather than decoration. Reads as "made by people who care about detail," never loud.

## Anti-references

- **Marketing / SaaS landing pages** — no hero gradients, no oversized display type, no decorative flourish, no "AI slop."
- **Flat & dull** — avoid a lifeless, all-gray, depthless sheet; the team wants tangible refinement (considered spacing, hairline structure, restrained elevation).
- **Cramped / fatiguing density** — not a wall of tightly packed rows; whitespace and rhythm matter even though content is dense.

## Design Principles

1. **Content is the product; chrome recedes.** Every visual choice serves scanning and judging spec items faster; styling never competes with the text.
2. **Depth through craft, not decoration.** Hierarchy comes from spacing rhythm, hairlines, type weight, and restrained elevation — never gradients, heavy borders, or ornament.
3. **Status must be instant.** Ready/blocked/pending + priority are the most-scanned signals; they read at a glance and can't drift (single source → derived).
4. **Calm under density.** Pages hold many items; generous rhythm and quiet color keep them readable, not fatiguing.
5. **Lean by construction.** Rendered HTML stays semantic and token-light (external CSS/JS); polish lives in shared assets, never inline.

## Accessibility & Inclusion

- WCAG AA contrast: body ≥4.5:1, large/bold ≥3:1, in **both** light and dark (`[data-theme]`).
- Thai + Latin: type scale and line-height tuned for Thai glyph height (taller line-height; no tight tracking on Thai).
- `prefers-reduced-motion`: transitions degrade to instant/crossfade.
- Status never by color alone (badge text + position reinforce it).
- Keyboard `:focus-visible` for cards, tabs, filters, sortable headers.
