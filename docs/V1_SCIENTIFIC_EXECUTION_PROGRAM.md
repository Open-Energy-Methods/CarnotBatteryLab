# CarnotBatteryLab — Scientific v1.0 Execution Programme

**Plan revision:** 2026-11-15 / proposed for review  
**Status:** planning specification only; not evidence that the physics or v1.0 is implemented  
**Repository baseline:** v0.1.0 foundation; the withdrawn legacy A/B/C ranking remains in legacy_audited_screen  
**Related contracts:** MASTER_RESEARCH_PLAN.md, SCIENTIFIC_CONTRACT.md, VALIDATION_AND_RELEASE_GATES.md, METRICS_AND_SYSTEM_BOUNDARIES.md  
**Scope:** full research-grade **industrial heat** family H, with explicitly separated electricity-return family E as a later independent scientific release; no artificial calendar deadline.

## 0. Thesis and v1.0 claim

**Research question:** Under matched industrial heat-service conditions, how do the thermodynamic cycle, heat-exchanger network, TES medium/geometry, supervisory operation and electricity-price regime determine feasible, nondominated, cost-effective HTHP+TES architectures, and how robust are these findings to physical, economic, numerical and temporal uncertainty?

**v1.0 is a model-based scientific release, not an experimental certification**. It must deliver:
1. Independently benchmarked real-fluid natural-refrigerant high-temperature heat-pump cycle(s), with demonstrated source/sink/HX and compressor-envelope feasibility.
2. Dynamically solved, geometry-based **gas/solid packed-bed**, **liquid/solid dual-media thermocline** and **two-tank molten-salt** storage components, each inside a documented material/temperature envelope. Feasible *integrated system* comparisons must be restricted to shared service contracts; inapplicable configurations are reported as infeasible, not artificially given zero efficiency.
3. A causal coupled HP–HTF–TES–process HX flow network including temperature feedback, auxiliary electricity, start/stop, part-load and qualified process-heat delivery.
4. Reproducible design sizing, constrained price-responsive dispatch and *multi-objective* architecture optimisation; Pareto candidates re-simulated using reference nonlinear physics.
5. Equal-service direct-HP H0 baseline plus at least two genuinely distinct feasible HP+TES layouts evaluated under the same reference case. A third fully integrated salt layout must be shown under a separately qualified compatible high-temperature/low-melting-salt boundary if the reference service cannot charge it; **never invent apples-to-apples equivalence**.
6. Independent numerical and, if available, empirical validation; mesh/time/property convergence; uncertainty sensitivity; financial source provenance; machine-readable cases/results; open reproducibility package and comprehensive limitations.
7. A complete methods-and-results report with two paper-shaped studies: **R1 architecture and thermo-hydraulic trade-offs**; **R2 dynamic price flexibility, LCOH and robust sizing**. Optional R3 P2H2P requires an independently modelled discharge power cycle, not a renamed thermal COP.

A green software CI, a multiobjective scatterplot or a simulated transient alone is not sufficient. No claims of industrial predictive accuracy without independent experimental evidence.

## 1. Research questions, hypotheses and counterexamples

| RQ | Falsifiable hypothesis / alternative | Key response variables | Required null/control |
|---|---|---|---|
| Q1: cycle and source | finite HX approaches, condensing pressure and part-load limits materially change charge feasibility and electricity vs constant COP | cycle COP map, compressor work, approach/pinch, infeasibility domain | ideal Carnot upper bound; HTHP-alone |
| Q2: storage configuration | thermal effectiveness and useful capacity are jointly limited by stratification and pressure-drop/auxiliary trade-offs | temperature histories, exergy destruction, fan/pump work, useful hours | adiabatic tank/bed limiting case; matched 6 h useful delivery |
| Q3: dynamic operations | price-flexible dispatch may lower operating cost but raise gross electricity and total annualised capital cost | annual electricity, peak import, heat deficit, starts, LCOH, economic break-even | continuous/direct HP, no flexibility, rule-based dispatch |
| Q4: optimisation and uncertainty | nondominated architecture ranking and sizing may reverse under source, price, cost, thermal property or service uncertainty | feasible Pareto set, annual NPV/LCOH, rank reversal frequency, regret | fixed-design and dominated comparators |
| Q5: extension | an electricity-return heat engine fundamentally changes all primary performance denominators | net electric round-trip efficiency | do not evaluate until E-engine model exists |

