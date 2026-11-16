"""M1.7 source-verified out-of-sample R600 electrical-efficiency test.

Only the original 2024 OST measured pure-butane campaign is admitted. The
20-point split is frozen by operating conditions, not by target efficiencies.
The M1.4 80/70->110/150 R600 cycle is NOT fitted to this other compressor.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import json

from scripts.audit_public_r600_compressor_measurements import (
    fetch_source,SOURCE_MD5,
)
from carnot_battery_lab.physics.r600_offdesign_holdout import (
    EXPERIMENTAL_CAMPAIGN,
    REFERENCE_OVERALL_ELECTRIC_EFFICIENCY,
    SOURCE_DOI,parse_ost_pure_butane,
    reserve_operating_condition_groups,
    validate_reserved_offdesign,eos_ideal_electrical_work_diagnostics,
)


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--download",action="store_true")
    p.add_argument("--input-csv",type=Path)
    p.add_argument("--requirements",type=Path,required=True)
    p.add_argument("--output",type=Path,default=Path(
        "results/m1_7_r600_reserved_experimental_holdout_validation.json"))
    args=p.parse_args()
    if args.download==(args.input_csv is not None):
        raise ValueError("choose exactly --download or --input-csv")
    raw=fetch_source() if args.download else args.input_csv.read_bytes()
    points=parse_ost_pure_butane(raw,expected_md5=SOURCE_MD5)
    if len(points)!=20:
        raise ValueError("published frozen OST pure butane sample count changed")
    train,holdout,split=reserve_operating_condition_groups(points)
    result=validate_reserved_offdesign(train,holdout,split=split)
    eos=eos_ideal_electrical_work_diagnostics(points)
    requirements=json.loads(args.requirements.read_text(encoding="utf-8"))
    if requirements.get("evidence_status")!=(
            "M1_4_SCIENTIFIC_REQUIREMENTS_AND_LITERATURE_CROSSWALK_ONLY"):
        raise ValueError("mismatched M1.4 source/sink real-fluid requirements")
    model_cases=requirements[
        "r600_80C_source_110_150C_transcritical_screen"][
        "map_requirements_for_numerically_feasible_points"]
    suction_min=min(x.suction_pressure_Pa for x in points)
    suction_max=max(x.suction_pressure_Pa for x in points)
    discharge_min=min(x.discharge_pressure_Pa for x in points)
    discharge_max=max(x.discharge_pressure_Pa for x in points)
    temp_min=min(x.suction_temperature_C for x in points)
    temp_max=max(x.suction_temperature_C for x in points)
    target=[]
    for k,c in sorted(model_cases.items(),key=lambda t:int(t[0])):
        d=c["compressor_stage_demands"][0]
        hit=bool(
            suction_min<=d["suction_pressure_Pa"]<=suction_max
            and discharge_min<=d["discharge_pressure_Pa"]<=discharge_max
            and temp_min<=d["suction_temperature_C"]<=temp_max)
        target.append({
            "target_highside_pressure_Pa":d["discharge_pressure_Pa"],
            "target_suction_pressure_Pa":d["suction_pressure_Pa"],
            "target_suction_temperature_C":d["suction_temperature_C"],
            "inside_all_three_external_measured_marginal_ranges":hit,
            "inside_measured_multidimensional_envelope":False,
            "map_qualified":False,
        })
    # The publication's eta_is is OVERALL ELECTRIC. We compare the explicitly
    # composed electric meter reference, never the model's 0.74 SHAFT η as
    # though its meter boundary were identical.
    metrics=result["metrics"]["electric_isentropic_efficiency"]
    fixed_error=metrics["fixed_M1_4_reference"]["MAE"]
    comparison_status=(
        "OFFTARGET_FIXED_ELECTRIC_REFERENCE_WITHIN_PREDECLARED_0_05_MAE"
        if fixed_error<=.05
        else "OFFTARGET_FIXED_ELECTRIC_REFERENCE_NOT_CORROBORATED_AT_0_05_MAE")
    payload={
        "scientific_status":"M1_7_OST_PURE_R600_OUT_OF_SAMPLE_OTHER_MACHINE_ONLY",
        "source_DOI":SOURCE_DOI,
        "source_campaign":EXPERIMENTAL_CAMPAIGN,
        "published_csv_MD5":SOURCE_MD5,
        "download_SHA256":sha256(raw).hexdigest(),
        "M1_4_requirements_SHA256":sha256(
            args.requirements.read_bytes()).hexdigest(),
        "genuine_pure_butane_measured_count":len(points),
        "train_holdout_method":split,
        "training_model_origin":"fixed 2-parameter ridge predeclared, no heldout fitting",
        "reference_electric_efficiency":REFERENCE_OVERALL_ELECTRIC_EFFICIENCY,
        "fixed_reference_offtarget_benchmark_status":comparison_status,
        "reference_MAE_screening_tolerance_absolute_eta":.05,
        "holdout_experimental_validation":result,
        "CoolProp_EOS_specific_work_sanity":eos,
        "observed_condition_marginal_bounds":{
            "suction_pressure_Pa":{"min":suction_min,"max":suction_max},
            "discharge_pressure_Pa":{"min":discharge_min,"max":discharge_max},
            "suction_temperature_C":{"min":temp_min,"max":temp_max},
        },
        "H_REF_R600_model_pressure_scan_vs_experimental_range":target,
        "source_contains_additional_synthetic_and_mixed_fluid_rows_excluded":True,
        "individual_raw_measured_observations_in_artifact":False,
        "reported_eta_is_means_overall_electric_not_shaft":True,
        "actual_compressor_shaft_speed_rpm_measured":False,
        "measurement_point_uncertainty_available":False,
        "independent_campaign_or_laboratory_validation":False,
        "sample_count_precludes_robust_generalization":True,
        "M1_5_hardware_map_qualified":False,
        "reference_1MW_H_REF_process_heat_qualified":False,
        "matched_service_architecture_RTE":None,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n",
                           encoding="utf-8")
    print("M1_7_SOURCE_MD5_VALIDATED",SOURCE_MD5)
    print("M1_7_MEASURED_R600",len(points),
          "TRAIN",len(train),"RESERVED_HOLDOUT",len(holdout))
    print("M1_7_WITHIN_TRAIN_HULL_HOLDOUT",
          result["reserved_holdout_within_training_convex_hull"],
          "OUTSIDE_HULL_HOLDOUT",
          result["reserved_holdout_outside_training_convex_hull"])
    print("M1_7_ORIGINAL_FIXED_ELECTRIC_ETA",
          REFERENCE_OVERALL_ELECTRIC_EFFICIENCY)
    print("M1_7_FIXED_HOLDOUT_METRICS",
          metrics["fixed_M1_4_reference"])
    print("M1_7_FIT_ONLY_RIDGE_HOLDOUT_METRICS",
          metrics["train_only_ridge_log_pressure_ratio"])
    print("M1_7_VOLUMETRIC_HOLDOUT_METRICS",
          result["metrics"]["volumetric_efficiency"])
    print("M1_7_OFFTARGET_CONCLUSION",comparison_status)
    for row in target:
        print("M1_7_HREF_PRESSURE_CASE",row)
    print("H_REF_EXACT_SOURCE_PROCESS_HARDWARE_QUALIFIED=False")


if __name__=="__main__":
    main()
