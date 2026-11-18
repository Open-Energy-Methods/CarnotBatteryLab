# M3.10 — closed pressure-connected real-air thermal charging and discharging sequence

## Scope

M3.9 verified an open pressure-driven air bed and counterflow process-water exchanger beginning with a preheated solid. M3.10 replaces the two infinite-pressure air reservoirs by a return gas volume and a hypothesized blower. The complete finite gas inventory is conserved, pressure follows the same CoolProp HEOS::Air EOS throughout, and the initial gas, solid, water and wall inventories all start at 110°C. Charging is explicit electric resistance heating; the same state vector is then continued into discharge. The original M3.9 open-model reservoir fields are retained in the embedded geometry configuration for compatibility but are **not used** as boundary sources by the closed solver. No compressor map, physical gas or water pressure rating, plant or wear limits are inferred.

The study is a **single small-scale charge/discharge sequence, not a periodic cycle**, not a Carnot battery electricity recovery model, and not the original 1 MW, 110→150°C industrial service. The high-temperature gas charge specified here is unrelated to the unqualified original 80→70°C liquid waste-heat source. No manufacturer map has been invented.

## Fixed declared assumptions

| Model quantity | Assumption, not measurement |
|---|---:|
| Packed bed length, diameter, porosity, particle diameter | 0.5 m, 0.3 m, 0.4, 10 mm |
| Rock density, cp, fixed volumetric conductance | 2600 kg/m³, 850 J/(kg K), 5000 W/(m³ K) |
| Initial uniform gas, solid, HX metal, water | 383.15 K |
| Initial assumed gas pressure | 250 kPa abs |
| HX gas volume, flow area, hydraulic diameter | 0.01 m³, 0.012 m², 0.03 m |
| HX gas equivalent length, friction, minor-loss coefficient | 1 m, 0.04, 2 |
| HX overall UA, water inventory, wall capacity | 120 W/K, 1 kg, 1000 J/K |
| Return side gas inventory volume, flow area, loss coefficient | 0.02 m³, 0.012 m², 3 |
| Water inlet, pressure, discharge mass flow | 110°C, 2 MPa abs, 0.02 kg/s |
| Blower assumed shutoff head, zero head flow | 500 Pa, 0.1 kg/s |
| Assumed blower gas-work and motor efficiencies | 0.65, 0.85 |
| Resistance heater nominal electrical cap, efficiency | 5 kW, 95% |
| Heater proportional gain, return-gas target | 300 W/K, 190°C |
| Cooler UA, prescribed infinite sink | 100 W/K, 100°C |
| Charge / discharge | 1200 / 180 s |
| Baseline meshes, BDF maximum step | 3/3 gas bed/HX cells, 5 s |

No additional water or gas mass is supplied during charge; water remains in the HX at its initial mass (no water boundary flow during charge), and warms with the metal and gas. During discharge the original small water flow is applied, supplying water at 110°C. Gas flow direction remains the same in both phases; no reverse-flow manifold or valve dynamics are simulated. There is no bed/HX ambient wall loss in this prototype.

## Conserved extensive gas and thermal states

The gas has a rigid volume per finite-volume cell, with conserved M_i and U_i. Each gas state (T,P,h,rho,mu,a) is recovered from (M_i/V_i,U_i/M_i). A pressure-driven Ergun bed face, series Ergun/Darcy interface, HX Darcy and return-side Darcy resistance determine signed low-Mach upwind mass/enthalpy fluxes between cells. The pressure rise driving circulation is a **hypothetical low-head blower curve** with positive branch only:

    H(m) = H0 [1 - (m/m0)^2]
    P_bed - P_return + A*m + B*m^2 = H(m)
    W_gas = m*H(m)/(rho_suction*eta_blower)
    W_electric = W_gas/eta_motor

Here A,B are the Ergun inlet half-cell coefficients in mass-flow coordinates. The blower curve and efficiencies are assumed, not fitted to any actual machine; reverse flow is prevented by an ideal check valve. A request outside the positive-head branch fails rather than extrapolating to turbine operation. The low-head shaft-work approximation is restricted to small head/absolute pressure ratio; accepted solver nodes also check low interstitial/HX Mach. No real surge, valve Cv, mechanical inertia, blowdown, leak or manufacturer map is implied.

At the blower face, the identical suction enthalpy flux leaves the return volume and enters the first bed cell. Shaft work is added to the gas energy separately. The pressure losses and gas-volume pressure dynamics appear within the conservation equations, not as an extra invented thermal-energy subtraction.

An explicit idealized thermostat provides electrical heater power bounded by the assumed 5 kW cap during charge. Only eta_heater times this energy reaches the gas, with the difference classified as an external heater loss. During discharge, the heater is off and the return gas loses heat at:

    Q_cool = UA_cool * max(T_return - T_sink, 0)

