# Research request — original horizontal packed-bed measurement metadata

**Prepared, not sent.** Public corresponding-author address: **idcalderon@uc.cl**, listed in the Mendeley dataset DOI 10.17632/j37x6ptpk2.1 and in Wolde et al. (2022). The sender must review before contacting the experimental group. Do not imply that the authors endorsed CarnotBatteryLab.

Subject: Request for measurement metadata to independently benchmark copper-slag packed-bed TES (DOI 10.17632/j37x6ptpk2.1)

Dear Dr Calderón-Vásquez,

I am developing an open-source, conservation-based, two-temperature packed-bed thermal storage model and would like to independently benchmark it against the four horizontal copper-slag runs you and your co-authors published at DOI 10.17632/j37x6ptpk2.1. I have preserved the original CSV files and their checksums. I have also reviewed your 2022 Wolde et al. rig description (Revista Brasileira de Energia Solar, 13(2), pp.165–173) and the 2025 Journal of Energy Storage paper (DOI 10.1016/j.est.2025.116769).

Your 2024 dataset description invites requests for additional experimental conditions. To avoid fitting unknown instrumentation from the measured temperature curves, would you be able to share, if available:

1. **Flow and apparatus:** the actual **internal** diameter at the Kanomax hot-wire velocity probe, its exact model, any velocity-traverse/point-velocity-to-mean-flow correction, relevant calibration and uncertainty, the gas pressure/temperature at that cross section, and any independent mass-flow measurements. Was the 2024 rig identical to the 400 mm × 158 mm tank described in the 2022 article?
2. **Pressure:** the make/model/range of the differential transducer, raw 2024 CSV ΔP channel units and scale/zero, pressure-tap locations relative to bed and reducers, uncertainty, and any empty-tank or duct/minor-loss baselines. The 2022 methods describe pressure taps in the connecting pipes and 8 mm silicone hoses but the 2024 CSV does not specify its pressure units.
3. **Thermocouples:** the absolute axial and radial coordinates of T1–T7, their phase/contact configuration, time constants/calibration and the separation/thermal lag between the bed exit and downstream Tout probe. The 2022 methods describe Type-K sensor sheaths in contact with both stones and surrounding air, 50 mm apart.
4. **Material and operations:** actual packed slag mass, measured/estimated void fraction and particle-size distribution, thermophysical properties of the tested slag batch (preferably cp(T), density, conductivity), insulation and steel/pipe heat capacity, and any specific changes in operating conditions between Cases A–D.

I would use these solely for a clearly attributed model/experimental validation study. I would keep your original data intact, document uncertainty, and distinguish numerical verification from independent experimental agreement. If a methods supplement, sensor layout, calibration certificate, notebook, or updated dataset already contains these details, a reference to that material would be sufficient.

Thank you for considering the request.

Kind regards,

[Sender name]
[University/independent researcher affiliation, if appropriate]
[Project: Open-Energy-Methods/CarnotBatteryLab]

---

## Follow-up control and integrity

- **Do not send automatically.** A user-approved sender identity and correspondence are required.
- If a reply includes attachment data, retain original bytes and licence/access permission, add SHA-256 hashes and an instrument/source-level provenance register before changing any physical model inputs.
- Mark 2024 instrument revisions explicitly and do not silently assume that the 2022 rig was identical.
- Source-backed geometry/calibration and calibration/validation splits must be frozen **before** testing previously reserved full-run C/D temperature curves.
- Do not publish non-public raw lab files or identifiable instrument serial numbers without the authors' permission.
