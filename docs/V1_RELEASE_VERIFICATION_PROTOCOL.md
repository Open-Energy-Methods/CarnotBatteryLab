# CarnotBatteryLab — v1.0 Verification, Validation and Release Protocol

**Revision:** 2026-11-15  
**Status:** quality contract for subsequent implementation; ALL new physics gates are presently NOT_RUN  
**Precedence:** this protocol supplements VALIDATION_AND_RELEASE_GATES.md, not a substitution for its R0–R17 requirements.  
**Release class:** H-family model-based scientific v1.0; excludes experimentally certified industrial accuracy or electric-output Carnot battery unless independently demonstrated.

## 1. Four evidence classes (do not interchange)

- **V0 analytic/software verification:** dimensional analysis, sign identities, conservation, parser/solver failures, null cases, limits, property-envelopes. A unit test checking an equation against itself is not independent evidence.
- **V1 independently sourced numerical benchmark:** published equations/tables/operating points or independently derived analytical solutions with documented geometry, materials, conditions, uncertainty and reproduction procedure.
- **V2 external model cross-check:** an independent Modelica/FMU/second finite-volume implementation or similar solved under matched conditions, with cross-solver comparability and discretisation uncertainty.
- **V3 experimental predictive validation:** calibrated sensors and equipment, raw immutable observations, timing and spatial sensors, parameter-identification protocol and whole-run withheld experiments; uncertainty-aware model/data discrepancies. V3 is strongest, but one unrelated rig does not validate all temperature/fluid domains.

An H-family **model-based v1.0** may be released on V1/V2 for its evidenced domain when V3 is unavailable, but must NOT be called industrial/experimental validated in unmeasured regimes.

## 2. Proposed quantified numerical quality criteria

These are **provisional engineering limits to design tests**, not claims that a method or external measurement already satisfies them. After adopting a published/experimental benchmark, lock context-specific error budgets *before* calibrating and do not loosen them post hoc merely to pass.

| Quantity | Proposed initial acceptance target | Test interpretation |
|---|---|---|
| Steady mass balance | abs(sum mass in - sum mass out) / max(sum abs mass in, reference floor) <= 1e-8 in algebraically closed components | If double-precision/root-solver noise or physical source terms demand different scale, document numerical floor |
| Steady energy residual | abs(balance) / max(sum absolute enthalpy and heat/work rates, reference floor) <= 1e-6 for HP and HX algebraic components | Independent full-component ledger, not recomputation from a rearranged identity only |
| Transient integrated energy residual | abs(U_end-U_begin - integrated net inflow) / max(integrated absolute through-energy, meaningful storage-scale floor) <= 1e-3 | Evaluate with independent quadrature; 0.1% is a **numerical screening target**, not predicted model accuracy |
| Full-cycle inventory | abs(U_end-U_begin) / max(usable storage U, meaningful floor) <= 1e-3 after converged repeated cycles | Verify spatial temperature field, not scalar energy only; terminal field criterion also required |
| Storage temperature-field cyclicity | max node temperature difference <= a preregistered physically justified threshold (initial proposal 0.2 K for reference runs), plus convergence in delivered useful hours | If this cannot be achieved without excessive computation, report non-periodic operation and do not claim cyclic round trip |
| Spatial refinement | >=3 grids; relevant outputs (qualified heat, outlet traces, thermal-front time, fan/pump work) exhibit consistent convergence and a documented grid convergence error estimate | 0.5% qualified-heat change and 1% cutoff-time change are provisional stopping thresholds, not validation criteria |
| Integration tolerance | vary relative/absolute tolerances independently at fixed grid; output variation smaller than chosen spatial-error budget | No timestep-segment coupling; trace rejected solver events |
| Exergy/second law | exergy destruction nonnegative within separately calculated numerical tolerance; no unexplained negative entropy creation | System flow exergy uses h and s at one dead state and includes pressure effects |
| HX pinch and material ranges | zero physically invalid accepted states | Strong type/feasibility check; exactly zero tolerance for silent invalid solution |
| Service supply | zero unpriced/hidden deficit; any permitted thermal unserved energy explicitly exposed in objective and reporting | Equal quality heat at demanded T/flow/pressure and chronology |
| Optimizer candidate validity | 100% of published feasible Pareto points pass the independent, high-fidelity nonlinear re-simulation constraint audit | MILP feasibility is not the truth model |
| Scientific replay | all primary figures/tables regenerate using published case/config/hash/seed without manual editing | Release archive logs exact dependencies and numerical diagnostics |

When an external benchmark disagrees with the model, report both the discrepancy and the physical hypotheses; never adjust acceptance threshold by matching the result. Where uncertainty dominates, use an uncertainty-weighted comparison rather than a universal fixed temperature RMSE.

## 3. External evidence and statistical protocol

