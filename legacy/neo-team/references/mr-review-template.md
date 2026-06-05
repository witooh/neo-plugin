# MR Review Comment Template (neo-team)

The Orchestrator composes the GitLab MR review comment from this template after **Code Reviewer ∥ Security ∥ QA** return (SKILL.md § MR Workflows), then posts it via `Skill(gitlab)` ("Post a Comment"). **Table-first** — short and scannable. Keep file paths, code, and identifiers in English; write descriptions in Thai.

The **AC/TC Compliance** section appears **only in mode 8b** (the MR has a JIRA card); omit it entirely in mode 8a.

## Template

```
## 🤖 ผล Review MR

| | |
|---|---|
| **MR** | !<mr_id> — <title> |
| **Branch** | <source> → <target> |
| **โหมด** | มี JIRA card: <card IDs> / ไม่มี card |
| **ผล** | ✅ อนุมัติ (Approved) / ❌ ต้องแก้ก่อน merge |

### 🔎 Findings

| ระดับ | ด้าน | ไฟล์:บรรทัด | ประเด็น | ข้อเสนอแนะ |
|------|------|------------|---------|-----------|
| 🔴 Blocker | Code | path:line | <issue> | <fix> |
| 🟠 Critical | Security | path:line | <issue> | <remediation> |
| 🟡 Warning | Code | path:line | <issue> | <fix> |
| 🔵 Info | Code | path:line | <issue> | <suggestion> |

_(ด้าน = Code / Security / QA. ถ้าไม่มี finding เลย ดู § เมื่อไม่พบปัญหา)_

### 📊 สรุปนับ

| ระดับ | จำนวน |
|------|------|
| 🔴 ต้องแก้ก่อน merge (Blocker/Critical · Security Critical/High) | X |
| 🟡 คำเตือน (Warning · Security Medium) | X |
| 🔵 ข้อเสนอแนะ (Info · Security Low) | X |

### 🧪 QA

- **E2E regression:** ✅ ผ่าน N/N / ❌ fail X/N (<failing tests>) / ⚠️ รันไม่ได้ (<reason>)
- **Regression จาก MR นี้:** <list / ไม่มี>

### 🎯 AC/TC Compliance — เฉพาะโหมดมี card · JIRA: <card IDs>

| AC | สรุป | โค้ดตรง? | TC | ผล TC | ถ้าไม่ตรง (รายละเอียดให้ AI แก้) |
|----|------|---------|----|------|------------------------------|
| AC-001 | <ac summary> | ✅ | TC-001, TC-005 | 2/2 | — |
| AC-003 | <ac summary> | ❌ | TC-003 | 0/1 | <เจาะจง: คาดอะไร ได้อะไร ดูตรงไหน> |
| AC-005 | <ac summary> | ⚠️ | — | — | <เช่น ไม่มี TC trace / ไม่พบใน diff — ยังไม่ implement> |

---
*Review โดย neo-team · Claude Code*
```

## Severity reconciliation (two scales → one verdict)

Code Reviewer and Security use **different** scales. Keep each finding's **original label** in the `ระดับ` column (with an emoji), and use the `ด้าน` column to show which scale it came from. Roll them up in 📊 สรุปนับ by **merge impact**:

| Merge impact | Code Reviewer | Security |
|--------------|---------------|----------|
| 🔴 บล็อก merge | Blocker, Critical | Critical, High |
| 🟡 คำเตือน | Warning | Medium |
| 🔵 ข้อเสนอแนะ | Info | Low |

**ผล (verdict):** ❌ ต้องแก้ก่อน merge if there is **any** 🔴 row (Code Reviewer Verdict = Changes Required OR Security = Blocked OR QA Sign-Off = Blocked, OR any AC row marked ❌ in mode 8b); otherwise ✅ อนุมัติ (Approved).

## Translation guide

Keep technical terms, file paths, function names, and code in English; translate descriptions to Thai.

| English | Thai |
|---------|------|
| Blocker | ต้องแก้ (บล็อก) |
| Critical | วิกฤต |
| Warning | คำเตือน |
| Info | ข้อเสนอแนะ |
| Approved | อนุมัติ |
| Changes Required | ต้องแก้ก่อน merge |
| No findings | ไม่พบปัญหา |

## เมื่อไม่พบปัญหา

ถ้าทั้ง 3 role ไม่พบปัญหา ให้ละตาราง Findings แล้วใส่บรรทัดสรุปแทน:

```
### 🔎 Findings
ไม่พบปัญหาด้าน convention, security, หรือ test coverage ✅
```

โหมด 8b ยังคงแสดงตาราง AC/TC Compliance เสมอ (เป็นหลักฐานว่า MR ตรงกับการ์ดหรือไม่).
```
