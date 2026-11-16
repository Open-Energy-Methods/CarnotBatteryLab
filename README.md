# CarnotBatteryLab

**Verification-first research platform for coupled high-temperature heat pumps,
thermal energy storage, industrial flexibility, and Carnot-battery architectures.**

> **Current repository state: v0.1.0 research foundation, NOT scientific v1.0.**
> The models under `legacy_audited_screen/` are preserved *for historical audit
> purposes only*. Their A/B/C architecture ranking was withdrawn following the
> 2026-11-15 scientific audit. It is **not an endorsed result**, and it does not
> define the platform's current physics. Do not cite or reproduce those tables
> as validated engineering design conclusions.

## Scientific scope and terminology

1. **Industrial power-to-heat with TES (P2H+TES):** flexible production of
   *qualified industrial process heat*. Primary outputs: useful heat at required
   temperature, annual electricity consumption, LCOH, costs, operating
   flexibility, and operational robustness.
2. **Electricity-to-electricity Carnot battery (P2H2P):** electric input to a
   heat-pump/storage charging train and electricity recovered by a **modelled
   heat engine/power cycle**. Primary performance: net electrical round-trip
   efficiency, including auxiliary and standby electricity. A heat-only device
   is **not** automatically an electrical Carnot battery.
3. **Co-production of heat and electricity:** separate output ledgers, with an
   explicitly stated allocation convention; never add kWh_th and kWh_e as if
   they were interchangeable.

The current fully specified **research target** is the first track; the latter
tracks are reserved as independently gated research expansions.

## Planned capabilities (NOT claimed implemented)

- Natural-fluid real-property heat-pump cycles (R718, R601/R601a and other
  justified candidates), operating-envelope checks and component maps.
- Explicit storage: air/rock sensible beds, liquid-HTF/solid-filler
  dual-media thermoclines, two-tank molten salts only within verified
  liquid-temperature/chemical windows, plus justified PCM alternatives.
- Coupled HX, fluid-network hydraulics, transient charging/discharging,
  thermal losses, thermocline evolution and cyclic stationary operation.
- Architecture and capacity optimisation, dispatch under actual market
  scenarios, techno-economic and uncertainty assessment, research-level
  closed-loop control, and independently benchmarked physics.
- Transparent data/provenance management and open, reproducible results.

**Implemented in v0.1.0:** typed case input and validation; dimensionally explicit
energy/exergy and packed-bed hydraulic primitives; a unit-aware LCOH identity;
CLI; regression tests; CI; input provenance manifest generation;
comprehensive methodological and research plans.
No integrated dynamic HP+TES layout is claimed solved yet.

## Source repository organization

```
CarnotBatteryLab/
├── src/carnot_battery_lab/    # New verified package, pre-alpha
│   ├── cases.py               # Typed inputs; strong validation boundary
│   └── physics/              # Exergy, hydraulics, costing identities
├── cases/                    # Illustrative reference service contracts
├── docs/
│   ├── MASTER_RESEARCH_PLAN.md
│   ├── SCIENTIFIC_CONTRACT.md
│   ├── VALIDATION_AND_RELEASE_GATES.md
│   ├── methods/              # Equations, metric boundaries and assumptions
│   └── decisions/            # Architecture decision records
├── references/               # Source registry and provenance requirements
├── tests/                    # New package foundation regression tests
├── .github/workflows/ci.yml  # Automated cross-Python checks
└── legacy_audited_screen/    # Original audited proof-of-concept; WITHDRAWN claims
```

## Installation and first checks

```bash
python -m venv .venv
# Activate the environment for your platform.
python -m pip install -e ".[test]"
python -m pytest tests/ -v
python -m carnot_battery_lab.cli validate-case cases/reference_industrial_heat_150C.yaml
python scripts/create_input_manifest.py cases/reference_industrial_heat_150C.yaml
```

The `physics` optional dependency installs scientific packages and CoolProp for
future real-fluid models. It is **not required** for foundation tests.

## Non-negotiable research standards

- Every comparison must use matched **useful heat/power service**, not merely
  equal theoretical heat-storage inventory.
- Invalid temperature/phase constraints make a candidate *infeasible*, not a
  worse-performing point on a Pareto front.
- The heat-pump condenser cannot remain an infinite constant-temperature
  source when TES temperature and heat-transfer approach change.
- Every component has explicit energy, mass, and exergy balances, and every
  pressurised flow circuit includes justified auxiliary work.
