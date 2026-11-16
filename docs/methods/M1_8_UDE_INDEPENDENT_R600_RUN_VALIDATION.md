# M1.8 — UDE measured n-butane instrumentation audit, independent-run holdout gate

**Evidence class:** original laboratory compressor sensor data audit and test-design eligibility, **not** a validated compressor efficiency map. The original H-REF target remains source 80→70°C, 110→150°C liquid process at 1 MW. This work tests **whether another laboratory's genuine recordings have enough independent operating conditions to justify an interpolation validation claim**.

## Primary data and physical rig

Schmeing, Welp & Atakan (University of Duisburg-Essen), ["Experimental Dataset: Heat Pump coupled to a Thermal Storage for charging a Carnot Battery"](https://doi.org/10.5281/zenodo.18712882), 2026. Original `data.zip`, **published MD5 `d17bf8b134977f4672c1ec22f085f0ea`**, 36.1 MB. The conference paper (doi:10.36227/techrxiv.176478421.10869135/v1) describes a **3.3 kW electrical reciprocating compressor** integrated with two unpressurized hot-water tanks; temperature-dependent sink is roughly 45–90°C and the heat source tap water near ambient. This is **not** a 1 MW R600 transcritical 80°C industrial waste-heat compressor or a gas/rock packed-bed TES.

The checksum-verified original archive contains 184 entries, including **Bitzer primary compressor logger files** for the n-butane runs **026, 027, 028**, dated 9–10 October 2025. Their filenames state 70 Hz and varying nominal storage temperature. Metadata discovery established **2,280, 2,310, 2,249 records, respectively**, totaling **6,839 time-correlated records**. The logger CSVs have **157, 155, 155 columns**, respectively, using semicolon separators. Columns explicitly label low/high **absolute** pressure as bar(a), compressor speed, compressor frequency and motor power (the latter two mechanical/electrical quantities must not be assigned SI units by guesswork).

## Predeclared strict data protocol

1. Verify the original unmodified ZIP bytes against its **publisher-recorded MD5** *before* reading any source. Compute source SHA-256 in the result report. No external source code is executed. The source ZIP contains an experimental compressor model with a README explicitly saying its underlying Roskosch model must **not be made public**. Do **not** import, copy, redistribute, translate, trace or execute that model without explicit permission.
2. Read exclusively three instrument-logger filenames containing both the **expected experiment ID** and literal `n-Butane`. Reject duplicates, missing run files, unsafe ZIP paths, wrong CSV widths or absent mandatory sensor names. A CSV row with malformed or absent values cannot be relabeled as a valid test.
3. Parse original logger numeric strings with decimal-comma support, check finite values and **positive** original absolute suction pressure, strictly greater discharge pressure, positive speed and frequency, and positive motor-power channel. Rows failing those checks are recorded as unavailable/filtered, **not imputed, calibrated or fitted**.
4. Aggregate **only per-run** valid sample counts, sensor ranges and medians. Each run is the largest defensible distinct experimental unit; thousands of within-run samples are serially correlated and must **not** become thousands of fake independent train/holdout groups. Even the three runs are from one instrumentation system and campaign (run-level withholding is not independent laboratory validation).
5. Predeclare **leave-entire-run-out** assessments: for each of runs 026/027/028, reserve that entire run, leaving the other two runs for fit eligibility. Independently check whether the reserved run's operating centroid (absolute suction pressure bar(a), absolute discharge pressure bar(a), raw logger compressor-speed channel) is on the **nonnegative line segment** between the **two available training-run centroids**. A two-point training set spans a *line*, **not a three-dimensional operating envelope**. Merely being between separate coordinate min/max values is insufficient.
6. The predeclared **screening heuristic** is at least **five independently conducted usable runs** and a true in-domain withheld run, with independently confirmed sensor meter boundaries and calibration uncertainties, before any claim of in-envelope predictive accuracy. Five is a conservative research protocol heuristic, **not a manufacturer/regulatory standard**. Three runs necessarily fail the sample-size gate; no compressor efficiency model is trained or evaluated on them, even when individual recorder rows are plentiful.
7. Preserve the **original OST M1.7 five withheld measured conditions**, source MD5, source-data SHA-256, original holdout grouping seed and original **0.066520 MAE**. M1.8 calls the existing M1.7 parser and splitter **without changing its split, model or thresholds**. Original OST data are *not* combined with UDE observations to train a cross-machine surrogate. The original OST holdouts are *not* re-selected, retuned, "improved" or counted as independent UDE experimental points.
8. Publish **only source provenance, run-level aggregate sensor summaries, split eligibility, pre-registered missing-field decisions and original OST hashed holdout identities**, not original third-party time series, PDF/model source text or raw sensor data.

## Physics and measurement limits

- `Low pressure [bar(a)]` / `High pressure [bar(a)]` directly declare **absolute** pressure; pressure ratio may be calculated from those two reported channel values for valid records. Not evidence the pressure sensors are calibrated or correct at the original H-REF target.
- `Compressor speed`, `Compressor frequency`, and `Motor power` logger fields are genuine recorded channels, but their **units, signal provenance and motor/shaft meter boundaries are not independently established here**. Do **not** promote `Motor power` into measured shaft power [W], electrical input [kW] or measured overall isentropic efficiency by assuming a device manufacturer's scaling.
- The separate processed UDE table may contain mass-flow/temperature/efficiency variables, but it has a **multirow header and separate sensor metadata**. Joining it to the Bitzer raw logger by date/run/time or treating a derived model quantity as an independent sensor requires a documented, independently checked alignment, time base, original calibration and units. This milestone deliberately does not invent the join or derive absent source measurements.
- Time samples from the same charging run may share control ramps, drift, sensor offsets, common transients, and changing storage temperature. Temporal autocorrelation and leakage are why arbitrary random-row holdouts would be scientifically misleading.
- A model with `Motor power` as the dependent variable would be uninterpretable until its units and electrical/shaft boundary are independently established. Therefore **no physical power-prediction RMSE, COP, isentropic-efficiency accuracy or manufacturer's compressor map is claimed**.
- The run-level pressure/speed screening is at **UDE** suction/sink conditions, not the industrial R600 80°C source / 150°C process envelope; it is an *external research validity test*, not a plausible 1 MW industrial compressor architecture.

## Reproduction

```bash
python -m pip install -e ".[physics,test]"
python -m pytest tests/test_m1_8_ude_r600_run_validation.py tests/test_m1_7_r600_offdesign_holdout.py -v

python scripts/inspect_ude_r600_run_metadata.py \
    --download --output results/m1_8_ude_nbutane_schema_only.json

python scripts/run_m1_8_ude_r600_validation.py \
    --download --output results/m1_8_ude_original_nbutane_run_level_validation.json
```

Dedicated CI: `.github/workflows/m1-8-ude-nbutane-independent-run-validation.yml`. Both original datasets are pinned to published MD5 checksums; all reported experiments are genuine independently sourced recordings, **not simulated manufacturer EN12900 outputs**. Only the original publisher can verify source calibration documents, machine protection limits and redistribution licenses.

## Decision gate

**Current available external experimental runs: three. Required before credible independent in-envelope numerical accuracy study: five or more distinct, suitable calibrated R600 run conditions, heldout state genuinely inside training coverage, physical sensor units, suction temperature, mass-flow/motor boundary resolution and independent uncertainties.** Until those are obtained, the scientifically correct output is **INSUFFICIENT_INDEPENDENT_RUNS / NO_VALIDATED_IN_ENVELOPE_ACCURACY**, not an artificially small interpolation error from thousands of temporally correlated samples.

**Global architecture gate unchanged:** M1.5 original H-REF manufacturer map not verified; process-liquid heat exchanger and TES measured packed-bed breakthrough/pressure-loss validation pending; no matched-service 1 MW model or demonstrated round-trip efficiency.
