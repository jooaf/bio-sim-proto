# Stage 4 structured read-only signal response

## Decision

Spatially conditional behavior supported: **True**.

| arm | runs | interactions | reads | dispatches | uptake | left energy | right energy | max error |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| disabled | 5 | 8000 | 0 | 0 | 0 | 0.000000 | 0.000000 | 1.005e-15 |
| split | 5 | 8000 | 8000 | 8000 | 4035 | 9.990000 | 0.000000 | 2.274e-15 |
| uniform | 5 | 8000 | 8000 | 8000 | 8000 | 9.990000 | 9.990000 | 3.268e-15 |

This supports spatially conditional behavior by one immutable tape under read-only environmental signals. It does not establish communication, coordination, fitness, adaptation, or organization.
