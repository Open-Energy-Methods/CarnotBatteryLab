# M1.4 — Model-derived compressor operating requirements and independently supported limits

**Research status: NOT hardware qualified.** This module does **not** establish a manufacturer-certified heat-pump operating envelope; it turns existing source-correct real-fluid cycle hypotheses into explicit compressor performance requirements and rejects attempts to infer a vendor map from unrelated experiments or simulated COP optima.

## Exact H-REF service and conservation boundaries

The process-service contract is **80→70°C liquid waste heat**, **110→150°C liquid process heating**, **1 MW gross process heat**. The specific **source outlet 70°C**, assumed source flow cap **25 kg/s**, specific heat **4180 J/(kg K)**, 5 K pinch and both real-fluid compressor efficiencies remain **research assumptions**, not verified site measurements. The waste-heat stream's assumed maximum available thermal rate is `25 × 4180 × 10 = 1.045 MW`. This is not the required compressor source heat: the actual source heat is **calculated from first law**, with external intercooler rejection accounted for in R718.

The 1 MW liquid process stream at 110→150°C requires `1e6/(4180 × 40) ≈ 5.981 kg/s` under constant-cp assumptions. Neither flow is a plant measurement. This is a **direct process-temperature criterion** for M1: the M3 reverse packed-bed gas proxy and its sampled outlet temperature do not prove a liquid process HX delivers this contract.

For the assumed evaporator 5 K pinch, refrigerant evaporation at the 70°C waste-source outlet is **65°C**, *not* 80–85°C. Thus publications reporting R718 **85°C refrigerant evaporation** are physically ineligible as an exact positive-pinch machine for the original 80°C **liquid inlet**, even if a paper also reports 150°C refrigerant condensation.

## Explicit compressor-side demanded coordinates

For each numerically feasible CoolProp/finite-HX screen (R718 two-stage and R600 single-stage transcritical), M1.4 calculates:

- Suction **absolute pressure** and **temperature** at each stage, and independent outlet P/T.
- Stage pressure ratio `p_discharge/p_suction`; stage shaft duty `m_dot × (h_out-h_in)`; sum of R718 shaft stages cross-checked against the original energy ledger.
- Real-fluid suction density `rho(P_suction,T_suction)`; volume requirement `V_dot,suction = m_dot/rho_suction` (actual suction m³/s, **not standardized/normal-volume flow**).
- Refrigerant mass flow, process-liquid flow and source cooling requirement. The source heat cap is an **assumed scenario**; passing it never establishes actual flow availability.
- A **TES-feedback charge demand trajectory** for 2, 16 and 32 × 120s commanded charging schedules from a common 95°C gas/rock initial state. For every numerically completed step the gas return and supply are directly reused to recalculate the R718 compressor state and cross-check its original stored stage pressure ratios. Incomplete charging remains flagged with the actual termination reason.

These coordinates show **what a machine would need to do**. They are not a feasible compressor speed line, not a known flow stability zone and not an efficiency map. Compressor rotational speed, impeller/piston displacement, surge/choke, material/oil thermal limits and pressure losses remain undefined. Do **not** solve for rpm from an assumed volumetric efficiency and claim a machine exists. On the R600 branch, the model explicitly omits the experimental suction-gas-cooled compressor's IHX, so its reported COP is not comparable point-for-point to the experimental prototype.

## Independently sourced evidence: different plants, boundaries and model classes

