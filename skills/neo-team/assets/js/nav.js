/* ============================================================================
   nav.js — per-project sidebar registry for the Design Docs site.

   Edit THIS FILE ONLY to add/rename usecases. app.js (renderNav) builds the
   grouped sidebar from it on every page, so no page hardcodes its sidebar.

   - hrefs are RELATIVE TO docs/design/ (the site root). renderNav prepends each
     page's data-asset-prefix automatically, so write them once here, root-relative.
   - This file is created once by scaffold.sh and NEVER overwritten — it is the
     single source of truth for navigation + brand in this project.
   ========================================================================== */
window.DOCS_BRAND = { mark: "DS", title: "Design Docs", sub: "<project>" };

window.DOCS_NAV = [
  { group: "Overview", links: [
    { href: "index.html",      label: "Home · Registry", ico: "◎" },
    { href: "components.html", label: "Components",       ico: "◆" }
  ]},

  // Add ONE group per usecase (BA adds this on first gen of the usecase):
  // { group: "<Usecase Name>", links: [
  //   { href: "<usecase>/index.html",               label: "Overview",            ico: "▸" },
  //   { href: "<usecase>/acceptance-criteria.html", label: "Acceptance Criteria", ico: "✓" },
  //   { href: "<usecase>/api-contracts.html",       label: "API Contracts",       ico: "⇄" },
  //   { href: "<usecase>/test-cases.html",          label: "Test Cases",          ico: "⚗" },
  //   { href: "<usecase>/traceability.html",        label: "Traceability",        ico: "⛓" }
  // ]},

  { group: "System Design", links: [
    { href: "system-design/index.html",           label: "Overview",        ico: "▸" },
    { href: "system-design/module-design.html",   label: "Module Design",   ico: "▤" },
    { href: "system-design/database-schema.html", label: "Database Schema", ico: "▦" },
    { href: "system-design/adrs.html",            label: "ADRs",            ico: "⚖" },
    { href: "system-design/security-flags.html",  label: "Security Flags",  ico: "⚑" }
  ]}
];