### Data provenance and legal rights
For each external source record ID: title, DOI/URL, exact figure/equation/page, units, physical conditions, license/access, download timestamp and checksum, validation relevance and limitations. Software license for this repo must be selected separately by owner; external data licences remain attached. Reproduce measured values only if extraction/reuse rights allow.

### Calibration vs test
Choose calibration parameters with physical meaning and measured/prior bounds; e.g. overall heat-transfer multiplier, ambient U, compressor-map correction. Record identifiability and covariance; never tune a parameter merely to hit a target efficiency. Split raw test data by full run/design condition, not randomly by timestamps; reserve unseen conditions for validation. If the independent source supplies only one trajectory, mark as model-to-data illustration, not blinded validation.

### Measurement criteria
Record sensors, axial/radial locations, data acquisition rate, drift, bias, calibration records, and synchronization. Compare forward model with measured T/P/flow/power as independent channels and quantify lag and thermocline travel time. Include uncertainty estimates and propagated reference input uncertainty. Explain structural mismatch (e.g., neglected radial thermal bypass) and model-validity limits.

### External benchmark campaign candidates
1. Water saturation/steam tables via independent IAPWS source; branch-specific tolerance based on reported EOS resolution.
2. Published high-temperature HP operating state case within refrigerant, lift and pressure bounds; seek full table/numerical method, not just review abstract.
3. Calderón-Vásquez et al. 2024 copper-slag packed-bed temperature/velocity dataset, DOI 10.17632/j37x6ptpk2.1, open description CC BY 4.0. Extract geometry, bed dimensions, HTF and time-aligned sensor data; check if run-level split feasible. Its high-temperature range is **not automatic validation for low-temperature gas/rock geometry**.
4. Independent liquid/filler thermocline model and experimental reference under sufficiently close material geometry and temperature; **not selected yet**, blocking full H2 validation.
5. Independent two-tank salt model/experiment at valid thermophysical range; **not selected yet**, blocking full H3 validation.
6. Dynamic HP/TES operating profile from literature or independent FMU under matched boundary; where published data are unavailable, compare a separately developed reference model and label as V2 only.

**Critical gap:** H2/H3 reference datasets must be found, licensed and matched. Their absence is not resolved by conservation tests alone.

## 4. Release test matrix: mandatory evidence owners and artifacts

Each requirement R0–R17 in VALIDATION_AND_RELEASE_GATES.md maps to the evidence below; create a machine-readable gate ledger with states NOT_RUN, PASS, FAIL, BLOCKED or INAPPLICABLE and paths to results. 'INAPPLICABLE' requires approved written narrowing of claims, not an automatic exemption.

| Gate | Required evidence artifact(s) | Suggested verification code / method |
|---|---|---|
| R0 | references/claim_source_ledger.csv and data licence inventory | schema plus reviewer check on exact equation/page |
| R1 | docs/methods/METRICS_AND_SYSTEM_BOUNDARIES.md and typed heat/electric service tests | incompatible numerator/denominator negative tests |
| R2 | results/benchmark_hp_states/, cycles plots and compressor envelopes | property cross-check; first-law/exergy, full compressor state table |
| R3 | results/benchmark_hx/ finite-HX pinch/UA sweeps | independent segmented enthalpy/pinch solver and limits |
| R4 | results/benchmark_gas_bed/ T(z,t), pressure and cycle histories | analytic cases + external published test + grid/time study |
| R5 | results/benchmark_dual_media/ liquid/solid T(z,t) | independent reference/model and materials property audit |
| R6 | results/benchmark_salt/ mass/T/trace electrical and feasibility log | property/phase/compatibility checks, tank energy/mass reference |
| R7 | results/balances/ energy mass exergy residuals by component | independent ledger and sign reversal/zero-flow tests |
| R8 | results/convergence/ spatial, integrator and property convergence reports | three meshes, fixed-grid tolerance sweep, error estimate |
| R9 | results/cyclic_state/ repeated charge/standby/discharge and termination | terminal temperature vector + U residual |
| R10 | results/service_parity/ actual process T/flow, annual qualified useful heat | H0/H1/H2 (+conditional H3) exact service chronology and backup cost |
| R11 | results/flexibility/ dispatch time series, solver diagnostics, resimulation | rule vs MILP/MPC, heat loss and ramp constraints |
| R12 | results/external_validation/ raw/held-out split and model/data residuals | independent benchmark reviewer with uncertainty bands |
| R13 | results/costs/ CAPEX/OPEX input source ledger and price-year accounting | discounted vs annualized consistency, scale/energy units |
| R14 | results/pareto/ candidate table with feasible mask and verification | epsilon-constraint vs independent algorithm, seed replay |
| R15 | results/uncertainty/ parameter sets, correlations, CIs and rank reversals | seeded global sensitivity, scenario year holdout |
| R16 | results/replay/ environment lock, input and data hashes, clean CI replay | fresh checkout/install, deterministic render |
| R17 | reports/research_v1/, autogenerated research figures and limitations | independent artifact cross-check with machine outputs |

