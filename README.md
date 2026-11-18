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

## M2.3 variable-enthalpy and steel-shell-inertia alternative

A separately implemented, **conservative** thermophysical solver now computes ideal dry-air N₂/O₂ NIST Shomate sensible enthalpy and cp(T), uses a declared hypothetical temperature-dependent slag cp(T), and models a finite **7-mm nominal steel-shell thermal capacity** and two serial rock→wall→ambient heat-transfer interfaces. The original constant-cp source-locked solver is **unchanged**.

The independent synthetic four-step energy audit passed with ~**1.155 MJ** gas heat input and **0.0068 J** cumulative first-law residual. Tests verify `dh_air/dT = cp_air`, NIST segment continuity, gas/rock/wall conservation and physical guards. The actual 2024 slag batch material properties, wall UAs, gas pressure and measured flow are **not calibrated**; synthetic verification is **not external validation**. [Read M2.3 method and limitations](docs/methods/M2_VARIABLE_ENTHALPY_WALL_METHOD.md).

## M2.4 synthetic parameter identifiability — NO experimental fitting

A new deterministic, 7-parameter local sensitivity study varies the assumed exhaust bore, hot-wire gain, slag density and heat capacity, porosity, wall UA and gas conductivity, using only **synthetic** gas-temperature forcing. The verified model has two exact mathematical non-identifiabilities: **bore² × velocity scale** and **slag density × cp** cannot be separated using outlet temperature alone. Independent model runs preserved these aliases within numerical precision (~5.7×10⁻¹⁴ K or zero). The synthetic local-temperature SVD reports an effective rank of **2 at its declared 0.001 relative threshold**; that rank is *scenario, observable and threshold dependent*, not a Fisher-information or actual experimental parameter-identification result.

See [M2.4 model-only sensitivity and identifiability methods](docs/methods/M2_SYNTHETIC_IDENTIFIABILITY.md). No original 2024 Case A/B/C/D thermal measurements are fitted; pressure validation, physical sensor calibration and full M2 external validation remain blocked.

## M3 bidirectional TES and R718 charge-to-discharge handoff — UNVALIDATED

The conservative gas/rock packed-bed model now supports **physical reverse-flow thermal discharge** (cold process gas enters original x=L, hot exhaust leaves x=0), sampled process-temperature qualification, signed gas heat/exergy, separate modelled Ergun fan work, unclipped thermal state of charge and repeated charge/discharge **energy ledgers**. The synthetic short-cycle test returned **zero qualified high-grade heat and failed cyclic state closure**; a *separately* preheated uniform bed delivered **24.1 kJ** above the synthetic 350 K outlet cutoff. No round-trip efficiency is claimed.

The existing **TES-state-responsive R718 heat-pump charging simulation** is also now sequentially linked to this reverse-flow module using the actual post-charge storage state. In source-controlled real-fluid tests, the candidate gas 80→110°C stream gained ~**105.2 MJ**, but none met the 110°C outlet requirement. The target industrial gas 110→150°C stream instead *lost* ~**30.5 MJ** to the insufficiently hot bed, and delivered **zero qualified process heat**. These are valuable negative feasibility results for one illustrative charging trajectory, NOT proof that a hardware-qualified HTHP/storage system cannot ever supply that service.

Both modules explicitly **refuse experimental hardware qualification, a validated compressor map, cyclic RTE or matched-service architecture comparison**. Source lab gas-flow and pressure calibration, measured slag/sensor inputs, qualified compressor envelopes, actual process HXs, full cyclic steady state and independent physical validation remain outstanding.

- [Standalone M3 reverse-flow, service-grade and cycling methods](docs/methods/M3_REVERSE_FLOW_THERMAL_CYCLES.md)
- [R718 TES-state charging to process-discharge integrated screening](docs/methods/M3_R718_SEQUENTIAL_THERMAL_SERVICE.md)
- [M2.4 source-independent structural identifiability caveats](docs/methods/M2_SYNTHETIC_IDENTIFIABILITY.md)


