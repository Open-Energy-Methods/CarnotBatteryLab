# M3.5 — Compressor-independent packed-bed charge envelope and 110→150°C process-liquid duty

**Milestone class:** numerical **necessary thermal-service feasibility** for a declared hypothetical electric-resistance-heated gas boundary. **NOT physical equipment qualification**, independent measurement validation, matched-service architecture comparison or electrical round-trip efficiency. This study has **no dependency on pending R600/R718 manufacturer compressor maps**.

## 1. Fixed industrial functional unit and physical boundaries

| Item | Model input | Evidence status |
|---|---|---|
| External original waste-heat source | 80→70°C liquid | **NOT** used as an invented hot-gas heater; not physically coupled in M3.5 |
| Contracted industrial process | **1 MW gross** 110→150°C liquid for 1 or 2 h | Exact external thermal service target |
| Liquid cp | 4180 J kg⁻¹ K⁻¹ | **Constant-cp nominal assumption**, not measured |
| Required process-liquid flow | **5.980861 kg/s** | Derived from 1 MW /(4180×40 K), not a measured plant flow |
| Minimum counterflow approach | 5 K | Declared model hypothesis |
| Process-liquid phase | Saturated pressure at 150°C ≈ 0.476 MPa abs (CoolProp water); actual liquid pressure unknown | **Not** liquid-phase-qualified or pressure-designed |
| Required installed process HX UA | calculated from candidate gas temperature if thermal grade passes | **Installed exchanger UA unknown** |
| Initial storage | **Uniform 95°C** fluid+solid | Hypothetical model state, no free hot inventory |
| Bed diameter, length, particle diameter, porosity | 5.0 m, 4.0 m, 0.045 m, 0.40 | Original source-unvalidated research geometry |
| Bed volume | 78.54 m³ | Hypothetical geometry |
| Gas cp / density / viscosity | 1005 J kg⁻¹ K⁻¹ / 2.5 kg m⁻³ / 2.35×10⁻⁵ Pa·s | Constant air-like surrogates; **NO actual gas absolute pressure** |
| Rock density/cp | 2600 kg m⁻³ / 850 J kg⁻¹ K⁻¹ | Constant model properties, no measured thermal expansion/cycling |
| Total nominal wall UA | 120 W K⁻¹ | Assumed, not verified against experiment |
| Gas **charge** flow | 25 kg/s | Hypothetical, fan/compressor equipment unknown |
| Gas **reverse discharge** flow | 15 or 25 kg/s | Independent process-side gas, **not** liquid process flow |
| Gas **return into bed** on discharge | 110°C | Imposed model boundary, requires downstream cooler or revised loop closure |
| Charge gas temperatures | 150, 180, 220 or 260°C | **Imposed hot-gas** inlet; not demonstrated attainable from the original 80°C source |
| Charge durations | 4 min to 8 h | Explicitly varied independent of HP compressor maps |
| Model electric resistance heater | 100% assumed gas-heater conversion; 4.5 MW maximum electric input | **Idealized**, not manufactured/rated/installed |
| Integration time step | 600 s nominal; 300 s check | Time discretization, not measured sample rate |
| Spatial mesh | 16 cells scan; 16/32/64 verification | **Not yet experimentally validated** |

The original machine-specific R600/R718 compressor operating limits from M1.9 **remain fully blocked**. M3.5 has *not* invented a compressor able to take 80°C waste heat to a 260°C gas supply. This is a deliberately different, independent gas-heater-and-TES hypothesis. It is not a candidate Carnot-battery architecture ranking.

### Correlation provenance and nominal range checks

