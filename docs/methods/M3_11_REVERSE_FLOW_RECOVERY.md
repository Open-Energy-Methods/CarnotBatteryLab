# M3.11 — reversible bed routing and temperature-qualified recovery

Status: research implementation, pending exact-head CI and result review. No measured validation or industrial qualification.

## Scope and equations

The M3.10 real-air closed inventory is retained. During charging the hydraulic order is physical bed cells 0..N−1, then the HX gas cells and return. During reverse discharge only the bed order is reversed; the blower orientation, HX gas/water counterflow and return cooler remain unchanged. All physical mass, internal energy, solid temperature, wall temperature and water enthalpy states persist, including across cycles. Face fluxes use upstream enthalpy; differences are scattered to physical cell indices. The two active bed ports each use an assumed minor loss Δp = K m²/(2ρA²), with return area A; losses affect the blower/bed and bed/HX pressure equations. They are not measured. Switching is instantaneous and ignores valve dead volume, moving actuators, pressure waves, leakage and switching electricity.

At 2 MPa water pressure, the 150°C enthalpy threshold is obtained from the existing water table. Qualified heat is the integral of water mass flow times (outlet enthalpy − inlet enthalpy), only when outlet enthalpy meets the threshold. Duration and the complementary signed water ledger are recorded. Roots are bracketed by accepted BDF nodes and refined using dense output; cumulative water ledger differences integrate each qualifying segment. Unbracketed excursions are not guaranteed detected; max-step sensitivity is mandatory. Heat below grade is not counted as service. This is a temperature-only metric, not guaranteed 1 MW duty or continuous matched service.

## Study design

Compare identical cold initial conditions, 1200 s charging, 600 s discharging, same assumed blower, heater, sink and K=2 at each active port. Report charge heater and blower energy differences explicitly. Compare forward and reverse qualified duration and energy alongside gross signed heat, peak and final temperature, and discharge blower consumption. Sensitivities: independently refine bed and HX from 3 to 5 cells, halve integration max step from 5 to 2.5 s, increase valve K from 2 to 20. Three repeated cycles each direction use continuous inventories, not fresh starts. Differences at consecutive cycle boundaries are diagnostics, not proof of periodic convergence; across later cycles charging electricity may differ and no matched-energy ranking is claimed. Independent spatial changes are preliminary sensitivity rather than formal grid convergence.

The pre-existing M3.10 run remains the default (forward, no added valve loss, one cycle). Its top-level summary refers to the first cycle; repeated results are explicitly in cycle_records. Separate whole-repeated-sequence first-law and mass residuals are included.

## Reproduction

```sh
python -m pip install -e ".[physics,test]"
python -m pytest tests/test_m3_10_closed_real_air_cycle.py tests/test_m3_11_reverse_flow_recovery.py -q
python scripts/run_m3_11_reverse_flow_recovery.py
```

The workflow audits mass, all component energy ledgers, grade split, route order and equal cold-start charging. A passing workflow establishes numerical verification only. No positive reverse-flow benefit is imposed as an acceptance criterion. A negative or inconclusive result is permitted. External water pump, cooler circulation and valve actuation electricity are excluded; the equipment map and heat-transfer coefficients remain hypothetical. No Carnot battery round-trip efficiency is reported.
