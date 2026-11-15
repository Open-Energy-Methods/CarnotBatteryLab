# CarnotBatteryArchBench

> **Scientific audit notice (2026-11-15):** The historical headline A/B/C
> rankings below are **not physically validated and should not be cited as a
> defensible cost–exergy comparison**. Auditing found an infeasible nitrate/chloride
> salt temperature-cost pairing, incorrectly defined dual-media literature,
> non-equivalent exergy/electricity denominators, and non-periodic bed cycles.
> The source report for $60/kWh_th concerns Gen3 chloride-salt storage at
> approximately 500–720°C, not Gen2 nitrate salt at 30–145°C.
> **Read [Scientific audit](docs/SCIENTIFIC_AUDIT_2026-11-15.md) first.**
> Run `python src/audit_metrics.py` to see independently recalculated packed-bed
> stream exergy and electrical-input diagnostics; there is no defensible C
> comparison or Pareto frontier yet.


A steady-state, single-cycle screening comparison of three thermal
energy storage (TES) architectures for a high-temperature-heat-pump
"Carnot battery" -- built to genuinely investigate, not just
illustrate, the trade-off between storage cost and exergy quality that
hybrid HP+TES architecture selection actually involves.

**Status: locally verified research-screening study; not field
validated, independently peer reviewed, or published to Zenodo.**

## What this answers

For the *same* high-temperature heat pump charging the *same* nominal
thermal duty, how do these three storage architectures compare?

- **A: Single-media packed bed** (basalt/rock gravel)
- **B: Dual-media packed bed** (rock + a finer second filler)
- **C: Two-tank molten salt** (isothermal tanks)

on: round-trip energy efficiency, round-trip **exergy** efficiency
(the metric that actually captures how much of the heat pump's
electrical work survives storage as *usable, high-temperature* heat,
not just how many kWh survive), electricity consumed per unit of
usable exergy delivered, and a storage system cost proxy.

## Historical legacy output — RETRACTED as a design conclusion (`python src/compare.py`)

```
Shared HP cycle: R1233zd(E), T_evap=70C, T_cond=150C, eta_is=0.70, COP_heating=2.123

Architecture                             eta_E  eta_Ex  elec/exergy   $/kWh_th
A: Single-media packed bed (rock)       0.8868  0.7708       0.6110      31.68
B: Dual-media packed bed                0.9141  0.8249       0.5709      36.43
C: Two-tank molten salt                 0.9583  0.9325       0.5051      60.00
```

**Legacy claim is withdrawn pending physical feasibility and cost-model reconciliation.** A is the cheapest storage
but destroys the most exergy through thermocline temperature glide; C
is nearly exergy-ideal but costs almost twice as much per kWh of
thermal capacity. This is the real trade-off a "cost-effective,
high-performance hybrid configuration" design question has to resolve
-- not something assumed going in.

## Methodology

### Heat pump (`src/hp_cycle.py`)

