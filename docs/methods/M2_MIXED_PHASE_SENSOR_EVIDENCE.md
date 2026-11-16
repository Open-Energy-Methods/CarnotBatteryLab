# M2 — instrument evidence and mixed-contact sensor observation model

**Status 2026-11-16:** public source inspection improved the instrument evidence; **pressure and gas-flow calibrations still unavailable**. New model-versus-thermocouple results are **one-way diagnostic, not independently validated temperatures**.

## Verified original instrument evidence (distinct from assumed values)

Original 2022 experimental report: Wolde, Calderón-Vásquez, Segovia and Cardemil, *Revista Brasileira de Energia Solar* XIII(2), 165–173, DOI [10.59627/rbens.2022v13i2.395](https://doi.org/10.59627/rbens.2022v13i2.395), **Methods 2.1, page 166, Fig. 2**. Original accessible source: https://rbens.org.br/rbens/article/download/395/287.

| Variable/element | Exactly source-supported | Not independently supported for 2024 data |
|---|---|---|
| Tank | Horizontally arranged steel body, 400 mm length, 158 mm ID, 7 mm wall; stated 7.45 L internal volume | Internal dead-space/fixtures, 2022→2024 hardware continuity |
| Insulation | 25 mm mineral wool around tank and inlet/outlet pipes in 2022 setup | Actual wall thermal inertia / heat losses in Case B 2024 |
| Internal temperature | **Seven Type-K thermocouples 50 mm apart**; their **sheaths physically contact rock and surrounding air** | Exact first sensor offset, radial position, gas-versus-rock response weighting, calibration/time constant |
| Fluid temperature | Separate inlet and outlet pipe thermocouples Tin and Tout | Lag between bed exit and downstream pipe Tout; probe compensation |
| Differential pressure | Taps/capillaries in **inlet/outlet pipes**, stainless capillaries and **8 mm silicone hoses** to pressure sensor | Exact differential transducer make/model/scale/zero, placement relative to fittings and bed-only pressure loss |
| Data acquisition | **Campbell Scientific CR1000** logger | Whether 2024 logger/sensor firmware/settings identical |
| Air velocity | Outlet-pipe hot-wire connected to a **Kanomax digital anemometer** | Specific Kanomax model/probe calibration/traverse and actual pipe internal bore at the sensing position |
| Heat source | Leister HOTWIND SYSTEM air heater/blower; admissible 20–650°C and 200–900 L/min in 2022 Table 1 | Velocity-probe actual air mass flow and 2024 heater configuration |
| Slag | Approximate 20 mm irregular pieces, **estimated** packing voidage 0.39; previous materials range cp 0.8–2.3 kJ/(kg K) across samples | Exact 2024 batch particle-size distribution, porosity and cp(T)/k(T) |

Original 2024 measurement source: Calderón-Vásquez et al., [10.17632/j37x6ptpk2.1](https://doi.org/10.17632/j37x6ptpk2.1), CC BY 4.0, four original source-locked Case_A/B/C/D time series; 2024 source README contains sensor labels and velocities but **does not give pressure-channel units**. The dataset description explicitly invites researchers who wish to model its data to contact the corresponding author **idcalderon@uc.cl** for additional experimental conditions. This contact is public in both the dataset and 2022 article.

The later *Journal of Energy Storage* 2025 paper DOI [10.1016/j.est.2025.116769](https://doi.org/10.1016/j.est.2025.116769) refers to **2-inch nominal steel pipes**. It does not certify the internal bore at the hot-wire measurement location, whether it has Sch40/Sch80 wall thickness, or the same pipe version as the 2022 test. No nominal-diameter-to-actual-flow conversion has been applied.

**Separate external evidence is not transferable:** Claren et al., *Journal of Energy Storage* 2026, DOI [10.1016/j.est.2026.123432](https://doi.org/10.1016/j.est.2026.123432), reports about 63.2–257.4 Pa pressure loss for a **different radial-flow prototype** with an empty-tank baseline. Its measured pressure ranges and Darcy–Forchheimer coefficients are **NOT hydraulic calibration of the 2024 horizontal axial device**. Do not equate topologies or pipe losses.

## Mixed-phase thermocouple observation issue

A two-temperature continuum model has gas temperatures `Tf_i(t)` and solid temperatures `Ts_i(t)`. The 2022 text specifically states the thermocouple sheath is in contact with **both gas and stones**. Therefore mapping the measured `T1..T7(t)` directly to `Tf` or `Ts` is unsupported and could make a physically valid model appear inaccurate or vice versa.

With seven sensors, a confirmed axial increment `d=0.05m`, nominal bed length `L=0.40m`, and an **unknown** first sensor offset `x0`, purely geometric feasibility permits `0<=x0<=L-6d=0.10m`. The new observation-envelope code spans all finite-volume gas and solid cell temperatures in each sensor's possible axial interval; it explicitly **does not choose an x0 or a gas-solid mixing coefficient from the measured data**. Its bound is intentionally broad and ignores the sensor's uncertain transient time constant and contact details.

`sensor_phase_position_envelope` thus reports an **instantaneous model-phase/possible-position extrema** (minimum to maximum). This is **NOT an experimental uncertainty interval**, not a calibrated thermocouple transfer function and not a realizable joint sensor-field bound: all seven probes share a physical common offset, and the union independently computed per channel ignores that correlation. A measured point outside the extrema is cause for further instrument/model investigation, **not proof that a model fails**, because sensor lag and radial location are unknown. A measured point inside the extrema is **not evidence of validation**.

### Case B diagnostic boundaries

The new Case B-only forward script uses original case SHA-256 `5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab`, historical model initialisation from measured T1–T7 at assumed centres **0.05..0.35 m**, and subsequent source measured inlet Tin and exhaust velocity. It uses the earlier **predicted-outlet implicit mass-flow calculation**, so it does **not** use measured Tout or later measured T1–T7 as physical inputs. For comparison, the observation operator admits `x0` 0..0.10m; this broader range does not undo the fact that the initial model field was constructed with a 0.05m **assumed** offset.

The script records source observation, model interval lower/upper, fraction outside bounds and outside distance, plus explicit limitations. It excludes the first sample used to initialise the state and has no empirical fitting to any T1–T7 curves. **A was previously inspected and is not a pristine holdout; C/D remain unused for forward model selection.**

A 128-cell execution is only an exploratory sensor-observation check, not a new numerical front/phase field convergence pass. Previous 512-cell successful convergence pertains specifically to **outlet temperature/front**, not necessarily in-bed sensor observation operators. Never conflate the two.

## First source-locked Case B sensor-compatibility results

The dedicated GitHub Actions job ran the target-independent exhaust-flow 1-D solver at **128 cells** (numerical grid convergence of these in-bed extrema is **not** established), on the original source-hashed Case B with 300 post-initialisation sample times (301 original Case B rows; initial sample excluded). The model does not ingest measured downstream T1–T7 for forcing or calibration.

| Original measured TC | Fraction outside even broad gas/rock x-position extrema | Average outside distance (°C, zero for inside) | Maximum outside distance (°C) |
|---|---:|---:|---:|
| T1 | 56.3% | 3.02 | 26.73 |
| T2 | 46.3% | 2.01 | 20.01 |
| T3 | 51.3% | 5.09 | 57.69 |
| T4 | 46.7% | 5.20 | 61.80 |
| T5 | 48.3% | 7.59 | 70.11 |
| T6 | 50.3% | 9.48 | 71.75 |
| T7 | 55.7% | 15.53 | 91.00 |

**Interpretation:** even a broad, *independently uncalibrated* phase/possible-position envelope frequently does not contain the measured TC values, with especially large maximum downstream disagreement. This is evidence of **model/measurement incompatibility under current instantaneous assumptions** and a research diagnostic, not a physical-uncertainty estimate or a formal validation failure. The unknown sensor lag, thermal contact, radial placement, initial-layout assumption and source-input gas flow may substantially affect comparability. The maximum discrepancies must NOT be read as gas-only or rock-only residual errors, or as the result of a matched TC uncertainty calculation. No choice of a fitted x0 or fitted gas/solid mixing coefficient was made.

The original simulation already has large 512-cell outlet error with and without measured-Tout forcing. These new 128-cell in-bed diagnostics therefore **strengthen the need for independently calibrated sensor and mass-flow metadata**, not a claim that thermocouple placement adjustments fix the physical model.

The pipeline archives all 7 raw-sensor time histories of measured point and interval extrema plus **three clearly labelled diagnostic figures for T1/T4/T7**. Source URL/CSV hash and exact run are recorded. Numerical and physical model validation remain separate.

## What requires the authors or new experimental measurements?

The following are *not available* in original public files and cannot be guessed from observed model residuals:

- Actual internal bore at exhaust Kanomax hot-wire station, probe model and cross-sectional velocity traverse/calibration; operating pressure, density, possible air leaks and transit delay.
- Differential-pressure sensor manufacturer, native signal-to-Pa scale, zero, uncertainty, and whether 2024 inlet/outlet taps include duct/fittings or what empty-vessel baseline could remove.
- T1–T7 absolute axial/radial coordinates, sheath placement relative to the particles, calibration and first-order/instrument time constants.
- 2022-to-2024 apparatus continuity and slag batch cp(T), k(T), packing mass and porosity.

The public corresponding author contact is **idcalderon@uc.cl** (2024 Mendeley description); no contact was made automatically. The ready-to-send request is in `docs/validation/REQUEST_HORIZONTAL_BED_INSTRUMENT_METADATA.md`.

## Scientific status

Mathematical/internal energy and 512-cell outlet convergence are achieved at the original Case B scenarios. **Independent experimental predictive validation remains BLOCKED by physical evidence**. Any new sensor extrema plots are diagnostics only, not a claimed improvement in the 50°C source-locked model/expt outlet RMSE, a validated Ergun pressure curve, or industrial hardware proof.
