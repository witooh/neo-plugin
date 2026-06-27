# Shared: Convention Grounding — read the binding guides before reviewing or coding

**Single source of truth for HOW a role grounds itself in a project's engineering conventions.** Referenced by the Code Reviewer (file-set = the diff) and the Developer (file-set = the files it is about to write). The Architect grounds the same way but maps **design sections** to layers, so it keeps its own inline block in its role file; this file owns the **file-set-driven** mechanics those two roles share. The role file keeps its own BLOCKED / NEEDS_CONTEXT enforcement; this file owns the **procedure**.

## 1. Conventions may be LAYERED — an index is not the rules

`CLAUDE.md` / `AGENTS.md` may be only a thin **INDEX** that points to per-layer guides, not the rules themselves. When it does, reviewing or coding against the index alone misses the real binding rules. Follow the index to the guides and apply **those**. Never invent a convention from training data — if the project says nothing, it is not a rule (`preamble.md` §1).

## 2. Inclusion modes (when the guides declare one)

A layered system often keeps its guides in a folder whose files declare an `inclusion:` mode in frontmatter (e.g. a `.kiro/steering/`-style folder — one example, not the only shape):
- **`always`** — load first, unconditionally. This is the architecture map: dependency rule, layer boundaries, where interfaces / ports live, the cross-cutting invariants every change is checked against.
- **`fileMatch <glob>`** — load **only when a file in your file-set matches the glob** (e.g. an HTTP-delivery guide for `**/delivery/http/**`, a domain guide for `**/core/domain/**`). The glob is what makes selection deterministic.
- **`manual`** — never auto-loads; you load it on purpose. The most important manual file is the **real-names / instance** guide (§4).

A repo without `inclusion:` frontmatter still works: treat the index's links as the guide set and select by the same file-set logic (§5).

## 3. Binding, not reference

These guides are **binding**: they fix where every element lives and how errors / status / idempotency / naming work — the same authority as the api-spec for an endpoint. A pattern the guides **don't** cover → **don't improvise**. Surface it as an Open Question (Code Reviewer: an **Info** finding noting the convention gap; Developer: `NEEDS_CONTEXT` or a `DONE_WITH_CONCERNS` note) — same discipline as not designing around an AC defect.

## 4. The real-names / instance guide resolves the placeholders

Per-layer guides are usually **generic placeholders** (they describe "the domain layer", not your types) and point to one **manual** file that carries the project's real type / context / module names. Read that instance file to resolve the placeholders — a generic guide read without it tells you the *shape* of a rule but not the *concrete* binding. If the index names such a file, it is mandatory for any non-trivial review or change.

## 5. The file-set-driven selection algorithm (both roles)

Resolve your **file-set** (your role file says what it is — §6), then:
1. **Read the index** (`CLAUDE.md` / `AGENTS.md`). If it is the rules themselves (no layered guides) → §7 fallback.
2. **Read every `always`-load guide** — the architecture map, before anything file-specific.
3. **For each `fileMatch` guide, test its glob against your file-set; read every guide that matches.** Read a guide once even if many files match it; conversely read **every** distinct matched guide — do not stop at the first.
4. **Read the manual real-names / instance guide** (§4) to resolve placeholders.
5. **Gap** — a rule your file-set needs that no guide covers → Open Question (§3), never an improvised convention.

## 6. Per-role file-set (the only difference between the roles)

- **Code Reviewer = diff-driven.** Your file-set is **every file in the diff / PR**. A feature PR almost always spans many layers at once (handler + usecase + domain + repository + tests), so step 3 typically matches **nearly all** `fileMatch` guides — read them all. The failure mode here is **under-reading**: skipping a layer's guide because the diff "looked like one layer" lets a real binding rule go unchecked. When in doubt, read the guide.
- **Developer = write-driven.** Your file-set is **the files you are about to create or modify**. Read those layers' guides **before** writing, so the code is born conforming instead of being corrected in review. As the change grows to touch a new layer, read that layer's guide before you touch it.

## 7. Fallbacks

- **Single `CLAUDE.md`, no layered guides** — it is itself the rules; read it directly and apply it. There is no index to follow and no `inclusion:` modes; §5 collapses to "read it".
- **No conventions file at all** — the role's existing behavior governs: Code Reviewer → `BLOCKED` ("conventions cannot be verified"); Developer → `NEEDS_CONTEXT` (missing conventions). Never substitute training-data assumptions for the missing file.