Report negative results as genuine findings (e.g., TES cost cannot be recovered, pinch infeasible, no workable salt temperature window, larger media volume not helpful).

## 2. Mandatory architecture taxonomy and comparability

### H0 — direct natural-fluid HTHP, no TES
All source/sink equipment, HX pressure loss, auxiliary electrical work, backup supply policy and controls costed consistently. **Mandatory** counterfactual.

### H1 — HTHP → intermediate HTF/HX → gas/rock packed-bed
Two-temperature gas/solid bed with flow reversal, geometry-derived interfacial exchange and Ergun pressure drop. Explicitly account for circulation fan and gas–refrigerant isolation HX. If the process-side transfer needs another HX, include it.

### H2 — HTHP → liquid HTF + solid filler dual-media thermocline
**Dual-media means liquid HTF and separate solid filler**, not two sizes of rocks. Explicit liquid-temperature window, pump electrical work, freeze/mixing/stratification limits, and HTF/solid temperature-dependent properties.

### H3 — HTHP / specified auxiliary upgrade → two-tank molten salt
Mass and energy inventories for two tanks, cold/hot temperatures, minimum withdrawal levels, wall/heel/standby losses, heat tracing, minimum liquid temperature, pumps, materials/corrosion/safety limits, and complete upstream charge-upgrade energy and CAPEX. Do **not** use a 30–145 °C loop with Solar Salt: conventional nitrate salt melts around 220 °C and typical Solar-Salt cold-tank duty is around 290 °C. A sourced lower-melting salt such as a HITEC-type nitrite/nitrate mix may be independently evaluated (reported freezing point ~142 °C), with conservative engineering margins and material/safety review. Solar Salt demands its own genuinely hotter charging configuration. Never transfer Solar Salt or Gen3 chloride cost figures into a different salt/temperature regime.

### H4 — optional high-temperature process-specific variants
PCM, direct-steam MVR, cascaded R717/R718 or alternative natural gas-cycle heat pumps only where they answer a declared RQ and have distinct evidence. Do not dilute the benchmark set by forcing arbitrary extra architectures.

**H-family service parity:** same supply temperature/pressure/quality, load chronology, availability, source boundary, annual useful demand, reliability target, cost currency/price year, lifetime, discounting, dispatch knowledge and backup policy. Annual qualified heat must be delivered at the specified process HX boundary. Unserved heat and backup consumption reported separately. Do not force exact same compressor size if size is an optimisation variable; instead enforce identical feasible design space and service constraints.

**E-family:** only with explicit heat engine, rejecting heat appropriately, electrical import/export meters and valid electric round-trip definition. This branch must never inherit H-family v1.0 claims.

## 3. Reference service contracts and test matrix

All numbers below are **experiment design inputs**, not measured plant data, solved cases or anticipated performance.

| Case | Service/source | Duty | Research role |
|---|---|---|---|
| H-REF | 150 °C supply / 110 °C return; 80 °C source; 20 °C reference environment | 1 MW_th nominal, 6 h **qualified** TES discharge, 15 min dispatcher | primary equal-service H0/H1/H2 study; H3 only if independently feasible |
| H-LIFT | H-REF with 60 and 100 °C source alternatives | same declared process heat service | source-lift sensitivity, compressor boundaries |
| H-LOAD | continuous and intermittent matched-energy heat-load profiles | fixed annual qualified output | shape and duty-flexibility influence |
| H-PRICE | two or more verified national price areas and two separate, dated market years | preserve timezone, DST, negatives, missingness | design vs independent price-year holdout |
| H-HOT | challenging 250 °C process supply / 210 °C return / 80 °C source | 1 MW_th nominal (illustrative) | high-temperature and salt/upgrade feasibility **screening**, not automatically valid |
| H-STRESS | rapid price jumps, source loss, low SOC, off-design, ramp-limited start, hot/cold storage starts | physically bounded stresses | controls and reject/exclude checks |

Reserve one price year or entire chronological year as untouched external scenario to assess generalisation; avoid randomly splitting hourly observations. Synthetic prices may test implementation but never substitute for source-verified market evidence in the scientific conclusions. Reserve at least one **whole experimental run** or independently published experiment for held-out physical validation when the data permit.

