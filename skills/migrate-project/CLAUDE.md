# CLAUDE.md — editing the `migrate-project` skill

Scoped guidance for anyone (human or Claude) **editing files under `skills/migrate-project/`**. The
repo-root `AGENTS.md` owns the wider wiring (hook polyglot, version bump, publish flow); this file
owns the invariants that are easy to break when you touch `migrate-project` itself.

**This is a maintainer doc, not runtime.** The skill never point-to-reads it, and it is not loaded
when the plugin is installed in another repo. Zero runtime token cost. Don't reference it from
`SKILL.md` or any role file.

## Architecture in one paragraph

`migrate-project` is a **standalone phase-based orchestrator** — the **brownfield** sibling of
`init-project`. `SKILL.md` is a thin router (`tools: [Agent, Read, AskUserQuestion]`, **never**
`Edit`/`Write`/`Bash`) that dispatches `general-purpose` specialists via **point-to-read**:
**Analyzer** (maps the target → `target-map.md`) → **Mapper** (diffs vs the blueprint → ordered
slices in `plan.md`, its sole writer) → **Migrator** (executes one slice: `git mv` + import rewrite +
convention-gap fill, behavior-preserving) → **Verifier** (per-slice `go build`/`vet`/`test`/golangci
gate) → **Reviewer** (L2 fresh-eyes at the end). It plans-first (CP1 gate before any code), runs the
slice loop continuously, and verifies with three layers (L1 `structurecheck.py` + L2 fresh-eyes + L3
completeness). Per-target state is a resumable markdown plan at `<target>/docs/migration/plan.md`.

## Invariants — do not break

- **The blueprint is REUSED from `init-project`, never duplicated here.** The target-structure
  contract is `INIT_TEMPLATE = <MIGRATE_DIR>/../init-project/assets/template` (its `.kiro/steering/`
  guides + `.golangci.yaml` + `CLAUDE.md`). This skill ships **no copy** of the steering. When
  `account-service`'s conventions change, refresh **init-project's** template (its
  `references/init-project-guide.md` § "Refreshing the snapshot") — `migrate-project` needs no edit.
  This is a **runtime cross-skill dependency**: `migrate-project` requires `init-project` to be
  present as a sibling under `skills/` (both ship in this one plugin). If init-project's template path
  ever moves, fix the `INIT_TEMPLATE` formula in `SKILL.md`, `references/preamble.md`, and the role
  files in one sweep.
- **Point-to-read, never paste; `MIGRATE_DIR` + `INIT_TEMPLATE` on every dispatch.** The specialist is
  `general-purpose` and knows neither path. A dispatch sends the paths; the specialist reads its own
  role spec + the steering. Add a rule a specialist needs to the role file, not to `SKILL.md`'s
  dispatch prompt.
- **The sentinel module is a cross-skill constant.** Installing `.golangci.yaml` into the target
  substitutes init-project's sentinel module `example.com/neo/service` → the target's real module
  path. That literal lives in **two** places — `assets/structurecheck.py` (`SENTINEL_MODULE`) and
  `references/roles/migrator.md`. If init-project changes its sentinel (`scaffold.py`), update both.
- **`structurecheck.py` is a TRIPWIRE, not the gate.** It is stdlib-only, reads the file tree +
  imports (no Go toolchain, no build), and catches *structural* drift (layout, inward-only imports,
  the installed `.golangci.yaml` contract, old-dialect residue). The **authoritative** behavior + lint
  gate is the Verifier's `go build` + `go test` + `golangci-lint` (depguard/forbidigo). Keep
  structurecheck's DRIFT set to high-confidence structural facts; soft heuristics (nested-layer
  placement, ambient calls) stay `NOTE`. **Mutation-test it after any edit** (ad-hoc, not committed —
  same habit as the api-doc L1 scripts): build a tiny CONFORMS tree, apply one defect at a time,
  confirm each is caught + the baseline still CONFORMS. It must also run **CONFORMS on
  `account-service`** (the blueprint itself) and **DRIFT on a pre-migration target** — those two real
  runs are the regression guard.
