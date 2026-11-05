# OpenSearch: historical logs for SIT and UAT

One recipe for Core + Auxiliary, SIT + UAT. Use when **kubectl is not enough**
(window older than the live pod, multi-pod history, count/group by `msg`).
The shared cluster inspection procedure owns the path choice; this file is only the OS recipe.

## When to use

| Need | Path |
|---|---|
| Last ~15–30m, deploy/pod still up | **kubectl first** (`--since=15m`), shared procedure §4 |
| Older window / pod rotated / aggregate by `msg` / multi-pod history | **This recipe** |
| UAT, any window | **This recipe first** (`neo-core-uat/references/uat-access.md`) |
| Auxiliary SIT, older window or counts, while kubectl is blocked | **This recipe** (`neo-aux-sit` bindings); live pods use Argo REST `/logs` |

## Bind the active environment first

Use `OS_HOST`, `OS_INDEX`, `OS_VERSION` and, when set, `OS_CLUSTER` (a `cluster_name.keyword`
filter) from the active skill, verified against that environment. SIT values are recorded below;
UAT values are in `neo-core-uat/references/uat-access.md`. Resolve an empty binding from verified
infrastructure/configuration or the actual Dashboards UI; if unavailable, ask the user before a
historical search. Do not replace `sit` in a hostname or silently search the SIT index.
Read the current Dashboards version from the UI or `GET /_dashboards/api/status` before setting
`osd-version`. Bind `OS_INDEX` and `OS_VERSION` as strings in the browser evaluation below.
If a store spans environments/clusters, require an environment-specific index or a verified
cluster/environment filter from its mapping; a container name alone does not isolate UAT.

Log searches always target the wrapper's `OS_INDEX` (`console-sit-log` on SIT, `console-uat-log`
on UAT). Never take the index from the Dashboards `defaultIndex` setting or from what Discover
opens: on SIT that default is `access-sit-log` (2026-11-05). Search `access-<env>-log` or
`audit-<env>-log` only when the user asks for access or audit logs.

## Verified SIT surface (2026-11-05; not UAT defaults)

| | |
|---|---|
| Host | `https://opensearch.sit.awesome-poc-th.com`, for Core and Auxiliary |
| Dashboards | `3.7.0` |
| Index / pattern title | `console-sit-log`, an alias over rolled-over indices; the first was created 2026-11-02 |
| Index-pattern id | `c54fbf80-d82a-11f1-8e7b-53a37eebf317` |
| Other patterns | `access-sit-log` (Dashboards `defaultIndex`), `audit-sit-log` |
| Time field | `@timestamp` |
| Container field | `kubernetes_container_name.keyword` (exact `term`; e.g. `payment`) |
| Cluster field | `cluster_name.keyword`: `core-systems-dev` (Core), `auxiliary-systems-dev` (Aux); despite `dev`, both matched live SIT nodes |
| Core namespaces indexed | `core-systems`, `kong`; the live fluent-bit `grep` filter drops the rest |
| Aux namespaces indexed | `kong`, `portal`, `ekyc`, `consent`, `special-list`, `email`, `e-signature`, `branch-device` (24h to 2026-11-05) |
| Auth | Browser SAML session cookies (**httpOnly**: not in `document.cookie`) |

Every indexed host belongs to the new clusters: Core's two match `kubectl get nodes`; Auxiliary's eight
sit in its subnets, and its four running nodes match `ec2 describe-instances`. So `cluster_name` selects
the new cluster and old SIT's logs are not here. The oldest hits are Core 2026-11-02T05:30Z and Auxiliary
2026-11-04T08:08Z. Retention was not measured.

Zero hits is not proof of no logs. Core `payment` has no hits, while kubectl shows two lines from
2026-11-02T05:02Z, before fluent-bit started at 05:25Z with `read.head: Off`. Check kubectl or Argo before
reporting no logs.

Core's fluent-bit writes to `os.sit.awesome-poc-th.com` (live `fluent-bit-cluster-info` ConfigMap), which
resolves to the same private address as `opensearch.sit`, and those logs appear on `opensearch.sit`. Do
not browse `os.sit`: its SAML login ends on `opensearch.sit` with 400 `Invalid requestId`.

`ERR_NAME_NOT_RESOLVED` is a DNS failure, not an SSO prompt. Neither name resolved from the laptop on
2026-11-04 and both did on 2026-11-05; the cause was not measured. Report it and read live pods through
kubectl or Argo instead.

### Working SIT search endpoints (measured 2026-11-05)

```
POST /_dashboards/api/console/proxy?path=console-sit-log%2F_search&method=POST
```

