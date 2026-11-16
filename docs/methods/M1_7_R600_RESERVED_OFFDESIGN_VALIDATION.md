# M1.7 — Reserved experimental holdouts for R600 off-design electrical efficiency

**Release class:** genuine external experimental **out-of-sample screening**, *not* vendor map validation or industrial plant qualification.

## Source and narrow hypothesis

Independent publication: P. Widmaier et al., *Benchmarking and Validation of Reciprocating Piston Compressor Models for Industrial Heat Pump Design*, 15th IEA Heat Pump Conference (2026); original source [DOI 10.5281/zenodo.17599603](https://doi.org/10.5281/zenodo.17599603), CC BY 4.0. The source's original 3.4 MB `compressor_performance_data.csv` has archival MD5 `680dd400cfb39b2fa0a1dd22a09c731f`. Its [README](https://zenodo.org/records/17599603/preview/ZENODO_README.md?include_deleted=0) defines the **overall electricity-based** compressor isentropic efficiency:

\[
\eta_{is,electric}=\frac{\dot m\left[h(p_{dis},s_{suc})-h(p_{suc},T_{suc})\right]}{P_{electric}}.
\]

**Crucial meter boundary:** the original M1.4 R600 cycle uses the *hypothetical shaft* isentropic efficiency `eta_shaft=0.74`, plus *assumed* motor efficiency `0.95` and inverter efficiency `0.98`. The apples-to-apples *electrical isentropic* efficiency hypothesis for this meter boundary is therefore

\[
\eta_{is,electric,reference}=0.74\times0.95\times0.98=\mathbf{0.68894}.
\]

No gearbox, unmeasured generator power, or other auxiliaries are inserted. This constant is **pre-specified from the existing model** and not calibrated to the source. We must NOT compare the experimental `eta_is` to `0.74` as though both are shaft efficiency. We do **not** infer a measured shaft efficiency by dividing by the assumed drive efficiencies.

## Observation selection and source classification

The published CSV has 32,073 records. Source-class auditing (M1.6) establishes that **31,702** are *manufacturer EN12900 polynomial synthetic outputs*, **332** original OST experimental records, and **39** Milano experimental records. This study uses exactly **20 original, physically measured pure-butane records**, restricted to:

- `source == "Experimental OST (Purdue 2024 Natural)"`
- `refrigerant.lower() == "butane"` (mixtures and propane are excluded)
- one exact original OST Bock reciprocating compressor machine identity, one reported electrical frequency (48.33 Hz); **this is not a shaft RPM**.
- Positive measured absolute suction and discharge pressures, suction temperature, observed `eta_is,electric` and observed `eta_vol` in the physically admissible (0,1] interval.

This is a **single published experimental campaign** at one supply frequency, not an independent machine test campaign with known independent holdout runs. Model parameters do not come from the other 31,702 synthetic compressor records. No source rows are redistributed in artifacts.

## Frozen holdout protocol, declared before reading results

1. Group records by `(compressor, campaign, exact reported suction P, exact reported discharge P, suction T, supply frequency)`. Replicates at the same physical operating condition must stay together, so fitting and holdout cannot share operating coordinates.
2. Sort unique conditions using **input-only** `log(p_dis/p_suc)` (pressure ratio). Partition unique conditions into **five equal-count pressure-ratio bins**. Reserve **one condition group from each bin** with the smallest SHA-256 digest of the frozen seed `CarnotBatteryLab-M1.7-v1-precommitted-condition-quintile` and a canonical condition key.
3. Train exclusively on remaining operating-condition groups (nominal 15 observations); evaluate all observations from the five reserved groups. The random-seeming digest is fixed and independent of measured efficiencies; reordering the input file or changing efficiency labels cannot change the assignment.
4. Fix **two training-only exploratory surrogate models**: `eta_hat = mean_train(eta) + b[ln(PR) − mean_train(ln(PR))]` with `b = cov_sum / [sum((lnPR−mean_lnPR)^2)+0.20]`. The `0.20` ridge regularization was declared in the script, not tuned to the holdouts. Fit one slope for `eta_is,electric`, one for `eta_vol`, both using training data only. Compare against the training-only mean baselines.
5. Predict the original **zero-fit 0.68894 electrical efficiency hypothesis** on every reserved experimental point. Report MAE, RMSE, mean prediction-minus-measurement bias and maximum absolute error for the fixed hypothesis, training mean, and exploratory pressure-ratio surrogate. For volumetric efficiency, compare only training mean and exploratory slope because the existing M1.4 cycle has **no independent volumetric-efficiency hypothesis**.
6. Compute a separate **three-dimensional convex-hull support test** with source operating coordinates `(p_suc,T_suc,log(PR))`, using nonnegative barycentric weights (SciPy HiGHS). Evaluate MAE for the subset *inside* training support separately from holdouts outside the training hull. **Do not claim interpolation validity for the outside-hull subset.** This support test uses no observed efficiencies.
7. Obtain independent property-level diagnostic `delta_h_is=CoolProp(HEOS::n-Butane, p_suc,T_suc,p_dis)`; compute **ideal compression specific enthalpy**, **electric specific work IMPLIED by measured overall eta**, and **electric specific work IMPLIED by the fixed reference hypothesis**. These are not measured shaft work, measured motor power or evidence for the 1 MW heat-pump cycle.

The fixed 0.68894 hypothesis has a pre-declared *exploratory accuracy screen* of **MAE ≤0.05 in absolute efficiency units** over the full reserved set. Passing this would establish consistency only over this **other, low-pressure OST laboratory compressor campaign**, not at our high-pressure R600 H-REF service or any new compressor machine. Failing it would show the assumed reference electrical efficiency is **not corroborated across these independent measured off-target conditions**, without proving the assumed efficiency is wrong at the original target.

The fitted two-parameter ridge curve is **exploratory**: even if it yields a smaller holdout error, the 20-observation sample, one frequency, same experimental campaign, and possible source measurement correlations mean the performance estimate is preliminary. We do **not** use the five heldout outcomes to choose polynomial degree, regularization, covariates, sample composition, H-REF compressor efficiency or release-gate thresholds. No before/after retraining is allowed on the reserved observations in the frozen M1.7 evaluation.

## Reproduced results — pinned source CSV, CI 16 November 2026

The exact original Zenodo MD5 was independently verified before parsing. **20 real OST pure-butane observations** were selected; **15** entered the training group and **5** were reserved using the pressure-ratio-bin and SHA-256 input-condition protocol frozen above. No observed `eta_is` or `eta_vol` informed point allocation or ridge regularization.

| Experimentally reserved response/approach | N | MAE, absolute efficiency | RMSE |
|---|---:|---:|---:|
| Original zero-fit reference `eta_is,electric=0.68894` | 5 | **0.066520** | **0.102252** |
| Exploratory pressure-ratio ridge, **overall electrical η** | 5 | **0.087995** | **0.092751** |
| Training-only constant volumetric η | 5 | **0.098420** | **0.139053** |
| Exploratory pressure-ratio ridge, **volumetric η** | 5 | **0.040943** | **0.047854** |

For the zero-fit electrical efficiency reference, the prediction-minus-measurement **bias is +0.066520** and maximum absolute error is **0.216340**. The predeclared **MAE ≤0.05** exploratory consistency screen is therefore **FAILED**, not quietly weakened post hoc. The fitted electrical-efficiency ridge performs worse on MAE than the zero-fit model (though better on RMSE), so it is **not recommended** for use as a replacement R600 performance map. The volumetric-efficiency fit reduces heldout MAE relative to the training-only constant, but does not establish accurate volumetric flow or rated speed/pressure coverage.

Most critically, only **1/5 withheld experimental points** lies within the **three-dimensional training pressure/temperature/log-pressure-ratio convex hull**; **4/5 are beyond it**. Therefore these scores are primarily small-sample **out-of-support stress tests**, not demonstrated interior interpolation predictive accuracy. We **do not change the reserved split after seeing this result** or select a more flattering subset. An independent experimental campaign with enough dense map coverage and additional prespecified holdout points is necessary for robust in-envelope model validation.

At the original target, M1.4 R600 numerical suction is **719,909.92 Pa = 7.1991 bar**, above the available pure-butane experimental suction maximum **5.1494 bar**. Five high-side choices **4.0–6.0 MPa = 40–60 bar** all exceed the OST experimental discharge maximum **24.9463 bar**. Every nominal target case fails even marginal-pressure-range overlap, independently of the exploratory efficiency fits. This is a **dataset/machine noncoverage result**, not proof that natural-fluid heat pumps cannot meet H-REF.

The JSON artifact preserves exact source/model SHA-256, opaque hashes of training and reserved operating-condition identities, training-only model coefficients, original fixed baseline, aggregate error metrics, EOS ideal/specific-work diagnostics and explicit nonqualification fields. It contains **no individual original measured rows**. Neither error bars nor measured sensor uncertainties were invented.

## H-REF equipment compatibility remains blocked

The M1.6 physical source audit established measured OST pure-butane suction range **1.4813–5.1494 bar**, discharge **2.884–24.9463 bar**, suction 25.15–86.88°C, pressure ratios 1.947–12.002. The numerical R600 H-REF 80→70°C evaporator requires 65°C refrigeration evaporation; the M1.4 scan uses **40–60 bar high-side** and a higher suction pressure than the 20-point measured OST range. These independent experimental points do **not** include a matched machine operating envelope for any of our five numerical R600 high-side choices. Moreover the lab's Bock compressor geometry, capacity, control, speed and temperature limitations cannot be changed by scaling its efficiency alone to 1 MW.

The code reports source/target marginal coordinate range overlap **for awareness** and never claims 4D interpolation or a manufacturer map. M1.5 real map acceptance demands measured compressor mass flow, actual volumetric flow, speed lines, shaft power, discharge temperature, uncertainties, machine safety limits and point-specific provenance, which are **not** provided here. The experimental `eta_vol` is an independent measured response but does not supply a manufacturer-displacement or full geometric volumetric-flow capacity map without separate operating speed, geometry and validated motor coupling.

## Reproduction and claims

```bash
python -m pip install -e ".[physics,test]"
python -m pytest tests/test_m1_7_r600_offdesign_holdout.py -v
python scripts/run_m1_compressor_map_requirements.py \
  --output results/m1_compressor_map_requirements_80_70_to_110_150.json
python scripts/run_m1_7_r600_offdesign_validation.py \
  --download \
  --requirements results/m1_compressor_map_requirements_80_70_to_110_150.json \
  --output results/m1_7_r600_reserved_experimental_holdout_validation.json
```

The dedicated workflow `.github/workflows/m1-7-r600-original-measurements-reserved-holdout.yml` re-downloads and verifies the **original source MD5**; runs adversarial offline tests that swap labels/contaminate data/inject duplicate conditions and validate EOS; regenerates M1.4 independent demands; then publishes a **source-SHA-256, condition-hash, aggregate-metrics-only JSON**. The CSV itself is never committed.

**Status remains open for hardware qualification:** the public data support an independent, out-of-sample **off-design test of one electrical-efficiency hypothesis and an exploratory efficiency predictor**, not a measured complete compressor map; the original 80→70°C source and 110→150°C 1 MW process, dynamic TES charging, physical process heat exchanger, and industrial round-trip efficiency remain unvalidated.
