# Uncertainty model

BenchLineage implements a deliberately limited, GUM-inspired independent-component budget.

## Terms

A **standard uncertainty** is expressed like a standard deviation. An **expanded uncertainty** is
the combined standard uncertainty multiplied by a coverage factor `k`. A **sensitivity
coefficient** describes how a change in an input affects the reported output quantity.

For independent components:

```text
u_c = sqrt(Σ (c_i × u_i)²)
U   = k × u_c
```

BenchLineage reports each squared contribution divided by total variance. This makes the dominant
assumption visible.

## Supported inputs

### Direct standard uncertainty

```json
{
  "name": "repeatability",
  "standard_uncertainty": 0.0016,
  "sensitivity": 1.0,
  "distribution": "normal",
  "source": "twenty repeated acquisitions"
}
```

### Limit and distribution

```json
{
  "name": "resolution",
  "limit": 0.0005,
  "distribution": "rectangular",
  "sensitivity": 1.0,
  "source": "least significant display digit"
}
```

The conversion divisors are:

| Distribution | Standard uncertainty from stated limit `a` |
|---|---:|
| Normal, where limit represents approximately 95% coverage | `a / 2` |
| Rectangular | `a / sqrt(3)` |
| Triangular | `a / sqrt(6)` |

The normal interpretation is a convention and must match the actual specification. If a
certificate already gives standard uncertainty, record it directly.

## Limitations

The core engine does not currently model:

- correlated components;
- asymmetric distributions;
- effective degrees of freedom and Welch–Satterthwaite coverage;
- nonlinear propagation;
- Monte Carlo propagation;
- complex-valued quantities;
- covariance produced by shared instruments;
- automatic extraction from certificates.

Do not hide those limitations by adding more decimal places. Use a domain-specific analysis when
the model requires them, and store its output as a derived artifact.

## Reporting checklist

- Name the measurand and unit.
- Explain every component source.
- Distinguish standard and expanded uncertainty.
- State the coverage factor and interpretation.
- Record correlation assumptions.
- Preserve intermediate calculations.
- Avoid claiming metrological traceability from software output alone.
