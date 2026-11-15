# M2 external packed-bed validation register

**Evidence status: original measured temperature and pressure-channel histories acquired, source-hashed and reproducibly analysed. Predictive-model validation: NOT RUN.**

## Sources and data integrity

**Primary 2024 horizontal-flow experimental dataset:** Calderón-Vásquez, Wolde, Segovia, Battisti, Cardemil Iglesias and Escobar. DOI https://doi.org/10.17632/j37x6ptpk2.1, CC BY 4.0.

The archive contains Case_A.csv, Case_B.csv, Case_C.csv, Case_D.csv, README.txt and a five-page Electronic Supplementary Information PDF. The repository acquires, checksums and analyses them in GitHub Actions, without committing third-party raw files or inventing laboratory conditions. Source README: seven in-bed thermocouples (T1–T7), Tin at heater outlet, Tout downstream exhaust, ambient T0, differential-pressure channel and exhaust-pipe air velocity; temperature °C, time seconds at 30-second sampling, velocity m/s. **Pressure-channel units are not given in the source README**.

| Run | Raw CSV SHA-256 | Samples | Max measured Tout, °C | First measured Tout upward crossing of 80°C, s | Median recorded pressure, native units UNKNOWN | Median exhaust velocity, m/s |
|---|---|---:|---:|---:|---:|---:|
| A | 35558300d7d5ef7a2ccf5c039fb8f566fbcc97b8ff6ffc181af6ba567769a0e9 | 221 | 176.2 | 1059.18 | 0.894 | 5.855 |
| B | 5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab | 301 | 173.0 | 1847.84 | 0.365 | 3.825 |
| C | 5bfab2554b44ec5d1b5ce1e5aecd94074c35e126f7c7ed427aa9282777b454f9 | 293 | 243.1 | 1061.10 | 0.966 | 6.250 |
| D | b6db5d44e050d0cac259db42368cea421b88cfc51a9747586e47b5c20d27493f | 403 | 272.7 | 1870.75 | 0.294 | 3.750 |

These are **measurements**, not simulations or measured-vs-model errors. Threshold crossing uses linear interpolation across adjacent recorded samples. An exhaust-pipe Tout crossing is not a sensor-mapped in-bed thermal-front travel time. The recorded differential pressure cannot be interpreted in Pascals until units, calibration and tap geometry are independently established.

**Companion five-page modelling supplement**, SHA256 ca020dd17e9af13c8a6f4417786a17f3d94366230b5db93576934af67ff527fc, documents an equivalent one-temperature advection/dispersion/wall-loss model with boundary conditions (equations S1–S4), effective conductivity (S5), transformed analytical solution (S6–S19) and SOC (S20–S21). Its authors explicitly warn horizontal-bed radial gradients and buoyancy are not captured by simple 1D plug flow. It reports a prior air/solid h range about 90–130 W/(m² K) for their equipment, not a universal correlation for our 4m × 5m reference.

**Secondary 2025 A1/R4 dataset:** https://doi.org/10.17632/fgn79fzg7x.1, CC BY 4.0. The page advertises axial A1 and radial R4. However, the pinned publicly downloadable CSV SHA256 b557561cecb9b87092c0ea6f14bda178d7b9aae301a939267702bd943c46cce8 contains **only Run: R4 / Topology: Radial** (2,667 actual samples). No axial A1 samples were found. This dataset must not be cited as an available A1 validation curve without an independent source file from authors.

## Related independently published apparatus description (important new evidence)

Wolde, Calderón-Vásquez, Segovia and Cardemil (2022), *Estudio experimental de lecho empacado de piedras a alta temperatura utilizando escoria de cobre como material de almacenamiento*, Revista Brasileira de Energia Solar 13(2), pp.165–173: https://rbens.emnuvens.com.br/rbens/article/download/395/287/791 . Its Methods §2.1–2.2 document **400 mm cylinder length, 158 mm internal diameter, 7 mm steel wall, 25 mm mineral wool insulation, seven in-bed thermocouples spaced 50 mm, nominal 20 mm irregular copper-slag particles, estimated porosity 0.39**, and differential-pressure taps in the inlet and outlet pipes. The later 2025 companion article reports a horizontal **7.45 L** rig with 2-inch pipes and the same authors; this is strong evidence of apparatus continuity, but trace individual 2024 runs to the exact apparatus revision before claiming a validated match.

**Internal consistency caution:** a perfect 400 × 158 mm cylinder geometrically contains roughly 7.84 L rather than the cited 7.45 L nominal volume, a ~5% discrepancy that could reflect internal fixtures/dead space or rounding. Do not silently alter diameter or length to force agreement; log alternative effective volumes in uncertainty analysis.

The 2022 report plots pressure loss with a Pa axis but the **2024 raw CSV does not state its logged pressure channel unit or transformation**. Different original electronics/software versions may use different scaling, so treating 2024 values around 0.3–1.0 as direct Pa or kPa remains unsupported. Furthermore pressure taps are on pipes either side of the tank, so the observed channel may include more than pure Ergun bed loss.

The 2022 article characterises horizontal-bed radial thermal gradients, consistent with the supplement's structural-model warnings. Its reported slag particle size is approximate and its porosity estimated; these are an independently grounded **first-case geometry**, not exact certified batch material inputs.

