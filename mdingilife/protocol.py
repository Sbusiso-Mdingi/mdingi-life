"""Guard: nothing that fits a model runs until research/PROTOCOL.md is frozen at a commit."""
from __future__ import annotations

import re
import subprocess
import sys

from mdingilife.data import ROOT

PROTOCOL = ROOT / "research" / "PROTOCOL.md"
LINE = re.compile(r"^Frozen at commit: `?([0-9a-f]{7,40})`?\s*$", re.M)


def frozen_hash() -> str | None:
    m = LINE.search(PROTOCOL.read_text())
    if not m:
        return None
    ok = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{m.group(1)}^{{commit}}"],
                        capture_output=True).returncode == 0
    return m.group(1) if ok else None


def require_frozen() -> str:
    h = frozen_hash()
    if h is None:
        sys.exit("research/PROTOCOL.md is not frozen: commit it and record the hash on its "
                 "'Frozen at commit:' line before fitting anything.")
    return h
