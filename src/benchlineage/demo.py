"""Deterministic demonstration workspace with realistic EE measurements."""

from __future__ import annotations

import csv
import datetime as dt
import math
import random
import shutil
from pathlib import Path

from .analysis import analyze_run
from .io import read_json, write_json
from .provenance import seal_workspace
from .report import build_report
from .workspace import Workspace


def _portable_numbers(value):
    """Remove insignificant libm/statistics drift from the committed demo fixture."""
    if isinstance(value, float):
        if not math.isfinite(value):
            return value
        return float(f"{value:.10g}")
    if isinstance(value, list):
        return [_portable_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: _portable_numbers(item) for key, item in value.items()}
    return value


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _frequency_rows(
    *,
    resistance: float,
    capacitance: float,
    seed: int,
    points: int = 41,
) -> list[dict[str, float]]:
    randomizer = random.Random(seed)
    rows = []
    start, stop = math.log10(20.0), math.log10(100_000.0)
    for index in range(points):
        frequency = 10 ** (start + index * (stop - start) / (points - 1))
        omega_rc = 2.0 * math.pi * frequency * resistance * capacitance
        gain = 1.0 / math.sqrt(1.0 + omega_rc * omega_rc)
        phase = -math.degrees(math.atan(omega_rc))
        vin = 1.0 + randomizer.gauss(0.0, 0.0015)
        vout = vin * gain * (1.0 + randomizer.gauss(0.0, 0.003))
        rows.append(
            {
                "frequency_hz": round(frequency, 6),
                "vin_v": round(vin, 7),
                "vout_v": round(vout, 7),
                "phase_deg": round(phase + randomizer.gauss(0.0, 0.18), 5),
            }
        )
    return rows


def _efficiency_rows(seed: int) -> list[dict[str, float]]:
    randomizer = random.Random(seed)
    rows = []
    for load in (100, 68, 47, 33, 22, 15, 10, 8.2, 6.8, 5.6):
        output_voltage = 5.02 - 0.055 * (10 / load) + randomizer.gauss(0, 0.006)
        output_current = output_voltage / load
        efficiency = 0.73 + 0.19 * (1.0 - math.exp(-output_current / 0.12))
        efficiency -= max(0.0, output_current - 0.72) ** 2 * 0.08
        input_power = output_voltage * output_current / efficiency
        input_voltage = 12.0 + randomizer.gauss(0, 0.008)
        rows.append(
            {
                "load_ohm": load,
                "vin_v": round(input_voltage, 6),
                "iin_a": round(input_power / input_voltage, 7),
                "vout_v": round(output_voltage, 6),
                "iout_a": round(output_current, 7),
            }
        )
    return rows


