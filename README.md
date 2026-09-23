# neo

Org domain skills for AI coding agents (HTTP/API/e2e, Jira/GitLab, Go scaffold, SIT). No router, no bundled workflow.

neo is a skill pack: 17 skills in `skills/`. The host agent loads matching skills; developers can also pick a skill themselves. neo does not orchestrate ingest → spec → implement.

- **advice-mode** is user-invoked. The other 16 are model-invoked.
- **Your git stays yours.** Commit / push only when you ask, through `gitlab`.

## Install

**Claude Code**

```
/plugin marketplace add witooh/neo-plugin
/plugin install neo@neo
```

**Grok Build**

Native Grok plugin: `.grok-plugin/marketplace.json` plus `.grok-plugin/plugin.json`, skills from `skills/`. See [docs/grok-setup.md](docs/grok-setup.md).

```bash
grok plugin install witooh/neo-plugin --trust
grok plugin enable neo
```

Or add this repo as a marketplace, then install by catalog name:

```bash
grok plugin marketplace add witooh/neo-plugin
grok plugin install neo --trust
grok plugin enable neo
```

**omp**

Native omp package: the `omp` block in `package.json` and `skills/` discovered as-is. See [docs/omp-setup.md](docs/omp-setup.md).

```bash
# install
omp plugin install github:witooh/neo-plugin

# update (same command + --force — pulls latest tip / release)
omp plugin install github:witooh/neo-plugin --force

# uninstall
omp plugin uninstall neo
```

Lists under **npm Plugins** as `neo@<version>`. Do **not** use `omp plugin marketplace` or
`omp plugin upgrade` for neo — those are marketplace-only and will not track this install.

Dev against a working tree: `omp plugin link <path-to-local-clone>`.

**pi**

Installs as a native pi package; skills load from `skills/`. See [docs/pi-setup.md](docs/pi-setup.md).

Install from the repo:

```bash
pi install git:github.com/witooh/neo-plugin
```

Install from a local clone:

```bash
git clone https://github.com/witooh/neo-plugin.git
pi install ./neo-plugin
```

**Cursor**

In Customize, add this repo from GitHub. Cursor reads `.cursor-plugin/marketplace.json` and loads skills from `skills/`.

```text
https://github.com/witooh/neo-plugin
```

**Kiro**

```bash
./kiro.sh --project      # or --global → ~/.kiro
```

Copies **skills only**.

**Cursor Cloud Agent.** `scripts/install-cursor-cloud.sh` copies the pack into `~/.cursor/skills` during `install`, which is what the Build snapshots. Do not `curl | bash`. Do not put it in `start`. Pin a tag when the script is vendored outside this repo:

```bash
NEO_REF=v5.0.1 ./scripts/install-cursor-cloud.sh
```

From a neo-plugin checkout the script installs that tree and ignores `NEO_REF`. It does not modify the service working tree.

## Skills

**Session / ingest / trackers**

| Skill          | Purpose                                                                         |
| -------------- | ------------------------------------------------------------------------------- |
| `advice-mode`  | Pick omp session mode (plan / vibe / goal / none) — user-invoked                |
| `markitdown`   | Ingest JIRA, Confluence, URLs, and files into `docs/knowledge/` with provenance |
| `atlassian`    | JIRA / Confluence operations via `acli`                                         |
| `gitlab`       | GitLab MR operations via `glab`                                                 |

**Proving it works**

| Skill            | Purpose                                                     |
| ---------------- | ----------------------------------------------------------- |
| `e2e-playwright` | AC-driven HTTP e2e tests (Jest + Playwright request)        |
| `falsifying`     | Attack a green gate: can it go red?                         |
| `bug-hunter`     | Latent defects no gate covers                               |
| `attack-test`    | Live HTTP abuse paths after happy path                      |

**The API contract chain**

| Skill                | Purpose                                                          |
| -------------------- | ---------------------------------------------------------------- |
| `api-spec`           | Custom-YAML contract at `docs/api/` — spec-first source of truth |
| `openapi-doc`        | Go vs `docs/api/` drift report                                   |
| `open-collection`    | Bruno collection from the spec                                   |
| `confluence-api-doc` | Publish API docs to Confluence                                   |

**Shaping a service**

| Skill             | Purpose                                                                      |
| ----------------- | ---------------------------------------------------------------------------- |
| `init-project`    | Scaffold a Go hexagonal / DDD service from a frozen template                 |
| `migrate-project` | Restructure an existing Go service to that blueprint                         |
| `http-audit-log`  | Per-request HTTP audit logging (table + gin middleware + sqlc)               |

**SIT**

| Skill          | Purpose                                              |
| -------------- | ---------------------------------------------------- |
| `neo-core-sit` | Core SIT kubectl / ArgoCD / logs / secrets helpers   |
| `neo-aux-sit`  | Auxiliary SIT kubectl / ArgoCD / logs / secrets helpers |

## Maintaining

Validate before shipping:

```bash
node scripts/validate-skills.js       # frontmatter + dead-reference scan
node scripts/validate-pi-package.js   # pi package wiring
node scripts/validate-omp-package.js  # omp package wiring
node scripts/validate-grok-package.js # Grok marketplace + plugin wiring
node scripts/validate-cursor-package.js # Cursor marketplace + plugin wiring
claude plugin validate .              # Claude plugin structure
grok plugin validate .                # Grok plugin structure
```

## License

MIT
