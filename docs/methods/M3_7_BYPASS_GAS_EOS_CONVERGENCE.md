# M3.7 — gas-bypass process-water temperature control, dry-air EOS sensitivity and stronger two-grid convergence

**Evidence status:** merged-stage candidate, independently reproducible **NUMERICAL / MODEL-ONLY** investigation, not an installed valve controller, not a confirmed 1 MW continuous liquid-heating duty and **not an experimental gas/rock model validation**. Keeps the original 1 MW **110→150°C water** functional unit. Pending R600/R718 compressor manufacturer data and independent packed-bed breakthrough/pressure measurements are not invented or assumed available.

## Objective and important distinction from M3.6

M3.6 found that a hypothetically resistance-heated 220°C gas stream could warm a **separate pressurised process-water loop** above 150°C for a 1-hour sampled interval after warmup. But simply delivering water at 152–160°C is **not a controlled exact 150°C process-water service**. Also, its HX/bed pressure, material, gas properties and geometry remain hypothetical, and spatial refinement affects the prediction.

M3.7 adds a physically **mass-conserving hot-gas bypass hypothesis**, numerical predictive actuator constraints and accepted-ODE-node temperature checks, with explicit **steady-state thermal margin and control-failure reporting**. In parallel it compares *genuine CoolProp HEOS::Air thermophysical properties* with the old constant-property bed without corrupting the original physical first-law ledger by silently mixing two incompatible gas-property closures.

## The physically separate water and hot-gas valve system

Keep **all of the original process liquid flow** `m_liquid = 1 MW/[h_water(150°C,2MPa)-h_water(110°C,2MPa)]`, computed from CoolProp's original water EOS at an **ASSUMED** 2.0 MPa absolute water pressure. Do **not** bypass extra water, alter the required delivered duty, mix an invented amount of return water or declare unqualified hot-water spill/recovery.

An uninstalled upstream hot-gas valve instead sends a fraction `f ∈ [0.1,1.0]` of the **15 kg/s total gas** through the finite-volume HX and sends `1−f` around the exchanger. The two gas streams mix before the separate, **still-uninstalled** conditioner that would return gas to the TES at 110°C. The controller cannot affect the previously assumed **220°C gas charge source** or change the fixed bed/rock model.

```text
m_gas,total = 15 kg/s = f × 15 kg/s + (1-f) × 15 kg/s

m_liquid,HX = m_liquid,process = 1MW / [h(150C,2MPa)-h(110C,2MPa)]

E_bed→hot-gas = E_hot-gas→HX + E_gas-remaining→return-conditioner

E_HX→water = m_water × ∫[h(Twater,out(t),P) - h(110C,P)] dt

Target: m_water × interval_mean_delta_h = 1 MW (tolerance ±1.5 kW)
Additional accepted-node temperature BAND: water outlet 150 ±0.5C
```

The controller **does not** assert that reaching 1 MW *mean* enthalpy duty guarantees the outlet is 150°C at all times. Separate flags test minimum/maximum accepted BDF water outlet temperatures; **values between solver nodes are unbounded**. A full-hour pass requires every service interval to respect both mean-duty and node-wise supply temperature constraints, assumed single-phase water and local nominal 5 K gas/liquid temperature approach. The ideal **per-interval predictive** valve command is selected by bracketed bisection from the dynamic HX's current state; a five-point valve-flow sweep first checks whether duty increases monotonically with gas flow under that specific thermal state. A **40 percentage-point maximum valve through-flow change per 60 s interval** is imposed. The actuator is *unmanufactured and untested*, and there is no realistic sensor noise, valves Cv/pressure loss, delays, sampling controller, PID tuning or manufacturer stable flow limits. A negative controller result is a legitimate result.

Two explicitly frozen thermal startup strategies were audited:
- **Immediate controller**, at discharge t=0, with 10 min initial period not credited as process service.
- **120 s full-gas warmup before enabling controller**, again with a total 10 min warmup fully charged against the TES, followed by the same one-hour nominal process contract.

## Verified original source-run results, no invented successes

