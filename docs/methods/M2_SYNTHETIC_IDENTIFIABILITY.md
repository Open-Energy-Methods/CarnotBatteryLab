# M2.4 — Scenario sensitivities and structural identifiability without laboratory calibration

**Status:** deterministic synthetic model analysis, **not an experimentally validated parameter estimation**. The original 2024 datasets A/B/C/D are not opened or fitted by this program. No posterior uncertainty distribution, experimental noise covariance, inferred parameter value or instrument accuracy is fabricated.

## Model and independent parameter transformations

The existing conservative 1-D constant-property packed-bed model, with *model-predicted outlet temperature* for the exhaust velocity-derived flow boundary, is simulated under **illustrative** nominal 430 K inlet, 303.15 K initial temperature, 5 m/s exhaust velocity and a short fixed transient at 10 finite-volume cells. These inputs are synthetic, not the original 2024 experimental operating histories, and their spatial discretisation is not separately qualified.

Seven hypothetical parameters are varied by symmetric **±0.04 in natural-log space**, one at a time: exhaust pipe internal diameter (base 52 mm), velocity calibration multiplier (1), slag density (3700 kg/m³), slag specific heat (1100 J/kg K), porosity (0.39), wall UA (0.5 W/K), and gas thermal conductivity (0.034 W/m K). This is a derivative/screening design **not a measurement-based uncertainty range**.

For each parameter θ the output-gradient column is calculated from two independent forward solves:

\[
S_j(t)=\frac{T_{out}(t;\theta_j e^{+0.04})-
T_{out}(t;\theta_j e^{-0.04})}{2\times0.04}.
\]

Report the full outlet-temperature Jacobian, singular values, numerical effective rank at an **arbitrary declared** relative 0.001 threshold, and RMS gradient ranking. Without a noise model, the singular values are NOT confidence limits, Fisher information for an actual measurement device or proof of practical identifiability. Purely modelled Ergun pressure is reported separately; no source-measured differential pressure is available in Pa and it is **excluded** from the temperature-Jacobian rank.

Two **exact structural symmetries** are independently checked algebraically AND by full synthetic forward runs:

1. **Flow probe bore versus velocity gain:** the prescribed relationship \(\dot m\propto D^2 v_{measured} k_v/T_{out,model}\) is invariant to \(D\mapsto aD\), \(k_v\mapsto k_v/a^2\). Thus T-out alone cannot distinguish true bore from velocity-probe gain in the present model.
2. **Slag bulk density versus specific heat:** for constant rock properties, solid energy capacity per volume is \(C_s/V=(1-\epsilon)\rho_s c_{p,s}\). Keeping \(\rho_s c_{p,s}\) unchanged leaves the entire present temperature solution invariant (no independent conductivity/density relation). Thus these two factors cannot be identified separately from bed temperature without other information.

Even with a numerically full-rank Jacobian in an unrealistically constrained parameter subset, the above symmetries show **structural** nonidentifiability from thermal histories alone. The remedy is independent flow-meter cross-section/velocity calibration and physical rock density/cp measurement; choosing parameter values that minimise Case B mismatch would instead conceal the problem.

## Verification and release gate

Run: `python -m pytest tests/test_m2_synthetic_identifiability.py -v`

Run: `python scripts/run_m2_synthetic_identifiability.py --cells 10 --steps 18`

The source-controlled GitHub Actions job archives the synthetic settings, full numerical derivative matrix, sorted model sensitivities, independent alias invariance errors and provenance-labeled status. Numerical energy conservation remains necessary but never establishes experimental predictive agreement.

**M2 physical validation remains BLOCKED** by missing 2024 flow-probe internal bore and calibration, differential-pressure transducer units/zero/taps, thermocouple response/positions, measured slag cp(T)/density and horizontal 2-D mixing effects. These are precisely documented in issue #23. M3 should proceed only as an independently tested synthetic charge/discharge software module; its efficiency is not a validated industrial performance metric.