Minimal comparative study groups:
- **R1 thermo-hydraulics:** common 150 °C service, H0/H1/H2 + separately qualified H3; geometry sweep (bed aspect ratio, particle size, porosity, HTF flow, insulation, HX UA). Outcomes: qualified energy, useful time, delta P, electric auxiliaries, entropy/exergy ledger, storage-system CAPEX.
- **R2 dispatch:** fixed feasible finalists from R1 plus H0; chronological year and representative weeks; rule baseline vs MILP/MPC; resimulation with nonlinear dynamics. Outcomes: LCOH, purchased electricity, price-weighted import, unserved heat, ramp/start counts, cost of flexibility.
- **R3 robust optimisation:** mixed discrete topology/cycle + continuous sizing, multiobjective cost/electricity/peak import or reliability; uncertainty and held-out price-year, Pareto re-evaluation and infeasible explanation.
- **R4 optional P2H2P:** completely separate study contract with power-cycle discharge and storage thermal reference states.

Factorial full-year runs need not enumerate every combination: pre-register design-of-experiments and surrogate selection policy, with independent confirmation of Pareto regions and boundary cases.

## 4. Physics architecture, fidelity and solvers

### Thermophysical property kernel (S1)
SI-only internal quantities; pinned backend versions (CoolProp Water/HEOS and IF97/IAPWS water cross-check; qualified natural organics where relevant). Reject metastable, two-phase or out-of-domain states unless handled explicitly. Internal states include h, s, T, P, density, quality/phase label, valid range, fluid and backend version. Property-cache interpolation error quantified. Keep pressure and entropy terms in exergy; reference dead state consistently.

### Natural-fluid HP and finite HX (S2)
At least one fully closed, independently benchmarked water/steam R718 or natural hydrocarbon cycle; ideally two distinct cycle families in applicable pressure/temperature envelopes. Model compressor η_is or maps, motor/drive electrical input, pressure ratios, volumetric flow, suction/discharge envelopes, multi-stage/flash where feasible, evaporator, condensation/heating glide, process and storage HX, pinch/UA/pressure drop, start-up and part-load. Water R718 steam compression and organic cycles must not be represented by the same parameter-free efficiency. Compute COP only for a feasible, qualified heat delivery.

Finite HX must use distributed enthalpy-profile or segmented exchanger checks, including phase-change pinch; a simple average log-mean approach is insufficient if phase/temperature crossover occurs. Source-side finite thermal capacity and return temperature must affect available HP heat.

### Gas/solid packed bed (S3)
Conservative finite-volume 1D coupled fluid/solid energy storage with real void volume and inventory; temperature-dependent heat capacity, fluid properties and a geometry-connected Nusselt/HTC correlation; flow reversal; axial effective conduction and wall/ambient loss as justified. Charge/discharge/standby modes and end-state matching. Momentum equation or Ergun pressure drop and fan efficiency; pressure-dependent gas exergy and fan heat where material. Integrator tolerances independent of mesh; 3+ refinement levels and temporal independence.

### Liquid/solid thermocline (S4)
Separate liquid and filler mass inventories and energy equations; porosity, temperature-dependent liquid properties, axial mixing/conduction, fluid/solid heat transfer, stratification, pumps and HX. Material compatibility and freezing constraints per operating point. Check limits versus established thermocline model and external data; document where 1D cannot reproduce observed radial effects.

### Two-tank salt (S5)
Two dynamic mass/enthalpy tank inventories; hot and cold mass flows, fluid-loop pressure loss, pump work, finite HX, thermal losses, trace heat and empty/heel constraints. Explicitly test low-melt candidate against sourced property/stability/compatibility bounds; optionally model Solar Salt only for a qualified high-T booster pathway. Salt model may be valid independently while a specific H3 integrated comparison remains infeasible—report both separately.

### Plant coupler and modes (S6)
Graph/typed ports for refrigerant, gas, liquid HTF, heat and electricity; connection equations enforce mass/h/pressure conservation and heat exchanger two-side heat balance. Distinct modes: direct process, charge plus process, charge only, TES only, bypass, standby, cooldown and controlled start. Couple TES state to upstream hot-side condensing/heat pump work, not post-process a constant COP. Use algebraic residual norms, event detection, consistent transient inventories, actuator rate constraints and explicit infeasible-state exceptions. A full-year F1/F2 solution must be checked against higher-fidelity reference weeks and representative extreme transients.

## 5. Optimisation as a verified engineering experiment

