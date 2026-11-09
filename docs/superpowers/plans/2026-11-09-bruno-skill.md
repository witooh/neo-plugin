# `bruno` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the four api-doc skills with one `bruno` skill whose `bruno/` collection (`http` + `runtime` + `docs:`) is the API source of truth.

**Architecture:** One shared parser (`docsparse.py`) turns a request file's `docs:` markdown into tables; three scripts use it: `brunocheck.py` (L1 rules K1–K11), `migrate.py` (legacy `docs/api/*.yaml` → `docs:`), `driftcheck.py` (Go ↔ `bruno/`, ported). `SKILL.md` routes six modes to those scripts. Then the old skills are deleted and every dependent file is repointed.

**Tech Stack:** Python 3 stdlib + PyYAML; `unittest`; Node validators in `scripts/`.

**Spec:** `docs/superpowers/specs/2026-11-09-bruno-skill-design.md`

## Global Constraints

- **No commits.** The user's rule is "never commit or push unless explicitly asked". No task has a commit step.
- Python: stdlib + PyYAML only. Scripts start with `#!/usr/bin/env python3` and a module docstring, like the existing assets.
- Inside `skills/`, `AGENTS.md`, `README.md`: never write `api-spec`, `open-collection`, `openapi-doc`, `confluence-api-doc` (Task 7 adds them to `DEAD_SKILLS`). Call the old format "the legacy `docs/api/*.yaml` spec".
- Field table header, exact: `Field Name | Type | Mandatory | Description | Possible Value`.
- Error table header, exact: `Status | Response Code | Error Code | Error Messages | Description`.
- `Type` ∈ `String, Number, Boolean, Object, Array`; `Mandatory` ∈ `Yes, No`.
- `RESPONSE_STATUSES = {"001": 400, "002": 400, "003": 404, "004": 409, "005": 503, "006": 504, "999": 500}`; common-lib code regex `^[A-Z]{2,3}-[0-9]{4}$`.
- Request top-level order: `info → http → runtime → settings → docs`.
- Skill `description` ≤ 1024 characters, third person, "what" first then "when".
- Test command for every Python task: `python3 -m unittest discover -s skills/bruno/assets -p 'test_*.py' -v`.
- Real service repos (`/Users/witoo.h/dev/tcrb/*`) are read-only; Task 9 works on copies in the scratchpad.

## Review Focus

1. A cell holding an escaped pipe, e.g. `` `SUSPEND` \| `UNSUSPEND` `` → stays one cell (test in Task 1).
2. `http.body.data` with an unquoted `{{var}}`, e.g. `"amount": {{amount}}` → K5 compares key paths, no JSON ERROR (test in Task 3).
3. A path param written as `{{accountId}}` in `http.url` instead of `:accountId` → K2/K3 pass (test in Task 2).
4. Free `##` sections and prose between a table and its `### Example` → ignored by the parser (test in Task 1).
5. A legacy field typed `Integer` (the old validator allowed it) → migrated as `Number`, round-trip clean (test in Task 4).

---

### Task 1: `docsparse.py` and the shared fixture

**Files:**
- Create: `skills/bruno/assets/docsparse.py`
- Create: `skills/bruno/assets/testdata/good/` (fixture collection below)
- Test: `skills/bruno/assets/test_docsparse.py`

**Interfaces:**
- Produces (all in `docsparse.py`):
  - `class ParseError(Exception)` with attributes `file: str`, `line: int`, `msg: str`.
  - `FIELD_HEADER: list[str]`, `ERROR_HEADER: list[str]`, `TYPES: set[str]`, `MANDATORY: set[str]`, `TOP_ORDER: list[str]` (Global Constraints values).
  - `split_sections(md: str) -> list[dict]` — each `{"level": int, "title": str, "body": str, "line": int}` for `##`/`###` headings; text before the first heading is dropped.
  - `parse_table(text: str) -> tuple[list[str], list[list[str]]] | None` — first markdown table in `text`; header cells and data rows, separator row skipped, `\|` kept inside a cell as `|`, cells stripped.
  - `field_rows(header, rows) -> list[dict]` — `{"name", "type", "mandatory", "description", "possible"}`; `name` has backticks stripped.
  - `error_rows(header, rows) -> list[dict]` — `{"status": int|None, "response_code": str, "error_code": str, "error_messages": str, "description": str}`; backticks stripped; `response_code` kept as text (leading zeros).
  - `json_with_vars(text: str) -> object` — `json.loads` after replacing every `{{...}}` that is not inside a JSON string with `null`.
  - `key_paths(obj) -> set[str]` — dict key `a.b`; a list contributes its own path, and dict items inside it contribute `parent[].child`.
  - `group_by_parent(rows) -> dict[str, list[dict]]` — the spec's `field_tree`: parent path (`""` top level, `data`, `items[]`) → child rows with `name` set to the leaf.
  - `parse_request_docs(md: str) -> dict` — `{"headings": [titles], "endpoint": (METHOD, path) | None, "auth": str | None, "tables": {"headers", "path", "query", "body"} → rows, "request_example": str | None, "responses": {int: {"fields": rows, "example": str | None}}, "errors": rows, "free": [titles]}`. The `### Example` that follows `### Body (JSON)` is the request example; an `### Example` after an `### HTTP Status: N` belongs to that status.
  - `load_yaml_with_order(path) -> tuple[dict, list[str]]` — data plus top-level key order (from `^[a-z]+:` lines at column 0).
  - `parse_request(path) -> dict` — `{"file", "order", "info", "http", "runtime", "settings", "docs_raw", "docs"}`; `docs` is `parse_request_docs(docs_raw)`.
  - `parse_root_docs(md: str) -> dict` — `{"headings", "error_body": rows, "common_errors": rows}`.
  - `parse_collection(root) -> dict` — `{"root": Path, "root_docs", "folders": {rel_dir: dict}, "requests": [parse_request…], "env": {var_name: value}}`; request files = every `*.yml` except `opencollection.yml`, `folder.yml`, `environments/*`.

