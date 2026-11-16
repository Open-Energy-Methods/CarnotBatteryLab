# M1.9 — Primary manufacturer/experimental compressor-map acquisition dossier

**Status (16 November 2026): `NO_TARGET_MEASURED_MAP_ACQUIRED`.** This is a source-referenced, executable **negative component compatibility screen and targeted independent-data acquisition plan**, not actual machine qualification or a newly obtained full measured map. No manufacturer or author has been contacted by the code; no external data response, permission or commercial offer is asserted.

## Exact H-REF process service and M1.4 model-dependent requirements

- Assumed waste-source **80→70°C liquid** with finite heat availability and 5 K terminal pinch; proposed industrial process load **110→150°C liquid**, **1 MW gross**.
- **R600 n-butane** alternative: assumed single-stage transcritical compression, **without the prototype's internal heat exchanger or suction-gas-cooled compressor model**. M1.4 demands approximately **7.20 bar absolute, 75°C** compressor suction; **40, 45, 50, 55, 60 bar absolute** discharge; stage ratio approximately **5.56–8.33**; suction actual volume roughly **0.201–0.213 m³/s**, and calculated discharge **163–188°C**. None are manufacturer-certified ratings. Actual shaft speed, dimensional capacity, lubricating oil and cooling protection remain unestablished.
- **R718 water** direct two-stage/intercooled research hypothesis: stage 1 suction about **25.0 kPa absolute at 75°C**, stage 2 suction about **116.7 kPa absolute at 114°C**. Demand **stage ratio ≈4.659 individually**, **2.563 and 0.606 m³/s** actual inlet volume, and idealized model discharge ~**283°C and 339°C**, respectively. Original 5:1 numerical ratio ceiling and 350°C temperature guard are **assumed computational limits, not equipment limits**. Matching only the direct nominal point would not cover TES-responsive charging states.

## Manufacturer primary source: Sabroe UniSAB 4 controller engineering guide

