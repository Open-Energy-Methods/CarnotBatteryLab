# M2.2 — Independent analytical and fixed-position gas/solid convergence

**Classification:** Numerical verification and mesh-refinement evidence for the existing two-temperature packed bed. **No experimental in-bed TC calibration or predictive validation.**

## Mathematical reference independent of the BDF solver

For `m_dot=0`, `wall_UA=0`, `solid_axial_k=0` and constant material properties, every gas/solid control volume obeys:

\[
C_f\frac{dT_f}{dt}=-G(T_f-T_s),\qquad
C_s\frac{dT_s}{dt}=+G(T_f-T_s).
\]

There is no external energy transfer. Define `T_bar=(Cf Tf0+Cs Ts0)/(Cf+Cs)`, `D0=Tf0-Ts0` and `lambda=G(1/Cf+1/Cs)`. The exact solution, derived directly from the two energy equations, is

\[
T_f(t)=\bar T +\frac{C_s}{C_f+C_s}D_0 e^{-\lambda t},
\qquad
T_s(t)=\bar T -\frac{C_f}{C_f+C_s}D_0 e^{-\lambda t}.
\]

This is an **exact two-temperature interphase relaxation limiting case**, not a claim of reproducing Schumann's full analytical travelling-front solution or any third-party experiment. The independent closed-form temperatures and thermal inventory are checked for 8, 32 and 128 cells, different time intervals and nonuniform initial conditions. The results are checked against both the equations and global first-law ledger.

## Source-locked transient in-bed mesh comparisons

The baseline 2024 Case B experiment DOI [10.17632/j37x6ptpk2.1](https://doi.org/10.17632/j37x6ptpk2.1), original SHA `5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab`, is used only as a prescribed heater Tin(t), exhaust velocity(t), model-initial TC-derived temperature field and observed outlet after simulation.

The newer exhaust boundary derives gas mass flow from **predicted** outlet temperature in a self-consistent fixed point, not measured outlet Tout. The bed geometry and unknown 52 mm exhaust inner bore remain assumed, and the 2024 absolute probe locations are unverified.

The source-locked [existing five-grid workflow](../../.github/workflows/m2-fine-mesh-case-b.yml) is extended to sample **both gas and solid temperatures at the same seven physical positions** \(z=\{0.05,0.10,0.15,0.20,0.25,0.30,0.35\}\,m\) on 32/64/128/256/512 cell meshes. These positions are **fixed modelling-evaluation coordinates**, not measured 2024 thermocouple positions.

Linear interpolation of finite-volume cell-centre temperatures is used consistently across all grids and does not modify the conservative solver. At each mesh doubling, the analysis reports for each fixed x and each phase the **whole-time-trace RMS and maximum absolute difference**; the max across the 14 phase–position traces is retained as a conservative summary. Thus the outlet-only convergence result cannot automatically pass in-bed gas/rock accuracy.

A provisional <1 K maximum *RMS mesh-to-mesh* increment across all 14 positions is reported as an **engineering-resolution screening choice**, not an experimentally measured uncertainty or proof of valid sensor response. Full in-bed mathematical convergence also requires time refinement, true sensor coordinates, source-property qualification and horizontal-flow structural error analysis.

## Actual source-locked 2024 Case B numerical outcome

The dedicated 512-cell GitHub Actions workflow run **43841260535** passed its 21 targeted tests, independently regenerated the source-hashed five-grid trajectories and confirmed:

| Pair | Worst gas-history RMS at seven fixed coordinates | Worst rock-history RMS |
|---|---:|---:|
| 32→64 | 4.10096 K | 3.96737 K |
| 64→128 | 2.18086 K | 2.10890 K |
| 128→256 | 1.12571 K | 1.08831 K |
| 256→512 | **0.57191 K** | **0.55281 K** |

Thus, for this prescribed **target-independent exhaust-flow model and nominal assumed coordinates**, the final mesh doubling meets the provisional **1 K** whole-history RMS *numerical* increment screen for **both gas and rock at all seven points**. Values decrease across the observed series; this is consistent with expected first-order spatial refinement. We do not declare a maximum local error below 1 K, do not extrapolate an exact spatial solution, and do not assert measurement-error bounds.

No calibrated 2024 probe coordinates, mixed-phase time-response parameters or experimental model accuracy follow from this result. The outlet experiment discrepancy remains large despite excellent numerical convergence.

## Diagnostics and claim control

- Source DOI/hash, fixed x-coordinates and all five meshes are checked before reporting comparison.
- A variable/moving sensor coordinate, missing 32/64/128/256/512 mesh, source checksum mismatch or use of downstream measured TC to drive the fields is rejected.
- Thermal/gas field convergence reports are **numerical comparisons**, not T1–T7 physical validation or mechanical compressor certification.
- The separate M2.1 sensor observation model has unknown 2024 thermocouple contact and response parameters; until its physical inputs are independently sourced, even a numerically converged internal field cannot be called a validated measurement prediction.

## Reproduce

`python -m pytest tests/test_m2_analytic_two_temperature_exchange.py tests/test_m2_internal_field_convergence.py -v`

`python scripts/acquire_horizontal_bed_2024.py`

`python scripts/study_case_B_no_target_leak_512.py`

The result `case_B_no_target_leak_512_mesh.json` now includes `internal_two_phase_refinement` and separate seven-location gas/rock model-temperature time histories for every mesh. No additional Case A/C/D model fit is involved.
