# CarnotBatteryLab — Master Research & Engineering Plan

**Revision:** 1.0 (planning baseline, 2026-11-15)
**Software release:** v0.1.0 research foundation; no v1.0 physics claim
**Working repository:** `Open-Energy-Methods/CarnotBatteryLab` (published; see the GitHub main branch)
**Time horizon:** scientific readiness, not an application deadline

**Detailed v1.0 implementation contract:** see `V1_SCIENTIFIC_EXECUTION_PROGRAM.md`, `V1_STUDY_MATRIX_AND_BENCHMARKS.md`, and `V1_RELEASE_VERIFICATION_PROTOCOL.md`; these supplement the WP00–WP10 baseline rather than replacing it.

## Executive design decision

Build a multi-fidelity, open-source research **platform** for physically and
economically consistent, experimentally verifiable high-temperature heat-pump
and thermal-storage configurations. Software quality and domain validity are
both necessary. A stable Python library and tests do not by themselves
establish a credible thermodynamic design.

The core publishable question is not "which of three assumed efficiencies is
best?" but: *When service-temperature, material, heat-transfer, hydraulic,
compressor, cycle, dynamic and investment constraints are imposed
consistently, which HTHP–TES configurations are feasible, nondominated and
robust to uncertainty for a given industrial thermal duty and electricity
market?*

The project will support two distinct, non-interchangeable research families:
**H** heat delivered to an industrial process (primary platform) and **E**
actual electricity-to-electricity Carnot battery with a modelled power cycle.

## End-to-end system model

```
      waste-heat stream + source HX                  electricity tariff
                 │                                      │
                 ▼                                      ▼
   ┌──────────────────────────────┐            ┌───────────────────┐
   │ Natural-fluid HTHP           │◄───────────│ dispatch/control  │
   │ compressors + evaporator     │            │ constrained power │
   │ condensers + protection      │            └───────────────────┘
   └──────────────┬───────────────┘
                  │ variable heat output + state feedback
                  ▼
      thermal switchgear / HX network ←── sensor/pressure constraints
             ┌────┴───────────┐
             ▼                ▼
     direct process      TES charge pathway
         supply               │
             │          ┌─────┴───────────────────────┐
             │          │ packed bed / dual-media    │
             │          │ thermocline / molten salt  │
             │          │ phase change when justified│
             │          └─────┬───────────────────────┘
             │                │ discharge + HX + pumps
             └────────┬───────┘
                      ▼
          qualified industrial process heat
                      │
                 heat demand

  E-family only: hot storage ──> thermal power cycle ──> net electricity
```

Every interface transports a measurable state, not an assumed common
condenser-temperature scalar: heat-transfer fluid, mass flow, enthalpy,
pressure, compressor/valve state, and time-dependent capacity. Thermal
balances, electrical meter ledgers, economic costs and validation artifacts
must use the exact same topology identifiers and reference conditions.

## Physics fidelity ladder

- **F0 analytical verification:** elementary cycle identities, HX limiting
  cases, zero-heat-loss/tank ideal limits and hydraulic formulas. No claims of
  practical performance.
- **F1 reduced-order validated model:** steady real-fluid cycle, low-order HX,
  1D bed/tank dynamics, explicit thermo-hydraulics, feasible operating domain,
  and limited identified calibration parameters. Used for full-year dispatch.
- **F2 higher-fidelity physics:** 1D finite-volume two-temperature packed bed
  with temperature-dependent properties, axial conduction and wall losses;
  independently tested cyclic dynamics; compressor map and HX UA/pinch constraints.
  Reference simulation for correcting/rechecking F1 candidates.
- **F3 independent reference or experimental data:** data-matched validation
  with measured uncertainty and held-out operating conditions, or independent
  trusted FMU/library benchmarking. A numerical 2D/CFD model may be used when
  justified but is **not required** in every architecture to claim v1.0.

No optimisation algorithm may exploit accuracy differences between layouts.
All finalists are run in the same declared fidelity tier for performance
comparisons, and all Pareto points are rechecked in F2 and available F3.

---

# Work packages and gates

## WP00 — Research governance, definitions and provenance

**Deliverables**

