---
name: bruno
description: >-
  Generates the Bruno OpenCollection in a service repo's `bruno/` from the Go code, which is the
  single source of truth for every HTTP endpoint: each `<domain>/<endpoint>.yml` is a runnable
  request whose `docs:` markdown block holds the contract (field tables, error tables, examples)
  as read from the router, handlers, DTOs, usecases and error catalog. Two modes: Generate writes
  or refreshes requests from code; Check writes nothing and reports format errors and
  code-vs-collection drift. Every run ends in a three-layer verify (script, fresh-eyes,
  completeness sweep). Use when creating, refreshing or checking a service's Bruno collection
  after the code changed. Triggers: "gen bruno จาก code", "สร้าง bruno", "อัปเดต bruno",
  "เช็ค bruno ตรง code ไหม", "validate bruno", "api drift". Does not design an API before code
  exists, does not publish to Confluence, and is not an OpenAPI, Postman or curl converter.
---

# Bruno

The Go code is the **single source of truth** for every HTTP endpoint. This skill reads the code and generates the Bruno OpenCollection in the service repo's `bruno/`. One request file per endpoint holds two things:

- the runnable request: `http` and a `runtime` status test;
- the contract: a `docs:` Markdown block in a fixed layout.

Nobody edits `docs:` by hand. A change starts in the code, and the next Generate carries it into `docs:`. Every result rests on three things:

- evidence from deterministic scripts;
- an independent fresh-eyes pass;
- a completeness sweep.

It never rests on the running agent's confidence.

Paths and scripts:

- `ASSET_DIR` = `<skill base dir>/assets`.
- `SKILL_DIR` = `<skill base dir>`. The skill-load message gives the "Base directory for this skill".
- The scripts need PyYAML. Run them as `python3 "$ASSET_DIR/<script>"`.
- Exit **2** with `<script>: needs PyYAML (pip install pyyaml)` means: install pyyaml, or use an interpreter that has it, then re-run. Exit 2 is never a PASS and never a DRIFT.

## Audience (non-negotiable)

`docs:` is read by the teams that call this API (BFF, mobile, partner), not by the owning service's developers.

- Write the wire contract and caller-visible behaviour: wire names, types, Mandatory, examples, public error codes, and rules a caller can observe.
- The code is where the facts come from, not who reads them. Translate it into wire behaviour. Never cite a Go file, package, function or line in `docs:`.
- Never write ticket IDs (`GI-3467`), decision IDs (`D-07`), AC-IDs (`AC-001`), a `## Contract source` section, or repo-internal paths (`internal/…`, `docs/knowledge/…`, `handler.go:42`). Traceability lives in the ticket, the MR and the e2e test titles (`e2e-playwright`).
- `brunocheck.py` K10 ERRORs on those patterns. It NOTEs any `XX-NNNN` token not declared as an Error Code, because a regex cannot tell `GI-3467` from `ACC-1001`. L2 settles each NOTE.
- Full rules: [`references/docs-template.md`](references/docs-template.md) §Audience.

## Output location

```
bruno/
├── opencollection.yml       info.name + docs: (Overview, Field Information, Error Response Body, Common Error Responses)
├── environments/            local.yml · sit.yml
└── <domain>/
    ├── folder.yml           info{name, type: folder, seq} + request.auth/headers + optional docs:
    └── <endpoint>.yml       info → http → runtime → settings → docs
```

- **Collection root**, found in this order:
  1. an explicit path from the user;
  2. walk **up** from cwd for an `opencollection.yml`;
  3. `<repo-root>/bruno/`.

  In a monorepo, scope it to the chosen service. If there is no `bruno/` yet, propose `<repo-root>/bruno/` and **confirm before creating it**.
- **Go root** is where `go.mod` lives.
  - Not Go → STOP. This skill is Go only; do not guess patterns.
  - The candidate root has no `go.mod` but several services below it do → ask which service, then scope both `--src` and the collection root to it. Modules nested below a `go.mod` root (`tools/*`, worktrees, templates) are skipped by `driftcheck.py`, so they need no question.
- Before writing any file, read [`references/docs-template.md`](references/docs-template.md) (layout, table rules, full example) and [`references/yaml-reference.md`](references/yaml-reference.md) (Bruno keys).

## Mode

1. The request asks to check, validate or find drift ("validate bruno", "เช็ค bruno ตรง code ไหม", "api drift") → **Check**.
2. Otherwise → **Generate**.