The dedicated M3.7 CI runs the actual model, **42 original tests (M3.7+M3.6) passed**. Results for N_bed=16, N_HX=8, 60 s coupled steps, 220°C/25 kg/s assumed hot-gas charge for 2 hours, 10 min warmup, a 15 kg/s gas discharge and separately assumed HX 40 kW/K:

| Model-only strategy | Strict consecutive process interval band | Result |
|---|---:|---|
| Bypass feedback prediction from t=0 | **0/60 minutes** | **FAIL**. Final model water ~148.665°C. The initial heat exchanger is cold; premature control prevents stable preheating. |
| Full gas to HX for first 120 s, then predictive bypass | **48/60 minutes** | **FAIL** after service 48 min. Final water ~149.062°C; 12 min of requested full-duty guarantee missing. |

The 120s startup strategy reduces the maximum absolute interval-average water duty error in the service period to about **19.5 W** over the monitored intervals, but a near-exact **mean** 1 MW does **not** imply 150°C continuous controlled liquid water. The accepted-node supply temperature initially enters the 150±0.5°C band and later violates it. Its 70-minute numerical run has an additional **~2.415 GJ thermal gas-cooler duty**, not installed. **No full one-hour controlled process heat is qualified**, even as a strict model-only criterion. Avoid a fabricated "controller passed" conclusion.

For the immediate-controller failure the gas valve duty oscillates and the water end outlet alternates ~148.5/151.5°C even when interval-average duty is almost exactly 1 MW. The ideal controller is not tuned or demonstrated to be stable; it only reports failure honestly. The 120s full-flow startup is **not free energy**; the bed is debited during warmup, and cannot be credited to the one-hour contracted service.

The combined gas/metal/water/rock/cooler **numerical first-law** remains balanced to within ~6 J (immediate) or ~2 J (120s startup), at GJ-scale transferred heat. Numerical roundoff conservation is **verification of implementation**, not physical measurement validation or proof that the assumed HX exists.

## Independent dry-air thermophysical EOS sensitivity — NOT a changed bed model

The existing 1D packed bed and coupled gas–water HX still use constant `c_p=1005 J/kgK`, `rho=2.5 kg/m³`, `μ=2.35×10⁻⁵ Pa·s`. No actual gas-loop pressure measurement has been provided; these parameters **cannot be treated as physically temperature-independent across 110–260°C**. The new `src/carnot_battery_lab/physics/air_eos_sensitivity.py` independently computes **HEOS::Air** thermodynamic `h(T,P)`, `c_p(T,P)`, density `rho(T,P)`, viscosity `μ(T,P)`, thermal conductivity `k(T,P)`, Prandtl number and geometry-conditioned no-fit Ergun `Δp` for assumed absolute pressures **101.325, 250 and 500 kPa** and gas temperatures **110, 150, 180, 200, 220 and 260°C**.

At an **assumed 250 kPa absolute** pressure:

| Thermophysical property | 110°C | 220°C | 260°C |
|---|---:|---:|---:|
| HEOS::Air `c_p`, J/(kg K) | **1013.56** | **1029.31** | **1037.09** |
| HEOS::Air density, kg/m³ | **2.2723** | **1.7646** | **1.6321** |
| EOS enthalpy rise above 110°C, kJ/kg | **0** | **112.271** | **153.597** |
| Existing constant-`c_p` surrogate rise, kJ/kg | **0** | **110.550** | **150.750** |

Consequently, a 220→110°C dry-air enthalpy release predicted at *fixed 250kPa* differs by about **1.56%** between EOS enthalpy and the old constant-cp approximation, while the **density varies much more significantly** across the same temperature range. Gas mass hold-up, real-loop compression/pressure, Reynolds, bed interstitial velocities, blower energy and heat transfer must be solved *consistently* before a variable-density gas model can replace M3.6. **The new EOS audit is explicitly a sensitivity diagnostic, not a mixed-property "corrected" bed/plant calculation.** Numerical consistency requires a compressible mass/energy pressure-balance model, real gas absolute pressure, real equipment ratings and external independent thermocouple/pressure data. No architecture RTE or cost ranking is computed.

