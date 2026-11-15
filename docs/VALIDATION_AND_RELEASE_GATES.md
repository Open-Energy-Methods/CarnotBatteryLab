# Validation evidence matrix and v1.0 release gate

All entries are **requirements**, not completed milestones unless explicitly
stated. An unchecked gate cannot be represented as passing because a toy
problem solves or tests are green. Every item needs an artifact path and a
numerical benchmark/threshold justified from numerical/error physics or
measurement uncertainty.

| ID | Mandatory v1.0 requirement | Evidence required | Current status |
|---|---|---|---|
| R0 | Source and measurement provenance | Source ID, access, exact equation/conditions, units | Partial source registry |
| R1 | Correct Carnot-battery vs heat-only terminology | Separate H/E metrics, output boundaries | Defined, tested primitives |
| R2 | Natural-fluid real-property HP | State-point table, source/sink coupling, compressor constraints, external cycle benchmark | Not implemented |
| R3 | Explicit HTF/hot-process HXs | Temperature pinches, UA/rate limits, no phantom heat flow | Not implemented |
| R4 | Geometry-based sensible bed | Fluid/solid PDE, heat loss, ΔP, fan work, cyclic states | Only hydraulic primitive |
| R5 | Correct dual-media thermocline | HTF + filler with material validity and measured/literature check | Not implemented |
| R6 | Physically viable salt/tank branch | Liquidus margins, heat tracing, HTF constraints, full upgrader work | Not implemented |
| R7 | Mass, energy and exergy closure | Residual plots per component and full plant | Metric primitives only |
| R8 | Temporal/spatial/solver convergence | 3+ mesh/time resolutions, independent tolerance tests, phase-change front resolution | Not implemented |
| R9 | Repeated periodic TES cycles | Quantified end-start state residual, temperature-qualified discharge | Not implemented |
| R10 | Same-service architecture comparison | H0 direct reference, annual qualified heat, no hidden unserved demand | Not implemented |
| R11 | Dynamic price-responsive dispatch | Costed price time series, operational constraints and resimulation | Not implemented |
| R12 | Credible parameter estimation/validation | Independent reference reproduction; calibration/holdout separation | Not implemented |
| R13 | Uniform bottom-up economics | CAPEX/BOP scope, price-year normalization, uncertainty | LCOH identity only |
| R14 | Multi-objective optimisation | Documented feasible Pareto sets, seed, optimality/convergence | Not implemented |
| R15 | Robustness and uncertainty | UQ of thermophysical, cost and price domains, rank sensitivity | Not implemented |
| R16 | Reproducibility and release | Clean install, CI, versioned input/run manifest, scripts, dataset rights | Partial foundation |
| R17 | Scientific publication artifacts | Methods report, independent figures, limitations, machine-readable runs | Not implemented |

## Suggested evidence quality tiers

- **V0 — internal checks:** analytic limiting cases, conservation identities,
  unit tests, assert validity ranges. Useful but **not** independent validation.
- **V1 — independent numerical benchmark:** published tables/plots and/or
  independent mathematical solver; verify equations and conditions match.
- **V2 — external reference implementation:** separately developed FMU/Modelica
  or finite-volume reference with independent solver and convergence study.
- **V3 — experiments:** measured inlet/outlet, internal thermocline and
  pressure, electrical power; calibrated uncertainties and held-out cases.

The project can attain a **model-based scientific v1.0** with V1/V2 validation
provided its advertised predictive domain is limited to evidence-backed
conditions and the lack of V3 experiments is made explicit. Do not label
measured/industrial predictive accuracy achieved without V3 evidence.

## Numerical protocol

For every PDE/cycle family, evaluate spatial refinement, temporal tolerance
and property interpolation independently; report errors for thermal output,
cycle energy inventory, pressure drop and process supply temperature. Stop
refinement only after numerical uncertainty is small relative to required
engineering accuracy and the published validation reference uncertainty.

Test null and bounding cases: zero heat flow, zero standby loss, perfect HX
limit, zero flow, equal inlet/bed temperature, high/low storage SOC,
minimum fluid temperature, pressure drop at small velocity, cold start,
process-load discontinuity, solver time-out and optimization infeasibility.

## Validation protocol for experimental data

- Raw data immutable; record origins, sampling rate and time zone, sensor
  position, calibration and bias/covariance.
- Synchronise time bases and quantify lag/response; avoid reporting
  temperature pointwise accuracy across unaligned transients.
- Pre-register train/validation/test split or entire unseen experiment runs.
- Define MAE, RMSE, bias, peak errors, total energy errors, pressure errors,
  and per-segment thermocline arrival time; compare to propagated uncertainty.
- Publish both pass/fail verdicts and physical interpretation of residuals;
  do not replace failed tests with broader subjective agreement.

## Release process

- v0.x: feature-by-feature scientifically scoped research development with
  transparent partial evidence.
- v1.0-rc: **all mandatory scientific mechanisms** working, results frozen,
  independent reproduction and release matrix review underway.
- v1.0: release matrix complete or appropriately scoped exclusions documented
  (e.g. no electrical Carnot battery claims until E branch validated), clear
  design/fidelity limitations, clean CI, archived benchmark outputs,
  publication-grade report and provenance; only then tag, publish and DOI.
