# M1 — natural-fluid options and strict operating-envelope interpretation

**Status:** physics-first R600 transcritical screening and independently published **experimental** comparator points. No exact-source/sink manufacturer compressor-map validation. This document distinguishes heat-source temperature, refrigerant evaporation, source/sink return, model predictions and actual measurements.

## Target service

The established H-REF contract is a liquid waste-heat stream **80 → 70°C**, with industrial process heating **110 → 150°C** at **1 MW gross heat delivery**. The imposed 5 K evaporator pinch requires refrigerant evaporation at or below 65°C for the nominal source-outlet boundary. A bare evaporation temperature of 80–85°C is NOT interchangeable with 80°C source inlet and cannot extract heat from the source without violating local approach.

## Independent hardware / architecture evidence

| Evidence | Fluid | Class | Source | Sink | COP | Applicability |
|---|---|---|---|---|---|---|
| Verdnik & Rieberer (2022), DOI 10.1016/j.ijrefrig.2022.05.010 | **R600 n-butane, natural** | Measured experimental transcritical run | 60°C **inlet** | 160°C **outlet** | 3.1, 24.2 kW | One-stage suction-gas-cooled reciprocating, with IHX; different source from 80°C target |
| Ramirez et al. (2024), DOI 10.1016/j.applthermaleng.2024.122961 | **R1233zd(E), HFO** | Experiment, 50 test points | 80°C **inlet** | 148.5°C reported heat delivery | 3.6 at 38.6 kW heating /10.7 kW electrical | Near-matched lift but *not natural fluid*; source outlet and process return not matching/unspecified |
| Wu et al. (2019), DOI 10.1016/j.energy.2019.116427 | **R718 water, natural** | Experimental injected twin-screw | 85°C **refrigerant evaporating temperature**, no 80°C source claim | 150°C **refrigerant condensing temperature**, not confirmed 110→150 process | 1.96 | Strong high-lift R718 compressor evidence, **NOT a thermally eligible 80°C liquid source** |
| Verdnik et al. (2019), https://waermepumpe-izw.de/wp-content/uploads/2020/05/190800-ICR-1-3-E2_1186-Verdink-et-al.pdf | **R600, natural** | Published **simulation** of prototype high-pressure control, not measured point | 80→75°C | 80→160°C | 3.24 **simulated** | Temperature-lift support only; not H-REF 80→70 and 110→150, not verified compressor map |

**Conclusion:** the source/temperature elevation is physically plausible with a natural working fluid (R600), and strong *partially matching* machine evidence exists, but **no exact H-REF compressor/machine envelope is yet independently demonstrated**. A simulated model outcome must not be labelled hardware qualified; the original R718 5:1-per-stage numeric guard was never a measured manufacturer limit.

## CoolProp R600 finite heat-exchanger screen

The new code path `src/carnot_battery_lab/physics/r600_transcritical_screen.py` is a transparent simple single-stage transcritical **cycle hypothesis**:

1. Evaporator pressure from R600 saturation at `T_source,out - pinch`; example 70 − 5 = **65°C evaporation**. Compressor suction temperature = evaporating + prescribed 10 K superheat.
2. Compression from `p_evap` to an assumed **supercritical** high-side pressure with an assumed isentropic efficiency, including separately assumed motor/inverter electricity. **No compressor speed line** is available at the assumed pressure/suction conditions.
3. Gas-cooler outlet assumed at 115°C, 5 K above process return of 110°C. Gas-cooler enthalpy `h2 − h3`, mass flow `Q_process/(h2−h3)`; expansion valve `h4=h3`.
4. Exact refrigerant first-law `Q_source + W_shaft = Q_gas_cooler`, with source/process fluid capacities explicitly bounded.
5. Counterflow **enthalpy-resolved** evaporator and gas-cooler temperature profiles at 100 points and installed UA **assumptions**; internal approach violations or undersized UA cause explicit infeasibility. A high-pressure scan reports all feasible and rejected points individually; it does not silently select an infeasible COP optimum.
6. **No** real gas-cooler geometry, IHX, refrigerant pressure loss, measured part-load compressor speed/volumetric efficiency, discharge thermal guard, source/process pumps, system controls, transient TES or safety design. The source-published measured R600 rig **included an IHX**, so comparison of this model's COP to that machine is not matched-cycle validation.

The 4–6 MPa high-side scan should be read as **mathematical cycle screening** only. Its best COP within these arbitrary pressures is **not** a manufacturer-allowed pressure and does not establish an operating envelope without the experimental compressor's actual suction/flow/speed/discharge limits. We deliberately do not fit an efficiency curve or fabricate a speed-dependent compressor map from a single published COP.

## Natural-fluid / process safety

R600 is a flammable hydrocarbon. This research code is not a pressure-vessel, hazardous-area, fire-safety or regulatory compliance design. Actual systems require refrigerant charge minimisation, suitable equipment and electrical classification, leak detection, ventilation, emergency response, pressure protection and jurisdiction-specific risk assessment. Do not treat model feasibility as a commissioning endorsement.

## Reproduction and acceptance

- Install `python -m pip install -e ".[physics,test]"`
- Run `python -m pytest tests/test_r600_transcritical_screen.py -v`
- Generate `python scripts/run_natural_fluid_80c_evidence.py --output results/natural_refrigerant_80C_screen.json`
- Review report classes `FINITE_HX_THERMODYNAMIC_SCREEN_PASS` vs `INFEASIBLE_SCREEN`; the top-level field `hardware_qualified` must remain **false**.

**M1 hardware-qualified gate (still open):** obtain exact-target measured natural-fluid compressor maps or independently supported multipoint performance curves under **80→70°C source and 110→150°C process**; add actual gas-cooler/suction/injection topology, source/process hydraulic power, discharge/pressure/oil/safety limits, independent matched-unit validation and uncertainty. Existing numerical feasibility is an intermediate physics step—not final operating-envelope support.