- Persistent documentation of service H vs E, temperature ranges, source/sink
  contracts and architecture signatures, with no hidden common baseline.
- Literature map by subsystem; equation-level provenance ledger for pressure
  drop, heat transfer, working fluids, cost factors and ageing.
- Case schema with strict units, reference temperature, solver, source
  uncertainty and boundary definitions. Recorded changes by ADR.
- Versioned `results/<run_id>/` manifest: input checksum, git SHA, dependency
  versions, timestamp, seed, source IDs, output schema, solver diagnostics.

**Acceptance:** invalid/incomplete runs fail visibly; no numerical result can
be published without its conditions and data lineage.

## WP01 — Natural-working-fluid heat pump models

**Cycle set (scope ordered by physical relevance)**

1. R718 water vapour compression/MVR with separation and pressure/rate limits;
   evaluate single versus multistage/intercooling if demanded by lift.
2. R601/R601a, R600 and other natural-fluid compression cycles in the valid
   critical/phase envelope; do not assume all are safe or viable at 250°C.
3. Cascaded natural-fluid/steam architectures (R717/R718 or justified
   alternatives) when a single cycle cannot match source/process temperature.
4. Research-only gas/Brayton/Stirling or higher-temperature upgrade concepts
   when physically motivated, clearly labelled separately.

**Model capabilities:** property backend/cache and version pinning; compressor
isentropic/polytropic/map data with allowed pressure ratio, discharge
T and volumetric flow; heat exchanger approach/UA and pinch; suction
superheat, subcooling and heat-transfer rates; evaporator source pinch and
cooling constraints; part-load maps and cycling/start-up penalties; source
variability; pressure drops and electrical motor efficiency.

**Verification:** all thermodynamic state points physically defined;
component closure; COP/Carnot-consistency checks; phase boundary validation;
reject negative approach or property-domain extrapolation; compare against at
least one published reference case or independent engineering calculation.

**Gate G1:** verified real-fluid HP with heat rate/temperature dependent on
coupled condenser demand and known limitations, not a permanently fixed COP.

## WP02 — Rock packed-bed (gas + solid) TES

**Physics:** 1D two-temperature (fluid+solid) energy equations, conservative
finite-volume spatial discretisation, transient inlet/outlet, real geometry,
void fraction, solid/fluid mass, temperature-dependent cp and rho, axial
solid/HTF conduction as applicable, effective heat transfer, bed/tank losses,
wall/insulation energy, reversal charge/discharge and standby.

**Hydraulics:** particle diameter, porosity, frontal area and bed length;
Ergun pressure drop with correct validity checks, fan/pumping work. Surface
area and transfer coefficient linked to geometry rather than chosen NTU.

**Numerics:** stable stiff integration, solver failure detection, adaptive
integration with independent grid refinement, temperature/energy continuity,
zero-flow limit, adiabatic/no-heat-transfer limits, full charge/discharge and
periodic steady-state convergence under specified temperature cutoffs.

**Gate G2:** bed temperatures, outlet traces, stored energy and ΔP reproduce
independent analytic or literature references within documented tolerance.

## WP03 — Liquid HTF/solid dual-media thermocline TES

**Physical architecture:** liquid heat-transfer fluid occupying bed pores
with solid filler; fluid and filler properties separately modelled and
qualified across the whole operating temperature range. No rock-size-only
proxy masquerades as a distinct dual-media architecture.

**Physics:** porosity/packing, thermal stratification, two-medium exchange,
heat loss, buoyancy/mixing approximation when required, withdrawal/charging
mechanism, pump losses and corrosion/material constraints. Add 2D/radial
stratification only where 1D residuals show it matters.

**Temperature:** salt/HTF-freezing and decomposition margin, seal/material
limits, finite heat exchanger temperature approach; track heat tracing and
start-up inventories if required.

**Gate G3:** reproducible charge/discharge thermocline with demonstrable
mass/energy/exergy closure and geometry-dependent costs.

## WP04 — Two-tank molten salt and alternative TES

