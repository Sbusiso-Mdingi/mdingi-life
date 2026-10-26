"""v1.1's model average (research/PROTOCOL_v1.1.md): weights from out-of-sample deviance, and a mixture of paths."""
from __future__ import annotations

import numpy as np

PATHS, REFITS = 5000, 500


def weights(dev: dict[str, float], phi: float) -> dict[str, float]:
    """w ∝ exp(−(D − D_min) / (2 phi)), the out-of-sample quasi-likelihood weight."""
    d = np.array(list(dev.values()))
    w = np.exp(-(d - d.min()) / (2 * phi))
    return dict(zip(dev, w / w.sum()))


def inverse(dev: dict[str, float]) -> dict[str, float]:
    """The sensitivity: weights in proportion to 1 / D."""
    w = 1 / np.array(list(dev.values()))
    return dict(zip(dev, w / w.sum()))


def split(w: dict[str, float], paths: int = PATHS, refits: int = REFITS) -> dict[str, tuple[int, int]]:
    """(paths, refits) per model: round(paths × w), from ceil(refits × share) refits, at least one if any paths.
    Rounding is fixed so the paths add up to `paths`."""
    n = {m: int(round(paths * v)) for m, v in w.items()}
    top = max(w, key=w.get)
    n[top] += paths - sum(n.values())
    return {m: (k, max(int(np.ceil(refits * k / paths)), 1)) for m, k in n.items() if k > 0}
