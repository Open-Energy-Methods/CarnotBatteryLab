"""M1.8 original experimental run-level evidence + frozen M1.7 holdouts.

Fetches exact original OST and UDE Zenodo checksums in CI. ZIP model code is
NOT touched. Treat n-butane 026,027,028 as three *runs*, not 6839 trials.
No original time-series observations or model code leave the CI workspace.
"""
from __future__ import annotations
import argparse,hashlib,json,urllib.request
from pathlib import Path
from carnot_battery_lab.physics.r600_offdesign_holdout import (
    SOURCE_MD5 as OST_MD5, parse_ost_pure_butane,
    reserve_operating_condition_groups,validate_reserved_offdesign,
)
from carnot_battery_lab.physics.ude_r600_run_validation import (
    UDE_MD5,audit_original_ude_archive,
)
OST_URL="https://zenodo.org/records/17599603/files/compressor_performance_data.csv?download=1"
UDE_URL="https://zenodo.org/records/18712882/files/data.zip?download=1"

def _get(url:str,limit:int)->bytes:
    with urllib.request.urlopen(urllib.request.Request(
        url,headers={"User-Agent":"CarnotBatteryLab-M1.8/1.0"}),timeout=95) as r:
        if r.status!=200:raise ValueError("source download failed")
        raw=r.read(limit+1)
    if len(raw)>limit:raise ValueError("original source download too large")
    return raw

def evaluate(ost_raw:bytes,ude_raw:bytes)->dict:
    # Reuse the EXACT pre-existing split function, bin count, seed and source
    # classification; no allocation decisions based on newly acquired UDE.
    old=parse_ost_pure_butane(ost_raw,expected_md5=OST_MD5)
    if len(old)!=20:raise ValueError("original OST measured-point count changed")
    train,holdout,meta=reserve_operating_condition_groups(old)
    old_validation=validate_reserved_offdesign(train,holdout,split=meta)
    source_result=old_validation["metrics"][
        "electric_isentropic_efficiency"]["fixed_M1_4_reference"]
    if (len(train)!=15 or len(holdout)!=5 or
        abs(source_result["MAE"]-.06652)>1e-8 or
        old_validation["reserved_holdout_within_training_convex_hull"]!=1):
        raise ValueError("M1.7 OST reserved split/metric is not preserved")
    ude=audit_original_ude_archive(ude_raw,expected_md5=UDE_MD5)
    return {
        "scientific_status":"M1_8_INDEPENDENT_UDE_3_RUN_SENSOR_AUDIT_NOT_VALIDATED",
        "M1_7_OST_FROZEN_V1":{
            "published_CSV_md5":OST_MD5,
            "original_source_sha256":hashlib.sha256(ost_raw).hexdigest(),
            "same_M1_7_split_algorithm_seed_and_bins":True,
            "original_M1_7_fit_observations":len(train),
            "original_M1_7_reserved_observations":len(holdout),
            "original_M1_7_reserved_opaque_condition_hashes":
                meta["reserved_opaque_condition_hashes"],
            "original_M1_7_fixed_reference_holdout_MAE":source_result["MAE"],
            "original_M1_7_in_train_hull_holdouts":
                old_validation["reserved_holdout_within_training_convex_hull"],
            "M1_7_source_predictions_retrained_on_UDE":False,
            "M1_7_reserved_results_reselected_or_recalibrated":False,
        },
        "UDE_independently_measured_original_bitzeR_runs":ude,
        "cross_machine_training_or_efficiency_metric_pooling":False,
        "M1_5_exact_target_compressor_qualification":False,
        "matched_service_RTE":None,
        "experimental_raw_data_redistributed":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--download",action="store_true")
    p.add_argument("--ost-csv",type=Path)
    p.add_argument("--ude-zip",type=Path)
    p.add_argument("--output",type=Path,default=Path(
        "results/m1_8_ude_original_nbutane_run_level_validation.json"))
    a=p.parse_args()
    if a.download and (a.ost_csv or a.ude_zip):
        raise ValueError("choose all downloads or both local original source files")
    if not a.download and not (a.ost_csv and a.ude_zip):
        raise ValueError("require both original source files")
    ost=_get(OST_URL,7_000_000) if a.download else a.ost_csv.read_bytes()
    ude=_get(UDE_URL,45_000_000) if a.download else a.ude_zip.read_bytes()
    out=evaluate(ost,ude)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    preserved=out["M1_7_OST_FROZEN_V1"]
    d=out["UDE_independently_measured_original_bitzeR_runs"]
    print("M1_8_ORIGINAL_OST_HOLDOUT_FROZEN_SHA_IDS",
          preserved["original_M1_7_reserved_opaque_condition_hashes"])
    print("M1_8_SOURCE_OST_MAE_FROZEN",
          preserved["original_M1_7_fixed_reference_holdout_MAE"])
    print("M1_8_UDE_VERIFIED_EXPERIMENTAL_RUNS",
          d["independent_original_R600_run_count"],
          "CORRELATED_RECORDS",d["raw_correlated_time_sample_count_not_independent"])
    for x in d["run_sensor_aggregate_only"]:
        print("M1_8_UDE_RUN_SENSOR_AGGREGATE",
              x["run_id"],"valid_motor",x["positive_motor_channel_rows"],
              "valid_pressure",x["physically_running_pressure_valid_rows"],
              "refrigerant",x["refrigerant_text_unique"],
              "suction_bar_a",x["measured_pressure_suction_bar_a"],
              "discharge_bar_a",x["measured_pressure_discharge_bar_a"],
              "motor_raw_unverified_units",x["motor_power_logger_units_UNCONFIRMED"],
              "speed_raw_unverified_units",
              x["compressor_speed_logger_units_UNCONFIRMED"])
    print("M1_8_LEAVE_ONE_RUN_OUT_HULL_SUPPORT",
          d["leave_one_ENTIRE_run_out_support_checks"])
    print("M1_8_IN_ENVELOPE_PREDICTIVE_VALIDATION",
          d["claim_of_real_3D_in_envelope_predictive_accuracy"])
    print("M1_8_HREF_1MW_HARDWARE_QUALIFIED=False")

if __name__=="__main__":main()