The body is the plain query, and the response is the raw search response, where `hits.total` is
`{ value, relation }`. Required headers (SIT measurement; use the active environment's verified version):

- `osd-xsrf: true`
- `osd-version: 3.7.0`
- `content-type: application/json`
- `accept: application/json`

These returned identical hits in the same session, with the same headers:

```
POST /_dashboards/internal/search/opensearch-with-long-numerals
POST /_dashboards/internal/search/opensearch
```

Their body wraps the query as `{ "params": { "index": "console-sit-log", "body": { …ES DSL… } } }`. Their
response nests the search result under `rawResponse`, and `rawResponse.hits.total` is a plain number, so
`hits.total.value` is `undefined` there and the count gate below must read the number. No difference from
`opensearch` was seen; the test results held no integer above 2^53. Neither route was measured on UAT.

Status check: `GET /_dashboards/api/status` → version number `3.7.0`; it answers without a login.

## Hard constraints (measured failures)

1. **Sync XHR when the browser evaluate cannot await.**  
   `tab.evaluate(() => fetch(…))` returns a Promise this harness cannot await  
   (“tab.evaluate() returned a Promise…”). Use **synchronous** `XMLHttpRequest`  
   (`xhr.open(method, url, false)`).  
   Claude in Chrome's `javascript_tool` does evaluate top-level `await`, so `fetch` works there
   (measured on UAT 2026-10-29).

2. **Do not document cookie-export → shell curl as working.**  
   Session cookies are httpOnly; `document.cookie` is empty.  
   `page.cookies` was not available on this browser surface.  
   Cookie jar / CDP `Network.getAllCookies` → curl = **unproven**.

3. **Cold start / expired SSO.**  
   Opening the host does not guarantee an authenticated session.  
   If the page is a login / SSO redirect (or XHR returns 401/302/HTML login),  
   **stop and ask the user to log in** in that tab, then retry.  
   Do not loop or invent tokens.

4. **Filter logs with the `grep` tool**, not `bash | rg` / `bash | grep`  
   (repo interceptor blocks those). For kubectl: write logs to a temp file or  
   use the command output artifact, then `grep` tool.

## Procedure (agent)

1. Open (or reuse) a browser tab on the verified active environment's
   `OS_HOST` + `/_dashboards/app/home` (Discover URL optional).
2. Wait for app shell. If login/SSO → ask user to authenticate → wait for home/Discover.
3. Run **sync XHR** search via `tab.evaluate` (plain return value, no async/fetch).
4. **Count-complete tally (required before stating totals):**
   - Read `total = hits.total.value` (with `track_total_hits: true`).
   - If `hits.hits.length < total`, re-query with `size >= total` (cap reasonably, e.g. 1000). Over the cap, page with `search_after` set to the last hit's `sort` values; the `_id` tiebreaker in the body stops equal timestamps from skipping or repeating hits.
   - For each hit: `JSON.parse(_source.log)` → `msg` / `level` (fallback: raw slice if parse fails).
   - Build `counts[msg]++` and `levels[level]++` over **all returned hits**.
   - **Gate:** `sum(counts) === total` and `returned === total`. If not equal, do not publish the table as “full”, raise `size` or mark as partial top-N.
   - Sort `counts` desc for the report. (Measured: payment error/warn 24h → 78 hits, client tally summed to 78 after `size: 200` ≥ 78. A prior `size: 50` tally summed to 50 and was wrongly presented as full, do not repeat.)
5. Report in Thai: total hits, **full** counts by `msg` (only if gate passed), level split, a few timestamped examples, pod name if present.

## Body: logs for one container (copy-paste)

Replace `OS_CLUSTER` with the active wrapper's value, `CONTAINER` (e.g. `payment`) with the exact
live container name, and the time range as needed. For a new environment, verify its timestamp,
container, cluster and log fields before applying this query shape; adapt to the observed mapping.
The `should` block below keeps **error+warn**; drop it (or swap needles) for info/all-level or free-text hunts, always keep cluster + container + time `filter`.

```json
{
  "size": 200,
  "track_total_hits": true,
  "sort": [
    { "@timestamp": { "order": "desc", "unmapped_type": "boolean" } },
    { "_id": { "order": "desc" } }
  ],
  "query": {
    "bool": {
      "filter": [
        { "term": { "cluster_name.keyword": "OS_CLUSTER" } },
        { "term": { "kubernetes_container_name.keyword": "CONTAINER" } },
        {
          "range": {
            "@timestamp": {
              "gte": "now-24h",
              "lte": "now",
              "format": "strict_date_optional_time"
            }
          }
        }
      ],
      "should": [
        { "match_phrase": { "log": "\"level\":\"error\"" } },
        { "match_phrase": { "log": "\"level\":\"warn\"" } }
      ],
      "minimum_should_match": 1
    }
  },
  "_source": [
    "@timestamp",
    "log",
    "kubernetes_container_name",
    "kubernetes_pod_name",
    "kubernetes_namespace_name"
  ]
}
```

Notes:

- `log` is a **string** of JSON (not structured fields). Phrase-match on substrings inside `log`; parse client-side for `msg` / `level` / `error.message`.
- **No dedicated `level` / `service` / `msg` fields**: do **not** query `level:error` as an ES field. Filter with `match_phrase` on `log` for `"\"level\":\"error\""` / `"\"level\":\"warn\""` (body above).
- There is **no reliable ES `terms` agg on `msg`** here: `msg` lives inside the string. Client-side parse + count is the measured path.
- Match containers with `term` on `kubernetes_container_name.keyword`, never `match_phrase`: the
  text field is tokenized. On SIT, `match_phrase` `transaction` hit 5 containers across both
  clusters (62,061 vs 2,303 exact in 24h, 2026-10-29).
- `terms` aggregations do work on the `.keyword` metadata fields (SIT and UAT). Resolve live
  namespace and container names before searching:

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "term": { "cluster_name.keyword": "OS_CLUSTER" } },
    { "range": { "@timestamp": { "gte": "now-7d" } } }
  ] } },
  "aggs": { "ns": {
    "terms": { "field": "kubernetes_namespace_name.keyword", "size": 50 },
    "aggs": { "c": { "terms": { "field": "kubernetes_container_name.keyword", "size": 50 } } }
  } }
}
```
- Some older backing indices lack `@timestamp` mapping → shard failures in response are OK if `hits.total` and current indices still return data. Prefer `unmapped_type: "boolean"` on the sort as above.
- **`size` is not optional decoration.** Counts built from `hits.hits` only cover `min(size, total)`. Always gate with `sum(counts) === hits.total.value` before calling a table complete.
- For a free-text needle, add  
  `{ "match_phrase": { "log": "YOUR TEXT" } }`  
  to `filter` or `should`.

## Minimal sync-XHR evaluate sketch (count-complete)

Bind `esBody` to the complete JSON query above, with the live container/time range and any
required environment filter. Pass it and the verified `OS_INDEX` / `OS_VERSION` into the same
browser evaluation scope; do not replace the query with an empty object.

```js
// inside tab.evaluate: synchronous; bind OS_INDEX, OS_VERSION and esBody first
function sxhr(method, url, body) {
  const xhr = new XMLHttpRequest();
  xhr.open(method, url, false);
  xhr.setRequestHeader("osd-xsrf", "true");
  xhr.setRequestHeader("osd-version", OS_VERSION);
  xhr.setRequestHeader("accept", "application/json");
  if (body) {
    xhr.setRequestHeader("content-type", "application/json");
    xhr.send(body);
  } else {
    xhr.send();
  }
  return { status: xhr.status, body: xhr.responseText || "" };
}

