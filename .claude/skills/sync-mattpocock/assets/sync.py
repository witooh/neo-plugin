#!/usr/bin/env python3
"""Sync allowlisted method skills from mattpocock/skills into neo-plugin.

Only the skills listed in sync-state.json:synced_skills are in scope. Each is
copied from its nested upstream path (skills/engineering/<name> or
skills/productivity/<name>) into neo's flat skills/<name>/ layout.

Per-file 3-way compare so a neo hand-edit is never clobbered:

    theirs = upstream file at new ref
    base   = upstream file at last_synced_commit
    ours   = current file in neo

  ours missing            -> add
  ours == theirs          -> in sync
  ours == base            -> update   (upstream changed, neo did not)
  theirs == base          -> local kept (neo edited, upstream did not)
  all three differ        -> CONFLICT (report, do not overwrite)

Skills not on the allowlist are never touched. Allowlist skills removed
upstream are reported, never auto-deleted.

Default is a dry run. Pass --apply to write and advance the baseline.
"""

from __future__ import annotations

import argparse
import datetime
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import NoReturn

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
STATE_FILE = SKILL_DIR / "sync-state.json"

# Never overwrite these even if someone adds them to the allowlist by mistake.
NEO_OWNED = {
    "using-neo",
    "api-spec",
    "e2e-playwright",
    "openapi-doc",
    "open-collection",
    "confluence-api-doc",
    "markitdown",
    "init-project",
    "migrate-project",
    "atlassian",
    "gitlab",
}


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd)


def die(msg: str) -> NoReturn:
    sys.stderr.write(f"error: {msg}\n")
    sys.exit(1)


def load_state() -> dict:
    if not STATE_FILE.exists():
        die(f"missing state file: {STATE_FILE}")
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError) as e:
        die(f"cannot read state file: {e}")


def neo_root() -> Path:
    r = run("git", "-C", str(SKILL_DIR), "rev-parse", "--show-toplevel")
    if r.returncode != 0:
        die(f"not inside a git repo: {r.stderr.strip()}")
    return Path(r.stdout.strip())


def ensure_upstream(state: dict, path_arg: str | None, no_fetch: bool) -> Path:
    """Return a local clone path, cloning to a cache dir if needed."""
    if path_arg:
        p = Path(path_arg).expanduser().resolve()
        if not p.exists():
            die(f"--upstream path does not exist: {p}")
        return p

    if state.get("upstream_path"):
        p = Path(state["upstream_path"]).expanduser().resolve()
        if p.exists():
            if not no_fetch:
                r = run("git", "-C", str(p), "fetch", "--tags", "--prune")
                if r.returncode != 0:
                    die(f"git fetch failed: {r.stderr.strip()}")
            return p

    # Cache clone under the skill dir so re-runs are cheap.
    cache = SKILL_DIR / ".upstream-cache"
    url = state.get("upstream_url") or "https://github.com/mattpocock/skills.git"
    if cache.exists():
        if not no_fetch:
            r = run("git", "-C", str(cache), "fetch", "--tags", "--prune")
            if r.returncode != 0:
                die(f"git fetch failed: {r.stderr.strip()}")
        return cache

    print(f"cloning {url} → {cache}")
    r = run("git", "clone", "--filter=blob:none", url, str(cache))
    if r.returncode != 0:
        die(f"git clone failed: {r.stderr.strip()}")
    return cache


def resolve_ref(upstream: Path, ref: str) -> str:
    r = run("git", "-C", str(upstream), "rev-parse", ref)
    if r.returncode != 0:
        die(f"cannot resolve ref {ref!r}: {r.stderr.strip()}")
    return r.stdout.strip()


def tree_at(upstream: Path, ref: str, rel_dirs: list[str]) -> dict[str, bytes]:
    """{relpath: bytes} for files under rel_dirs at ref. Empty if ref unresolvable."""
    if not rel_dirs:
        return {}
    r = subprocess.run(
        ["git", "-C", str(upstream), "archive", ref, "--", *rel_dirs],
        capture_output=True,
    )
    if r.returncode != 0:
        return {}
    tf = tarfile.open(fileobj=io.BytesIO(r.stdout))
    out: dict[str, bytes] = {}
    for m in tf.getmembers():
        if m.isfile():
            f = tf.extractfile(m)
            if f is not None:
                out[m.name] = f.read()
    return out


def skill_files(
    tree: dict[str, bytes], source_dir: str
) -> dict[str, bytes]:
    """Map skill-relative path → bytes for one source skill directory."""
    prefix = source_dir.rstrip("/") + "/"
    out: dict[str, bytes] = {}
    for path, data in tree.items():
        if path.startswith(prefix):
            out[path[len(prefix) :]] = data
        elif path == source_dir.rstrip("/"):
            continue
    return out