- A storage round-trip claim requires consistent terminal states, specified
  qualified-delivery cutoffs and a cyclic steady operating point.
- Capital costs must share boundary, price year, currency, scale and duty;
  assumptions and uncertain estimates remain labelled as such.
- Independent analytical and external-model/experimental verification is
  documented separately from model self-consistency tests.
- Optimiser outputs must be re-evaluated using the highest applicable physics
  fidelity, and Pareto claims must be constraint-compliant.
- Unknown parameters are exposed through uncertainty analysis, never
  invented to force a comparison.

## Scientific v1.0 execution programme

The scientific v1.0 target is a **model-based, externally benchmarked H-family research platform**, not a claim of completed experimental validation or an electricity-return Carnot battery. The programme uses predefined architecture and service contracts, separate literature benchmarks, physics and solver convergence, coupled dynamic re-simulation of Pareto candidates, and source/price-year uncertainty studies. All physical v1.0 features remain planned until evidenced by the release matrix.

- [Scientific v1.0 execution programme](docs/V1_SCIENTIFIC_EXECUTION_PROGRAM.md)
- [Preregistered comparative study matrix and benchmark candidates](docs/V1_STUDY_MATRIX_AND_BENCHMARKS.md)
- [Verification, validation and scientific v1.0 acceptance protocol](docs/V1_RELEASE_VERIFICATION_PROTOCOL.md)

## Current M1 vertical slice (screening, NOT validated industrial model)

The model now includes a real-fluid R718 single/two-stage water-vapour screening calculation with finite source, condenser and externally-cooled intercooler temperature profiles; required-UA/pinch checks; compressor stage guards; source/process flow availability and shaft/electric heat ledgers. The first demonstration is explicitly illustrative and does **not** represent validated full HP/TES integration, manufacturer compressor matching, dynamic operation or system-wide electricity use.

- [R718 finite-HX screening methods, equations and limitations](docs/methods/R718_FINITE_HX_SCREENING.md)
- Screening input assumptions: cases/r718_h0_screen_parameters.yaml
- Generate a hashed, unvalidated JSON result: python scripts/run_r718_reference.py
- GitHub Actions physics job installs CoolProp and executes real-fluid regression tests.

## M1/M2 development increments — explicitly not yet scientifically validated

- **M1 evidence and hydraulics:** published R718 impeller *nominal design* points and different-rig *measured maxima* are compared with the hypothetical R718 stage ratios; these reject the available reference-hardware fit, but are not complete compressor maps. Pressurised process/source/interstage liquid line-loss electricity, gearbox/inverter efficiencies and three heat-exchanger quadrature-refinement checks are now available. The example compressor-electric COP **must not** be used as system COP.
- **M2 charging-only coupling:** the condenser loop is linked to a conservative 1-D, 2-temperature gas/rock packed bed with geometry-based hA, Ergun pressure loss, blower electric energy, BDF transient temperatures, thermal wall loss and a time-averaged outlet-temperature fixed point. The required condensing temperature and compressor work now respond to storage state, and infeasible states terminate visibly. It does **not** yet deliver industrial process heat, match experimentally measured bed curves, contain real compressor maps, or establish cyclic TES round-trip performance.
- [M1 published compressor/auxiliary/HX methodology](docs/methods/M1_COMPRESSOR_HYDRAULICS_HX_EVIDENCE.md).
- [M2 coupled charging equations, tests, and exclusions](docs/methods/M2_R718_GAS_ROCK_CHARGE_ONLY.md).
- Rerun `python scripts/run_m1_reference_evidence.py` and `python scripts/run_m2_coupled_charge.py` with the optional physics dependencies. Machine-readable results are GitHub Actions artifacts, not fabricated precomputed performance figures.

**The published compressor evidence does not support the present high-lift 5:1-per-stage design.** The latter remains a numerical **hypothesis/control** pending a viable multi-stage compressor or alternative natural-fluid/cascade design. No architecture is yet experimentally validated or cost-optimised.

## Published nominal R718 compressor design-point reproduction

In addition to the original 80°C-source hardware-**unqualified** screen, the research code now contains a separate **2018 liquid-injection two-stage** R718 cycle matching the nominal stage pressure/temperature design conditions documented by Zühlsdorf et al. It predicts the second-stage mass flow and inlet volume flow without tuning them to the table. This uses a hotter **120°C illustrative source** and does **not** validate an 80°C-source installation, a vendor compressor speed line, or dynamic TES operation.