An initial **uncalibrated, explicitly non-blind** replay is implemented in scripts/exploratory_forward_horizontal_bed.py. It uses this published geometry and original measured Tin(t), exhaust velocity(t), and **measured Tout(t) to estimate exhaust-air density and flow**, matching the earlier source's experimental Eq.(1). Because measured Tout enters the flow boundary, the reported difference to Tout is not a genuinely independent blind validation metric. The exhaust pipe assumed inner diameter of 52 mm is NOT a published internal diameter, and gas/rock properties, absolute TC offset and wall UA are assumptions. Case A is untouched by fitting; neither Case B nor A is used to tune parameter values. Separate pressure predictions in Pa are never overlaid as if matching the unqualified raw channel.

## Frozen test protocol and missing evidence

Pre-register **Case A as held-out experimental run**, with B/C/D as potential physical-model calibration cases only if their conditions and instrument mappings are validated. Do not fit the model to Case A. Required before comparing any numerical model to data:

1. Use the 2022 source-backed 400 mm / 158 mm vessel and ~20 mm slag / 0.39 porosity as the initial apparatus hypothesis, and independently verify correspondence to each 2024 case; still resolve particle shape/distribution, solid properties, absolute sensor coordinates, sensor measured phase and uncertainties.
2. Establish the actual time-aligned gas mass flow and inlet temperature at the bed. Exhaust-pipe velocity must **not** be treated as bed superficial velocity without exhaust cross-sectional area, gas properties and loss/flow routing.
3. Establish source-measured pressure-channel units, transducer zero/calibration, pressure-tap locations, duct effects and uncertainty. Only with independently determined gas flow and axial bed geometry can Ergun ΔP be compared on the same measurement boundary.
4. Use measured initial bed-temperature profiles, independent material/flow coefficients, 3+ spatial meshes, time/integrator tolerance convergence and full holdout-run comparisons (T1–T7, Tout, breakthrough delay).
5. Publish MAE/RMSE/bias, time-to-temperature-crossing error with uncertainty, full mass/energy/exergy balances and structural limitations of a 1D approximation in a horizontal bed.
6. No independent manufacturer/experimental benchmark for the original 80°C-source R718 compressor operating envelope is established by this bed dataset.

The strict comparator in src/carnot_battery_lab/validation/experimental.py reports BLOCKED_METADATA or COMPARED_NOT_VALIDATED. It never sets experimental validation PASS purely because synthetic test arrays match. Tests use explicitly labelled synthetic data to exercise plumbing, not to establish physical accuracy.

## Exploratory forward comparison — a transparent negative finding

Using the existing conservative two-temperature BDF solver, nominal dimensions sourced from Wolde et al. (2022), and fixed **unfitted** rock/gas assumptions, an exploratory forward replay has been run on Cases B and A. Assumptions are stored explicitly in scripts/exploratory_forward_horizontal_bed.py: a **52 mm exhaust pipe inner bore** (not established by source), rock density **3700 kg/m³** and cp **1100 J/(kg K)** (indicative), lumped wall UA **0.5 W/K**, gas density **1 kg/m³**, constant gas cp, μ and k. The script derives its flow from measured exhaust velocity and **measured Tout for outlet air density**, following the earlier experimental paper's mass-flow equation. Because measured Tout is used to estimate the forcing, this is **not an independent blind prediction**. It also approximates the thermocouple axial-centre positions based on their reported 50 mm spacing.

The first GitHub CI execution (unfitted, no optimisation or calibration) gave:

| Metric | Case B | Case A (nominal holdout, not fitted) |
|---|---:|---:|
| Model vs measured exhaust temperature RMSE | **38.052 °C** | **24.413 °C** |
| Mean absolute error | **28.102 °C** | **19.027 °C** |
| Numerical bed-energy relative residual maximum | **5.9×10⁻¹²** | **4.3×10⁻¹²** |

The low energy residual is a numerical internal-conservation test, **not evidence of external predictive agreement**. Large discrepancies are retained in the output, not hidden or retuned. The code now also reports the **observed vs model 80°C breakthrough crossing time**, marking missing crossings explicitly as null rather than extrapolating. Plots overlay the measured exhaust channel and exploratory model predictions with warnings.

These outputs demonstrate a key scientific limitation: a physically conservative one-dimensional model can significantly miss experiments because of uncertain true air-flow cross section, radial gradients, real material heat capacities, sensor transport delay, pressure drop and heat leaks. No V3 physical validation gate has passed.

## Source-to-result commands

- python scripts/acquire_public_copper_slag_a1.py --require-download
- python scripts/inspect_public_copper_slag_a1.py
- python scripts/acquire_horizontal_bed_2024.py
- python -m pip install pypdf matplotlib
- python scripts/inspect_horizontal_methods.py
- python scripts/analyze_horizontal_bed_observations.py
- python scripts/plot_horizontal_bed_observations.py

Github Actions workflow .github/workflows/external-benchmark-a1.yml runs these acquisitions, saves checksum manifests, raw data and a PDF source extract, and renders **eight original measured-data plots** (4 temperature histories, 4 native pressure vs exhaust velocity). All plots explicitly say measured only; no fabricated or fitted prediction is overlaid.

**Next validation gate:** use the demonstrated negative model-vs-observation discrepancy to prioritise confirmation of 2022-to-2024 apparatus continuity, source exact exhaust bore/pressure scale and sensor absolute positions, and perform a calibrated-on-B/C/D, unseen-A nonlinear bed simulation with qualified temperature-dependent material properties and strict holdout. Until then, the reproducible experimental data is obtained, but thermal breakthrough and pressure-loss **model validation is not achieved**.
