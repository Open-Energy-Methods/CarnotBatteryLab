# M2.1 — Shared-layout, dynamic, mixed-contact thermocouple observation

**Evidence class:** mathematically checked *hypothetical observation operator*. **Not** a calibrated thermocouple model, laboratory response calibration, independent physical validation, or a measured uncertainty interval.

## Source and scope

Wolde et al. (2022), *Revista Brasileira de Energia Solar* 13(2), DOI [10.59627/rbens.2022v13i2.395](https://doi.org/10.59627/rbens.2022v13i2.395), Methods §2.1, describe seven Type-K probes spaced 50 mm apart, with sheath contact to gas and copper-slag particles in a nominal 400 mm-long horizontal packed bed. The [2024 original measured time series](https://doi.org/10.17632/j37x6ptpk2.1) contain Tin, Tout and T1–T7, but do **not** independently determine all 2024 probe coordinates, thermal contact conductances, response constants or calibration. Laboratory continuity with 2022 is a hypothesis, not established.

A reasonable *model class* for a bead observing both phases is a lumped first-order sensor:

\[
T_{eq,i}(t)=\alpha T_f(x_0+i\Delta x,t)+(1-\alpha)T_s(x_0+i\Delta x,t),
\quad
\tau\dot T_{TC,i}=T_{eq,i}-T_{TC,i}.
\]

This is an assumed zero-instrument-bias, one-way response model, not an independently validated physical contact correlation. \(x_0\) is shared by all seven probes; \(\alpha\) and \(\tau\) are fixed per **entire seven-probe trajectory**. Sensor thermal mass is not coupled back into the model. \(\tau=0\) is the algebraic instantaneous limit.

**Unfitted deterministic sensitivity hypotheses:** \(x_0\in\{0,0.05,0.10\}\,\mathrm{m}\), \(\alpha\in\{0.25,0.50,0.75\}\), and \(\tau\in\{0,30,180\}\,\mathrm{s}\), yielding 27 predefined physically layout-consistent scenarios. All values except the layout-spacing bound are **illustrative**, and no probability weights or measurement uncertainty are assigned. Neither the contact fraction nor time constant is fitted to the observed T1–T7. They are common across sensors within each scenario only as a declared simplification; real sensors may have distinct responses.

## Numerical implementation and independent mathematical tests

- **Spatial operator:** interpolate gas and solid temperatures independently at cell-centre coordinates to the same absolute position \(x_0+i\Delta x\). The observation interpolation is not the finite-volume conservation scheme. Clamp at the boundary to the nearest cell-centre value rather than extrapolating artificial temperatures.
- **Time operator:** with a linear equilibrium stimulus between snapshots \(E_a\to E_b\) over \(\Delta t\), the exact sensor update is
  
  \[
  T_{TC}^{b} = e^{-r}T_{TC}^{a}+(1-e^{-r})E_a+
  \left(1-\frac{1-e^{-r}}{r}\right)(E_b-E_a),\quad r=\Delta t/\tau.
  \]
  
  Implemented using \(\operatorname{expm1}\) and a short-time series for numerical stability; no ad-hoc Euler time-step error. Constant-stimulus and linear-ramp analytic identities are independently tested.
- **Initial sensor state:** model equilibrium at initial model state, **not observed T1–T7 values as sensor outputs**. However, the existing packed-bed **initial field itself was reconstructed from the first measured T1–T7 sample**, assuming initial axial centres at 0.05…0.35 m. This initial-state measurement dependency remains; the first sample is never scored.
- **Simulation:** original Case B SHA-256 `5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab`, 128-cell numerical forward calculation using measured Tin and measured velocity but **model-predicted** exhaust temperature for density/flow; assumed internal exhaust pipe bore 52 mm. No downstream measured Tout or later T1–T7 enters the physics. Phase histories are reused for all 27 scenarios.
- **Output:** deterministic min/max of scenario trajectories at each sensor/time; because the extremising scenario may differ by sensor and time, this is **NOT a jointly realizable calibration envelope**, likelihood region or measurement uncertainty interval. It is only an exploratory sensitivity bound.
- **Independence and limitations:** no Case A/C/D model selection; no experimental manufacturer sensor response, probe-radial positions, confirmed calibration, fully qualified flow or horizontal 2-D buoyancy. The 128-cell in-bed observation-operator spatial convergence has not yet been demonstrated.

## Initial source-locked results (2024 original Case B)

GitHub Actions run 43839962679 successfully executed the 128-cell forward phase-field model and the **27 deterministic, jointly configured** sensor hypotheses. The published initial seven original TC values were used only to initialise the field; subsequent 300 samples were diagnostic comparisons. The output reports:

| Source TC | Measured samples outside wide scenario range | Maximum outside-range distance |
|---|---:|---:|
| T1 | 52.00% | 12.67°C |
| T2 | 44.00% | 20.33°C |
| T3 | 47.33% | 56.04°C |
| T4 | 45.67% | 61.82°C |
| T5 | 47.67% | 72.23°C |
| T6 | 47.33% | 72.26°C |
| T7 | 52.00% | 90.71°C |

This sensor-response hypothesis envelope is typically wider than the prior instantaneous phase/location extrema, but cannot be interpreted as improved physical calibration. In particular, **over half of T7 samples remain outside** even the chosen broad response/contact scenarios. No likelihood weights, sensor time constants, positions or contacts were estimated from these residuals. The source-informed experimental error is still substantial, and no 128→512 internal-field convergence was yet demonstrated.

## Reproduce

`python -m pytest tests/test_m2_dynamic_thermocouples.py -v`

`python scripts/acquire_horizontal_bed_2024.py`

`python scripts/study_case_B_sensor_phase_envelopes.py --cells 128`

`python scripts/report_case_B_dynamic_sensors.py`

The GitHub Actions workflow `m2-source-sensor-observation` creates a versioned original-data manifest, phase-state file, 27 fixed shared-layout scenarios and original-data-vs-scenario diagnostics.

**Acceptance:** sensor response equations and shared-layout consistency must pass analytic unit tests. External experimental *predictive* validation remains **BLOCKED** until lab-source sensor offsets, mixed-contact thermal coefficients and response, and gas/pressure instrumentation are verified. Even a measured TC contained in every simulated scenario range does not imply validation.
