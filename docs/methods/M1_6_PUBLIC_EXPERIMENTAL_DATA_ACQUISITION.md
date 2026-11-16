# M1.6 — External compressor experiments and original Carnot-battery HP/TES data

**Evidence status: acquisition and independent model-validation triage, not qualified R718/R600 compressor hardware.** The exact H-REF service is **80→70°C waste-source liquid; 110→150°C industrial process liquid, 1 MW gross heat**. M1.4 calculated stage P/T/flow demands; M1.5 implemented an independent measured compressor-map eligibility test. This work obtains publicly available primary measurements, distinguishes them from synthetic data, checks immutable source checksums and reports why the original case is **still unqualified**.

## Dataset A — independent OST Buchs butane compressor measurements

Original record: **Widmaier, Brendel, Roskosch, Bardow & Casati (2026)**, [DOI 10.5281/zenodo.17599603](https://doi.org/10.5281/zenodo.17599603). [CSV download](https://zenodo.org/records/17599603/files/compressor_performance_data.csv?download=1). [Detailed source README](https://zenodo.org/records/17599603/files/ZENODO_README.md?download=1).

The published CSV's archival MD5 is **`680dd400cfb39b2fa0a1dd22a09c731f`**; its actual SHA-256 is generated at download. The source record explicitly states **CC BY 4.0**. It contains original measured campaigns at **OST Buchs** and **Politecnico di Milano**, alongside **synthetic outputs** from manufacturer DIN EN 12900 polynomial coefficients. The source README gives all three origins, including important caveats about mixtures and efficiency meter boundaries. It is scientifically invalid to treat the entire collection of ~32,000 points as physical measurements or to fit manufacturer polynomials as held-out experimental truth.

The original field `source` is used **row-by-row** to separate `Experimental OST`, `Experimental Milano`, `Bitzer EN12900` and `Bock EN12900`. Only **pure measured butane** (`refrigerant == butane`) from the OST Purdue-2024 natural-fluid experimental campaign is used in the R600 evidence comparison. Mixed butane/propane measurements are separately present but **not** silently treated as pure R600. The aggregate report includes verified counts, actual experimental pressure/temperature/ratio ranges, electrical isentropic and volumetric efficiency ranges and the compressor identifier.

### Independently reproduced archive result (GitHub Actions, 16 Nov 2026)

The exact published MD5 verified successfully: **32,073 actual CSV records**. Source-class counts were **31,702 manufacturer-polynomial-generated synthetic observations**, **332 independent OST experimental records**, and **39 independent Politecnico di Milano experimental records**. Exactly **20 physically measured pure-butane observations** originate from the OST subset.

Measured pure-butane ranges were **1.4813–5.1494 bar suction**, **2.884–24.9463 bar discharge**, **25.15–86.88°C suction**, **1.947–12.002 stage pressure ratio**, **0.3334–0.6819 overall *electric* isentropic efficiency**, and **0.4747–0.887 volumetric efficiency**. The source's electrical frequency is **48.33 Hz at every measured pure-butane point**; it is not an independently measured compressor RPM or a speed map.

For the five M1.4 R600 scan candidates (4.0, 4.5, 5.0, 5.5 and 6.0 MPa high-side), **none** has an independent OST measurement within ±5% of **both** exact inlet and outlet pressure and ±5 K of the numerical suction temperature. Most tellingly, the test compressor's maximum recorded suction pressure is **5.1494 bar**, while the M1.4 target R600 evaporation is 65°C (a substantially higher suction pressure), and measured discharge pressures reach only **24.9463 bar**. This is **not** a general proof no commercially suitable R600 compressor exists; it is a clear *noncoverage finding for this specific independently published instrumented compressor*.

The original landing-page count and README description are slightly inconsistent. Use the checksum-verified source CSV row count **32,073** rather than propagating an unverified rounded/contradictory dataset count. No publication-derived data are silently treated as equal to experimental observations.

### What this CSV actually measures / omits

Available: experimental **absolute** suction/discharge pressure (bar, source units), suction temperature (°C), **overall electricity-based** isentropic efficiency, volumetric efficiency, electrical drive frequency (Hz), cylinder geometry, compressor identity and provenance/campaign. The source README defines `eta_is = m_dot Δh_is / P_elec`; this **is not automatically** the R600 numerical model's **shaft isentropic efficiency**. Supply frequency `f_elec_Hz` **is not shaft rpm** unless motor poles, gear ratio or measured encoder speed are independently documented.

Not available as original CSV columns: measured refrigerant mass flow, measured actual suction volumetric flow, compressor **shaft** work, measured discharge temperature, calibration uncertainty per sample, verified rated compressor map boundaries, independent holdout campaign split or matching 1 MW train. **Do not derive absent fields from other variables and present them as independent measurements.** In particular, hypothetical piston geometry × frequency and assumed pole pairs cannot substitute for measured speed or source flow.

M1.6 produces `results/m1_6_public_r600_real_measurements_range_audit.json` through GitHub Actions. It tests every **M1.4 R600 4–6 MPa high-side candidate's** input suction pressure, discharge pressure and suction temperature against actual measured pure-butane points. A count within **±5% on each pressure and ±5 K on suction temperature** is *only* a transparent preliminary nearest-condition count. It is **not** a 4D convex-hull or complete manufacturer's machine envelope. No count may set M1.5 `machine_hardware_qualified=true`. A nominal R600 screen point with a far higher suction pressure than the OST measurements cannot become validated through the similarity of one discharge-pressure dimension.

## Dataset B — independent Carnot-battery heat-pump and TES experiments

Original dataset: **Schmeing, Welp & Atakan**, University of Duisburg-Essen, published Feb 2026, [DOI 10.5281/zenodo.18712882](https://doi.org/10.5281/zenodo.18712882), [36.1 MB archive](https://zenodo.org/records/18712882/files/data.zip?download=1), archival MD5 **`d17bf8b134977f4672c1ec22f085f0ea`**.

The source describes **17 experimental HP + two-tank sensible TES runs**, with varying propane, butane and propane/pentane mixtures and time series of temperature, pressure, flow and electrical compressor demand; it includes time-averaged performance and compressor modelling material. This is independently measured evidence of **thermal-storage coupling**, but the physical apparatus differs from our **gas/rock packed bed** and 1 MW liquid process case. Do not cross-map two-tank liquid storage to a gas/rock regenerator or claim its compressor measurements certify our R600 IHX-less or R718 stage topology.

The file is openly listed on Zenodo, but its landing-page licence field is not clearly reported; **verify reuse/redistribution rights before publishing raw rows or models**. M1.6 only downloads and verifies the checksum and lists safe archive metadata/model/README file paths and types. It does not extract files to disk, redistribute sensor histories, infer column units or fit an experimental compressor map. After inspection, a separate reserved-run validation protocol can be designed **only after reading actual README field definitions and experiment controls**.

### Independently reproduced archive metadata (GitHub Actions, 16 Nov 2026)

The 36.1 MB original archive also passed its publisher MD5 and contains **184 ZIP entries**, including **39 CSVs, 11 Python source files, six spreadsheets and 19 YAML files**. A bounded, read-only schema inventory found **19 CSVs with extractable column headers**. It identified independent n-butane experimental Bitzer data logs for **experiments 026–028** (dated 9–10 October 2025) containing explicitly labelled **compressor speed, motor power, frequency, refrigerant, low/high absolute pressure and compressor control fields**. There are separately included compressor performance/model CSVs with headings for inlet/outlet P/T and compressor efficiencies. These files are different from an independently published, traceable manufacturer machine map; sensor calibration, measurement meter boundaries, and reliable steady-state selection remain unreviewed.

**Important rights warning:** an included compressor-model README contains explicit language that its underlying model **must not be made public**. Therefore the public archive's availability is **not** permission to copy or republish the proprietary model code. Our inventory detects and flags this warning, marks model-code reuse as blocked and publishes **only file names and column headers**, never the original dataset contents or model implementation. Before developing any derived or redistributed model, obtain rights clarification from the original authors.

## Dataset C — SINTEF steam R718 compressor map *figures*, not complete raw map

**Verpe et al. 2020**, [DOI 10.18462/iir.gl.2020.1019](https://doi.org/10.18462/iir.gl.2020.1019), [full preprint](https://sintef.brage.unit.no/sintef-xmlui/bitstream/handle/11250/2757327/Verpe2020eeo_akseptert.pdf?sequence=1). This publication **does** explicitly state that two turbo-compressor performance maps were constructed on a 500 kW test rig; measured peak first-stage ratio 2.4 and eta 0.67, second-stage ratio 2.0 and eta 0.77. However, its source is around atmospheric inlet steam, not 65°C low-pressure R718 evaporation / 25 kPa suction; compressed steam was desuperheated by water injection rather than our assumed external intercooler. **Figure curves without original digital readings, point uncertainty, exact machine/energy meter boundary and operating rights are not independently qualified M1.5 map packages.** Request original tabular measurements and actual pressure/speed/volumetric coordinates from the study authors.

## Other relevant open data — not substitutes for our natural-fluid machine

- **DLR CoBra**, [DOI 10.5281/zenodo.15862451](https://doi.org/10.5281/zenodo.15862451): 1 Hz compressor flow/pressure/speed and thermal process history for a **Brayton** heat-pump demonstrator; useful independent transient compressor data, **not R718 or R600 vapour compression**. The repository also links a **2026-11-10 heat sink flow-sensor correction**, which must be propagated before using those flow histories.
- **University of Bayreuth**, [DOI 10.17632/56m3dd55zf.1](https://doi.org/10.17632/56m3dd55zf.1), 2026: independently measured R1233zd(E) off-design HTHP compressor and heat exchanger data; a method-validation comparator but **not a natural refrigerant** or full original target.
- **FlexGeo University of Liège**, [DOI 10.5281/zenodo.20845165](https://doi.org/10.5281/zenodo.20845165): actual reversible HP/ORC Carnot-battery experiment, but different fluid/operating envelope and two parallel fixed-speed scroll compressors.
- **FlexGeo TUM**, [DOI 10.5281/zenodo.20830460](https://doi.org/10.5281/zenodo.20830460): original twin-screw reversible ORC/heat-pump experiments; suitable for later cycle validation if working fluid, equipment, and measurement coverage match.

## Reproduction and checks

```bash
python -m pip install -e ".[physics,test]"
python -m pytest tests/test_m1_6_public_data_acquisition.py tests/test_m1_6_ude_archive.py -v
python scripts/run_m1_compressor_map_requirements.py \
  --output results/m1_compressor_map_requirements_80_70_to_110_150.json
python scripts/audit_public_r600_compressor_measurements.py \
  --requirements results/m1_compressor_map_requirements_80_70_to_110_150.json \
  --download --output results/m1_6_public_r600_real_measurements_range_audit.json
python scripts/audit_ude_carnot_hp_tes_archive.py \
  --download --output results/m1_6_ude_carnot_hp_tes_archive_inventory.json
```

The M1.6 GitHub Actions workflow creates **small provenance-hashed aggregate reports only**. An external network outage or source archive being moved is a **retrieval failure**, not absence of experimental support or a model-validation result. The primary CSV's checksum is mandatory. The separate larger archive job is explicitly marked best-effort; its success/failure must be inspected and cannot be assumed from overall workflow success. The source page's description and README give different overall row counts; actual CSV count wins when the pinned checksum matches.

## Scientifically legitimate next use

1. **R600 independent off-target efficiency sanity:** compare *electrically defined* isentropic and volumetric efficiency curves against a separately defined corresponding reference model at **the OST measured points**, splitting fitting and holdout points by experimental campaign. Avoid claiming calibration of the 80→70°C high-pressure compressor or converting overall electricity efficiency to assumed shaft efficiency.
2. **UDE HP/TES:** inspect verified archive documentation for actual compressor inputs, storage temperature histories, reference control cases, sampling interval and uncertainty; reserve whole runs from tuning before any quantitative validation. The published two-tank storage cannot validate a packed-bed thermocline.
3. **Data request:** obtain original full multipoint stage compressor maps (R718 wet/dry steam and natural R600), including speed, inlet/outlet pressure/temp, mass/volume flow, shaft and electrical work, discharge temp, manufacturer limits and uncertainty. Only these data permit meaningful direct M1.5 eligibility; the present literature and off-target datasets do not.

**Release gate remains blocked:** no exact 1 MW 80→70°C source / 110→150°C process heat pump machine map, no packed-bed measured breakthrough/pressure-loss agreement, no complete process liquid HX and no matched service/rated round-trip efficiency.