### M3.2 repeated thermal-cycle gas-service feasibility (unvalidated)

The source-controlled finite-schedule scan now reuses **each previous discharge's actual full packed-bed temperature field** for the next R718 charge, enforcing a per-interval 110→150°C / 1 MW gas-proxy grade and two consecutive full-field thermal-cycle closure checks. The initial outlet-temperature sample is corrected to the physical downstream cell, with regression tests. The scan retains signed heat and first-law ledgers, and reports blocked/incomplete cycles rather than inventing service. The original 80°C-source compressor map, process-liquid HX, packed-bed experimental validation, and round-trip efficiency are **not qualified**.

See [M3.2 matched gas thermal service and cyclic closure method](docs/methods/M3_MATCHED_GAS_CYCLIC_SCREEN.md).

### M1.4 compressor map requirements — evidence gate still OPEN

A reproducible real-fluid dossier now exports required **suction pressure, temperature, density, actual volumetric flow, stage ratio, discharge temperature and shaft duty** for the reference 80→70°C source / 110→150°C, 1 MW heat pump and for TES-state-responsive charging points. Each computed requirement is crosswalked against separately classed published R718/R600 experiments and theoretical comparators. Literature evidence does **not** supply a manufacturer-qualified map at the full original contract; no map is synthesized from isolated COP/maximum-temperature points.

See [M1.4 map-requirements methodology and sourcing](docs/methods/M1_4_COMPRESSOR_OPERATING_REQUIREMENTS.md). No compressor or process-side heat exchanger is certified; architecture ranking remains blocked.

### M1.5 measured compressor-map acceptance — fail-closed evidence screening

The M1.4 real-fluid operating demands can now be tested against separately supplied, machine-specific **measured compressor maps**, when available, without inventing missing data. M1.5 requires stage and topology identity, declared machine pressure/speed/thermal limits, a fixed-speed *measured interior* for every operating point, independent withheld map tests, and separate validation of flow, power and discharge-temperature predictions. The default CI intentionally supplies **no actual map** and publishes the negative result. Synthetic fixture success proves only the numerical acceptance algorithm, **not hardware suitability**. Physical map authentication, full R718 charge trajectories, startup/control/surge and 1 MW liquid process heat still require independent evidence.

See [M1.5 map acceptance methodology](docs/methods/M1_5_MEASURED_MAP_ACCEPTANCE.md).

### M1.6 authentic experimental-data acquisition — no target-map qualification

Open original compressor and Carnot-battery heat-pump/TES measurements are now source-audited separately from synthetic manufacturer-polynomial data. A fixed-checksum ETH/OST n-butane experimental dataset is compared with the exact M1.4 R600 compressor requirements, while the University of Duisburg-Essen independent HP/TES experiment archive is inventoried without publishing third-party raw data. Both provide **off-target validation opportunities**, not a measured 80→70°C / 110→150°C, 1 MW H-REF compressor map. The M1.5 hardware acceptance gate remains open. See [M1.6 acquisition and research ethics](docs/methods/M1_6_PUBLIC_EXPERIMENTAL_DATA_ACQUISITION.md).

### M1.7 R600 out-of-sample experiment — other compressor, not H-REF hardware qualification

The independent OST Buchs n-butane compressor campaign is now tested with a frozen, **condition-disjoint five-group reserved holdout**. The original M1.4 shaft-efficiency hypothesis is converted to its matching **overall electrical** meter boundary (0.74 × 0.95 × 0.98 = 0.68894), then compared with actual measured `eta_is,electric`; a training-only 2-parameter pressure-ratio ridge fit serves as a separately labelled exploratory comparator. Training-hull membership, observed volumetric efficiency and CoolProp ideal-work sanity are audited. No synthetic manufacturer-polynomial records, pure/mixture mixing, data leakage or target compressor-map extrapolation are permitted. See [M1.7 scientific validation methodology](docs/methods/M1_7_R600_RESERVED_OFFDESIGN_VALIDATION.md). H-REF equipment and architecture-viability gates remain blocked.

