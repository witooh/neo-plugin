#!/usr/bin/env python3
"""
lint.py — self-contained structural linter for the design-docs HTML site.
Zero install: pure Python 3 (stdlib only). No browser / chrome-devtools needed.

Catches the "silent breakage" classes that HTML editing is prone to:
  1. Unbalanced block tags (a dropped/extra </div> etc.)  -> ERROR
  2. Unknown tags = likely an unescaped "<" in content
     (e.g. someone typed <valid-uuid> instead of &lt;valid-uuid&gt;) -> ERROR
  3. Bad "&" that is not a valid HTML entity (should be &amp;)      -> ERROR
  4. .card without data-status (filters/coverage would silently break) -> WARNING

Usage:
  python3 lint.py            # lint every *.html under this file's folder
  python3 lint.py DIR        # lint every *.html under DIR (recursive)
  python3 lint.py a.html ... # lint specific files
Exit code: 0 = clean, 1 = at least one ERROR.
"""
import re, sys, pathlib

# Block tags that are NEVER auto-closed in HTML — safe to balance-count.
BALANCE = ["div", "section", "nav", "aside", "main", "header", "footer",
           "table", "thead", "tbody", "ul", "ol", "dl",
           "button", "pre", "script", "style", "code", "span", "a",
           "h1", "h2", "h3", "h4", "ac-card", "tc-card", "callout-box", "card-flow", "status-badge", "trace-matrix",
           "ac-summary", "ac", "tc-summary", "tc-deferred", "tc", "ac-total", "tc-total"]

# Generous whitelist of valid tags we use (lowercase).
KNOWN = set(BALANCE) | {
    "html", "head", "body", "title", "meta", "link", "base",
    "p", "br", "hr", "wbr", "b", "i", "em", "strong", "small", "mark", "sub", "sup",
    "li", "dt", "dd", "tr", "td", "th", "caption", "colgroup", "col", "tfoot",
    "article", "figure", "figcaption", "blockquote", "cite", "q",
    "img", "picture", "source", "input", "textarea", "select", "option",
    "label", "form", "fieldset", "legend", "kbd", "samp", "var",
    "abbr", "time", "data", "details", "summary",
    # svg (in case a diagram is ever pre-rendered inline)
    "svg", "path", "g", "rect", "circle", "line", "polyline", "polygon", "text", "tspan", "defs", "marker",
    # <ac-card> authoring tags: GWT prose holders + business-rule holder ("g" already present above as SVG)
    "w", "t", "rule", "blocker",
    # <tc-card> authoring tags: request/response JSON, test steps, + field-row prose holders
    # ("tdata" not "data" — <data> is a real HTML element already in KNOWN above)
    "req", "res", "steps", "step", "expected", "tdata", "precond",
}

# Regions where raw "<" / "&" are NOT HTML content (so entity/tag rules don't apply):
#   - mermaid source blocks (free text, arrows)
#   - <script> inner content (JS uses && and < legitimately)
#   - <style> inner content (CSS)
# We blank the INNER text but keep the surrounding tags (so balance-counting still works)
# and keep line numbers stable.
RE_COMMENT = re.compile(r'<!--.*?-->', re.S)
RE_MERMAID = re.compile(r'(<div class="mermaid">)(.*?)(</div>)', re.S)
RE_SCRIPT  = re.compile(r'(<script[^>]*>)(.*?)(</script>)', re.S)
RE_STYLE   = re.compile(r'(<style[^>]*>)(.*?)(</style>)', re.S)

def _blank_inner(m):
    return m.group(1) + ("\n" * m.group(2).count("\n")) + m.group(3)

def strip_noise(html):
    # Blank HTML comments entirely (tags inside a comment must not be counted).
    html = RE_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), html)
    html = RE_SCRIPT.sub(_blank_inner, html)
    html = RE_STYLE.sub(_blank_inner, html)
    html = RE_MERMAID.sub(_blank_inner, html)
    return html

def lint(path):
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    html = strip_noise(raw)
    errors, warns = [], []

    # 1. Balance counts
    for tag in BALANCE:
        opens = len(re.findall(r'<' + tag + r'(?=[\s/>])', html))
        closes = len(re.findall(r'</' + tag + r'\s*>', html))
        if opens != closes:
            errors.append(f"tag <{tag}> unbalanced: {opens} open vs {closes} close")

    # 2. Unknown tags (likely unescaped '<')
    for m in re.finditer(r'<(/?)([a-zA-Z][\w-]*)', html):
        name = m.group(2).lower()
        if name not in KNOWN:
            line = html.count("\n", 0, m.start()) + 1
            errors.append(f"line {line}: unknown tag <{m.group(1)}{m.group(2)}> "
                          f"(unescaped '<'? use &lt;)")

    # 3. Bad ampersand
    for m in re.finditer(r'&(?!(?:[a-zA-Z][a-zA-Z0-9]*|#[0-9]+|#x[0-9a-fA-F]+);)', html):
        line = html.count("\n", 0, m.start()) + 1
        ctx = html[m.start():m.start()+12].replace("\n", " ")
        errors.append(f"line {line}: bare '&' not an entity (use &amp;) near \"{ctx}\"")

    # 4. .card missing data-status (warning) — match "card" as a standalone class
    #    token only, so "link-card" / other *-card variants are NOT flagged.
    for m in re.finditer(r'<div class="([^"]*)"[^>]*>', html):
        classes = m.group(1).split()
        if "card" in classes and "data-status" not in m.group(0):
            line = html.count("\n", 0, m.start()) + 1
            warns.append(f"line {line}: .card without data-status (filter/coverage may miss it)")

    # 4b. <ac-card> missing status= (parity with the .card check above; lint sees the
    #     SOURCE <ac-card status="…">, which components.js upgrades into data-status).
    for m in re.finditer(r'<ac-card\b[^>]*>', html):
        if not re.search(r'\bstatus\s*=', m.group(0)):
            line = html.count("\n", 0, m.start()) + 1
            warns.append(f"line {line}: <ac-card> without status= (filter/coverage may miss it)")

    # 4c. <tc-card> missing status= (parity with 4b; status drives is-<status>,
    #     data-status, the badge, and the derived data-tags=blocked).
    for m in re.finditer(r'<tc-card\b[^>]*>', html):
        if not re.search(r'\bstatus\s*=', m.group(0)):
            line = html.count("\n", 0, m.start()) + 1
            warns.append(f"line {line}: <tc-card> without status= (filter/coverage may miss it)")

    return errors, warns

def main():
    args = sys.argv[1:]
    here = pathlib.Path(__file__).parent
    roots = [pathlib.Path(a) for a in args] if args else [here]
    files = []
    for r in roots:
        files += sorted(r.rglob("*.html")) if r.is_dir() else [r]
    # skip templates/partials (e.g. _shell.html with {{placeholders}}) — keeps a
    # no-arg run inside the assets dir from failing on the page skeleton.
    files = [f for f in files if not f.name.startswith("_")]
    total_err = 0
    for f in files:
        try: rel = f.relative_to(here)
        except ValueError: rel = f
        errs, warns = lint(f)
        total_err += len(errs)
        status = "OK" if not errs else f"{len(errs)} ERROR"
        extra = f" / {len(warns)} warn" if warns else ""
        print(f"{'✗' if errs else '✓'} {str(rel):42} {status}{extra}")
        for e in errs:  print(f"    ERROR  {e}")
        for w in warns: print(f"    warn   {w}")
    print(f"\n{'FAILED' if total_err else 'PASS'} — {total_err} error(s) across {len(files)} file(s)")
    sys.exit(1 if total_err else 0)

if __name__ == "__main__":
    main()
