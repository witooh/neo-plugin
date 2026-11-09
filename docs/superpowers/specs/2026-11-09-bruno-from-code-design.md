# Design: `bruno` generated from code

**Status:** approved
**Supersedes:** the source-of-truth model, the Modes section and the `migrate.py` component of
`docs/superpowers/specs/2026-11-09-bruno-skill-design.md`. Everything not named here stays as that spec
says: collection layout, `docs:` layout, table rules, K1–K11, `driftcheck.py`, Audience.

## Goal

Go code is the single source of truth for an HTTP API. The `bruno` skill reads the code and generates
the Bruno OpenCollection under `bruno/`, with a `docs:` block per request. Nobody edits `docs:` by hand,
because a second hand-kept source would drift from the code.

## Decisions

| # | Decision | Reason |
| --- | --- | --- |
| 1 | Code is the single source of truth; `bruno/` is generated from it | The user's direction. Spec-first design is rare. |
| 2 | Two modes: **Generate** (writes) and **Check** (read-only) | Draft, Update, Validate, Drift and Migrate collapse into these two. |
| 3 | **Draft is removed.** Designing an API before code is not a mode. The user directs such a case by hand, and the next Generate from code replaces it. | It is rare, and the user prefers case-by-case. |
| 4 | **Migrate is removed**, with `migrate.py`, `test_migrate.py` and `testdata/legacy/`. A repo with a legacy `docs/api/` runs Generate from code. The skill then asks before removing `docs/api/`. | Code is the source; legacy prose is not carried over. |
| 5 | The agent authors from code (approach A), and deterministic gates check the result: `brunocheck.py` checks the format, `driftcheck.py` checks structural fidelity to Go. There is no generator script. | `driftcheck` already proves routes, fields, M/O and types (parity 100/100 against the legacy checker). A generator built on the same heuristics would turn today's NOTEs into silently wrong tables. |
| 6 | Every `docs:` statement traces to code. Where the code says nothing, the docs say nothing: a field without a comment gets a short neutral description, and no business meaning is guessed. | A source of truth that invents content is not one. |
| 7 | Generate's default scope is the endpoints the user names. If none are named, the scope is new routes plus the requests `driftcheck` reports as drifted. A full regeneration happens only when `bruno/` is missing or the user asks for one. | Rewriting prose for unchanged endpoints creates churn in the diff. |
| 8 | Generate rewrites `docs:` and makes `http.method` and `http.url` follow the code. It keeps `http.auth`, `http.headers` values, `runtime` (scripts, variables), `settings`, `info.seq` and environment values. It keeps `http.body` when its key set still matches the DTO; otherwise it regenerates the body from the DTO. | These runnable parts cannot be derived from code. |
| 9 | A request with no route in the code is listed as an orphan and deleted only after the user confirms. | Deleting user files needs a yes. |
| 10 | The K11 NOTE on `Not documented in the source spec.` stays. | Any collection migrated with neo 5.6.0 may still carry the sentence. |

## Generate flow

1. **Locate:** the Go module root and `bruno/`. If `bruno/` is missing, confirm its location before
   creating it. If `docs/api/` exists, say it is obsolete and offer to remove it once Generate passes.
2. **Inventory:** the agent reads the router for routes and cross-checks them against `driftcheck`'s
   Go route list.
3. **Author** each in-scope endpoint by reading the code in this order:
   - the handler;
   - the request DTO, whose binding tags give Mandatory;
   - the response DTO;
   - the usecase, for business logic and error paths;
   - the error catalog, for codes and messages.

   Write the request in the order `info → http → runtime → settings → docs`, with `docs:` following
   `references/docs-template.md`.
4. **Preserve** per Decision 8.
5. **Orphans** per Decision 9.
6. **Verify:**
   - **L1:** `brunocheck.py bruno` exits 0, and `driftcheck.py bruno --src .` shows 0 DRIFT lines for the
     in-scope request files. DRIFT outside the scope is reported and left alone.
   - **L1.5:** offer the L2 pass (default yes).
   - **L2:** the verifier checks that each Business Logic sentence and each error row traces to a
     handler or usecase line, that the Audience rule holds, and that headers and auth are mapped.
   - **L3:** every in-scope route has a request, and every error path in the usecase has an error row.

**Check** runs the two L1 scripts and writes nothing. It reports format ERRORs and drift, meaning code
that changed since the last Generate.