## 5. Scientific peer-review questions before marking a gate PASS

- Is the component physically connected to the source, sink and load, or has heat been created at an assumed constant temperature?
- Has every electrical auxiliary, pump, pressure drop, trace heater and standby load been counted?
- Is the heat output at the process temperature and required chronology, or only a nominal stored MWh amount?
- Does a coupled layout change compressor operation with storage temperature and available source heat?
- Has every medium/working fluid been qualified for phase, pressure, criticality, materials and safety boundaries?
- Is this a numerical convergence check, a benchmark reproduction or actual experimental predictive validation—and does the report say which?
- Are measured/derived cost values source-matched for price year, installed scope, equipment size and technology?
- Was optimisation performed under the same available knowledge, service contract and physical constraints for competing designs?
- Can a negative result be reproduced and does it constrain an attractive-but-incorrect conclusion?
- Would another engineer independently reproduce the reported chart and machine-readable table with only this release bundle?

A documented FAIL is scientifically more useful than a fabricated PASS. A supported claim is tied to both its validation result and its applicability domain.

## 6. CI and reproducibility architecture

Proposed jobs:
- **lint-and-types:** ruff, typing, schema validation, security/dependency hygiene; deterministic Python versions.
- **physics-unit:** dimensional, property and state validity, energy/exergy negative tests, zero-flow/perfect HX limit.
- **physics-regression:** small HP+bed coupled transient with fixed stored golden outputs (generated independently once) and tolerance budget.
- **validation-benchmarks:** short V1 reference suite including property and TES curves; compare against immutable public dataset *not* code-created synthetic truth.
- **optimisation-sanity:** feasible/infeasible schedule, small exact enumeration vs MILP, matched-service and Pareto-dominance verification.
- **scheduled-heavy:** high-resolution PDE convergence, multiple price years, MC/UQ seeds and complete paper figures. These may run scheduled/on-demand rather than on each code change.
- **release-replay:** clean install with environment lock, license/file checks, archived figures, manifest and figures/tables digest.

Scripts must fail nonzero on physical violations, solver failures, missing required sources or expected result files. CI never marks missing optional data 'passed'; it reports blocked/skipped with cause.

## 7. Evidence freeze and versioning

### Research milestones
- v0.1.x: contracts and pure physics identities; avoid performance claims.
- v0.2: natural-fluid, finite-HX, H0 validated against real/reference states.
- v0.3: gas/rock transient and independent bed verification.
- v0.4: dual-media and salt components with property and phase checks.
- v0.5: physical H0/H1/H2/H3 compatibility, state coupling and cyclic operations.
- v0.6: verified long-horizon operating control and common service.
- v0.7: economic/cost provenance, original figures and reference comparisons.
- v0.8: constrained multi-objective design and independently re-simulated feasible Pareto sets.
- v0.9: numerical convergence, external benchmark and UQ papers/provenance complete.
- v1.0-rc: science/results freeze, independent clean replay and written peer review.
- **v1.0:** only when model/domain claims, methods, datasets, validation, reproducibility, license and archived results agree.

These are readiness states, **not dates or permission to increment a tag after feature code is written**.

### Release package
- Code, dependency lock, package licence/citation, version and machine setup.
- Model state/flow equations and model discrepancy statement.
- Reference cases and source registry.
- Verification/validation results with residuals, benchmark uncertainty and failures.
- Machine-readable architecture comparison, full economic unit ledger and Pareto verification.
- Clean-run command to regenerate figures and tables.
- Two substantial scientific reports and a limitations page.
- Explicit listing of unvalidated components, excluded physical domains and negative findings.
- Optional Zenodo DOI only once dataset rights are confirmed.

### Red-team sign-off
Do not tag if: any physically invalid salt/cycle case survives feasibility filtering; any architecture ranking uses unrelated cost scopes; any reported COP ignores required auxiliary electric work; any published Pareto point violates the nonlinear plant; any described experiment uses synthetic or unlicensed data mislabelled as measured; or release replay depends on undeclared manual files.

## 8. Next work packages (unblock order)

**First:** finish external state/cycle/source selection and benchmark records.  
**Second:** implement the natural-fluid HP + finite HX vertical slice, with a truly coupled 150°C H0 reference and independent test.  
**Third:** conservative geometry-based packed-bed charging/standby/discharge and repeated cyclic operating state.  
**Fourth:** liquid/filler thermocline and physically viable salt module, with source-verified fluid properties.  
**Fifth:** integrated H1/H2, conditional H3, scenario dispatch, engineering-cost analysis and multi-objective Pareto with external re-simulation.  
**Then:** independent validation, sensitivity, reporting and release peer review. 

This protocol does not assert any new numerical or physical result.
