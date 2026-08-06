# OpenSearch SIT — historical logs (measured)

Shared SIT log store for Core + Aux containers. Use when **kubectl is not enough**
(window older than the live pod, multi-pod history, count/group by `msg`).
Parent skills (`neo-core-sit` / `neo-aux-sit`) own the path choice — this file is only the OS recipe.

## When to use

| Need | Path |
|---|---|
| Last ~15–30m, deploy/pod still up | **kubectl first** (`--since=15m`) — parent skill section A |
| Older window / pod rotated / aggregate by `msg` / multi-pod history | **This recipe** |

## Verified surface (2026-08-06)

| | |
|---|---|
| Host | `https://opensearch.sit.awesome-poc-th.com` |
| Dashboards | `3.5.0` |
| Index / pattern title | `console-sit-log` |
| Index-pattern id | `0118f120-7391-11f1-b139-918a526f3084` |
| Time field | `@timestamp` |
| Container field | `kubernetes_container_name` (phrase match; e.g. `payment`) |
| Auth | Browser SSO session cookies (**httpOnly** — not in `document.cookie`) |

### Working search endpoint

```
POST /_dashboards/api/console/proxy?path=console-sit-log%2F_search&method=POST
```

Required headers:

- `osd-xsrf: true`
- `osd-version: 3.5.0`
- `content-type: application/json`
- `accept: application/json`

Also works (same session):

- `POST /_dashboards/internal/search/opensearch` with body wrapped as `{ "params": { "index": "console-sit-log*", "body": { …ES DSL… } } }`

Status check: `GET /_dashboards/api/status` → version number `3.5.0`.

## Hard constraints (measured failures)

1. **Sync XHR only inside the browser tab.**  
   `tab.evaluate(() => fetch(…))` returns a Promise this harness cannot await  
   (“tab.evaluate() returned a Promise…”). Use **synchronous** `XMLHttpRequest`  
   (`xhr.open(method, url, false)`).

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

1. Open (or reuse) browser tab on  
   `https://opensearch.sit.awesome-poc-th.com/_dashboards/app/home`  
   (Discover URL optional).
2. Wait for app shell. If login/SSO → ask user to authenticate → wait for home/Discover.
3. Run **sync XHR** search via `tab.evaluate` (plain return value, no async/fetch).
4. **Count-complete tally (required before stating totals):**
   - Read `total = hits.total.value` (with `track_total_hits: true`).
   - If `hits.hits.length < total`, re-query with `size >= total` (cap reasonably, e.g. 1000; page with `search_after` only if over cap).
   - For each hit: `JSON.parse(_source.log)` → `msg` / `level` (fallback: raw slice if parse fails).
   - Build `counts[msg]++` and `levels[level]++` over **all returned hits**.
   - **Gate:** `sum(counts) === total` and `returned === total`. If not equal, do not publish the table as “full” — raise `size` or mark as partial top-N.
   - Sort `counts` desc for the report. (Measured: payment error/warn 24h → 78 hits, client tally summed to 78 after `size: 200` ≥ 78. A prior `size: 50` tally summed to 50 and was wrongly presented as full — do not repeat.)
5. Report in Thai: total hits, **full** counts by `msg` (only if gate passed), level split, a few timestamped examples, pod name if present.

## Body: logs for one container (copy-paste)

Replace `CONTAINER` (e.g. `payment`) and time range as needed.  
The `should` block below keeps **error+warn**; drop it (or swap needles) for info/all-level or free-text hunts — always keep container + time `filter`.

```json
{
  "size": 200,
  "track_total_hits": true,
  "sort": [{ "@timestamp": { "order": "desc", "unmapped_type": "boolean" } }],
  "query": {
    "bool": {
      "filter": [
        { "match_phrase": { "kubernetes_container_name": "CONTAINER" } },
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
- **No dedicated `level` / `service` / `msg` fields** — do **not** query `level:error` as an ES field. Filter with `match_phrase` on `log` for `"\"level\":\"error\""` / `"\"level\":\"warn\""` (body above).
- There is **no reliable ES `terms` agg on `msg`** here — `msg` lives inside the string. Client-side parse + count is the measured path.
- Some older backing indices lack `@timestamp` mapping → shard failures in response are OK if `hits.total` and current indices still return data. Prefer `unmapped_type: "boolean"` on the sort as above.
- **`size` is not optional decoration.** Counts built from `hits.hits` only cover `min(size, total)`. Always gate with `sum(counts) === hits.total.value` before calling a table complete.
- For a free-text needle, add  
  `{ "match_phrase": { "log": "YOUR TEXT" } }`  
  to `filter` or `should`.

## Minimal sync-XHR evaluate sketch (count-complete)

```js
// inside tab.evaluate — MUST be sync; return a plain object
function sxhr(method, url, body) {
  const xhr = new XMLHttpRequest();
  xhr.open(method, url, false);
  xhr.setRequestHeader("osd-xsrf", "true");
  xhr.setRequestHeader("osd-version", "3.5.0");
  xhr.setRequestHeader("accept", "application/json");
  if (body) {
    xhr.setRequestHeader("content-type", "application/json");
    xhr.send(body);
  } else {
    xhr.send();
  }
  return { status: xhr.status, body: xhr.responseText || "" };
}

const esBody = {
  size: 200, // bump if total > size
  track_total_hits: true,
  sort: [{ "@timestamp": { order: "desc", unmapped_type: "boolean" } }],
  query: { /* same bool query as JSON body above */ },
  _source: ["log", "@timestamp", "kubernetes_pod_name"],
};

const r = sxhr(
  "POST",
  "/_dashboards/api/console/proxy?path=console-sit-log%2F_search&method=POST",
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

## kubectl companion (recent only — parent skill owns this path)

For the last ~15–30m while the pod is up, prefer kubectl (parent skill section A).  
This block is a short reminder, not an OS fallback hierarchy.

```bash
kubectl --context CTX logs -n NS deploy/APP --since=15m --tail=500
kubectl --context CTX logs -n NS deploy/APP --previous --tail=200
```

Then filter with the **grep tool** on the command output/artifact.  
Do **not** pipe to `rg`/`grep` in bash.

## Aux note

Same host + index for SIT. Filter `kubernetes_container_name` to the Aux
container/deploy name. Core `payment` path was exercised end-to-end; Aux
container names on this index are expected to work the same but were not
separately smoke-tested in the session that wrote this file.
