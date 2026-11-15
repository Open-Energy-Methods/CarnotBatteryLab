# Scientific contract — 2026-11-15

**Contract status:** approved for engineering planning; research design targets,
not executed numerical results. Any technical alteration requires a documented
architecture decision and test updates.

## Mission

Develop an independently auditable simulator and comparative research framework
for industrial high-temperature heat pump + TES hybrid configurations. The
platform must answer under what source, sink, service, price and cost conditions
each viable layout is technically, thermodynamically and economically attractive;
quantify uncertainty; and state what cannot yet be established.

## Questions (not predetermined answers)

- Q1: How do natural-fluid cycle selection and heat exchanger temperature glide
  shift attainable storage charge temperature and useful service quality?
- Q2: For equal *qualified thermal service*, when do rock beds, HTF/filler
  thermoclines and molten-salt tanks form a defensible Pareto frontier?
- Q3: How do particle/bed geometry, transfer coefficients and pressure losses
  create the heat-transfer / pumping-power trade-off?
- Q4: Under what combinations of prices, source variability, heat demand and
  start-up constraints does TES actually justify higher CAPEX?
- Q5: Which architectural choices remain robust under uncertain material,
  compressor, price, lifetime and thermal-loss assumptions?
- Q6: How does the answer change if electricity output is explicitly recovered
  through a power cycle instead of consuming stored heat as process heat?

## Research invariants

1. **Service parity**: compare systems at fixed target supply temperature,
   allowed return temperature, required heat schedule, availability and annual
   useful energy. Document all shortfall and unserved thermal energy.
2. **Thermophysical validity**: no property extrapolation outside the fluid
   backend validity region; explicit melting/freezing, material and pressure
   limits; salt tank temperatures obey an evidenced safety margin.
3. **Exergy reference**: common reference environment and explicit flow
   definition including reference pressure/composition where material.
4. **Common accounting**: electrical auxiliaries, heater/booster, hold losses,
   process HX losses, charge/discharge flow work and control standby included.
5. **True state coupling**: HP output temperature, compressor/HTF operation and
   storage temperature influence each other through physical exchangers.
6. **Dynamic closure**: simulation must conserve energy and mass in charging,
   standby, discharging and repeated cycles; cyclic residuals quantified.
7. **Optimization validity**: samples/candidates failing constraints are
   infeasible; no reward through extrapolation or solver non-convergence.
8. **Reproducibility**: record version, code hash, input checksum, property
   backend, source records, solver version/limits and random seed.
9. **Uncertainty**: separate epistemic parameters from numerical error;
   report confidence/sensitivity and model structural limitations.
10. **No circular validation**: fitting and holdout benchmark datasets stay
    distinct. A model passing its own conservation tests is not experimentally
    validated.

## Service families

### H: useful industrial heat

Initial design service contract (`cases/reference_industrial_heat_150C.yaml`):
illustrative 1 MW_th qualified process load, 150 °C process supply, 110 °C
return, 80 °C waste heat inlet, 20 °C dead-state ambient, 6 h useful storage,
15 min dispatch increment. All values are **research inputs**, not claimed to
match a real site or to establish a feasible compressor arrangement.

Reference H0: direct HTHP heat supply with no TES. This is an essential
comparison: if TES does not beat the direct case under the same heat service,
the storage architecture need not be recommended.

### H+: high-temperature extension

The 250 °C process service is a **challenging study envelope**, not an
assumed viable single-stage R601 heat pump. If a heat-pump source cannot
provide the desired salt/hot process temperature, the topology must use a
thermodynamically specified upgrade/booster or be marked infeasible. Associated
parasitic work and capital must be counted. Molten nitrate-salt operating
windows must be evidenced and cannot inherit 150 °C baseline costs.

### E: electricity returned

Not eligible for an E-family comparison until both charging and **heat-engine
power-cycle models** and electrical input/output meters exist. Electrical
round-trip efficiency cannot be reported for a heat-only output topology.

## Architecture definitions

- H0 Direct HTHP-to-process baseline, no TES.
- H1 HTHP / intermediate HTF / air-rock (solid-filler) packed-bed sensible TES;
  explicitly separate refrigerant and storage heat-transfer-fluid circuits.
- H2 HTHP / heat-transfer fluid plus solid-filler **dual-media thermocline**;
  HTF/solid definitions and usable temperatures must be specified. Avoid using
  "two sizes of rocks" as the definition of dual-media.
- H3 Two-tank molten-salt TES operating within real liquid-temperature range;
  only include if a feasible higher-temperature heat source/upgrade is part
  of the same system boundary.
- H4 Optional PCM/steam/process-heat cascade if justified by validation data;
  not a forced additional point on a price-efficiency chart.
- E1 HTHP + TES + modelled heat engine (true electrical Carnot battery);
  separate service family and comparison objective.

## Required results

For each **feasible** architecture: transient process supply/return T and
flow; HP state points and COP trends; charge/standby/discharge SOC and bed/tank
temperatures; energy/exergy destruction by component; compressor and auxiliary
work; qualified heat, supply shortfall and downtime; CAPEX with provenance;
LCOH and discounted cash flows; dynamic price response; uncertainty intervals;
Pareto nondominance and constraint verification.

Do not compare infeasible candidates by setting their performance to zero or
assigning arbitrary penalty values in published plots. Present them in an
explicit infeasibility table with cause and boundary conditions.
