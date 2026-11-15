# Implementation backlog (ordered, gated)

The goal is NOT to rush through versions. Each issue must have physics,
verification, data and interface acceptance. Make each issue a reviewable pull
request and link its tests/evidence to the release matrix.

## Phase A — first complete end-to-end physics

- **A01** Natural-fluid property adapter with property-domain bounds, backend
  metadata, cached SI states; compare CoolProp against reference tables.
- **A02** R718 cycle solver: real vapor compression, pressure/discharge-temp
  screening, degree superheat, finite source and sink approach. Infeasible
  states must be rejected. Include reference state table and closure tests.
- **A03** R601/R601a single-stage cycle plus 2-stage/multistage candidate
  evaluation if constraints require it; confirm near-critical validity and
  appropriate compressor capabilities.
- **A04** Source/process counterflow HX with finite UA and pinch constraints;
  enforce matched flow, enthalpy and temperature profiles.
- **A05** Implement 1D two-temperature packed-bed finite-volume model with
  explicit solid-fluid energy transfer, geometry and temperature profiles.
- **A06** Add Ergun hydraulics to dynamic bed, fan work, convective heat
  transfer correlation, insulation/wall and standby losses; source correlation
  domains, compare with published packed-bed benchmark.
- **A07** Cyclic warm-start solver for repeated charge/standby/discharge;
  enforce supply temperature cutoff, energy/exergy balance and time/grid
  convergence.
- **A08** Coupled H0/H1 network where storage and HTF outlet affect condenser
  temperature and HP electrical input each step. Simulate 24 h and 7 days.
- **A09** Independent reference test suite and comparison report with
  qualified industrial process heat and heat pump alone.

## Phase B — architecture completeness

- **B01** Formal typed network topology/ports, switching states, constraints
  and per-component work/exergy ledgers.
- **B02** HTF + solid-filler liquid dual-media thermocline with sourced fluid
  stability and geometry/pressure/transfer physics.
- **B03** Two-tank nitrate-salt system with liquidus guards, thermal tracing,
  two-tank mass/energy conservation and high-temperature HTF/HX.
- **B04** Explicit 250°C+ charge pathway (natural-fluid, cascade, steam/MVR,
  or auxiliary booster), comparing all added electricity and cost; exclude
  unchargeable architectures, not penalise them artificially.
- **B05** Alternative PCM storage when credible data justify it, with latent
  enthalpy method and sourced phase transition data.
- **B06** Matched-service sizing and direct H0 comparator across layouts.

## Phase C — flexibility, economics and optimisation

- **C01** Time-series import with timezone, leap/DST, price quality and
  missing-data policy; two independent electricity markets.
- **C02** Rule-based baseline dispatch with hard heat-demand constraints.
- **C03** MILP/NLP dispatch with finite charge rates and verified nonlinear
  re-simulation of HP/TES response.
- **C04** Bottom-up CAPEX/OPEX estimation, quote/source boundaries, reference
  price-year treatment and replacement schedule.
- **C05** Annual model with heat demand, source variability and common input
  datasets; LCOH/NPV and flexibility breakeven.
- **C06** Engineering design space (mixed discrete/continuous variables),
  constrained multi-objective solver and Pareto filter with metadata.
- **C07** UQ, scenario robustness, convergence, price regimes and rank
  reversal. Validate surrogates against unseen samples and OOD tests.

## Phase D — validation, research output and release

- **D01** Source traceability ledger with exact model equation/page/units.
- **D02** Independent published/experimental comparison with blind held-out
  data, uncertainty and thermal/pressure time alignment.
- **D03** Instrumentation/physical validation campaign protocol with
  calibrated T, P, flow and power sensor location diagrams and DAQ specs.
- **D04** Programmatic scientific figures and reproducible run manifests.
- **D05** Research paper package for coupled thermodynamic architecture
  study and robust price-driven systems analysis.
- **D06** V1.0 release gate checklist, clean-install CI, data/licence audit,
  scientific changelog and DOI publication (only if rights permit).
- **D07** Optional E-family power-cycle and electricity-return test suite.

## First immediate feature branch

`feat/natural-fluid-hp-hx-baseline`

Acceptance before merging:

1. R718 and/or R601 real-fluid benchmark with **traceable** operating points.
2. Correct state point and heat/electric balance under finite HX approach.
3. Demonstrable connection to an actual time-varying process/HTF loop.
4. A rigorous hard-failure mode at pressure, temperature and pinch limits.
5. Dependency pins, reproducible figures, numerical uncertainty and tests.
6. No reuse of R1233zd(E) COP=2.123 as universal heat-pump response.

This is the start of a **full platform**, not a pilot used to draw
three arbitrary architecture dots.
