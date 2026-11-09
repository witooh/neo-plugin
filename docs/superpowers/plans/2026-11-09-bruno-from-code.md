# Bruno From Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the `bruno` skill into a generator that writes the Bruno OpenCollection from Go code, which is the single source of truth. It has two modes: Generate and Check.

**Architecture:** The host agent reads the code (router, handler, DTOs, usecase, error catalog) and writes the requests and `docs:`. Two existing deterministic gates check the result: `brunocheck.py` for format and `driftcheck.py` for structural fidelity to Go. Migrate and Draft are removed. No new script is written.

**Tech Stack:** Markdown skill text; Python 3 stdlib + PyYAML (existing assets, `unittest`); Node validators.

**Spec:** `docs/superpowers/specs/2026-11-09-bruno-from-code-design.md` (read it in full). It supersedes parts of `docs/superpowers/specs/2026-11-09-bruno-skill-design.md`. That older spec still governs the layouts, table rules and K1–K11.

## Global Constraints

- **No commits, no staging.** The user's rule is "never commit or push unless explicitly asked".
- PyYAML interpreter for every local run: `/opt/homebrew/bin/python3.14`. The default `python3` has no PyYAML. Shipped commands keep `python3 "$ASSET_DIR/<script>"`.
- Use `/usr/bin/grep` for every verification grep. The shell's `grep` is a wrapper that silently skips files named `CLAUDE.md`.
- Inside `skills/`, `AGENTS.md` and `README.md`, never write `api-spec`, `open-collection`, `openapi-doc` or `confluence-api-doc` (`DEAD_SKILLS`).
- Skill `description` must be ≤ 1024 characters, in the third person, with the "what" first and then the "when".
- These are unchanged and copied verbatim:
  - Field table header: `Field Name | Type | Mandatory | Description | Possible Value`.
  - Error table header: `Status | Response Code | Error Code | Error Messages | Description`.
  - Request top-level order: `info → http → runtime → settings → docs`.
- Modes are exactly **Generate** and **Check**.
- Generate's default scope: the endpoints the user names. If none are named, new routes plus the requests `driftcheck` reports as drifted. A full regeneration happens only when `bruno/` is missing or the user asks.
- Generate preserves `http.auth`, `http.headers` values, `runtime`, `settings`, `info.seq` and environment values.
  - It keeps `http.body` when its key set still matches the DTO.
  - It rewrites `docs:`.
  - `http.method` and `http.url` follow the code.
- Orphans and `docs/api/` removal both need user confirmation.
- `/Users/witoo.h/dev/tcrb/*` is read-only. Acceptance runs on scratchpad copies.

## Review Focus

1. **Default scope on a repo with wide drift.** When `driftcheck` flags many requests and the user names none, the user should see the scope list before anything is written. Task 2 makes SKILL.md print the scope before writing, and Task 4 observes it.
2. **A route `driftcheck` cannot parse** (non-gin registration, nested groups). The agent's own router reading must still inventory it, and the gap is reported as a NOTE. Task 2 puts this in Step "Inventory", and Task 4 reports any route missing from `driftcheck`'s list.
3. **A legacy `docs/api/` present.** The skill offers removal only after both L1 gates pass and never removes it unasked. Task 2 covers the text, and Task 4 observes the offer, since `manual-posting-service` has `docs/api/`.
4. **Orphan requests.** Requests with no route stay on disk until the user confirms. Task 4 checks that they are still present.
5. **Audience leaks from code-derived prose** (`internal/…` paths, Go file:line, package names). K10 and L2 catch them. Task 4 requires `brunocheck` 0 ERROR, which includes K10.

---

### Task 1: Remove Migrate assets

