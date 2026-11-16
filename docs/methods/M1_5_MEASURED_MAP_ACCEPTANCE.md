# M1.5 — Measured compressor-map acceptance framework (fail closed)

**Scientific status:** **executable map-data acceptance framework, not qualified hardware**. This increment implements the acceptance test that real compressor suppliers/laboratories must be able to satisfy. As of this release, **no independently authenticated map is present** for the original H-REF heat-source and process service. The source-controlled no-map report must return `NO_MEASURED_COMPRESSOR_MAPS_SUPPLIED` and `manufacturer_certified_compressor_envelopes=false`.

## Purpose and fixed research contract

H-REF requires a **liquid** source at 80→70°C and **liquid** process service at 110→150°C, with nominal **1 MW process heat**. The assumed 25 kg/s source cap, 5 K approaches, R718 and R600 cycle topology, partial auxiliaries, and M1.4 isentropic efficiencies are not measured plant equipment.

M1.4 calculates each refrigeration compressor stage's **model demand** at the direct 1 MW process point and for each completed TES-responsive R718 charging step. M1.5 asks whether separately supplied measured maps genuinely support those demand coordinates. The model output **never** becomes source data for its own acceptance test.

## Dataset contract and machine identity

An optional external JSON dataset, **not bundled as if measured**, uses `schema: m1.5-measured-map-v1` and `maps: [...]`. A single `maps` entry represents **one specific physical compressor stage**. Every entry contains:

- `evidence`: `evidence_class` (`SYNTHETIC_TEST_FIXTURE`, `SUPPLIER_REPORTED_UNREVIEWED`, `MEASURED_UNREVIEWED`, `MEASURED_REVIEW_ASSERTED`); `manufacturer_or_laboratory`; `machine_id`; `train_id`; exact `topology_id`; `stage`; `refrigerant`; source PDF/CSV `source_document_url`, hexadecimal `source_document_sha256`, traceable `calibration_traceability_reference`, reserved `heldout_test_campaign_id`, and independent `independent_review_reference`.
- `rated_limits`: documented minimum/maximum rpm, maximum absolute discharge pressure in Pa, maximum stage pressure ratio, maximum discharge temperature °C, and maximum shaft power W. These **must come from equipment documentation**, never from the maximum of the provided operating-point sample.
- `points`: each point has an independent `point_id`, `role` equal to `fit` or `holdout`, `speed_rpm`, `suction_pressure_Pa`, `suction_temperature_C`, `stage_pressure_ratio`, `suction_volumetric_flow_m3_s`, `refrigerant_mass_flow_kg_s`, `shaft_power_W`, `discharge_temperature_C`, `isentropic_efficiency`, `stability_confirmed`, and positive standard uncertainties for gas mass flow, shaft power and discharge temperature. **All pressures are absolute. All volumes are actual suction volumes, not normal m³/h.**

The origin label in a supplied JSON is an **assertion**, not independently validated authenticity. The framework checks that provenance fields are present and syntactically plausible; it cannot authenticate a PDF's contents, calibration certificate, signature or operating clearance. The report explicitly retains `source_documents_digest_checked_against_original=false` and `manufacturer_certified_compressor_envelopes=false`, even for a `MEASURED_REVIEW_ASSERTED` record.

## Physics and geometry checks

For every compressor-stage demand, define the four-dimensional operating coordinate

\[
\mathbf{x}=(p_{suction},T_{suction},p_{discharge}/p_{suction},\dot V_{suction}).
\]

**A single declared and measured speed line at a time** is used. Fit points at that exact rpm must positively bracket the requested coordinate by a nonnegative convex combination (a linear-programming feasibility check with weights summing to 1). Extrapolation on even one coordinate fails. There is **no interpolation across rpm**, no fitting across different manufacturers, stages or topologies, and no use of holdout data to construct the interpolation.

Fit observations must contain at least three points, the map must contain at least two **unique, withheld** operating-coordinate observations distinct from all fit coordinates, and **every speed line used for acceptance must have at least two holdouts of its own**. The withheld observations must themselves be interpolable from the fit operating range. Every withheld point is compared against its prediction for three output variables: measured mass flow, measured shaft power, and measured discharge temperature. Failure of any holdout fails the map support check.

For every **declared measured** R718-water or R600-butane pure-fluid stage point, an additional property-level check independently recomputes `rho(p_s,T_s)`, `m_dot = rho × V_dot_suction`, the isentropic enthalpy increment, shaft-derived isentropic efficiency and EOS-based discharge temperature. A violation of the declared model/measurement uncertainties rejects the candidate map. **Synthetic fixtures bypass the real-fluid physical-state check only to test the acceptance algorithm, and are permanently labeled synthetic.** Mixtures or unsupported refrigerant topologies require a separately validated EOS implementation rather than being blindly accepted. This EOS consistency check does not verify the source's authenticity or substitute for laboratory validation.

The default **declared screening thresholds**, not data-fitted uncertainties or industrial acceptance standards, are:

| Quantity | Default model / map comparison | Held-out measured comparison |
|---|---:|---|
| Refrigerant mass flow | ≤5% relative discrepancy | Must meet **both** 5% and 3×reported relative standard uncertainty |
| Compressor shaft power | ≤5% relative discrepancy | Must meet **both** 5% and 3×reported relative standard uncertainty |
| Discharge temperature | ≤5 K absolute discrepancy | Must meet **both** 5 K and 3×reported standard uncertainty |

