# M3.13 — fixed process duty and ideal water mixing

The earlier water-flow feedback improved outlet temperature by reducing delivered mass. The fixed-demand alternative declares a temperature of 150 C, fixed inlet enthalpy hi and fixed duty Q*. These give total mass flow M=Q*/(h*-hi), not two independent degrees of freedom. If the exchanger outlet hHX exceeds h*, send Q*/(hHX-hi) through the exchanger and the rest through an ideal adiabatic inlet-water bypass, yielding mixed outlet h*. Otherwise send all flow through the exchanger and report actual duty and deficit. No additional water or heat source. The HX branch alone updates its finite water inventory; mixed product duty is equal to the existing HX water energy export. Separately integrate bypass mass, nonnegative duty deficit and excess. Demand minus deficit plus excess equals signed delivered heat. The bypass is an ideal algebraic actuator, not hardware with valve slew, hydraulic pressure drop or pump electricity.

The target is 150 +/- 0.5 C and duty +/-0.15% (same relative duty tolerance as the 1 MW reference). Because total mass flow is fixed, the simultaneous accepted enthalpy interval is the intersection of both tolerances (upper endpoint excluded in the dense-output duration calculation). Root detection remains bracketed by accepted steps; full modeled service requires periodic gate, accepted-node limits and essentially complete modeled interval coverage. This is not a continuous-time certification. Periodic-state gate is inherited from M3.12; no periodic outcome is presumed.

Predeclared 600 s discharge with 1200 s charge, ten consecutive cycles, identical assumed K=2 valve loss. Reverse-flow 500, 1000, 2000 and 3400 W demand levels are separate services; never compare as equal service. At 1000 W compare forward/reverse and bypass/no-bypass, independently refine bed and HX from 3 to 5 cells and halve max integration step. These are sensitivity checks, not formal grid convergence. Report actual energy, missing energy, overdelivery, grade heat, mass delivered, modeled electricity, duration and full-service gate. A negative outcome is permitted. No ranking across unequal duties or qualification of the original industrial case. Auxiliary electricity, valve dynamics, measured equipment parameters and experimental validation remain excluded.

Reproduce:
```sh
pip install -e ".[physics,test]"
python -m pytest tests/test_m3_13_matched_duty.py -q
python scripts/run_m3_13_matched_duty.py
```