### M1.8 original UDE R600 measurement independence gate

The [Duisburg-Essen Carnot-battery laboratory dataset](https://doi.org/10.5281/zenodo.18712882) contains **six author-labeled original butane experimental summary conditions** with measured compressor mass flow, absolute P/T and electric inverter-input power. Its three separate Bitzer logs contain **6,839 correlated, sparsely populated device-controller entries**; their `R290` controller setting conflicts with the butane experiment filenames, and they provide no jointly valid compressor P/flow/power snapshots. M1.8 verifies publisher MD5, independently recalculates measured-source overall electric efficiency with CoolProp, reserves entire original experimental summaries for train-only benchmark checks, and tests same-frequency convex-hull support. The **five original M1.7 OST holdouts, hashes and out-of-sample MAE stay unchanged**, with no cross-machine pooling, invented calibration, source-model redistribution or H-REF equipment qualification. See [M1.8 original experiment evidence validation](docs/methods/M1_8_UDE_INDEPENDENT_R600_RUN_VALIDATION.md).

### M1.9 original compressor-map acquisition — manufacturer control limits and research requests

Official Sabroe/Johnson Controls **UniSAB 4 Rev 005 item 30** documents an **R600 HPC/HPO high-pressure shutdown setting of 36 bar**, versus our R600 numerical 40–60 bara discharge demands. M1.9 explicitly screens **both possible gauge/absolute interpretations**, failing all five nominal HPC/HPO cases robustly, but never mislabels a controller setpoint as mechanical design pressure. HPX generic 65-bar-design / 57.5-bar-shutdown **does not establish R600 approval**. Original SINTEF R718 measured 2020 stage peak ratios (2.4/2.0) and 2024 1–2-bara inlet rig similarly fail direct transfer to our two-stage 25-kPa source case. The 2026 OST 439-measured-point publication's original Table 1 contains **no pure R600**, despite broad *all-fluid* pressure coverage. Targeted, original-source/rights-specific data requests are ready, **not yet sent**. No exact-target measured maps have been acquired or accepted. See [M1.9 scientific source and acquisition dossier](docs/methods/M1_9_PRIMARY_MANUFACTURER_MAP_ACQUISITION.md).

### M2.1 original packed-bed experimental validation protocol (independent of compressor vendors)

Independent source studies include Weber et al.'s [nine experimentally measured shallow air/particle packed-bed runs](https://doi.org/10.17632/3pp86gdvh4.2), recording time-resolved thermocouples and bed differential pressure, and a separate [axial/radial copper-slag air-bed charging/discharging series](https://doi.org/10.17632/fgn79fzg7x.1). M2.1 includes original dataset discovery/provenance, **whole-experimental-run** calibration/holdout grouping, strict TC position/time and calibration-field admission, fail-closed measured bed-only pressure-loss correction and *unfitted* Ergun diagnostics. A time-aligned temperature scoring routine is available but never marks its own generated predictions as independent empirical validation. **The current original dataset APIs did not yet provide accessible raw time histories**, so measured breakthrough and measured pressure-loss validation **have not occurred**; simulated fixtures and API source metadata are never treated as experimental proof. This work requires **no R718/R600 manufacturer compressor reply**. See [M2.1 experiment acquisition and validation design](docs/methods/M2_1_PRIMARY_PACKED_BED_EXPERIMENT_DATA_PLAN.md).

### M3.4 actual industrial process-liquid heat delivery boundary (NOT gas outlet)

The industrial benchmark requires **1 MW gross heat to liquid at 110→150°C**. M3.4 uses a distinct **counterflow hot gas→process water HX** with conservation-derived gas cooling, original water mass flow ~5.981 kg/s at assumed 4180 J/(kg K), nominal 5 K internal approach, actual liquid pressure-vs-150°C saturation requirement and separately estimated required UA. The original R718→TES→reverse gas discharge model yields **only ~102.6–114.4°C simulated hot-gas outlet** during the three original 60 s industrial-service intervals—far below **155°C** needed for a 150°C liquid outlet even before finite-capacity gas cooling. **All 9 original gas temperature samples fail the necessary liquid-HX hot-terminal temperature-grade test**. This is a **specific, model-only negative result**, not a claim no physical HT heat pump could perform the original service. Installed process-water pressure, HX UA, compressor maps and experimentally validated packed-bed pressure/breakthrough remain unknown. No liquid-process heat or matched architecture RTE is certified. See [M3.4 liquid process HX necessary-condition audit](docs/methods/M3_4_PROCESS_LIQUID_HX_NECESSARY_SCREEN.md).

### M3.5 hypothetical electric-heater-to-TES-to-1MW-process-liquid thermal envelope

Independent of R600/R718 compressor maps, [M3.5's reproducible thermal operating envelope](docs/methods/M3_5_THERMAL_GRADE_OPERATING_ENVELOPE.md) uses an **explicitly assumed ideal resistance heater**, 4.5 MW electrical input limit, original 4×5 m air-like gas/rock bed, charging at 150–260°C for 4 min–8 h, reverse gas discharge and a **separate 1 MW 110→150°C process-liquid HX necessary-condition screen**. The old 4-minute schedule fails; 220°C for 2h passes a *sampled* full 1h necessary gas-to-liquid duty screen under synthetic assumptions, at **12.95 GJ modeled source gas heat / 3.60 MWh ideal charge-heater electricity**, with further unqualified cooler and hydraulic work. The **10-minute discrete charging search** on 16/32/64 cells brackets the *first sampled model pass* between **50 and 60 minutes**, but **cannot establish a physically minimum charging time, a continuous temperature guarantee, a real liquid heat delivery, an installed UA, process pressure or round-trip efficiency**. The finite-volume bed, uncalibrated Ergun gas pressure loss, ideal heater and missing real equipment/experimental data remain strict limitations. See the [executable parameter scan](scripts/run_m3_5_independent_thermal_service_envelope.py), [source-independent simulator](src/carnot_battery_lab/physics/independent_thermal_envelope.py) and [negative/positive physics tests](tests/test_m3_5_independent_thermal_envelope.py). **M1/M2 hardware and experimental qualification remain open**.

### M3.6 — dynamic separate process-liquid HX and fully audited gas-return heat balance

Building on M3.5, [M3.6 dynamic process-water HX and return-loop method](docs/methods/M3_6_DYNAMIC_LIQUID_PROCESS_HX_AND_RETURN_LOOP.md) models a **three-inventory, time-dependent, counterflow gas/metal/process-water heat exchanger** downstream of the 1D gas/rock TES. It uses **CoolProp water h(T,P) and cp(T,P)** to derive the exact nominal 1 MW 110→150°C process-water mass flow (rather than mixing a fixed-cp flow with real water enthalpy); imposed **2 MPa absolute process pressure** and **40 kW/K overall HX UA** remain **explicitly uninstalled/uncalibrated hypotheses**. The code accounts for gas, metal and liquid holdup, all independent first-law ledgers, thermal startup, gas-return conditioning cooler/reheater, and hypothesized fluid pressure losses and pump/fan power. On the original 220°C assumed 2h gas charge, an **initially cold** HX fails the initial full-duty requirement, while a **separately charged 10-minute warmup** gives a model-only 1h nominal water-outlet grade screen pass with water outlet ~160.46→152.40°C at HX N=8, bed N=16, step 60s. **A 10 kW/K assumed UA fails** and 0.4 MPa assumed water pressure fails the 150°C liquid-phase criterion. The gas cooler would need to reject ~1.55 GJ thermal over 70 min, but **no cooler equipment is installed or power-validated**. The result is sensitive to spatial resolution: HX N=4 fails whereas N=8/12/16 pass, and refining the packed bed N=16→32 shifts the final liquid outlet by ~1.9 K. Above-150°C water requires unmodelled outlet trim/flow/bypass regulation. These are **sampled model-only ability screens**, NOT verified physical 1 MW delivery, actual plant controls, gas absolute pressure, 80°C-source compressor viability, experimental TES calibration or whole-system RTE. [Executable study](scripts/run_m3_6_dynamic_liquid_process_service.py) · [HX solver](src/carnot_battery_lab/physics/transient_liquid_hx.py) · [coupled return-loop energy audit](src/carnot_battery_lab/physics/coupled_transient_process_loop.py) · [adversarial tests](tests/test_m3_6_transient_liquid_hx.py).

### M3.7 — exact-process-water controller failure audit, dry-air EOS and independent bed/HX convergence

The [M3.7 method and results](docs/methods/M3_7_BYPASS_GAS_EOS_CONVERGENCE.md) add a **mass-conserving hypothetical hot-gas bypass valve** to M3.6: all process water retains the *same* precisely enthalpy-derived **1 MW, 110→150°C** flow; 10–100% of hot gas can pass through the gas/water HX and the bypassed fraction is recombined before an **uninstalled 110°C-return cooler**. The simulated predictive valve has an explicit **40 percentage-point/60s actuator movement limit** and targets **1 MW interval-average liquid enthalpy duty (±1.5 kW)** while independently checking that all accepted numerical water-outlet states remain **150±0.5°C**. An uncontrolled hot-water temperature exceeding 150°C is **not** itself a controlled exact-150°C service. With original 220°C/2h gas charge and 10-min warmup, the controller switched on immediately **fails (0/60 service minutes)**; giving the HX **120s explicit full hot-gas startup** before valve activation improves the **sampled contiguous water setpoint/duty pass to 48/60 min**, still **fails the one-hour contract**. In parallel, a strictly separate [CoolProp HEOS::Air EOS sensitivity](src/carnot_battery_lab/physics/air_eos_sensitivity.py) quantifies the temperature-dependent dry-air density, cp, viscosity and enthalpy for *assumed* 101/250/500kPa gas pressures: actual gas-loop pressure is **unknown**, so the existing bed/HX constant-property model remains unchanged and is **not secretly claimed variable-EOS-validated**. Additional independent bed N16/32/64, HX N8/12/16 and 60→30s checks still show spatial outlet sensitivity **~1 K**. Numerical conservation and negative control tests pass, but **manufacturer compressor maps, actual gas pressure, original measured bed holdouts, installed valves/UA/cooler, complete continuous 1MW liquid delivery and electrical Carnot RTE remain unqualified**. [Controlled source audit](scripts/run_m3_7_control_and_eos_audit.py) · [bypass physics](src/carnot_battery_lab/physics/process_gas_bypass_control.py) · [tests](tests/test_m3_7_bypass_and_air_eos.py).

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

<!-- portfolio-reader-guide-2026:start -->
## Engineering portfolio reader's guide (November 2026)

**What to inspect:** The new HTHP/TES research foundation: read the finite-heat-exchanger and charge-side coupling methodology alongside the withdrawn legacy architecture ranking and unresolved compressor/experimental evidence.

**Portfolio context:** [Project or engineering selection](https://abhijith-sivaprasadan.github.io/projects/carnot-battery-lab.html) · [Armada 2026 employer-facing selection](https://abhijith-sivaprasadan.github.io/for/armada-2026.html).

These navigation links do not supersede the research status, assumptions, provenance, licences or validation limits documented above. This independent research project is not an employer-commissioned deliverable or externally qualified engineering product.
<!-- portfolio-reader-guide-2026:end -->
