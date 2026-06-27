"""Discrete semantic entropy and union-find clustering for SECV.

Pure functions with no I/O — all exhaustively unit-testable.
"""
from __future__ import annotations
import math
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crucible.verify.entailment import EntailmentOracle


class UnionFind:
    def __init__(self, n: int) -> None:
        self._parent = list(range(n))

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]  # path halving
            x = self._parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        self._parent[self.find(x)] = self.find(y)

    def clusters(self) -> list[list[int]]:
        groups: dict[int, list[int]] = defaultdict(list)
        for i in range(len(self._parent)):
            groups[self.find(i)].append(i)
        return list(groups.values())


def cluster_by_bidirectional_entailment(
    propositions: list[str],
    oracle: "EntailmentOracle",
) -> list[list[int]]:
    """i and j co-cluster iff oracle(i⊨j) AND oracle(j⊨i). O(n²) pairs."""
    n = len(propositions)
    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if (
                oracle.entails(propositions[i], propositions[j])
                and oracle.entails(propositions[j], propositions[i])
            ):
                uf.union(i, j)
    return uf.clusters()


def discrete_semantic_entropy(
    cluster_sizes: list[int],
    M: int,
) -> tuple[float, float, float]:
    """Returns (se, se_norm, confidence).

    se_norm = SE / log(M) ∈ [0, 1]; confidence = 1 − se_norm.
    M ≤ 1: trivially certain → (0, 0, 1).
    """
    if M <= 1:
        return 0.0, 0.0, 1.0
    se = -sum((n / M) * math.log(n / M) for n in cluster_sizes if n > 0)
    se_norm = se / math.log(M)
    return se, se_norm, max(0.0, min(1.0, 1.0 - se_norm))