1. **Feasibility-first enumerator:** reject unsupported fluid/material/temperature/pressure/heat-exchanger combinations before optimisation; preserve reason codes.
2. **DOE and sensitivity:** scaled Latin hypercube/Sobol across physical variables; produce correlation and numerical-error maps with seed/sample manifests. Validate model surrogates with disjoint split by parameter domain and deliberate OOD tests if surrogates are used.
3. **Sizing:** discrete cycle/HTF/TES network and continuous heat pump rating, UA, bed/tank size, height/diameter, particle size, insulation, flow, SOC window, pressure loss limits. Explicit engineering and budget bounds.
4. **Dispatch:** MILP if piecewise-affine surrogate is validated; otherwise nonlinear optimisation / rigorous simulation-control loop. No storage simultaneous charge/discharge absent justified topology. Thermal demand, start count, min on/off, ramp, SOC, process supply temp and peak grid constraints mandatory.
5. **Multi-objective:** use epsilon-constraint for interpretable efficiency–LCOH trade-offs plus independent nondominated sorting/evolutionary cross-check. Select objectives deliberately: annual qualified heat LCOH, net purchased electricity or exergy input, and peak grid draw/flexibility as either third objective or constraint. Emissions are scenario-specific; do not mix thermal and electrical energy units.
6. **Truth-check every candidate:** high-fidelity nonlinear resimulation across all relevant seasons and a held-out price year; recompute objective and feasibility from actual states, not from MILP variables. Rejected points never enter the final Pareto plot.
7. **Robustness:** economic price year, input source temperature, heat-transfer correlations, compressor maps/part load, HTF ageing, tank loss, installed CAPEX and debt/discount assumptions. Report frontier bands, ranking/regret, infeasibility probability and the practical boundary where storage stops making financial sense.

## 6. Accounting and service metrics

All metrics have machine-readable boundary definitions and uncertainty:
- **COP_cycle** = condenser/heating-duty rate divided by relevant compressor electric input, evaluated only at defined cycle boundary; **COP_system** = cumulative qualified process heat / total purchased electricity at plant boundary (with explicit external waste-heat source). Neither equals a pure storage round trip.
- **TES delivered-heat fraction**, **TES exergy ratio**, **bed first-law closure**, **useful hours**, **thermal cyclic-state residual**, **process-unserved-heat** and **auxiliary consumption** use full time integrals and common terminal storage state.
- **Electrical round-trip efficiency (E only)** = net electricity exported / net electricity imported over a defined full cycle; external heat inputs and inventory changes disclosed.
- **Economics:** installed CAPEX by subsystem, year/currency and scale basis, replacements, financing/real discount rate, annual OPEX, LCOH, annual savings vs H0, NPV/break-even and uncertainty. Never conflate indicative literature unit costs with project-specific procurement estimates. Include maintenance, trace heaters, control equipment, safety, pressure vessels and balance of plant.
- **Flexibility:** ramp MW_e/min, sustained MW_e reduction at constant qualified heat, response time, recovery energy, starts, hours unavailable, peak-import changes, and effect of forecast error.
- **Emissions:** separately report source-matched hourly electricity emissions method (average vs marginal), baseline boiler/heat source and embodied-material coverage; no unsupported carbon-savings claim.

## 7. Validation-first acceptance evidence (details in the execution matrix)

**V0:** internal identity, property domain, analytical null/limiting case and negative-control tests.  
**V1:** independent numerical benchmark (published tables/curves or hand-derived analytical solutions).  
**V2:** independently developed numerical model or external FMU crosscheck under matched boundaries.  
**V3:** calibrated experimental records and held-out campaigns, if obtainable.

For each validation: freeze data licence/source, geometry, operation, sensors/time alignment, solver and accepted error metric before fitting. Separate thermal, hydraulic and compressor parameter calibration from validation; document identifiability. Use uncertainty-aware acceptance bounds rather than adjusting models until they pass. No independent-data access = no experimental predictive-accuracy claim.

**Numerical preregistration:** (a) component and integrated energy conservation; (b) mass and inventory closure; (c) entropy/exergy generation nonnegativity within residual tolerance; (d) mesh/time/property sensitivity using at least 3 resolutions and numerical-uncertainty report; (e) multiple-cycle terminal-state matching; (f) pinch and material-limit failure tests; (g) optimised schedule re-simulation. Targets defined in the validation matrix are *provisional engineering screening values*, subject to published benchmark uncertainty and physical numerical order.

