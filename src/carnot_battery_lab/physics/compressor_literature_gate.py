"""Provenance-conservative literature crosswalk for H-REF compressor evidence.

A reported point, maxima across different tests, a simulated optimum, and a
measured MULTIPOINT compressor map are not interchangeable evidence classes.
Nulls are unknowns, not free extrapolation. Evidence does not auto-certify a
machine even when a single measured test is thermally similar to the target.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import isfinite

TARGET={
    "source_inlet_C":80.0,"source_outlet_C":70.0,
    "sink_return_C":110.0,"sink_supply_C":150.0,
    "process_heat_kW":1000.0,
}
REQUIRED_MAP_FIELDS=(
    "refrigerant_and_actual_cycle_topology",
    "source_inlet_and_outlet_full_range",
    "sink_inlet_and_outlet_full_range",
    "speed_lines_rpm",
    "suction_pressure_and_temperature",
    "stage_outlet_pressures_and_discharge_temperatures",
    "stage_mass_flow_and_inlet_volumetric_flow",
    "stage_efficiency_and_shaft_power",
    "surge_choke_or_operating_stability_boundaries",
    "verified_oil_lubrication_and_material_limits",
    "measured_performance_with_uncertainty",
    "continuous_service_capacity_or_qualified_parallel_units_for_1MW",
)


@dataclass(frozen=True)
class PublishedHardwareEvidence:
    id: str
    url: str
    refrigerant: str
    natural_refrigerant: bool
    evidence_class: str
    source_inlet_C: float | None=None
    source_outlet_C: float | None=None
    sink_return_C: float | None=None
    sink_supply_C: float | None=None
    maximum_reported_sink_C: float | None=None
    heating_output_kW: float | None=None
    refrigerant_evaporation_C: float | None=None
    reported_compressor_map_at_target: bool=False
    topology: str="not independently established"
    important_limitations: str=""

    def __post_init__(self):
        if self.evidence_class not in (
            "EXPERIMENTAL_POINT",
            "EXPERIMENTAL_REPORTED_MAXIMA",
            "MODEL_PREDICTION"):
            raise ValueError("unrecognized literature evidence class")
        if not self.id or not self.url.startswith("https://"):
            raise ValueError("source record needs verifiable provenance")
        numeric_fields=(self.source_inlet_C,self.source_outlet_C,
            self.sink_return_C,self.sink_supply_C,
            self.maximum_reported_sink_C,self.heating_output_kW,
            self.refrigerant_evaporation_C)
        if any(v is not None and not isfinite(v) for v in numeric_fields):
            raise ValueError("nonfinite experimental boundary")
        if self.reported_compressor_map_at_target:
            # None of these references publishes an exact-target measured map;
            # a reviewed map must be incorporated with separate provenance.
            raise ValueError("single point or paper abstract is not a vendor map")


LITERATURE=(
    PublishedHardwareEvidence(
        id="verdnik_rieberer_2022_r600_experiment",
        url="https://doi.org/10.1016/j.ijrefrig.2022.05.010",
        refrigerant="R600 n-butane", natural_refrigerant=True,
        evidence_class="EXPERIMENTAL_POINT",
        source_inlet_C=60.,sink_supply_C=160.,
        heating_output_kW=24.2,
        topology="single-stage suction-gas-cooled reciprocating, IHX",
        important_limitations="Source exit and sink return not verified for cited 160C point; not 1 MW"),
    PublishedHardwareEvidence(
        id="benkert_2025_2026_r600_steam_test",
        url="https://doi.org/10.1002/cite.70046",
        refrigerant="R600 n-butane",natural_refrigerant=True,
        evidence_class="EXPERIMENTAL_REPORTED_MAXIMA",
        maximum_reported_sink_C=120.,heating_output_kW=125.,
        topology="R600 test bench, hot water and wet/dry steam modes",
        important_limitations="120C and 125kW reported maxima need not be same measured point"),
    PublishedHardwareEvidence(
        id="pfeiffer_2026_r290_r601a_mixture_model",
        url="https://heatpumpingtechnologies.org/publications/transcritical-high-temperature-heat-pump-with-hydrocarbonmixtures-experimental-setup-and-model-predictions/",
        refrigerant="R290/R601a mixture",natural_refrigerant=True,
        evidence_class="MODEL_PREDICTION",
        source_inlet_C=90.,source_outlet_C=60.,
        sink_return_C=100.,sink_supply_C=150.,
        topology="transcritical mixture; prototype built, published comparison is model-only",
        important_limitations="20kW prototype existence does not validate the reported mixture COP at target"),
    PublishedHardwareEvidence(
        id="verdnik_2019_r600_80_75_model",
        url="https://waermepumpe-izw.de/wp-content/uploads/2020/05/190800-ICR-1-3-E2_1186-Verdink-et-al.pdf",
        refrigerant="R600 n-butane", natural_refrigerant=True,
        evidence_class="MODEL_PREDICTION",
        source_inlet_C=80.,source_outlet_C=75.,
        sink_return_C=80.,sink_supply_C=160.,
        topology="single-stage R600 simulated receiver pressure control without IHX",
        important_limitations="COP 3.24 is simulated, not an 80-to-70C experimental point"),
    PublishedHardwareEvidence(
        id="ramirez_2024_r1233zde",
        url="https://doi.org/10.1016/j.applthermaleng.2024.122961",
        refrigerant="R1233zd(E)",natural_refrigerant=False,
        evidence_class="EXPERIMENTAL_POINT",
        sink_supply_C=148.5,heating_output_kW=38.6,
        topology="variable-speed piston with external subcooler",
        important_limitations="50 experimental points; published peak 148.5C/38.6kW is not 1MW and not natural"),
    PublishedHardwareEvidence(
        id="wu_2019_r718_injected_screw",
        url="https://doi.org/10.1016/j.energy.2019.116427",
        refrigerant="R718 water",natural_refrigerant=True,
        evidence_class="EXPERIMENTAL_POINT",
        refrigerant_evaporation_C=85.,sink_supply_C=None,
        topology="water-injected twin-screw, distinct evaporation/condensation boundaries",
        important_limitations="85C refrigerant evaporation cannot accept heat from 80C source with positive pinch"),
)


def assess_reference_against_h_ref(e:PublishedHardwareEvidence,
                                   target:dict=TARGET)->dict:
    """Fail closed: a single paper abstract is never manufacturer map evidence."""
    exact_keys=(
        ("source_inlet_C","source_inlet_C"),
        ("source_outlet_C","source_outlet_C"),
        ("sink_return_C","sink_return_C"),
        ("sink_supply_C","sink_supply_C"),
    )
    missing=[name for name,_ in exact_keys if getattr(e,name) is None]
    different={name:{"published_C":getattr(e,name),
                     "target_C":target[tname]}
               for name,tname in exact_keys
               if getattr(e,name) is not None and
               abs(getattr(e,name)-target[tname])>0.01}
    thermally_incompatible=(
        e.refrigerant_evaporation_C is not None and
        e.refrigerant_evaporation_C>=target["source_inlet_C"])
    if (e.maximum_reported_sink_C is not None
        and e.maximum_reported_sink_C<target["sink_supply_C"]):
        different["maximum_reported_sink_C"]={
            "published_C":e.maximum_reported_sink_C,
            "target_C":target["sink_supply_C"],
        }
    capacity_known_below_target=bool(
        e.heating_output_kW is not None and
        e.heating_output_kW<target["process_heat_kW"])
    # A small prototype isn't excluded from eventual modular scaling; there
    # is simply no measured 1MW identical-component solution to claim.
    return {
        **asdict(e),
        "missing_exact_boundary_fields":missing,
        "explicitly_different_or_insufficient_boundaries":different,
        "refrigerant_evaporation_incompatible_with_80C_inlet":
            thermally_incompatible,
        "reported_single_unit_capacity_below_1MW":capacity_known_below_target,
        "measured_exact_target_compressor_map_qualified":False,
        "technical_applicability":(
            "SIMULATION_ONLY_NOT_HARDWARE_QUALIFICATION"
            if e.evidence_class=="MODEL_PREDICTION"
            else "THERMALLY_INCOMPATIBLE_EVAPORATION"
            if thermally_incompatible
            else "DIFFERENT_OR_UNREPORTED_TARGET_BOUNDARIES"
            if missing or different
            else "SINGLE_EXPERIMENTAL_POINT_NOT_FULL_ENVELOPE"),
        "qualification_missing":list(REQUIRED_MAP_FIELDS),
    }


def evidence_crosswalk()->dict:
    rows=[assess_reference_against_h_ref(x) for x in LITERATURE]
    return {
        "target":TARGET.copy(),
        "records":rows,
        "natural_refrigerant_exact_target_measured_compressor_map_found":False,
        "required_measured_map_and_unit_qualification_fields":
            list(REQUIRED_MAP_FIELDS),
        "no_multipoint_compressor_map_may_be_inferred_from_COP_or_peak_temperature":True,
    }
