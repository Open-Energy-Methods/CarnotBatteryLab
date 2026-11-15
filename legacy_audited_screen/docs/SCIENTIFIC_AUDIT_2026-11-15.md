# Scientific audit of CarnotBatteryArchBench (2026-11-15)

**Status: corrective methods audit, not a scientific v1.0 or published benchmark.**
The original implementation and its 14 tests are preserved for reproducibility. The
original `src/compare.py` headline figures are **RETRACTED AS ENGINEERING CLAIMS**;
they are historical outputs only. The new `src/audit_metrics.py` independently
recomputes flow exergy for the packed-bed histories and refuses to offer a
comparable two-tank-salt result under the specified conditions.

## What was actually tested

* Original thermal-storage tests: `python -m pytest tests/test_tes_architectures.py -q`: **6 passed**.
* Original full 14-test suite: **not executed** in this audit because CoolProp is
  absent and package installation is unavailable in the audit runtime. An earlier
  account reported 14/14, but this was not independently confirmed here.
* New corrective tests: run `python -m pytest tests/test_audit_metrics.py -q`.
* Analytical energy-accounting check: original packed-bed integration conserves
  heat as charged heat = recovered heat + remaining bed energy, to numerical precision.

## Critical issues, in order of impact

**P0-1. Infeasible two-tank conventional molten salt.**
The candidate 30°C cold tank / 145°C hot tank does not contain liquid solar salt
(NaNO3/KNO3). Conventional solar salt melts around 220°C, with 290°C cold and
565°C hot in the NREL reference Gen2 design. It is also not appropriate to reuse
a Gen3 chloride-salt storage CAPEX number for a 145°C hypothetical salt tank.
The NREL report explicitly specifies 500°C/720°C Gen3 chloride salt, four tanks,
and $60/kWh_th system cost. This was incorrectly represented as a Gen2 nitrate-
salt cost in the original README. Its technology, scale, and boundary conditions
do not match this model.

**P0-2. Incorrect dual-media architecture definition and literature inference.**
In the cited Mira-Hernández, Flueckiger & Garimella (2015) study, a dual-media
thermocline is molten salt plus a solid packed filler; a single-media thermocline
uses salt alone. Their paper does not establish that two grades of rock increase
NTU from 15 to 25 or exergy efficiency by a fixed amount, and indeed the abstract
reports slightly higher first- and second-law efficiency for the single-medium
salt-only thermocline under the investigated cases. The existing A and B models
are a **hypothetical lower/higher-NTU sensitivity test**, not demonstrated
single- vs dual-media architectural variants.

**P0-3. Heat/electrical/exergy dimension mismatch.**
The legacy `electricity_per_unit_exergy_delivered = (1/COP)/eta_exergy`
wrongly uses TES exergy efficiency as though it were `X_discharge/Q_charge`.
For electric input per delivered heat exergy, the consistent formula under
fixed HP COP and matched charging duty is

    W_electric / X_delivered = (Q_charge / COP) / X_discharge.

Legacy exergy heat uses `Q * (1-T0/T_out)` for an entire fluid stream whose
temperature changes along the HX. With constant cp and negligible pressure
changes, the correct flow-exergy change is

    X_stream/(mdot*cp) = (T_high - T_low) - T0*ln(T_high/T_low),  [K]

and must be integrated over time. The new `src/audit_metrics.py` implements
that calculation. This provides internally consistent **packed-bed-only**
diagnostics, subject to the boundary-condition assumptions and missing process
HX coupling.

| Legacy case | NTU | Thermal energy recovered / charged | Stream exergy recovered / charged | Corrected W_elec / X_delivered* |
|---|---:|---:|---:|---:|
| A, rock-bed sensitivity | 15 | 0.8868 | 0.7104 | 3.294 |
| B, higher-NTU sensitivity | 25 | 0.9141 | 0.7746 | 3.079 |

\* Fixed COP=2.123 carried forward from the original calculation, not
independently reverified in this environment. Both electricity ratios have
units kWh electric / kWh recovered exergy. They are not external validation.

**P0-4. Non-periodic, non-closed cycle.**
The original packed bed starts uniformly at 30°C, undergoes one charge then one
discharge, and ends warmer than it started. Recovered energy is 88.68% for A and
91.41% for B, but the missing 11.32%/8.59% of input remains *stored in the bed*
after discharge; it is not all thermal loss. To claim round-trip efficiency,
one needs a specified service temperature, consistent cutoffs and a periodic
steady-cycle state, plus stand-by thermal losses, parasitic pumping, etc.