**Molten-salt branch:** distinct hot and cold mass inventories, finite tank
heat capacities, flow reversal, tank walls/insulation losses, tank heel,
pumping, valves, charge/discharge HX, level constraints, freeze protection,
tracing electricity and off-design start-up/standby. Reference salt chosen
from sourced phase-stability/property data, with an evidenced margin.

A nitrate-salt two-tank system cannot be connected directly to a 150°C
condenser while retaining 290°C cold-salt duty. Either (i) the entire plant
is configured at valid high temperatures using an explicit upgrade stage
whose power/cost is included, or (ii) that combination is excluded.

**Alternative storage:** PCM or pressurised hot-water/storage concepts only if
appropriate for the service and accompanied by material enthalpy curves,
pressure-vessel cost, and separate validation. Avoid adding technologies
merely to increase the plotted number of architectures.

**Gate G4:** physically viable storage with temperature/phase and mechanical
limits satisfied across every dispatch interval.

## WP05 — Hybrid architecture/network integration

- Graph-based port/interface model: pressure, temperature, enthalpy and flow
  continuity; physically placed source, condenser, TES and process HXs.
- Explicit switching (bypass, simultaneous heat+charge, pure charge,
  TES-only discharge, standby, restricted start-up) and actuator constraints.
- Coupled solution per time interval: TES state changes HP condensing state,
  capacity and electricity; source limits propagate to charge rates.
- Failure states must be reported rather than silently clipped: infeasible
  HX pinch, negative fluid inventory, no useful heat at setpoint, compressor
  envelope breach, salt freeze, bed overpressure.
- Consistent flow/energy/exergy/cost ledgers for every topology.

**Gate G5:** end-to-end 24 h and repeated multi-day cases in H0/H1/H2/H3,
with service parity, limits and conservation demonstrated. A layout can be
reported infeasible; it need not produce a number merely to fill a table.

## WP06 — Supervisory control and price-responsive operation

- Baselines: deterministic rule-based charging schedule and heuristic
  price thresholds; explicit part-load efficiency and actuator ramp limits.
- Dispatch optimiser: mixed-integer formulation (or equivalent) for HP on/off,
  TES charge/discharge exclusivity, rates, level constraints, heat demand and
  optional grid-import maximum. Verify convex/linear approximations against
  high-fidelity nonlinear re-simulation.
- Supervisory dynamic control: feedback SOC/temperature, heat-demand tracking,
  ramp-limited transitions, forecast errors and failed market signals; optional
  MPC or learning control only after an independent control baseline.
- Study horizon: representative weeks first, full weather/price years then;
  chronological preservation and multiple electricity-market regimes.

**Gate G6:** no heat-demand violations hidden by the optimisation; all
reported economic improvements exceed numerical/model uncertainty and are
sensitive-tested against tariff shapes and ambient/source conditions.

## WP07 — Multi-objective sizing/architecture optimisation

**Discrete variables:** topology, storage medium, fluid/cycle family,
number of beds/tanks, optional upgrade stages. **Continuous variables:** HP
rated power/temperature glide, TES inventory, diameter/height, particle
size, flow limits, HX UA, insulation, SOC band, operating temperatures and
control parameters.

**Objectives:** qualified heat LCOH, system input electricity or exergy
consumption, total annualised system cost, emissions (clearly defined) and
price-response flexibility. Do not mix correlated or incompatible objectives
without a written rationale. Track CAPEX and peak grid import as explicit
constraints even if not optimised.

**Method:** reproducible design-of-experiments/Sobol screening; constraint
filtering with real physics; epsilon-constraint MILP/nonlinear approaches
and an independent evolutionary multi-objective algorithm; nondominated
sorting with feasibility constraint; optimizer seed and convergence archive.
Fit surrogates only on disjoint train/validation/test sets, report OOD failures,
and re-evaluate Pareto solutions using the reference physics.

**Gate G7:** reproducible verified Pareto sets with convergence diagnostics,
representative dominated alternatives, cost/fidelity sensitivity and a
publication-quality physics-backed explanation of their trade-offs.

## WP08 — Techno-economics, environmental impacts and uncertainty

**Bottom-up components:** HP compressor/drive, evaporator/condenser and other
HX, TES bed/tank/media, pumps/fans, insulation, valves/heat tracing, controls,
BOP and contingency. Record economic scope and escalation to common real-year
price basis. Distinguish real vs nominal rate and vendor quote vs analogy.

