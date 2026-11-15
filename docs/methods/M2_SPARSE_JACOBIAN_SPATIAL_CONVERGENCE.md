# M2 sparse-Jacobian verification and measured-Case-B spatial refinement

**Scientific status:** source-hashed numerical convergence evidence only; independent experimental thermal or hydraulic validation remains blocked. Target dataset: 2024 Calderón-Vásquez et al. horizontal copper-slag observations DOI 10.17632/j37x6ptpk2.1. Only Case B is used for numerical-development comparisons. C and D remain out of model fits; A was seen previously and is no longer a pristine test case.

## Analytical Jacobian derivation

The existing conservative 1-D two-temperature finite-volume equations are linear during a fixed boundary/flow/material step. With gas capacity `Cf`, rock capacity `Cs`, gas advective conductance `M = mdot cp_f`, interfacial thermal conductance `G=h A_i`, wall loss `Uw`, and solid axial conductance `Ks=k_s A_bed/dz`:

- `Cf dTf_i/dt = M(Tf_up - Tf_i) - G(Tf_i-Ts_i)`
- `Cs dTs_i/dt = G(Tf_i-Ts_i) - Uw(Ts_i-Ta) + Ks (Ts_(i-1)-2Ts_i+Ts_(i+1))` for interior solid cells; end cells have a single neighbour and adiabatic zero-end flux.
- The integrated energy ledger carries `dQ_hot/dt=M(Tin-Tf_n)` and `dQ_wall/dt=Σ Uw(Ts_i-Ta)`.

The new implementation constructs the EXACT sparse derivative matrix for gas/solid states and the two integrated flux variables. SciPy `solve_ivp(method=BDF,jac=sparse_matrix)` solves the **same ODEs** as the original independent numerical finite-difference Jacobian, without repeated expensive dense differentiation at n>=64. Nine tests cross-check analytical vs independently estimated Jacobians for 8/16/32 cells and axial conduction 0/2/10 W m⁻¹ K⁻¹, including thermal-front and energy-ledger agreement. The option `use_analytic_sparse_jacobian=False` preserves the baseline independent code path.

## Source-locked Case B spatial refinement (no fitting)

For the original 2024 Case B measured heater inlet and exhaust velocity with **assumed** 52-mm exhaust ID, measured Tout-dependent mass-flow forcing as in the old paper Eq.(1), constant gas and solid cp, original wall loss and NO axial conduction:

| N cells | First modeled T_out crossing of 80°C (s) | Model-vs-measured T_out RMSE (°C) |
|---:|---:|---:|
| 8 | 1266.74 | 35.519 |
| 16 | 1450.85 | 38.052 |
| 32 | 1556.38 | 40.600 |
| 64 | 1613.73 | 42.277 |
| 128 | 1644.08 | 43.228 |

The actually observed exhaust first 80°C crossing was 1847.84 s. Since the gas-flow estimate uses **measured Tout** to calculate exhaust density in this particular historical replay, these errors are **diagnostic** and cannot be called an independent blind forward prediction. A separately implemented predicted-Tout exhaust boundary fixes that dependency but has not itself been checked across 8–128 cells.

| Mesh doubling | RMS difference in modeled entire outlet temperature history | Difference in 80°C crossing |
|---|---:|---:|
| 8→16 | 9.8903 K | 184.11 s |
| 16→32 | 5.8734 K | 105.53 s |
| 32→64 | 3.2472 K | 57.35 s |
| 64→128 | 1.7150 K | 30.35 s |

The successive temperature increments decrease toward first-order upwind spatial behaviour. Calculating the observed order as `p_i = log2(Δ_i/Δ_(i+1))` yields approximately **0.75, 0.85 and 0.92**, consistent with but not definitive proof of first-order asymptotic convergence.

**Core negative scientific result:** mesh refinement makes the apparently close 16-cell fit WORSE, not better: RMSE increases from 38.052 to 43.228°C. This suggests numerical diffusion at coarse resolution was partially compensating for physical-model and flow-boundary deficiencies. **Never optimise TES architecture based on the 16-cell curve** merely because it had a smaller measured RMSE.

## Evidence-gated numerical acceptance

The audit now emits `case_B_spatial_convergence_assessment.json` with all mesh-pair RMS differences, front crossing shifts, observed convergence orders and explicit scientific status. A **prospective, post-initial-study engineering target** for future grid refinement is <1 K pairwise RMS outlet change and <15 s change in the 80°C outlet crossing. These numbers are **not measurement-uncertainty values or preregistered experimental validation tolerances**. At N=128 the last pair is 1.715 K and 30.35 s; thus the new `numerical_resolution_pass` remains **false**, and `external_predictive_validation_pass` is **false** by construction.

Before any external validation or architecture rankings:
1. Extend to N=256/512 or use a justified higher-order conservative transport discretisation and establish an actual asymptotic space/time error.
2. Replace the target-informed mass-flow forcing with the predicted-exhaust implicit solver on each grid, with independently measured exhaust bore and pressure.
3. Introduce measured gas/slag property and pressure dependence, radial buoyancy/dispersion, wall thermal inertia, sensor time response and exact thermocouple coordinates.
4. Verify source-calibrated pressure units/taps and separate physical bed resistance from duct losses.
5. Freeze parameters on development data and evaluate permitted held-out cases only once with independently measured inputs and documented uncertainty.

## Reproduction

- `python -m pip install -e ".[physics,test]"`
- `python -m pytest tests/test_m2_sparse_jacobian.py tests/test_m2_numerical_convergence.py -v`
- `python scripts/acquire_horizontal_bed_2024.py`
- `python scripts/study_horizontal_bed_resolution.py`
- `python scripts/report_m2_spatial_convergence.py`

The external-data GitHub Actions workflow archives JSON and underlying measurement hashes; the measured raw source is never silently replaced. These numerical tests are not physical validation.
