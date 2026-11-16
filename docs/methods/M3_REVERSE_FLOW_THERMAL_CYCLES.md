# M3 — Independent reverse-flow thermal TES discharge and cycling (synthetic)

**Classification:** implemented numerical research software. **No independent pressure-loss, field-temperature or useful-industrial-service validation**; heat-pump coupling is deferred until the separate M1 compressor operating envelope is independently supported.

## What M3 adds

The previously verified constant-property, two-temperature, first-order packed-bed solver `advance_bed` is mathematically symmetric under reversal of a bed with uniform section, material properties and heat-transfer correlations. To simulate **physical reverse-flow discharge**, the new `advance_reverse_discharge` operation:

1. Reverses gas **and** solid spatial state arrays (without changing total energy), turning the original right-hand physical cold-gas inlet x=L into the numerical upwind x=0.
2. Runs the original same positive-flow conservative BDF solver with specified *process return gas* inlet temperature and mass flow.
3. Reverses both final arrays back to the physical coordinates. The useful hot stream exits at original x=0; it is NOT simply read from the original forward-flow outlet.
4. Tracks signed gas enthalpy gain `Q_gas_out = -Q_from_hot_gas`, rock/gas storage energy change, wall loss and independent Ergun-only fan energy (source-unvalidated).
5. Applies a conservative **discrete-sample** temperature-grade screen: the initial, interval-average and final reverse outlet must all reach the service cutoff before any positive gas enthalpy gain in that interval is counted as *qualified* delivered heat. This does **NOT** establish a continuous-time outlet constraint between samples and is not a matched industrial heat exchanger/loop.
6. Reports signed ideal cp exergy gain of the process gas relative to an explicitly assumed dead state, using `Δb=cp[(Tout−Tin)−T0 ln(Tout/Tin)]`. The exergy record applies to the total process stream, including intervals below the heat-grade cutoff; it is not certified useful high-grade exergy.

## Conservation, SOC and repeated cycles

For a discharge interval, the original solver's exact integral energy ledger implies

\[
\Delta U_{bed}+Q_{gas\,out}+Q_{ambient}=0,
\]

where `Q_gas_out` is positive when the bed heats process return gas and `Q_ambient` is positive ambient loss. Charging and discharge are integrated through repeated cycles with independent **cycle-level** closure:

\[
\Delta U_{cycle}-Q_{charge,gas}+Q_{discharge,gas}
+Q_{ambient,charge}+Q_{ambient,discharge}=0.
\]

The bed gas/rock storage energy is the existing constant-cp thermal inventory. Nominal SOC is **unclipped** relative to two freely declared uniform reference temperatures, so a value below 0 or above 1 remains visible rather than being silently corrected. End-versus-start maximum gas/rock cell temperature deviation is reported for each repeated cycle. The provisional 0.25 K end-state criterion is a numeric **scenario requirement**, not a convergence demonstration over all duty conditions or a measured uncertainty.

**No thermal round-trip efficiency is reported**, because a legitimate useful-service round-trip comparison requires cyclic steady state, consistent terminal bed state, fixed qualified process heat cutoffs, and an externally supported heat-pump charging/heat-source boundary. **No electricity-return or electricity-to-heat system performance claim** is computed; fan electricity is tracked separately, heat pump/compressor electricity absent.

## Synthetic independent demonstration

Nominal 0.4 m × 0.158 m test vessel, ~20 mm particles, estimated porosity 0.39; 12 volume cells; unmeasured gas density and slag cp/density; 30 min×? actually **30 charging steps ×30 s and 30 reverse discharge steps ×30 s per cycle**; three repeated cycles; heat-gas charging inlet 430 K, discharge return 303.15 K, useful process cutoff 350 K, 0.010 kg/s and ambient 303.15 K; **unverified** wall UA 0.2 W/K and modelled Ergun blower energy. This is completely synthetic: no real gas/slag instrument data and no R718/R600 compressor map or process heat exchanger.

Numerical tests independently compare reverse flow to the original forward solver applied on physically reversed states; check full energy inventories, positive discharge heat, unavailable-grade withholding, blower energy, exergy formula, unclipped SOC, total cyclic first law and fail-closed duty guards. The CI artifact archives every interval grade and pressure estimate, scenario input hash and cyclic state deviation.

## Research acceptance gates not yet satisfied

- Independent pack geometry (especially actual exhaust bore), pressure transducer units/zero/tap losses and uncertainty; thermocouple true gas/rock contact response and measured slag thermophysical properties.
- Bidirectional flow manifold, valve dead volumes, wall/pipe inertia, axial/lateral gradients, time-dependent gas pressure/flow and validated pumping/fan work.
- At least 3–4 meshes with independent thermal/exergy convergence under a chosen duty cycle, and verified cyclic steady operation for the intended process heat grade.
- The compressor/HX temperature envelopes must respond to TES state, with actually supported equipment maps and heat-pump control. Existing R718 compressor design has no exact 80°C source hardware qualification, and R600 cycle screening has no manufacturer compressor map.

**M3 deliverable is a verified synthetic bidirectional TES building block, not a physically validated integrated Carnot Battery architecture and not scientific v1.0.**
