# Scientific v1.0 — Comparative Study Matrix & Independent Benchmark Register

**Status:** preregistration proposal, not a report of computed or validated results. All cases and thresholds require source-specific finalisation before the relevant study is run.  
**Reference programme:** V1_SCIENTIFIC_EXECUTION_PROGRAM.md  
**Key principle:** study geometry/working-fluid constraints **before** economic ranking; rank only physically feasible designs providing the same service.

## 1. Experiment structure and case fidelity

Each result has a unique structured identifier: [study]/[service]/[topology]/[cycle]/[medium]/[date-or-market]/[resolution]/[seed]/[git-sha].

Required independent variables:
- Thermal service: process supply/return T, quality/pressure, heat demand timeline, accepted unserved fraction and backup policy.
- Available source: source inlet T, flow/heat-capacity and return constraints, duty availability/uncertainty.
- HP: working-fluid identity and cycle family, compressor map/envelope, HX geometry/UA, part-load limits and start/ramp parameters.
- TES: geometry, material source, initial thermal inventory, cold/hot setpoints, flow, charge/discharge cutoff and initial/final cyclic state.
- Economy: reference price/currency year, tariff area/year, demand/power charges, scope of BOP, financial horizon, discounting, replacements and salvage.
- Numeric: spatial mesh, integrator tolerances, property backend, interpolation fidelity and convergence diagnostics.

Service contracts:
- C0 / H-REF: source 80 °C, supply 150 °C, return 110 °C, 1 MW_th nominal, 6 h **qualified useful heat storage** target, 15 min dispatch and T0=20 °C. **Illustrative inputs**, not published operating/feasibility evidence.
- C1 / H-LIFT: source 60/80/100 °C with otherwise matched H-REF.
- C2 / H-LOAD: fully specified continuous/intermittent demand profiles with matched annual useful heat; all variants get the same exact profile.
- C3 / H-MARKET: at least two named price areas and two nonidentical historical years, source-verifiable with timezone, day-length, missing and negative-price handling. One complete year excluded from design/fit for stress-testing.
- C4 / H-HOT: source 80 °C, process supply 250 °C/return 210 °C, 1 MW_th nominal challenge; qualified with its own source/upgrade/medium checks. **No assumption of existing HP feasibility**.
- C5 / FAULT: source interruption, low initial SOC, hot start, cold start, grid price spikes, actuator ramp and thermal delivery limit.

Comparative architecture universe:
- A0 H0 direct HTHP→process.
- A1 H1 gas/rock bed with physically separated refrigerant, charging gas and process HX.
- A2 H2 liquid-HTF plus filler dual-media thermocline with separately justified fluid and medium.
- A3 H3 two-tank salt, with specified low-freezing-point salt under suitable temperatures and independently validated charge pathway; conventional Solar Salt treated as a *different* higher-temperature case.
- A4 conditional justified PCM/steam or cascade — never included merely to increase the number of options.

## 2. Physics experiments and hold-out tests

| ID | Test or comparison | Minimum computed observables | Mandatory countercheck |
|---|---|---|---|
| P01 | Fluid property reference states | T,P,h,s,rho,phase,dh/dT, validity | qualified IAPWS/independent thermodynamic table; reject outside envelope |
| P02 | R718 HP state machine | evaporator/condenser Q, W, COP, p-h and T-s, compressor discharge | first law, property independent crosscheck, Carnot bound, pressure/saturation boundary |
| P03 | Second feasible natural-fluid/cascade HP | same plus stage/pressure ratios and motor limits | independent published state/cycle at same boundary, no fixed universal efficiency |
| P04 | HX phase and pinch | two sides enthalpy and temperature profile, UA/Q, dP, min delta T | exact energy closure; reject temperature cross; high-UA/zero-UA limits |
| P05 | Gas/solid bed charge/hold/discharge | axial T_f,T_s, outlet T, stored U, useful heat, dP, fan work | analytical limiting cases, 3+ mesh/time/tolerance, published bed transient |
| P06 | Liquid/filler thermocline | liquid and solid T, outlet and stratification evolution, pump work | energy/exergy, 3+ mesh, external thermocline benchmark |
| P07 | Salt tanks | hot/cold mass, enthalpy, liquidus margin, pump/trace/heel work | mass/energy, no freeze, no unsupported external cost/temperature transfer |
| P08 | Integrated H0/A0 direct | source T, compressor W, HX/pinch, qualified heat and price cost | HP thermodynamic closure; no TES bypass claim |
| P09 | Integrated H1/A1 closed loop | dynamic TES return to HP/HX, COP changes, P/T profile, no missed load | compare against decoupled constant-COP negative control and energy ledger |
| P10 | Integrated H2/A2 closed loop | same including HTF and filler, pump work, stratification | H1/H2 service parity, phase/material guards |
| P11 | Integrated H3/A3 | same with freeze/trace/auxiliary/upgrade and tank levels | clear compatibility evidence; infeasible reasons stored |
| P12 | Full cycle / periodic state | Q charge/discharge, delta stored U, start/end T field | converge repeated cyclic operation; no one-shot false RTE |
| P13 | Dynamic controls | baseline and optimised dispatch, starts, ramps, SOC, load and price | nonlinear re-simulation, controller disturbances and perfect-forecast ablation |
| P14 | Full-service sizing/optimisation | feasible cost/electricity/frontier, sizes, Pareto residuals | 2 independent optimiser methods, seeds, dominated and infeasible designs |
| P15 | UQ/generalisation | finance/source/material confidence ranges, rank reversal, year holdout | sensitivity by error class, no use of held-out prices for selection |
| P16 | Full reproducible replay | input/data hashes, package versions, exact figures/tables and validation verdict | clean environment without notebook state/manual edits |