def build_demo(
    destination: str | Path,
    *,
    seed: int = 20260804,
    replace: bool = False,
    build_html: bool = True,
) -> Workspace:
    root = Path(destination)
    if root.exists() and any(root.iterdir()):
        if not replace:
            raise FileExistsError(f"demo destination is not empty: {root}")
        shutil.rmtree(root)
    bench = Workspace(root)
    bench.initialize(
        title="Power-conversion and RC-filter characterization",
        owner="Shurong Cao",
    )
    bench.add_instrument(
        instrument_id="scope-01",
        kind="oscilloscope",
        manufacturer="Acme Metrology",
        model="WaveView 2000",
        serial="SYN-SCOPE-0042",
        asset_tag="EE-DEMO-001",
        notes="Synthetic identity used only in the public demonstration.",
    )
    bench.add_instrument(
        instrument_id="dmm-01",
        kind="digital multimeter",
        manufacturer="Acme Metrology",
        model="CountPro 6.5",
        serial="SYN-DMM-0017",
        asset_tag="EE-DEMO-002",
        notes="Synthetic identity used only in the public demonstration.",
    )
    bench.add_instrument(
        instrument_id="source-01",
        kind="function generator and DC source",
        manufacturer="Acme Metrology",
        model="SourceBox 80",
        serial="SYN-SRC-0009",
        asset_tag="EE-DEMO-003",
        notes="Synthetic identity used only in the public demonstration.",
    )
    performed = "2026-01-15T09:00:00+00:00"
    due = "2027-01-15T09:00:00+00:00"
    for instrument, uncertainty, unit in (
        ("scope-01", 0.0025, "V"),
        ("dmm-01", 0.0008, "V"),
        ("source-01", 0.0015, "V"),
    ):
        bench.add_calibration(
            calibration_id=f"cal-{instrument}-2026",
            instrument_id=instrument,
            performed_at=performed,
            due_at=due,
            certificate=f"SYNTHETIC-CERT-{instrument.upper()}",
            standard_uncertainty=uncertainty,
            unit=unit,
            status="valid",
        )
    bench.create_study(
        study_id="rc-filter",
        title="First-order RC low-pass characterization",
        objective="Estimate the -3 dB cutoff and quantify the effect of a resistor substitution.",
        hypothesis="The measured cutoff follows 1/(2πRC) within the expanded uncertainty.",
        protocol=(
            "Apply a 1 V sine sweep from 20 Hz to 100 kHz. Record input amplitude, output "
            "amplitude, and phase at 41 logarithmically spaced frequencies."
        ),
        tags=["analog", "frequency-response", "filter", "metrology"],
    )
    bench.create_study(
        study_id="buck-efficiency",
        title="Buck-converter load sweep",
        objective="Measure conversion efficiency and locate its observed peak across resistive loads.",
        hypothesis="Efficiency rises at light-to-moderate load and then plateaus below 95%.",
        protocol=(
            "Apply 12 V DC. Sweep ten resistive loads, wait for thermal stabilization, then "
            "record input/output voltage and current."
        ),
        tags=["power-electronics", "efficiency", "load-sweep"],
    )
    frequency_a = root / "data" / "raw" / "rc-baseline.csv"
    frequency_b = root / "data" / "raw" / "rc-resistor-swap.csv"
    efficiency = root / "data" / "raw" / "buck-load-sweep.csv"
    _write_csv(
        frequency_a,
        ["frequency_hz", "vin_v", "vout_v", "phase_deg"],
        _frequency_rows(resistance=10_000, capacitance=10e-9, seed=seed),
    )
    _write_csv(
        frequency_b,
        ["frequency_hz", "vin_v", "vout_v", "phase_deg"],
        _frequency_rows(resistance=12_000, capacitance=10e-9, seed=seed + 1),
    )
    _write_csv(
        efficiency,
        ["load_ohm", "vin_v", "iin_a", "vout_v", "iout_a"],
        _efficiency_rows(seed + 2),
    )
    common_time = dt.datetime(2026, 8, 4, 6, 0, tzinfo=dt.UTC)
    bench.add_run(
        run_id="rc-baseline-001",
        study_id="rc-filter",
        operator="Shurong Cao",
        started_at=common_time.isoformat(),
        instruments=["scope-01", "source-01"],
        raw_files=["data/raw/rc-baseline.csv"],
        conditions={"ambient_temperature_degC": 23.4, "nominal_r_ohm": 10000, "nominal_c_f": 1e-8},
        deviations=[],
        notes="Synthetic demonstration data; no physical measurement claim.",
    )
    bench.add_run(
        run_id="rc-swap-002",
        study_id="rc-filter",
        operator="Shurong Cao",
        started_at=(common_time + dt.timedelta(hours=2)).isoformat(),
        instruments=["scope-01", "source-01"],
        raw_files=["data/raw/rc-resistor-swap.csv"],
        conditions={"ambient_temperature_degC": 23.8, "nominal_r_ohm": 12000, "nominal_c_f": 1e-8},
        deviations=["Resistor changed from 10 kohm to 12 kohm by design."],
        notes="Synthetic demonstration data; no physical measurement claim.",
    )
    bench.add_run(
        run_id="buck-load-001",
        study_id="buck-efficiency",
        operator="Shurong Cao",
        started_at=(common_time + dt.timedelta(days=1)).isoformat(),
        instruments=["dmm-01", "source-01"],
        raw_files=["data/raw/buck-load-sweep.csv"],
        conditions={"ambient_temperature_degC": 24.1, "input_setpoint_v": 12.0},
        deviations=[],
        notes="Synthetic demonstration data; no physical measurement claim.",
    )
    uncertainty = [
        {
            "name": "oscilloscope vertical accuracy",
            "limit": 0.005,
            "distribution": "rectangular",
            "source": "synthetic calibration certificate",
        },
        {
            "name": "repeatability",
            "standard_uncertainty": 0.0016,
            "distribution": "normal",
            "source": "repeat sweep summary",
        },
        {
            "name": "frequency timebase",
            "limit": 0.0008,
            "distribution": "rectangular",
            "source": "synthetic instrument specification",
        },
    ]
    analyze_run(bench, "rc-baseline-001", uncertainty_components=uncertainty)
    analyze_run(bench, "rc-swap-002", uncertainty_components=uncertainty)
    analyze_run(
        bench,
        "buck-load-001",
        uncertainty_components=[
            {
                "name": "voltage channels",
                "limit": 0.006,
                "distribution": "rectangular",
                "source": "synthetic calibration certificate",
            },
            {
                "name": "current channels",
                "limit": 0.004,
                "distribution": "rectangular",
                "source": "synthetic calibration certificate",
            },
            {
                "name": "load temperature drift",
                "standard_uncertainty": 0.002,
                "source": "stability window",
            },
        ],
    )
    fixed_created_at = "2026-08-04T07:59:00+00:00"
    for record_path in [
        root / "benchlineage.json",
        *sorted((root / "instruments").glob("*.json")),
        *sorted((root / "calibrations").glob("*.json")),
        *sorted((root / "studies").glob("*.json")),
        *sorted((root / "runs").glob("*.json")),
        *sorted((root / "analysis").glob("*.json")),
    ]:
        record = _portable_numbers(read_json(record_path))
        if "created_at" in record:
            record["created_at"] = fixed_created_at
        if "recorded_at" in record:
            record["recorded_at"] = fixed_created_at
        write_json(record_path, record)
    seal_workspace(
        bench,
        label="Public synthetic demonstration",
        created_at="2026-08-04T08:00:00+00:00",
    )
    if build_html:
        build_report(
            bench,
            root / "reports" / "demo-report.html",
            title="BenchLineage synthetic EE demonstration",
            note=(
                "A fully synthetic dataset showing traceable instruments, calibrated runs, "
                "derived analyses, uncertainty budgets, and a sealed evidence root."
            ),
        )
    return bench