Before screening, maps with declared standard measurement uncertainties greater than **3%** for mass flow or shaft power or **2 K** for discharge temperature are also rejected. These are provisional evidence-quality requirements, not universal instrumentation standards. Larger claimed uncertainties **cannot** relax the 5%/5 K cap.

The match is also rejected if the model or interpolated output exceeds a declared machine limit for rpm, discharge pressure, pressure ratio, discharge temperature or shaft power. A map may therefore fail because of **no matching machine**, **no holdout validation**, **model outside measured convex hull**, **model disagreement**, or **machine ratings exceeded**. This is not a compressor design optimizer. The chosen 5%/5 K thresholds are transparent, provisional research rules and **not** a certification or an uncertainty interval validated for all technologies.

### What even a numerical pass does NOT mean

A sampled interior point merely establishes that submitted operating-coordinate data **locally support a cycle hypothesis under the chosen tolerances**. The following remain strictly false:

- Independent software authentication of manufacturer/source document or laboratory calibration.
- Industrial compressor certification, machine-train interstage mass/pressure matching, actual motor/gearbox and lubrication qualification.
- Surge/choke margin between sampled points, safe rpm ramp and coordinated two-stage control under changing TES return temperatures.
- Measured isentropic efficiency/shaft duty validation of the **complete** R718/R600 cycle, actual installed HX and process-water delivery.
- Part-load and startup performance, trained pressure-loss/thermal histories, experimentally validated TES, and electricity/thermal system RTE or architecture ranking.

The R718 32-step **charging termination** under the existing model must remain a failure even if all previously completed steps are map-supported. A map is not permission to increase the original assumed R718 350°C discharge guard or 5:1 stage-ratio assumption.

## Exact topology segregation

- `H_REF_R718_TWO_STAGE_INTERCOOLED` / `R718_TWO_STAGE_WITH_EXTERNAL_INTERCOOLER` / `R718 water`, stages **`stage1` and `stage2`**. The R718 M1.4 direct 1 MW operating point and separate **2, 16 and 32-step** TES-responsive charge trajectories are evaluated. **Both stages** must be supported at **every completed time point**, and incomplete charging cannot pass.
- `H_REF_R600_TRANSCRITICAL_NO_IHX` / `R600_SINGLE_STAGE_TRANSCRITICAL_NO_IHX` / `R600 n-butane`, stage **`single_stage`**. All M1.4 finite-HX-passing high-pressure scan points are evaluated separately. The modeled no-IHX compressor is **not equivalent** to an experimental IHX/suction-gas-cooled R600 package.
- Published R718 different-rig nominal ratios and separately observed stage maxima are **never substituted for a machine's speed line**. The SGH165 hybrid/steam comparator is **not** an exact-source/target process-liquid map.

## Reproduction

First generate the exact M1.4 real-fluid demand dossier:

```bash
python -m pip install -e ".[physics,test]"
python scripts/run_m1_compressor_map_requirements.py \
  --output results/m1_compressor_map_requirements_80_70_to_110_150.json
python -m pytest tests/test_m1_5_measured_map_gate.py -v
python scripts/run_m1_5_map_acceptance.py \
  --requirements results/m1_compressor_map_requirements_80_70_to_110_150.json \
  --output results/m1_5_independent_compressor_map_acceptance.json
```

**With an independently supplied map package:**

```bash
python scripts/run_m1_5_map_acceptance.py \
  --requirements results/m1_compressor_map_requirements_80_70_to_110_150.json \
  --map-package path/to/private_verified_compressor_maps.json \
  --output results/private_m1_5_preliminary_acceptance.json
```

Do not commit confidential manufacturer maps to a public repository. For a real dataset, first verify supplier rights, protect raw point files as required, record source hashes and calibration traceability independently, and use a private workspace. The generated JSON should also be treated as potentially confidential because it can contain measured-map machine identifiers and operating-point support results.

**CI evidence:** `.github/workflows/m1-5-independent-compressor-map-acceptance.yml` runs synthetic **positive** convex-hull and independent-holdout tests; negative tests for off-hull queries, above-rated operation, mismatched topology/stage, absent/stale evidence, withheld-point contamination, missing holdouts on a specific rpm line, physically inconsistent declared measured suction points, and incomplete TES charging; recreates the real-fluid M1.4 dossier; then uploads an explicit *no real measured maps supplied* report. No synthetic test or literature point is promoted to authentic machine qualification.

## M1.5 acceptance and remaining gate

**Implemented:** source schema, machine identity/topology protection, explicit rated limits and uncertainty, interpolation constrained to measured fixed-speed interiors, independent withheld tests, mass/shaft/discharge consistency, full stage trajectory screening, no-real-map negative provenance and deterministic CI.

**Blocked:** actual original, traceable, independently auditable compressor maps for the proposed 80→70°C source and 110→150°C process **across the complete dynamic operating envelope**; measured compressor train and process liquid-HX performance at a legitimate 1 MW plant. This data gap is distinct from a software defect and cannot be resolved by changing a numerical guard.
