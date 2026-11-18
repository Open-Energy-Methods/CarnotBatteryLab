# M3.8 — terminal outlet control and a conservative pressure-driven real-air bed prototype

**Scope:** numerical advancement of M3.7, with unchanged 1 MW, 110→150°C process liquid and separate hypothetical electrical hot gas source. This is not a qualified plant, verified manufacturer heat-pump machine, calibrated packed bed, installed gas bypass, or industrial 150°C temperature guarantee. A negative model result is acceptable.

## A. Controlled process water: separate temperature and duty objectives

M3.7's per-interval mean enthalpy objective caused an oscillating outlet even when mean duty was about 1 MW. M3.8 retains the same separate water stream, mass flow calculated using CoolProp water at *assumed* 2 MPa absolute, 40 kW/K assumed HX UA, total 15 kg/s discharge gas and 110°C imposed gas-bed return. It adds an alternative objective to the existing predictive split valve: solve for the **end-of-step** water outlet of 423.15 K rather than the interval mean duty. The two requirements are not interchangeable:

- All accepted numerical water outlet nodes must be 150 ± 0.5°C.
- Interval integrated actual process-water enthalpy gain must give 1 MW ± 1.5 kW.
- The same minimum local gas-water approach, model phase-pressure gate and mass conservation still apply.
- Gas valve range is 10–100% through the HX and the command change limit is **0.4/60 per second** (40 percentage points per minute); the step-change maximum scales with time step. This is a constrained **sampled command** model, not a resolved mechanical valve motion model or calibrated actuator Cv law.
- A 120 s full-gas initial startup is included in the same 600 s warmup, with no free hot inventory or process-service credit.
- The hypothetical gas cooler/reheater is still uninstalled and pressure losses from the bypass branch/valve are not yet characterized.

The study freezes six cases: the M3.7 60 s mean-duty reference; terminal objective with 60, 30 and 10 s updates; terminal 30 s with jointly refined bed/HX 32/12 cells; terminal 30 s with four rather than two hours of assumed 220°C hot-gas charge. The first four retain N_bed=16,N_HX=8 and two-hour charge. All demand a full 60 minutes after the explicitly debited warmup. This isolates the control objective, update time, joint mesh sensitivity and charge-time effect without tuning the acceptance criteria. Joint spatial refinement is a diagnostic, **not** a proven independent convergence order or global mesh independence. The underlying industrial gas/rock and HX gas properties remain M3.7's constant-property surrogate in these six runs.

Thermal feasibility of precise control is judged only from the regenerated report, not from an arbitrary controller success flag or final outlet temperature. An accepted numerical node check does not prove continuous service between solver nodes. This study uses perfect state knowledge of each energy-equivalent inlet gas step, no real sensor delay/error and no validated actuator. It is not a commissioned optimizer or closed-loop plant control certification.

### Verified M3.8 outcome (PR #49)