The infinite sink assumption supplies an external heat-rejection boundary, not a simulated cooler water circuit or electricity-free real system. Secondary cooler circulation electricity, water pump electricity, real valves and piping containment are excluded. The blower motor loss is separate from gas shaft work. Water uses an isobaric enthalpy inventory with single-phase table at the assumed 2 MPa pressure; water pressure losses and boiling margins at actual unknown local pressure are not qualified.

The integrated ledgers include heater electricity, heater gas heat, blower electricity, blower gas work, heat rejection to sink, signed net water boundary heat and interface mass. The revised implementation also integrates gas-solid, gas-wall and wall-water transfers and reports each thermal-inventory residual independently. In each phase, total gas mass must remain unchanged and:

    ΔU_g + ΔU_s + ΔU_wall + ΔH_water
      = Q_heater_to_gas + W_blower_to_gas - Q_cool - Q_water

The electrical-boundary form replaces the two delivered energy terms with heater and blower electrical input and explicitly includes the modeled heater/motor losses. These forms are algebraically related; the independently integrated inter-component heat flows separately test individual inventories. Positive water boundary heat is gross modeled heat, not automatically heat meeting the stipulated industrial grade. No electricity-to-electricity efficiency is calculated, and no initial inventory is reset or freely replenished at the phase switch.

## Verified first numerical study

The initial dedicated workflow [44407401331](https://github.com/Open-Energy-Methods/CarnotBatteryLab/actions/runs/44407401331) passed 16 M3.9/M3.10 targeted tests and six complete charge/discharge scenarios on revision 5efdee73. Values are small-scale model outputs:

| Case | Heater electricity, kWh | Net heat stored in solid during charge, kWh | Water boundary heat during discharge, kWh | Cooler heat, kWh | Final water outlet, °C |
|---|---:|---:|---:|---:|---:|
| Baseline 3/3 | 0.856869 | 0.739136 | 0.120952 | 0.062975 | 128.175 |
| Coarse 2/2 | 0.831056 | 0.714517 | 0.110262 | 0.065377 | 125.833 |
| Refined 4/4 | 0.870789 | 0.752337 | 0.127406 | 0.061423 | 129.589 |
| Blower head 300 Pa | 0.803929 | 0.695020 | 0.108684 | 0.049741 | 126.118 |
| Cooler UA 30 W/K | 0.856869 | 0.739136 | 0.123983 | 0.034368 | 129.117 |
| Charge 600 s | 0.540687 | 0.467471 | 0.072071 | 0.045199 | 120.725 |

Baseline blower electricity across both phases is 6.048 Wh, separate from heater electricity. The initial six cases have gas mass residual below 1.1e-16 kg and full electrical-boundary residual below 5.1e-8 J. This verifies numerical conservation, not experiment. Joint mesh refinement from 3/3 to 4/4 changes terminal water by 1.414 K and net water heat by ~5.3%; numerical independence is not established. The baseline final water temperature is below the original grade and the small water stream is not the industrial duty. The output report includes accepted-node temperature and pressure ranges, separate component ledgers, remaining solid inventory, and a seventh max-step sensitivity case following the initial study.

The lower cooler UA gives more gross water heat in this one sequence because it rejects less thermal energy to the prescribed sink; that is not permission to omit cooling hardware, pressure limits or circulation. Likewise remaining energy above the cold reference after three minutes is not a loss and cannot be credited as recovered process energy. No repeated periodic state or full useful heat recovery has been established.

## Reproduce and remaining gates

    python -m pip install -e ".[physics,test]"
    python -m pytest tests/test_m3_10_closed_real_air_cycle.py tests/test_m3_9_open_real_air_water_train.py -q
    python scripts/run_m3_10_closed_real_air_cycle.py

The dedicated workflow archives the JSON with every assumption and stage ledger. Remaining work includes independent bed/HX spatial convergence and full-cycle integration tolerance checks, reverse-flow charge/discharge plumbing, variable-Re heat-transfer closure, measured blower/valve/cooler characteristics and a finite secondary cooling circuit, source-compatible compressor maps, actual process regulation and independently measured bed holdouts. Original 1 MW service must be re-established with the **closed variable-property** model rather than transferred from M3.8's different constant-property ideal-control calculation. No scientific v1.0 or industrial hardware claim.

Sources: the M3.9 model and M3.6 water EOS treatment; Bell et al. (2014), CoolProp DOI 10.1021/ie4033999; Ergun (1952), Chemical Engineering Progress 48, 89–94. The blower curve and all equipment inputs are declared synthetic assumptions, not sourced manufacturer data.
