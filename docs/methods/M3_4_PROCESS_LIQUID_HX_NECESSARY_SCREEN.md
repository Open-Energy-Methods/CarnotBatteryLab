# M3.4 — The actual 110→150°C process-liquid heat exchanger is NOT the gas/TES outlet

**Evidence class:** reproducible **necessary physical interface screen**, not calibrated/installed industrial heat exchanger or compressor qualification. This milestone is independent of supplier R600/R718 compressor-map replies and can be merged on its own.

## Contract: one thermal service, two different fluids

The original benchmark requires **1 MW gross useful heat delivered to a liquid process stream** heating **110→150°C**. The earlier M3.0–M3.3 reverse-flow packed-bed model instead warms a **constant-cp gas** passing through a simulated rock bed. The original code's phrase "process gas" does **not** mean a pressurised water or liquid process stream; a gas outlet temperature of 150°C is **not** by itself evidence that water can exit at 150°C with finite heat transfer.

For a nominal liquid heat capacity `c_p,l=4180 J/(kg K)`, the modelled required process water flow is **5.980861 kg/s**:

`m_l = Q_process / [c_p,l × (150-110)] = 1,000,000/(4180×40)`.

This is a **constant-cp boundary assumption**, not a measured plant water flow. Actual water remains liquid at 150°C only if its measured **absolute** static pressure exceeds the local saturation pressure at 150°C, approximately **0.476 MPa** (subject to pressure loss, stability margin and water property accuracy). M3.4 computes saturation pressure independently using CoolProp `HEOS::Water` but **does not invent a measured process-loop pressure**.

## Counterflow heat exchanger, separate from the bed

For a *candidate modeled hot gas inlet* `T_g,in`, with mass flow `m_g` and gas heat capacity `c_p,g` (from the existing gas-bed model), a heat transfer of exactly 1 MW to water requires

```text
T_g,out = T_g,in - Q_process/(m_g * cp_g)

ΔT_hot,end  = T_g,in  - T_water,supply = T_g,in  - 150°C
ΔT_cold,end = T_g,out - T_water,return = T_g,out - 110°C

min(ΔT_hot,end, ΔT_cold,end) ≥ 5 K (ASSUMED design minimum)
```

With constant two-stream `c_p`, the local counterflow temperature difference is a **linear function of cumulative exchanged duty**, so a terminal minimum of at least 5 K is sufficient to avoid internal crossing under this specific thermophysical approximation. This is neither a vendor-certified approach limit nor an installed-`UA` assessment. For an explicitly assumed gas case 220°C inlet, 10 kg/s and `cp=1000 J/kgK`, the hot outlet for 1 MW is **120°C**; hot and cold-end terminal approaches are **70 K** and **10 K**, respectively. That mathematically passes the 5 K pinch, yet without a verified process-loop pressure and installed UA **it does not qualify industrial delivery**.

For a thermodynamically possible state, required `UA = Q/ΔT_lm` with the actual constant-cp counterflow LMTD. The code reports this as an **estimated required UA**, not an installed exchanger. A passed invented/assumed `UA` cannot certify process equipment. External shell/pipe pressure drops, heat transfer fouling, non-ideal thermal dispersion, actual process-liquid property variation, residence/hold-up, transient control and gas blowers remain unverified.

## Applied to the existing real-fluid numerical R718→TES→gas-discharge result

The independent M3 source-generation script was run before the HX screen, with 2×120 s charged R718/TES steps followed by three 60 s reverse gas discharges. This is a model-only scenario, *not* physical testing. Its nominal return gas state was **110°C**, separate from the real process water return at 110°C. The original three discharge intervals produced these **modeled gas outlet** samples (°C):

| 60 s interval | Initial gas outlet | Time-mean gas outlet | Final gas outlet |
|---|---:|---:|---:|
| 1 | 114.40 | 103.75 | 103.48 |
| 2 | 103.48 | 103.24 | 103.01 |
| 3 | 103.01 | 102.79 | 102.57 |

To heat real process water to 150°C with even a nominal **5 K** thermal approach, the heat exchanger's **gas inlet must be at least 155°C at every required service instant**—before checking gas temperature reduction at the cold terminal. **All nine sampled model temperatures are below 155°C**, and the earliest sampled gas temperature (~114.4°C) is insufficient by ~40.6 K at the hot terminal alone. Therefore the 1 MW 110→150°C liquid process service **fails a strict necessary temperature-grade condition at every sampled state**. Increasing the installed UA cannot overcome this crossing; neither a large imaginary gas flow nor an unverified compressor can cure a hot inlet colder than the required process-water supply.

The source M3 gas-only model also reports **zero high-grade qualified gas heat** under the original 110→150°C candidate, and its integrated signed heat to gas is **negative** for that test due to the selected initial storage state. The new physically separate process-water HX criterion is even stricter, while preserving the original model energy balances unchanged. Do not convert low-grade gas enthalpy into credited 150°C process heat.

This **demonstrates failure of one explicitly simulated short-charge/short-discharge schedule**, not global impossibility for all heat pumps, all bed inventories, solar or industrial sources. The bed gas/rock thermophysical coefficients and Ergun pressure loss remain uncalibrated; R718 equipment maps are absent. The M3.4 report has `actual_process_liquid_heat_delivered_qualified=false`, `industrial_H_REF_service_qualified=false`, `RTE=null` permanently until independently supported physics and measured process streams exist.

## Verification and reproducibility

Added `src/carnot_battery_lab/physics/liquid_process_hx_gate.py`:
- Conservation-defined gas cooling after exactly 1 MW; positive finite pressure and process/liquid parameters;
- **Water saturation-pressure** gate through CoolProp, with actual pressure explicitly unknown by default;
- Counterflow terminal pinch, **required UA** (only if both endpoints satisfy a user-declared minimum), and optional clearly labeled *assumed* installed UA;
- Strict original initial/mean/final simulated gas sample availability per interval, with error if a value is missing; no fabricated between-sample thermal guarantee;
- No measured industrial exchanger, hardware compressor map, matching architecture or system RTE claims even for synthetic unit-test positives.

Added `scripts/run_m3_4_gas_to_liquid_process_hx_screen.py` to consume the existing numerical `scripts/run_m3_r718_sequential_service.py` output with exact input-SHA256 provenance and contract verification. Dedicated CI installs real-fluid EOS, executes regression tests, regenerates the original gas/TES trace and reports the actual sampled numerical liquid-HX necessary-condition failure.

```bash
python -m pip install -e ".[physics,test]"
python -m pytest tests/test_m3_4_liquid_process_hx_gate.py tests/test_finite_hx.py -v

python scripts/run_m3_r718_sequential_service.py \
  --output results/m3_r718_sequential_hp_tes_discharge_screen.json

python scripts/run_m3_4_gas_to_liquid_process_hx_screen.py \
  --sequential-model results/m3_r718_sequential_hp_tes_discharge_screen.json \
  --output results/m3_4_gas_to_liquid_process_hx_necessary_condition.json
```

**Next independent work after M3.4:** develop dynamic fluid-to-liquid actual counterflow finite volume HX with time-varying gas supply, physically resolved liquid outlet/pressure drop and transient UA uncertainty. This still can be developed without manufacturer compressor replies, but until real inlet and equipment data exist its predictions remain hypothetical.

**Decision:** Original short schedule rejects 110→150°C liquid-process service at necessary gas temperature, `NO_MATCHED_SERVICE`; model code/test verification is not experimental validation, thermal/gas-only cycling is not electrical Carnot-battery RTE.
