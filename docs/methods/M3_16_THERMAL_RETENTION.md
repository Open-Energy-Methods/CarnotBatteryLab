# M3.16 — thermal retention, regenerative buffer, and electric load screening

## Reference and scope
M3.15 exact-head seven workflows passed, merged dc6e067. In 4 m header surrogate the 1 MW cooler cap achieved 1 MW/150 C for 600 s at approximate periodic operation, mean modeled electrical input 2114886.5575723182 W including water/coolant pumps. Unrestricted cooler 3148469.2369691115 W. Same 1200/600 s staggered three-bank schedule, 20 hypothetical vessels per bank, 4 m headers. No actual qualified continuous service.

## Changes
Test cooler capacity 0, 250, 500, 750, 1000 kW. Zero means physically remove the modeled heat export, not just omit its power from results. At 1 MW cap additionally independently test 12 versus 16 cells and 5 versus 2.5 s maximum step. Return-temperature feedback uses assumed sink 100 C and proportional control q=min(cap,UA*max(0,T_return-T_set)), with 160 or 170 C setpoint and 1 MW cap. Heater power remains proportional control capped at installed nameplate. Test 3 MW per bank instead of 5 MW for two selected cases, not a global optimum.

A finite sensible thermal buffer in each bank exchanges heat with the return gas: during discharge capture UA*max(Tgas-Tbuffer,0); during charge release UA*max(Tbuffer-Tgas,0). A constant 5 MJ/K capacity, 100 kW/K conductance, and 100 W/K ambient-loss conductance at 25 C are explicitly hypothetical; the buffer begins at the same cold state as the gas, evolves conservatively through all phases and is never reset. The model is a lumped thermal contact with ideal phase selection, no added hydraulic loss, piping, pump or real heat exchanger design, so recovery is not actionable equipment sizing. The buffer has separate captured, returned, loss and stored-energy-change ledgers; add its inventory and ambient loss to total first law. No credit subtracted from modeled electricity. Buffer temperature and all buffer energy ledgers repeat to the same M3.12 two-boundary tolerances in addition to existing periodic conditions. Compare buffer cases to exactly matched nonbuffer cases.

## Acceptance and reporting
Ten cycles, 13 configurations. Same duty and grade gate and positive raw temperature margin. Added analyst-selected 200 C maximum accepted-node gas, rock and HX wall temperature screen; not a material rating or continuous peak guarantee. A failed periodic or service gate is a valid negative result. Numerical errors cause workflow failure and must be resolved or retained as failed evidence, not converted into false feasibility. Only complete case sets aggregate; rank eligible primary-grid cases by mean modeled electric power, not recovered heat. Strongest nonreference candidate requires its own later mesh/time corroboration. No claims of global optimization or hardware validation.

Exergy: at 25 C reference, use CoolProp water h and s at 2 MPa, inlet 110 C and target 150 C; calculate target flow exergy rise m[(h2-h1)-T0(s2-s1)] for 600 MJ target heat. Ratio to modeled electric input reported only for full-service cases; this is target reference, not actual instantaneous output exergy or complete component irreversibility. Exergy of rejected heat, buffer, inventory, pumping and ambient losses needs consistent entropy balances in the next milestone. No Carnot round-trip efficiency. Same unresolved utility assumptions and ideal phase switching as M3.15.

## Reproduction
pip install -e ".[physics,test]"
python -m pytest tests/test_m3_16_thermal_retention.py -q
python scripts/run_m3_16_thermal_retention.py --case cap0_buffer --output results/case_cap0_buffer.json
Run all 13 cases; aggregate with --aggregate results --output results/m3_16_summary.json.
