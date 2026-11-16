# M3.2 — Matched R718–TES gas service and repeated thermal-state screening

**Evidence class:** finite-grid, numerical gas-thermal feasibility screening only. **NOT** a manufacturer-qualified 80°C-source R718 compressor, measured packed-bed validation, industrial liquid-process exchanger, or architecture-performance result.

## Scientific correction before screening

The earlier finite-volume `BedStep.first_temperature_K` field was erroneously sampled from cell 0 (the **inlet** cell for the standard x=0→L solver). Its physically correct first-time **outlet** value is the state at cell `[-1]`. For reverse-flow discharge the complete field is inverted before passing to that solver, so the corrected initial outlet is the physical original x=0 end. A deliberately nonuniform bed regression demonstrates that the previous index could misclassify a high-grade discharge.

All earlier **temperature-grade classifications** that relied on the first sample require regeneration. The change does not alter the conservative ODE, heat transfer, final state or integrated energy ledgers. Previous PR #31 numerical-grade outputs remain historical evidence until reproduced with this fix; no prior process grade is carried forward as independently verified.

## Target model contract, units and separate gates

The original proposed H-REF **liquid** contract is a waste-heat source at **80→70°C**, and process fluid at **110→150°C** with **1 MW** of heating. This module models only a *constant-cp process GAS proxy* at 383.15→423.15 K, reverse gas flow 25 kg/s, with a 60 s interval. This does **not** establish liquid delivery or HX pinch/UA.

For every requested discharge interval:

1. The **initial outlet** (corrected cell), time-mean outlet and final outlet must individually reach 423.15 K. This is a sampled criterion, **not** a continuous guarantee between samples.
2. Qualified sensible-gas heat must meet at least `max(1 MW, mass_flow * cp * (423.15−383.15)) * interval_seconds` (about **1.005 MW** as a gas proxy with these inputs).
3. Signed gas heating is never clipped positive for an infeasible process return. An interval below grade is **zero qualified service**, even when the gas gains lower-grade enthalpy.

## Repeated state advancement

For each candidate fixed schedule:

- Run `simulate_charge` with R718 source and condenser boundaries responsive to the **current bed** (no arbitrary hot restart); incomplete HP charging blocks that candidate.
- Pass that charge's exact full fluid+solid bed state to reverse discharge.
- Use the **actual post-discharge fluid+solid field** as the next cycle's initial condition. Do not replace it by a uniform state, a target SOC, or a fabricated charge temperature.
- Independently audit full-cycle storage first law: `ΔU_bed + Q_wall_charge + Q_wall_discharge + Q_to_process_gas - Q_from_charge_gas = 0`, with the actual charge-gas/TES transfer and signed discharge heat.
- Demand **two consecutive** closed start/end full-field temperature cycles within the declared 0.25 K maximum absolute cellwise difference. Equality of bulk energy alone cannot satisfy this.
- Require the full sampled temperature and power grade in both of those same final cycles. A single grade-passing interval or an unconverged one-time discharge is not matched thermal service.

The bounded illustrative scan uses **2, 4, 8, 16 and 32** HP charging steps (120 s each), **2** discharge steps (60 s each), and **3 successive** no-reset cycles. This tiny schedule grid proves neither global feasibility nor global impossibility. It is deliberately not an unconstrained optimizer, and it holds the proposed compressor envelope assumptions unchanged.

## M3.3 — breakthrough and charging-envelope diagnosis

The extended charge-horizon sweep reports the physical discharge-outlet fluid temperature at the beginning of reverse flow, `T_fluid(x=0, charge end)`. **For an immediately qualifying full gas-delivery interval, this temperature must be at least 423.15 K (150°C)**, because it is the very first outlet sample. The positive deficit `max(0, 423.15 K − T_fluid(x=0))` is a model-diagnostic **necessary-condition shortfall**, not a material property fit, universal theoretical impossibility, or proven manufacturer compressor operating limit.

For each completed cycle, the artifact additionally provides the maximum rock temperature, final charging hot-gas supply, condenser saturation temperature, maximum nominal R718 stage ratio, and full-field start/end drift. Distinguish **failure to charge the physical hot end**, **failure to sustain outlet grade and 1 MW duty during discharge**, **cycle-state nonclosure**, and **any R718/HX charging termination**. Do not increase the stage pressure-ratio guard to force a positive result; its 5:1 value is already a nominal screening assumption, not a verified compressor map.

Longer charging may pass a single-temperature necessary condition yet fail the full duty or cyclic match. Even a model-only numerical match would not resolve the original process-liquid HX and physical equipment-qualification gates.

## Scientific release gates remain blocked

A result can at most be `MODEL_ONLY_SAMPLED_GAS_THERMAL_MATCH_NO_HARDWARE_QUALIFICATION`. No round-trip efficiency, matched architecture ranking, industrial heat-price advantage or hardware qualification is generated. The missing evidence remains independently measured compressor operating envelope for actual 80→70°C source, thermocline sensor calibration and time histories, pressure/mass-flow measurements, material and wall properties, process-liquid HX design and uncertainty. The gas bed is not the planned full dual-media thermocline.

## Reproduction and CI

```bash
python -m pip install -e ".[physics,test]"
python -m pytest tests/test_m3_outlet_initial_sample_regression.py tests/test_m3_matched_thermal_service.py -v
python scripts/run_m3_matched_thermal_scan.py
python scripts/run_m3_r718_sequential_service.py
```

The `m3-matched-r718-gas-service-cycle-screen` workflow tests both new regressions plus the original sequential and reverse-flow modules. It uploads the complete screen, per-cycle temperature fields, signed energy/power ledgers, explicit failures, and hashed input assumptions. Do not report process delivery as validated from a passing synthetic unit test or a real-fluid `CoolProp` execution alone.
