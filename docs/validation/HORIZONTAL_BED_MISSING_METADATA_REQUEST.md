# Experimental metadata requests — horizontal copper-slag packed bed

**Evidence status:** unresolved items required to turn the 2024 Case B/C/D measurement series (DOI 10.17632/j37x6ptpk2.1, CC BY 4.0) into a traceable thermohydraulic benchmark. This is a lab-source checklist, not a claim that the authors have supplied answers.

**Supporting sources:** Wolde et al., *Revista Brasileira de Energia Solar* 13(2), 165–173, doi:10.59627/rbens.2022v13i2.395, and Calderón-Vásquez et al., *Modelling the temperature distribution in a horizontal packed-bed thermal energy storage system with copper slag as filler material*, doi:10.1016/j.est.2025.116769. The 2022 paper gives a 400 mm horizontal body, 158 mm internal diameter, 25 mm mineral wool insulation, ~20 mm particles with estimated porosity 0.39, seven in-bed TCs spaced 50 mm and pressure taps in connecting pipes. We must verify the 2024 runs used the identical hardware revision.

## Exact missing instrument fields

1. **Exhaust velocity to gas mass flow:** measured internal (not nominal) diameter and straight run at the Kanomax hot-wire probe, traverse or point-velocity profile, pressure at the probe, gas composition/humidity, sensor correction/calibration, sampled timestamps/time lag, leak bypass paths and whether outlet air mass flow was independently verified by another flow device.
2. **Pressure channel:** transducer manufacturer/model/range/accuracy, logger channel units (2024 CSV `$\Delta P$` appears without calibration metadata), analog volts-to-Pa or kPa transfer function, initial zero and drift correction, sample averaging/rejection of negative values near lower limit, exact upstream/downstream pressure-tap positions, connecting pipe/valve/mesh losses and a comparable empty-vessel trace. 2022 paper graphs have Pa axes, but this does not by itself establish the scaling of the *2024 CSV*.
3. **Thermocouples:** T1–T7 axial centres relative to bed inlet, heights/radial penetration, exposed gas versus contact-with-solid sensitivity, bead time constant, trace calibration/class, exact lag between downstream exhaust T_out and bed exit. Source confirms 50 mm axial spacing but not all offsets and response behaviour.
4. **Bed/filler:** actual copper slag packed mass, true/tested porosity and bed-length free area rather than nominal cylinder volume; particle size distribution, sphericity/shape, relevant high-temperature batch cp(T), thermal conductivity, density, heated wall/pipe thermal masses, insulation conductivity and ambient heat-loss calibration.
5. **Test protocol:** official mapping of Case A/B/C/D to experimental runs/operating levels, heater ramp and fan control, charge/discharge transitions, continuous flowmeter readings if available, instrument clock offsets, changes made between 2022 and 2024 experiments and whether existing author model parameters were trained on Case A.

## Scientific protocol upon receipt

- Archive the author-provided file(s) separately with date, original filename, licence, SHA-256, instrument identifier, serial number if disclosed, and exact measurement boundary. Do not replace original source versions silently.
- Fix pressure units and tap corrections **before comparing** numeric Ergun output in Pa.
- Use measured gas flow independently of the temperature being predicted, or describe the remaining target information path.
- Pre-register model parameters and acceptance metrics using development Case B only. Case A has already been evaluated and is **not blind**; Cases C/D were not used for model fitting but their descriptive statistics were previously visible.
- Perform 64/128-cell thermal-front convergence, measured-mass-flow and source-property uncertainty propagation, and independent C/D model comparison only after releasing the frozen model and calibration specification.

**No author contact has been made by this repository workflow.**
