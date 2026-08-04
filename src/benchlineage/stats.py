"""Dependency-free numerical summaries used by bench analyses."""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence


def require_finite(values: Sequence[float], *, minimum: int = 1) -> list[float]:
    clean = [float(value) for value in values]
    if len(clean) < minimum:
        raise ValueError(f"at least {minimum} finite observations are required")
    if not all(math.isfinite(value) for value in clean):
        raise ValueError("observations must be finite")
    return clean


def summary(values: Sequence[float]) -> dict[str, float | int]:
    clean = require_finite(values)
    count = len(clean)
    mean = statistics.fmean(clean)
    standard_deviation = statistics.stdev(clean) if count > 1 else 0.0
    standard_error = standard_deviation / math.sqrt(count) if count > 1 else 0.0
    return {
        "count": count,
        "mean": mean,
        "median": statistics.median(clean),
        "minimum": min(clean),
        "maximum": max(clean),
        "standard_deviation": standard_deviation,
        "standard_error": standard_error,
        "relative_standard_deviation": (
            abs(standard_deviation / mean) if mean != 0.0 else math.inf
        ),
    }


def linear_regression(x_values: Sequence[float], y_values: Sequence[float]) -> dict[str, float]:
    x = require_finite(x_values, minimum=2)
    y = require_finite(y_values, minimum=2)
    if len(x) != len(y):
        raise ValueError("x and y must contain the same number of observations")
    x_mean = statistics.fmean(x)
    y_mean = statistics.fmean(y)
    sxx = sum((value - x_mean) ** 2 for value in x)
    if sxx == 0.0:
        raise ValueError("x observations must not all be equal")
    sxy = sum((left - x_mean) * (right - y_mean) for left, right in zip(x, y, strict=True))
    slope = sxy / sxx
    intercept = y_mean - slope * x_mean
    predictions = [intercept + slope * value for value in x]
    residuals = [observed - predicted for observed, predicted in zip(y, predictions, strict=True)]
    sse = sum(value * value for value in residuals)
    syy = sum((value - y_mean) ** 2 for value in y)
    r_squared = 1.0 - sse / syy if syy > 0 else 1.0
    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_squared,
        "rmse": math.sqrt(sse / len(x)),
    }


def interpolate_crossing(
    x_values: Sequence[float], y_values: Sequence[float], target: float
) -> float | None:
    x = require_finite(x_values, minimum=2)
    y = require_finite(y_values, minimum=2)
    if len(x) != len(y):
        raise ValueError("x and y must contain the same number of observations")
    for left in range(len(x) - 1):
        y0, y1 = y[left], y[left + 1]
        if (y0 - target) * (y1 - target) > 0:
            continue
        if y0 == y1:
            return x[left]
        fraction = (target - y0) / (y1 - y0)
        return x[left] + fraction * (x[left + 1] - x[left])
    return None
