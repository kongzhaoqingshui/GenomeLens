"""Pure-Python fallback for jcvi.assembly.chic.

This module mirrors the API of the Cython extension so that the engine can run
in ``core`` mode when the compiled extension is not available. It is slower and
intended only as a graceful degradation path.
"""

from __future__ import annotations

import numpy as np


LIMIT = 10_000_000
BB = 12
GR = (
    5778,
    9349,
    15127,
    24476,
    39603,
    64079,
    103682,
    167761,
    271443,
    439204,
    710647,
    1149851,
)


def score_evaluate_M(tour, tour_sizes=None, tour_M=None):
    """Python version of chic.score_evaluate_M."""

    sizes_oo = np.array([tour_sizes[x] for x in tour])
    sizes_cum = np.cumsum(sizes_oo) - sizes_oo // 2
    s = 0.0
    size = len(tour)
    for ia in range(size):
        a = tour[ia]
        for ib in range(ia + 1, size):
            b = tour[ib]
            links = tour_M[a, b]
            if links == 0:
                continue
            dist = sizes_cum[ib] - sizes_cum[ia]
            if dist > LIMIT:
                break
            s += links / dist
    return (s,)


def score_evaluate_P(tour, tour_sizes=None, tour_P=None):
    """Python version of chic.score_evaluate_P."""

    sizes_oo = np.array([tour_sizes[x] for x in tour])
    sizes_cum = np.cumsum(sizes_oo)
    s = 0.0
    size = len(tour)
    for ia in range(size):
        a = tour[ia]
        for ib in range(ia + 1, size):
            b = tour[ib]
            dist = sizes_cum[ib - 1] - sizes_cum[ia]
            if dist > LIMIT:
                break
            c = tour_P[a, b, 0]
            if c == 0:
                continue
            s += c / (tour_P[a, b, 1] + dist)
    return (s,)


def score_evaluate_Q(tour, tour_sizes=None, tour_Q=None):
    """Python version of chic.score_evaluate_Q."""

    sizes_oo = np.array([tour_sizes[x] for x in tour])
    sizes_cum = np.cumsum(sizes_oo)
    s = 0.0
    size = len(tour)
    for ia in range(size):
        a = tour[ia]
        for ib in range(ia + 1, size):
            b = tour[ib]
            if tour_Q[a, b, 0] == -1:
                continue
            dist = sizes_cum[ib - 1] - sizes_cum[ia]
            if dist > LIMIT:
                break
            for ic in range(BB):
                c = tour_Q[a, b, ic]
                s += c / (GR[ic] + dist)
    return (s,)