const r = sxhr(
  "POST",
  "/_dashboards/api/console/proxy?path=" + encodeURIComponent(OS_INDEX + "/_search") + "&method=POST",
  JSON.stringify(esBody)
);
// if r.status is 401/403 or body looks like login HTML → user must SSO login
const parsed = JSON.parse(r.body);
const total = parsed.hits?.total?.value ?? parsed.hits?.total;
const hits = parsed.hits?.hits || [];
if (hits.length < total) {
  return { incomplete: true, total, returned: hits.length }; // caller must re-query larger size
}
const counts = {};
const levels = {};
for (const h of hits) {
  let msg = "(unparsed)";
  let level = "?";
  try {
    const j = JSON.parse(h._source.log);
    msg = j.msg || "(no msg)";
    level = j.level || "?";
  } catch {}
  counts[msg] = (counts[msg] || 0) + 1;
  levels[level] = (levels[level] || 0) + 1;
}
const sumCounts = Object.values(counts).reduce((a, b) => a + b, 0);
const ranked = Object.entries(counts)
  .sort((a, b) => b[1] - a[1])
  .map(([msg, n]) => ({ msg, n }));
return {
  status: r.status,
  total,
  returned: hits.length,
  sumCounts,
  complete: sumCounts === total && hits.length === total,
  levels,
  ranked,
};
```

## kubectl companion (recent only: shared procedure owns this path)

For the last ~15–30m while the pod is up, prefer kubectl (shared procedure §4).
This block is a short reminder, not an OS fallback hierarchy.

```bash
kubectl --context CTX logs -n NS deploy/APP --since=15m --tail=500
kubectl --context CTX logs -n NS deploy/APP --previous --tail=200
```

Then filter with the **grep tool** on the command output/artifact.  
Do **not** pipe to `rg`/`grep` in bash.

## Auxiliary and UAT notes

Core and Auxiliary share the `opensearch.sit` host/index: filter on `cluster_name.keyword` (`OS_CLUSTER`) as well
as the exact live container name (`ingress-controller` exists in both clusters).
If an Auxiliary search has zero hits, verify that name from a live pod before saying “no logs”;
the index held only the Aux namespaces listed in the SIT surface table when last measured (2026-11-05).
Core `transaction` and Auxiliary `consent` passed the count-complete gate on 2026-11-05 (8 and 30
error hits in 24h).
UAT host/index/mapping and SSO must be verified on UAT; the SIT measurement is not UAT evidence.
