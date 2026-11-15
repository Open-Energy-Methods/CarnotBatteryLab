# M1 hardware evidence, hydraulic auxiliary work and HX convergence

**Status:** verification increment within M1. The inherited R718 reference remains **screening-only**, NOT independently validated at its requested 80°C source / 150°C service point. Consult the original R718_FINITE_HX_SCREENING.md and R0–R17 release gates.

## Published compressor evidence (distinct hardware and evidence classes)

**D-2018, nominal compressor DESIGN data**: Zühlsdorf, Schlemminger, Bantle, Evenmo & Elmegaard, *Design recommendations for R-718 heat pumps in high temperature applications* (2018), doi:10.18462/iir.gl.2018.1367, Section 2.1, Table 1 (publisher PDF accessible via DTU Orbit). Low-stage design: inlet 1.0 bar, 110°C, 0.196 kg/s, 1231 m³/h, PR=3.2, expected η_is=0.74. High-stage design: inlet 3.2 bar, 145°C, 0.222 kg/s, 468 m³/h, PR=2.0, expected η_is=0.74. Rotational speed is 80,000 rpm for both impellers. The paper explicitly says these are expected isentropic efficiencies validated in air tests and comparable steam equipment; it does not provide a complete verified R718 compressor speed/flow map for the present case. Stage nominal mass flows differ; our **externally cooled constant-mass** two-stage model is not the injection/arrangement used by all published examples.

**E-2020, measured MAXIMA on a different rig**: Verpe, Schlemminger, Bantle & Ahrens, *Experimental evaluation of a water based high temperature heat pump with novel high pressure lift turbo compressors*, doi:10.18462/iir.gl.2020.1019 (SINTEF/IIR). Reported maximum first-stage PR 2.4 and max η_is 0.67; second stage PR 2.0 and max η_is 0.77; two-stage system delivered steam at 4.23 bar with a reported COP 4.5. Maxima are not simultaneous guaranteed operating points, and the authors describe a separate physical rig. **It is invalid to stitch these peak efficiency/PR values into one imaginary manufacturer curve.**

**Observed comparison:** the current *hypothetical* equal-stage R718 pressure ratio ~4.659 exceeds both separate D-2018 design ratios and the E-2020 measured maxima. This is a hardware-compatibility **negative result**, not universal impossibility. Real compressor selection demands actual pressure ratio, speed, volumetric flow, inlet pressure/temperature, map boundaries (choke/surge), discharge temperature and installed multiple-stage design, or a different cycle/architecture. M1 must remain BLOCKED for manufacturer-qualified H0.

For the 2018 design Table 1 we independently recompute density and inlet volumetric flow from water EOS at each reported p/T and the reported mass flow. This is a **property-level cross-check**, not a reproduction of measured outlet state nor an independent cycle/rig validation. References are linked; the original PDFs are not redistributed.

## Liquid auxiliary hydraulics

The separate pressurised liquid circuits are **hypothetical transparent sizing inputs** in auxiliary_hydraulics. They use actual calculated source, process and interstage coolant mass flows from the R718 screen. For each pipe:
- fluid temperature, pressure, density ρ(P,T) and dynamic viscosity μ(P,T) supplied by CoolProp; the screening requires subcooled liquid at stated pressure (the 130°C process water is at **1 MPa**, not atmospheric pressure);
- mean velocity v=mdot/(ρ A), Reynolds=ρvD/μ;
- laminar Darcy f=64/Re; turbulent Haaland approximation f = [−1.8log10((e/D/3.7)^1.11+6.9/Re)]^−2; smoothly interpolated transitional regime (model choice);
- Δp=(fL/D+K)ρv²/2, hydraulic pump electrical work Δp(mdot/ρ)/η_pump;
- inverter and gearbox efficiencies are separately specified as 0.98 and 0.95, as **illustrative** representative values aligned with Zühlsdorf et al. 2018 Table 1 context; do not imply the same motor/gear hardware or guaranteed efficiencies.

The original compressor electric COP used motor efficiency only. This extension gives an explicitly **broader** electrical meter boundary (inverter, gear and all three liquid pumps). The fan for any TES, refrigerant-side heat-exchanger and piping pressure drop, startup, environmental loss, controls and auxiliary cooling utility remain outside and must not be hidden when comparing layouts. Pump output is not automatically counted as useful heat; assume pump motor/dissipation heat leaves to unqualified environment and state this energetic boundary.

## HX quadrature convergence

For each of the source, condenser and intercooler, required-UA = Q∫[1/(Th(x)-Tc(x))]dx along a reverse counterflow fraction of cumulative heat x. Real-fluid T(p,h) profiles include superheating, desuperheating and two-phase condensation/evaporation, so terminal-only LMTD cannot detect all internal pinches. The model uses uniform-x trapezoidal numerical integration. Sweep 24,48,96,192,384 segments and report changes in UA for **all three** exchangers independently. A result change <=1% at final grid is a provisional quadrature-screening criterion, not accuracy of actual HX geometry or heat-transfer correlation. Phase boundaries may reduce textbook asymptotic order; do not advertise Richardson convergence unless the observed sequence supports it. To establish physical HX UA require actual area, internal geometry, clean/fouled U and temperature-dependent pressure loss.

## Reproduce

Install CoolProp dependencies and run:
- python -m pytest tests/test_m1_evidence_hydraulics.py -v
- python scripts/run_m1_reference_evidence.py --output results/m1_reference_evidence.json

The output explicitly distinguishes 2018 nominal data, 2020 observed reported maxima and the *screening model*, plus full pipe assumptions and UA resolution values. It is machine-readable and archived in the real-fluid GitHub Actions workflow. Do not use this output to certify the 1 MW installation.

## Acceptance status

**Achieved:** source-verified design-point provenance, independent EOS density comparisons, evidence-class separation, transparent pipe and pump electrical accounting, source/process fluid-phase guards, numerical HX quadrature sequence, and negative controls.

**Blocked:** measured full steam-compressor map, geometry- and operating-specific compressor validation, actual full plant auxiliary power, documented refrigerant pressure drops in cycle solver, off-design, geometry-based HX UA and experimental cycle data matched to 80→70°C source and 150/110°C process. This is a realistic scientific stop; M1/H0 remains unvalidated, and no present compressor model may be presented as industrially suitable.
