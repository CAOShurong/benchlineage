"""GUM-inspired uncertainty budget calculations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Component:
    name: str
    standard_uncertainty: float
    sensitivity: float = 1.0
    distribution: str = "normal"
    degrees_of_freedom: float = math.inf
    source: str = ""

    def contribution(self) -> float:
        return abs(self.standard_uncertainty * self.sensitivity)


def component_from_limit(
    name: str,
    limit: float,
    *,
    distribution: str,
    sensitivity: float = 1.0,
    source: str = "",
) -> Component:
    if limit < 0 or not math.isfinite(limit):
        raise ValueError("limit must be finite and non-negative")
    divisors = {
        "normal": 2.0,
        "rectangular": math.sqrt(3.0),
        "triangular": math.sqrt(6.0),
    }
    if distribution not in divisors:
        raise ValueError(f"unsupported distribution: {distribution}")
    return Component(
        name=name,
        standard_uncertainty=limit / divisors[distribution],
        sensitivity=sensitivity,
        distribution=distribution,
        source=source,
    )


def combine(components: Sequence[Component], *, coverage_factor: float = 2.0) -> dict:
    if not components:
        raise ValueError("an uncertainty budget needs at least one component")
    if coverage_factor <= 0 or not math.isfinite(coverage_factor):
        raise ValueError("coverage factor must be finite and positive")
    contributions = [component.contribution() for component in components]
    combined = math.sqrt(sum(value * value for value in contributions))
    variance = combined * combined
    shares = [value * value / variance if variance else 0.0 for value in contributions]
    rows = []
    for component, contribution, share in zip(components, contributions, shares, strict=True):
        rows.append(
            {
                "name": component.name,
                "standard_uncertainty": component.standard_uncertainty,
                "sensitivity": component.sensitivity,
                "contribution": contribution,
                "variance_share": share,
                "distribution": component.distribution,
                "source": component.source,
            }
        )
    return {
        "components": rows,
        "combined_standard_uncertainty": combined,
        "coverage_factor": coverage_factor,
        "expanded_uncertainty": combined * coverage_factor,
    }


def from_records(records: Sequence[dict], *, coverage_factor: float = 2.0) -> dict:
    components = []
    for record in records:
        if "standard_uncertainty" in record:
            component = Component(
                name=str(record["name"]),
                standard_uncertainty=float(record["standard_uncertainty"]),
                sensitivity=float(record.get("sensitivity", 1.0)),
                distribution=str(record.get("distribution", "normal")),
                degrees_of_freedom=float(record.get("degrees_of_freedom", math.inf)),
                source=str(record.get("source", "")),
            )
        else:
            component = component_from_limit(
                str(record["name"]),
                float(record["limit"]),
                distribution=str(record["distribution"]),
                sensitivity=float(record.get("sensitivity", 1.0)),
                source=str(record.get("source", "")),
            )
        components.append(component)
    return combine(components, coverage_factor=coverage_factor)