**Outcomes:** CAPEX, OPEX, LCOH, equivalent annual costs, discounted NPV,
LCOH and breakeven frontiers, cost of flexibility and avoided grid peak under
source-specified baselines. Include life, replacement and residual value.

**Environmental:** time-matched electricity carbon intensity and defined
counterfactual process heat; material manufacture/embodied impacts only when
compatible source inventories are available and uncertainties are honest.

**Uncertainty:** Monte Carlo/Sobol for price, source energy, HP efficiency,
U-values, heat transfer, bed voidage, installed cost, discount rate and
lifetime; global sensitivity and numerical error decomposition; rank reversal
and probability of constraint violation; multiple source-verified markets.

**Gate G8:** all apparent "best" configurations supported by intervals and
robustness analysis; source-specific cost references and reproducible boundary.

## WP09 — Verification, model/data validation and experimental design

Follow `VALIDATION_AND_RELEASE_GATES.md`. Benchmarks must be genuinely
independent; retained historical screening outputs can be a negative-control
regression test, not a validation reference.

Potential data sources: accessible industrial/experimental published datasets,
self-contained analytical benchmark problems, independently generated FMUs,
external natural-fluid cycle reference cases and published packed-bed test
points. Do not claim measurement-backed validation when the raw data are not
obtainable. Obtain any necessary distribution permissions.

Create a targeted future rig design if experimental access becomes available:
T sensors distributed axially/radially, inlet/outlet T and P, flow meter,
ambient and insulation surface T, HP electrical/compressor power, source inlet,
process load and HX approach. Instrumentation records calibration/uncertainty,
timestamp synchronisation, sensor response, experimental safety envelope,
test matrix and withheld-test protocol.

**Gate G9:** externally benchmarked predictive accuracy in a declared domain,
including energy and ΔP residuals and an uncertainty budget; any
unvalidated component clearly marked.

## WP10 — Scientific communication, release and adoption

- Versioned figures generated from machine-readable manifests (cycle T-s/p-h,
  process HX plots, thermocline evolution, Sankey/exergy balance, Pareto map,
  source/price/load time series, uncertainty violin/frontiers).
- Full method report (state equations, solvers, verification, baseline
  comparisons, validity region, cost provenance, sensitivity, limitations).
- Reproducibility bundle with source/code/data environment, deterministic
  commands, tests and evidence maps; GitHub release and Zenodo DOI *only after*
  quality gates and rights review.
- Two paper-grade research packages: (A) coupled thermodynamic architecture
  comparison and (B) dynamic price-response/cost/uncertainty analysis. Optional
  (C) electricity-to-electricity Carnot battery once heat engine is modelled.
- Developer API and reference notebooks, scientific changelog, dataset
  dictionary, contribution policy and issue/PR templates.

**Gate G10 / Scientific v1.0:** all mandatory gates in the release matrix
pass, without pending physical-feasibility contradictions or unsupported
experimental claims. Missing independent measurements are clearly documented
and bound the scope of all accuracy claims.

---

# Ordered integration plan (no calendar-pressure shortcuts)

| Sequence | Milestone | Why it precedes the next | Observable completion evidence |
|---|---|---|---|
| 0 | Evidence and contracts | Prevents invalid comparisons | Case schemas, corrected definitions, audit quarantine, CI |
| 1 | Natural-fluid HP + HX | Can actually charge a stated service | Verified cycle/property/pinch reference tests |
| 2 | Bed geometry and coupled transient PDE | Replaces arbitrary NTU and single-cycle proxy | Grid/time/periodic-state checks, ΔP and UA |
| 3 | Alternative TES and compatibility | Enables real architecture differences | Physical H1/H2/H3 definitions and exclusions |
| 4 | Full network coupling | Removes fixed-COP/postprocessing fiction | Coordinated transients + conservation |
| 5 | Costed service-parity references | Establishes a defensible H0 comparison | Validated load continuity + cost scope |
| 6 | Dispatch and control | Adds credible flexibility | Price/load time series and constraint verification |
| 7 | Multi-objective optimisation | Explores feasible trade-offs | Pareto validation and independent solver checks |
| 8 | External benchmarking and UQ | Quantifies predictive credibility | Held-out comparisons, intervals, source registry |
| 9 | Scientific v1.0 release | Produces an auditable result | Reproducible full suite, figures and documented claims |

