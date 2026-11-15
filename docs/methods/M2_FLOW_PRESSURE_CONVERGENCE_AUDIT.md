# M2 — flow, pressure, mesh and material uncertainty (2026-11-15)

**Status:** quantitative *numerical-resolution and parameter-sensitivity audit* from source-locked experimental **Case B** only. No model fitting, no independent full-model validation. Latest evidence scripts: `scripts/study_horizontal_bed_resolution.py`, `src/carnot_battery_lab/validation/flow_pressure_audit.py`, `scripts/exploratory_forward_horizontal_bed.py`.

## Source and observation provenance

2024 horizontal copper-slag packed bed: DOI https://doi.org/10.17632/j37x6ptpk2.1, CC BY 4.0. Original Case_B.csv hash `5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab`. Related source rig methodology: Wolde, Calderón-Vásquez, Segovia and Cardemil, *Revista Brasileira de Energia Solar* 13(2), 165–173, doi:10.59627/rbens.2022v13i2.395, section 2 and equation (1), https://rbens.org.br/rbens/article/download/395/287.

The latter provides 400 mm vessel length, 158 mm internal diameter, approximate 20 mm irregular slag particles, estimated voidage 0.39, thermocouples spaced 50 mm and **25 mm mineral wool insulation**. It explicitly identifies an exhaust hot-wire anemometer and inlet/outlet-pipe pressure taps; its equation (1) estimates exhaust mass flow `mdot = rho(T_out) A_exhaust v_exhaust`.

**Still unknown:** actual 2024 exhaust-pipe internal diameter, pressure-transducer transfer function and zero, channel pressure units, complete duct losses between taps, absolute positions/phase response of in-bed thermocouples, high-temperature specific heat of this actual heterogeneous slag batch and effects of local porosity and horizontal buoyancy. The 2022 paper plots pressure in Pa for its own test series, but that does not prove the 2024 source CSV's $Δ P$ **channel numeric units** are Pa. Do not rescale the 2024 raw series to fit the 2022 chart.

## Analytical flow sensitivity and pressure evidence gate

Under measured exhaust velocity and `Tout` Eq. (1), at fixed pressure, `mdot` scales as **D²**. A scenario of assumed D=45 mm to 60 mm creates a factor **1.7778** difference in mass flow at the same measured v and Tout. This is a *bounded scenario*, not a confidence interval; the source does not establish either the assumed low or high bore.

`flow_pressure_audit.py` returns these scenarios with source notes. The `PressureCalibration` dataclass hard-blocks physical pressure comparison unless the sensor's calibrated units, zero/offset, source, uncertainty, pressure-tap locations and independently measured duct/minor losses are supplied. Hypothetical unit multipliers or the magnitude of the raw CSV cannot yield valid Ergun agreement. Negative/near-zero instrument values are preserved and counted, not clipped away.

The 2022 article notes an experimental pressure sensor near its lower measurement limit in low-airflow conditions, an additional warning against calibrating Ergun from unfiltered near-zero readings.

## First Case-B sensitivity results (unfitted and non-blind)

The actual 2024 Case B data were replayed with independent prescribed published vessel geometry, *assumed* 52 mm exhaust ID, representative rock cp=1.1 kJ/kg K, axial conduction originally zero, wall UA=0.5 W/K and constant properties. Measured Tout enters density and inferred gas mass flow; **comparison to Tout is therefore not an independent holdout validation**.

| Case B variant | Temperature RMSE to measured exhaust (°C) | First modeled outlet 80°C crossing (s) | RMS temperature difference vs 16 cells (K) |
|---|---:|---:|---:|
| 8 cells | 35.519 | 1266.74 | 9.89 |
| 16 cells (baseline) | 38.052 | 1450.85 | 0 |
| 32 cells | 40.600 | 1556.38 | 5.87 |
| 16 cells, 2 solver substeps per measured interval | 38.052 | 1450.85 | <0.001 |
| 16 cells, 4 solver substeps per measured interval | 38.052 | 1450.85 | <0.001 |
| Assumed exhaust ID 45 mm | 24.201 | 1944.85 | 40.06 |
| Assumed exhaust ID 60 mm | 68.324 | 1034.78 | 41.85 |
| Slag cp=0.8 kJ/kg K | 72.189 | 1061.72 | 46.63 |
| Slag cp=2.3 kJ/kg K | 47.094 | 2763.11 | 81.64 |

These figures were calculated from **one source-hashed measured run** and a fixed, unfitted model. The 45 mm scenario is closer to the observed Case B series, but **MUST NOT be adopted as an estimated pipe diameter** without source measurement. Likewise, cp cannot be chosen to minimise RMSE if published material measurements/independent identification are absent.

The 16→32-cell difference of ~5.87 K RMS and ~106 s at the modeled 80°C crossing demonstrate **material spatial numerical error** despite tiny solver substep/tolerance effects. Therefore the 16-cell model is **NOT numerically converged** in actual transient outlet/front observables, even though it conserves energy. Its reported RMSE should not be used to rank candidate architecture physics.

## Separate conservative axial-conduction option

