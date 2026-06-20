#!/usr/bin/env python3
"""
deref.py — emit a DEREFERENCED view of an openapi-doc spec
           (bruno/openapi.yaml  →  bruno/openapi.deref.yaml).
Zero install beyond PyYAML: pure Python 3 stdlib + PyYAML. A mechanical companion to the
openapi-doc skill — NOT a verifier.

WHY THIS EXISTS
  openapi-doc's canonical spec wires operations and schemas with internal $ref
  (#/components/...). Some viewers (Bruno API Designer, Swagger UI) do not expand internal
  $ref when rendering, so fields never show. This emits a fully-inlined ("dereferenced")
  copy for those viewers. The canonical spec stays the single source of truth — verified by
  speccheck.py + the fresh-eyes pass — and the whole downstream chain (open-collection,
  confluence-api-doc) keeps reading it. This file is a DERIVED VIEW: its correctness is
  INHERITED from the canonical, so it is never independently verified.

WHAT IT DOES
  • Replaces every internal $ref node ({"$ref": "#/..."}) with a deep copy of its target,
    recursively. Dereference ONLY — structure is preserved: allOf stays allOf (its $ref
    members inlined, NOT merged), and x-error-catalog / other extensions pass through.
  • When no $ref remains, the now-redundant components.schemas + components.responses are
    dropped (securitySchemes stay — `security` references them by NAME, not $ref).
  • Cycle guard: a $ref pointing back to an ancestor still being expanded (a recursive type)
    is LEFT in place and reported; components are then kept so it still resolves. Output is
    always finite + valid.
  • Self-sanity (transform integrity, NOT semantic re-verification): the emitted YAML
    re-parses; the only $ref left is the recorded cycle/unresolved set; the paths keys +
    per-path operation set match the canonical; openapi/info/servers/tags are unchanged.
    Any failure → exit 1 (a transform bug, never a content judgement).

  No PyYAML → prints a notice and exits 0 WITHOUT writing (mirrors speccheck.py's
  degradation); the canonical spec + downstream chain are unaffected.

USAGE
  python3 deref.py bruno/openapi.yaml                              # → bruno/openapi.deref.yaml
  python3 deref.py bruno/openapi.yaml -o path/to/out.yaml          # explicit output
  python3 deref.py bruno/openapi.yaml --check                      # don't write; assert the
                                                                   #   on-disk view is in sync
Exit code: 0 = view written / in sync / skipped-no-PyYAML;
           1 = transform-or-sanity failure, or (with --check) the view is missing/stale.
"""
import sys, copy, pathlib

try:
    import yaml                         # PyYAML — required to parse + dump; absent ⇒ skip
    HAVE_YAML = True
except Exception:
    HAVE_YAML = False

HTTP_METHODS = {'get', 'put', 'post', 'delete', 'patch', 'options', 'head', 'trace'}


def parse_args(argv):
    inp = out = None
    check = False
    it = iter(argv)
    for a in it:
        if a in ('-o', '--output'):
            out = next(it, None)
        elif a.startswith('--output='):
            out = a.split('=', 1)[1]
        elif a == '--check':
            check = True
        elif a in ('-h', '--help'):
            print(__doc__)
            sys.exit(0)
        elif inp is None:
            inp = a
        # extra positionals ignored
    return inp, out, check


def default_out(inp):
    """bruno/openapi.yaml → bruno/openapi.deref.yaml (insert '.deref' before the suffix)."""
    return inp.with_name(inp.stem + '.deref' + inp.suffix)


def resolve_pointer(root, ref):
    """'#/components/schemas/Foo' → the target node, or None if it does not resolve."""
    node = root
    for raw in ref[2:].split('/'):
        key = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return None
    return node


def leave(state, bucket, ref):
    """Record a $ref that can't be inlined (external / recursive / dangling) and leave it
       in place. Keeps `state['left']` (occurrence count) in lock-step with the refs that
       actually remain in the output — the integrity self-check relies on that equality."""
    state['left'] += 1
    state[bucket].add(ref)
    return {'$ref': ref}


def inline(node, root, stack, state):
    """A deep, dereferenced copy of `node`. Never mutates its input (returns fresh
       dicts/lists). `stack` = the internal $refs currently being expanded on this DFS
       path (cycle guard). `state` accumulates leftovers: counter `left`, sets `cyclic`
       and `unresolved`."""
    if isinstance(node, dict):
        ref = node.get('$ref')
        if isinstance(ref, str):
            if not ref.startswith('#/'):
                return leave(state, 'unresolved', ref)    # external file-path ref — cannot inline
            if ref in stack:
                return leave(state, 'cyclic', ref)        # recursive type — leave at the cycle
            target = resolve_pointer(root, ref)
            if target is None:
                return leave(state, 'unresolved', ref)    # dangling — canonical's L1 owns this
            stack.append(ref)
            result = inline(copy.deepcopy(target), root, stack, state)
            stack.pop()
            siblings = {k: v for k, v in node.items() if k != '$ref'}
            if siblings and isinstance(result, dict):     # OpenAPI 3.1 $ref-with-siblings
                for k, v in siblings.items():
                    result[k] = inline(v, root, stack, state)
            return result
        return {k: inline(v, root, stack, state) for k, v in node.items()}
    if isinstance(node, list):
        return [inline(v, root, stack, state) for v in node]
    return node