**Scientific holdout:** preserve full out-of-sample price years and complete experimental test runs; calibrating only on one dynamic trajectory and calling every subsequent time step independent validation is forbidden.

## 8. Development phases and dependencies (no calendar deadlines)

| Milestone | Includes | Exit proof and hard gate |
|---|---|---|
| M0 Contract + evidence register | cases, matrix, DOI/source provenance, metric ledger, architecture diagram, false-claim audit | consistency, CI, immutable input/run identifiers |
| M1 Natural-fluid HP+HX | S1/S2, 150 °C case qualified state, compressor/part-load feasibility | V0+V1 state table, cycle/HX/exergy closure; H0 reference |
| M2 Gas/rock TES | S3 cyclic and standby, geometry, HT/pump trade-off | mesh/time + independent bed curve, energy/ΔP, repeated cycles |
| M3 Liquid/solid and salt | S4/S5, sourced property envelopes, thermal-hydraulic models | independent component tests, salt exclusions where physically invalid |
| M4 Real hybrid integration | S6 state feedback, operating modes, 24 h+week tests | end-to-end conservation, load-service proof and automatic feasibility flags |
| M5 Service parity and costing | installed equipment estimates and comparable H0/H1/H2, scoped H3 | audit-grade cost/inventory definitions and valid equal-service study |
| M6 Dispatch/control | price-quality checks, rule baseline, MILP/NLP resimulation, response | no false supply claims, constraint and forecast-error tests |
| M7 Multi-objective research | design exploration, optimisation, UQ, validation of finalists | traceable feasible frontiers, numerically insensitive interpretation |
| M8 Independent external audit | V1/V2+available V3, ablation, negative controls and year holdout | stable results and no circular validation |
| M9 Research release | report, data package, figures, CI and scientific claim ledger | all required release matrix gates pass, no contradiction/rights gap |

This is an **evidence dependency graph**, not a requirement to wait until all model components are complete before any integration testing. Every milestone ends with reproducible tests/figures and an explicit limitation statement.

## 9. Deliverable figures, tables and studies

### Paper-shaped Study A: architecture and physical design
- Fig A1: four explicit P&ID/thermal schematic layouts including validated charge pathway.
- Fig A2: R718/selected natural-fluid log(p)–h and T–s states, compressor and pinch maps.
- Fig A3: axial fluid/solid temperature evolution through charge, hold, reversal and discharge for H1/H2.
- Fig A4: energy/exergy Sankey (with residual) and geometry-dependent pressure-drop/heat-transfer trade-off.
- Fig A5: *feasible* cost/efficiency Pareto front with infeasible design ledger.
- Table A1: material limits, property validity and cost-boundary provenance.
- Table A2: independently benchmarked errors and mesh/time convergence.

### Paper-shaped Study B: price flexibility and robust techno-economics
- Fig B1: verified electricity price, source and heat load chronologies; split between design and held-out years.
- Fig B2: HP electric demand, charging/heat delivery and bed/tank temperature/SOC histories.
- Fig B3: energy/temperature quality of process heat and backup/unserved supply.
- Fig B4: cost–electricity–peak Pareto maps with high-fidelity re-simulation acceptance status.
- Fig B5: NPV/LCOH break-even regions, UQ rank reversal/regret under assumptions.
- Table B1: life-cycle CAPEX/OPEX by subsystem with source uncertainty and currency year.
- Table B2: sensitivity to source, demand duty, market year, tariff and storage life.

Each figure must be regenerated by one command using logged inputs, signed git SHA and data hashes. Visual quality cannot override numerical correctness.

## 10. Reproducibility, project engineering and scientific governance

Proposed package boundaries: property backend; cycles/compressors; HXs; TES/fluids; network; controllers; economics; optimisation; verification; plotting/reports. Stable typed dataclasses/Pydantic-style inputs and explicit units, structured warnings/error codes, no hidden global parameters. Numerical kernels separated from GUI and notebooks. No opaque interpolated manufacturer map without a visible licensed source.

CI layers: (1) lint, type checking and fast property/analytical tests; (2) representative cycle/TES/system numerical regressions; (3) optional scheduled heavyweight yearly solves and high-resolution baselines; (4) release replay on clean environment. Lock dependencies and test defined platform/Python versions. Each result directory contains source case, model/backend versions, OS/CPU where relevant, git SHA, dependency lock hash, input hash, random seed, solver feasibility and iterations, units and state/ledger outputs. The published release includes a source/copyright/redistribution audit.