Milestones are **readiness gates**, not instructions to sequentially write all
code before integration. Cross-module contracts and benchmark cases should be
implemented incrementally, each milestone ending with a demonstrable end-to-end
example and a clear limitation statement.

# Proposed paper-grade experiments

### Experiment R1 — Thermo-hydraulic feasibility frontier

Fix process heat load, temperature and availability. Screen natural-fluid HP
and realistic storage choices against material, pressure and temperature
limits. Resolve why and when two-tank salt cannot be compared in the same
service family without an upgrade stage. Quantify source and heat-transfer
lift sensitivity. **Deliverable:** feasibility map and failure mechanisms.

### Experiment R2 — Geometry and cyclic degradation

For one viable packed bed, vary particle size, bed length/diameter, porosity,
heat transfer coefficients and insulation. Compare NTU/front sharpness,
charging/discharging duration, ΔP, auxiliaries, cyclic state and usable output.
Demonstrate energy closure and time/grid sensitivity. **Deliverable:** coupled
hydraulic-thermal design frontier with independent validation.

### Experiment R3 — Same-service architecture Pareto

Compare H0 and multiple feasible H cases at identical time-resolved process
heat requirements. Optimise HP/storage/HX sizing and report qualified heat,
unserved demand, capex/OPEX, LCOH, exergy, peak import, uncertainties and why
candidate layouts are nondominated or dominated. **Deliverable:** credible
physics-and-cost Pareto, not a plot of assumed storage costs.

### Experiment R4 — Dispatch realism and robustness

Use at least two independently sourced price regimes, matched weather/waste
heat assumptions and continuous/intermittent industrial duty. Compare
uncontrolled, deterministic rule-based, MILP and receding horizon controls;
verify nonlinear re-simulation, price forecast errors and seasonality.
**Deliverable:** conditions where storage flexibility pays, and where it does not.

### Experiment R5 — Actual Carnot-battery branch

Connect thermally compatible TES to a specified heat engine and compare
P2H2P electrical cycles against H-only alternatives **without confusing their
output services**. Analyse electricity RTE and co-produced process heat.
**Deliverable:** power-to-power research study, only once verified hardware
and power-cycle assumptions exist.

# Acceptance rules for the repository

1. Every new physical module states equations, units, validity range,
   simplifying assumptions and independent benchmark(s).
2. Every report figure is generated directly from an identifiable run manifest.
3. Every fit/calibration states the raw data access and train/holdout split.
4. Every actual cost input states year, currency, scale, scope and uncertainty.
5. No point appears on a published Pareto frontier if it fails a hard physical
   constraint or reference-simulation convergence.
6. Historical results are not silently reused under new file names.
7. Normal users can reproduce every claimed headline within documented,
   reasonable numerical tolerances in a clean environment.
8. A scientific release requires the `VALIDATION_AND_RELEASE_GATES.md` matrix
   to be filled with evidence links, not just green software unit tests.

# Decision log and unresolved scientific inputs

- Working-fluid feasibility and compressor maps: **not solved**, sourced
  candidate set in WP01. Do not choose a universal fluid before service matching.
- Process temperature: initial H 150°C is an illustrative workload, while
  valid nitrate salt requires a different high-T branch or explicit booster.
- TES media prices: no publication-grade figures yet; earlier cross-study
  cost ratios are withdrawn.
- Experimental data: not yet secured; no fabricated experimental validation.
- Study markets: choose verifiable price time series and price-year alignment
  when dispatch analysis begins; avoid cherry-picked periods.
- Code/data licence: repository owner must choose and approve publication.
- Electrical-power output: research expansion requires full heat-engine model.

This plan is intentionally **substantial**; the appropriate scope is an
engineering research tool and associated studies, not a rapid job-application
work sample. Its public claims must always reflect which gates have been met.
