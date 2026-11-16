# Research data request — measured compressor maps for 80°C-source H-REF

This is an **outreach-ready request**, not evidence a manufacturer has replied, endorsed the research, or approved its operating points. **Do not send automatically**. Obtain permission before sharing any confidential returned compressor data or re-publishing curves.

## Prospective recipients and published anchors

- **R718 experimental turbo-compressor team**, Verpe, Schlemminger, Bantle & Ahrens (SINTEF / NTNU), [DOI 10.18462/iir.gl.2020.1019](https://doi.org/10.18462/iir.gl.2020.1019). The paper explicitly reports constructed stage maps, but those published figures concern another inlet pressure (approximately atmospheric) and water-injection desuperheating. Ask whether original point tables / calibration / speed and mass-flow metadata can be shared for independent interpolation assessment.
- **R600 high-temperature reciprocating compressor team**, Verdnik & Rieberer (Graz), [DOI 10.1016/j.ijrefrig.2022.05.010](https://doi.org/10.1016/j.ijrefrig.2022.05.010). Ask for data from the **measured** transcritical 160°C rig, including suction-gas cooling, IHX effectiveness, compressor limits, rotational speed, mass/volume flow and high-side pressure. Source temperature in their reported nominal benchmark was 60°C, so an 80→70°C map **must not be inferred**.
- **OST Buchs original experimental R600 dataset**, Brendel et al., [Energies 2024, 17, 1981](https://doi.org/10.3390/en17081981), [independent open compressor data](https://doi.org/10.5281/zenodo.17599603). Ask for matching measured mass-flow/electric power/thermocouple uncertainty and actual compressor drive-speed metadata. The present 20 measured butane points are outside H-REF nominal pressures.
- **University of Duisburg-Essen HP+TES experimental campaign**, Schmeing, Welp & Atakan, [DOI 10.5281/zenodo.18712882](https://doi.org/10.5281/zenodo.18712882). Ask for an independent original model publication/reuse-rights clarification, especially the archived compressor-model README indicating nonpublic code, and measurement calibration and working-fluid-specific complete P/T/mass/drive time series. Do not repackage the archived source code.

## Research request template

**Subject:** Research data request: independently measured R718/R600 compressor maps for high-temperature heat-pump/TES validation

Dear Research Team,

I am developing a reproducible open research benchmark for industrial heat pumps coupled to thermal energy storage. We are evaluating a source-liquid stream cooling from **80 to 70°C**, a **110 to 150°C** process-liquid heating service, and a nominal **1 MW** heat duty.

I found your published experimental work on high-temperature compressors and would like to ask whether you can share original, measurement-based **single-machine or stage compressor maps**, or a paper supplement containing their point tables, with explicit permissions for scientific comparison. We are **not** looking to fit or infer hardware ratings from a published peak COP, and we will attribute the original research.

For each measured operating point, the most useful data are **working fluid and exact stage/intercooler/IHX topology**, calibrated *absolute* compressor inlet/outlet pressures and temperatures, measured **shaft speed (rpm)**, suction actual volumetric flow and refrigerant mass flow, compressor shaft and electrical power with their measurement boundaries, isentropic and volumetric efficiencies, discharge thermal protection limits, and stability/choke/surge or other manufacturer limits. Please also provide uncertainties, sensor calibration, campaign/run IDs and a description of measurements withheld from model fitting. We can accept a restricted-access arrangement and publish only non-confidential validation metrics if required.

Our current **numerical requirements, not verified machine specifications**, are:

| Hypothesis | Compressor suction | Stage ratios | Actual inlet volumetric requirements | Notes |
|---|---|---|---|---|
| R718, two stages, direct nominal process heat | ~25.0 kPa / 75°C (stage 1), ~116.7 kPa / 114°C (stage 2) | ~4.659 each | ~2.56 m³/s then ~0.606 m³/s | Discharge ~283°C/339°C; external intercooler in model |
| R600, single-stage transcritical, no IHX in numerical model | ~65°C saturation / 75°C suction; p≈0.72 MPa | ~5.56–8.33 over 4–6 MPa high side | ~0.201–0.213 m³/s | Calculated discharge ~163–188°C; **not** rated operation |

Are original map tables or experimental condition ranges available, and would their reuse conditions permit a clearly labeled **independent held-out comparison**? If the compressors were not operated near this envelope, that negative result is equally valuable to document.

Thank you for considering the request.

## Required response/rights record

Capture `contact/group`, `source_DOI`, `document_URL`, `original_data_sha256`, `permission_class`, `exact_refrigerant_and_topology`, `measurement_method`, `uncertainty`, `machine_id`, `stage_id`, `speed_range`, `inlet_range`, `stable_pressure_ratio_range`, `volume_and_mass_flow_range`, `discharge_limit`, `map_fit_split`, `independent_holdouts`, `model_vs_measured_meter_boundaries`, `known_caveats`.

No reply, dataset, operating-point existence, or redistribution license is implied by this template. M1.5 does **not** accept a request, response summary or single COP as a compressor map, and no industrial plant can be qualified from these source documents alone.