- [Read exact source, mass/enthalpy balance, independent comparison and remaining hardware gaps](docs/methods/M1_PUBLISHED_R718_INJECTION_DESIGN_POINT.md)
- Re-run: `python scripts/run_r718_injection_design.py` (CoolProp required; JSON archived by CI).

## Independent packed-bed experimental evidence — validation still open

The external-data workflow now retrieves and source-hashes a published CC BY 4.0 horizontal packed-bed dataset (DOI 10.17632/j37x6ptpk2.1). Four full runs (A–D), seven in-bed thermocouple channels, measured inlet/outlet temperatures, exhaust velocity and an uncalibrated native differential-pressure channel are archived as an Actions artifact. The project regenerates eight **measured-only** plots and four observed 80°C outlet crossing times, with Case A reserved as the proposed holdout.

**No experimental model-validation claim yet.** A related 2022 publication by the same team documents the 400 mm × 158 mm horizontal vessel, ~20 mm slag particles, ~0.39 estimated porosity and 50 mm thermocouple spacing, but exact 2024 apparatus identity, exhaust bore, absolute sensor offsets, logged pressure units/calibration, material properties and bed flow remain insufficiently confirmed. A second dataset (10.17632/fgn79fzg7x.1) advertises axial A1 plus radial R4 but its pinned public CSV contains **R4 only**—the provenance checker explicitly blocks using it for axial validation.

- [External packed-bed evidence, exact case hashes, observations, restrictions and holdout protocol](docs/methods/M2_EXTERNAL_PACKED_BED_VALIDATION_REGISTER.md)
- [Temperature/pressure validation comparators with strict source/holdout gates](src/carnot_battery_lab/validation/experimental.py)
- Unfitted preliminary 1D forward comparisons with Case B and an untouched Case A yield RMSE **38.1°C and 24.4°C** respectively, despite excellent numerical energy conservation. This is a documented **negative accuracy finding**, not validation; the flow calculation uses measured outlet temperature and an assumed exhaust-pipe bore. See the source/evidence register for uncertainty and caveats.
- [GitHub Actions external measured-data workflow](.github/workflows/external-benchmark-a1.yml)

## Source-compatible natural-fluid cycle screening — NOT compressor-qualified

The research code now includes a finite-HX real-fluid **R600 n-butane transcritical** candidate for the original **80→70°C waste-source / 110→150°C process** thermal service. It evaluates five high-side pressures with CoolProp, mass/energy balance, HX pinch and UA constraints and source/process flow limits. Numerically feasible points are explicitly **not matched to a manufacturer compressor speed/surge/choke/discharge map**, and the high-pressure search is **not a certified operating envelope**.

The [M1 natural-fluid evidence ledger](docs/methods/M1_NATURAL_FLUID_80C_ENVELOPE.md) separates experimental 60°C-source/160°C R600 operation, the 80°C-source/148.5°C R1233zd(E) experimental HFO prototype, R718 experimental 85°C evaporation/150°C condensation, and a 2019 *simulated* R600 80/75→80/160°C point. None alone proves the exact-target natural-fluid machine. CI generates `results/natural_refrigerant_80C_screen.json`.

## M2 rigorous flow and mesh uncertainty audit — numerical convergence NOT achieved

The 2024 horizontal-bed data have now been re-evaluated using only Case B for numerical-development/sensitivity experiments, with original experimental CSV hashes checked. The **16-cell base model is not spatially converged**: 16→32 cells changes the outlet trajectory by approximately 5.87 K RMS and shifts modeled 80°C breakthrough ~106 s; independent BDF substep/tolerance refinements have negligible effect. Assumed exhaust inner diameter (45/52/60 mm) and source-reported slag cp range (0.8–2.3 kJ/kg K) produce even larger temperature uncertainty. **These are uncertainty scenarios, not fitted effective instrument measurements.**

The validation tooling now refuses to convert raw pressure-channel values to Pa absent sourced instrument scale, zero, pressure-tap locations and independent pipe-loss correction. A separate **implicit exhaust-flow solver** now estimates density from **its own predicted outlet temperature**, not the experimental Tout being evaluated. On source-locked Case B its unfitted 16-cell RMSE remains **37.8°C** and breakthrough remains early. Removing target leakage is methodological progress, not proof of physical model accuracy. A new *optional* rock axial-conduction term uses pairwise conservative internal interface fluxes and adiabatic ends; source-locked Case B tests did **not** establish a real-model accuracy gain from adding conduction.

