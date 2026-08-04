"""Small, explicit unit registry for common EE bench measurements."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Unit:
    symbol: str
    dimension: str
    scale: float
    offset: float = 0.0


_UNITS = {
    "1": Unit("1", "dimensionless", 1.0),
    "%": Unit("%", "dimensionless", 0.01),
    "v": Unit("V", "voltage", 1.0),
    "mv": Unit("mV", "voltage", 1e-3),
    "uv": Unit("uV", "voltage", 1e-6),
    "kv": Unit("kV", "voltage", 1e3),
    "a": Unit("A", "current", 1.0),
    "ma": Unit("mA", "current", 1e-3),
    "ua": Unit("uA", "current", 1e-6),
    "ohm": Unit("ohm", "resistance", 1.0),
    "kohm": Unit("kohm", "resistance", 1e3),
    "mohm": Unit("Mohm", "resistance", 1e6),
    "hz": Unit("Hz", "frequency", 1.0),
    "khz": Unit("kHz", "frequency", 1e3),
    "mhz": Unit("MHz", "frequency", 1e6),
    "ghz": Unit("GHz", "frequency", 1e9),
    "s": Unit("s", "time", 1.0),
    "ms": Unit("ms", "time", 1e-3),
    "us": Unit("us", "time", 1e-6),
    "ns": Unit("ns", "time", 1e-9),
    "w": Unit("W", "power", 1.0),
    "mw": Unit("mW", "power", 1e-3),
    "kw": Unit("kW", "power", 1e3),
    "j": Unit("J", "energy", 1.0),
    "mj": Unit("mJ", "energy", 1e-3),
    "f": Unit("F", "capacitance", 1.0),
    "uf": Unit("uF", "capacitance", 1e-6),
    "nf": Unit("nF", "capacitance", 1e-9),
    "pf": Unit("pF", "capacitance", 1e-12),
    "h": Unit("H", "inductance", 1.0),
    "mh": Unit("mH", "inductance", 1e-3),
    "uh": Unit("uH", "inductance", 1e-6),
    "deg": Unit("deg", "angle", 1.0),
    "rad": Unit("rad", "angle", 57.29577951308232),
    "degc": Unit("degC", "temperature", 1.0),
    "db": Unit("dB", "log_ratio", 1.0),
    "dbm": Unit("dBm", "log_power", 1.0),
}

_ALIASES = {
    "ω": "ohm",
    "Ω": "ohm",
    "kω": "kohm",
    "kΩ": "kohm",
    "µv": "uv",
    "μv": "uv",
    "µa": "ua",
    "μa": "ua",
    "µs": "us",
    "μs": "us",
    "µf": "uf",
    "μf": "uf",
    "µh": "uh",
    "μh": "uh",
    "°": "deg",
    "°c": "degc",
}


def normalize_unit(symbol: str) -> str:
    key = symbol.strip()
    key = _ALIASES.get(key, _ALIASES.get(key.lower(), key.lower()))
    if key not in _UNITS:
        raise ValueError(f"unknown unit: {symbol}")
    return _UNITS[key].symbol


def unit_definition(symbol: str) -> Unit:
    normalized = normalize_unit(symbol)
    for unit in _UNITS.values():
        if unit.symbol == normalized:
            return unit
    raise ValueError(f"unknown unit: {symbol}")


def convert(value: float, source: str, target: str) -> float:
    source_unit = unit_definition(source)
    target_unit = unit_definition(target)
    if source_unit.dimension != target_unit.dimension:
        raise ValueError(
            f"incompatible units: {source_unit.symbol} ({source_unit.dimension}) and "
            f"{target_unit.symbol} ({target_unit.dimension})"
        )
    base = (value + source_unit.offset) * source_unit.scale
    return base / target_unit.scale - target_unit.offset


def compatible(source: str, target: str) -> bool:
    try:
        return unit_definition(source).dimension == unit_definition(target).dimension
    except ValueError:
        return False


def registry() -> list[dict[str, str | float]]:
    return [
        {"symbol": unit.symbol, "dimension": unit.dimension, "scale": unit.scale}
        for unit in sorted(_UNITS.values(), key=lambda item: (item.dimension, item.scale))
    ]
