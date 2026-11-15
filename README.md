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