**Property source:** [Bell, Wronski, Quoilin & Lemort (2014), CoolProp DOI 10.1021/ie4033999](https://doi.org/10.1021/ie4033999); [CoolProp source: HEOS::Air property interface](https://coolprop.org/coolprop/HighLevelAPI.html).

## Stronger independent bed/HX grid and step sensitivity

The source-independent **same** unregulated M3.6 warmup/test case was recalculated, changing one discretization at a time while preserving exactly the same gas source, bed, water EOS pressure, 1 MW contract, assumed HX UA, gas return and initial HX state.

| Single numerical perturbation | Absolute difference in final water outlet |
|---|---:|
| HX cells **8→12** | **1.023 K** |
| HX cells **12→16** | **0.527 K** |
| Bed cells **16→32** | **1.911 K** |
| Bed cells **32→64** | **1.035 K** |
| Coupling step **60→30 s**, N_bed=16/N_HX=8 | **0.034 K** |

The simultaneously refined **N_bed=32/N_HX=12/60s** model gives final water outlet ~**155.38°C**, whereas the nominal 16/8 case lies lower. A nominal 5 K approach and 150°C control band demand tighter spatial independence than observed. Spatial truncation error is currently more important than time-step error in this particular 1D/3-temperature model. Three levels do **not** establish Richardson extrapolation validity or an asymptotic convergence order, and a *near-threshold* physical design cannot use the N=8 result as equipment sizing evidence.

## Experiment and manufacturer data: no false acceptance

- Real original packed-bed measured temperature histories and differential-pressure traces exist in [Weber et al., Mendeley Data, DOI 10.17632/3pp86gdvh4.2](https://data.mendeley.com/datasets/3pp86gdvh4/2), 9 experimental runs, **CC BY 4.0**, with axial/radial thermocouples, bed pressure taps, mass-flow and calibration-context folders. **The M2.1 metadata-only CI could not retrieve those original raw observations.** M3.7 does not synthesize their rows or claim original independent thermal breakthrough/pressure-loss acceptance. Frozen whole-run holdout and original calibration procedure remains tracked in [Issue #43](https://github.com/Open-Energy-Methods/CarnotBatteryLab/issues/43).
- [Mendeley original public API documentation](https://data.mendeley.com/api/docs/) describes the source dataset metadata snapshot, public file descriptors and downloading datasets/files. Browser or an OAuth-authorized download route may be required; original file checksums and column/units must be verified before reading as measured values.
- Real original experimental holdout performance, measured compressor maps and actual water HX UA/pressure remain **missing**. Work cannot be called an industrial 1 MW solution or a validated Carnot Battery simply because synthetic first laws and conditional water temperatures run.

## How to reproduce, negative controls and acceptance

```bash
python -m pip install -e ".[physics,test]"

python -m pytest tests/test_m3_7_bypass_and_air_eos.py \
  tests/test_m3_6_transient_liquid_hx.py -v

python scripts/run_m3_7_control_and_eos_audit.py \
  --output results/m3_7_bypass_control_air_EOS_and_convergence.json
```

The report includes every timestamp-indexed assumed valve through-flow fraction, water-start/end and accepted-node min/max outlet temperatures, controller duty error, gas energy/cooler ledger, original input assumption hash, three independent assumed gas pressures with EOS data, mesh/step sensitivity tables, explicit no-experiment claim, `validated_process_liquid_delivery_J=0` and `Carnot_battery_RTE=null`.

**Decision:** M3.7 satisfies the numerical implementation/audit goals. The **strict 150°C controlled one-hour process service is *NOT* reached by either tested valve strategy**, and the bed/HX remains spatially sensitive and unvalidated. Next steps before valid physical qualification: test a dynamically controlled outlet strategy at subminute update rates and robust capacity margin, derive consistent compressible gas-bed/HX pressure/energy physics, obtain Weber original measurements and manufacturer machine maps, and only then attempt a genuinely matched service/RTE comparison.