Issue/PR conventions: one hypothesis and acceptance metric per scientific PR; cross-reference methods equation, source record, verification code and generated figure. Scientific claims are maintained in a claim-to-evidence ledger. Failed physical configurations remain archived with reason codes. Preserve negative findings and prior withdrawn claims. Prefer permissive open-source licence once attribution and dependencies are audited; no licence assumption until owner approves.

## 11. Controlled exclusions and honest claims

- **Not required for H-family v1.0:** an electricity-return heat engine, CFD of every vessel, manufacturer-certified compressor design, real-time power market bidding, hardware-in-loop, regulatory certification, industrial field guarantees.
- **Required even if inconvenient:** infeasibility ledgers, real heater/trace/parasitic work, material stability, dynamic coupling, identical service boundary, independent verification, uncertainty and full economic scope.
- **Experimental status:** Open datasets and published cases can support validation within their operating range. Without controlled experimental or industrial source data, release must say **numerically verified and independently benchmarked**, not physically validated at industrial scale.
- **v1.0 completion rule:** no release tag until the release checklist lists every required criterion as PASS with linked evidence; exceptions must reduce the advertised scientific scope rather than silently weakening physics.

## 12. Immediate action: first physics vertical slice

1. Finalize source provenance and external reference cases (IAPWS/CoolProp water, published cycle, experimentally reported packed-bed data). Establish test and figure naming.
2. Implement real-fluid **R718 baseline** and one relevant other natural-fluid/cascade choice, with phase/pressure envelope and two-sided HX checks. Do not presume R601 is appropriate at 250 °C.
3. Couple H0 to an explicit source and 150 °C process loop. Produce true state table, log(p)–h/T–s, component energy/exergy and sensitivity to source T.
4. Begin H1 conservative two-temperature TES and closed-loop exchanger coupling in small transient runs, then advance to H2/H3 and cross-validated equal-service design comparison.
5. Open issues and PRs following the execution matrix; every apparent improvement is measured against H0, not against the withdrawn legacy architecture rankings.

## 13. Evidence sources and access level (initial shortlist)

The following publications establish **research motivations and validation candidates**; their abstract-level observations are not substitutes for reproducing experimental conditions or detailed numerical models. Full method extraction and source licences are explicit M0 tasks.

- IEA HPT Annex 58 Final Report (2024): https://heatpumpingtechnologies.org/publications/annex-58-high-temperature-heat-pumps-final-report/ — industrial HTHP integration, technology and bounds.
- High-temperature heat pumps for industrial use (2024): https://doi.org/10.1002/cite.202300241 — technology/process interfaces, applicability.
- Water-refrigerant HTHP review (2024): https://doi.org/10.1016/j.energy.2024.133847 — natural-water cycle selection and engineering constraints.
- Systematic integration of HTHP in multi-energy systems (2025): https://doi.org/10.1016/j.applthermaleng.2025.127440 — cascade R717/R718 and transient integrations.
- Price-driven flexibility of industrial HTHP+TES (2026): https://doi.org/10.1016/j.energy.2026.141713 — MILP, national-price sensitivity and 150 °C industrial service.
- HTHP+TES in eco-industrial clusters (2026): https://doi.org/10.1016/j.enconman.2026.122001 — coupled techno-economics and packed-bed cost structure.
- Published experimental horizontal packed-bed T/velocity series (2024): https://doi.org/10.17632/j37x6ptpk2.1 — potential independent bed benchmark, verify available experimental metadata, permission and relevance of regime before use.
- KTH ENERSTOCK integrated Stirling HP and PCM TES laboratory *preliminary design* (2024): https://zenodo.org/records/13944316 — useful topology and instrumentation source; **not a validated measurement dataset by itself**.
- CoolProp water EOS / IAPWS: https://coolprop.org/fluid_properties/fluids/Water.html ; https://coolprop.org/fluid_properties/IF97.html — property backend and cross-check.
- Lower-melting HITEC property research: https://pubs.rsc.org/en/content/articlehtml/2023/ra/d2ra07384f — material property candidate, not an endorsed feasibility/cost assessment.

**New protocols to read alongside this programme:** V1_STUDY_MATRIX_AND_BENCHMARKS.md and V1_RELEASE_VERIFICATION_PROTOCOL.md. The main prior plan remains the detailed WP00–WP10 engineering background; this document adds a concrete falsifiable and reproducible v1.0 execution contract.
