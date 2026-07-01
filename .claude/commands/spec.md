---
description: Start spec-driven development — write a structured specification before writing code
---

Invoke the neo:spec-driven-development skill.

**First, load existing context from the knowledge base.** Before asking the user anything, check `docs/knowledge/` — start with its `INDEX.md` — for material relevant to this feature (this is where `/ingest` curates JIRA cards, docs, and specs). Read every relevant entry in full and treat it as primary source context for the spec. **Never ask the user a question the knowledge base already answers** — read first, then ask only about what the request and the KB leave genuinely unresolved. If `docs/knowledge/` is absent or empty, proceed with the request as the only context.

Begin by understanding what the user wants to build. Ask clarifying questions about:
1. The objective and target users
2. Core features and acceptance criteria
3. Tech stack preferences and constraints
4. Known boundaries (what to always do, ask first about, and never do)

Then generate a structured spec covering all six core areas: objective, commands, project structure, code style, testing strategy, and boundaries.

**Always include an `## Acceptance Criteria` section** — this is the canonical criteria section; use it in place of the skill template's generic "Success Criteria" when the feature has discrete criteria. If the source material — a JIRA card, a requirements doc, or ingested `docs/knowledge/` — already lists acceptance criteria, **capture them faithfully**: preserve every one, keep the original intent, and never silently drop, merge, or invent criteria. If the source has none, derive testable criteria from the objective. Give each a stable ID (`AC-001`, `AC-002`, …) — this is the id the neo:api-spec skill records in `covers_ac` and that downstream tests trace back to. Every AC must be independently testable (a passing test can demonstrate it).

**Include a `## Sources` section** in the spec that lists every `docs/knowledge/` entry the spec drew on (plus any JIRA card or external doc) — link each one (e.g. `docs/knowledge/<topic>.md`) so every requirement is traceable back to its curated source. Omit the section only when there were genuinely no sources to cite.

Ask the user for the feature name or JIRA card id to use as the task folder name (`<card>`). Save the spec to `docs/tasks/<card>/spec.md` (create the folder if it doesn't exist) and confirm with the user before proceeding.

If the spec describes an HTTP API, follow up by invoking the neo:api-spec skill in **Draft** mode to author the `docs/api/` contract spec-first — from the acceptance criteria, before any code exists — so implementation has a contract to build against. Skip this when the feature exposes no HTTP endpoints.

Once api-spec has authored `docs/api/`, keep the endpoint contract in **one place only**: replace any endpoint-contract detail in the spec (request/response shapes, per-endpoint field tables, error taxonomy) with a short **reference to `docs/api/`** (link `docs/api/index.md` and the relevant `<domain>/<endpoint>.yaml`, listing method + path + `covers_ac`). The spec keeps the business intent and acceptance criteria; `docs/api/` is the single source of truth for the contract. Do not duplicate the contract in both.
