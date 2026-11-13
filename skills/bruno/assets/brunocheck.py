#!/usr/bin/env python3
"""L1 structural checker for a Bruno OpenCollection whose request `docs:` blocks hold the endpoint contracts.

Rules here: K1 file shape/order, K2 docs headings + endpoint, K3 path params, K7 status test,
K8 env vars/secrets, K9 folder.yml + unique seq, K4 field tables, K5 example vs table,
K6 error tables, K10 leaked internals, K11 root docs headings, K12 auth key, K13 query params
in the url, K14 literal ids sent (NOTE). Usage: brunocheck.py <bruno-root>
Exit 1 iff any ERROR. Stdlib + PyYAML only. Regex helpers are ported from the legacy collection checker.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import docsparse as dp  # noqa: E402
except ModuleNotFoundError as e:
    if e.name != "yaml":
        raise
    sys.exit(print("brunocheck.py: needs PyYAML (pip install pyyaml)", file=sys.stderr) or 2)

RE_LEADING_VAR = re.compile(r"^\{\{[^}]*\}\}")
RE_VAR = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
RE_DOC_PARAM = re.compile(r"(?<!\{)\{([^{}]+)\}(?!\})")
RE_COLON_PARAM = re.compile(r"(?:(?<=/)|^):([^/?#]+)")
RE_STATUS_TEST = re.compile(r"\bres\.(status\b|getStatus\(\))")
RE_PROCESS_ENV = re.compile(r"\{\{\s*process\.env\.\w+\s*\}\}")
RE_UUID = re.compile(r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b")
REQUIRED_HEADINGS = ["Purpose", "Request", "Endpoint", "Auth", "Response"]
SECRET_WORDS = {"password", "secret", "token", "bearer", "otp"}
PII_WORDS = {"pin", "national", "citizen", "cif", "biometric"}
RESPONSE_STATUSES = {"001": 400, "002": 400, "003": 404, "004": 409, "005": 503, "006": 504, "999": 500}
COMMON_LIB_CODE = r"[A-Z]{2,3}-[0-9]{4}"
REQUIRED_ROOT_HEADINGS = ["Error Response Body", "Common Error Responses"]
AUTH_NONE = "{} is `none`, which Bruno rejects (`Unsupported auth type`): omit the key"
LEAK_PATTERNS = [
    (re.compile(r"(?<![\w/.])internal/[\w./-]+"), "internal source path"),
    (re.compile(r"\bdocs/(knowledge|tasks)/"), "docs/knowledge or docs/tasks reference"),
    (re.compile(r"[\w./-]+\.go:\d+"), "Go file:line reference"),
    (re.compile(r"\bAC-\d{2,4}\b"), "acceptance-criterion id"),
    (re.compile(r"\bD-\d+\b"), "decision id"),
    (re.compile(r"^#{1,6}\s*contract source\b", re.I | re.M), "`Contract source` heading"),
]
RE_TICKET = re.compile(r"\b[A-Z]{2,}-\d+\b")
RE_AC_ID = re.compile(r"^AC-\d{2,4}$")
# Bruno dynamic variables (`{{$name}}`), copied verbatim from
# https://docs.usebruno.com/testing/script/dynamic-variables (fetched 2026-11-09). `$uuid` is not on it.
BRUNO_DYNAMIC_VARS = {
    "guid", "timestamp", "isoTimestamp", "randomUUID", "randomNanoId", "randomAlphaNumeric",
    "randomBoolean", "randomInt", "randomColor", "randomHexColor", "randomAbbreviation", "randomWord",
    "randomWords",
    "randomIP", "randomIPV4", "randomIPV6", "randomMACAddress", "randomPassword", "randomLocale",
    "randomUserAgent", "randomProtocol", "randomSemver", "randomDomainName", "randomDomainSuffix",
    "randomDomainWord", "randomExampleEmail", "randomEmail", "randomUserName", "randomUrl",
    "randomFirstName", "randomLastName", "randomFullName", "randomNamePrefix", "randomNameSuffix",
    "randomJobArea", "randomJobDescriptor", "randomJobTitle", "randomJobType", "randomPhoneNumber",
    "randomPhoneNumberExt",
    "randomCity", "randomStreetName", "randomStreetAddress", "randomCountry", "randomCountryCode",
    "randomLatitude", "randomLongitude",
    "randomAvatarImage", "randomImageUrl", "randomAbstractImage", "randomAnimalsImage",
    "randomBusinessImage", "randomCatsImage", "randomCityImage", "randomFoodImage",
    "randomNightlifeImage", "randomFashionImage", "randomPeopleImage", "randomNatureImage",
    "randomSportsImage", "randomTransportImage", "randomImageDataUri",
    "randomBankAccount", "randomBankAccountName", "randomCreditCardMask", "randomBankAccountBic",
    "randomBankAccountIban", "randomTransactionType", "randomCurrencyCode", "randomCurrencyName",
    "randomCurrencySymbol", "randomBitcoin",
    "randomCompanyName", "randomCompanySuffix", "randomBs", "randomBsAdjective", "randomBsBuzz",
    "randomBsNoun", "randomCatchPhrase", "randomCatchPhraseAdjective", "randomCatchPhraseDescriptor",
    "randomCatchPhraseNoun",
    "randomDatabaseColumn", "randomDatabaseType", "randomDatabaseCollation", "randomDatabaseEngine",
    "randomDateFuture", "randomDatePast", "randomDateRecent", "randomWeekday", "randomMonth",
    "randomFileName", "randomFileType", "randomFileExt", "randomCommonFileName", "randomCommonFileType",
    "randomCommonFileExt", "randomFilePath", "randomDirectoryPath", "randomMimeType",
    "randomPrice", "randomProduct", "randomProductAdjective", "randomProductMaterial",
    "randomProductName", "randomDepartment",
    "randomNoun", "randomVerb", "randomIngverb", "randomAdjective", "randomPhrase", "randomLoremWord",
    "randomLoremWords", "randomLoremSentence", "randomLoremSentences", "randomLoremParagraph",
    "randomLoremParagraphs", "randomLoremText", "randomLoremSlug", "randomLoremLines",
}


def _strip_query(p):
    return re.split(r"[?#]", p or "", maxsplit=1)[0].strip()


def norm_path(p):
    p = RE_LEADING_VAR.sub("", _strip_query(p))
    p = re.sub(r"\{\{[^}]*\}\}", "{}", p)
    p = re.sub(r"\{[^}]+\}", "{}", p)
    p = re.sub(r"(?:(?<=/)|^):[^/?#]+", "{}", p)
    return p.rstrip("/") if len(p) > 1 else p


def url_path_params(url):
    p = RE_LEADING_VAR.sub("", _strip_query(url))
    names = set(RE_COLON_PARAM.findall(p))
    names |= {m.strip() for m in re.findall(r"\{\{\s*([^}]+?)\s*\}\}", p)}
    return names


def _request_paths(root):
    out = []
    for path in sorted(root.rglob("*.yml")):
        rel = path.relative_to(root)
        if rel.parts[0] == "environments" or path.name in ("folder.yml", "opencollection.yml"):
            continue
        out.append(path)
    return out


def _rel(root, path):
    return Path(path).relative_to(root).as_posix()


def _segments(name):
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", str(name))
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", spaced)
    return [p.lower() for p in re.split(r"[_\-.\s]+", spaced) if p]


def _is_empty(value):
    """No committed value: blank, or wholly a `{{process.env.X}}` reference to the OS env."""
    return value is None or str(value).strip() == "" or bool(RE_PROCESS_ENV.fullmatch(str(value).strip()))


def _env_files(root):
    """{rel: {name: value}} for every environments/*.yml, plus K1 findings for unreadable ones."""
    envs, findings = {}, []
    for path in sorted((root / "environments").rglob("*.yml")) if (root / "environments").is_dir() else []:
        rel = _rel(root, path)
        try:
            envs[rel] = dp._env_vars(dp.load_yaml_with_order(path)[0])
        except dp.ParseError as exc:
            findings.append(("ERROR", "K1", rel, exc.msg))
    return envs, findings


def _section_tables(md):
    """[(kind, title, header, rows)] for every table under a known table heading; kind is 'field' or 'error'."""
    out = []
    for sec in dp.split_sections(md):
        key = sec["title"].lower()
        if key in dp._TABLE_SECTIONS or key.startswith("http status") or key == "error response body":
            kind = "field"
        elif key in ("error responses", "common error responses"):
            kind = "error"
        else:
            continue
        table = dp.parse_table(sec["body"])
        if table:
            out.append((kind, sec["title"], table[0], table[1]))
    return out


def _check_field_table(title, rows):
    """K4 row checks; returns messages."""
    out = []
    by_name = {r["name"]: r for r in rows}
    for r in rows:
        if r["type"] not in dp.TYPES:
            out.append(f"{title}: `{r['name']}` has type {r['type']!r}, expected one of {sorted(dp.TYPES)}")
        if r["mandatory"] not in dp.MANDATORY:
            out.append(f"{title}: `{r['name']}` has mandatory {r['mandatory']!r}, expected Yes or No")
        parent, _, _ = r["name"].rpartition(".")
        if not parent:
            continue
        is_array = parent.endswith("[]")
        base = parent[:-2] if is_array else parent
        want = "Array" if is_array else "Object"
        if is_array and not base:
            continue  # `[].x` in a top-level array body: its parent is the body itself
        if base not in by_name:
            out.append(f"{title}: `{r['name']}` has no parent row `{base}`")
        elif by_name[base]["type"] != want:
            out.append(f"{title}: parent `{base}` of `{r['name']}` must have type {want}")
    return out


def _check_tables(md, errors, rel):
    """K4 (field tables) and K6 (error table header + common-lib codes) for one docs block."""
    f = []
    for kind, title, header, rows in _section_tables(md):
        if kind == "field":
            if header != dp.FIELD_HEADER:
                f.append(("ERROR", "K4", rel, f"{title}: header {header} != {dp.FIELD_HEADER}"))
            f += [("ERROR", "K4", rel, m) for m in _check_field_table(title, dp.field_rows(header, rows))]
        elif header != dp.ERROR_HEADER:
            f.append(("ERROR", "K6", rel, f"{title}: header {header} != {dp.ERROR_HEADER}"))
    for e in errors:
        code = e["error_code"]
        if not re.fullmatch(COMMON_LIB_CODE, code):
            continue
        rc = e["response_code"]
        if not rc:
            f.append(("ERROR", "K6", rel, f"common-lib error {code} is missing a Response Code"))
        elif rc not in RESPONSE_STATUSES:
            f.append(("ERROR", "K6", rel, f"unknown common-lib Response Code {rc!r} for {code}"))
        elif e["status"] != RESPONSE_STATUSES[rc]:
            f.append(("ERROR", "K6", rel, f"Response Code {rc!r} requires HTTP {RESPONSE_STATUSES[rc]}, got {e['status']!r}"))
    return f


def _parse_example(text, label, add):
    try:
        return dp.key_paths(dp.json_with_vars(text))
    except ValueError as exc:
        add("ERROR", "K5", f"{label} is not valid JSON: {exc}")
        return None


def _compare_example(label, paths, rows, add):
    names = {r["name"] for r in rows}
    for path in sorted(paths - names):
        add("ERROR", "K5", f"{label}: key `{path}` has no table row")
    for r in rows:
        if r["mandatory"] != "Yes":
            continue
        parent = r["name"].rpartition(".")[0]
        if parent.endswith("[]"):  # an array parent is present only when it has an element
            present = any(p.startswith(parent + ".") for p in paths)
        else:
            present = not parent or parent in paths
        if present and r["name"] not in paths:
            add("ERROR", "K5", f"{label}: required field `{r['name']}` is missing from the Example")


def _check_examples(req, rel):
    f = []

    def add(level, rule, msg):
        f.append((level, rule, rel, msg))

    docs = req["docs"]
    body_rows = docs["tables"]["body"]
    example = docs["request_example"]
    example_paths = None
    if example is not None:
        example_paths = _parse_example(example, "request Example", add)
        if example_paths is not None:
            _compare_example("request Example", example_paths, body_rows, add)
    elif body_rows:
        add("ERROR", "K5", "`### Body (JSON)` table has no `### Example` after it")

    http = req["http"] if isinstance(req["http"], dict) else {}
    body = http.get("body") if isinstance(http.get("body"), dict) else {}
    has_data = body.get("type") == "json" and isinstance(body.get("data"), str)
    if has_data and body["data"].strip() and (example is None or not body_rows):
        add("ERROR", "K5", "http.body.data is sent but docs has no `### Body (JSON)` table followed by an `### Example`")
    if has_data and example_paths is not None:
        data_paths = _parse_example(body["data"], "http.body.data", add)
        if data_paths is not None and data_paths != example_paths:
            add("ERROR", "K5", f"http.body.data key paths differ from the request Example: "
                               f"only in data {sorted(data_paths - example_paths)}, "
                               f"only in Example {sorted(example_paths - data_paths)}")

    for status, resp in docs["responses"].items():
        if resp["example"] is None:
            continue
        label = f"HTTP Status {status} Example"
        paths = _parse_example(resp["example"], label, add)
        if paths is not None:
            _compare_example(label, paths, resp["fields"], add)
    return f


def _check_leaks(text, rel, declared):
    out = []
    for pattern, what in LEAK_PATTERNS:
        m = pattern.search(text)
        if m:
            out.append(("ERROR", "K10", rel, f"docs leak an {what}: `{m.group(0).strip()}`"))
    for token in sorted(set(RE_TICKET.findall(text)) - declared):
        if not RE_AC_ID.match(token):
            out.append(("NOTE", "K10", rel, f"`{token}` looks like a ticket key but is not a declared Error Code"))
    return out


def _route_key(req):
    """(METHOD, normalised path) of a request, or None when its http block is unusable."""
    http = req["http"] if isinstance(req["http"], dict) else {}
    if not isinstance(http.get("method"), str) or not isinstance(http.get("url"), str):
        return None
    return http["method"].upper(), norm_path(http["url"])


def _enclosing_auth(root, directory):
    """The auth a folder.yml between `directory` and `root` hands to its requests, or None."""
    for d in (directory, *directory.parents):
        if d == root or root not in d.parents:
            return None
        try:
            data = dp.load_yaml_with_order(d / "folder.yml")[0] if (d / "folder.yml").is_file() else {}
        except dp.ParseError:
            data = {}
        request = data.get("request") if isinstance(data, dict) else None
        auth = request.get("auth") if isinstance(request, dict) else None
        if auth not in (None, "inherit", "none"):
            return auth
    return None


def _check_request(req, rel, env_names, folder_auth=None):
    f = []

    def add(level, rule, msg):
        f.append((level, rule, rel, msg))

    order = req["order"]
    for key in ("info", "http", "settings", "docs"):
        if key not in order:
            add("ERROR", "K1", f"missing top-level `{key}`")
    present = [k for k in order if k in dp.TOP_ORDER]
    if present != sorted(present, key=dp.TOP_ORDER.index):
        add("ERROR", "K1", f"top-level keys out of order: {present}, expected order {dp.TOP_ORDER}")

    http = req["http"] if isinstance(req["http"], dict) else {}
    docs = req["docs"]
    headings = docs["headings"]
    for h in REQUIRED_HEADINGS:
        if h not in headings:
            add("ERROR", "K2", f"docs missing heading `{h}`")
    for status in docs["duplicate_statuses"]:
        add("ERROR", "K2", f"duplicate `### HTTP Status: {status}`")
    if not any(status < 400 for status in docs["responses"]):
        add("ERROR", "K2", "no success `### HTTP Status: N` section (N < 400)")

    url = http.get("url") if isinstance(http.get("url"), str) else ""
    params = http.get("params") if isinstance(http.get("params"), list) else []
    endpoint = docs["endpoint"]
    doc_names = set()
    if "Endpoint" in headings:
        if endpoint is None:
            add("ERROR", "K2", "`### Endpoint` has no `METHOD /path` line")
        else:
            method, path = endpoint
            if method != str(http.get("method", "")).upper():
                add("ERROR", "K2", f"Endpoint method {method} != http.method {http.get('method')}")
            if norm_path(path) != norm_path(url):
                add("ERROR", "K2", f"Endpoint path {norm_path(path)} != http.url path {norm_path(url)}")
            doc_names = set(RE_DOC_PARAM.findall(path))
    if endpoint is not None:
        table_names = {r["name"] for r in docs["tables"]["path"]}
        url_names = url_path_params(url)
        if not (doc_names == table_names == url_names):
            add("ERROR", "K3", f"path params differ: docs path {sorted(doc_names)}, "
                               f"Path Parameters table {sorted(table_names)}, url {sorted(url_names)}")
        typed = {p.get("name") for p in params if isinstance(p, dict) and p.get("type") == "path"}
        for name in sorted(RE_COLON_PARAM.findall(RE_LEADING_VAR.sub("", _strip_query(url)))):
            if name not in typed:
                add("ERROR", "K3", f"`:{name}` has no http.params row with type: path")

    if http.get("auth") == "none":
        add("ERROR", "K12", AUTH_NONE.format("http.auth"))
    elif "auth" in http and (docs["auth"] or "").lower() == "none":
        if http["auth"] != "inherit":
            add("ERROR", "K12", "`### Auth` is `None` but http.auth sets an auth: omit the key or use `inherit`")
        elif folder_auth is not None:
            add("ERROR", "K12", "`### Auth` is `None` but `auth: inherit` picks up the auth a folder.yml sets: "
                                "omit the key")

    sent = {kv.split("=", 1)[0] for kv in url.split("#", 1)[0].partition("?")[2].split("&")}
    for p in params:
        if isinstance(p, dict) and p.get("type") == "query" and p.get("name") not in sent:
            add("ERROR", "K13", f"query param `{p.get('name')}` is not in the http.url query string: "
                                f"Bruno sends only the query the url carries")

    body = http.get("body") if isinstance(http.get("body"), dict) else {}
    sent_text = " ".join([url, str(body.get("data") or "")] +
                         [str(p.get("value") or "") for p in params if isinstance(p, dict)])
    for uid in sorted(set(RE_UUID.findall(sent_text))):
        add("NOTE", "K14", f"the request sends the literal id `{uid}`: an id that must name an existing "
                           f"record is an environment variable, an optional id that turns a create into "
                           f"an update is left out")

    runtime = req["runtime"] if isinstance(req["runtime"], dict) else {}
    scripts = runtime.get("scripts") if isinstance(runtime.get("scripts"), list) else []
    if not any(isinstance(s, dict) and s.get("type") == "tests" and RE_STATUS_TEST.search(str(s.get("code") or ""))
               for s in scripts):
        add("ERROR", "K7", "no runtime test script asserting res.status")

    request_vars = dp._env_vars(runtime)
    f += _undefined_vars(json.dumps(http, default=str), env_names | set(request_vars), rel)
    f += _check_env_values(rel, request_vars)
    f += _check_tables(req["docs_raw"], docs["errors"], rel)
    f += _check_examples(req, rel)
    return f


def _undefined_vars(text, env_names, rel):
    out = []
    for name in sorted(set(RE_VAR.findall(text))):
        if name.startswith("process.env.") or (name.startswith("$") and name[1:] in BRUNO_DYNAMIC_VARS):
            continue
        if name not in env_names:
            out.append(("ERROR", "K8", rel, f"`{{{{{name}}}}}` is not defined in environments/"))
    return out


def _check_env_values(rel, variables):
    out = []
    for name, value in variables.items():
        if _is_empty(value):
            continue
        segs = _segments(name)
        if SECRET_WORDS & set(segs) or "".join(segs) == "apikey" \
                or ("api", "key") in zip(segs, segs[1:]):
            out.append(("ERROR", "K8", rel, f"secret-like variable `{name}` has a committed value"))
        elif PII_WORDS & set(segs):
            out.append(("NOTE", "K8", rel, f"`{name}` may hold personal data and has a value"))
    return out


def check(root):
    root = Path(root)
    findings = []
    root_docs_raw = None
    try:
        root_data = dp.load_yaml_with_order(root / "opencollection.yml")[0]
        root_docs_raw = root_data.get("docs") or ""
        if not isinstance(root_docs_raw, str):
            findings.append(("ERROR", "K1", "opencollection.yml", "`docs` must be a string"))
            root_docs_raw = None
    except dp.ParseError as exc:
        findings.append(("ERROR", "K1", "opencollection.yml", exc.msg))

    envs, env_findings = _env_files(root)
    findings += env_findings
    env_names = {n for variables in envs.values() for n in variables}
    for rel, variables in envs.items():
        findings += _check_env_values(rel, variables)

    parsed = []
    for path in _request_paths(root):
        rel = _rel(root, path)
        try:
            parsed.append((path, rel, dp.parse_request(path)))
        except dp.ParseError as exc:
            findings.append(("ERROR", "K1", rel, exc.msg))
    documented = {_route_key(req) for _, _, req in parsed if "docs" in req["order"]}

    by_dir = {}
    requests = []
    for path, rel, req in parsed:
        key = _route_key(req)
        if key is not None and "docs" not in req["order"] and key in documented:
            method, url = key[0], RE_LEADING_VAR.sub("", _strip_query(req["http"]["url"]))
            findings.append(("NOTE", "K1", rel, f"extra request for {method} {url} (no `docs:`): not checked"))
            continue
        findings += _check_request(req, rel, env_names, _enclosing_auth(root, path.parent))
        by_dir.setdefault(path.parent, []).append((rel, req))
        requests.append((rel, req))

    declared = {e["error_code"] for _, req in requests for e in req["docs"]["errors"]}
    if root_docs_raw is not None:
        root_docs = dp.parse_root_docs(root_docs_raw)
        declared |= {e["error_code"] for e in root_docs["common_errors"]}
        findings += _check_tables(root_docs_raw, root_docs["common_errors"], "opencollection.yml")
        for h in REQUIRED_ROOT_HEADINGS:
            if h not in root_docs["headings"]:
                findings.append(("ERROR", "K11", "opencollection.yml", f"root docs missing heading `{h}`"))
        if any(s["title"] == "Error Response Body" and s["body"].strip() == "Not documented in the source spec."
               for s in dp.split_sections(root_docs_raw)):
            findings.append(("NOTE", "K11", "opencollection.yml", "`## Error Response Body` reads `Not documented in "
                             "the source spec.`: a human must document the error body"))
        findings += _check_leaks(root_docs_raw, "opencollection.yml", declared)
    for rel, req in requests:
        findings += _check_leaks(req["docs_raw"], rel, declared)

    for directory in sorted(by_dir):
        folder = directory / "folder.yml"
        if directory != root:
            if not folder.is_file():
                findings.append(("ERROR", "K9", _rel(root, directory) + "/", "directory holds requests but has no folder.yml"))
        seen = {}
        for rel, req in by_dir[directory]:
            seq = req["info"].get("seq") if isinstance(req["info"], dict) else None
            if seq is None:
                continue
            if seq in seen:
                findings.append(("ERROR", "K9", rel, f"info.seq {seq} duplicates {seen[seq]}"))
            else:
                seen[seq] = rel

    for folder in sorted(root.rglob("folder.yml")):
        rel = _rel(root, folder)
        try:
            data = dp.load_yaml_with_order(folder)[0]
        except dp.ParseError as exc:
            findings.append(("ERROR", "K1", rel, exc.msg))
            continue
        findings += _undefined_vars(json.dumps(data.get("request"), default=str), env_names, rel)
        if isinstance(data.get("request"), dict) and data["request"].get("auth") == "none":
            findings.append(("ERROR", "K12", rel, AUTH_NONE.format("request.auth")))
        if isinstance(data.get("docs"), str):
            findings += _check_leaks(data["docs"], rel, declared)
    return findings


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: brunocheck.py <bruno-root>", file=sys.stderr)
        return 2
    root = Path(argv[0])
    findings = check(root)
    errors = [x for x in findings if x[0] == "ERROR"]
    bad_files = {x[2] for x in errors}
    for path in _request_paths(root):
        rel = _rel(root, path)
        print(f"{'✗' if rel in bad_files else '✓'} {rel}")
    for level, rule, file, msg in findings:
        suffix = " — needs fresh-eyes" if level == "NOTE" else ""
        print(f"{level} {rule} {file}: {msg}{suffix}")
    print(f"FAIL: {len(errors)} error(s)" if errors else "PASS: 0 error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
