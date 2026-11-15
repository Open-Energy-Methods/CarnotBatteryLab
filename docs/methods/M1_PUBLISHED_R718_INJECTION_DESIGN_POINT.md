# M1 independent design-point reproduction — two-stage R718 with liquid injection

**Evidence class:** V1 nominal published design-parameter cross-check + V0 thermodynamic/mass/energy verification. **Not** experimentally measured compressor-map validation, full H0 or hardware certification. Research code: \`src/carnot_battery_lab/physics/r718_injection_reference.py\`.

## Source, authorship and applicability

Zühlsdorf, B., Schlemminger, C., Bantle, M., Evenmo, K., and Elmegaard, B. (2018), *Design recommendations for R-718 heat pumps in high temperature applications*. 13th IIR Gustav Lorentzen Conference. DOI **10.18462/iir.gl.2018.1367**. Source: https://backend.orbit.dtu.dk/ws/files/153326069/_CP04_Zuehlsdorf_et_al._2018_Design_Recommendations_for_R718_HPs.pdf ; **Section 2.1 Table 1** and **Section 2.2 Figure 2 (parallel expansion plus liquid injection)**.

Published **nominal** compressor design states, not measured R718 operating map:

| Input | Low-stage impeller | High-stage impeller |
|---|---:|---:|
| Suction pressure (bar) | 1.0 | 3.2 |
| Suction temperature (°C) | 110 | 145 |
| Nominal mass flow (kg/s) | 0.196 | 0.222 |
| Nominal inlet volume (m³/h) | 1231 | 468 |
| Reported design pressure ratio | 3.2 | 2.0 |
| Expected isentropic efficiency | 0.74 | 0.74 |
| Speed | 80,000 rpm | 80,000 rpm |

**Critical distinction:** the 2018 article uses an injection intercooler (liquid from the condenser), whereas the earlier default \`r718.py\` implements an **externally cooled** constant-mass two-stage steam path. Their energy and mass accounting must not be mixed. The experimental Verpe et al. 2020 test is a separate rig with different measured stage maxima, not an independent validation of all 2018 nominal points.

## Thermodynamic reproduction and new independent check

Take the 2018 reported *design* P/T/η at the two inlets, the first-stage mass flow, and stage ratios. Calculate isentropic endpoint enthalpies using \`HEOS::Water\` and actual outlet enthalpy \`h_out=h_in+(h_is-h_in)/η_is\`. At 6.4 bar condensed saturated liquid state \`h_l\`, an injection stream is throttled isenthalpically to 3.2 bar, with \`h_inj=h_l\`. The required injection flow is **predicted** from mass and enthalpy mixing:

\`m_inj = m_1 (h_2 - h_3) / (h_3 - h_inj)\`; \`m_3 = m_1 + m_inj\`.

The published 0.222 kg/s stage-two mass flow is **not** used in the calculation, which instead predicts **0.221020 kg/s** (about -0.44% relative difference). Calculated volume flows from independent water EOS are approximately **1231.1 and 465.7 m³/h**, versus published 1231 and 468 m³/h. These are strong independent consistency cross-checks of the **nominal flow and topology data**; they cannot establish surge/choke, speed-line, drive efficiency or real steam performance.

Cycle first-law and mixing residuals:
\`Q_evap = m_1(h_suction1 - h_liquid)\`
\`Q_cond = m_3(h_discharge2 - h_liquid)\`
\`W_shaft = m_1(h_out1-h_in1) + m_3(h_out2-h_in2)\`
\`Q_evap + W_shaft - Q_cond = 0\` with exact injection enthalpy closure.

Source-side and condenser finite-HX enthalpy profiles are evaluated using segmented pinch/required-UA integration. These **external process interfaces are newly assumed**, not supplied in the 2018 impeller table. The 1-bar first-stage suction at 110°C requires saturated evaporation near 99.6°C. Here, a **120°C illustrative source inlet** and source outlet fixed at evaporation + 5 K (~104.6°C) maintain a finite source-side approach. A hypothetical pressurised source circuit is required to keep the source liquid. The 150°C sink supply is a separate imposed service with finite pinch and unknown installed HX geometry. The example does **not** apply to an 80°C source: that source cannot satisfy the 2018 1-bar suction/evaporation boundary. Electricity includes motor, gearbox and inverter efficiencies only, excludes source/process pumps and liquid-injection hardware.

### Reproduced numerical results (GitHub Actions, CoolProp)

- P-ratio stage 1/2: **3.2 / 2.0** (*specified published design inputs*).
- Mdot stage two predicted **0.221020 kg/s** compared to 0.222 kg/s (*independent held-as-check nominal data*).
- Nominal inlet volume EOS **1231.1 / 465.7 m³/h** compared to 1231 / 468.
- Condenser thermal rate **499.0 kW** at given first-stage mass flow; compressor drive-boundary heating COP **4.2406** with assumed 0.95 motor/gear and 0.98 inverter.
- Source thermal boundary **120.0→104.61°C** (*new illustrative inputs*); sink **110→150°C** (*reference service inputs*).
- Mass-mixing residual about **1.2×10^-10 W**, overall refrigerant first law zero at reported precision.

These calculations are **not** reproductions of an actual COP test in the 2018 or 2020 papers, and the headline COP cannot be compared directly to published values with differing heat/source boundaries.

## Scientific interpretation: two noninterchangeable reference cases

1. **Original H-REF 80°C source / 150°C useful process supply:** the available 2018 two-stage hardware reference is **not a compatible compressor choice**. Additional physically grounded compressor stages, a different natural fluid, a cascade/booster, or another hardware reference are necessary. The old illustrative 5:1-stage point remains labelled \`screening_unqualified\`.
2. **H-ALT hardware-aligned high-source R718 design:** nominal 1.0→3.2→6.4 bar liquid-injection layout and 120°C source inlet. It reproduces nominal mass/volume-state consistency, satisfies the finite HX idealised interfaces, and is a **component design-point-aligned conceptual cycle**. It must *not* be called manufacturer-certified or high-fidelity hardware model without actual compressor performance maps and measured heat pump duty.

## Required next tests before hardware-qualified plant claim

- Digitised measured stage pressure/volume/speed/η maps, at 1.0/3.2bar inlet, with surge/choke and dry vapor envelopes.
- Demonstrated stage-two injection separator and nozzle with validated pressure drop, piping losses and actual injection water temperature.
- Source/sink pressure, HX geometry-derived UA, refrigerant property/entropy/cooling utility accounting and part load.
- Thermo-hydraulic energy and safety requirements for coupling to high-temperature TES and process service.
- Independently measured whole-cycle performance under matched supply/source states.

## Reproduce

\`python -m pip install -e ".[physics,test]"\`  
\`python -m pytest tests/test_r718_injection_reference.py -v\`  
\`python scripts/run_r718_injection_design.py --output results/r718_injection_design_reference.json\`

JSON includes exact source inputs, reported comparator fields, predicted mass and volume, first-law/injection residuals, method/permission labels, fluid/backend version and input hash. The GitHub Actions \`r718-realfluid-tests\` job performs these checks on a clean Linux environment.
