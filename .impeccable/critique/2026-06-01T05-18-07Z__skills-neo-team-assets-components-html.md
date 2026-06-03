---
target: skills/neo-team/assets/components.html (+ realistic demo page)
total_score: 32
p0_count: 0
p1_count: 2
timestamp: 2026-06-01T05-18-07Z
slug: skills-neo-team-assets-components-html
---
# Critique — neo-team Design Docs component system (`components.html` + realistic demo page)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | theme persist/toggle, active nav + TOC scroll-spy, sort direction, "Copied ✓", active pill — ครบ; sort ไม่มี `aria-sort`, filter ไม่โชว์ผลนับ default |
| 2 | Match System / Real World | 4 | พูดภาษา domain คล่อง (AC/TC/GWT/JIRA/Ready-Blocked-Pending/traceability), Thai+EN เป็นธรรมชาติ, ลำดับ doc สมเหตุผล |
| 3 | User Control & Freedom | 3 | กาง/พับ, กรอง toggle-off, tab, theme, deep-link, drawer-scrim ครบ; กลุ่มคีย์บอร์ดคุมไม่ได้ (ดู #4/#7) |
| 4 | Consistency & Standards | 3 | visual system นิ่งมาก (token/card/badge เดียว) แต่ `<div class="card__head">` + `<th>` คลิกแทน `<button>`; catalog §0 shell snippet drift จาก `_shell.html` จริง |
| 5 | Error Prevention | 3 | drift-proof by construction: summary/matrix/total derive จาก `<ac-card>`/`<tc-card>` → นับ/สถานะค้างไม่ได้ (จุดเด่น domain จริง) |
| 6 | Recognition Rather Than Recall | 4 | sidebar(label+icon) + auto-TOC + badge + crumbs + heading — มองเห็นหมด ไม่ต้องจำ |
| 7 | Flexibility & Efficiency | 2 | เมาส์: filter/sort/collapse-all/deep-link/theme คล่อง + print stylesheet; แต่ไม่มี keyboard shortcut และ **กาง/เรียงด้วยคีย์บอร์ดไม่ได้เลย** |
| 8 | Aesthetic & Minimalist Design | 4 | Linear/Stripe-grade restraint, hairline, elevation เบา, ไม่มี side-stripe/gradient-text/eyebrow-ทุก section |
| 9 | Help Recognize / Recover Errors | 3 | mermaid → degrade เป็น mono source, clipboard มี textarea fallback; filter 0 ผล → อาจ blank (empty-state เป็น optional element) |
| 10 | Help and Documentation | 3 | catalog + `html-output.md` + `.small.muted` explainer ใต้ทุก component ครบมาก; แต่ §0 "skeleton" snippet **ตกหล่น `components.js`** (ทำให้เข้าใจผิดบน detail ที่ load-bearing) |
| **Total** | | **32/40** | **Good (28–35) — ฐานแข็ง แก้จุดอ่อนเฉพาะจุด** |

## Anti-Patterns Verdict

**ดูเหมือน AI สร้างไหม? — ไม่** นี่อ่านเหมือน internal design-system ที่ตั้งใจ craft (engineer's reference tool) ไม่ใช่ landing page generative

**LLM assessment:** ผ่าน slop test ชัด — ไม่มี hero-gradient, ไม่มี gradient text (มีแค่โลโก้ 34px), ไม่มี side-stripe (card ใช้ tinted border เต็มเส้นตาม comment ใน CSS), ไม่มี eyebrow-บน-ทุก-section abuse, ไม่มี identical-card-grid, ไม่มี hero-metric template. Restraint + craft ตรง brand "precise/quiet/trustworthy"

**Deterministic scan (`detect.mjs --json`):** 2 finding ทั้งคู่ severity ต่ำ
- `em-dash-overuse` (warning, 30 ใน catalog / 9 ใน demo) — **ส่วนใหญ่ false-positive**: "—" ที่นี่เป็น functional separator ("AC-001 — Open account", "BR-01 — unique id") + **placeholder ของ empty cell ที่ออกแบบไว้ตั้งใจ** ("Sub-operation —") + Thai tech doc ไม่ใช่ marketing cadence. (เหลือเศษจริงนิดเดียวใน prose explainer ที่ "—" แทนด้วย `,`/`:` ได้)
- `numbered-section-markers` (advisory) — บน **demo page = false-positive** (detector อ่าน `AC-001/002/003` = data ID เป็น section marker); บน **catalog = scaffold อ่อนๆ จริง** (`0·..12·` หัวข้อ) แต่ defensible สำหรับหน้า reference ที่อ้างอิงด้วยเลข (TOC ใช้)

**Visual overlay:** ไม่ได้ inject detect.js overlay — ใช้ CLI detector + screenshot จริง (light/dark/mobile) + computed-style probe เป็น browser evidence แทน (browser inspection ทำครบ ไม่มี overlay ในหน้าให้ดู)

## Overall Impression

ระบบนี้ **craft ดีจริง** — สะอาด, restraint, scannable, ตรง brand Linear/Stripe และมี idea เชิง product ที่แข็ง: **drift-proof by construction** (summary/matrix/total derive จาก card → single source) ทำให้ของที่ปกติ "พิมพ์มือแล้วค้าง" กลายเป็นกันพลาดได้เอง — เห็นทำงานจริง end-to-end ทั้ง light/dark/mobile

จุดที่ฉุดคะแนน **ไม่ใช่เรื่อง look** แต่เป็น **accessibility ที่สัญญาไว้แต่ไม่ตรง** (PRODUCT.md เขียนชัดว่า keyboard-focus สำหรับ cards/sortable-headers + AA contrast ทั้ง 2 theme — ทั้งคู่ยังไม่ครบ) โอกาสใหญ่สุด = ปิด gap a11y/contrast ให้ implementation ตรงกับ principle ที่ประกาศไว้เอง แล้วคะแนนจะขึ้นไป 36+ ง่ายๆ

## What's Working

1. **Aesthetic + domain fit (heuristic 8/2):** hairline structure, rhythm กว้าง, elevation เบา, status-by-non-color (badge = dot + text + border + ตำแหน่ง ไม่พึ่งสีอย่างเดียว) — ตรง "Status never by color alone" และผ่าน WCAG "ห้ามสื่อด้วยสีล้วน"
2. **Drift-proof architecture ที่ทำให้เห็น (heuristic 5):** `<ac-summary>`/`<trace-matrix>`/`<ac-total>` derive จาก card จริง — ไม่ใช่ลูกเล่น แต่คือ error-prevention ระดับ product ที่ตรง Design Principle #3 ("can't drift, single source → derived")
3. **Progressive-enhancement discipline:** offline-safe (mermaid guard), reduced-motion + print stylesheet ครบ, ทุก feature guard ด้วย element presence (one app.js เสิร์ฟทุกหน้า), theme ไม่มี FOUC

## Priority Issues

- **[P1] คีย์บอร์ด/Screen-reader ใช้ card + sortable header ไม่ได้**
  - **Why:** `.card__head` เป็น `<div>` (tabindex/role = null, focusable = false), sortable `<th>` ไม่มี tabindex/`aria-sort` → ผู้ใช้คีย์บอร์ด **กางการ์ด/เรียงตารางไม่ได้เลย** และ SR ไม่รู้ว่ากดได้ — ขัด PRODUCT.md ตรงๆ ("Keyboard :focus-visible for **cards**, tabs, filters, **sortable headers**"). tabs/filter ผ่านเพราะเป็น `<button>` แต่ 2 ใน 4 ที่สัญญาไว้ไม่ผ่าน
  - **Fix:** ทำ card head เป็น `<button>` (หรือ `role="button"` + `tabindex=0` + handler Enter/Space ใน app.js §5) + `aria-expanded`; sortable `<th>` ใส่ปุ่ม/`tabindex=0` + keydown + `aria-sort=ascending|descending`; เพิ่ม skip-to-content link
  - **Suggested command:** `/impeccable harden`

- **[P1] Contrast ต่ำกว่า AA — `--text-faint` ทั้ง 2 theme + status/chip ใน light**
  - **Why:** คำนวณ WCAG จริง: `--text-faint` บน bg = **2.95 (light)** / 4.22 (dark) ใช้กับ breadcrumb (13px) + section label (TOC/nav-group/filter/stat 11–12px); และ **light-mode** status badge Ready 3.92 / Blocked 3.89 / Pending 4.03, chip P1 **3.04** / JIRA 4.45 — ต่ำกว่า 4.5 ที่ PRODUCT.md สัญญา และ status คือ signal ที่ "most-scanned" (dark theme ผ่านหมด → เป็นปัญหา tuning เฉพาะ light)
  - **Fix:** ดัน `--text-faint` ให้เข้ม (light ~`#6b7280`+, dark ~`#8a929e`+ ให้ ≥4.5 บน bg/surface); ใน light ดัน fg ของ ready/blocked/pending/warn/info ลง ~12–18% ให้ badge/chip text ≥4.5; active pill (dark) white/primary = 3.14 → ใช้ตัวอักษรเข้มขึ้นหรือ primary เข้มขึ้น
  - **Suggested command:** `/impeccable polish` (หรือ `/impeccable audit` เพื่อ sweep contrast ทั้งชุดก่อน)

- **[P2] Doc drift: catalog §0 "skeleton" ตัด `components.js` ออก**
  - **Why:** `_shell.html` จริง (line 57) โหลด `mermaid → nav → components → app` + comment ระบุ load-bearing; แต่ §0 ของ `components.html` (snippet + prose) โชว์แค่ `nav → app` → คนที่ก็อปจาก style-guide แทน `_shell.html` จะได้หน้าที่ `<ac-card>` **ไม่ upgrade** (custom element ไม่ถูก define). หน้า "spec ที่ specialist อ่าน" ที่ผิดบน detail สำคัญ = เสี่ยง
  - **Fix:** เพิ่มบรรทัด `components.js` ใน §0 snippet + prose ให้ตรง `_shell.html`
  - **Suggested command:** `/impeccable clarify`

- **[P3] Filter ผล 0 รายการ → หน้าว่างไม่มีข้อความ**
  - **Why:** empty-state (`.filter-empty`) เป็น element ที่ author ต้องใส่เอง; หน้า AC จริงที่กรอง "blocked" แล้วไม่มี blocked → blank เงียบ (Riley red flag)
  - **Fix:** ให้ filter logic สร้าง/โชว์ empty message อัตโนมัติเมื่อ shown===0 (ไม่ต้องพึ่ง author)
  - **Suggested command:** `/impeccable harden`

## Persona Red Flags

**Sam (Accessibility-dependent):** กางการ์ด AC/TC ด้วยคีย์บอร์ดไม่ได้ (div คลิก ไม่มี focus/role) · เรียงตารางด้วยคีย์บอร์ดไม่ได้ + ไม่มี `aria-sort` · ไม่มี skip-link → tab ผ่าน sidebar 7 ลิงก์ทุกหน้า · breadcrumb/section label contrast 2.95 อ่านยากตอน low-vision. **โดน hard ที่สุด — และเป็นกลุ่มที่ PRODUCT.md สัญญาไว้ตรงๆ**

**Alex (Power user):** ไม่มี keyboard shortcut, กาง/เรียงต้องใช้เมาส์, filter search แยกต่อ bar (ไม่ global) — แต่มี collapse/expand-all + deep-link ช่วย. ระดับกลาง

**Riley (Stress tester):** filter → 0 ผล = หน้าว่างเงียบ · catalog **ไม่โหลด `components.js`** → demo ในนั้นเป็น markup พิมพ์มือที่อาจ drift จาก output จริงของ `components.js` (น่าขันเพราะระบบขายเรื่อง drift-proof) · long Thai string wrap โอเค

## Minor Observations

- lede inline-code chip wrap กลางคำบน mobile ("`<ac-/card>`") — เพิ่ม `white-space:nowrap` ให้ `:not(pre)>code` หรือยอมรับได้
- chevron `▸` (text-faint) เป็น cue เดียวว่าการ์ดกางได้ — contrast ต่ำ + เล็ก, first-timer อาจไม่เห็น affordance
- active pill ไม่มี `aria-pressed`; tabs ไม่มี `role=tab`/`aria-selected` (ARIA tab pattern) — enhancement
- 4 ตาราง (AC/TC summary, Deferred, Matrix) ติดกันใน doc จริง → visual sameness ช่วงกลาง (ยอมรับได้สำหรับ tabular data, มี heading คั่น)

## Questions to Consider

- ถ้า a11y เป็นกลุ่มที่ PRODUCT.md สัญญาไว้ — ควรถือว่า keyboard/SR เป็น P1 ที่ต้องปิดก่อน ship จริงไหม?
- "—" ในฐานะ empty-cell placeholder เป็น decision ที่ดี — จะ document ให้ detector/คนอื่นรู้ว่าไม่ใช่ slop ไหม?
- catalog ควร "โหลด components.js + ใช้ tag จริง" เพื่อให้ demo ไม่มีทาง drift จาก output จริง (กิน dogfood ตัวเอง) ไหม?