- [ ] **Step 1: Write the fixture `testdata/good/`**

`opencollection.yml`: `opencollection: 1.0.0`, `info.name: Fixture Service`, `bundled: false`, and `docs:` with `## Overview`, `## Error Response Body` (field table with `responseCode`, `errorCode`, `errorMessage`, all `String`/`Yes`), `## Common Error Responses` holding one row `| 400 | 001 | FIX-1001 | Mandatory field missing | A required field is absent |`.

`environments/local.yml`: `baseUrl`, `accountId`, `customerId`.

`account/folder.yml`: `info: {name: Account, type: folder, seq: 10}`, `request: {auth: none}`.

`account/create-account.yml` (the canonical example; later tasks mutate it):

```yaml
info:
  name: Create Account
  type: http
  seq: 10

http:
  method: POST
  url: "{{baseUrl}}/v1/accounts"
  body:
    type: json
    data: |-
      {
        "customerId": "{{customerId}}",
        "accountType": "SA",
        "items": [{"code": "X1"}]
      }
  auth: inherit

runtime:
  scripts:
    - type: tests
      code: |-
        test("status is 201", function() { expect(res.status).to.equal(201); });

settings:
  encodeUrl: true

docs: |-
  ## Purpose

  Open an account. Values are `SA` \| `FD`.

  ## Request

  ### Endpoint

  `POST /v1/accounts`

  ### Auth

  `None`

  ### Body (JSON)

  | Field Name | Type | Mandatory | Description | Possible Value |
  |---|---|---|---|---|
  | customerId | String | Yes | Owner | `"uuid-v4"` |
  | accountType | String | Yes | `SA` \| `FD` | `"SA"` |
  | items | Array | No | Extra items | `[{…}]` |
  | items[].code | String | Yes | Item code | `"X1"` |

  ### Example

  ```json
  {"customerId": "uuid-v4", "accountType": "SA", "items": [{"code": "X1"}]}
  ```

  ## Response

  ### HTTP Status: 201

  Created.

  | Field Name | Type | Mandatory | Description | Possible Value |
  |---|---|---|---|---|
  | status | String | Yes | Envelope status | `"Success"` |
  | data | Object | Yes | Payload | see below |
  | data.accountId | String | Yes | New id | `"uuid-v4"` |

  All fields are always present.

  ### Example

  ```json
  {"status": "Success", "data": {"accountId": "uuid-v4"}}
  ```

  ### Error Responses

  | Status | Response Code | Error Code | Error Messages | Description |
  |---|---|---|---|---|
  | 400 | 001 | FIX-1002 | Invalid field format | Malformed field |

  ## Business Logic

  1. Validate, then create.
```

`account/get-account.yml`: `GET`, url `"{{baseUrl}}/v1/accounts/:accountId"`, `http.params` with `{name: accountId, value: "{{accountId}}", type: path}`, a status-200 test, `docs:` with `### Endpoint` `` `GET /v1/accounts/{accountId}` ``, a `### Path Parameters` table row `accountId | String | Yes | Account id | "uuid-v4"`, and a 200 response table `status`, `data`, `data.accountId`.

- [ ] **Step 2: Write the failing tests in `test_docsparse.py`**

Load `docsparse` with `importlib.util.spec_from_file_location`, as `open-collection/assets/test_error_tables.py` does. Tests:

```python
def test_escaped_pipe_stays_in_one_cell(self):
    hdr, rows = dp.parse_table("| A | B |\n|---|---|\n| `SA` \\| `FD` | x |\n")
    self.assertEqual(rows[0], ["`SA` | `FD`", "x"])

def test_request_docs_tables_and_examples(self):
    r = dp.parse_request(GOOD / "account/create-account.yml")
    d = r["docs"]
    self.assertEqual(d["endpoint"], ("POST", "/v1/accounts"))
    self.assertEqual([f["name"] for f in d["tables"]["body"]],
                     ["customerId", "accountType", "items", "items[].code"])
    self.assertIn('"customerId"', d["request_example"])
    self.assertEqual(sorted(d["responses"]), [201])
    self.assertEqual(len(d["responses"][201]["fields"]), 3)          # Review Focus 4: prose after table
    self.assertIn('"accountId"', d["responses"][201]["example"])
    self.assertEqual(d["errors"][0]["response_code"], "001")
    self.assertEqual(d["free"], ["Business Logic"])

def test_order(self):
    r = dp.parse_request(GOOD / "account/create-account.yml")
    self.assertEqual(r["order"], ["info", "http", "runtime", "settings", "docs"])

def test_json_with_vars_and_key_paths(self):
    obj = dp.json_with_vars('{"a": {{amount}}, "b": "{{x}}", "items": [{"code": 1}]}')
    self.assertEqual(dp.key_paths(obj), {"a", "b", "items", "items[].code"})

def test_group_by_parent(self):
    rows = [{"name": "data", "type": "Object"}, {"name": "data.accountId", "type": "String"}]
    self.assertEqual([r["name"] for r in dp.group_by_parent(rows)["data"]], ["accountId"])

def test_collection(self):
    c = dp.parse_collection(GOOD)
    self.assertEqual(len(c["requests"]), 2)
    self.assertEqual(c["root_docs"]["common_errors"][0]["error_code"], "FIX-1001")
    self.assertIn("accountId", c["env"])
```

