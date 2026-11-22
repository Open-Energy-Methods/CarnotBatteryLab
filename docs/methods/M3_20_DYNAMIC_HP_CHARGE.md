# M3.20 — Thermally coupled 150°C HP-water preheater and electric booster

## Status and research question

This is the first explicitly *energy-coupled* external thermal source in the previously electric-heated real-air/TES numerical ODE. It does not simulate a functioning measured refrigerant compressor, HP transient refrigerant inventory, start/stop cycling or physical heat exchanger sizing. It is not a demonstrated operating Carnot battery.

Original requirement: source 80°C (outlet 60°C assumed), process hot water 110→150°C at 1 MW for 600 seconds. The M3.16b electric TES reference has 3 MW/bank resistance heater and assumed 500 W/K ambient heat-loss conductance, 4 m gas header, three staggered 1200/600 s banks. M3.18 source80 R600a 110→150°C heat-pump **EOS candidate** returned COP 2.302054578653484 at assumed compressor isentropic/motor efficiencies and 160°C nominal temperature limit. That number is neither measured nor a suitable speed-dependent calibrated map.

M3.19 compares heater setpoints 145–190°C and upper bounds for hypothetical HP preheat. M3.20 retains the 190°C TES gas target while adding actual power- and enthalpy-bounded HP heat injection into the ODE. Its results are conditional on heat-pump COP, temperature supply, heat-exchanger UA and source/sink water flows; hardware/equipment qualification remains open.

## Governing heat, electrical and source balances

At each solver RHS evaluation and during charging only, compute original feedback requested thermal power Qtarget = ηres Eres,original. For actual return-gas temperature/pressure and blower mass flow, with 150°C HP hot-water supply, 5 K minimum approach and gas preheat ceiling 145°C, define:

QHP = max(0, min(Qtarget, Qrated, UA*(145°C-Treturn), mgas*(hair(145°C,Pgas)-hair(Treturn,Pgas)), mhot,max*(hwater(150°C)-hwater(max(110°C,Treturn+5K))), msource,max*(hwater(80°C)-hwater(60°C))/(1-1/COP))).

Use zero if Treturn≥145°C or no gas/heater demand. Each water state is evaluated at assumed 2 MPa, gas enthalpy at instantaneous return-gas pressure (CoolProp HEOS). The 150°C/110°C hot-water loop, variable water flow and 80°C/60°C source loop are idealised instantaneously regulated reservoirs, with source/sink enthalpy balances and flow bounds. These endpoint approaches are necessary but *not a computed local exchanger temperature profile* and not a proven ≥5 K pinch throughout real equipment. The UA expression is a deliberately optimistic linear thermal-transfer bound, not a resolved LMTD.

Booster heat = Qtarget-QHP; Ebooster = Qbooster/ηres; EHP,compressor=QHP/COP; Qsource=QHP-EHP; hence QHP=EHP+Qsource at every time step. Optional gas preheater hydraulic penalty K=2 during charging is included in the return-side assumed pressure loss; ideally switched/bypassed during discharge. Water-side and source pumps assume 100 kPa each, efficiency 65%, rho=950 kg/m³ and variable instantaneous hot/source mass flows; Efluidpumps=(mhot+msource)*Δp/(rho*ηp). Pump power is treated as dissipation to the environment, not phantom useful gas heat.

All six HP time-integrated ledgers (gas heat, compressor electric, source heat, pump electric, hot-water mass, source-water mass) persist through charge and discharge and are validated on each stage. New gas, all-inventory first-law, electric and HP source/work closure use these ledgers, with existing gas mass and TES heat-loss inventories unchanged. When HP is disabled the legacy solver route and heater behavior are preserved.

The feedback shares rather than adds to the original heater demand; this bounds the dynamic comparison and avoids double-counting HP heat as extra charging. It can maintain nearly identical thermal trajectories if HP minor loss is zero. Any reduction in electric input must account for HP compressor, source/hot water pumps, and the existing booster and gas blower; source heat is not an electricity input. External source heat is real required industrial waste heat and site availability is unproven. External HP cooling fan, actual high-pressure refrigeration piping, charge-loop circulation temperature dynamics, electricity-grid demand, control response and physical COP part-load maps are absent.

## Cases and acceptance

Seven 10-cycle cases: electric-only, rated 0.5 MW with 25 kW/K, 1 MW with 25 and 100 kW/K, 1 MW 100 kW/K source/hot-water-limited variant, 12/16 cell and 5/2.5 s sensitivity at 1 MW 100 kW/K. All identical 1 MW 150°C 600 s service, source80, TES 190°C heater target, nominal three-bank staggered schedule, same assumed heat-loss and pump conditions. Validate approximate periodicity for the existing states/energy/service and additional HP thermal/electric/flow ledgers at the last two cycle boundaries, max accepted gas/rock/wall T≤200°C, independently resolved HX temperature margin, no duty deficit and mass/first-law closure. The baseline must reproduce 1.303752 MW within 0.5%. Relative changes for refined cases are reported without assuming asymptotic convergence. A fail must not be turned into a successful design.

## Critical limitations

The OST 2026 paper describes measured 100→70°C source 100→150°C sink operation, not source80 80→60°C and 1 MW. The HP compressor electrical COP in this model is derived from M3.18 EOS assumptions and is NOT experimental validation. The OST compressor's published nominal discharge limit 160°C cannot directly support 190°C gas charging, so the model uses its 150°C hot-water outlet only for low-temperature gas preheating and retains electric booster for the remaining temperature lift. The HP thermal nameplate and capacity/flow rates are hypothetical. No manufacturer compressors, flammability safeguards, machinery/pressure-vessel compliance, or independent uncertainty / holdouts. No ambient heat losses from the added HP/heat-transfer pipes. No credible Carnot round-trip electrical efficiency until a complete matched-service thermodynamic architecture with electricity-generation/discharge equipment exists.

## Reproduce

`pip install -e ".[physics,test]"`, `python -m pytest tests/test_m3_20_dynamic_hp_charger.py -q`, `python scripts/run_m3_20_dynamic_hp_charge.py --case hp1000_ua100k --output results/case_hp1000_ua100k.json`. Run the seven named cases and aggregate using `--aggregate results --output results/m3_20_summary.json`.