| Evidence source | What is actually supported | What is **not** supported |
|---|---|---|
| Verdnik & Rieberer, *International Journal of Refrigeration* (2022), [DOI 10.1016/j.ijrefrig.2022.05.010](https://doi.org/10.1016/j.ijrefrig.2022.05.010) | Measured single-stage R600 prototype at a **60°C source inlet** producing **160°C** heat-sink outlet, **24.2 kW**, COP **3.1**; test rig includes IHX and suction-gas-cooled reciprocating compressor | Source outlet and sink return of this exact reported point not established here, no 80→70°C operation, no 1 MW compressor map |
| Benkert et al., *Chemie Ingenieur Technik*, first published **6 Nov 2025**, [DOI 10.1002/cite.70046](https://doi.org/10.1002/cite.70046) | R600 experimental bench reports **up to 120°C** heat output and up to **125 kW** capacity, with pressurized-water and steam-generation modes | These maxima are not necessarily simultaneous, do not meet the 150°C output service, no exact H-REF map |
| Pfeiffer et al., HPT TCP conference release **26 May 2026**, [publication](https://heatpumpingtechnologies.org/publications/transcritical-high-temperature-heat-pump-with-hydrocarbonmixtures-experimental-setup-and-model-predictions/) | 20 kW experimental prototype exists; **model prediction** of R290/R601a mixture for **90→60°C** source and **100→150°C** sink with improved glide match | The reported mixture performance is a **prediction**, not a measured verified 80→70°C map or 1 MW solution |
| Ramirez et al., *Applied Thermal Engineering* (2024), [DOI 10.1016/j.applthermaleng.2024.122961](https://doi.org/10.1016/j.applthermaleng.2024.122961) | **50 measured HFO R1233zd(E)** prototype points; highest cited near-150°C duty **38.6 kW** at **148.5°C**, **10.7 kW electrical**, COP **3.6**; model subsequently extends to simulated points | Not a natural fluid; not 1 MW; published near-target heat output cannot be substituted for complete measured boundary/qualified map |
| Zühlsdorf et al., IIR 2018 [DOI 10.18462/iir.gl.2018.1367](https://doi.org/10.18462/iir.gl.2018.1367) | R718 **nominal design**, low/high stage ratios **3.2/2.0**, 80,000 rpm nominal impellers | Published expected performance is **not** a full steam measured speed map at our H-REF suction |
| Verpe et al., IIR 2020 [DOI 10.18462/iir.gl.2020.1019](https://doi.org/10.18462/iir.gl.2020.1019) | Separate experimental R718 rig reports **maximum** low/high stage ratios **2.4/2.0** | Maxima need not be simultaneous; different equipment/topology. A stage-wise numerical comparison is a **negative screen**, never a global law or a concatenated measured map |
| Published R600 simulated 80→75°C source and 80→160°C sink, IIR 2019 [proceedings PDF](https://waermepumpe-izw.de/wp-content/uploads/2020/05/190800-ICR-1-3-E2_1186-Verdink-et-al.pdf) | COP **3.24 from simulation** with prototype-motivated assumed pressure control | Not a measured operating point at 80→70°C, 110→150°C |

Source gate intentionally lists **unknown** original source/sink boundary fields as `null`, does not fill them by interpolation, and rejects attempts to label an isolated experiment or a reported maximum a complete multi-dimensional compressor map. Even exact nominal temperatures and 1 MW in one test are insufficient to qualify a machine across TES-responsive charging states.

## Manufacturer data to close the gate

A candidate compressor package needs an **original manufacturer's or independently measured, uncertainty-bounded multi-point performance map**, tied to its actual architecture, with:

1. Working fluid, complete multi-stage/injection/IHX/intercooling topology, cooling utility and nominal units/trains.
2. Suction absolute pressure/temperature, discharge pressure/temperature, refrigerant mass flow, **actual suction volumetric flow**, speed lines, shaft/electrical input and efficiencies across relevant HP/TES states—not just a nominal point.
3. Surge/choke or other stable compressor operating area, pressure limits, lubrication/oil temperature, sealing, vibration/material limits, startup and part-load controls.
4. Source 80→70°C and sink 110→150°C **heat exchanger installed UA and minimum internal approach**, with real source/process flow limits, pressure losses, and no uncounted intercooler heat credit.
5. Evidence of how the entire **1 MW** duty is supported by qualified machine(s) and how transient TES return temperatures remain inside the measured safe operating range.
6. Raw experimental P/T/flow/electricity measurement uncertainty, calibration, independent holdouts and rights to use cited maps.

For R600 (safety group A3), an equipment selection also requires a separate safety/pressure-vessel and refrigerant-charge assessment. No screen result endorses an A3 installation.

**Release gate:** M1.4 can deliver a defensible, reproducible manufacturer inquiry/data-acquisition dossier. It **cannot** set `equipment_qualified=True`, fit missing efficiency maps to a single COP, increase R718's **hypothetical** 5:1 ratio or 350°C discharge guard to force a positive M3 cycle, or rate architecture COP/round-trip efficiency at exact source until the missing independent data exist.

## Reproduce and provenance

```bash
python -m pip install -e ".[physics,test]"
python -m pytest tests/test_m1_compressor_envelope_requirements.py -v
python scripts/run_m1_compressor_map_requirements.py --output results/m1_compressor_map_requirements_80_70_to_110_150.json
```

The GitHub Actions workflow `m1-compressor-operating-requirements.yml` publishes an input-hashed JSON including original cycle assumptions, per-stage demands, TES-dynamic requirements, separate published compressor-ratio comparator classes, evidence-classed literature records and explicit non-qualification fields. Source citations are external URLs and DOIs; no copyrighted PDFs or proprietary vendor maps are redistributed.
