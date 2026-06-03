/* ============================================================================
   components.js — <ac-card> custom element (neo-team design-docs)

   Light-DOM "upgrade-in-place": on connect, <ac-card> rewrites ITSELF into the
   canonical .card markup. styles.css and app.js are BOTH class-keyed (.card,
   .card__head, .gwt …) — never tag-keyed — so <ac-card class="card"> is matched
   by both with ZERO changes to either. Authors write a compact <ac-card> + a few
   child tags; all the repeated chrome (status badge, chips, chevron, GWT labels,
   field-rows) is DERIVED here from one source, so it can never drift out of sync.

   LOAD ORDER IS LOAD-BEARING. This MUST be a CLASSIC <script> (NOT type=module)
   and MUST load AFTER nav.js and BEFORE app.js:
       mermaid CDN -> nav.js -> components.js -> app.js
   customElements.define() upgrades already-parsed <ac-card> elements
   SYNCHRONOUSLY during the call, so by the time app.js runs its on-load
   $$(".card") / $$(".filter-bar") scans, every card is already a real .card node.
   A type=module would be DEFERRED and run AFTER app.js — breaking this.

   NOTE: `.card` sets `display:block` in styles.css — REQUIRED, because custom
   elements default to `display:inline`. Without it the inner DOM matches a
   hand-written card but the layout breaks (margins drop, height differs).

   Authoring form (see references/html-output.md / components.html):
     <ac-card id="AC-001" status="ready" priority="p0" traces="TC-001 TC-002"
              subop="1" jira="GI-90" label="happy path">
       <g>…given…</g><w>…when…</w><t>HTTP <b>200</b></t>
       <rule>BR-01 — …</rule>
       <blocker>…only for blocked ACs…</blocker>   <!-- optional -->
     </ac-card>
   ========================================================================== */