**Files:**
- Delete: `skills/bruno/assets/migrate.py`, `skills/bruno/assets/test_migrate.py`, `skills/bruno/assets/testdata/legacy/`
- Modify: `skills/bruno/assets/test_driftcheck.py:80`, which loops over `("driftcheck.py", "brunocheck.py", "migrate.py")`. Drop `"migrate.py"`.
- Modify: `skills/bruno/assets/docsparse.py:2-4`. Line 2 says the docstring's `docs:` block "is the API source of truth" → change it to "holds the endpoint contract". Line 4 says "Imported by brunocheck.py, migrate.py and driftcheck.py" → drop `migrate.py`.
- Modify: `skills/bruno/assets/brunocheck.py:2`. "are the API source of truth" → "hold the endpoint contracts".
- Modify: `skills/bruno/assets/driftcheck.py:7-9`, the docstring under "WHY THIS EXISTS".
  - Today: "Each Bruno request file's `docs:` markdown is the SOURCE OF TRUTH for its endpoint. This script scans the Go code and reports where the implementation has DRIFTED from that contract."
  - Change to: "Go code is the SOURCE OF TRUTH; each Bruno request file's `docs:` markdown is generated from it. This script scans the Go code and reports where a request's `docs:` has DRIFTED from the implementation (a stale contract)."
  - Keep the rest of the docstring.
- These are docstring-only edits. The spec says `brunocheck.py` and `driftcheck.py` are "unchanged"; read that as their *behavior*. Their docstrings must stop contradicting the new model, and criterion 3 greps for "API source of truth". No code line, message string or test changes.

**Interfaces:**
- Produces: the asset set `docsparse.py`, `brunocheck.py`, `driftcheck.py` and their tests. Their CLIs and exit codes are unchanged. Task 2 documents them.

- [ ] **Step 1: Record the baseline**

  Run `/opt/homebrew/bin/python3.14 -B -m unittest discover -s skills/bruno/assets -p 'test_*.py'`.
  Expected: `Ran 82 tests` … `OK`.

- [ ] **Step 2: Delete the three paths and make the four edits**

- [ ] **Step 3: Verify**

  ```bash
  /opt/homebrew/bin/python3.14 -B -m unittest discover -s skills/bruno/assets -p 'test_*.py'
  /usr/bin/grep -rnE "migrate|API source of truth|SOURCE OF TRUTH for its endpoint" skills/bruno/assets
  ```

  Expected:
  - `Ran 59 tests` … `OK`. The 23 tests of `test_migrate.py` are gone.
  - `grep` prints nothing. Leave `brunocheck.py:7` ("ported from the legacy collection checker") as it is: it records history and is not stale.

---

### Task 2: Skill text for Generate and Check

**Files:**
- Modify (rewrite): `skills/bruno/SKILL.md` (206 lines today)
- Modify: `skills/bruno/references/bruno-verifier.md`, `references/docs-template.md`, `references/drift-verifier.md`, `references/yaml-reference.md`
- Modify: `skills/bruno/agents/openai.yaml:3` → `short_description: "Bruno collection generated from Go code"`

**Interfaces:**
- Consumes these CLIs, unchanged:
  - `brunocheck.py <bruno-root>`: 0 = PASS, 1 = ERROR, 2 = usage or missing PyYAML.
  - `driftcheck.py [<bruno-root>] --src <go-root>`: 0 = PASS, 1 = DRIFT, 2 = missing root, missing Go source, or missing PyYAML. Output is grouped per request file: `✓|✗ <file> … DRIFT`, then the `DRIFT`/`NOTE` lines.

**`SKILL.md` content:**
- **Frontmatter `name: bruno`.** The description says:
  - it generates the Bruno OpenCollection in `bruno/` from Go code;
  - code is the single source of truth;
  - each request's `docs:` holds the contract;
  - there are two modes, Generate and Check, and a three-layer verify.

  Triggers: "gen bruno จาก code", "สร้าง bruno", "อัปเดต bruno", "เช็ค bruno ตรง code ไหม", "validate bruno", "api drift".
- **Keep** the existing Audience section, Output location, `ASSET_DIR`/`SKILL_DIR`, and the verify-loop rule: on exit 1, fix and re-run, and escalate after about three rounds.
- **Mode table** with Generate and Check, using the columns Writes / Input / L1 / L2 / L3, per the spec.
- **Generate steps**, numbered as the spec's Generate flow 1–6. They must include:
  - Print the scope list (endpoint → request file) before writing anything (Review Focus 1).
  - Inventory routes from the router yourself. Cross-check against `driftcheck`'s Go route list, and report each route it missed as a NOTE (Review Focus 2).
  - The code reading order: handler → request DTO (binding tags give Mandatory) → response DTO → usecase → error catalog.
  - The preserve rules (spec Decision 8) and orphan confirmation (Decision 9).
  - Every statement traces to code, and a field without a comment gets a short neutral description (Decision 6).
  - With `docs/api/` present, offer removal only after both L1 gates pass (Review Focus 3).