Single-stage vapour-compression cycle, R1233zd(E) via CoolProp 8.0.0
(same refrigerant already independently verified for real-fluid HTHP
cycle screening in the sibling HTHP-ControlBench project's WP7).
T_evap=70 C, T_cond=150 C, isentropic efficiency 0.70 -- an
**illustrative** operating point, not fit to a specific real plant.
COP_heating = 2.123, exactly first-law-closed (`q_cond = w_comp +
q_evap` to machine precision, checked in `tests/test_hp_cycle.py`).

### Packed-bed thermocline (A, B) (`src/tes_architectures.py`)

Modelled as an M-segment regenerator (the standard way to discretise
the Schumann packed-bed energy equation) **integrated in continuous
time with `scipy.integrate.solve_ivp`** (RK45, `rtol=1e-8`). M is the
only discretisation parameter and its convergence is checked directly
(`tests/test_tes_architectures.py::test_discretisation_converged_in_segment_count`).
The physically meaningful parameter is NTU_total = UA_total /
(mdot*cp_fluid): higher NTU -> sharper thermal front -> less exergy
destroyed by mixing during charge/discharge.

- **A (single coarse rock filler): NTU_total = 15** (assumed,
  illustrative)
- **B (dual-media, finer 2nd stage): NTU_total = 25** (assumed,
  illustrative)

B's higher NTU represents the *qualitative, literature-documented*
effect of a finer second filler reducing flow disturbance and mixing
in dual-media thermocline tanks (Mira-Hernandez, Flueckiger &
Garimella, *J. Solar Energy Engineering*, 2015) -- that paper reports
no specific NTU or percentage figure applicable here, so none is
invented; B's exact NTU value is a modelling assumption, not an
empirical fit, and is labelled as such everywhere it is used.

### Two-tank molten salt (C)

Isothermal tanks by design: only a fixed 5 K charging approach
temperature is modelled as a loss. Ambient tank heat loss is **not**
modelled -- a known omission, flagged rather than smoothed over, and
one that can only help C's two competitors look relatively better if
later added (not worse).

### Cost proxies ($/kWh_th, system-level CAPEX, not raw material cost)

- **A: $31.68/kWh_th** -- rock/basalt packed bed, 4-hour discharge
  duration. Allen et al., rock-bed TES cost study, via OSTI/NREL
  (<https://www.osti.gov/servlets/purl/1783087>), Table 2, Case 1.
- **B: $36.43/kWh_th** = A x 1.15. **Assumed** +15% for the second
  filler material and more complex packing -- not independently
  sourced, flagged as an assumption.
- **C: $60/kWh_th** -- two-tank molten salt (Gen2 nitrate-salt
  design), system-level CAPEX including tanks and refractory. NREL,
  SolarPACES 2020 proceedings
  (<https://nrel.gov/docs/fy22osti/77852.pdf>).

Known asymmetry, stated rather than hidden: A's figure is specific to
a 4-hour discharge duration (packed-bed $/kWh drops sharply at longer
durations, per the same source); C's figure is not duration-specific
in the same way (molten-salt tank cost scales roughly linearly with
capacity). The comparison is therefore most directly valid at the
~4-hour discharge duration used throughout this study, not as a
duration-independent generalisation.

## A real bug, found and fixed before shipping

An earlier version of the packed-bed model hand-rolled an explicit
Euler time-stepping loop that coupled the timestep count to the
segment count M in a way that silently double- or under-counted
flow-through energy. Refining the timestep alone (holding M fixed)
changed the computed efficiency by **40x** -- a clear sign of a real
bug, not a subtlety. Fixed by replacing the hand-rolled loop with
`scipy.integrate.solve_ivp`, which removes the coupling entirely: M is
now the only discretisation parameter, and its convergence is checked
directly rather than assumed. Documented in the module docstring and
in this project's memory record so the same mistake isn't repeated.

## Explicit limitations (not exhaustive, but not omitted either)

- **Steady/quasi-steady, single-cycle, not transient or multi-cycle.**
  Does not model degradation over repeated cycling, start-up
  transients, or part-load HP operation. HTHP-ControlBench already
  covers full transient HP dynamics and control; this project
  deliberately does not duplicate that.
- **NTU_total for A and B are assumed, illustrative values**, not
  fitted to any specific real bed geometry or measured data.
- **B's cost premium (+15%) is assumed**, not independently sourced.
- **C's model omits ambient tank heat loss.**
- **Cost figures are system-level CAPEX from different studies with
  different scope and vintage**, not a bottom-up, apples-to-apples
  bill of materials. They are sourced and cited, not fabricated, but
  they are not a unified cost model.
- No pumping power, piping losses, or balance-of-plant costs are
  included for any architecture.
- No GitHub Release or Zenodo DOI exists for this repository.

## Reproducing

```
pip install coolprop numpy scipy pytest
python -m pytest tests/ -v   # 14 tests
python src/compare.py        # headline comparison table
```

## Relationship to sibling projects

- **HTHP-ControlBench**: full transient dynamic modelling and
  PID/MPC/SOC control of a high-temperature heat pump. This project
  does not repeat that; it answers a different question (storage
  architecture choice) at a different fidelity (steady-state
  screening).
- **TES Discharge Screen**: validates a *single* storage architecture's
  discharge behaviour against a compiled FMU. This project compares
  *three* architectures against each other, using its own from-scratch
  regenerator model rather than the FMU (which needs Windows + a
  compiled binary and would not run in this project's CI).
- **sCO2-BraytonBench**: a different high-temperature thermodynamic
  cycle (sCO2 Brayton), not a heat pump, and not storage-coupled.