All three PR workflows completed successfully on a8d4ab0; [dedicated results](https://github.com/Open-Energy-Methods/CarnotBatteryLab/actions/runs/44393489259). Merged into main as 95f1e0a. Final simulated controls:

| Objective / grid / update | Consecutive passing minutes | Max absolute interval-mean duty error, W | Min / max accepted water node, °C |
|---|---:|---:|---:|
| Mean duty 16/8, 60s | 48 | 19.50 | 149.0622 / 150.9327 |
| Terminal 16/8, 60s | 60 | 605.20 | 149.9589 / 150.0016 |
| Terminal 16/8, 30s | 60 | 139.32 | 149.9904 / 150.0011 |
| Terminal 16/8, 10s | 60 | 8.13 | 149.9994 / 150.0004 |
| Terminal 32/12, 30s | 60 | 151.36 | 149.9898 / 150.0010 |
| Terminal 16/8, 30s, four-hour charge | 60 | 143.09 | 149.9904 / 150.0011 |

All are conditional model results with a hypothetical heater, ideal predictor, constant-property industrial gas model, and no actual actuator/sensor qualification. Refined mesh result and small control errors do not establish experimental accuracy. The 10 s case still requires ~2.408 GJ additional thermal gas conditioning over 70 min, uninstalled. Independent real-air bed N=2/4/8 outlet gas temperatures at 10 s were 396.699, 391.352, 388.660 K respectively; 4→8 shift 2.692 K remains material and no mesh independence is established. Both real-air mass and energy ledgers closed at numerical roundoff.

## B. EOS-conservative variable-property gas physics (separate prototype)

The original constant-density gas in M3.7 cannot simply be replaced by density evaluated at fixed pressure and variable temperature without accounting for gas inventory. M3.8 first implements a rigid gas control volume whose independently advanced extensive quantities are gas mass M and internal energy U:

```
rho = M/V; u = U/M
(T,P,h,mu,k,cp) = HEOS::Air(rho,u)
dM/dt = mdot_in - mdot_out
dU/dt = mdot_in*h_in - mdot_out*h_out + Qdot
```

This model distinguishes internal energy inventory from enthalpy carried by flowing gas. Pressure is a calculated state, not simultaneously fixed with incompatible gas mass, density and volume. Sealed heating, steady same-state flow and variable-mass inflow are regression controls. Gas kinetic energy and moving-boundary work are excluded in this rigid low-Mach primitive; imposed inlet/outlet flow is not a pressure-driven actuator.

The separate real-air packed-bed prototype adds multiple rigid void volumes and solid thermal inventories. Each gas cell contains M_i and U_i; a local EOS is evaluated at M_i/Vvoid and U_i/M_i. The finite-volume continuity and energy equations are

```
dM_i/dt = F_i-1/2 - F_i+1/2
dU_i/dt = H_i-1/2 - H_i+1/2 - Q_gs,i
C_s,i dTs_i/dt = Q_gs,i - Q_wall,i
H_face = F_face h_upwind
```

At each face a quasi-steady Ergun resistance yields a superficial velocity from signed pressure difference. With upstream real gas density and viscosity, and face distance L, define A and B by

```
A = 150 mu (1-epsilon)^2 L/(epsilon^3 dp^2)
B = 1.75 rho (1-epsilon) L/(epsilon^3 dp)
abs(deltaP) = A abs(u) + B abs(u)^2
abs(u) = 2 abs(deltaP)/(A + sqrt(A^2 + 4 B abs(deltaP)))
F = sign(deltaP) rho A_cross abs(u)
```

Upwind enthalpy flux is signed consistently with mass. No artificial mass source is needed to maintain a prescribed pressure at all interior cells. BDF integrates M_i,U_i,Ts_i and both signed boundary mass/enthalpy integrals and wall heat; independently recomputed full-bed mass/energy ledgers must close. A guard checks interstitial Mach number from accepted integration states. Numerical boundary half-cell and interior full-cell lengths are explicit. At exactly equal pressure the resolved pressure-driven face flow vanishes (with a tiny numerical roundoff tolerance).

### Hypotheses and limitations

The independent pressure-driven computational test deliberately uses a **different small bed** (length 0.5 m, diameter 0.3 m, 10 mm spheres, void fraction 0.4; not the Weber apparatus or industrial bed), assumed uniform initial gas/solid 383.15 K, initial pressure 250 kPa absolute, left reservoir 493.15 K and 250.1 kPa, right reservoir 383.15 K and 249.9 kPa. Solid density 2600 kg/m³, solid cp 850 J/(kg K), volumetric gas-to-solid conductance 5000 W/(m³ K), default wall UA 0. Duration 10 s, N=2/4/8. All numbers are uncalibrated numerical hypotheses.

This is **only an open pressure-reservoir standalone bed model**. Its Ergun face approximation ignores acoustic inertia, integrated compressible pressure gradients, entry/distributor losses, and kinetic-energy transport. Uses a fixed *assumed* volumetric gas/solid heat-transfer conductance: no validated Re-dependent variable-property heat transfer, particle distribution, gas expansion energy outside the rigid CV, wall calibration, or realistic blower characteristic. Real gas properties are consistent in mass/energy and upwind face hydraulics; cp and conductivity are calculated but are not yet used for the convective heat-transfer closure. The 1 MW model has **not** been migrated to it. A compatible variable-gas HX, pressure-connected circulation, valve/cooler friction and real gas pressure data remain necessary. Do not characterize this prototype as the complete M3.8 variable-property bed/HX workstream.

Source: Bell et al. (2014), CoolProp property library, DOI [10.1021/ie4033999](https://doi.org/10.1021/ie4033999); original CoolProp HEOS Air. Ergun's original relationship S. Ergun (1952), Chemical Engineering Progress 48, 89–94. Correlation selection is a model hypothesis, not independent apparatus validation.

## C. Independent experimental evidence admission remains open

Weber et al. original [dataset DOI 10.17632/3pp86gdvh4.2](https://data.mendeley.com/datasets/3pp86gdvh4/2), version 2, published 22 April 2025, CC BY 4.0, documents nine distinct shallow-bed air runs with thermocouples, pressure and flow instruments. Associated data article [DOI 10.1016/j.dib.2025.111743](https://doi.org/10.1016/j.dib.2025.111743). A published [2026 corrigendum DOI 10.1016/j.dib.2026.113089](https://doi.org/10.1016/j.dib.2026.113089) adds acknowledgement of technical support; it does not supply missing raw traces or change measurement equations. These are source and metadata checks, not independent scoring.

The dataset landing page was accessible, but the attempted Mendeley file/snapshot endpoints were not accessible in the available retrieval environment (direct file API and local HTTP attempts did not return the raw data; local DNS failed). No source-file payload, SHA-256, raw sensor observations or calibration record was fabricated. No data acquisition status has changed to validated. **Obtain the actual original version-2 archive via the publisher's Download All or directly from authors, then run the M2.1 admission and whole-run holdout protocol.** A user-uploaded original archive would allow reproducible file inventory, source SHA and calibration/column decoding without confusing plot curves with measured rows. See [Issue #43](https://github.com/Open-Energy-Methods/CarnotBatteryLab/issues/43).

The new pressure-driven bed's test temperature range and geometry do not imply a match to Weber's apparatus. Model validation requires independently documented lower-Re heat-transfer applicability and real instrument uncertainty. Continue to report separately thermal breakthrough, corrected measured bed pressure drop, and hardware qualification.

## Reproduce

```bash
python -m pip install -e ".[physics,test]"
python -m pytest tests/test_m3_8_terminal_and_real_air.py tests/test_m3_8_real_air_bed_prototype.py tests/test_m3_7_bypass_and_air_eos.py tests/test_m3_6_transient_liquid_hx.py -q
python scripts/run_m3_8_terminal_control_and_air_volume.py
```

Reproducible output: results/m3_8_control_and_real_air.json (dedicated workflow artifact). Contains six controlled 1 MW numerical trials, independent gas CV balances, small pressure-driven bed N2/4/8 results and explicit negative qualification flags. **No measured compressor maps, installed process hardware, actual 1 MW delivery or electrical RTE has been accepted.**