- **L1 for Generate:** `brunocheck.py bruno` exits 0, and the `driftcheck.py bruno --src <go-root>` output shows 0 DRIFT lines for in-scope request files. Out-of-scope DRIFT is reported, not fixed. Exit 2 means a missing input and is never PASS.
- **L1.5:** the `AskUserQuestion` offer (default yes).
- **L2:** one prompt block for `references/bruno-verifier.md` (Generate) and one for `references/drift-verifier.md` (Check, and the `driftcheck` NOTEs from Generate), each with `SKILL_DIR` paths.
- **L3:**
  - Generate: every in-scope route has a request, and every error path in the usecase has an error row.
  - Check: both the route and the request inventories are compared.
- **Output block:** `## Bruno: <Generate / Check>`, plus the counts the steps produce (scope, created, updated, orphans, ERROR, DRIFT, NOTE).
- **"What this skill is NOT"** adds: designing an API before code exists is not a mode. The user directs that case by hand, and the next Generate from code replaces it. Keep the Confluence line.
- Nothing about Draft, Migrate, Update, Validate or `docs/api` beyond the removal offer.

**References:**
- `bruno-verifier.md`:
  - The ground truth is the Go code: handler, DTOs, usecase, error catalog. It is no longer "source-of-intent".
  - Checks 1–5 are re-stated against code. For example, check 5: each `## Business Logic` sentence cites a usecase line.
  - Remove the Draft and Migrate text at `:5,19,52-53,65-81,115,123,128,140`, adjusting wherever the wording names intent.
  - Every finding cites the request file:line and the code file:line.
- `docs-template.md`:
  - `:3,18` "source of truth" → "contract, generated from code".
  - Delete the Migrate placeholder bullet at `:53-57`, replacing it with one line: the root `## Error Response Body` documents the error body the code renders (common-lib).
  - `:101` → "`## Business Logic` is written from the usecase".
  - Add Decision 6 as one bullet.
- `drift-verifier.md`:
  - `:4,11,18,22,125`: Go is the source of truth, and drift means the `docs:` are stale.
  - The remedy is a scoped Generate, not "Update-from-code".
- `yaml-reference.md:138,194`: "Update" → "Generate on an existing request".

- [ ] **Step 1: Write the six files**

- [ ] **Step 2: Verify**

  ```bash
  node scripts/validate-skills.js
  /opt/homebrew/bin/python3.14 -c "import yaml;print(len(yaml.safe_load(open('skills/bruno/SKILL.md').read().split('---')[1])['description']))"
  /usr/bin/grep -rnE "Migrate|migrate\.py|Draft|docs/api|source-of-intent|Update-from-code" skills/bruno
  ```

  Expected:
  - The validator passes with 16 skills.
  - The length is ≤ 1024.
  - `grep` prints only the SKILL.md line(s) for the `docs/api/` removal offer.
  - Ruling: spec criterion 3 says "no `docs/api`", but Generate flow step 1 requires the removal offer. The flow wins, so the offer lines are the only allowed hits.

---

### Task 3: Dependents and the old spec

**Files (one edit each):**
- `README.md:132`: change the row to `| \`bruno\`              | Bruno collection at \`bruno/\`, generated from Go code; format and drift checks |`
- `skills/init-project/assets/template/bruno/README.md:6`, `skills/init-project/assets/template/.kiro/steering/bruno.md:8` and `skills/init-project/assets/template/CLAUDE.md:119`: "the API source of truth, authored with the `bruno` skill" becomes "generated from the code with the `bruno` skill; the code is the source of truth". Keep each file's sentence shape.
- `skills/bug-hunter/SKILL.md:125`: the chain becomes `bruno ← code ← ticket/spec ← docs/knowledge/{contracts,requirements}/ ← the originating issue`.
- `docs/superpowers/specs/2026-11-09-bruno-skill-design.md`: add a new first line, `> Superseded in part by \`2026-11-09-bruno-from-code-design.md\` (source of truth, modes, migrate).`, followed by a blank line.

- [ ] **Step 1: Make the six edits**

