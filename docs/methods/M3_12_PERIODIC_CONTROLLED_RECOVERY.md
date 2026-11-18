# M3.12 — periodic operation and bounded water-flow feedback

Predeclared numerical study, not hardware validation. The physical state is carried through ten repeated 1200 s charge / 600 s discharge cycles. State recurrence is tested at identical cycle boundaries for all rock, wall, water and gas temperatures (0.05 K), gas pressure (50 Pa) and relative gas cell mass (0.0002). Gas mass and temperature jointly determine the internal energy at fixed volume. Require two successive transitions that also show stable heater, blower, cooler, gross, grade and band energy (max of 10 J or 0.5% of the larger magnitude), and grade/band durations (0.5 s). These analyst-selected tolerances are numerical diagnostics only. No extrapolation to infinite repetitions; ten cycles may fail. Conservation CI and periodic gate are distinct.

Water-side proportional feedback changes the imposed mass flow in the conservative liquid enthalpy equations: m = clip(m_nom + Kp*(T_out-423.15), 0.1*m_nom, 2*m_nom); charge flow zero. Fixed inlet state; equal inlet/outlet instantaneous flows preserve water mass. The assumed actuator is instantaneous, with no pump power, pressure drop, slew rate or anti-windup needed for proportional control. No physical actuator is qualified. The fixed-flow case uses Kp=0. The band metric is accepted-step-bracketed dense-output integral for 149.5 <= T < 150.5 C, in addition to the separate >=150 C grade metric. Root detection may miss excursions entirely within a solver step. This is temperature tracking, not 1 MW matching. Band heat can include water below 150 C and must not be relabeled grade-qualified heat.

Screen three preselected gains (0.001, 0.004, 0.012 kg/s/K), report two fixed-flow references and separately refine the middle gain in time and space. Rank ONLY periodic-gate-passing gain cases by final-cycle band heat, with all input electricity, gross and grade heat and water throughput reported. This is a finite screening, not a global optimum or equal-energy matched-service comparison. Report negative results; no gain is required to pass the periodic gate. Independently report the numerical sensitivity of the middle gain; no grid convergence claim. Excluded cooler/pump/valve electricity and hypothetical component parameters remain blockers.

Reproduce:
```sh
pip install -e ".[physics,test]"
python -m pytest tests/test_m3_12_periodic_recovery.py -q
python scripts/run_m3_12_periodic_controlled_recovery.py
```