[Read the flow/pressure, grid and parameter uncertainty audit](docs/methods/M2_FLOW_PRESSURE_CONVERGENCE_AUDIT.md). Case A was already evaluated in the previous development iteration, so it is no longer described as a pristine blind holdout. Cases C/D remain withheld from numerical model fitting, but their measured descriptive summaries are already public and velocity-derived flow still uses measured outlet temperature.

## M2 source-backed 128-cell spatial refinement — still not resolution-qualified

The 1-D two-temperature gas/solid packed-bed solver now has an **exact analytical sparse BDF Jacobian**, regression checked against an independent finite-difference Jacobian across several meshes and optional axial conduction. The original conservative differential equations and integrated energy ledger are unchanged.

The source-locked 2024 horizontal-bed **Case B** study now extends 8→16→32→64→128 cells. Pairwise RMS outlet-temperature changes decline **9.89→5.87→3.25→1.72 K**, with first 80°C crossing shifts **184→106→57→30 s**. Approximate observed grid orders are **0.75, 0.86, 0.92**, consistent with first-order convergence. The finest result still fails the forward-looking **1 K RMS / 15 s** numerical refinement goals; external validation is separate and unpassed. Coarse-grid apparent agreement improves because numerical diffusion masks physical-model errors: Case B RMSE increases from **38.05°C at 16 cells to 43.23°C at 128 cells**.

- [Sparse Jacobian implementation and exact source-locked grid comparisons](docs/methods/M2_SPARSE_JACOBIAN_SPATIAL_CONVERGENCE.md)
- [Specific missing apparatus/instrument evidence needed to resolve mass flow and pressure](docs/validation/HORIZONTAL_BED_MISSING_METADATA_REQUEST.md)

**No full measured pressure calibration, actual exhaust bore, 2D horizontal-buoyancy validation or exact-target 80°C-source compressor map has been obtained.** As a result M1/M2 remain open; discharge, matched-service optimisation and v1.0 are not claimed.

## M2 512-cell numerical verification — physical accuracy still unqualified

A source-locked replay of the 2024 copper-slag packed-bed Case B now extends the conservative 1-D two-temperature model to **512 finite-volume cells** and independently verifies heat exchange against an analytical zero-flow solution.

- Original measured-outlet-informed flow: 256→512 **0.448 K** RMS outlet-profile change and **7.87 s** 80°C crossing shift; final measured-data RMSE **44.0°C**. **Not** an independent forward prediction because measured Tout enters the flow estimate.
- Target-independent implicit exhaust flow: 256→512 **0.595 K** RMS profile change and **6.40 s** crossing shift, meeting the pre-existing provisional **1 K/15 s** numerical screening limits. But 512-cell measured-data RMSE remains **50.1°C** and modelled 80°C breakthrough is about **173 s early**.
- 2025 source documents 2-inch nominal flanged pipes, NOT actual hot-wire-probe bore or schedule. NPS2 nominal Schedule 40/80 bores (52.48/49.22 mm) are explicitly conditional scenarios, not measured calibration. Raw 2024 pressure units and tap losses are still unverified; **no Ergun experimental validation** is claimed.

[Complete 512-cell methods and physical validation gaps](docs/methods/M2_512_CELL_NUMERICAL_VS_PHYSICAL_VALIDATION.md). The [dedicated reproducible GitHub Actions workflow](.github/workflows/m2-fine-mesh-case-b.yml) archives two Case B numerical JSON outputs, source hashes and three figures. **Physical predictive validation and scientific v1.0 remain blocked.**

## M2 original instrument source and mixed-phase thermocouple diagnostic

The original 2022 horizontal copper-slag rig methods explicitly state that seven Type-K thermocouple **sheaths contact both stones and air** (50 mm axial spacing). Comparing measured T1–T7 to **gas-only** or **solid-only** model temperatures is therefore not independently justified. The same methods locate pressure taps in inlet/outlet **pipes**, connected through stainless capillaries and 8 mm silicone tubing, with a Campbell Scientific CR1000 logger and Kanomax outlet hot-wire flow probe. The available 2024 data do **not** establish its raw ΔP channel units, calibration, true anemometer pipe bore or exact absolute TC locations.

