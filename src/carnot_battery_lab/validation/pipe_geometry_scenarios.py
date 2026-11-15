"""Conditional NPS-2 exhaust-bore scenarios; NEVER an observed 2024 pipe ID.

2025 Calderón-Vásquez et al. J. Energy Storage (doi
10.1016/j.est.2025.116769) describes 2-inch steel pipes at both
vessel flanges. That does NOT document the internal diameter at the
downstream velocity probe, the schedule of that section, an accurate
velocity traverse, or pressure measurement calibration.

The NPS-2 dimensions below are engineering-standard reference values
from ASME B36.10-type tables (not direct manufacturer certification):
NPS2 OD 60.3 mm; Sch40 ID about 52.48 mm and Sch80 ID about 49.22 mm.
Use only to demonstrate flow-area consequence under *conditional* schedule
hypotheses if—and ONLY if—the anemometer section is proven to be NPS2.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from math import pi, isfinite
from .flow_pressure_audit import sensitivity_scenarios

NPS2_OUTSIDE_DIAMETER_MM=60.3
NPS2_CANDIDATE_SCHEDULES=(
    ("schedule_40",3.91),
    ("schedule_80",5.54),
)
RESEARCH_ARTICLE_DOI="10.1016/j.est.2025.116769"
ENGINEERING_REFERENCE_URL="https://process-bench.com/ref/schedule-40-pipe-dimensions/"


def nominal_scenario_table(*,velocity_m_s:float=5.,
                           measured_exhaust_C:float=100.)->dict:
    if not all(isfinite(x) for x in (velocity_m_s,measured_exhaust_C)):
        raise ValueError("finite source-referenced conditions required")
    if velocity_m_s<0 or measured_exhaust_C<=-273.15:
        raise ValueError("nonnegative velocity and physical temperature required")
    sizes=[]
    for name,wall_mm in NPS2_CANDIDATE_SCHEDULES:
        internal=(NPS2_OUTSIDE_DIAMETER_MM-2*wall_mm)/1000
        result=sensitivity_scenarios(
            Tout_C=measured_exhaust_C,velocity_m_s=velocity_m_s,
            diameters_m=(internal,internal+0.000001))
        # Read mass flow of base diameter without claiming the pipe is installed.
        flow=result["diameter_scenarios"][0]["mass_flow_kg_s"]
        sizes.append({
            "schedule_label":name,
            "nominal_outside_diameter_mm":NPS2_OUTSIDE_DIAMETER_MM,
            "nominal_wall_mm":wall_mm,
            "conditional_nominal_bore_mm":1000*internal,
            "conditional_exhaust_mass_flow_kg_s":flow,
            "actual_probe_pipe_schedule_verified":False,
        })
    return {
        "article_doi":RESEARCH_ARTICLE_DOI,
        "engineering_pipe_dimension_reference_url":ENGINEERING_REFERENCE_URL,
        "source_articles_identify_2_inch_flanged_connections_NOT_probe_internal_bore":True,
        "assumes_velocity_probe_is_in_same_NPS2_section":True,
        "this_assumption_is_UNVERIFIED":True,
        "scenarios":sizes,
        "flow_ratio_larger_over_smaller":(
            sizes[0]["conditional_exhaust_mass_flow_kg_s"]/
            sizes[1]["conditional_exhaust_mass_flow_kg_s"]
            if velocity_m_s>0 else None),
        "cannot_calibrate_pressure_channel":True,
        "measurement_status":"SCENARIO_ONLY_NOT_INSTRUMENT_GEOMETRY_VERIFIED",
    }