def count_refs(node):
    n = 0
    if isinstance(node, dict):
        if isinstance(node.get('$ref'), str):
            n += 1
        for v in node.values():
            n += count_refs(v)
    elif isinstance(node, list):
        for v in node:
            n += count_refs(v)
    return n


def fail(msg):
    print(f"✗ deref FAILED — {msg}")
    sys.exit(1)


def build_view(doc):
    """Return (inlined_doc, state). Drops redundant components when fully dereferenced;
       keeps them (so a leftover ref still resolves) when anything was left in place."""
    state = {'left': 0, 'cyclic': set(), 'unresolved': set()}
    out = inline(doc, doc, [], state)
    if state['left'] == 0:
        comps = out.get('components')
        if isinstance(comps, dict):
            # Every $ref is inlined now, so every component bucket is redundant EXCEPT
            # securitySchemes (which `security` references by name, not via $ref).
            for k in [k for k in comps if k != 'securitySchemes']:
                comps.pop(k)
            if not comps:
                out.pop('components', None)
    return out, state


def assert_integrity(doc, out, state):
    remaining = count_refs(out)
    if remaining != state['left']:
        fail(f"{remaining} $ref remain but {state['left']} expected — inlining incomplete")
    src_paths = doc.get('paths') or {}
    out_paths = out.get('paths') or {}
    if set(src_paths) != set(out_paths):
        fail("paths keys differ between canonical and view")
    for k, item in src_paths.items():
        a = {m for m in item if m in HTTP_METHODS} if isinstance(item, dict) else set()
        b = ({m for m in out_paths[k] if m in HTTP_METHODS}
             if isinstance(out_paths.get(k), dict) else set())
        if a != b:
            fail(f"operations on path {k!r} differ")
    for key in ('openapi', 'info', 'paths'):
        if key not in out:
            fail(f"top-level {key!r} missing from the view")
    for key in ('openapi', 'info', 'servers', 'tags'):
        if key in doc and out.get(key) != doc.get(key):
            fail(f"top-level {key!r} changed during dereference")


def main():
    inp, out, check = parse_args(sys.argv[1:])

    if not HAVE_YAML:
        print("deref: PyYAML not installed — deref view skipped (canonical + chain unaffected)")
        sys.exit(0)
    if not inp:
        print("deref: no input spec given\n"
              "usage: python3 deref.py bruno/openapi.yaml [-o out.yaml] [--check]")
        sys.exit(0)

    inpath = pathlib.Path(inp)
    if not inpath.exists():
        print(f"deref: {inpath} not found — nothing to dereference")
        sys.exit(0)
    outpath = pathlib.Path(out) if out else default_out(inpath)

    try:
        doc = yaml.safe_load(inpath.read_text())
    except Exception as e:
        fail(f"cannot parse {inpath}: {e}")
    if not isinstance(doc, dict):
        fail(f"{inpath} is not a YAML mapping")

    view, state = build_view(doc)
    assert_integrity(doc, view, state)

    text = yaml.safe_dump(view, sort_keys=False, default_flow_style=False,
                          allow_unicode=True, width=10 ** 9)
    try:
        yaml.safe_load(text)                              # the emitted view must re-parse
    except Exception as e:
        fail(f"emitted YAML does not parse: {e}")

    def annotate(line):
        if state['cyclic']:
            names = ', '.join(sorted(r.split('/')[-1] for r in state['cyclic']))
            line += f"; kept {len(state['cyclic'])} recursive $ref ({names})"
        if state['unresolved']:
            refs = ', '.join(sorted(state['unresolved']))
            line += f"; WARNING {len(state['unresolved'])} unresolved $ref left ({refs})"
        return line

    if check:
        if not outpath.exists():
            print(f"✗ deref view {outpath} missing — run deref to generate")
            sys.exit(1)
        if outpath.read_text() != text:
            print(f"✗ deref view {outpath} is STALE — re-generate (canonical changed)")
            sys.exit(1)
        print(annotate(f"✓ deref view {outpath} in sync"))
        sys.exit(0)

    outpath.write_text(text)
    print(annotate(f"✓ {outpath} — dereferenced view written"))
    sys.exit(0)


if __name__ == '__main__':
    main()