## Changes

**Delete:** `skills/bruno/assets/migrate.py`, `skills/bruno/assets/test_migrate.py`,
`skills/bruno/assets/testdata/legacy/`.

**Scripts:**
- `test_driftcheck.py:80` drops `migrate.py` from the missing-PyYAML loop.
- `docsparse.py:4` drops `migrate.py` from the docstring.
- `brunocheck.py` is unchanged.
- `driftcheck.py` changes in three places. The acceptance run and the final review found these on
  real repos:
  - it skips modules nested below a `go.mod` root (`tools/*`, `.claude/worktrees/*`, templates);
  - it counts inline handler closures such as `r.GET("/health", func(c *gin.Context) {…})`;
  - Mandatory: a request field is `Yes` only with `binding`/`validate:"required"`, and a response
    field is `No` when it is a pointer or `omitempty`. This was the user's decision on 2026-11-09:
    "ตามหลักมันคือ ไม่บังคับ" ("by principle it is not mandatory"). Collections written under the
    old rule show M/O DRIFT until a Generate rewrites them.

**Skill text:**
- `SKILL.md`:
  - The description and triggers: "gen bruno จาก code", "อัปเดต bruno", "เช็ค bruno ตรง code ไหม",
    "validate bruno".
  - The two modes, the Generate flow and the verify layers above.
  - Step 2M and Draft are gone.
  - "What this skill is NOT" adds the spec-first line (Decision 3).
- `references/bruno-verifier.md`: fidelity is checked against code, not intent; Migrate sampling is dropped.
- `references/docs-template.md`: the Migrate and Draft text is removed, and Decision 6 is added.
- `references/drift-verifier.md` and `references/yaml-reference.md`: any Migrate reference is removed.
- `agents/openai.yaml`: `short_description: "Bruno collection generated from Go code"`.

**Dependents:**
- `README.md:132`: the `bruno` row says the collection is generated from Go code and lists the format
  and drift checks.
- `skills/init-project/assets/template/bruno/README.md:6`, `.kiro/steering/bruno.md:8` and
  `CLAUDE.md:119`: "API source of truth" becomes "generated from code with the `bruno` skill; the code
  is the source of truth".
- `skills/bug-hunter/SKILL.md:125`: the chain becomes
  `bruno ← code ← ticket/spec ← docs/knowledge/{contracts,requirements}/ ← the originating issue`.
- The old spec gets a first line: `Superseded in part by 2026-11-09-bruno-from-code-design.md`.

## Testing and success criteria

| # | Criterion | Measured by |
| --- | --- | --- |
| 1 | Remaining unit tests pass | `python3 -m unittest discover -s skills/bruno/assets -p 'test_*.py'` (PyYAML interpreter) |
| 2 | Packages valid | the six validators in `AGENTS.md`, `claude plugin validate .`, `grok plugin validate .` |
| 3 | No stale text | `/usr/bin/grep` finds no `Migrate`, `migrate.py`, `Draft` or `docs/api` under `skills/bruno/`, and no "API source of truth" for `bruno` under `skills/`, `README.md` or `AGENTS.md` |
| 4 | Generate works from code | A fresh agent follows the new `SKILL.md` on a scratch copy of `tcrb/manual-posting-service` (6 Go routes), doing a full Generate. Result: `brunocheck` 0 ERROR and `driftcheck` 0 DRIFT. |
| 5 | Check sees code change | In that copy, change one DTO field. Check reports DRIFT on that endpoint's request only. |
| 6 | Scoped Generate does not churn | A scoped Generate for that endpoint gives 0 DRIFT, and every other request file is byte-identical to before. |

The real repos under `/Users/witoo.h/dev/tcrb/` stay read-only. Criteria 4–6 run on scratch copies.

## Risks

- **Prose L2 is not deterministic.** Business Logic and descriptions have no L1 gate, so L2 is the only
  check that they come from code.
- **`driftcheck` heuristics.** Where it emits a NOTE (unconfident groups, inline params, envelopes), L2
  must confirm by reading the code.
- **Legacy prose is lost.** Removing `docs/api/` drops prose that code never held (measured: business
  logic in 34/39 account, 62/62 consent, 20/24 product files). This is accepted by Decision 1 and can
  be recovered from git history.
- **Breaking change.** Removing Migrate and Draft breaks the `bruno` skill's contract. The version bump
  is decided at release.