The regenerator now optionally includes *pairwise-conservative*, no-end-flux axial thermal conduction in the rock:
`F_(i+1/2)=k_s A (T_(s,i+1)-T_(s,i))/dz`; each interface flux is added to one cell and subtracted from its neighbour. The term sums to zero over the whole packed bed, preserving the independent energy ledger. The default `k_s=0` reproduces the original model unchanged; positive `k_s` values are **scenario assumptions** rather than fitted effective thermal dispersion. The published equivalent one-phase horizontal-bed dispersion model is not identical to this two-temperature solid-conduction term, so no performance gain is asserted without actual Case B and holdout checks.

The additional output scenarios of `k_s=2` and `10 W/m K` are structural-sensitivity experiments only. Verified source-locked Case B runs yielded **38.061°C RMSE, 1,405 s 80°C crossing** for `k_s=2` and **39.458°C RMSE, 1,265 s crossing** for `k_s=10`, compared with 38.052°C RMSE and 1,451 s crossing at `k_s=0`. **Increasing axial conduction did not materially improve RMSE**, and at 10 W/m K substantially moved the front earlier. It would be scientifically unsound to label this new term a validated correction without physical conductivity data and a resolved flow boundary. A more sophisticated energy/flow model must independently specify temperature-dependent slag cp, measured rock thermal conductivity, wall inertia, pressure-dependent air density, and two-dimensional effects.

## Predictor-based exhaust flow removes the previous Tout-target leakage

The earlier Wolde Eq.(1) forcing used observed exhaust `Tout(t)` to calculate density and mass flow, therefore comparing model `Tout(t)` to measured `Tout(t)` was not a fully independent forward test. A new module, `validation/exhaust_flow_coupling.py`, now iteratively solves `m_dot = p A v_measured / (R T_out,model)` within each model time interval: all fixed-point trials start from the **same initial bed state**, so they do not double-count charging energy; the bed is advanced only with the final converged mass flow. The measured `Tout(t)` is only accessed **after** model integration for RMSE/MAE calculation. External measured exhaust velocity, inlet Tin and measured initial T1–T7 remain permitted source-forcing/state measurements. BDF integration remains energetically conservative.

**Source-hashed Case B only, initial 16-cell model and assumed 52mm pipe:**

| Criterion | Earlier measured-Tout-dependent mass flow | Predicted-Tout implicit flow |
|---|---:|---:|
| RMSE to Case B measured outlet | 38.052°C | **37.777°C** |
| MAE to Case B measured outlet | 28.102°C | **28.607°C** |
| Model first 80°C outlet crossing | 1450.85 s | **1495.08 s** |
| Experimental first 80°C outlet crossing | 1847.84 s | 1847.84 s |
| Mean implicit flow iterations per step | Not applicable | **8.91** |
| Maximum relative flow fixed-point residual | Not applicable | **9.93×10⁻⁷** |

**Interpretation:** model-target leakage has been removed, but **physical predictive accuracy is not yet acceptable** and only a small change in RMSE was observed. The new boundary assumes model bed outlet temperature equals the downstream exhaust sensor temperature, and uses unverified pipe ID and exhaust pressure; the model still assumes constant density in bed fluid inventory while varying exhaust mass flow using the ideal-gas law. The previous spatial 16→32 mesh sensitivity makes differences of ~0.3°C RMSE statistically meaningless as evidence of a better physical model. The new result is a methodological and input-independence correction, not a validation pass. No C/D full model simulations have been run.

## Test-split integrity

The previous development iteration **already evaluated Case A** and reported its RMSE and breakthrough error. Even though no parameters were fitted to A, it is no longer an entirely *unseen* blind test; do not use that label. Case B is the sole numerical-development run for the present study; **Cases C and D are excluded from simulation and parameter selection** until the model and uncertainty gates are frozen. Their measured-only descriptive statistics were published previously, so even these should be called *held-out from model fitting*, not inaccessible data or completely blind evaluation. Using their actual Tout to infer flow will still be a partially target-informed simulation.

## Scientific acceptance gates

- **A (data metadata): BLOCKED:** obtain measured internal exhaust pipe bore and calibrated/traceable pressure channel with tap/duct geometry and uncertainties.
- **B (model numerical quality): BLOCKED:** demonstrate at least 3–4 spatial resolutions of the front/outlet dynamics, independent solver-time and tolerance convergence and conservation at each resolution. Evidence shows 16 cells insufficient; no design comparatives should rely on grid-sensitive breakthrough.
- **C (model physical quality): BLOCKED:** gas/slag cp(T), density and viscosity variation, wall/duct inertia, solid-fluid interfacial transfer appropriate to irregular slag and horizontal buoyancy/possible radial flow.
- **D (external model validation): BLOCKED:** lock parameters on B or other permitted training runs with source-backed constraints, then evaluate C/D once, without reading their target results to choose physics or coefficients. Report measured-vs-predicted temperature/front, pressure-loss uncertainty, error decomposition and model discrepancy limits. No validation PASS may be assigned solely for a good RMSE.

## Reproduce

- `python scripts/acquire_horizontal_bed_2024.py` (source acquisition)
- `python -m pip install -e ".[physics,test]"`
- `python -m pytest tests/test_flow_pressure_audit.py tests/test_m2_solid_conduction.py -v`
- `python scripts/study_horizontal_bed_resolution.py --input-dir results/external_horizontal_bed`
- `python scripts/run_case_B_no_target_leak.py --input-dir results/external_horizontal_bed`

All numerical resolution, measurement and physically motivated scenario results are JSON artifacts of the external-data workflow, not hand-edited data files. Do not interpret a Python test PASS as experimental model validity.
