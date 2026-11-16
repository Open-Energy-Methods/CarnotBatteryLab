# M2.3 — Conservative, temperature-dependent enthalpy and steel-shell inertia

**Evidence class:** independent numerical model DEVELOPMENT, not model calibration or laboratory predictive validation. The earlier constant-cp two-temperature `GasRockBed` and source-locked 512-cell experimental benchmark are retained unchanged for rigorous comparison. This is a **separate optional solver**, `physics/enthalpy_wall_bed.py`.

## Sourced gas heat capacity and consistent enthalpy

The NIST Chemistry WebBook / JANAF (Chase 1998) provides piecewise **Shomate** ideal-gas coefficients for [N₂](https://webbook.nist.gov/cgi/cbook.cgi?Formula=N2&cTG=on) and [O₂](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7782447&Type=JANAFG). The model assumes **79 mol% N₂ and 21 mol% O₂** (trace CO₂, Ar, humidity and gas composition changes neglected). For each species, `t=T/1000`, `cp_mol=A+B*t+C*t²+D*t³+E/t²`, and the integrated molar sensible-enthalpy primitive is `H=A*t+B*t²/2+C*t³/3+D*t⁴/4−E/t` (kJ/mol). Species integrals are split and summed exactly at the **500 K N₂** and **700 K O₂** fit boundaries.

The mixture sensible specific enthalpy `h_air(T)` uses the same coefficients as `cp_air(T)`; `dh_air/dT=cp_air` within fit sections. The code checks this numerically on both sides of each fit boundary, including temperature 300/400/900/1200 K. **No fixed-heat-capacity approximation `cp_ref*(T-T_ref)` is used in the gas energy ledger.** The current guarded modelling range is 298.15–1500 K.

The 2024 measured laboratory air humidity/composition is not reported, so this is a sourced **dry-mixture hypothesis**, not a certified actual-air property representation. Gas viscosity uses an illustrative Sutherland law; conductivity is an illustrative power law. Neither should be confused with independently verified experimental transport properties.

## Solid and steel thermal states

The nominal steel shell of the related 2022 horizontal rig was specified as **7 mm steel wall**, with nominal 400 mm length and 158 mm inside diameter; source DOI [10.59627/rbens.2022v13i2.395](https://doi.org/10.59627/rbens.2022v13i2.395). `CylindricalSteelShell` computes mass from the annular cylinder \(m_w=\pi[(r+t)^2-r^2]L\rho_w\). The illustrative \(\rho_w=7850\,kg/m^3\) and \(c_{p,w}=500\,J/(kg K)\) are not material certificates and **end caps/fittings/inlet-outlet duct inertia are omitted**. This creates a finite wall temperature state, instead of imposing instantaneous ambient heat loss directly from the stones.

For slag, \(c_{p,s}(T)=c_{ref}+a_s(T-T_{ref})\) is a **declared unknown-parameter hypothesis**, not a source-calibrated batch correlation. The specific sensible enthalpy \(h_s(T)=c_{ref}(T-T_{ref})+\tfrac12 a_s(T-T_{ref})^2\) is integrated consistently; unknown batch cp(T), k(T), density and particle distribution are open external validation gates. Do not fit the slope using outlet temperature without a frozen identifiability/holdout protocol.

## Three-reservoir finite-volume conservation

Each cell contains gas \(T_g\), rock \(T_s\), steel-shell \(T_w\) and temperature-dependent gas/solid heat capacities. For constant gas mass inventory \(m_g\) per control volume and mass flow \(\dot m\), the equations are

\[
m_gc_{p,g}(T_g)\dot T_g=
\dot m[h_g(T_{up})-h_g(T_g)]-q_{gs},
\quad
m_sc_{p,s}(T_s)\dot T_s=q_{gs}-q_{sw},
\quad
C_{w,cell}\dot T_w=q_{sw}-q_{wa}.
\]

Wakao-like interphase convection uses local gas viscosity/thermal conductivity/prandtl and source-validity guard \(15\le Re\le8500\). Wall-to-rock and wall-to-ambient UA are **separate imposed scenarios**; \(q_{gs}\) and \(q_{sw}\) are exactly equal and opposite in corresponding phases. Numerical BDF integrates both *gas inlet/outlet enthalpy flux* and *external wall loss* simultaneously:

\[
\Delta(U_g+U_s+U_w)-\int \dot m(h_{in}-h_{out})dt
+\int q_{wa}\,dt=0.
\]

This is a reduced-order low-Mach energy model: gas inventory is held at an **assumed constant density**, while sensible cp/enthalpy/transport depend on temperature. The gas pressure, gas compressibility/mass accumulation, transverse buoyancy and original experimental pressure-channel unit conversion are NOT solved. No prediction should be treated as high-fidelity industrial or pressure-qualified behaviour.

## Verification and reproduction

`python -m pytest tests/test_m2_enthalpy_wall_bed.py -v`

`python scripts/run_m2_enthalpy_wall_screen.py`

The former validates source coefficient/enthalpy derivatives, piecewise continuity, positive domain guards, geometry-derived steel shell capacitance, flow-fed and no-flow multi-reservoir energy conservation and source-external wall cooling. The latter produces a **synthetic** 4×120s heat/ambient/wall ledger for 350 K initial temperature, 480 K inlet, 0.02 kg/s assumed mass flow and eight cells. It archives inputs, SHA-256, source/properties/version metadata and explicitly **experimental_validation_pass=false**.

**No code path silently replaces the earlier verified Case B results, and the synthetic series does NOT count as experimental validation.** Subsequent steps can compare model-form sensitivity against the earlier baseline once experimental gas/slag properties and instrument measurements become available.
