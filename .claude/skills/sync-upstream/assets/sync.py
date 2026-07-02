#!/usr/bin/env python3
"""Sync upstream addyosmani/agent-skills into the neo fork.

Scope: upstream skills/ (except using-agent-skills), hooks/, agents/, references/.
Everything else (docs/, manifests, README) is neo-owned and untouched.

After --apply, scripts/bundle-references.sh re-fans the shared references/ files
into the skills that cite them (the per-skill copies are generated artifacts).

Per-file decision uses a 3-way compare so a neo hand-edit is never clobbered:

    theirs = transform(upstream @ new ref)
    base   = transform(upstream @ last synced commit)
    ours   = the file currently in neo

  ours missing            -> add        (write theirs)
  ours == theirs          -> in sync    (no-op)
  ours == base            -> update     (upstream changed, neo did not -> write theirs)
  theirs == base          -> local kept (neo edited, upstream did not -> keep ours)
  all three differ        -> CONFLICT   (both changed -> report, do NOT overwrite)

Skill-level: skills only in neo (never upstream, never in the baseline) are
neo-local and preserved; skills upstream deleted are reported, never auto-removed.

Default is a dry run. Pass --apply to write add/update files and advance the baseline.
"""

import argparse
import datetime
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
STATE_FILE = SKILL_DIR / "sync-state.json"

SCOPE_DIRS = ["skills", "hooks", "agents", "references"]
EXCLUDED_UPSTREAM_SKILLS = {"using-agent-skills"}  # neo owns the router as using-neo
NEO_OWNED_SKILLS = {"using-neo"}                    # never overwritten / never "removed"

sys.path.insert(0, str(HERE))
from rebrand import residual_brand, transform_text


def run(*args):
    return subprocess.run(args, capture_output=True, text=True)


def die(msg):
    sys.stderr.write("error: %s\n" % msg)
    sys.exit(1)


def load_state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def neo_root():
    r = run("git", "-C", str(SKILL_DIR), "rev-parse", "--show-toplevel")
    if r.returncode != 0:
        die("not inside a git repo: %s" % r.stderr.strip())
    return Path(r.stdout.strip())


def tree_bytes(upstream, ref):
    """{relpath: raw bytes} for in-scope files at ref ({} if ref is unresolvable)."""
    r = subprocess.run(
        ["git", "-C", upstream, "archive", ref, "--"] + SCOPE_DIRS, capture_output=True
    )
    if r.returncode != 0:
        return {}
    tf = tarfile.open(fileobj=io.BytesIO(r.stdout))
    return {m.name: tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()}


def xform(raw):
    """(transformed bytes, residual-brand hits). Binary content is copied verbatim."""
    try:
        text = transform_text(raw.decode("utf-8"))
        return text.encode("utf-8"), residual_brand(text)
    except UnicodeDecodeError:
        return raw, []


def main():
    ap = argparse.ArgumentParser(description="Sync upstream agent-skills into neo.")
    ap.add_argument("--upstream", help="path to a local addyosmani/agent-skills clone")
    ap.add_argument("--ref", help="upstream ref (default: state.default_ref or origin/main)")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--no-fetch", action="store_true", help="skip 'git fetch' on the clone")
    args = ap.parse_args()

    state = load_state()
    root = neo_root()
    upstream = args.upstream or state.get("upstream_path")
    if not upstream or not Path(upstream).exists():
        die("upstream clone not found (set --upstream or sync-state.json:upstream_path)")
    ref = args.ref or state.get("default_ref", "origin/main")
    baseline = state.get("last_synced_commit", "")

    if not args.no_fetch:
        run("git", "-C", upstream, "fetch", "--quiet", "origin")

    rev = run("git", "-C", upstream, "rev-parse", ref)
    if rev.returncode != 0:
        die("cannot resolve ref %r in %s" % (ref, upstream))
    commit = rev.stdout.strip()

    new_tree = tree_bytes(upstream, ref)
    base_tree = tree_bytes(upstream, baseline) if baseline else {}
    if baseline and not base_tree:
        sys.stderr.write(
            "warning: baseline %s not found in clone; neo edits will surface as CONFLICT\n"
            % baseline[:12]
        )

    adds, updates, locals_, conflicts, landmines = [], [], [], [], []
    upstream_skills = set()

    for rel in sorted(new_tree):
        parts = rel.split("/")
        if parts[0] == "skills" and len(parts) > 1:
            if parts[1] in EXCLUDED_UPSTREAM_SKILLS:
                continue  # neo owns using-neo; never sync using-agent-skills
            upstream_skills.add(parts[1])

        theirs, hits = xform(new_tree[rel])
        base = xform(base_tree[rel])[0] if rel in base_tree else None
        dest = root / rel
        ours = dest.read_bytes() if dest.exists() else None

        if ours is None:
            adds.append(rel)
        elif ours == theirs:
            continue  # already in sync
        elif ours == base:
            updates.append(rel)
        elif theirs == base:
            locals_.append(rel)  # neo edited, upstream did not -> keep ours
            continue
        else:
            conflicts.append(rel)  # both changed -> manual merge
            continue

        if hits:
            landmines.append((rel, sorted(set(hits))))
        if args.apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(theirs)

    neo_skills = {p.name for p in (root / "skills").iterdir() if p.is_dir()}
    synced = set(state.get("synced_skills", []))
    removed = sorted((synced - upstream_skills) - NEO_OWNED_SKILLS)
    neo_local = sorted(
        neo_skills - upstream_skills - synced - NEO_OWNED_SKILLS - EXCLUDED_UPSTREAM_SKILLS
    )
    to_apply = len(adds) + len(updates)

    print("upstream: %s @ %s" % (state.get("upstream_repo", upstream), commit[:12]))
    print("baseline: %s" % (baseline[:12] or "(none)"))
    print("mode:     %s" % ("APPLY" if args.apply else "dry-run"))
    print("-" * 60)
    if to_apply:
        for rel in adds:
            print("  add     %s" % rel)
        for rel in updates:
            print("  update  %s" % rel)
    else:
        print("changes to apply: none (in sync / idempotent)")
    if locals_:
        print("neo-owned edits kept (%d): %s" % (len(locals_), ", ".join(locals_)))
    if neo_local:
        print("neo-local skills preserved (%d): %s" % (len(neo_local), ", ".join(neo_local)))
    if conflicts:
        print("CONFLICT - both neo & upstream changed (merge by hand, NOT overwritten):")
        for rel in conflicts:
            print("  %s" % rel)
    if removed:
        print("REVIEW - removed upstream (kept, not deleted): %s" % ", ".join(removed))
    if landmines:
        print("REVIEW - residual brand tokens (novel pattern -> add a rule to rebrand.py):")
        for rel, toks in landmines:
            print("  %s -> %s" % (rel, ", ".join(toks)))

    if args.apply:
        state["last_synced_commit"] = commit
        state["last_synced_date"] = datetime.date.today().isoformat()
        state["synced_skills"] = sorted(upstream_skills)
        STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
        print("-" * 60)
        print("applied %d file(s); baseline advanced -> %s" % (to_apply, commit[:12]))
        bundle = run("bash", str(root / "scripts" / "bundle-references.sh"))
        if bundle.returncode != 0:
            die("bundle-references.sh failed: %s" % bundle.stderr.strip())
        sys.stdout.write(bundle.stdout)

    return 2 if (conflicts or landmines) else 0


if __name__ == "__main__":
    sys.exit(main())
