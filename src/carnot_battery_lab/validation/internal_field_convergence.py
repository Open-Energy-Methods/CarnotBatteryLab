"""Internal two-phase spatial refinement at FIXED independent coordinates.

No measured T1..T7 at t>0 are used here. The seven evaluation x-positions
are 0.05...0.35m hypothetical points chosen before comparison, NOT
independently surveyed 2024 thermocouple coordinates. Never interpret
internal field agreement as validation against measured sensor output.

The internal convergence report complements outlet/front convergence;
one cannot infer internal phase mesh convergence from outlet alone.
"""
from __future__ import annotations
import math
from statistics import mean

SOURCE_SHA="5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab"
EXPECTED_POSITIONS=tuple(.05*i for i in range(1,8))


def _rms_difference(a:list[float],b:list[float])->dict:
    if len(a)!=len(b) or len(a)<10:
        raise ValueError("short/mismatched in-bed time series")
    differences=[float(x-y) for x,y in zip(b[1:],a[1:])]
    if not all(math.isfinite(x) for x in differences):
        raise ValueError("nonfinite internal temperatures")
    return {
        "rms_K":math.sqrt(mean(x*x for x in differences)),
        "max_absolute_K":max(abs(x) for x in differences),
        "points_compared":len(differences),
    }


def assess_internal_field_refinement(runs:dict[int,dict])->dict:
    meshes=tuple(sorted(runs))
    if meshes!=(32,64,128,256,512):
        raise ValueError("internal convergence requires all source-locked 32..512 meshes")
    for n in meshes:
        data=runs[n]
        if data["source_sha256"]!=SOURCE_SHA or data.get(
            "outlet_temperature_target_used_in_physics") is not False:
            raise ValueError("source/target forcing not qualified")
        if data.get("internal_fields_do_not_use_post_initial_measured_TC") is not True:
            raise ValueError("in-bed field depends on downstream observed TC")
        if tuple(data["internal_sample_positions_m"])!=EXPECTED_POSITIONS:
            raise ValueError("in-bed observations must use same fixed physical coordinates")
    comparisons={}
    for coarse,fine in zip(meshes,meshes[1:]):
        a,b=runs[coarse],runs[fine]
        if a["model_time_s"]!=b["model_time_s"]:
            raise ValueError("mesh time axes differ")
        per_phase={}
        for phase,key in (("gas","internal_sampled_gas_K"),
                          ("rock","internal_sampled_rock_K")):
            per_pos={}
            for i in range(1,8):
                name=f"x{i*5:02d}cm"
                per_pos[name]=_rms_difference(a[key][name],b[key][name])
            per_phase[phase]={
                "fixed_location_differences":per_pos,
                "max_RMS_across_positions_K":max(r["rms_K"] for r in per_pos.values()),
                "max_absolute_temperature_difference_K":
                    max(r["max_absolute_K"] for r in per_pos.values()),
            }
        comparisons[f"{coarse}_to_{fine}"]=per_phase
    finest=comparisons["256_to_512"]
    return {
        "status":"SOURCE_LOCKED_INTERNAL_PHASE_MESH_COMPARISON_NOT_EXPERIMENTAL_VALIDATION",
        "source_doi":"10.17632/j37x6ptpk2.1",
        "source_case":"B_only",
        "raw_source_sha256":SOURCE_SHA,
        "fixed_positions_m":EXPECTED_POSITIONS,
        "positions_are_assumed_not_measured_sensor_locations":True,
        "mesh_pairs":comparisons,
        "finest_pair_max_gas_RMS_K":finest["gas"]["max_RMS_across_positions_K"],
        "finest_pair_max_rock_RMS_K":finest["rock"]["max_RMS_across_positions_K"],
        "prospective_internal_increment_screen_1K_all_positions":bool(
            max(finest["gas"]["max_RMS_across_positions_K"],
                finest["rock"]["max_RMS_across_positions_K"])<=1.0),
        "qualification_of_internal_sensor_measurement_operator":False,
        "experimental_predictive_validation_pass":False,
        "no_C_D_model_selection":True,
        "warning":"A 1K purely numerical screening threshold is NOT an experimentally measured instrument uncertainty.",
    }
