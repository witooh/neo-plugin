/* ============================================================================
   Design Docs — shared, project-agnostic site script (bundled by neo)
   app.js — vanilla JS, progressive enhancement, offline-safe.
   Every feature is guarded by element presence so this one file serves all pages.
   ========================================================================== */
(function () {
  "use strict";
  var $  = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var root = document.documentElement;

  /* -------------------------------------------------------------------------
     1. Theme (localStorage + system fallback) — also drives mermaid theme
     ----------------------------------------------------------------------- */
  var THEME_KEY = "ds-theme";
  function currentTheme() { return root.getAttribute("data-theme") || "light"; }
  function applyTheme(t) {
    root.setAttribute("data-theme", t);
    try { localStorage.setItem(THEME_KEY, t); } catch (e) {}
    $$(".js-theme-label").forEach(function (el) { el.textContent = t === "dark" ? "Light" : "Dark"; });
    $$(".js-theme-ico").forEach(function (el) { el.textContent = t === "dark" ? "☀" : "☾"; });
  }
  (function initTheme() {
    var saved = null;
    try { saved = localStorage.getItem(THEME_KEY); } catch (e) {}
    if (!saved) {
      saved = (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
    }
    applyTheme(saved);
  })();
  function toggleTheme() { applyTheme(currentTheme() === "dark" ? "light" : "dark"); drawMermaid(); }
  document.addEventListener("click", function (e) {
    if (e.target.closest(".js-theme-toggle")) { e.preventDefault(); toggleTheme(); }
  });

  /* -------------------------------------------------------------------------
     2. Mermaid (offline) — store raw source so we can re-theme on toggle
     ----------------------------------------------------------------------- */
  var diagrams = $$(".mermaid");
  diagrams.forEach(function (d) { if (!d.dataset.src) d.dataset.src = d.textContent.trim(); });
  function mermaidTheme() { return currentTheme() === "dark" ? "dark" : "default"; }
  var drawMermaid = function () {
    if (!window.mermaid || !diagrams.length) return;
    try {
      window.mermaid.initialize({
        startOnLoad: false,
        theme: mermaidTheme(),
        securityLevel: "loose",
        fontFamily: getComputedStyle(document.body).getPropertyValue("--font") || "sans-serif",
        flowchart: { curve: "basis", useMaxWidth: true, htmlLabels: true },
        sequence: { useMaxWidth: true, mirrorActors: false }
      });
      diagrams.forEach(function (d) { d.removeAttribute("data-processed"); d.innerHTML = d.dataset.src; });
      var p = window.mermaid.run({ nodes: diagrams });
      if (p && p.catch) p.catch(function (err) { console.warn("[mermaid] render issue:", err && err.message); });
    } catch (err) { console.warn("[mermaid] init issue:", err && err.message); }
  };
  if (document.readyState !== "loading") drawMermaid();
  else document.addEventListener("DOMContentLoaded", drawMermaid);

  /* -------------------------------------------------------------------------
     3. Sidebar: render from window.DOCS_NAV (B2) → mark active link → mobile drawer
        renderNav builds the grouped sidebar from a per-project nav.js so pages
        don't hardcode it. Idempotent: skips if the sidebar is already populated
        (hardcoded B1 fallback) or if no DOCS_NAV is present. Runs BEFORE navActive.
     ----------------------------------------------------------------------- */
  (function renderNav() {
    var aside = $(".sidebar");
    if (!aside || !window.DOCS_NAV) return;          // no sidebar / no nav data → leave as-is
    if (aside.querySelector(".nav-group")) return;   // already populated (B1 fallback) → idempotent
    var prefix = root.getAttribute("data-asset-prefix") || "";
    var brand = window.DOCS_BRAND || {};
    function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
    var html = '<div class="brand"><div class="brand__mark">' + esc(brand.mark || "DS") + "</div>"
      + '<div><div class="brand__title">' + esc(brand.title || "Design Docs") + "</div>"
      + '<div class="brand__sub">' + esc(brand.sub || "") + "</div></div></div>";
    window.DOCS_NAV.forEach(function (grp) {
      html += '<nav class="nav-group"><div class="nav-group__title">' + esc(grp.group || "") + "</div>";
      (grp.links || []).forEach(function (lnk) {
        html += '<a class="nav-link" href="' + esc(prefix + (lnk.href || "")) + '">'
          + '<span class="nav-link__ico">' + esc(lnk.ico || "•") + "</span> " + esc(lnk.label || "") + "</a>";
      });
      html += "</nav>";
    });
    html += '<div class="sidebar__foot"><span class="brand__sub">design docs</span>'
      + '<button class="theme-toggle js-theme-toggle"><span class="js-theme-ico">☾</span> <span class="js-theme-label">Dark</span></button></div>';
    aside.innerHTML = html;
    applyTheme(currentTheme()); // re-sync the freshly-rendered theme button label/icon
  })();
  (function navActive() {
    var path = location.pathname.split("#")[0].split("?")[0];
    function norm(h){ return h.split("#")[0].split("?")[0].replace(/^(\.\.\/)+/, "").replace(/\/$/, ""); }
    var best = null, bestLen = -1;
    $$(".nav-link").forEach(function (a) {
      var href = norm(a.getAttribute("href") || "");
      if (href && (path === href || path.endsWith("/" + href))) {
        var len = href.split("/").length;
        if (len > bestLen) { bestLen = len; best = a; }
      }
    });
    if (best) best.classList.add("active");
  })();
  document.addEventListener("click", function (e) {
    if (e.target.closest(".js-nav-toggle")) { document.body.classList.toggle("nav-open"); }
    else if (e.target.closest(".nav-scrim") || e.target.closest(".sidebar .nav-link")) {
      document.body.classList.remove("nav-open");
    }
  });

  /* -------------------------------------------------------------------------
     4. Auto TOC (from main h2[id]/h3[id]) + scroll-spy
     ----------------------------------------------------------------------- */
  (function buildTOC() {
    var tocNav = $(".toc__list");
    var main = $(".main");
    if (!tocNav || !main) return;
    var heads = $$("h2[id], h3[id]", main);
    if (!heads.length) { var t = $(".toc"); if (t) t.style.display = "none"; return; }
    heads.forEach(function (h) {
      var a = document.createElement("a");
      a.href = "#" + h.id;
      a.textContent = h.textContent.replace(/\s*#\s*$/, "");
      a.setAttribute("data-depth", h.tagName === "H3" ? "3" : "2");
      tocNav.appendChild(a);
    });
    var links = $$("a", tocNav);
    var byId = {};
    links.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a; });
    if ("IntersectionObserver" in window) {
      var seen = {};
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { seen[en.target.id] = en.isIntersecting ? en.intersectionRatio : 0; });
        var bestId = null, best = -1;
        Object.keys(seen).forEach(function (id) { if (seen[id] > best) { best = seen[id]; bestId = id; } });
        links.forEach(function (a) { a.classList.remove("active"); });
        if (bestId && byId[bestId] && best > 0) byId[bestId].classList.add("active");
      }, { rootMargin: "-10% 0px -75% 0px", threshold: [0, 0.5, 1] });
      heads.forEach(function (h) { io.observe(h); });
    }
  })();

  /* -------------------------------------------------------------------------
     5. Collapsible cards (click/keyboard head) + expand/collapse-all + a11y
        Heads are keyboard-operable buttons (role + tabindex + aria-expanded).
        Cards upgrade via components.js BEFORE this runs, so the decorate pass
        sees every head. Header-only cards (no .card__body) are left untouched.
     ----------------------------------------------------------------------- */
  function setCardOpen(card, open) {
    card.classList.toggle("is-open", open);
    var head = card.querySelector(".card__head");
    if (head && head.getAttribute("role") === "button") head.setAttribute("aria-expanded", open ? "true" : "false");
  }
  function toggleCard(card) { setCardOpen(card, !card.classList.contains("is-open")); }
  $$(".card__head").forEach(function (head) {
    if (!head.parentElement.querySelector(".card__body")) return; // not expandable → no button semantics
    head.setAttribute("role", "button");
    if (!head.hasAttribute("tabindex")) head.setAttribute("tabindex", "0");
    head.setAttribute("aria-expanded", head.parentElement.classList.contains("is-open") ? "true" : "false");
  });
  document.addEventListener("click", function (e) {
    var head = e.target.closest(".card__head");
    if (head && !e.target.closest("a")) { toggleCard(head.parentElement); }
    var allBtn = e.target.closest(".js-expand-all, .js-collapse-all");
    if (allBtn) {
      var open = allBtn.classList.contains("js-expand-all");
      var scope = allBtn.getAttribute("data-target");
      $$((scope ? scope + " " : "") + ".card").forEach(function (c) { setCardOpen(c, open); });
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" && e.key !== " " && e.key !== "Spacebar") return;
    var head = e.target.closest(".card__head");
    if (!head || e.target.closest("a") || head.getAttribute("role") !== "button") return;
    e.preventDefault(); // Space would scroll the page otherwise
    toggleCard(head.parentElement);
  });

  /* -------------------------------------------------------------------------
     6. Tabs
     ----------------------------------------------------------------------- */
  document.addEventListener("click", function (e) {
    var tab = e.target.closest(".tab");
    if (!tab) return;
    var wrap = tab.closest(".tabs");
    var key = tab.getAttribute("data-tab");
    $$(".tab", wrap).forEach(function (t) { t.classList.toggle("active", t === tab); });
    $$(".tab-panel", wrap).forEach(function (p) { p.classList.toggle("active", p.getAttribute("data-tab") === key); });
  });

  /* -------------------------------------------------------------------------
     7. Code blocks: add bar + copy, JSON syntax highlight
     ----------------------------------------------------------------------- */
  function escapeHtml(s) { return s.replace(/[&<>]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]; }); }
  function highlightJSON(src) {
    return escapeHtml(src).replace(
      /("(?:\\.|[^"\\])*"\s*:)|("(?:\\.|[^"\\])*")|(\b-?\d+\.?\d*(?:[eE][+-]?\d+)?\b)|\b(true|false)\b|\b(null)\b/g,
      function (m, key, str, num, bool, nul) {
        if (key)  return '<span class="tok-key">' + key.replace(/\s*:$/, "") + '</span><span class="tok-punc">:</span>';
        if (str)  return '<span class="tok-str">' + str + "</span>";
        if (num)  return '<span class="tok-num">' + num + "</span>";
        if (bool) return '<span class="tok-bool">' + bool + "</span>";
        if (nul)  return '<span class="tok-null">' + nul + "</span>";
        return m;
      }
    );
  }
  function copyText(text, btn) {
    function ok() { var old = btn.textContent; btn.textContent = "Copied ✓"; btn.classList.add("ok");
      setTimeout(function () { btn.textContent = old; btn.classList.remove("ok"); }, 1400); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(ok).catch(function () { fallback(text, ok); });
    } else { fallback(text, ok); }
  }
  function fallback(text, ok) {
    var ta = document.createElement("textarea"); ta.value = text;
    ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); ok(); } catch (e) {} document.body.removeChild(ta);
  }
  $$(".code").forEach(function (block) {
    var pre = $("pre", block); if (!pre) return;
    var raw = pre.textContent;
    var lang = block.getAttribute("data-lang") || "";
    if (!block.querySelector(".code__bar") && !block.classList.contains("no-bar")) {
      var bar = document.createElement("div"); bar.className = "code__bar";
      var label = document.createElement("span"); label.textContent = block.getAttribute("data-title") || lang || "code";
      var btn = document.createElement("button"); btn.className = "code__copy"; btn.type = "button"; btn.textContent = "Copy";
      btn.addEventListener("click", function () { copyText(raw, btn); });
      bar.appendChild(label); bar.appendChild(btn); block.insertBefore(bar, pre);
    }
    if (lang === "json") {
      var code = pre.querySelector("code") || pre;
      code.innerHTML = highlightJSON(raw);
    }
  });

  /* -------------------------------------------------------------------------
     8. Filter bar (pills = single-select per group) + search
        .filter-bar[data-target="#sel"]  .pill[data-group][data-value]
        items carry data-* matching group names; search matches text.
     ----------------------------------------------------------------------- */
  $$(".filter-bar").forEach(function (bar) {
    var targetSel = bar.getAttribute("data-target"); if (!targetSel) return;
    var items = $$(targetSel);
    var state = {}; // group -> value ('all' = no constraint)
    var input = $("input", bar);

    function apply() {
      var q = (input && input.value || "").trim().toLowerCase();
      var shown = 0;
      items.forEach(function (it) {
        var ok = true;
        Object.keys(state).forEach(function (g) {
          var v = state[g];
          if (v && v !== "all") {
            var data = (it.getAttribute("data-" + g) || "").toLowerCase();
            // support space-separated multi-values on the item (e.g. data-traces)
            var set = data.split(/\s+/);
            if (set.indexOf(v.toLowerCase()) === -1) ok = false;
          }
        });
        if (ok && q) { if (it.textContent.toLowerCase().indexOf(q) === -1) ok = false; }
        it.classList.toggle("is-hidden", !ok);
        if (ok) shown++;
      });
      // empty-state: auto-create a .filter-empty the first time if the author didn't
      // supply one, so a list filtered to zero never goes silently blank.
      var empty = bar.parentElement.querySelector(".filter-empty");
      if (!empty) {
        empty = document.createElement("div");
        empty.className = "filter-empty";
        empty.textContent = "No items match this filter";
        bar.parentNode.insertBefore(empty, bar.nextSibling);
      }
      bar.parentElement.classList.toggle("is-empty", shown === 0);
      var counter = bar.querySelector(".js-filter-count");
      if (counter) counter.textContent = shown + "/" + items.length;
    }

    $$(".pill", bar).forEach(function (p) {
      var g = p.getAttribute("data-group"); if (g && !(g in state)) state[g] = "all";
      p.addEventListener("click", function () {
        var grp = p.getAttribute("data-group"), val = p.getAttribute("data-value");
        state[grp] = (state[grp] === val) ? "all" : val;
        $$('.pill[data-group="' + grp + '"]', bar).forEach(function (q) {
          q.classList.toggle("active", q.getAttribute("data-value") === state[grp]);
        });
        apply();
      });
    });
    if (input) input.addEventListener("input", apply);
    apply();
  });

  /* -------------------------------------------------------------------------
     9. Sortable tables
     ----------------------------------------------------------------------- */
  $$("table.data-table[data-sortable]").forEach(function (table) {
    var ths = $$("thead th", table);
    ths.forEach(function (th, idx) {
      th.setAttribute("tabindex", "0"); // keyboard-focusable sort control
      function doSort() {
        var dir = th.getAttribute("data-sort") === "asc" ? "desc" : "asc";
        ths.forEach(function (t) { t.removeAttribute("data-sort"); t.removeAttribute("aria-sort"); });
        th.setAttribute("data-sort", dir);
        th.setAttribute("aria-sort", dir === "asc" ? "ascending" : "descending");
        var tbody = $("tbody", table);
        var rows = $$("tr", tbody);
        rows.sort(function (a, b) {
          var x = (a.children[idx] ? a.children[idx].textContent.trim() : "");
          var y = (b.children[idx] ? b.children[idx].textContent.trim() : "");
          var nx = parseFloat(x.replace(/[^0-9.\-]/g, "")), ny = parseFloat(y.replace(/[^0-9.\-]/g, ""));
          var both = !isNaN(nx) && !isNaN(ny) && /\d/.test(x) && /\d/.test(y);
          var cmp = both ? (nx - ny) : x.localeCompare(y, undefined, { numeric: true });
          return dir === "asc" ? cmp : -cmp;
        });
        rows.forEach(function (r) { tbody.appendChild(r); });
      }
      th.addEventListener("click", doSort);
      th.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") { e.preventDefault(); doSort(); }
      });
    });
  });

  /* -------------------------------------------------------------------------
     10. Trace matrix: click row header to highlight the AC row
     ----------------------------------------------------------------------- */
  $$(".trace-matrix").forEach(function (m) {
    $$("tbody th", m).forEach(function (th) {
      th.addEventListener("click", function () {
        var tr = th.parentElement;
        var wasActive = tr.classList.contains("is-active");
        $$("tbody tr", m).forEach(function (r) { r.classList.remove("is-active"); });
        if (!wasActive) tr.classList.add("is-active");
      });
    });
  });

  /* -------------------------------------------------------------------------
     11. Deep-link: open collapsed card targeted by hash, then scroll
     ----------------------------------------------------------------------- */
  function revealHash() {
    if (!location.hash) return;
    var el; try { el = document.querySelector(location.hash); } catch (e) { return; }
    if (!el) return;
    var card = el.closest(".card"); if (card) setCardOpen(card, true);
    var panelKey = el.closest(".tab-panel"); // open its tab if inside one
    setTimeout(function () { el.scrollIntoView({ behavior: "smooth", block: "start" }); }, 60);
  }
  window.addEventListener("hashchange", revealHash);
  if (document.readyState !== "loading") revealHash();
  else document.addEventListener("DOMContentLoaded", revealHash);

  /* -------------------------------------------------------------------------
     12. Scroll-to-top
     ----------------------------------------------------------------------- */
  var topBtn = $(".scroll-top");
  if (topBtn) {
    window.addEventListener("scroll", function () { topBtn.classList.toggle("show", window.scrollY > 600); }, { passive: true });
    topBtn.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });
  }
})();
