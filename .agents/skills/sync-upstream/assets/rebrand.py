#!/usr/bin/env python3
"""Deterministic agent-skills -> neo rebrand transform.

Single source of truth for the text transformation applied when syncing
upstream addyosmani/agent-skills content into the neo fork. Applied to the
CONTENT of in-scope files (skills/, hooks/, agents/, references/).

Keep this in lockstep with the manual rebrand: `sync.py --dry-run` against the
recorded baseline must report zero changes (the idempotent self-test).
"""

import re

# External / verbatim strings shielded from transformation (third-party refs).
# Shielded before the rules run, restored afterwards, so an upstream URL slug
# that happens to contain "agent-skills" is never corrupted.
PROTECT = [
    "https://www.linkedin.com/pulse/superpowers-vs-agent-skills-faster-shipping-safer-reasoning-om-mishra-dzakf/",
]

# Ordered literal replacements (case-sensitive), applied top-to-bottom.
# ORDER MATTERS: the repo/URL/namespace rules run before the generic brand rule
# so they are not clobbered by it (e.g. addyosmani/agent-skills must map to the
# repo before the bare "agent-skills" -> "neo" rule sees it).
RULES = [
    ("addyosmani/agent-skills", "witooh/neo-plugin"),  # upstream repo refs & URLs
    ("agent-skills@addy-agent-skills", "neo@neo"),      # plugin install id
    ("addy-agent-skills", "neo"),                       # marketplace name (residual)
    ("agent-skills", "neo"),                            # brand, `agent-skills:` namespace, using-agent-skills -> using-neo (substring)
    ("Agent Skills", "Neo"),                            # Title-Case product prose
]

# Brand tokens that must NOT survive a transform. Case-sensitive by design:
# external "Agent-Skills" citations and lowercase "agent skills" (the generic
# concept) are intentionally left alone.
_RESIDUAL = re.compile(r"addyosmani|agent-skills")


def transform_text(text):
    """Apply the ordered rebrand rules, shielding protected strings."""
    holds = {}
    for i, s in enumerate(PROTECT):
        if s in text:
            token = "\x00P%d\x00" % i
            holds[token] = s
            text = text.replace(s, token)
    for old, new in RULES:
        text = text.replace(old, new)
    for token, s in holds.items():
        text = text.replace(token, s)
    return text


def residual_brand(text):
    """Brand tokens left after transform (excluding shielded strings).

    A non-empty result means a novel pattern the RULES did not cover -> the
    sync must surface it for human review rather than ship a half-rebranded file.
    """
    t = text
    for s in PROTECT:
        t = t.replace(s, "")
    return _RESIDUAL.findall(t)


if __name__ == "__main__":
    import sys

    sys.stdout.write(transform_text(sys.stdin.read()))
