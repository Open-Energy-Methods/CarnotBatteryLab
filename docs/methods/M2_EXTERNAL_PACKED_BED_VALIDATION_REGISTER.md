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

## Frozen test protocol and missing evidence

Pre-register **Case A as held-out experimental run**, with B/C/D as potential physical-model calibration cases only if their conditions and instrument mappings are validated. Do not fit the model to Case A. Required before comparing any numerical model to data:

1. Independently verify actual vessel axial length, diameter, voidage, particle shape/size/distribution, solid properties, axial and radial sensor coordinates, sensor measured phase and uncertainties.
2. Establish the actual time-aligned gas mass flow and inlet temperature at the bed. Exhaust-pipe velocity must **not** be treated as bed superficial velocity without exhaust cross-sectional area, gas properties and loss/flow routing.
3. Establish source-measured pressure-channel units, transducer zero/calibration, pressure-tap locations, duct effects and uncertainty. Only with independently determined gas flow and axial bed geometry can Ergun ΔP be compared on the same measurement boundary.
4. Use measured initial bed-temperature profiles, independent material/flow coefficients, 3+ spatial meshes, time/integrator tolerance convergence and full holdout-run comparisons (T1–T7, Tout, breakthrough delay).
5. Publish MAE/RMSE/bias, time-to-temperature-crossing error with uncertainty, full mass/energy/exergy balances and structural limitations of a 1D approximation in a horizontal bed.
6. No independent manufacturer/experimental benchmark for the original 80°C-source R718 compressor operating envelope is established by this bed dataset.

The strict comparator in src/carnot_battery_lab/validation/experimental.py reports BLOCKED_METADATA or COMPARED_NOT_VALIDATED. It never sets experimental validation PASS purely because synthetic test arrays match. Tests use explicitly labelled synthetic data to exercise plumbing, not to establish physical accuracy.

## Source-to-result commands

- python scripts/acquire_public_copper_slag_a1.py --require-download
- python scripts/inspect_public_copper_slag_a1.py
- python scripts/acquire_horizontal_bed_2024.py
- python -m pip install pypdf matplotlib
- python scripts/inspect_horizontal_methods.py
- python scripts/analyze_horizontal_bed_observations.py
- python scripts/plot_horizontal_bed_observations.py

Github Actions workflow .github/workflows/external-benchmark-a1.yml runs these acquisitions, saves checksum manifests, raw data and a PDF source extract, and renders **eight original measured-data plots** (4 temperature histories, 4 native pressure vs exhaust velocity). All plots explicitly say measured only; no fabricated or fitted prediction is overlaid.

**Next validation gate:** obtain independently sourced geometry/sensor/pressure metadata and perform a calibrated-on-B/C/D, unseen-A nonlinear bed simulation with qualified material correlations. Until then, the reproducible experimental data is obtained, but thermal breakthrough and pressure-loss **model validation is not achieved**.
