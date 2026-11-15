# M2 — 512-cell source-locked numerical convergence vs experimental validation

**Scientific status:** Both Case B simulations reach **previously established provisional mesh-refinement criteria** (256→512 difference <= 1 K RMS across outlet-temperature history and <= 15 s crossing shift). Neither delivers predictive physical validation. The raw experimental source hash and every numeric simulation input are archived in GitHub Actions.

## Source, provenance and claims

- Copper-slag 2024 horizontal-flow PBTES data: https://doi.org/10.17632/j37x6ptpk2.1 (CC BY 4.0). All runs in this study read **Case B ONLY**, source CSV SHA-256: 5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab. No C/D simulation/parameter selection. Case A was already inspected in earlier development and must NOT be represented as pristine blind.
- Wolde et al. 2022 rig methods (doi:10.59627/rbens.2022v13i2.395) provide 400 mm length, 158 mm internal diameter, approximate 20 mm copper-slag particles, estimated porosity 0.39 and 50 mm thermocouple spacing. The 2025 7.45-L experimental description differs from the perfect-cylinder volume (roughly 7.84 L), so internal fixtures/dead-volume must be verified.
- 2025 paper doi:10.1016/j.est.2025.116769 identifies **nominal 2-inch steel flange connections**, not the internal bore at the exhaust velocity probe. Reference ASME B36.10-type NPS-2 nominal Sch40 bore ≈52.48 mm and Sch80 ≈49.22 mm (https://process-bench.com/ref/schedule-40-pipe-dimensions/), giving about 13.7% conditional difference in inferred mass flow. **Neither option is proven installed at the anemometer.** The probe bore, pressure-channel units, tap/duct losses and transducer calibration remain unresolved.

## Mathematical solver verification

The model integrates separate finite-volume gas and rock temperatures with conservative gas upwind advection, coupled hA, rock/solid wall losses and a full integrated heat flux ledger. The exact sparse analytical Jacobian is independently regression-tested against numerical finite-difference BDF Jacobians.

New independent **closed-form heat exchange** tests on 8, 32, 128 and 256 cells use zero gas flow, zero wall losses and an initially uniform gas/rock temperature difference. For one cell, with gas heat capacity Cf, solid heat capacity Cs and interfacial conductance H:

    Cf dTf/dt = -H (Tf-Ts)
    Cs dTs/dt =  H (Tf-Ts)
    (Tf-Ts)(t) = (Tf0-Ts0) exp[-H(1/Cf+1/Cs)t]
    Cf Tf(t) + Cs Ts(t) = Cf Tf0 + Cs Ts0

The analytical solution supplies a reference independent of any experimental fitting. This checks internal numerical physics, **not the experimentally correct value of the heat-transfer coefficient**.

## A. Original literature-inspired mass-flow boundary: source measured Tout enters density

Historical experiment replay uses measured exhaust velocity AND measured outlet temperature to calculate source flow (rho at observed Tout × inferred A × observed velocity). This is a numerical test under *prescribed source-measured forcing*, NOT a blind model-to-measurement comparison.

| N cells | Predicted first upward Tout=80°C (s) | Model/expt outlet RMSE (°C) |
|---:|---:|---:|
| 64 | 1613.73 | 42.277 |
| 128 | 1644.08 | 43.228 |
| 256 | 1659.63 | 43.734 |
| 512 | 1667.50 | 43.995 |

| Doubled mesh | RMS outlet profile change (K) | Breakthrough shift (s) |
|---|---:|---:|
| 64→128 | 1.7150 | 30.351 |
| 128→256 | 0.8824 | 15.552 |
| **256→512** | **0.4477** | **7.870** |

The experimental first 80°C exhaust crossing is 1847.84 s; the 512-cell predicted crossing is ~180 s early. The apparent coarser mesh agreement is contaminated by numerical diffusion and observed-temperature-informed flow.

## B. Model-predicted exhaust density: measured Tout excluded from physics

The independent-forcing variant uses measured inlet temperature Tin(t), velocity v_exhaust(t) and original measured initial thermocouple values, but predicts the mass flow from the **modelled** exit temperature, iterated for each time interval:

    mdot = p_exhaust × A_exhaust × v_measured / (R_air × Tout_model)

The measured Tout is accessed only AFTER the completed integration for MAE/RMSE. Fixed-point iterations each start from the same previous bed state. Actual exhaust velocity-probe bore is still unmeasured: the default 52 mm is assumed. Constant gas density in the bed inventory, assumed material properties, horizontal-flow radial gradients and pipe-sensor thermal lag remain significant model limitations.

| N cells | Predicted first upward Tout=80°C (s) | Model/expt outlet RMSE (°C) |
|---:|---:|---:|
| 32 | 1583.24 | 43.345 |
| 64 | 1630.84 | 46.732 |
| 128 | 1655.66 | 48.596 |
| 256 | 1668.27 | 49.573 |
| 512 | 1674.67 | **50.073** |

| Doubled mesh | RMS outlet profile change (K) | Breakthrough shift (s) |
|---|---:|---:|
| 32→64 | 4.2353 | 47.596 |
| 64→128 | 2.2604 | 24.824 |
| 128→256 | 1.1693 | 12.608 |
| **256→512** | **0.5947** | **6.400** |

The 512-cell model breakthrough remains about **173 seconds earlier** than measured. Even though target leakage is corrected, observed/model RMSE is **50°C**: not an acceptable validated model. Mesh corrections must not be called experimental validation.

## Evidence gates and next high-value physics

1. Closed-form gas/solid energy-exchange comparison — PASS (mathematical verification).
2. Exact sparse versus independent finite-difference BDF — PASS.
3. Historical and no-target-flow 512-cell provisional **pairwise numerical mesh criteria** — PASS. These are engineering screening values, not calibrated confidence intervals, true grid-extrapolated error bounds or a certified continuum result.
4. Predicted experimental breakthrough shape and level — LARGE DISCREPANCY. NO physical predictive validation.
5. Actual hot-wire anemometer pipe section bore, velocity traverse, source mass flow, temperature response/pressure — MISSING.
6. Experimental ΔP channel gain, native units, baseline, tap positions, duct loss and uncertainties — MISSING. Do not invent a Pa scale to match Ergun.
7. Physical model: slag cp(T) and conductivity, 2-D horizontal buoyancy/radial gradients, steel/insulation/pipe heat capacity and precise TC geometry/lag — NOT VERIFIED.
8. Held-out C/D full model prediction and uncertainty-aware pressure/thermal agreement — NOT RUN.
9. Full R600/R718 compressor map and source-compatible 80→70°C HTHP envelope — separate open M1 gate.

The 2025 paper (doi:10.1016/j.est.2025.116769) reports a calibrated *different* analytical single-temperature surrogate with normalized error near 4%; that result **must not** be compared directly with the absolute RMSE of this unfitted two-temperature model without consistent metrics, boundaries, calibration and test splits.

## Reproduce exact source-locked evidence

    python -m pip install -e ".[physics,test]"
    python -m pytest tests/test_m2_fine_mesh_analytic.py tests/test_m2_no_target_leak_grid.py tests/test_pipe_geometry_scenarios.py -v
    python scripts/acquire_horizontal_bed_2024.py --output-dir results/external_horizontal_bed
    python scripts/study_horizontal_bed_fine_mesh_512.py
    python scripts/study_case_B_no_target_leak_512.py
    python -m pip install "matplotlib>=3.8"
    python scripts/plot_case_B_fine_mesh_evidence.py

The dedicated workflow (.github/workflows/m2-fine-mesh-case-b.yml) archives full time-aligned 64–512 observations/predictions, raw-source provenance, solver versions, acceptance evidence and three labelled research figures. No C/D simulation is permitted in these numerical-development scripts.

**Conclusion:** remove coarse-grid numerical diffusion as an explanation for the remaining large experimental error. The next physical research demands independently measured flow, pressure and material properties; code-level numerical convergence alone cannot qualify CarnotBatteryLab v1.0.