Benchmarks are not performance claims unless the actual method, geometry and reference measurements have been extracted and matched.

## 3. Evidence and benchmark candidates

| ID | Source (verified URL) | What it can check | Current evidence/access status | Prerequisite before acceptance |
|---|---|---|---|---|
| B-HP-01 | CoolProp water/IAPWS EOS: https://coolprop.org/fluid_properties/fluids/Water.html and https://coolprop.org/fluid_properties/IF97.html | saturation, h,s,rho, cross-backend water states | documentation publicly accessible | defined independent table or release, selected state grid and tolerance |
| B-HP-02 | IEA HPT Annex 58 (2024): https://heatpumpingtechnologies.org/publications/annex-58-high-temperature-heat-pumps-final-report/ | real HP/process integration, capacity and temperature applicability | public report description | extract comparable measured/numerical case, parameters and uncertainty |
| B-HP-03 | Water cycle HTHP review (2024): https://doi.org/10.1016/j.energy.2024.133847 | steam/MVR architecture, pressure and lift limits | public abstract checked | obtain actual numerical reproduction case or independent detailed dataset |
| B-HP-04 | HTHP multi-energy dynamic integration (2025): https://doi.org/10.1016/j.applthermaleng.2025.127440 | R717/R718 cascade and dynamic source/load integration | article abstract checked | obtain boundary states and make fair equivalent case |
| B-BED-01 | Calderón-Vásquez et al. experimental copper-slag packed-bed dataset (2024): https://doi.org/10.17632/j37x6ptpk2.1 | published fluid/bed temperature and velocity traces under varied charging conditions | dataset available, CC BY 4.0 description | download raw/README, geometry/sensors/units; check applicability; split entire runs before any fit |
| B-BED-02 | KTH ENERSTOCK preliminary HP+TES rig (2024): https://zenodo.org/records/13944316 | topology/operating modes, instrumentation planning, PCM 70/155/245°C | preliminary rig design, **not** direct experimental validation data | do not use as held-out measurements without raw runs |
| B-SALT-01 | NREL conventional salt storage description: https://www.nrel.gov/docs/fy19osti/71912.pdf | typical Solar Salt cold/hot operating temperatures | public report | extract actual temperature/material constraints for separate high-temperature branch |
| B-SALT-02 | HITEC salt study: https://pubs.rsc.org/en/content/articlehtml/2023/ra/d2ra07384f | lower-melting candidate physical-property references | public article | confirm operating composition, model property correlations, corrosion/safety/cost feasibility and heat tracing |
| B-INT-01 | Integrated HP+TES in Danish eco-industrial setting (2026): https://doi.org/10.1016/j.enconman.2026.122001 | packed-bed cost methodology and process integration | public abstract/method description, data on request | acquire detailed equations/cost basis and independent comparison conditions |
| B-MARKET-01 | Price-driven industrial HTHP+TES (2026): https://doi.org/10.1016/j.energy.2026.141713 | historical price strategies, 150°C service; MILP comparator | open-access article, reported demand/year | extract consistent service, market/tariff scope and compare **not** copy claimed cost reductions |
| B-SCOPE-01 | Industrial HTHP integration review (2024): https://doi.org/10.1002/cite.202300241 | end-use HX and process design context | full abstract accessible | cite process boundary rationale, not a validation dataset |