(function () {
  "use strict";

  // Local escaper — app.js's esc()/escapeHtml() are function-scoped, not reachable here.
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c];
    });
  }
  function cap(s) { s = String(s || ""); return s ? s.charAt(0).toUpperCase() + s.slice(1) : ""; }
  function fieldRow(label, htmlValue) {
    return '<dl class="field-row"><dt>' + label + '</dt><dd>' + htmlValue + '</dd></dl>';
  }
  // A single JSON code block. app.js adds the copy bar + JSON highlight on load
  // (it reads pre.textContent, which decodes our esc() back to raw JSON).
  function codeBlock(title, json) {
    return '<div class="code" data-lang="json" data-title="' + esc(title) + '">'
         + '<pre><code>' + esc(json) + '</code></pre></div>';
  }
  // The canonical status pill. Identical to what the standalone <status-badge>
  // derives; shared so ac-card / tc-card / trace-matrix can't diverge from it.
  function statusBadge(status) {
    return '<span class="status-badge" data-status="' + esc(status) + '">' + cap(status) + '</span>';
  }
  // Count the page's <ac-card>/<tc-card> by status — for the drift-proof totals lines.
  function cardCounts(tag) {
    var cards = document.querySelectorAll(tag), n = cards.length, ready = 0, blocked = 0;
    for (var i = 0; i < n; i++) {
      var s = cards[i].getAttribute("status");
      if (s === "ready") ready++; else if (s === "blocked") blocked++;
    }
    return { n: n, ready: ready, blocked: blocked };
  }

  // authored prose child tag -> [data-k value, visible label]
  var GWT = { g: ["given", "Given"], w: ["when", "When"], t: ["then", "Then"], a: ["and", "And"] };

  // Build the .gwt block from <g>/<w>/<t>/<a> children in document order.
  // Uses each child's innerHTML verbatim so inline markup (e.g. <b>200</b>) survives.
  function buildGwt(host) {
    var rows = "", kids = host.children;
    for (var i = 0; i < kids.length; i++) {
      var tag = kids[i].tagName.toLowerCase();
      if (Object.prototype.hasOwnProperty.call(GWT, tag)) {
        var k = GWT[tag];
        rows += '<span class="gwt__k" data-k="' + k[0] + '">' + k[1] + '</span>'
              + '<div class="gwt__v">' + kids[i].innerHTML + '</div>';
      }
    }
    return rows ? '<div class="gwt">' + rows + '</div>' : "";
  }

  // Priority chip: p0/p1 carry data-tone; anything else (e.g. p2) is a plain chip
  // (per html-output.md §5: only p0/p1/jira tones exist). No priority -> no chip.
  function priorityChip(priority) {
    if (!priority) return "";
    var p = priority.toLowerCase();
    var tone = (p === "p0" || p === "p1") ? ' data-tone="' + p + '"' : "";
    return '<span class="chip"' + tone + '>' + esc(priority.toUpperCase()) + '</span>';
  }

  // <callout> kind -> default icon glyph. CSS keys color/bg off data-kind; the
  // icon is hand-typed today (drift risk) — deriving it here makes kind the single source.
  var CALLOUT_ICONS = { note: "ℹ️", success: "✅", warning: "⚠️", pending: "⏳", blocked: "⛔" };

  if (!customElements.get("ac-card")) {
    customElements.define("ac-card", class extends HTMLElement {
      connectedCallback() {
        if (this.__up) return;        // one-shot: innerHTML is rewritten; never re-process
        this.__up = true;

        var id       = this.getAttribute("id")       || "";
        var status   = this.getAttribute("status")   || "";
        var priority = this.getAttribute("priority") || "";
        var traces   = this.getAttribute("traces")   || "";
        var subop    = this.getAttribute("subop")    || "";
        var jira     = this.getAttribute("jira")      || "";
        var label    = this.getAttribute("label")    || "";

        // capture authored child prose BEFORE overwriting innerHTML
        var gwt = buildGwt(this);
        var ruleEl    = this.querySelector("rule");
        var blockerEl = this.querySelector("blocker");
        var rule    = ruleEl    ? ruleEl.innerHTML    : "";
        var blocker = blockerEl ? blockerEl.innerHTML : "";

        // upgrade self into the canonical .card host (class-keyed -> CSS + app.js match it)
        this.classList.add("card");
        if (status)   this.classList.add("is-" + status);   // is-pending is intentionally style-inert
        if (status)   this.setAttribute("data-status", status);
        if (priority) this.setAttribute("data-priority", priority);
        if (traces)   this.setAttribute("data-traces", traces);
        if (subop)    this.setAttribute("data-subop", subop);
        if (jira)     this.setAttribute("data-jira", jira);

        var badge = statusBadge(status);
        var jiraChip = jira ? '<span class="chip" data-tone="jira">' + esc(jira) + '</span>' : "";

        // body: GWT -> Business Rule -> JIRA Ref -> Priority/Status -> Blocker callout
        var body = gwt;
        if (rule) body += fieldRow("Business Rule", rule);
        if (jira) body += fieldRow("JIRA Ref", esc(jira));
        var prio = priority ? esc(priority.toUpperCase()) + ' · ' : "";
        body += fieldRow("Priority / Status", prio + badge);
        if (blocker) {
          body += '<div class="callout" data-kind="blocked"><span class="callout__ico">⛔</span>'
                + '<div class="callout__body">' + blocker + '</div></div>';
        }

        this.innerHTML =
          '<div class="card__head">'
            + '<span class="card__id">' + esc(id) + '</span>'
            + '<span class="card__title">' + esc(label) + '</span>'
            + '<span class="card__meta">' + badge + priorityChip(priority) + jiraChip
              + '<span class="card__chev">▸</span></span>'
          + '</div>'
          + '<div class="card__body">' + body + '</div>';
      }
    });
  }

  /* --------------------------------------------------------------------------
     <tc-card> — Test Case card. Same Light-DOM upgrade-in-place pattern as
     <ac-card>, reusing esc/cap/fieldRow/codeBlock/buildGwt/priorityChip/GWT.
     Richer body than AC: Endpoint, Request/Response JSON (.tabs when BOTH,
     a single .code when one), a Test Steps <ol>, Expected/Test-Data/
     Precondition/Traces-To/JIRA-Ref field-rows, and — blocked only — an
     "AC Status" row + a blocker callout (AC Status + data-tags derived from
     status, so the @blocked filter can't drift from the badge).

     Authoring form:
       <tc-card id="TC-002" status="ready" priority="p1" traces="AC-002"
                jira="PROJ-123, PROJ-456" endpoint="POST /v1/accounts"
                label="open account">
         <g>…</g><a>…and…</a><w>…</w><t>HTTP <b>200</b></t>   <!-- G-A-W-T order -->
         <req>{ …request json… }</req>
         <res>HTTP 200
{ …response json… }</res>
         <steps><step>call <code>POST /v1/accounts</code></step><step>assert 200</step></steps>
         <expected>HTTP 200, status = OPEN</expected>
         <tdata><code>denomination: "THB"</code></tdata>
         <precond>TC-001 must pass</precond>
         <blocker>…only for blocked TCs…</blocker>   <!-- optional -->
       </tc-card>
     ------------------------------------------------------------------------ */
  if (!customElements.get("tc-card")) {
    customElements.define("tc-card", class extends HTMLElement {
      connectedCallback() {
        if (this.__up) return;        // one-shot: innerHTML is rewritten; never re-process
        this.__up = true;

        var id       = this.getAttribute("id")       || "";
        var status   = this.getAttribute("status")   || "";
        var priority = this.getAttribute("priority") || "";
        var traces   = this.getAttribute("traces")   || "";
        var jira     = this.getAttribute("jira")      || "";
        var endpoint = this.getAttribute("endpoint")  || "";
        var label    = this.getAttribute("label")    || "";
        var tags     = this.getAttribute("tags")      || "";

        // capture authored children BEFORE overwriting innerHTML.
        // GWT (<g>/<a>/<w>/<t>) → buildGwt reads direct children in document order.
        var gwt = buildGwt(this);
        var reqEl     = this.querySelector("req");
        var resEl     = this.querySelector("res");
        var stepEls   = this.querySelectorAll("steps > step");
        var expectedEl = this.querySelector("expected");
        var tdataEl    = this.querySelector("tdata");
        var precondEl  = this.querySelector("precond");
        var blockerEl  = this.querySelector("blocker");
        // JSON: textContent (raw text, entities decoded) → esc()'d into <pre><code>.
        var reqJson = reqEl ? reqEl.textContent : "";
        var resJson = resEl ? resEl.textContent : "";
        // prose children keep innerHTML so inline <b>/<code> survive.
        var steps = "";
        for (var i = 0; i < stepEls.length; i++) steps += "<li>" + stepEls[i].innerHTML + "</li>";
        var expected = expectedEl ? expectedEl.innerHTML : "";
        var tdata    = tdataEl    ? tdataEl.innerHTML    : "";
        var precond  = precondEl  ? precondEl.innerHTML  : "";
        var blocker  = blockerEl  ? blockerEl.innerHTML  : "";

        // blocked TCs always carry the @blocked filter tag (single source → can't drift)
        var dataTags = tags;
        if (status === "blocked" && !/\bblocked\b/.test(dataTags)) {
          dataTags = (dataTags ? dataTags + " " : "") + "blocked";
        }

        // upgrade self into the canonical .card host (class-keyed → CSS + app.js match it)
        this.classList.add("card");
        if (status)   this.classList.add("is-" + status);
        if (status)   this.setAttribute("data-status", status);
        if (priority) this.setAttribute("data-priority", priority);
        if (traces)   this.setAttribute("data-traces", traces);
        if (jira)     this.setAttribute("data-jira", jira);
        if (dataTags) this.setAttribute("data-tags", dataTags);

        var badge = statusBadge(status);
        var jiraChip = jira ? '<span class="chip" data-tone="jira">' + esc(jira) + '</span>' : "";

        // body: GWT → Endpoint → Request/Response → Test Steps → Expected →
        //       Test Data → Precondition → Traces To → JIRA Ref → AC Status → Blocker
        var body = gwt;
        if (endpoint) body += fieldRow("Endpoint", '<code>' + esc(endpoint) + '</code>');
        if (reqEl && resEl) {
          body += '<div class="tabs"><div class="tabs__nav">'
                + '<button class="tab active" data-tab="req">Request</button>'
                + '<button class="tab" data-tab="res">Response</button></div>'
                + '<div class="tab-panel active" data-tab="req">' + codeBlock("Request", reqJson) + '</div>'
                + '<div class="tab-panel" data-tab="res">' + codeBlock("Response", resJson) + '</div>'
                + '</div>';
        } else if (reqEl) {
          body += codeBlock("Request", reqJson);
        } else if (resEl) {
          body += codeBlock("Response", resJson);
        }
        if (steps)    body += fieldRow("Test Steps", '<ol>' + steps + '</ol>');
        if (expected) body += fieldRow("Expected Result", expected);
        if (tdata)    body += fieldRow("Test Data", tdata);
        if (precond)  body += fieldRow("Precondition", precond);
        if (traces)   body += fieldRow("Traces To", esc(traces));
        if (jira)     body += fieldRow("JIRA Ref", esc(jira));
        if (status === "blocked") {
          body += fieldRow("AC Status", statusBadge("blocked"));
        }
        if (blocker) {
          body += '<div class="callout" data-kind="blocked"><span class="callout__ico">⛔</span>'
                + '<div class="callout__body">' + blocker + '</div></div>';
        }

        this.innerHTML =
          '<div class="card__head">'
            + '<span class="card__id">' + esc(id) + '</span>'
            + '<span class="card__title">' + esc(label) + '</span>'
            + '<span class="card__meta">' + badge + priorityChip(priority) + jiraChip
              + '<span class="card__chev">▸</span></span>'
          + '</div>'
          + '<div class="card__body">' + body + '</div>';
      }
    });
  }

  /* --------------------------------------------------------------------------
     <callout> — hand-authored callout. Derives the icon glyph from `kind` (one
     source: kind drives BOTH the CSS color/bg via data-kind AND the icon), so
     the glyph can't drift from the kind. Optional `ico=` overrides the glyph.
     Cards emit their own blocked-callout markup directly; this element is for
     HAND-authored callouts (notes, ADRs, warnings, …).

       <callout-box kind="warning">draft: <b>not</b> finalized</callout-box>
       <callout-box kind="note" ico="🎯">custom-icon note</callout-box>
     (name needs a hyphen — HTML custom-element rule; the CSS class stays .callout)
     ------------------------------------------------------------------------ */
  if (!customElements.get("callout-box")) {
    customElements.define("callout-box", class extends HTMLElement {
      connectedCallback() {
        if (this.__up) return;
        this.__up = true;
        var kind = this.getAttribute("kind") || "note";
        var ico  = this.getAttribute("ico");
        if (ico == null) ico = CALLOUT_ICONS[kind] || "";
        var content = this.innerHTML;     // authored prose, kept verbatim
        this.classList.add("callout");
        this.setAttribute("data-kind", kind);
        this.innerHTML = (ico ? '<span class="callout__ico">' + esc(ico) + '</span>' : "")
                       + '<div class="callout__body">' + content + '</div>';
      }
    });
  }

  /* --------------------------------------------------------------------------
     <card-flow> — gate / validation chain (pure-CSS .flow; app.js never touches it).
     Derives the per-step NUMBER (auto-increment) and the ARROW between steps, so
     neither can drift / be missed. Each <step> is a plain data holder (shared with
     <tc-card>; not a custom element).

       <card-flow>
         <step status="ready" href="#a" tag="ERR_CODE" detail="sub text">title <b>1</b></step>
         <step status="blocked" href="#b">title 2</step>
       </card-flow>
     ------------------------------------------------------------------------ */
  if (!customElements.get("card-flow")) {
    customElements.define("card-flow", class extends HTMLElement {
      connectedCallback() {
        if (this.__up) return;
        this.__up = true;
        var steps = [], kids = this.children;
        for (var i = 0; i < kids.length; i++) {
          if (kids[i].tagName.toLowerCase() === "step") steps.push(kids[i]);
        }
        var html = "";
        for (var j = 0; j < steps.length; j++) {
          var s = steps[j];
          var status = s.getAttribute("status") || "";
          var href   = s.getAttribute("href");          // null if absent
          var tag    = s.getAttribute("tag")    || "";
          var detail = s.getAttribute("detail") || "";
          var title  = s.innerHTML;                      // prose, kept verbatim
          html += '<a class="flow__step' + (status ? " is-" + status : "") + '"'
                + (href != null ? ' href="' + esc(href) + '"' : "") + '>'
                + '<span class="flow__num">' + (j + 1) + '</span>'
                + '<div class="flow__main"><div class="flow__t">' + title + '</div>'
                + (detail ? '<div class="flow__d">' + esc(detail) + '</div>' : "")
                + '</div>'
                + (tag ? '<span class="code-tag">' + esc(tag) + '</span>' : "")
                + '</a>';
          if (j < steps.length - 1) html += '<div class="flow__arrow"></div>';
        }
        this.classList.add("flow");
        this.innerHTML = html;
      }
    });
  }

  /* --------------------------------------------------------------------------
     <status-badge> — status pill. Derives the visible label from `status`
     (capitalized) so it can't drift from data-status; non-empty content
     OVERRIDES the label (e.g. show "Deferred" with blocked styling). The colored
     dot is a CSS ::before. For HAND-authored badges (summary tables / trace
     matrices); cards emit their own .status-badge span.

       <status-badge status="ready"></status-badge>           -> "Ready"
       <status-badge status="blocked">Deferred</status-badge> -> "Deferred"
     ------------------------------------------------------------------------ */
  if (!customElements.get("status-badge")) {
    customElements.define("status-badge", class extends HTMLElement {
      connectedCallback() {
        if (this.__up) return;
        this.__up = true;
        var status = this.getAttribute("status") || "";
        var label = this.textContent.trim() || cap(status);
        this.classList.add("status-badge");
        if (status) this.setAttribute("data-status", status);
        this.textContent = label;
      }
    });
  }

  /* --------------------------------------------------------------------------
     <trace-matrix> — Phase B "derive-from-siblings": builds the WHOLE AC↔TC
     traceability table from the page's <ac-card>s. Author writes one empty tag
     <trace-matrix></trace-matrix>; every row (AC id), its TC chips, and the
     status badge are READ from each card's id/traces/status — so the matrix can
     never drift from the cards. Reads attributes only (present from initial
     parse), so upgrade order is irrelevant; defined LAST so all <ac-card>s are
     already in the DOM. app.js §10 wires the row-click highlight on load.

       <trace-matrix></trace-matrix>
     (host becomes .matrix-wrap — which needs display:block in styles.css, like
      .card — wrapping an inner <table class="trace-matrix">)
     ------------------------------------------------------------------------ */
  if (!customElements.get("trace-matrix")) {
    customElements.define("trace-matrix", class extends HTMLElement {
      connectedCallback() {
        if (this.__up) return;
        this.__up = true;
        var cards = document.querySelectorAll("ac-card");
        var rows = "";
        for (var i = 0; i < cards.length; i++) {
          var c = cards[i];
          var id     = c.getAttribute("id")     || "";
          var status = c.getAttribute("status") || "";
          var traces = c.getAttribute("traces") || "";
          var tcs = traces.split(/\s+/).filter(Boolean);
          var chips = "";
          for (var j = 0; j < tcs.length; j++) chips += '<span class="chip">' + esc(tcs[j]) + '</span>';
          if (!chips) chips = "—";
          rows += '<tr><th>' + esc(id) + '</th><td>' + chips + '</td><td>' + statusBadge(status) + '</td></tr>';
        }
        this.classList.add("matrix-wrap");
        this.innerHTML = '<table class="trace-matrix">'
                       + '<thead><tr><th>AC</th><th>Tests</th><th>Status</th></tr></thead>'
                       + '<tbody>' + rows + '</tbody></table>';
      }
    });
  }

  /* --------------------------------------------------------------------------
     <ac-summary> — Phase B derive-with-authored-gaps: the AC Summary table.
     5 of 7 columns DUPLICATE <ac-card> data (id/label/priority/status/jira) and
     are DERIVED here from the matching card (so they can't drift); the 2 gaps
     that live ONLY in the table — Sub-operation NAME + Business-Rule short-ref —
     are authored per row on an <ac> child, keyed by `ref` to its <ac-card>.

       <ac-summary>
         <ac ref="AC-001" subop="Create account" rule="BR-01 unique name"></ac>
         <ac ref="AC-002" rule="BR-02 valid denomination" blocker="GI-90"></ac>
       </ac-summary>

     `ref` (NOT id) avoids a duplicate id with the <ac-card id="…"> on the page.
     subop omitted -> "—"; blocker -> " (blocked by …)" appended to the rule cell.
     Per acceptance-criteria.md: Status -> badge, Priority/JIRA -> chip; rest plain.
     Reads card ATTRIBUTES only, so upgrade order is irrelevant. Emits
     .table-wrap > table.data-table[data-sortable]; app.js §9 wires sort on load.
     (host becomes .table-wrap — which needs display:block in styles.css, like .card.)
     ------------------------------------------------------------------------ */
  if (!customElements.get("ac-summary")) {
    customElements.define("ac-summary", class extends HTMLElement {
      connectedCallback() {
        if (this.__up) return;
        this.__up = true;
        var kids = this.children, rows = "";
        for (var i = 0; i < kids.length; i++) {
          if (kids[i].tagName.toLowerCase() !== "ac") continue;
          var r = kids[i];
          var ref     = r.getAttribute("ref")     || "";
          var subop   = r.getAttribute("subop")   || "";
          var rule    = r.getAttribute("rule")    || "";
          var blocker = r.getAttribute("blocker") || "";
          var card = ref ? document.querySelector('ac-card[id="' + ref + '"]') : null;
          var scenario = card ? (card.getAttribute("label")    || "") : "";
          var priority = card ? (card.getAttribute("priority") || "") : "";
          var status   = card ? (card.getAttribute("status")   || "") : "";
          var jira     = card ? (card.getAttribute("jira")     || "") : "";
          var ruleCell = esc(rule) + (blocker ? " (blocked by " + esc(blocker) + ")" : "");
          rows += '<tr>'
                + '<td>' + esc(ref) + '</td>'
                + '<td>' + (subop ? esc(subop) : "—") + '</td>'
                + '<td>' + esc(scenario) + '</td>'
                + '<td>' + (priorityChip(priority) || "—") + '</td>'
                + '<td>' + statusBadge(status) + '</td>'
                + '<td>' + (jira ? '<span class="chip" data-tone="jira">' + esc(jira) + '</span>' : "—") + '</td>'
                + '<td>' + ruleCell + '</td>'
                + '</tr>';
        }
        this.classList.add("table-wrap");
        this.innerHTML = '<table class="data-table" data-sortable>'
                       + '<thead><tr><th>ID</th><th>Sub-operation</th><th>Scenario</th>'
                       + '<th>Priority</th><th>Status</th><th>JIRA Ref</th><th>Business Rule</th></tr></thead>'
                       + '<tbody>' + rows + '</tbody></table>';
      }
    });
  }

  /* --------------------------------------------------------------------------
     <tc-summary> — the Test Case Summary table (TC counterpart of <ac-summary>).
     Description/Traces/JIRA/Status are DERIVED from the matching <tc-card> (can't
     drift); Suite + Precondition live ONLY in the table → authored per <tc> row,
     keyed by `ref`. Description = the card's `label`. subop-less defaults: suite
     omitted -> "—", precond omitted -> "None" (per test-case-document.md).

       <tc-summary>
         <tc ref="TC-001" suite="Product Configuration" precond="None"></tc>
       </tc-summary>
     ------------------------------------------------------------------------ */
  if (!customElements.get("tc-summary")) {
    customElements.define("tc-summary", class extends HTMLElement {
      connectedCallback() {
        if (this.__up) return;
        this.__up = true;
        var kids = this.children, rows = "";
        for (var i = 0; i < kids.length; i++) {
          if (kids[i].tagName.toLowerCase() !== "tc") continue;
          var r = kids[i];
          var ref     = r.getAttribute("ref")     || "";
          var suite   = r.getAttribute("suite")   || "";
          var precond = r.getAttribute("precond") || "";
          var card = ref ? document.querySelector('tc-card[id="' + ref + '"]') : null;
          var desc   = card ? (card.getAttribute("label")  || "") : "";
          var traces = card ? (card.getAttribute("traces") || "") : "";
          var jira   = card ? (card.getAttribute("jira")   || "") : "";
          var status = card ? (card.getAttribute("status") || "") : "";
          rows += '<tr>'
                + '<td>' + esc(ref) + '</td>'
                + '<td>' + (suite ? esc(suite) : "—") + '</td>'
                + '<td>' + esc(desc) + '</td>'
                + '<td>' + (precond ? esc(precond) : "None") + '</td>'
                + '<td>' + esc(traces) + '</td>'
                + '<td>' + (jira ? '<span class="chip" data-tone="jira">' + esc(jira) + '</span>' : "—") + '</td>'
                + '<td>' + statusBadge(status) + '</td>'
                + '</tr>';
        }
        this.classList.add("table-wrap");
        this.innerHTML = '<table class="data-table" data-sortable>'
                       + '<thead><tr><th>ID</th><th>Suite</th><th>Description</th>'
                       + '<th>Precondition</th><th>Traces To</th><th>JIRA Ref</th><th>Status</th></tr></thead>'
                       + '<tbody>' + rows + '</tbody></table>';
      }
    });
  }

  /* --------------------------------------------------------------------------
     <tc-deferred> — the Deferred Test Cases table (blocked TCs only). TC-ID/
     Traces/JIRA are DERIVED from the matching <tc-card>; Blocker reason + Upstream
     ref are authored per <tc> row (the author lists only the blocked TCs). Shares
     the <tc> holder tag with <tc-summary> (each parent reads its own <tc> kids,
     different attrs). Empty <tc-deferred></tc-deferred> → header-only ("no deferrals").

       <tc-deferred>
         <tc ref="TC-005" blocker="error code not finalized" upstream="FX-104"></tc>
       </tc-deferred>
     ------------------------------------------------------------------------ */
  if (!customElements.get("tc-deferred")) {
    customElements.define("tc-deferred", class extends HTMLElement {
      connectedCallback() {
        if (this.__up) return;
        this.__up = true;
        var kids = this.children, rows = "";
        for (var i = 0; i < kids.length; i++) {
          if (kids[i].tagName.toLowerCase() !== "tc") continue;
          var r = kids[i];
          var ref      = r.getAttribute("ref")      || "";
          var blocker  = r.getAttribute("blocker")  || "";
          var upstream = r.getAttribute("upstream") || "";
          var card = ref ? document.querySelector('tc-card[id="' + ref + '"]') : null;
          var traces = card ? (card.getAttribute("traces") || "") : "";
          var jira   = card ? (card.getAttribute("jira")   || "") : "";
          rows += '<tr>'
                + '<td>' + esc(ref) + '</td>'
                + '<td>' + esc(traces) + '</td>'
                + '<td>' + (jira ? '<span class="chip" data-tone="jira">' + esc(jira) + '</span>' : "—") + '</td>'
                + '<td>' + esc(blocker) + '</td>'
                + '<td>' + esc(upstream) + '</td>'
                + '</tr>';
        }
        this.classList.add("table-wrap");
        this.innerHTML = '<table class="data-table" data-sortable>'
                       + '<thead><tr><th>TC-ID</th><th>Traces To</th><th>JIRA Ref</th>'
                       + '<th>Blocker</th><th>Upstream Reference</th></tr></thead>'
                       + '<tbody>' + rows + '</tbody></table>';
      }
    });
  }

  /* --------------------------------------------------------------------------
     <ac-total> / <tc-total> — the summary "Total …" line, COUNTED from the page's
     <ac-card>/<tc-card> (zero-config, like <trace-matrix>). The N/Ready/Blocked
     counts are derived, so they can't go stale when a card is added or re-statused.
     Reads the status attribute only → timing-irrelevant. Host renders as a block
     line via .doc-total (custom els default to inline).

       <ac-total></ac-total>  →  Total Acceptance Criteria: 5 (Ready: 4 / Blocked: 1)
       <tc-total></tc-total>  →  Total Test Cases: 5 (Ready: 4 / Blocked (Deferred): 1)
     ------------------------------------------------------------------------ */
  if (!customElements.get("ac-total")) {
    customElements.define("ac-total", class extends HTMLElement {
      connectedCallback() {
        if (this.__up) return;
        this.__up = true;
        var c = cardCounts("ac-card");
        this.classList.add("doc-total");
        this.innerHTML = '<b>Total Acceptance Criteria:</b> ' + c.n
                       + ' (Ready: ' + c.ready + ' / Blocked: ' + c.blocked + ')';
      }
    });
  }
  if (!customElements.get("tc-total")) {
    customElements.define("tc-total", class extends HTMLElement {
      connectedCallback() {
        if (this.__up) return;
        this.__up = true;
        var c = cardCounts("tc-card");
        this.classList.add("doc-total");
        this.innerHTML = '<b>Total Test Cases:</b> ' + c.n
                       + ' (Ready: ' + c.ready + ' / Blocked (Deferred): ' + c.blocked + ')';
      }
    });
  }
})();
