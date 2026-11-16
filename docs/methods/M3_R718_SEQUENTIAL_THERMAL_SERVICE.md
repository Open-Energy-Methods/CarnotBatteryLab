# M3.1 — Sequential R718 coupled charging to reverse-flow process-gas discharge

**Status:** executable but equipment-**UNQUALIFIED** thermodynamic screening integration. This is the next integration increment after conservative standalone M3 discharge. It is **not** a validated Carnot battery or an 80°C-source manufactured compressor architecture.

## Strongly separated evidence classes

The existing `physics/coupled_charge.py` already calculates **TES-state-responsive** R718 heat-pump charging. In each time interval the bed outlet defines the recirculating hot-gas return, affecting required condenser supply/saturation, HP stage ratios, compressor electricity and source/intercooling circuit hydraulics. It is a **real-fluid numerical cycle** but not a measured vendor map for the original 80°C-source 5:1-per-stage machine.

The new `physics/sequential_hp_tes_service.py` receives that very `ChargeRun.final_bed` and passes it unchanged to the **reversed-flow** packed-bed discharge solver. It does not reset or reinitialise storage to make service attractive. Charge and discharge are sequential and cannot exchange heat simultaneously. Process return gas enters the original TES right-hand end x=L and hot product gas exits x=0.

Two contracts are evaluated on the SAME charged state:

| Gas stream requested | Return | Required outlet | Purpose |
|---|---:|---:|---|
| Exploratory lower-temperature gas service | 80°C | 110°C | Additional sensitivity; not the original industrial contract |
| Proposed original industrial heat grade | **110°C** | **150°C** | Strict thermal grade required to count useful industrial process heating |

These are model gas-temperature grades, **not** a physically modelled water/process HX. The tool records signed gas enthalpy pickup even when the bed is too cold, but **qualified useful heat is zero** unless the *initial*, mean and final outlet temperature of an interval all meet the requested grade. No claim of continuously meeting the cut between samples. The original 110→150°C contract is expected to be **infeasible for this short charge trajectory**; a negative finding is preserved rather than replaced by an arbitrary hotter initial state.

## Independent energy and auxiliary ledgers

- Charging takes place with the original HP condenser/bed fixed point and its already tested flow, pressure and compressor-electric ledgers. Existing `ChargeRun` reports **actual gas→TES heat** separately from nominal HP condenser heat; their small coupling split residual remains reported, not erased.
- Discharge first-law and state transfer use the same bed thermal inventory and reverse-flow BDF model. **\(\Delta U_{discharge}+Q_{gas\,to\,process}+Q_{wall}=0\)** is checked explicitly.
- The discharge gas exergy uses constant cp and a declared reference dead state; **only the gas exergy change** is measured as a model output, not a whole-system exergy efficiency.
- Compressor/source/intercooler/fan electricity from charging and a distinct modelled Ergun discharge blower electricity are both retained. The Ergun result remains **not matched to measured differential-pressure units** and should not be interpreted as an actual plant auxiliary.
- If the heat-pump charging run is incomplete/infeasible, **discharge is blocked**; it must not reuse partial storage as though a valid charged-state service contract had been fulfilled.
- A numerical qualified-temperature count is NOT a matched process heat service contract: no manufacturer-validated compressor maps, process-side HX, demand/dispatch profile, cyclic steady terminal state or storage-output uncertainty budget.

## Reproduction

`python -m pytest tests/test_m3_r718_sequential_service.py -v`

`python scripts/run_m3_r718_sequential_service.py`

The workflow `m3-r718-sequential-thermal-service.yml` installs the real-fluid physics option and publishes the source and configuration hashed JSON including full charged state, the two process-gas discharge trajectories, both energy/electricity ledgers and explicit unqualified scientific status.

**Acceptance:** matching the original 110→150°C grade is a necessary thermal screen but still insufficient for equipment qualification. A zero-delivery case is scientifically meaningful. No matched-service architecture comparison or system round-trip efficiency may be asserted unless independent equipment, process and experimental-validation gates are met.