- [ ] **Step 3: Run and confirm failure**

Run the Global test command. Expected: errors loading `docsparse.py` (file missing).

- [ ] **Step 4: Implement `docsparse.py` per the Interfaces block**

`split_sections` must ignore `#` lines inside fenced code blocks. Prose between a table and the next heading is not a table row (table = contiguous lines whose left-stripped text starts with `|`).

- [ ] **Step 5: Run tests**

Expected: all `test_docsparse` tests PASS.

---

### Task 2: `brunocheck.py` structure rules (K1, K2, K3, K7, K8, K9) and CLI

**Files:**
- Create: `skills/bruno/assets/brunocheck.py`
- Test: `skills/bruno/assets/test_brunocheck.py`

**Interfaces:**
- Consumes: `docsparse.parse_collection`, `parse_request`, `TOP_ORDER`.
- Produces:
  - `check(root: Path) -> list[tuple[str, str, str, str]]` — `(level, rule, file, msg)`, `level` ∈ `ERROR`, `NOTE`; `rule` ∈ `K1`…`K11`; a `ParseError` becomes `("ERROR", "K1", file, msg)`.
  - `main()` — `brunocheck.py <bruno-root>`; prints `✓/✗ <file> …`, `ERROR` and `NOTE` lines (NOTE lines end `needs fresh-eyes`), last line `PASS: 0 error(s)` or `FAIL: N error(s)`; exit 1 iff any ERROR.
  - `norm_path(p: str) -> str` — `{x}`, `:x`, and non-leading `{{x}}` segments → `{}`; leading `{{baseUrl}}`-style token removed; trailing slash removed.

Rules in this task:
- **K1:** every `.yml` loads; `info`, `http`, `settings`, `docs` present in a request; present known keys follow `TOP_ORDER`.
- **K2:** headings `Purpose`, `Request`, `Endpoint`, `Auth`, `Response` present; `### Endpoint` method/path equals `http.method` / `norm_path(http.url)`.
- **K3:** `{param}` names in the docs path == Path Parameters table names == the URL's path params, where the URL's set is every `:name` segment plus every non-leading `{{name}}` segment; each `:name` also needs an `http.params` row with `type: path`.
- **K7:** some `runtime.scripts[]` has `type: tests` and code matching `res\.(status|getStatus\(\))`.
- **K8:** every `{{var}}` in `http` and `folder.yml` `request` (not `process.env.*`) is in `env`. ERROR when a var whose name contains (case-insensitive) `password`, `secret`, `token`, `apikey`, `api_key`, `bearer`, `otp` has a non-empty value; NOTE for `pin`, `national`, `citizen`, `cif`, `biometric` with a non-empty value.
- **K9:** every directory holding request files has `folder.yml`; request `info.seq` unique per directory.

- [ ] **Step 1: Write failing tests**

Helper `mutated(*edits: tuple[str, str, str]) -> Path`: `shutil.copytree(GOOD, tmp)`, then for each `(rel, old, new)` assert `old` occurs in the file and replace it. Helper `rules(findings, level="ERROR") -> set[str]`.

```python
def test_good_fixture_has_no_errors(self):
    self.assertEqual(rules(bc.check(GOOD)), set())

def test_k1_missing_settings(self):
    root = mutated(("account/create-account.yml", "settings:\n  encodeUrl: true\n\n", ""))
    self.assertIn("K1", rules(bc.check(root)))

INFO = "info:\n  name: Create Account\n  type: http\n  seq: 10\n\n"

def test_k1_info_after_docs(self):
    root = mutated(("account/create-account.yml", INFO, ""))
    p = root / "account/create-account.yml"
    p.write_text(p.read_text() + "\n" + INFO)
    self.assertIn("K1", rules(bc.check(root)))

def test_k2_method_mismatch(self):
    root = mutated(("account/create-account.yml", "`POST /v1/accounts`", "`PUT /v1/accounts`"))
    self.assertIn("K2", rules(bc.check(root)))

def test_k3_param_missing_from_http_params(self):
    root = mutated(("account/get-account.yml", "type: path", "type: query"))
    self.assertIn("K3", rules(bc.check(root)))

def test_k3_var_style_path_param_is_accepted(self):   # Review Focus 3
    root = mutated(("account/get-account.yml", '/v1/accounts/:accountId"', '/v1/accounts/{{accountId}}"'))
    found = rules(bc.check(root))
    self.assertNotIn("K3", found)
    self.assertNotIn("K2", found)

def test_k7_no_status_test(self):
    root = mutated(("account/create-account.yml", "res.status", "res.body"))
    self.assertIn("K7", rules(bc.check(root)))

def test_k8_undefined_var(self):
    root = mutated(("account/create-account.yml", "{{customerId}}", "{{nope}}"))
    self.assertIn("K8", rules(bc.check(root)))

def test_k9_missing_folder_yml(self):
    root = mutated()
    (root / "account/folder.yml").unlink()
    self.assertIn("K9", rules(bc.check(root)))

def test_cli_exit_codes(self):
    ok = subprocess.run([sys.executable, BC, str(GOOD)])
    self.assertEqual(ok.returncode, 0)
```

