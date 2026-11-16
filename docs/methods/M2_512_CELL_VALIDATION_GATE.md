# M2 — 512-cell spatial convergence and physical-validation STOP gate

**Evidence status:** Conditional numerical-resolution criterion PASSED for the original source-forced Case B. **Experimental model validation remains BLOCKED.** These statuses are independent.

## Original source and fixed model boundary

Original 2024 horizontal copper-slag experiment DOI https://doi.org/10.17632/j37x6ptpk2.1 (CC BY 4.0), Case B CSV SHA-256 5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab. Apparatus nominal dimensions from related 2022 publication: length 400 mm, inside diameter 158 mm, approximately 20 mm slag particles and estimated porosity 0.39. The 52 mm exhaust inner diameter, constant properties and wall UA remain **assumed**, not calibrated.

**Crucial boundary limitation:** the historical model uses observed exhaust outlet temperature to calculate exhaust density and thus infer mass flow, following the original source's Eq.(1). This produces a target-informed boundary, so its converged prediction is **not an independent blind prediction of experimental outlet temperature**.

## Seven-grid numerical study

| Cells | Predicted first 80°C outlet crossing (s) | RMSE against measured Case B (°C) |
|---:|---:|---:|
| 8 | 1266.74 | 35.519 |
| 16 | 1450.85 | 38.052 |
| 32 | 1556.38 | 40.600 |
| 64 | 1613.73 | 42.277 |
| 128 | 1644.08 | 43.228 |
| 256 | 1659.63 | 43.734 |
| 512 | 1667.50 | 43.995 |

Measured Case B first 80°C outlet crossing: 1847.84 s. The 512-cell model remains significantly too early and the outlet RMSE worsens with grid refinement. Hence coarse-grid numerical diffusion had partially hidden physical-model and/or forcing errors.

| Mesh refinement | RMS difference in full model outlet history (K) | Difference in 80°C crossing (s) |
|---|---:|---:|
| 8→16 | 9.89031 | 184.114 |
| 16→32 | 5.87337 | 105.527 |
| 32→64 | 3.24716 | 57.351 |
| 64→128 | 1.71500 | 30.351 |
| 128→256 | 0.88241 | 15.552 |
| 256→512 | **0.44771** | **7.870** |

Observed refinement orders computed from successive RMS ratios: 0.7518, 0.8550, 0.9210, 0.9587, 0.9789, approaching first-order upwind behaviour. The latest pair meets the existing *prospective engineering* numerical targets (RMS ≤1 K and absolute breakthrough shift ≤15 s), with monotonic decrease across all pairs.

This is a **conditional numerical-resolution pass at the specified boundary, material assumptions and first-order model**, not a physical-error bound, experimental measurement uncertainty tolerance, verified higher-order method, or demonstration that another operating point will converge identically.

## Machine-readable physical-validation STOP gate

The added script scripts/report_m2_validation_readiness.py consumes the source-hashed measurement JSON and the independent numerical convergence report. It records:
- Missing true exhaust internal bore, velocity probe area correction, local static pressure, mass-flow/transport uncertainty.
- Unverified native differential-pressure transducer units, zero/offset and bed-versus-duct/tap loss corrections; no Pa conversion or Ergun agreement permitted.
- Unverified absolute axial/radial thermocouple positions, sensor time constants, actual batch slag properties and horizontal-buoyancy effects.
- Model target leakage in this historical study. The newer **model-predicted outlet** implicit flow solver avoids that leak at 16 cells but has not yet been verified at 256/512 cells.
- Case A has previously been inspected (not pristine blind). C/D have observed descriptive summaries and are excluded from model fitting or parameter selection in this study.

The validation readiness status remains EXPERIMENTAL_MODEL_VALIDATION_BLOCKED regardless of a successful numerical refinement. No manufacturer-qualified compressor, experimental bed predictive validation, Ergun pressure validation, full-system TES charging/discharge or scientific v1.0 claim is justified.

## Reproduction

Install physics/test dependencies and run these scripts in order:

1. python scripts/acquire_horizontal_bed_2024.py
2. python scripts/study_horizontal_bed_resolution.py
3. python scripts/report_m2_spatial_convergence.py
4. python scripts/report_m2_validation_readiness.py

The external-data GitHub Actions workflow archives original source hashes, full seven-grid reports and separately enumerated blocked experimental gates. For specific author/instrument metadata requests see docs/validation/HORIZONTAL_BED_MISSING_METADATA_REQUEST.md.