- **Behavior preservation is the prime directive.** Every slice is `done` only when the **existing**
  tests + build + golangci stay green (`migration-tracking.md` §3). A deleted/disabled test to make a
  slice pass is a defect, not a pass — the Verifier and the L2 Reviewer both flag it.
- **The plan-file is markdown, sole-writer = Mapper, lives in the target.**
  `<target>/docs/migration/plan.md` (+ `target-map.md`) — never HTML, never in this skill's tree. The
  orchestrator reads it to resume; only the Mapper writes it.

## Language rule

Body + every reference file are **English** (language-neutral). **Thai is allowed only in the
`SKILL.md` `description` triggers** — matching `init-project` / `atlassian` (the strict "0 Thai"
English-neutral rule is **neo-scoped**, not plugin-wide; bilingual triggers improve activation on Thai
phrasing). After an edit, the references + the SKILL **body** must stay 0-Thai; the SKILL
**description** carries the Thai triggers by design.

```
# references + SKILL body must be 0; the SKILL description's Thai triggers are expected
python3 - <<'PY'
import glob
for f in glob.glob('skills/migrate-project/**/*.md', recursive=True):
    n = sum(1 for c in open(f, encoding='utf-8').read() if 0x0e00 <= ord(c) <= 0x0e7f)
    if n: print(f"{n:4} {f}")   # only SKILL.md (description triggers) should appear
PY
```

## Reference layout (what reads what)

```
SKILL.md                       thin orchestrator (loaded on every trigger — keep lean)
references/
  preamble.md                  universal agent header (read first on every dispatch): steering-is-truth,
                               never-guess, cleanup, behavior-preservation, status, report-discipline
  migration-tracking.md        the slice progress axis + the resumable plan-file (Mapper + orchestrator)
  migrate-verifier.md          L2 fresh-eyes verifier contract (Reviewer point-to-reads this)
  roles/<role>.md              distilled role capsule (Analyzer / Mapper / Migrator / Verifier)
  templates/                   plan-template.md + target-map-template.md (content specs)
assets/
  structurecheck.py           L1 structural-conformance tripwire (stdlib-only; mutation-tested)
```

## Adding / editing — sync these

1. **Role file** `references/roles/<role>.md` (start from `preamble.md` as the header; distilled).
2. **`SKILL.md`** dispatch block + phase flow if the role / order / checkpoints change; the
   `description` triggers if the trigger surface changes.
3. **`preamble.md`** if a cross-cutting rule changes (every role reads it first).
4. **Cross-references** — every `<file> §<section>` / steering-guide citation still resolves
   (`structure.md`, `domain.md`, … live in `INIT_TEMPLATE`).
5. **Repo root** — README trigger table + `hooks/session-start` overview block + root `AGENTS.md`
   skills list (per root `AGENTS.md` § Skill Authoring Conventions) if the trigger surface changed.

## Verify before commit

1. **`structurecheck.py`** — compiles (`python3 -c "import ast; ast.parse(open(...).read())"`),
   mutation test GREEN, **CONFORMS on `account-service`**, **DRIFT on a pre-migration target**.
2. **Triggers disjoint from `init-project`** — migrate = existing/refactor/restructure; init =
   new/scaffold/empty. No overlapping trigger phrase.
3. **Language scan** — references + SKILL body 0-Thai (snippet above).
4. **Frontmatter** valid YAML; `tools` = `[Agent, Read, AskUserQuestion]`.
5. **Runtime proof** (only the user can do this) — reinstall, then `/migrate-project` against a real
   service through P2 (analyze + plan), confirm the slice plan is sane before any code moves.
6. **Bump the plugin version** following root `AGENTS.md` § Versioning and Releases for every
   publishable change. Don't reuse the skill `metadata.version` for that — they're separate.
