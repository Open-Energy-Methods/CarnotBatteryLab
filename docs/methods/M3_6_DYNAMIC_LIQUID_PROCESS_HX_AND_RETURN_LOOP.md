# M3.6 — dynamic gas/metal/process-water exchanger and return-gas-loop audit

**Research evidence class:** numerical **model-only** time-marched heat-exchanger feasibility and three-inventory first-law verification. **Not** calibrated heat-pump/compressor machinery, original 80→70°C waste-source coupling, independent packed-bed validation, installed process-water heat exchanger, gas cooler, continuous guarantee or whole-system RTE. This milestone implements [Issue #45](https://github.com/Open-Energy-Methods/CarnotBatteryLab/issues/45) independently of compressor-manufacturer responses.

## 1. Source and declared original functional unit

The only fixed external process contract remains **1 MW gross heat**, separate **110→150°C liquid process stream**, for **60 minutes after any explicitly charged startup**. M3.6 does not use the original 80→70°C waste-heat inlet as a fictional thermal source. Charge is an **assumed 220°C gas stream at 25 kg/s for two hours**, supported by an **idealized uninstalled electrical-resistance heater** with an assumed 4.5 MW initial-power ceiling. The existing conservative finite-volume gas/rock bed is first charged from **uniform 95°C** and then discharged in reverse flow with **15 kg/s** gas, held at **110°C gas-bed return** by an external, **uninstalled** thermal gas-conditioning stage.

M3.5 supplied **only three independently sampled hot-gas outlet temperatures per coarse discharge interval** and a static 1 MW counterflow temperature/enthalpy necessity check. M3.6 resolves a **time-dependent hot-gas inlet sequence at 60 s nominal intervals**, a **finite-volume gas stream**, an **oppositely flowing water stream**, and a **finite thermal-mass metal wall**. *Each 60 s gas inlet is the exact bed-step energy-equivalent mean*, not a reconstructed, independently measured or bounded instantaneous temperature history. The bed gas uses the same M3.5 **constant cp=1005 J/(kg K), density=2.5 kg/m³** hypothesis; these are NOT temperature- or pressure-resolved verified air properties.

## 2. Original liquid-process mass flow uses water enthalpy, not nominal cp

The older M3.4 static screen approximated mass flow from constant `c_p=4180 J kg⁻¹ K⁻¹` as **5.9809 kg/s**. That is acceptable as an explicitly nominal preliminary screen but conflicts with using original **temperature-dependent water enthalpy** in the dynamic HX. M3.6 therefore uses **CoolProp's HEOS::Water**:

```text
h_in  = h_water(T=110°C, P=2.000 MPa absolute ASSUMED)
h_out = h_water(T=150°C, P=2.000 MPa absolute ASSUMED)

m_water = 1,000,000 W / (h_out - h_in)
```

No measured process water pressure is available; the **2.0 MPa absolute is a numerical hypothesis**. The liquid temperature-dependent `h(T,P)`, `cp(T,P)`, reference density and saturation boundary are derived from direct CoolProp calls. A **0.5 K grid** interpolates original EOS enthalpy and cp inside the **single-phase interval only**, without clipping/extrapolation; multiple off-grid points are independently rechecked against direct EOS values in automated tests.

Cooling flow/differential-pressure formulas and water saturation limits use the **assumed** local pressure, not a manufacturer curve. The actual process water pressure must independently exceed the pressure needed to keep the **hottest modeled water state** single-phase with a declared **2 K saturation margin**, including the modeled liquid pressure loss. A separately assumed **0.4 MPa absolute** process-water test fails closed before any 150°C-liquid result can be credited. No assertion of an actual 2 MPa installed water circuit is made.

Sources:
- [Bell, Wronski, Quoilin & Lemort (2014), CoolProp open-source property library, DOI 10.1021/ie4033999](https://doi.org/10.1021/ie4033999)
- [CoolProp high-level `PropsSI`, T/P and saturated T/Q or P/Q documentation](https://coolprop.org/coolprop/HighLevelAPI.html)

## 3. Dynamic counterflow three-inventory finite-volume equations

The HX has **N=8 axial cells** nominal (N=4,8,12,16 tested), with gas flowing **i=0→N−1** and process water flowing **i=N−1→0**. The thermal-wall node is located between the two fluids. Initial gas, water and wall are each **110°C**. The declared uncalibrated equipment quantities are:

| Input | Assumed | Origin/qualification |
|---|---:|---|
| Overall HX installed UA | **40,000 W/K** | Hypothetical value, not a datasheet |
| Low-UA counterexample | **10,000 W/K** | Hypothetical deliberately undersized |
| Metal-wall lumped heat capacity | **1,000,000 J/K** (also 500,000 J/K sensitivity) | Hypothetical |
| Gas holdup | **24 kg** | Hypothetical |
| Liquid holdup | **200 kg** | Hypothetical |
| Assumed liquid inlet absolute pressure | **2.0 MPa** | Hypothetical, no actual measured loop |
| Gas/liquid hydraulic geometry | 1.2/0.025 m² open flow area; 0.05/0.03 m hydraulic diameter; each 12 m length | Hypothetical, no engineering drawing |
| Darcy friction factors | 0.03 gas / 0.025 liquid | Hypothetical, no Reynolds-dependent friction solution |
| Lumped minor-loss coefficients | 2.0 gas / 2.0 liquid | Hypothetical |
| Auxiliary hydraulic efficiency | 70% | Hypothetical |

A **gas-wall thermal conductance** and **wall-water thermal conductance** of `2 UA/N` per cell are used so two contact resistances in series give the declared overall UA in the static limit. Axial advection is first-order upwind; there is no axial wall conduction or exchanger thermal radiation, real heat-transfer surface geometry, fouling, variable shell-pass arrangement or manufacturer rating.

Each cell's state is advanced with stiff SciPy BDF integration. Water energy is driven by **actual enthalpy differences** rather than constant `cpΔT`, and the water temperature derivative uses `cp(T,P)`. The gas and wall hold-ups each have separate capacities:

```text
dU_g,i/dt = m_g cp_g (T_g,up - T_g,i) - UA_g,i (T_g,i - T_wall,i)

dU_l,i/dt = m_l [h(T_l,up,P) - h(T_l,i,P)]
            + UA_l,i (T_wall,i - T_l,i)

dU_wall,i/dt = UA_g,i (T_g,i - T_wall,i)
               - UA_l,i (T_wall,i - T_l,i)
```

The process-water grade gate checks **the minimum liquid outlet temperature across every accepted BDF solver node within each integration interval**, in addition to the requested 1 MW interval-average water enthalpy flow and the minimum gas–liquid approach at all accepted nodes. This is stronger than checking only first and last temperatures, but accepted solver nodes still cannot certify a **mathematically continuous minimum between nodes**. Heat delivery is still unqualified without real inlet histories, water pressure and installed process control.

The code integrates four independent heat ledgers for **gas boundary heat**, **liquid outlet enthalpy rise**, **gas-to-wall** and **wall-to-liquid**. They produce three independently checked inventories and a whole-HX first-law residual:

```text
ΔU_gas    = Q_gas,boundary - Q_gas→wall
ΔH_liquid = Q_wall→liquid - Q_liquid,process
ΔU_wall   = Q_gas→wall - Q_wall→liquid

ΔU_gas + ΔH_liquid + ΔU_wall
         = Q_gas,boundary - Q_liquid,process
```

These are numerical **enthalpy-inventory** approximations with assumed constant holdup masses and water pressure; their residual is not real instrumentation/calibration uncertainty.

## 4. Closed gas-return boundary and overall storage energy ledger

At each step, the bed emits a signed integrated thermal gas gain and a corresponding energy-equivalent mean hot-gas temperature. The HX model computes an independently integrated gas boundary energy gain/loss. A separate **signed thermal gas conditioner** is derived to reconcile the HX gas outlet's **time-integrated temperature** with the imposed **110°C return**:

```text
Q_bed→gas = Q_gas→HX + Q_gas,return-conditioner

Q_gas,return-conditioner > 0: additional cooler thermal duty required
Q_gas,return-conditioner < 0: additional reheater thermal duty required

ΔU_bed + ΔU_HX,gas + ΔH_HX,liquid + ΔU_HX,wall
     + Q_bed,ambient + Q_liquid,process
     + Q_return-cooler - Q_return-reheater = 0
```

This uses the **signed** conditioner term; a cooler thermal load is never called electrical energy. A real cooler would need an outlet sink temperature, actual heat-exchange area/UA, additional circulation work, controls, installation and cooling source. **None is included**. The HX gas and liquid friction losses are simple **assumed geometry/friction** Darcy-Weisbach calculations, not demonstrated piping and pump/fan curves, so their nominal electric demand is not qualified either.

## 5. Reproducible 1 MW process-water operating scenarios

The existing M3.5 source-independent 220°C/2h bed charging case was replayed, with the **process water flowing from 110°C**, always using original 1MW required **CoolProp enthalpy-derived mass flow**, and a **60 s bed/HX step**, nominal **N_bed=16, N_HX=8**:

| Model scenario | Duty pass for **all** 60 requested process minutes? | First process interval water outlet at step end | Final process outlet |
|---|---|---:|---:|
| 40 kW/K assumed UA, **cold start** (no warmup) | **No**: fails first interval because outlet initially 110°C and metal/water inventory is cold | ~150.84°C at 60 s; **start remains 110°C** | ~155.44°C |
| 40 kW/K assumed UA, **10 min separately accounted warmup** | **Yes: sampled numerical threshold, model only** | ~160.46°C | ~152.40°C |
| 10 kW/K UA, 10 min warmup | **No** | ~137.40°C | ~133.05°C |
| 40 kW/K UA, **half the assumed wall capacity**, 10 min warmup | **Yes: sampled numerical threshold, model only** | ~160.46°C | ~152.35°C |
| 40 kW/K UA, 10 min warmup but **0.4 MPa assumed water** | **Blocked**: 150°C liquid-phase requirement not satisfied | — | — |

**Crucial:** 160.46°C is **above the exact 150°C requested delivery temperature**. The model checks "at least 150°C and at least 1 MW" as a **necessary temperature/enthalpy capability condition**, not a certified exactly-150°C process control solution. A real exchanger would require bypass/trim valves, modulated UA/flow, other balancing and process temperature control. This is **not** presently installed or simulated.

The passing 10 min warmup + 60 min process case reports **5.056 GJ gas-to-water heat across all 70 minutes**, including water warmed during startup that **cannot** be credited to the one-hour process contract. The 110°C bed-return loop also requires **~1.546 GJ of additional gas cooler thermal duty over the same 70 minutes**, or ~0.368 MW average, which is **not an installed or electrically characterized cooler**. The assumed HX gas+water pumping/circulating demand is about **2.88 kWh** over the period; this excludes the separate Ergun bed blower, electric charge heater and real heat-transfer equipment. The complete bed + gas HX + water + metal + conditioner discharge first-law residual is **well below 2 J**, compared with GJ-scale real-fluid modelled flows. Thus energy accounting closes **numerically**, without validating the physical parameters.

## 6. Numerical spatial/temporal sensitivity — do not overinterpret near-threshold duty

The passing-warmup scenario was rerun on a separate HX grid while holding the **bed at N=16**:

| HX cells | Coupled bed/HX time step | Last simulated liquid outlet | 60 min sampled service |
|---:|---:|---:|---|
| 4 | 120 s | **149.67°C** | **Fails**; 58/60 min prefix |
| 8 | 120 s | **152.51°C** | Passes |
| 12 | 120 s | **153.54°C** | Passes |
| 16 | 120 s | **154.07°C** | Passes |
| 8 | 60 s | **152.40°C** | Passes |
| 12 | 60 s | **153.42°C** | Passes |

M3.6 N_HX=8→12 differs by **1.03 K** at 120 s; 12→16 differs by **0.53 K**. Halving the coupling step from 120→60 s shifts the final outlet by **~0.12 K** at N=8 or N=12. Independently refining the **bed spatial grid N=16→32**, keeping HX N=8 and step 120s, changes the final water outlet by **~1.90 K**; this difference is material relative to the **150°C** threshold. Therefore **numerical independence is not established**, even where the sampled model pass remains unchanged.

The hot-gas inlet passed to each HX time step is the **bed-step energy-equivalent mean**, and cannot exclude inter-step temperature dips or step-internal process-duty failures. The model has no independent physical measurement uncertainty, true continuous-gas sampling, measured heat-transfer coefficients or manufacturer HX geometry. A numerical "pass" must **not** be described as validated one-hour 1MW delivered heat.

## 7. Negative tests and proof boundaries

The M3.6 tests and dedicated CI include: original 110→150°C exact 1MW enthalpy flow vs the old cp approximation; independent gas/liquid/metal/total heat ledgers; cold-start supply failure; wall warmup debited against actual TES discharge; lower UA deficiency; water pressure below saturation phase rejection; mismatched axial discretizations; positive Darcy-flow loss but **unmeasured** fan/pump ratings; time-step sensitivity; gas conditioner sign and total-bed energy first law; explicit refusal to alter the original functional unit, invent compressor maps, infer actual installation or report Carnot electrical RTE.

**Unfinished necessary science:** calibrated 2T bed against measured axial/radial histories, temperature-dependent gas EOS and density with known real gas pressure, proper pressure-rated water HX and gas-side containment, validated heat transfer and fouling characteristics, *continuous real inlet gas and water temperature histories*, an explicitly installed and powered gas conditioner/cooler, dynamic process control at exactly 150°C, liquid pressure/flow sensor calibration, repeatable cyclic terminal state and original 80°C waste-source hardware compressor feasibility. Separately, native manufacturers' R600/R718 measured maps remain open.

## Reproduce independently

```bash
python -m pip install -e ".[physics,test]"
python -m pytest tests/test_m3_6_transient_liquid_hx.py \
  tests/test_m3_4_liquid_process_hx_gate.py -v

python scripts/run_m3_6_dynamic_liquid_process_service.py \
  --output results/m3_6_dynamic_110_150C_water_HX_study.json
```

Code: `src/carnot_battery_lab/physics/transient_liquid_hx.py` (strict 3-phase dynamic FV HX, original water property interpolants and direct EOS tests); `src/carnot_battery_lab/physics/coupled_transient_process_loop.py` (complete conditional source heater→packed bed→water HX→separately conditioned return gas flow with total first-law ledger); `scripts/run_m3_6_dynamic_liquid_process_service.py` (reproducible trial/mesh/time sensitivity); `tests/test_m3_6_transient_liquid_hx.py` (adversarial actual EOS and synthetic model only). Dedicated GitHub workflow preserves the model report artifact and **hard-asserts every "qualified real process" flag remains false**.
