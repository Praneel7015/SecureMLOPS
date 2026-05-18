from __future__ import annotations

import math
from typing import Iterable


def cosine_distance(a: Iterable[float], b: Iterable[float]) -> float:
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    return 1.0 - (dot / (math.sqrt(norm_a) * math.sqrt(norm_b)))


def z_score(value: float, mean: float, std: float) -> float:
    if std == 0:
        return 0.0
    return (value - mean) / std


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))
