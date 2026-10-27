"""Guard: nothing that fits a model runs until its protocol (research/PROTOCOL.md for v1, PROTOCOL_v2.md for v2, PROTOCOL_v3.md for v3,
PROTOCOL_v4.md for v4, PROTOCOL_v1.1.md for v1.1, PROTOCOL_v1.2.md for v1.2, PROTOCOL_v1.3.md for v1.3, PROTOCOL_v1.4.md for v1.4, PROTOCOL_v5.md for v5) is frozen at a commit."""
from __future__ import annotations

import re
import subprocess
import sys

from mdingilife.data import ROOT

PROTOCOL = ROOT / "research" / "PROTOCOL.md"
PROTOCOL_V2 = ROOT / "research" / "PROTOCOL_v2.md"
PROTOCOL_V3 = ROOT / "research" / "PROTOCOL_v3.md"
PROTOCOL_V4 = ROOT / "research" / "PROTOCOL_v4.md"
PROTOCOL_V1_1 = ROOT / "research" / "PROTOCOL_v1.1.md"
PROTOCOL_V1_2 = ROOT / "research" / "PROTOCOL_v1.2.md"
PROTOCOL_V1_3 = ROOT / "research" / "PROTOCOL_v1.3.md"
PROTOCOL_V1_4 = ROOT / "research" / "PROTOCOL_v1.4.md"
PROTOCOL_V5 = ROOT / "research" / "PROTOCOL_v5.md"
# the hash may be followed by a bracketed note, as in v1.4's "(27 October 2026)"
LINE = re.compile(r"^Frozen at commit: `?([0-9a-f]{7,40})`?(?:\s+\([^)]*\))?\s*$", re.M)


def frozen_hash(path=None) -> str | None:
    m = LINE.search((path or PROTOCOL).read_text())
    if not m:
        return None
    ok = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{m.group(1)}^{{commit}}"],
                        capture_output=True).returncode == 0
    return m.group(1) if ok else None


def require_frozen(path=None) -> str:
    h = frozen_hash(path)
    if h is None:
        sys.exit(f"research/{(path or PROTOCOL).name} is not frozen: commit it and record the hash on its "
                 "'Frozen at commit:' line before fitting anything.")
    return h
