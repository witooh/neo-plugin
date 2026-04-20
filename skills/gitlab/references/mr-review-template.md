# MR Review Comment Template

Use this template when posting via `glab mr note`. Fill in the findings from code-reviewer, security, and qa agents. Keep file paths and code snippets in English — translate findings and descriptions to Thai.

```
## 🤖 ผลการ Review Merge Request

**MR:** !<mr_id> — <mr_title>
**Branch:** <source_branch> → <target_branch>

---

### 📋 Code Review

<code_reviewer_findings_in_thai>

---

### 🔒 Security Review

<security_findings_in_thai>

---

### 🧪 QA Review

<qa_findings_in_thai>

---

### สรุปผล

| ระดับ | จำนวน |
|-------|-------|
| Blocker | X |
| Critical | X |
| Warning | X |
| Info | X |

**ผลการตรวจสอบ:** ✅ Approved / ❌ ต้องแก้ไขก่อน Merge

<brief_next_steps_if_any_in_thai>

---
*Review โดย GitLab Skill · Claude Code*
```

## Translation Guide

Translate findings into Thai. Keep technical terms, file paths, function names, and code snippets in English.

| English | Thai |
|---------|------|
| Blocker | ต้องแก้ไข (บล็อก) |
| Critical | วิกฤต |
| Warning | คำเตือน |
| Info | ข้อเสนอแนะ |
| Approved | อนุมัติ |
| Changes Required | ต้องแก้ไขก่อน Merge |
| No findings | ไม่พบปัญหา |

## When there are no findings

If all three agents return no issues:

```
### 📋 Code Review
ไม่พบปัญหาด้าน convention ✅

### 🔒 Security Review
ไม่พบปัญหาด้าน security ✅

### 🧪 QA Review
ไม่พบปัญหาด้าน test coverage ✅
```