New [source and instrument evidence](docs/methods/M2_MIXED_PHASE_SENSOR_EVIDENCE.md) and [source-hashed Case B T1–T7 observation operator](src/carnot_battery_lab/validation/sensor_phase_envelopes.py) evaluate a deliberately broad **phase/possible-position model-extrema interval**, without fitting any sensor offset or gas–rock mixture to observations. It is an exploratory diagnostic **NOT a measurement uncertainty interval or experimental validation**. The first source TCs are already used to initialise the model (assumed 0.05–0.35 m locations), so that sample is never scored. C/D remain untouched by model fitting.

The original public data provider lists an author contact for additional experiment metadata. A [specific author information request](docs/validation/REQUEST_HORIZONTAL_BED_INSTRUMENT_METADATA.md) is prepared **but has not been sent**. Source-qualified gas-flow and pressure instrument calibration, sensor response and actual material properties remain the M2 external-validation blockers.

## First source-backed mixed-phase Type-K sensor discrepancy — NOT validated

The new 128-cell Case B phase/position-extrema pipeline found that **46–56%** of measured T1–T7 readings lie outside even a permissive simulated gas/rock temperature envelope over all possible (unmeasured) axial first-sensor offsets, with maximum outside distances increasing up to **91°C at T7**. These are **source-locked exploratory incompatibility diagnostics**, not calibrated observation uncertainty or physical validation, and the sensor operator has not been separately grid qualified. The first thermocouple sample was used to initialise the model and excluded from scoring.

[Original instrumentation evidence and scientific limitations](docs/methods/M2_MIXED_PHASE_SENSOR_EVIDENCE.md) · [Author metadata request, prepared but not sent](docs/validation/REQUEST_HORIZONTAL_BED_INSTRUMENT_METADATA.md). Physical calibration and M2 remain **blocked** despite the previously demonstrated 512-cell outlet numerical convergence.

## Dynamic seven-probe mixed-contact observation (M2.1)

An independent **one-way thermocouple observation module** now applies one common axial layout (50 mm spacing), shared assumed gas/solid contact and first-order response time to all seven Type-K probes. Exact piecewise-linear sensor forcing integration is analytically tested. **No probe offset, contact fraction or time constant is fitted to experimental curves.** The source-locked 2024 Case B data study compares 27 fixed joint hypotheses to T1–T7 and still finds frequent disagreement (T7 readings outside the broad scenario band **52%** of the time, maximum outside distance **90.7°C**). These are **not calibrated error bars or experimental validation**.

[Read M2.1 methods and the seven-probe measured diagnostics](docs/methods/M2_DYNAMIC_TC_OBSERVATION.md). Physical validation remains source-limited and M2 open.

## M2.2 internal gas/solid numerical convergence verified on fixed coordinates

The target-independent Case B fine-mesh workflow now records both gas and rock model histories at **seven fixed, assumed physical positions (0.05–0.35 m)** on 32/64/128/256/512-cell meshes. At 256→512 cells the worst full-history RMS increment is **0.572 K for gas** and **0.553 K for rock**, meeting the provisional 1 K *numerical* screen for these inputs. A separate exact, closed-form two-temperature/no-flow exchange benchmark verifies phase temperatures and total energy independently of the BDF integrator.

[Read M2.2 source-locked in-bed numerical verification](docs/methods/M2_INTERNAL_TWO_PHASE_CONVERGENCE.md). **This is not laboratory TC validation:** the actual sensor coordinates and response, source gas flow and slag properties remain unresolved.

## Development and evidence

- [Master scientific research plan](docs/MASTER_RESEARCH_PLAN.md)
- [Scientific contract](docs/SCIENTIFIC_CONTRACT.md)
- [Definitions and metric boundaries](docs/methods/METRICS_AND_SYSTEM_BOUNDARIES.md)
- [Validation and v1.0 release gates](docs/VALIDATION_AND_RELEASE_GATES.md)
- [Literature and source registry](references/LITERATURE_EVIDENCE.md)
- [Actionable implementation backlog](docs/IMPLEMENTATION_BACKLOG.md)
- [GitHub publication instructions](docs/PUBLISHING_AND_GITHUB_SETUP.md)
- [Historical corrective audit](legacy_audited_screen/docs/SCIENTIFIC_AUDIT_2026-11-15.md)

## Licence and citation

A public software licence is **not selected** until the repository owner chooses
one. Do not imply this pre-alpha archive is already licensed for redistribution.
A CITATION.cff and dataset DOI will be added after the contributor attribution,
licence, provenance and scientific release strategy are approved.