- [ ] **Step 2: Verify**

  ```bash
  /usr/bin/grep -rnE "API source of truth" skills README.md AGENTS.md
  node scripts/validate-skills.js
  /opt/homebrew/bin/python3.14 -B skills/bruno/assets/brunocheck.py skills/init-project/assets/template/bruno
  ```

  Expected:
  - `grep` prints nothing.
  - The validator passes.
  - `brunocheck` prints `PASS: 0 error(s)` with no NOTE.

---

### Task 4: Acceptance on real code and full validation

This task does **not** edit `skills/`. A defect it finds in the skill text is reported with evidence, and the controller rules on it. The implementer acts as a host agent that knows only `skills/bruno/SKILL.md` and the files that file points to. It must not use knowledge from this plan to fill gaps in the skill. A gap it has to fill is itself a finding.

**Files:**
- Scratch only: `/private/tmp/claude-502/-Users-witoo-h-dev-witooh-neo-plugin/1b6ceb2a-d6c3-4b3a-84a2-c15146b2dca3/scratchpad/accept/manual-posting-service/`

- [ ] **Step 1: Copy**

  ```bash
  git -C /Users/witoo.h/dev/tcrb/manual-posting-service status --porcelain > <scratch>/accept/tcrb-before.txt
  rsync -a --exclude .git --exclude vendor /Users/witoo.h/dev/tcrb/manual-posting-service/ <scratch>/accept/manual-posting-service/
  ```

- [ ] **Step 2: Full Generate (criterion 4)**

  Follow `SKILL.md`'s Generate on the copy with scope "all". The skill asks questions; answer them as follows:
  - location: yes;
  - remove `docs/api/`: no;
  - L1.5: no, because this run does not dispatch subagents;
  - delete orphans: no.

  Then run:

  ```bash
  /opt/homebrew/bin/python3.14 -B skills/bruno/assets/brunocheck.py <copy>/bruno
  /opt/homebrew/bin/python3.14 -B skills/bruno/assets/driftcheck.py <copy>/bruno --src <copy>
  ```

  Expected: `PASS: 0 error(s)` and `PASS: 0 drift`.

  Record:
  - the printed scope list (Review Focus 1);
  - any route `driftcheck` missed (Review Focus 2);
  - the `docs/api/` offer (Review Focus 3);
  - the orphans still on disk (Review Focus 4).

- [ ] **Step 3: Snapshot**

  Run `(cd <copy> && find bruno -type f -exec shasum {} + | sort -k2) > <scratch>/accept/before.sha`.

- [ ] **Step 4: Change code and Check (criterion 5)**

  Add one JSON field to the request DTO of exactly one endpoint in `<copy>` (Go source). Then follow `SKILL.md`'s Check.

  Expected: `driftcheck` reports `DRIFT` on that endpoint's request file only.

- [ ] **Step 5: Scoped Generate (criterion 6)**

  Follow Generate scoped to that endpoint. Then run:

  ```bash
  /opt/homebrew/bin/python3.14 -B skills/bruno/assets/driftcheck.py <copy>/bruno --src <copy>
  (cd <copy> && find bruno -type f -exec shasum {} + | sort -k2) | diff <scratch>/accept/before.sha -
  ```

  Expected: `PASS`, and the `diff` lists only that endpoint's request file.

- [ ] **Step 6: Full validation (criteria 1–3)**

  ```bash
  /opt/homebrew/bin/python3.14 -B -m unittest discover -s skills/bruno/assets -p 'test_*.py'
  for v in validate-skills validate-pi-package validate-omp-package validate-grok-package validate-cursor-package validate-codex-package; do node scripts/$v.js; done
  claude plugin validate .
  grok plugin validate .
  /usr/bin/grep -rnE "Migrate|migrate\.py|Draft|docs/api" skills/bruno
  /usr/bin/grep -rnE "API source of truth" skills README.md AGENTS.md
  git -C /Users/witoo.h/dev/tcrb/manual-posting-service status --porcelain | diff <scratch>/accept/tcrb-before.txt -
  ```

  Expected:
  - `Ran 59 tests … OK`.
  - Each validator exits 0.
  - The first grep prints only the `docs/api/` removal-offer line(s).
  - The second grep prints nothing.
  - The tcrb `diff` prints nothing.

- [ ] **Step 7: Report**

  Write a table for criteria 1–6 with columns criterion | measured | pass/fail. Add a list of every place where `SKILL.md` was ambiguous, wrong, or silent while the run needed it, each with the file:line.