One more K8 test, `test_k8_secret_with_value`: append `  - name: auth_token\n    value: "abc"\n` to `environments/local.yml` and add `{{auth_token}}` as a header value in `create-account.yml` (two edits in one `mutated` call) → `K8` ERROR.

- [ ] **Step 2: Run and confirm the new tests fail**

- [ ] **Step 3: Implement the six rules, `norm_path` and `main()`**

Port `collect_env_vars`, `norm_template`, `RE_VAR` and `RE_LEADING_VAR` logic from `skills/open-collection/assets/colcheck.py:77-100,233-258` (copy, don't import).

- [ ] **Step 4: Run tests**

Expected: `test_docsparse` and `test_brunocheck` tests PASS.

---

### Task 3: `brunocheck.py` content rules (K4, K5, K6, K10, K11)

**Files:**
- Modify: `skills/bruno/assets/brunocheck.py`
- Test: `skills/bruno/assets/test_brunocheck.py`

**Interfaces:**
- Consumes: Task 2's `check()` and `mutated()` helper; `docsparse.json_with_vars`, `key_paths`, `field_rows`, `error_rows`.
- Produces: the same `check()` with five more rules; `RESPONSE_STATUSES`, `COMMON_LIB_CODE` constants.

Rules:
- **K4:** every field table header == `FIELD_HEADER`; `type` ∈ `TYPES`; `mandatory` ∈ `MANDATORY`; a row `a.b` needs row `a` with type `Object`; `a[].b` needs `a` with type `Array`.
- **K5:** each Example parses with `json_with_vars`; each key path of the Example has a table row; each `Yes` row is in the Example when its parent path is in the Example (top-level parent = always); a Body table requires a request Example; when `http.body.type == json`, `key_paths(json_with_vars(http.body.data)) == key_paths(request example)`.
- **K6:** error table header == `ERROR_HEADER` (requests and `## Common Error Responses`); for a code matching `COMMON_LIB_CODE`, Response Code non-empty, in `RESPONSE_STATUSES`, and `status == RESPONSE_STATUSES[code]`. Logic follows `skills/api-spec/assets/apispeccheck.py:114-139`.
- **K10:** ERROR on `\binternal/[\w./-]+`, `\bdocs/(knowledge|tasks)/`, `[\w./-]+\.go:\d+`, `\bAC-\d{2,4}\b`, `\bD-\d+\b`, heading `Contract source` (case-insensitive), anywhere in a request or root `docs:`. NOTE on a `\b[A-Z]{2,}-\d+\b` token that is not an Error Code anywhere in the collection.
- **K11:** root docs headings include `Error Response Body` and `Common Error Responses`.

- [ ] **Step 1: Write failing tests**

```python
CA = "account/create-account.yml"

def test_k4_bad_mandatory(self):
    root = mutated((CA, "| customerId | String | Yes |", "| customerId | String | M |"))
    self.assertIn("K4", rules(bc.check(root)))

def test_k4_orphan_child(self):
    root = mutated((CA, "| data | Object | Yes | Payload | see below |\n", ""))
    self.assertIn("K4", rules(bc.check(root)))

def test_k5_example_key_not_in_table(self):
    root = mutated((CA, '"accountType": "SA", "items"', '"accountType": "SA", "ghost": 1, "items"'))
    self.assertIn("K5", rules(bc.check(root)))

def test_k5_body_data_key_set_differs(self):
    root = mutated((CA, '"accountType": "SA",\n', ""))
    self.assertIn("K5", rules(bc.check(root)))

def test_k5_unquoted_var_in_body_data(self):            # Review Focus 2
    root = mutated((CA, '"accountType": "SA",\n', '"accountType": {{accountType}},\n'),
                   ("environments/local.yml", "variables:\n", "variables:\n  - name: accountType\n    value: SA\n"))
    self.assertNotIn("K5", rules(bc.check(root)))

def test_k5_required_child_of_absent_optional_parent(self):
    root = mutated((CA, ', "items": [{"code": "X1"}]}', "}"),
                   (CA, ',\n        "items": [{"code": "X1"}]', ""))
    self.assertNotIn("K5", rules(bc.check(root)))

def test_k6_wrong_status_for_response_code(self):
    root = mutated((CA, "| 400 | 001 | FIX-1002 |", "| 422 | 001 | FIX-1002 |"))
    self.assertIn("K6", rules(bc.check(root)))

def test_k6_missing_response_code(self):
    root = mutated((CA, "| 400 | 001 | FIX-1002 |", "| 400 |  | FIX-1002 |"))
    self.assertIn("K6", rules(bc.check(root)))

def test_k10_internal_path_and_ticket(self):
    root = mutated((CA, "1. Validate, then create.", "1. See internal/handler/a.go:12 (AC-001)."))
    self.assertIn("K10", rules(bc.check(root)))

def test_k10_unknown_key_is_note(self):
    root = mutated((CA, "Open an account.", "Open an account (GI-3467)."))
    self.assertIn("K10", rules(bc.check(root), level="NOTE"))
    self.assertNotIn("K10", rules(bc.check(root)))

def test_k11_missing_error_body(self):
    root = mutated(("opencollection.yml", "## Error Response Body", "## Something Else"))
    self.assertIn("K11", rules(bc.check(root)))
```

The fixture's `http.body.data` lines are indented 8 spaces; adjust the `old` strings to the exact fixture text if the implementer formats it differently (the helper asserts `old` occurs, so a mismatch fails loudly instead of testing nothing).

- [ ] **Step 2: Run and confirm the new tests fail**

- [ ] **Step 3: Implement K4, K5, K6, K10, K11**

- [ ] **Step 4: Run tests**

Expected: every `test_brunocheck` test PASS; `python3 skills/bruno/assets/brunocheck.py skills/bruno/assets/testdata/good` prints `PASS: 0 error(s)`.

---

### Task 4: `migrate.py`

**Files:**
- Create: `skills/bruno/assets/migrate.py`
- Create: `skills/bruno/assets/testdata/legacy/` (fixture below)
- Test: `skills/bruno/assets/test_migrate.py`

**Interfaces:**
- Consumes: `docsparse` (`parse_request`, `split_sections`, `FIELD_HEADER`, `ERROR_HEADER`); `brunocheck.check` in tests.
- Produces:
  - `flatten_fields(fields: list, objects: dict, prefix: str = "") -> list[dict]` — legacy rows → `{"name", "type", "mandatory", "description", "possible"}` with dot-paths; `M→Yes`, `O→No`, `Integer→Number`; description + `" " + remark` when remark non-empty; possible = `` `json.dumps(example)` `` or `""` for an `object:` row; an `object: X` row is followed by X's rows under `name.` (type `Object`) or `name[].` (type `Array`), recursively.
  - `render_request_docs(ep: dict) -> str`, `render_root_docs(meta: dict) -> str`, `render_folder_docs(dmeta: dict) -> str | None` — layouts from the spec's "Request `docs:`" and "Collection-root `docs:`" sections.
  - `split_top_level(text: str) -> list[tuple[str, str]]` and `join_blocks(blocks) -> str` — raw top-level blocks keyed by `^[a-z]+:` at column 0; used so `http`/`runtime` stay byte-identical.
  - `migrate(api_dir: Path, bruno_root: Path) -> dict` — `{"updated": [...], "created": [...], "orphans": [...], "warnings": [...]}`. Never deletes.
  - `roundtrip(api_dir: Path, bruno_root: Path) -> list[str]` — one message per mismatched endpoint.
  - `main()` — `migrate.py <docs/api> <bruno-root> [--check]`; without `--check` runs `migrate()` then `roundtrip()`, with `--check` runs `roundtrip()` only; prints the report; exit 1 iff `roundtrip` returns anything.

Behaviour pinned by the spec (§ `assets/migrate.py`): match by method + normalized path (suffix-tolerant, `_meta.base_url` stripped); unmatched spec endpoint → new `<domain>/<stem>.yml` with `info`, `http`, a `test("status is <first 2xx>")` script, `settings.encodeUrl: true`; matched request → only `docs` replaced and blocks reordered to `TOP_ORDER`, a missing `runtime` gets the default test, `http.body.data` kept or set from `request_body.example`; error responses with exactly `responseCode`/`errorCode`/`errorMessage` dropped, others kept as `### HTTP Status: N`; `covers_ac` dropped; prose passed through `audience_text` / `audience_notes`, ported from `skills/open-collection/assets/yaml2md.py:100-189`; `_meta` → root `docs:`, `domains` → `folder.yml` (create with `info.seq` when missing, else only replace its `docs` block); `extra_endpoints` without a request → a minimal request. Unmatched existing requests and any `bruno/openapi*.yaml` → `warnings`.

Fixture `testdata/legacy/`:
- `docs/api/_meta.yaml` with `title`, `base_url: /`, `overview`, one `common_errors` row (`status: 400, responseCode: "001", code: LEG-1001`), `domains: {Account: {seq: 10}}`.
- `docs/api/account/create.yaml`: `POST /v1/accounts`, `request_body.fields` with `customerId` (String M), `count` (**Integer** O), `items` (Array O, `object: Item`), `responses` 201 with `data` → `object: AccountResponse` plus a 400 common-lib error response, `objects: {Item: [code String M], AccountResponse: [accountId String M]}`, `errors` one common-lib row, `covers_ac: [AC-001]`, `business_logic`.
- `docs/api/account/get.yaml`: `GET /v1/accounts/{accountId}` with a path param.
- `bruno/opencollection.yml`, `bruno/environments/local.yml`, `bruno/account/folder.yml`, and `bruno/account/create.yml` in the old layout (`info → http → docs → settings`, 6-column table) with a custom header `X-Trace: keep-me` and a `runtime` tests block.

- [ ] **Step 1: Write failing tests**

```python
def setUp(self):
    self.tmp = copy of testdata/legacy
    self.api, self.bruno = self.tmp / "docs/api", self.tmp / "bruno"

def test_migrated_collection_passes_brunocheck(self):
    mg.migrate(self.api, self.bruno)
    self.assertEqual(mg.roundtrip(self.api, self.bruno), [])
    self.assertEqual({f[1] for f in bc.check(self.bruno) if f[0] == "ERROR"}, set())

def test_http_and_runtime_kept_byte_identical(self):
    before = dict(mg.split_top_level((self.bruno / "account/create.yml").read_text()))
    mg.migrate(self.api, self.bruno)
    after = dict(mg.split_top_level((self.bruno / "account/create.yml").read_text()))
    self.assertEqual(after["http"], before["http"])
    self.assertEqual(after["runtime"], before["runtime"])

def test_missing_endpoint_is_created(self):
    report = mg.migrate(self.api, self.bruno)
    self.assertTrue((self.bruno / "account/get.yml").exists())
    self.assertIn("account/get.yml", report["created"])

def test_integer_becomes_number(self):                  # Review Focus 5
    mg.migrate(self.api, self.bruno)
    body = dp.parse_request(self.bruno / "account/create.yml")["docs"]["tables"]["body"]
    self.assertEqual({f["name"]: f["type"] for f in body}["count"], "Number")

def test_nested_objects_flatten_and_covers_ac_dropped(self):
    mg.migrate(self.api, self.bruno)
    d = dp.parse_request(self.bruno / "account/create.yml")
    names = [f["name"] for f in d["docs"]["tables"]["body"]]
    self.assertIn("items[].code", names)
    self.assertIn("data.accountId", [f["name"] for f in d["docs"]["responses"][201]["fields"]])
    self.assertNotIn("AC-001", d["docs_raw"])
    self.assertNotIn(400, d["docs"]["responses"])        # common-lib error body dropped

def test_roundtrip_catches_dropped_row_and_keeps_source(self):
    mg.migrate(self.api, self.bruno)
    p = self.bruno / "account/create.yml"
    p.write_text(p.read_text().replace("| customerId |", "| renamed |"))
    self.assertTrue(mg.roundtrip(self.api, self.bruno))
    r = subprocess.run([sys.executable, MG, str(self.api), str(self.bruno), "--check"])
    self.assertEqual(r.returncode, 1)
    self.assertTrue(self.api.exists())
```

- [ ] **Step 2: Run and confirm failure**

- [ ] **Step 3: Implement per the Interfaces block**

- [ ] **Step 4: Run tests**

Expected: all `test_migrate`, `test_brunocheck` and `test_docsparse` tests PASS.

---

### Task 5: `driftcheck.py` and Go scan patterns

**Files:**
- Create: `skills/bruno/assets/driftcheck.py` (copy of `skills/openapi-doc/assets/speccheck.py`)
- Create: `skills/bruno/references/go-scan-patterns.md` (moved from `skills/openapi-doc/references/go-scan-patterns.md`)
- Create: `skills/bruno/assets/testdata/go/` (tiny Go service)
- Test: `skills/bruno/assets/test_driftcheck.py`

**Interfaces:**
- Consumes: `docsparse.parse_collection`, `group_by_parent`.
- Produces: `load_bruno(root: Path) -> tuple[list[dict], set]`, which replaces `load_spec`. It returns the same endpoint shape `{file, method, npath, request_fields, response_objects, has_envelope, has_params}` and an empty `extra_set`. Rules:
  - `request_fields` = top-level Body rows.
  - `response_objects` = `group_by_parent` of each success response table minus the `""` group, keyed by parent path.
  - `has_envelope` = a success table has top-level rows.
  - Mandatory is mapped `Yes→M`, `No→O`.

  CLI: `driftcheck.py <bruno-root> --src <go-root>`, default root `bruno`. Exit 1 iff any DRIFT.

Fixture `testdata/go/`: `go.mod` (`module example.com/fix`), `router.go` with `r.POST("/v1/accounts", h.Create)` and `r.GET("/v1/accounts/:accountId", h.Get)`, `dto.go` with:
- `CreateAccountRequest{CustomerID string \`json:"customerId" binding:"required"\`; AccountType string \`json:"accountType" binding:"required"\`; Items []Item \`json:"items,omitempty"\`}`
- `Item{Code string \`json:"code"\`}`
- `AccountResponse{AccountID string \`json:"accountId"\`}`

Its collection is `testdata/good/`.

- [ ] **Step 1: Write failing tests**

Helper `run(*args) -> subprocess.CompletedProcess` = `subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)`; Go fixture mutations work on a `shutil.copytree` of `GO` in a temp dir.

```python
def test_good_collection_matches_go(self):
    r = run(DC, GOOD, "--src", GO)
    self.assertEqual(r.returncode, 0, r.stdout)

def test_undocumented_go_field_is_drift(self):
    go = copy of GO; append `Nickname string \`json:"nickname"\`` to CreateAccountRequest
    r = run(DC, GOOD, "--src", go)
    self.assertEqual(r.returncode, 1)
    self.assertIn("nickname", r.stdout)

def test_go_route_without_request_is_drift(self):
    go = copy of GO; add `r.DELETE("/v1/accounts/:accountId", h.Delete)`
    self.assertIn("DELETE", run(DC, GOOD, "--src", go).stdout)
```

- [ ] **Step 2: Run and confirm failure**

- [ ] **Step 3: Copy and adapt**

Replace `load_spec` with `load_bruno`. Rewrite the docstring and messages so they say `bruno/` instead of `docs/api/`, and so they name no removed skill. Leave the Go parsing (`speccheck.py:73-252`) and the drift checks (`:318-415`) unchanged. In `go-scan-patterns.md`, replace every removed-skill name and `docs/api` mention with `bruno`.

- [ ] **Step 4: Run tests**

Expected: all tests PASS.

---

### Task 6: `SKILL.md`, references, agent manifest

**Files:**
- Create: `skills/bruno/SKILL.md`
- Create: `skills/bruno/references/docs-template.md`, `yaml-reference.md`, `bruno-verifier.md`, `drift-verifier.md`
- Create: `skills/bruno/agents/openai.yaml`

**Interfaces:**
- Consumes: the CLIs from Tasks 2–5: `brunocheck.py <root>`, `migrate.py <docs/api> <root> [--check]`, `driftcheck.py <root> --src <go-root>`.

Content:

- **`SKILL.md`** frontmatter `name: bruno`. The description names:
  - what it is: the source of truth for HTTP endpoints, kept in `bruno/` with `docs:`;
  - the six modes;
  - its triggers: "สร้าง bruno", "อัปเดต bruno", "draft api", "เช็ค code ตรงกับ bruno ไหม", "api drift", "migrate docs/api", "validate bruno";
  - that Confluence is not handled.

  The body follows the old skills' spine (`ASSET_DIR`/`SKILL_DIR`, Audience, Output location, Mode, Steps, three-layer verify, Output block, "What this skill is NOT"). It carries:
  - the mode table and selection order from the spec, with Migrate confirmed before writing;
  - Draft: intent only, never reads code, writes no `## Business Logic`, runs L1 + L3 only;
  - Update: preserves `http.headers`, `http.auth`, `runtime` and environment values;
  - the Audience rule (spec Decision 8) and the collection-root location (`bruno/`, confirm before creating one);
  - Migrate: run `migrate.py`, then `brunocheck.py`; only when both exit 0, `git rm -r docs/api`;
  - the L1.5 `AskUserQuestion` offer (default yes);
  - an L2 prompt block with `SKILL_DIR` for each verifier;
  - L3 sweeps per mode.
- **`docs-template.md`:** the spec's layouts, table rules and Audience rules, with `testdata/good/account/create-account.yml` as the full example.
- **`yaml-reference.md`:** `skills/open-collection/references/yaml-reference.md`, with these changes:
  - section order `info → http → runtime → settings → docs`;
  - a `runtime.scripts` section (`type: tests`, Chai `expect`);
  - every renderer and removed-skill mention removed.
- **`bruno-verifier.md`:** `skills/api-spec/references/api-spec-verifier.md` and `skills/open-collection/references/col-verifier.md` merged. Its checks:
  - semantic fidelity to intent;
  - auth/header mapping;
  - runnable body vs `docs:`;
  - the K10 NOTEs: a ticket key or an error code?
- **`drift-verifier.md`:** `skills/openapi-doc/references/openapi-doc-verifier.md` plus the "M/O Classification" and "Drift Verification Checklist" sections of `skills/openapi-doc/references/openapi-doc-template.md`.
- **`agents/openai.yaml`:** `display_name: "Bruno"`, `short_description: "Bruno collection as API source of truth"`.

- [ ] **Step 1: Write all six files**

- [ ] **Step 2: Verify**

Run each:

```bash
node scripts/validate-skills.js
python3 -c "import yaml;print(len(yaml.safe_load(open('skills/bruno/SKILL.md').read().split('---')[1])['description']))"
grep -rnE "api-spec|open-collection|openapi-doc|confluence-api-doc" skills/bruno
```

Expected:
- `validate-skills.js` passes (20 skill directories exist at this point; the old four go in Task 7).
- The description length prints a number ≤ 1024.
- `grep` prints nothing.

---

### Task 7: Remove the old skills and repoint dependents

**Files:**
- Delete: `skills/api-spec/`, `skills/open-collection/`, `skills/openapi-doc/`, `skills/confluence-api-doc/`
- Modify: `scripts/validate-skills.js:31-56` (append the four names to `DEAD_SKILLS`)
- Modify: every row of the spec's "Changes outside `skills/bruno/`" table, except the `init-project` rows (Task 8)

**Interfaces:**
- Consumes: the skill name `bruno` and the contract path `bruno/<domain>/<endpoint>.yml` (`docs:`).

Exact replacements in `skills/bug-hunter/SKILL.md`:
- Line 125 becomes `code ← bruno ← ticket/spec ← docs/knowledge/{contracts,requirements}/ ← the originating issue`.
- The Ground 1 command:

```bash
for c in $(grep -rhoE '`"?[A-Z][A-Z0-9_]{5,}"?`' bruno --include='*.yml' | tr -d '`"' | sort -u); do
  grep -rqi "$c" docs/knowledge/ || echo "$c"
done
```

- The Ground 2 `declared` line:

```bash
grep -rhE '^\s*\| *[0-9]{3} *\|' bruno --include='*.yml' | awk -F'|' '{gsub(/[ `]/,"",$4); if ($4!="") print $4}' | sort -u > /tmp/declared
```

- "a scratch copy of the spec" becomes "a scratch copy of a request's `### Error Responses` table".

In `README.md`, the four table rows (`:132-135`) become this one row:

```markdown
| `bruno`              | Bruno collection at `bruno/`: API source of truth, drift check, migration |
```

Also change "19 skills" → "16 skills" (`README.md:5`, `AGENTS.md:7,9,21,36`), and in `AGENTS.md:12` drop the four names and insert `bruno` after `gitlab`.

- [ ] **Step 1: Delete the four directories and extend `DEAD_SKILLS`**

- [ ] **Step 2: Run the validator to list every stale reference**

Run: `node scripts/validate-skills.js`
Expected: FAIL. It lists `references removed skill` lines for each file in the spec table, except `docs/*.md` and the `init-project` template files that only mention `docs/api`.

- [ ] **Step 3: Edit every listed file, plus `docs/getting-started.md:29` and `docs/grok-setup.md:31`**

- [ ] **Step 4: Verify**

```bash
node scripts/validate-skills.js
ls skills | wc -l
grep -rnE "api-spec|open-collection|openapi-doc|confluence-api-doc|docs/api" README.md AGENTS.md docs/*.md skills | grep -v -E "^skills/(bruno|init-project)/"
```

Expected:
- `validate-skills.js` passes.
- `ls` prints `16`.
- `grep` prints nothing. The validator does not catch a bare `docs/api` mention, so this grep is what catches e2e-playwright lines such as `e2e-verifier.md:37`. `bruno` is excluded because Migrate needs `docs/api`, and `init-project` is excluded because Task 8 owns it.

---

### Task 8: `init-project` template

**Files:**
- Modify: `skills/init-project/assets/template/bruno/README.md`
- Modify: `skills/init-project/assets/template/bruno/opencollection.yml`
- Modify: `skills/init-project/assets/template/.kiro/steering/bruno.md`
- Modify: `skills/init-project/assets/template/.kiro/steering/errors.md:214`
- Modify: `skills/init-project/assets/template/.kiro/steering/new-feature-checklist.md:59`

**Interfaces:**
- Consumes: `brunocheck.py <root>` (Task 3).

Changes:
- **`opencollection.yml` `docs:`** gets three sections:
  - `## Overview` (keep the `neo-service` placeholder wording);
  - `## Error Response Body`, with the three common-lib fields;
  - `## Common Error Responses`, with the header row only.
- **`bruno/README.md`:** the collection is authored with the `bruno` skill and is the API source of truth.
- **`steering/bruno.md`:** the request layout and table rules from `skills/bruno/references/docs-template.md`, in short form. Remove every `openapi.yaml` mention, and change section order to `info → http → runtime → settings → docs`.
- **`errors.md:214`:** "update the endpoint's `### Error Responses` table in `bruno/<domain>/<endpoint>.yml`".
- **`new-feature-checklist.md:59`:** "Add or update the request under `bruno/<resource>/` with the `bruno` skill (contract in `docs:`)."

- [ ] **Step 1: Make the five edits**

- [ ] **Step 2: Verify**

```bash
python3 skills/bruno/assets/brunocheck.py skills/init-project/assets/template/bruno
grep -rnE "docs/api|openapi\.yaml|api-spec|open-collection" skills/init-project
node scripts/validate-skills.js
```

Expected:
- `brunocheck.py` prints `PASS: 0 error(s)` (zero requests, K11 satisfied).
- `grep` prints nothing.
- `validate-skills.js` passes.

---

### Task 9: Real-data migration and package validation

**Files:**
- Modify (only if a defect is found): `skills/bruno/assets/*.py` + a regression test in the matching `test_*.py`

**Interfaces:**
- Consumes: all CLIs.

- [ ] **Step 1: Copy two real repos into the scratchpad (read-only sources)**

```bash
S=/private/tmp/claude-502/-Users-witoo-h-dev-witooh-neo-plugin/1b6ceb2a-d6c3-4b3a-84a2-c15146b2dca3/scratchpad/realdata
mkdir -p "$S"
for r in account-service consent-service; do rsync -a --exclude .git --exclude vendor /Users/witoo.h/dev/tcrb/$r/ "$S/$r/"; done
```

- [ ] **Step 2: Migrate and check each copy**

```bash
for r in account-service consent-service; do
  python3 skills/bruno/assets/migrate.py "$S/$r/docs/api" "$S/$r/bruno"; echo "migrate=$?"
  python3 skills/bruno/assets/brunocheck.py "$S/$r/bruno"; echo "brunocheck=$?"
done
```

Expected: both print `migrate=0`. `brunocheck` prints `0`, or each remaining ERROR is classified as one of two things:
- **source defect:** the legacy YAML is itself wrong. List it in the final report and do not change the script.
- **script defect:** fix the script, add a regression test that reproduces it, then re-run this step.

- [ ] **Step 3: Drift check on one copy**

Run: `python3 skills/bruno/assets/driftcheck.py "$S/account-service/bruno" --src "$S/account-service"`
Expected: it runs to a `PASS` or `DRIFT FOUND` summary with no Python traceback. Record the count in the report. Drift here is real data, not a test failure.

- [ ] **Step 4: Full validation**

```bash
python3 -m unittest discover -s skills/bruno/assets -p 'test_*.py' -v
node scripts/validate-skills.js
node scripts/validate-pi-package.js
node scripts/validate-omp-package.js
node scripts/validate-grok-package.js
node scripts/validate-cursor-package.js
node scripts/validate-codex-package.js
claude plugin validate .
grep -rn "docs/api" . --exclude-dir=.git | grep -v -E "^\./(docs/superpowers|skills/bruno)/"
```

Expected:
- Every unittest passes.
- Each validator exits 0.
- The last `grep` prints nothing, so `docs/api` appears only in the spec, the plan and `skills/bruno/`.

- [ ] **Step 5: Report against the spec's success criteria 1–7, with each command's actual output**