Johnson Controls Sabroe, *UniSAB 4 Engineering Guide*, Rev. **005**, Doc **IR-SAB-ENG-0001**, [Notes item 30](https://docs.johnsoncontrols.com/industrialrefrigeration/r/Sabroe/en-US/UniSAB-4-Engineering-Guide/005/Warnings-and-shutdowns/Analog-warnings-and-shutdowns/Notes?contentId=ED6PJOpwsqeb9wnpJtanEA):

- For **HPC/HPO compressors operating with R600**, the **maximum configurable high-discharge warning limit** is listed as **35.5 bar** and **high-discharge shutdown limit** **36.0 bar**. Do not conflate these **controller settings** with mechanically rated pressure, approved refrigerant, thermodynamic operating envelope, pressure vessel design, or measured machine speed lines.
- The same note separately describes **HPX units released for 65.0 bar design pressure**, with higher **general high-discharge warning/shutdown settings** of **57.0/57.5 bar**, respectively. **It does not prove that this variant is approved for R600, 150°C process heat, the given oil/temperature limits or high-side compressor performance.** Do not transfer the HPX generic number to HPC/HPO or to a hypothetical HPX-R600 train.
- The cited note displays **"bar" without independently clarifying whether its control setpoints are gauge or absolute**. The executable screen evaluates both interpretations and uses *nominal atmospheric pressure 1.01325 bar solely for a transparent gauge-to-absolute sensitivity*, not as a claimed manufacturer calibration. Since every modelled **40–60 bara** R600 case exceeds **both 36 bara and 36 barg ≈37.013 bara**, **5/5 are robustly incompatible with the documented HPC/HPO R600 UniSAB high-discharge shutdown setting**. This is a machine/controller-specific negative finding, **not proof all R600 transcritical heat pumps are infeasible**. Never increase or bypass a safety shutdown to make a numerical screen pass.

**Unresolved**: manufacturer-confirmed pressure reference, exact HPC/HPO/HPX model and release, R600 compatibility, pressure vessel design class, A3 safety and charge, complete speed-flow/P-T-enthalpy map, high discharge temperature/oil stability and cooling limitations, certified shaft/electric input, VSD and process control. [Manufacturer contact route](https://www.sabroe.com/contact-us). A vendor datasheet, sales brochure, or controller guide without measurements cannot satisfy M1.5 on its own.

## R718 evidence is measured, but at different stage conditions

- **Verpe, Schlemminger, Bantle & Ahrens (2020)**, [DOI 10.18462/iir.gl.2020.1019](https://doi.org/10.18462/iir.gl.2020.1019), original SINTEF ~500 kW steam test rig: **measured stage 1 peak pressure ratio 2.4, stage 2 peak 2.0**, with efficiencies up to 67% and 77%. The maxima are **not necessarily simultaneous**, and the rig uses roughly atmospheric inlet steam with water-injection desuperheating and different hardware/topology. Our model demands **4.659 / 4.659** at ~0.25 and 1.17 bara suction, above both of these **specific experimental machine** maxima. This rejects treating that **particular rig** as proof of our exact stage design. It does **not** establish a universal pressure-ratio ceiling for R718.
- **Dowdell, Moen, Rotan & Schlemminger (2024)**, [DOI 10.18462/iir.gl2024.1286](https://doi.org/10.18462/iir.gl2024.1286), measured two-stage R718 solar-assisted demonstrator: first-stage suction **1–2 bara**, reported maximum second-stage discharge **5.3 bara**, permitting ~154°C condensation. Our first-stage suction is **0.25 bara**. Despite similar high sink temperature, **source/suction state does not overlap**, and the published abstract does not provide the full stage speed/volume/stability maps, uncertainty, interstage injection losses or original 1 MW heat-transfer capability.

**Consequence:** No original complete measured R718 maps were retrieved that jointly support **25 kPa suction**, **4.66 pressure ratio per stage**, requested actual flow/speed or verified simultaneous TES-responsive charging. Claims of a 150°C steam outlet at 1–2 bara suction cannot be silently promoted to positive physical performance at our *subatmospheric* source condition.

## R600 experimental leads: distinguish candidate data from exact map

- **Verdnik & Rieberer (2022)**, [DOI 10.1016/j.ijrefrig.2022.05.010](https://doi.org/10.1016/j.ijrefrig.2022.05.010): real measured **R600 transcritical** prototype, reported 160°C sink outlet and ~24.2 kW thermal, COP ~3.1 from a **60°C inlet** heat source; includes **IHX, suction-gas-cooled compressor**. TU Graz development document [project F39100](https://online.tugraz.at/tug_online/fdb_detail.ansicht?cvfanr=F39100&cvorgnr=2267&sprache=2) states development ambition of **up to 50 bar** for a compressor capable of temperatures up to **170°C**. A research goal or paper's nominal COP is **not an independent speed/rated temperature/mass-flow map** and is not necessarily measured at our 80→70°C source and 110→150°C liquid service. This is the **most relevant research-team request** for a real 40–50 bar R600 test machine.
- **Benkert et al. (2025/2026)**, [DOI 10.1002/cite.70046](https://doi.org/10.1002/cite.70046): measured R600 bench with **Sabroe HPX 704**, swept suction 111 m³/h at full 1500 rpm, 31 kW motor, heat-output up to **120°C** and thermal capacity up to **125 kW**, which need not occur simultaneously. Source boundary differs, and 120°C **does not** support 150°C H-REF service.
- **Brendel et al. (2026)**, [DOI 10.1016/j.ijrefrig.2025.11.012](https://doi.org/10.1016/j.ijrefrig.2025.11.012): **439 real test points**, original 2DES-3Y reciprocating machine, seven pure fluids and many mixtures. **Important discovery:** inspection of the actual published **Table 1** shows **NO pure R600 entry**. Its overall all-refrigerant suction range of **41–922 kPa** is therefore **not** a pure-R600 operating map. The source might be useful for methods and calibration comparisons, **not for satisfying our natural-butane M1.5 boundary**.
- M1.6 and M1.7 **OST** separately found **20 actual pure butane measured rows** from another campaign, and M1.8 **UDE** reports six genuine butane experiment means; neither experimental machine provides the target **40–60 bara discharge** or a complete SHA-verified stage map with measured shaft power and independent heldouts. Keep the exact original five OST reserved-condition hashes and results unchanged.

## Actual data access route — preaddressed source inquiries, NOT SENT

Verified public professional contacts:

| Priority | Source | Recipient or official route | Data request |
|---|---|---|---|
| 1 | TU Graz measured 160°C R600 research | `manuel.verdnik@tugraz.at`; `rene.rieberer@tugraz.at` ([university](https://online.tugraz.at/tug_online/fdb_detail.ansicht?cvfanr=F60024&cvorgnr=&sprache=2)) | Measured stage map of 40–50 bar transcritical prototype, machine identity/controls/IHX, source inlet/outlet, pressure, ṁ, actual suction m³/s, speed, shaft/electric power and head/oil limits, uncertainty/holdouts |
| 2 | SINTEF steam turbo-compressors (2020, 2024) | `christian.schlemminger@sintef.no` ([IEA HPT Annex 58 author directory](https://heatpumpingtechnologies.org/content/uploads/sites/70/2024/04/annex58finalwebinarpresentations.pdf)) | Original stage speed lines and sensor uncertainty, 25 kPa absolute / stage PR ≥4.66 if tested, or definitive negative range statement, alternative subatmospheric R718 equipment |
| 3 | Johnson Controls Sabroe | [official enquiry route](https://www.sabroe.com/contact-us) | Clarify HPC/HPO R600 **36 bar** shutdown pressure basis, whether HPX 65-bar variant is approved for R600 high-temperature A3 service, speed and actual-flow map, pressure/oil/discharge limits and availability |
| 4 | OST primary compressor measurements | `leon.brendel@ost.ch` ([paper's corresponding author](https://doi.org/10.1016/j.ijrefrig.2025.11.012)) | Confirmation 439-point published Table 1 contains no pure R600; any separate R600 measured machine data near 7.2 bar suction and 40–60 bar discharge with traceable sensor uncertainties |

### TU Graz exact request

> **Subject:** Request for original R600 transcritical compressor map / measured operating limits (80→70°C source)
>
> Dear Dr Verdnik and Professor Rieberer,
>
> I am researching a reproducible industrial heat-pump/TES architecture benchmark requiring an 80→70°C waste-liquid source and a 110→150°C liquid process load at nominal 1 MW. Your R600 prototype reports real transcritical operation to 160°C with an internal heat exchanger and suction-gas-cooled reciprocating compressor (DOI 10.1016/j.ijrefrig.2022.05.010).
>
> Our **model-derived, not approved** single-stage screening coordinates are approximately 7.2 bar absolute suction at 75°C, 40–60 bar absolute discharge, a pressure ratio of 5.56–8.33 and actual inlet volume around 0.20–0.21 m³/s (before proving machine capacity). We do not assume that your prototype operates at those points.
>
> Could you share non-confidential **original measured compressor stage operating tables or digital maps** with exact refrigerant/topology, absolute suction/discharge pressure and temperature, speed, measured refrigerant mass flow, actual inlet volume, shaft and inverter electrical power, measured discharge/outlet temperature, rated oil/head and design pressure limits, stability boundaries, calibration uncertainty, and independently withheld runs? We can accept a restricted dataset and publish only aggregate validation outcomes, subject to permission. A definitive **negative** answer about this operating range would be as valuable as a matching map.
>
> Please let me know if you can point me to a supplementary dataset or an equipment supplier able to confirm this envelope.
>
> Best regards,
>
> Abhijith Sivaprasadan
>
> MSc Sustainable Energy Engineering, KTH
>
> Open-Energy-Methods / CarnotBatteryLab

### SINTEF exact request

> **Subject:** Original R718 steam turbo stage maps and subatmospheric suction envelope (25 kPa)
>
> Dear Dr Schlemminger,
>
> I am developing an independently verifiable industrial heat-pump/thermal-storage benchmark for an 80→70°C water source and 110→150°C process-liquid duty, nominally 1 MW. I reviewed your original R718 two-stage experimental work (DOI 10.18462/iir.gl.2020.1019) and the 2024 FRIENDSHIP prototype (DOI 10.18462/iir.gl2024.1286).
>
> At a conservative assumed source-outlet pinch, our R718 compressor **model demands** first-stage suction approximately 25 kPa absolute at 75°C, stage-1 pressure ratio ~4.66 and actual inlet volume 2.56 m³/s; second stage around 117 kPa suction, pressure ratio ~4.66 and ~0.61 m³/s inlet volume. These are **requirements**, not a physical compressor rating, and they exceed the separate 2020 test stage maxima.
>
> Are original **multipoint digital stage speed maps**, stability/surge boundaries, mass and inlet volume flow, measured shaft input, discharge temperatures, mechanical/oil/shaft limits and calibration/uncertainty available for those rigs or successor machines? Has any R718 unit actually been measured at **subatmospheric ~25 kPa suction**, or is that beyond the verified range? We would preserve run-level heldouts, respect redistribution restrictions, and publish negative range findings as clearly as positive results.
>
> Best regards,
>
> Abhijith Sivaprasadan
>
> MSc Sustainable Energy Engineering, KTH
>
> Open-Energy-Methods / CarnotBatteryLab

### Supplier exact request

> **Subject:** Technical R600 HPC/HPO vs HPX limitations — 40–60 bar industrial heat-pump compressor inquiry
>
> To the Sabroe Technical Engineering Team,
>
> I am conducting a noncommercial engineering study of a high-temperature n-butane (R600) heat pump supplying 110→150°C process liquid from an 80→70°C liquid waste-heat source, with a nominal 1 MW duty. The preliminary cycle demands approximately 7.2 bar absolute compressor suction and 40–60 bar absolute discharge. These are **hypothetical design requirements**, not an equipment request for immediate operation.
>
> I reviewed **UniSAB 4 Engineering Guide Rev 005, Notes item 30**, which lists an R600-specific 35.5 bar warning / 36.0 bar high-discharge shutdown setting for HPC/HPO and different generic 57.0/57.5 bar settings for HPX units rated to a 65.0 bar design pressure.
>
> Could you clarify whether these controller values are **barg or bara**, which exact R600-rated compressor variants (if any) are approved above 40 bar and at relevant discharge temperatures, and whether any non-confidential original multipoint speed/pressure/mass-flow/power map exists? We also need permissible refrigerant/oil/discharge-temperature/shaft-speed limits, pressure-vessel design, A3 handling, available capacity and operational safeguards. We will **not** alter controller shutdown limits or infer HPX R600 approval from a generic design-pressure figure.
>
> Thank you for directing this to an appropriate technical contact.
>
> Best regards,
>
> Abhijith Sivaprasadan
>
> MSc Sustainable Energy Engineering, KTH

**Messages are templates only.** The script does not send email or submit the supplier web form. Reviewer/user approval and a chosen sender account are required for actual correspondence. Do not claim contact, a reply, license or machine support until recorded.

## Data acceptance and M1.5 gate

Submit an **original manufacturer/independent lab measured map** only after verifying the precise machine, natural working fluid and topology, certified pressure/temperature/oil and safety limits, calibration, and measured speed lines. M1.5 requires at least **three fit points plus two reserved holdouts**, with **suction P/T, pressure ratio, actual suction volume, mass flow, shaft power, discharge T and point uncertainties at fixed speed**; checks robust nonnegative interpolation in the measured fit hull. External provenance metadata alone or a synthetic manufacturer-polynomial table is not an independently measured machine.

Even if a new dataset eventually passes local map interpolation, M1.5's architecture result **still does not certify hardware**, utility/heat-exchanger fit, TES-responsive charging across all required points, multiple-machine 1 MW deployment, or plant electrical round-trip efficiency. Original pressure and thermal protection limits must not be weakened to make a model pass.

## Reproducibility

```bash
python -m pip install -e ".[physics,test]"
python -m pytest tests/test_m1_9_manufacturer_map_sources.py -v
python scripts/run_m1_compressor_map_requirements.py \
  --output results/m1_compressor_map_requirements_80_70_to_110_150.json
python scripts/audit_m1_9_manufacturer_map_sources.py \
  --requirements results/m1_compressor_map_requirements_80_70_to_110_150.json \
  --output results/m1_9_primary_compressor_source_and_vendor_limit_audit.json
```

Only source URLs, exact primary claims, model demand SHA-256 and **component-specific negative comparison** appear in CI artifacts. No model-claimed compressor acceptance, supplier data, author replies, instrument raw observations or new fluid/refrigerant design approval is fabricated.