Possible V3 independent experiments beyond B-BED-01 are a gap to address honestly. Obtain full dataset metadata and redistribute only under documented licences. If a reference is outside our fluid, geometry or temperature domain, mark it **non-transferable** and find a more relevant one instead of plotting superficial agreement.

## 4. Explicit negative controls and impossibility tests

- NC01: feed legacy synthetic-fluid COP=2.123 into changing 150°C storage conditions; verify it is rejected for real coupled HP models.
- NC02: apply Solar Salt 30°C or other below-liquidus cold condition; must trigger physical infeasibility, *not* low efficiency.
- NC03: take first discharge after a nonperiodic charge and claim round-trip; metrics must flag unmatched terminal storage inventory.
- NC04: increase bed packing/particle size while holding UA, fan work and ΔP constant despite geometry change; physical network must recalculate and/or reject.
- NC05: design MILP schedule requires more useful heat than nonlinear HP/TES could deliver; reject Pareto point rather than silently add heat.
- NC06: claim P2H2P electricity round trip from useful thermal kWh; type system must prohibit this.
- NC07: economic advantage disappears under installed-BOP and trace heaters; retain the negative economic result.
- NC08: leak future price-year information into optimised design/train partition; reproducibility audit detects overlap.
- NC09: for pressure drop→0 with flow→0, test finite transfer solver's conservation and no fictitious convective heating.
- NC10: zero/negative thermal approach at a proposed HX interface; reject or legitimately reverse heat direction only if topology supports it.

## 5. Comparisons and causal ablations

For **each** selected representative viable case calculate:
1. Ideal thermodynamic/adiabatic limit, then finite HX, then variable compressor, then TES hydraulics, then tank loss/standby, then part-load/start-up, then operating schedule, then installed costs.
2. H0 direct HP; H1 and H2 with matched heat and price history; H3 only after charge route feasible in a shared or explicitly separate study family.
3. Geometric sensitivity separating heat-transfer benefit from fan/pump work; no ungrounded NTU uplift assignment.
4. Same annual demand, prices and external heat-source inventory; do not optimise one case with perfect foresight and the other with rule-based control without identifying that bias.
5. No-TES, infinite-TES, zero-heat-loss, zero-pumping, constant-COP and no-start-penalty *ablation controls* as deliberately unphysical model variants to quantify modelling consequences, never as engineering proposals.
6. Chronological weather/price-year holdout; demand-shape shift; heat-source loss and rapid grid response.

Ablation results show which physical mechanism caused a reported change. When the result is indistinguishable from numerical/price/cost uncertainty, label it **unresolved**, not a proven architecture advantage.

## 6. Data architecture and immutable analysis convention

Each publication result must include:
- case.yaml with exact service and topology, geometry and property references;
- price/source/load input files with DOI/URL, licence, download timestamp, file hash, timezone and transformation code;
- outputs/state_points.csv, flow_ledger.csv, energy_exergy_ledger.csv, hourly_or_subhourly_operations.csv, constraint_violations.csv, capex_breakdown.csv, model_uncertainty.json;
- convergence.json, solver_status.json, manifest.json and generated figures metadata;
- validation comparisons to external source with train/holdout flags, error bars, sensor positions and geometry.
All data inputs and outputs carry SI units internally; presentation may use °C, bar, MW, MWh and EUR but no unitless conversion assumptions.

Publication release should include the cases required to regenerate main figures on a clean install (or explicit licensed-data retrieval command). Store only distributable material in Git; bulk data via Zenodo or authorized data repositories after rights review. Every study has machine-readable PASS, FAIL, NOT_RUN or NOT_APPLICABLE status, never a default true.

## 7. Study acceptance before interpretation

- Physics cases: in-domain states, no silent extrapolation, component and system balances, no unexplained thermal or electrical energy creation.
- Numerical reproducibility: >=3 independent spatial grids where PDE applies, separate temporal/tolerance and property-interpolation study, and a declared reference-resolution outcome; compare per time history, not only cycle average.
- External comparison: pre-specified MAE/RMSE/bias/time-of-front and delta-P with input sensor uncertainties, not calibrated to the held-out test.
- End-use: full qualified-load coverage or quantified deficit with explicitly applied backup cost; no unpriced service shortfall.
- Financial: same system-boundary, currency-year, cost uncertainty and scale; uncertain material premium not treated as sourced certainty.
- Optimiser: constraint audit passes using reference physics; at least one independent algorithm or simple exact benchmark, stochastic run reproducible.
- Evidence: all plotted values trace to source inputs and code hash, with no dependence on legacy withdrawn performance ranking.

These studies are **planned** and have not yet produced physics-backed conclusions.