**P0-5. No natural refrigerant.**
R1233zd(E) is a synthetic hydrochlorofluoroolefin (HCFO), even if low GWP.
The DTU posting explicitly asks for high-temperature heat-pump cycles using
**natural working fluids**. Consider water (R718), n-pentane (R601) or
isopentane (R601a), screened for pressure ratios, thermophysical validity,
flammability/compressor design and thermal process requirements. Do not simply
swap names while assuming the same COP.

**P1-6. Incomplete hybrid integration, objective and sizing parity.**
The HP always sees a fixed evaporating and condensing temperature, so storage
outlet temperature/flow/feedback does not alter the compressor point. This is
HP/TES post-processing, not a **thermodynamically coupled hybrid**. The bed NTU
is not derived from heat transfer coefficient, particle size, porosity and bed
geometry; pumping power and system size/cost are omitted. The three-case
comparison is not a multi-objective optimisation or a dynamic price-response
analysis. The project incorrectly says all candidates share equal nominal
thermal duty yet has no explicit duty, volume or matched useful heat delivery.

**P1-7. Cost provenance and uncertainty.**
The original $31.68/kWh_th rock-cost reference to OSTI 1783087 was not
independently retrieved by this audit and remains UNVERIFIED; do not cite it as
confirmed. The original +15% dual-media premium is explicitly hypothetical.
The original $60/kWh_th source *is* traceable but represents a significantly
different higher-temperature chloride-salt system. With incompatible boundaries,
the apparent cost–exergy Pareto frontier is unsupported.

## Defensible route to v1.0, ordered by scientific risk

1. **Define service**: fixed industrial load (MW_th, minimum delivery
   temperature, return temperature, 4-hour duty), waste-heat source,
   electricity tariff, charge/discharge schedule and pressure/flow boundaries.
2. **Select physically admissible layouts and media** for the chosen temperature
   range; separate air/rock regenerators, HTF+solid thermocline, and two-tank
   salt *only if* its liquid temperature range can be met. A different lower-
   melting medium requires its own evidence and CAPEX, not a relabeled Gen3 value.
3. **Implement natural-fluid HP** with tested refrigerant domain boundaries,
   pinch/UA, compressor maps or explicit isentropic-efficiency assumptions,
   and physical heat exchange that constrains the storage charge loop.
4. **Close energy and exergy balances** over all components, provide time-series
   profiles, end states, cyclic steady state, minimum useful discharge T and
   definitions of heat and exergy efficiency (no mismatched denominators).
5. **Derive NTU and parasitics from geometry**, compare heat-transfer and
   pressure-drop vs particle size; define thermal capacity on a common service
   basis, not only theoretical inventory.
6. **Run uncertainty/sensitivity first** for UA, cp, particle size, costs,
   compressor eta_is, pinch and source temperature; then add constrained
   multi-objective optimisation with reproducible Pareto filtering.
7. **Verify against literature/integration tests** including independent
   analytical limit, grid/time convergence, heat loss and conservation tests;
   use external experimental or FMU data when available, with strict disclosure.
8. **Only then add price-response transients**: price series, rate limits,
   thermal duty continuity, controller mode switches, states and storage SOC.

For the DTU 24 November application, the *required critical literature review*
(maximum three pages, up to five papers, original figure/table) and degree/
transcript/cover-letter evidence must not be displaced by premature pursuit of
v1.0. The appropriate current portfolio claim is **"preliminary hybrid screening
and self-audit with identified thermodynamic and feasibility limitations"**.

## References verified through accessible sources (15 Nov 2026)

- NREL, Augustine, Kesseli & Turchi (2021), *Technoeconomic Cost Analysis of NREL
  Concentrating Solar Power Gen3 Liquid Pathway*, NREL/CP-5500-77852:
  https://docs.nrel.gov/docs/fy22osti/77852.pdf
- NREL, *Solar Two central receiver tests*, conventional solar salt melting
  around 220°C: https://docs.nrel.gov/docs/fy00osti/27925.pdf
- Mira-Hernández, Flueckiger & Garimella (2015),
  DOI: https://doi.org/10.1115/1.4029453 ; repository abstract:
  https://docs.lib.purdue.edu/coolingpubs/249/
- DTU vacancy and mandatory review requirements (posted 27 Oct 2026):
  https://euraxess.ec.europa.eu/jobs/475735
- HTHP natural-working-fluid examples: Heat Pumping Technologies (May 2026):
  https://heatpumpingtechnologies.org/publications/analysis-of-natural-refrigerant-for-different-applications-in-heatpumps-above-100%E2%81%B0c/

**No claim is made that the referenced papers constitute the applicant's required
five-publication review; that is a separate, original critical-synthesis task.**