| Mode | Writes | Input | L1 | L2 fresh-eyes | L3 completeness |
| --- | --- | --- | --- | --- | --- |
| Generate | the requests in scope (+ root, folders, environments when missing; the root also on a full regeneration) | Go code; the existing `bruno/` only for the parts it preserves | `brunocheck.py` + `driftcheck.py` | offered, default yes | every in-scope route has a request; every usecase error path has an error row |
| Check | nothing | Go code + `bruno/` | `brunocheck.py` + `driftcheck.py` | offered, default yes | both the route and the request inventories compared |

Designing an API before its code exists is not a mode. See *What this skill is NOT*.

## Generate

### Step 1 · Locate

- Find the Go root and the collection root (see *Output location*).
- Read `CLAUDE.md` / `AGENTS.md` / `README` for the service name (`info.name`), the dev port (the `local` environment's `baseUrl`) and the environments. An existing `info.name` is kept.
- Project docs that describe another way to write `bruno/` (for example, generated from a legacy API spec, or another file format) are stale. List each stale line under Warnings and do not follow it. Find them by search, not from memory: agent guides (`CLAUDE.md`, `AGENTS.md`, `.kiro/steering/`, `.cursor/rules/`) and READMEs that describe the collection or count its requests. Use `git grep`: it searches every tracked file, including ones `.gitignore` lists. Agent folders such as `.kiro/` are often force-added under an ignore rule, and ripgrep-based search skips them.

  ```
  git grep -n -i bruno -- '*.md' '*.mdc' ':!bruno/'
  ```
- If a legacy `docs/api/` exists:
  - say it is obsolete;
  - never read it as input;
  - offer its removal in Step 6, after L1 passes.

### Step 2 · Inventory and scope

1. Read the router setup yourself and list every route: method + full path, with group prefixes resolved. Use [`references/go-scan-patterns.md`](references/go-scan-patterns.md) §Route Registration Patterns.
2. Run `driftcheck.py` (the L1 command) and compare its result with your list:
   - its summary line `… + N Go route(s)`;
   - its `(routes)` DRIFT lines.

   For each route on your list that the script did not count, add a NOTE `driftcheck missed <METHOD /path>` to Warnings. Author that route anyway.

   With no `bruno/` yet, the script exits 2 here. Make this comparison at L1 instead.
3. **Scope**, in this order:
   1. the endpoints the user names;
   2. otherwise, every route when `bruno/` is missing or the user asks for a full regeneration;
   3. otherwise, the new routes (`Go route … has no request in bruno/`) plus every request file `driftcheck.py` marks `✗ … DRIFT`.
4. **Print the scope list before writing anything:** `METHOD /path → bruno/<domain>/<endpoint>.yml (new | update)`, plus the orphans (Step 5).

   A request that is out of scope is not touched, even when it shows a NOTE.
5. **When the user named no endpoint**, ask once via `AskUserQuestion` before Step 3 writes anything. Show the printed list and offer: proceed, or narrow it to the endpoints the user names. Old-layout requests that `driftcheck.py` cannot parse all show up as new routes, so an unnamed scope can cover the whole collection.

### Step 3 · Author from code

For each in-scope endpoint, read the code in this order. [`go-scan-patterns.md`](references/go-scan-patterns.md) has the exact patterns.

1. **The handler.** Read:
   - the bind calls (body, query, path);
   - the success status (§Success Status Code);
   - the response rendering (§Response Wrapper Detection);
   - the auth middleware on its route group (§Auth Type Detection);
   - every header the handler and the middleware on its chain read (§Header Detection).
2. **The request DTO.** It gives the wire names and types. Its binding tags give Mandatory: `Yes` only with `binding:"required"` or `validate:"required"`; otherwise `No` ([`drift-verifier.md`](references/drift-verifier.md) §Mandatory classification). Embedded structs and custom types are expanded per [`go-scan-patterns.md`](references/go-scan-patterns.md) §Field Extraction Completeness.
3. **The response DTO.** Pointer or `omitempty` → `No`; otherwise `Yes`.
4. **The usecase**, every domain-service and usecase method it calls, and the return sites of the repository and gateway methods they call. These give `## Business Logic` and the error paths (§Error Tracing Patterns).
5. **The error catalog.** It gives Error Code, Error Messages and Response Code; Status follows Response Code (§Error Mapping).

Write the files per [`docs-template.md`](references/docs-template.md) + [`yaml-reference.md`](references/yaml-reference.md):

- **Every statement traces to code.** Each row, each enum value, each error row and each Business Logic sentence comes from a line you read.
  - When the code says nothing, `docs:` says nothing more.
  - A field with no comment gets a short neutral description of what its name and type say. Never guess a business meaning.
  - `## Business Logic` lists only the steps the usecase performs, in their order.
- **`opencollection.yml`.** Write it when it is missing or on a full regeneration:
  - `info.name`;
  - a root `docs:` with `## Overview`, an optional `## Field Information`, `## Error Response Body` (the body the code renders, documented once) and `## Common Error Responses` (may hold zero rows).

  If its `## Error Response Body` reads `Not documented in the source spec.`, replace that sentence with the body the code renders.
- **`environments/`.** Write `local.yml` and `sit.yml` when they are missing, with `baseUrl` + one variable per `{{name}}` used. Secret-looking names get `value: ""` + `secret: true`. An older file of the same name (`environments/<name>.bru`) hands its values and comments to the new one.
  - **`local.yml` runs as committed.** Each id gets a value the local stack accepts, taken from a file you read: a seed migration row, a mock-stub sample (for example a Mockoon environment), or an e2e sentinel id.
  - **An id the service creates during the run** gets `value: ""`. The request that returns it stores it with an `after-response` script (`bru.setVar`, [`yaml-reference.md`](references/yaml-reference.md) §`runtime`), and its `seq` puts it before every request that reads the id.
  - **Every other environment** (`sit.yml`, `uat.yml`, …) fills only `baseUrl`; its ids stay `""`. A full run there writes shared data, so the user fills an id on purpose. Never copy a local or seed id into it.
- **`<domain>/folder.yml`.** It holds:
  - `info{name, type: folder, seq}` (10, 20, 30…);
  - the auth and headers that every request in the folder shares, with each of those requests on `auth: inherit`. A folder whose requests share no auth sets none; a request with no auth then omits `auth` or reads `auth: inherit`, never `auth: none` (K12);
  - optional domain prose in `docs:`.
- **`<domain>/<endpoint>.yml`.**
  - Order: `info → http → runtime → settings → docs`.
  - `http.url` uses `:param`, with a `type: path` row per param.
  - `http.body.data` has the same key paths as the `docs:` Body Example.
  - Body and param values are ones the local stack accepts in a full run. Two requests that update the same record in one run send different values: an update that changes nothing may be rejected.
  - `runtime.scripts` holds a `type: tests` script asserting the success status.
  - `settings.encodeUrl: true`.
- **Error rows.** When the code renders a Response Code, Status follows it per the common-lib table. When it does not (an older common-lib, a partner body), Status is what the code sets and Response Code stays blank. The common-lib body is never repeated per endpoint; `### Error Responses` lists only that endpoint's errors. A partner contract's error body gets its own `### HTTP Status: <4xx/5xx>` section. A dead branch, one the code can never take whatever data is stored, gets no row and goes under Warnings (§Error Tracing Patterns, Step 4).

### Step 4 · Preserve (an existing request)

- **Pairing.** An existing request belongs to a route when two things match:
  - its `http.method`;
  - its `http.url` path, with `{{baseUrl}}` and the query string removed. The path may match the route's path in full or as a suffix of it, the same way `driftcheck.py` matches.

  Never pair by `docs:`; an older layout may not have one.
- **Several requests on one route** (for example hand-written negative cases): the one with a `docs:` block holds the contract; when none has one, the lowest `seq` gets it. The others are **extra requests**: kept untouched without `docs:`, never deleted, and listed under Warnings. `brunocheck.py` skips them with a `NOTE K1 … extra request` line.
- **Rewritten from code:**
  - `docs:`, in full;
  - `http.method` and `http.url`;
  - the names in `http.params`. Keep the existing values of params that survive.
- **Kept as they are:**
  - `http.auth`;
  - `http.headers` values;
  - `runtime` (scripts, variables);
  - `settings`;
  - `info.seq`;
  - every environment value, and the comment next to it. Edit environment files as text: a YAML load and dump drops comments.

  These parts are runnable and often hand-typed; the code cannot give them back.
- **`http.body`:** keep it when its key-path set equals the request DTO's. Otherwise regenerate it from the DTO, keeping the values of the keys that survive.
- **A new request** takes the highest `seq` in its folder + 10.

### Step 5 · Orphans

A request is an orphan only when its method and path (paired as in Step 4) match no route on **your own** Step 2 route list.

- `driftcheck.py`'s `spec endpoint … has no matching Go route` line is only a candidate. When the request's route *is* on your list, the line is a confirmed false positive (`driftcheck missed …`), never an orphan.

1. List every orphan in the scope print and under Warnings.
2. Ask once whether to delete them. Delete only the ones the user confirms.

A request may be documented before its handler exists, in a case the user directs by hand. That request stays an orphan until the code lands.

### Step 6 · Verify, then offer to remove `docs/api/`

1. Run the three-layer verify below, then the live run (§Live run).
2. Only after L1 passes, and only if a legacy `docs/api/` exists:
   1. List what still reads it: agent and skill prompts, CI jobs, scripts, READMEs. Use `git grep` for the reason in Step 1.

      ```
      git grep -ln 'docs/api' -- ':!docs/'
      ```
   2. Ask once, naming those files: "`docs/api/` is obsolete now that `bruno/` is generated from code. Remove it with `git rm -r docs/api`? These files still point at it: …"
      - yes → run it, and list the files that still point at it under Warnings;
      - no → leave it and report it under Warnings.

Committing stays with the user.

## Check

Check writes nothing.

- Run L1 (both scripts), then L1.5, L2 and L3.
- Report the format ERRORs and the drift. Drift means code that changed since the last Generate.
- The remedy for drift is a Generate scoped to the drifted requests and the new routes.

## Three-layer verify

### verify-L1 · Script tripwire (always)

```
python3 "$ASSET_DIR/brunocheck.py" bruno
python3 "$ASSET_DIR/driftcheck.py" bruno --src <go-root>
```

- **`brunocheck.py`** prints, in order:
  - `✓`/`✗ <request>` per request;
  - `ERROR K<n> <file>: <msg>` and `NOTE K<n> <file>: <msg> — needs fresh-eyes` lines;
  - `PASS: 0 error(s)` or `FAIL: N error(s)`.

  Its rules K1-K14 are tagged in brackets in [`docs-template.md`](references/docs-template.md).
- **`driftcheck.py`** reads Go per [`go-scan-patterns.md`](references/go-scan-patterns.md) and prints:
  - a `(routes)` block;
  - `✓`/`✗ <request file>` for each request that has a `DRIFT` or a `NOTE`, with those lines. A request with neither is not printed;
  - `PASS` or `DRIFT FOUND: N drift / M note(s) across … + K Go route(s)`.

  It exits 2 when the collection root or the Go source is missing, and says so. Report that as "not compared", never as in sync.
- **Tripwire, not ground truth.**

Pass rules:

- **Generate passes L1** when `brunocheck.py` exits 0 and `driftcheck.py` prints no DRIFT for an in-scope request file or an in-scope route.
  - DRIFT outside the scope is reported under Warnings and left alone.
  - A confirmed false positive (see below) that is listed under Warnings does not block the pass.
  - This means `driftcheck.py` may exit 1 on a scoped Generate that passes.
- **Check** reports every ERROR and DRIFT.

What to do on each exit:

- **exit 1 in scope** → for each ERROR / DRIFT:
  1. Open the request and the code.
  2. Fix the request so it says what the code does.
  3. Re-run.

  Loop until L1 passes, **or** stop after ~3 rounds with no progress and escalate. Never fake a green run.
- **A DRIFT the code contradicts** (the script's heuristic is wrong) → confirm it by reading the code, then record it under Warnings as a confirmed false positive. Never bend `docs:` away from the code to silence the script.
- **exit 2** → there is no result yet; fix the cause and re-run. The causes are:
  - missing PyYAML;
  - a wrong argument count (`brunocheck.py`);
  - a missing collection root or Go source (`driftcheck.py`).

Collect every `NOTE` line (each ends `needs fresh-eyes`): they feed L2.

### verify-L1.5 · Offer fresh-eyes (default yes)

Ask once via `AskUserQuestion`: *"Run an independent fresh-eyes verify? (default: yes)"*.

- **no** → skip L2 and mark it "skipped by user".
- **yes** → run L2.

### verify-L2 · Independent verifier

Spawn a read-only sub-agent that did **not** write the files.

**Generate:**

```
# Role: Bruno Contract Verifier
Read first: <SKILL_DIR>/references/bruno-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify that the Bruno requests below say what the Go code does. Check ONLY semantic
fidelity to the code, auth/header mapping, runnable body vs docs:, and Audience fitness (not the
scripts' mechanical checks). For each K10 NOTE, decide: ticket key or error code? For each K1 extra-request NOTE, confirm it
is a variant of that route's documented request. Read the code yourself.

## Files under review
<in-scope request .yml + folder.yml + opencollection.yml + environments/*.yml paths>

## Go code
<go-root>; per endpoint: handler, request/response DTO, usecase, error catalog paths

## NOTEs to focus on
<every brunocheck NOTE + every driftcheck NOTE on an in-scope file>

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
```

**Check:**

```
# Role: Bruno Drift Verifier
Read first: <SKILL_DIR>/references/drift-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the drift report just produced. Check ONLY the judgment-level drift the
script degraded to NOTE (not its mechanical checks). Read the Go source AND bruno/ yourself.

## Under review
bruno/<domain>/*.yml vs the Go implementation at <go-root>: list the endpoints whose fields or
routes the script could not confidently compare.

## driftcheck NOTEs to focus on
<paste every NOTE line from L1>

## brunocheck NOTEs and Audience
Also read <SKILL_DIR>/references/bruno-verifier.md checks 11-13. Apply check 11 (Audience) to every
request docs:, and settle each brunocheck NOTE below with check 12 (K10) or 13 (K1).
<paste every brunocheck NOTE line from L1>

## Project conventions
CLAUDE.md (the relevant section)

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
```

- `SKILL_DIR` is mandatory. Without it the verifier cannot read its role file and fails silently.
- The verifier is read-only (no write, edit or commit). **You** reconcile the files from the code, then re-run L1.
- Do not auto-redispatch. Offer a second round (default yes), then escalate.

### verify-L3 · Completeness sweep (omission critic)

L1 and L2 inspect what is present; L3 catches what is **missing entirely**. Re-derive the inventory yourself:

- **Generate:**
  - every in-scope route on your Step 2 list has a request with `docs:`;
  - for each of them, every error path the usecase can reach has a row in `### Error Responses` or the root `## Common Error Responses`. This includes the reserved validation and unexpected codes, where they are reachable;
  - two requests whose usecases call the same method carry the same rows for that method's errors;
  - every header the handler or its middleware chain reads has a `### Headers` row;
  - every stale line the Step 1 search found is listed under Warnings.
- **Check:** both inventories re-derived, meaning the full route list from the router setup and the full request list from `bruno/`.
  - Every route and every request was compared.
  - Every "no confident struct match" reached L2.
  - See the [Drift Verification Checklist](references/drift-verifier.md#drift-verification-checklist).

Report any whole endpoint the pipeline silently dropped, fix it, then re-run L1.

### Live run (after a Generate, when a local stack is up)

The three layers compare the files with the code; this run proves the collection works as committed. It writes data, so it runs against `local` only, never a shared environment.

1. Probe a route from your Step 2 list that needs no data, usually the health route, at the `local.yml` `baseUrl` (for example `curl -fsS <baseUrl>/health`). No answer, or no `bru` CLI → report `⏭ not run` with the reason, never as passed.
2. From the collection root, run `bru run -r --env local`. Only `baseUrl` may be overridden (`--env-var baseUrl=…`), when the stack listens on another port. Every id comes from `local.yml` or a stored run-time variable; needing `--env-var` for an id means `local.yml` is wrong, so fix it.
3. A failure caused by run order or values (an update that repeats the previous value, an id from the wrong scope) is fixed in the request's values. Never drop the request or its test.
4. Re-run until every request passes, or stop after ~3 rounds with no progress and report the failures.

### Output

```
## Bruno: <Generate / Check>
**Collection:** bruno/ (N requests, M folders)   **Go root:** <path>
**Scope:** N endpoints (named / new + drifted / all)   (Check: none)
**Changes:** Created … / Updated … / Orphans: N listed, N deleted   (Check: none)
**Verification (three-layer):**
- L1 brunocheck.py: ✅ PASS / ❌ N ERROR · driftcheck.py: ✅ 0 DRIFT in scope / ⚠️ N DRIFT (N out of scope) · N NOTE · loop rounds: 0-3
- L2 fresh-eyes: ✅ Clean / ⚠️ N findings fixed / ⏭ Skipped
- L3 completeness sweep: ✅ all covered / ⚠️ N silent omissions fixed
- Live run: ✅ N/N requests pass / ❌ N failing / ⏭ not run (<reason>)
- Verdict: ✅ in sync with code / ⚠️ gaps to reconcile / ⏸ escalated
**Warnings:** routes driftcheck missed, out-of-scope drift, confirmed false positives, dead error branches left out (each with the code that rules it out), orphans, extra requests, stale project docs, `docs/api/` left in place or files that still point at it, open questions for a human
```

---

## What this skill is NOT

- **Not** an API designer. Designing an API before its code exists is not a mode. The user directs such a case by hand, and the next Generate from code replaces it.
- **Not** a publisher. Confluence publishing and syncing into the central `bruno-api-documents` repo are out of scope.
- **Not** an OpenAPI / Postman / curl converter. `bruno/openapi*.yaml` files are left untouched and reported.
- **Not** the e2e suite. The `runtime` status test is a smoke check; AC-driven HTTP tests are `e2e-playwright`.
- **Check writes nothing.** The remedy for drift is a scoped Generate, never a hand edit to `docs:`.