The existing two-temperature bed employs the particle–gas heat-transfer correlation `Nu = 2 + 1.1 Re_p^0.6 Pr^(1/3)` from **Wakao, Kaguei & Funazkri (1979), [DOI 10.1016/0009-2509(79)85064-2](https://doi.org/10.1016/0009-2509(79)85064-2)**, originally associated with a reported **particle Reynolds range 15–8500** and gas-like Prandtl values near 0.7–1. The exact constant property assumptions used here imply `Pr≈0.716`, `Re_p≈2438` for 25 kg/s and `Re_p≈1463` for 15 kg/s in the 5 m diameter bed, all **nominally** inside that correlation range. The code refuses out-of-range Reynolds inputs. This is only a check of published correlation arguments, **not validation** of the assumed large-scale industrial 1D rock bed, particle shape, thermal dispersion, high-temperature air density, gas pressure or actual physical heat-transfer coefficients.

## 2. Conservation of energy and heater model

Charging uses the original conservative finite-volume two-temperature bed model `advance_bed()`, whose fluid/rock/ambient integrated first-law residual is independently recomputed. The physical **gas recirculation heater** assumption is:

```text
P_heater,gas(t) = m_charge × cp_gas × [T_hot_gas_in(t) - T_bed_gas_out(t)]
P_ideal_electric(t) = P_heater,gas(t) / eta_resistive
E_heater = integrated actual heat passed from source gas into bed / eta_resistive
delta(U_bed)_charge = Q_from_hot_gas - Q_wall,charge
```

The nominal limit `P_ideal_electric <= 4.5 MW` is checked at the initial gas condition and sampled finite-volume outlet endpoints. **Intra-step power peaks and real hardware capacities are not independently verified.** Ergun-only bed pressure loss and blower electricity are calculated as **uncalibrated** diagnostics and not used as actual fan selection or gas pressure ratings.

Discharge reuses the original conservative, **opposite flow direction** packed-bed solver `advance_reverse_discharge()`; every step reports actual **SIGNED** gas heat gain, initial/mean/final outlet temperatures, bed wall heat, predicted Ergun pressure drop and a global storage first-law ledger. The gas leaving the bed is **NOT** the process water.

At each discharge gas outlet sample, a *separate* 1 MW gas-to-110→150°C process-liquid counterflow exchanger is tested:

```text
T_gas,after_1MW = T_gas,bed_out - 1MW / (m_discharge * cp_gas)

ΔT_hot_end = T_gas,bed_out - 150°C
ΔT_cold_end = T_gas,after_1MW - 110°C

Require BOTH ΔT_hot_end and ΔT_cold_end >= 5 K
And estimated UA_required = 1MW / LMTD(ΔT_hot_end, ΔT_cold_end)
```

At constant cp, the temperature difference is linear along cumulative counterflow exchanged heat, and checking the two endpoints is a model-internal no-crossing criterion. There is **no independently measured installed UA** or real process-water pressure, so a *passing modeled temperature/energy state never counts as actual 1 MW process heat delivered*. The 110°C discharge gas-bed return is imposed: a thermal gas **cooler** (or more defensible coupled gas-loop return temperature) is required to remove the excess gas enthalpy after transferring 1 MW to process liquid. The script calculates the **additional average THERMAL cooler load** but has neither sized the cooler nor called that load electrical power.

**Three sampled gas outlet temperatures** (initial/time-mean/final) are required **in every 10-min discharge interval**. The first failing sample disqualifies the claimed full continuous duty, even if prior samples meet the grade. Conversely, all three samples passing do **not** establish true between-sample minimum, transient HX dynamics, valve control or industrial availability.

## 3. Reproduced model-only operating-envelope results

The dedicated workflow independently executes the actual source code, without calibrated compressor maps, sensor histories or external pricing:

| Model scenario | Requested 1 MW liquid delivery | Result on N=16 and Δt=600s |
|---|---:|---|
| 150°C gas charge for 8 h; 15 kg/s discharge | 1 h | **Preblocked**: source gas below 155°C required hot-side threshold |
| 180°C gas charge for 4 h; 15 kg/s discharge | 1 h | **Preblocked**: gas enthalpy flow cannot meet 1 MW and 5 K cold-end pinch even at best-case source temperature |
| 220°C gas charge for 4 min; 15 kg/s discharge | 1 h | **Fails**: 0 of 60 min contiguous service screened |
| 220°C gas charge for 2 h; 15 kg/s discharge | 1 h | **Passes sampled necessary thermal gate**: 60/60 min |
| 220°C gas charge for 4 h; 15 kg/s discharge | 1 h | **Passes sampled necessary thermal gate**: 60/60 min |
| 260°C gas charge for 4 h; 15 kg/s discharge | 1 h | **Passes sampled necessary thermal gate**: 60/60 min |
| 260°C gas charge for 8 h; 15 kg/s discharge | 1 h | **Passes sampled necessary thermal gate**: 60/60 min |
| 260°C gas charge for 8 h; 25 kg/s discharge | 1 h | **Passes sampled necessary thermal gate**: 60/60 min |
| 260°C gas charge for 8 h; 15 kg/s discharge | 2 h | **Fails full 2 h**: first 110 min pass, final 10 min fail |

The 220°C / 2 h nominal case requires **12.95465 GJ** modeled net gas-to-bed charging heat = **3.59851 MWh idealized heater input**, with **0.02759 MWh** additional modeled Ergun-based charge blower electricity. Its maximum computed bed pressure losses are **0.966 kPa during charge** and **0.352 kPa during discharge** (15 kg/s); neither is a measured value. Its most-demanding required static process HX UA within passing discharge samples is approximately **22.91 kW/K**, not an installed value. The extra *thermal* gas-cooler interval-average requirement reaches about **0.654 MW** to enforce the artificially imposed 110°C discharge return after delivering 1 MW.

The **required nominal liquid-process output** is **1 MW × 1 h = 3.6 GJ = 1 MWh useful heat**. The nominal **12.95 GJ charge heat is not equal to useful process output**: a substantial portion heats the storage inventory, subsequently leaves in gas enthalpy that cannot be converted to the contracted process grade, is removed by the unmodeled cooler, remains in the bed, or is lost to ambient. **No electrical energy round-trip efficiency or real delivery efficiency is established.**

## 4. Frozen numerical 1-hour duty charge-duration bracket

The exact same 220°C hot gas, 25 kg/s charge, 15 kg/s discharge, 95°C initial bed, 110°C discharge return, 1 h liquid duty were held fixed while a **10-minute charging-duration grid** over 10–240 minutes was searched. The search is based on full first/mean/final sampled liquid-HX gates; it does **not** fit a model parameter to the duty.

| Numerical mesh | Last failing charging time | First passing charging time | Ideal heater electricity at first passing time |
|---|---:|---:|---:|
| 16 cells | 50 min | **60 min** | 2.7934 MWh |
| 32 cells | 50 min | **60 min** | 2.8446 MWh |
| 64 cells | 50 min | **60 min** | 2.8725 MWh |

The nominal **50–60 min interval is a grid-bracket for a model-only sampled thermal gate**. It is *not* an actual shortest charge duration, optimal heater energy, assured thermal stability, 1-hour operating guarantee or experimentally validated bed capability. A different wall-UA calibration, particle dispersion, fluid property variation, gas pressure, installed exchanger or truly continuous service requirement can move the boundary.

## 5. Solver consistency, spatial/time sensitivity

On the separate **220°C / 4 h charge / 1 h discharge** model with original 95°C initial bed and 15 kg/s gas return, the final discharge gas outlet is:

| N cells | Time step | Simulated end outlet |
|---:|---:|---:|
| 16 | 600 s | 209.209°C |
| 32 | 600 s | 212.169°C |
| 64 | 600 s | 213.699°C |
| 32 | 300 s | 212.169°C |

N=32→64 difference **1.530 K**; time step 600→300 s at N=32 difference **0.000018 K** at this terminal sample. The full storage first-law integrated residual stays at numerical roundoff (on the order of 10⁻⁵ J against GJ input) due to conservative ledger integration. **Numerical conservation does not demonstrate convergence in physical prediction**, and the N=32→64 temperature difference requires higher-resolution checks before close-to-threshold performance differences can support any design conclusion. No Richardson order or asymptotic extrapolation is claimed.

## 6. Decision and open physical science

**Decision:** The original 4-minute numerical charge does not supply the thermal duty, but the current **hypothetical resistance-heated gas/rock bed can** produce a gas stream that meets *sampled necessary conditions* for a separate 1 MW, 110→150°C liquid duty for one hour when supplied with considerably more hot-gas charging time/energy.

The strongest legitimate output is a **conditional thermal-envelope map and numerical charging-time bracket**. It neither discharges validated **150°C water** nor compares 80°C-source compressor architectures. The following remain open:

1. **M2.2:** independently measured packed-bed temperature histories, material/geometry, thermocouple and flow-pressure calibrations, experimental pressure-drop, frozen whole-run holdouts. Current gas/rock 1D model does not resolve radial dispersion and remains unvalidated.
2. **M3.6:** time-dependent, source-coupled **gas-to-process-water** HX with pressure-dependent liquid properties, actual circulation loop, cooling return closure, realistic installed `UA(t)`, real process water pressure, gas thermal capacity and transient outlet threshold.
3. **M1.9 manufacturer evidence:** real R718/R600 compressor maps for an **80→70°C** liquid source. Even a passing M3.5 gas-heater hypothesis does not imply a matching heat pump exists.
4. Physical electrical charging equipment, gas loop pressure and air/material temperature limits, fan curves, valves, storage containment, source/return heat exchanger, control, instrument uncertainty, insulation design, capex and repeated cyclic steady state. **No system RTE**.

The independent resistance heater is an **alternative hypothetical charging boundary**, not yet a qualified physical architecture. Do not compare its model electricity use against the unqualified original HP cycles as if both met the same installed service.

## 7. Reproduction and source files

```bash
python -m pip install -e ".[physics,test]"
python -m pytest tests/test_m3_5_independent_thermal_envelope.py \
  tests/test_m3_4_liquid_process_hx_gate.py -v

python scripts/run_m3_5_independent_thermal_service_envelope.py \
  --output results/m3_5_independent_hot_gas_liquid_heat_service_envelope.json
```

The reproducible JSON contains exact initial conditions, assumption SHA-256, all source and discharge cases, inlet/mean/outlet gas histories, integrated heat and electric-heater/fan/cooler hypothetical demand, uncalibrated Ergun pressure losses, 16/32/64-cell sensitivity, numerical first-law residual, and explicit `matched_1MW_service_empirically_qualified=false`, `matched_service_architecture_ranking=null`, `round_trip_efficiency=null`.

M3.5 implementation lives in `src/carnot_battery_lab/physics/independent_thermal_envelope.py` with the executable frozen scenario scan and negative/positive synthetic tests. All source and experiment provenance remains distinct from primary measurement data.