def classify(
    ours: bytes | None, base: bytes | None, theirs: bytes | None
) -> str:
    if theirs is None:
        return "upstream-removed"
    if ours is None:
        return "add"
    if ours == theirs:
        return "in-sync"
    if base is not None and ours == base:
        return "update"
    if base is not None and theirs == base:
        return "local-kept"
    if base is None:
        # First sync or file appeared after baseline — treat as update if different.
        return "update" if ours != theirs else "in-sync"
    return "conflict"


def main() -> None:
    ap = argparse.ArgumentParser(description="Sync mattpocock/skills method layer into neo.")
    ap.add_argument("--upstream", help="path to a local mattpocock/skills clone")
    ap.add_argument("--ref", help="upstream ref (default: state.default_ref)")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--no-fetch", action="store_true", help="skip git fetch")
    args = ap.parse_args()

    state = load_state()
    root = neo_root()
    skills_root = root / "skills"
    allowlist: dict[str, str] = state.get("synced_skills") or {}
    if not allowlist:
        die("synced_skills is empty in sync-state.json")

    for name in allowlist:
        if name in NEO_OWNED:
            die(f"allowlist collides with neo-owned skill: {name}")

    upstream = ensure_upstream(state, args.upstream, args.no_fetch)
    ref = args.ref or state.get("default_ref") or "origin/main"
    new_sha = resolve_ref(upstream, ref)
    base_sha = state.get("last_synced_commit") or ""

    source_dirs = sorted(set(allowlist.values()))
    theirs_tree = tree_at(upstream, new_sha, source_dirs)
    base_tree = tree_at(upstream, base_sha, source_dirs) if base_sha else {}

    report: dict[str, list[str]] = {
        "add": [],
        "update": [],
        "in-sync": [],
        "local-kept": [],
        "conflict": [],
        "upstream-removed": [],
        "missing-upstream-skill": [],
    }
    writes: list[tuple[Path, bytes]] = []  # (dest path, content)

    for name, source_dir in sorted(allowlist.items()):
        theirs_files = skill_files(theirs_tree, source_dir)
        base_files = skill_files(base_tree, source_dir)
        dest_dir = skills_root / name

        if not theirs_files:
            report["missing-upstream-skill"].append(f"{name} ← {source_dir}")
            continue

        # All paths that appear in any of the three sides.
        rels = set(theirs_files) | set(base_files)
        if dest_dir.exists():
            for p in dest_dir.rglob("*"):
                if p.is_file() and not p.is_symlink():
                    rels.add(str(p.relative_to(dest_dir)))

        for rel in sorted(rels):
            dest = dest_dir / rel
            ours = dest.read_bytes() if dest.is_file() else None
            base = base_files.get(rel)
            theirs = theirs_files.get(rel)
            action = classify(ours, base, theirs)
            label = f"{name}/{rel}"
            report[action].append(label)
            if action in ("add", "update") and theirs is not None:
                writes.append((dest, theirs))

    # Print report
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"== sync-mattpocock [{mode}] ==")
    print(f"upstream: {upstream}")
    print(f"ref:      {ref} → {new_sha[:12]}")
    print(f"baseline: {base_sha[:12] if base_sha else '(none — first sync)'}")
    print()
    for key in ("add", "update", "local-kept", "conflict", "upstream-removed", "missing-upstream-skill"):
        items = report[key]
        if not items:
            continue
        print(f"  {key.upper()} ({len(items)})")
        for item in items:
            print(f"    {item}")
        print()
    print(f"  in-sync: {len(report['in-sync'])} file(s)")
    print(f"  pending writes: {len(writes)} file(s)")

    if report["conflict"]:
        print("\nCONFLICT: resolve by hand, then re-run. Nothing was written.")
        sys.exit(2)
    if report["missing-upstream-skill"]:
        print("\nWARNING: some allowlisted skills are missing upstream — check paths in sync-state.json.")

    if not args.apply:
        print("\nDry run only. Pass --apply to write.")
        return

    for dest, content in writes:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)

    state["last_synced_commit"] = new_sha
    state["last_synced_date"] = datetime.date.today().isoformat()
    # Never persist a machine-local absolute path. The default cache is
    # SKILL_DIR/.upstream-cache; pass --upstream to override per run.
    if state.get("upstream_path") and not Path(state["upstream_path"]).exists():
        state["upstream_path"] = ""
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
    print(f"\nApplied {len(writes)} file(s). Baseline → {new_sha[:12]}")
    print("Next: node scripts/validate-skills.js")


if __name__ == "__main__":
    main()
