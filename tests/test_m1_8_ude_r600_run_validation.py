"""Adversarial offline controls for actual-archive UDE n-butane run groups.

Synthetic values here NEVER constitute empirical observations. Tests verify
identity, exact provenance, source fields, non-pooling and geometry/independence.
"""
from hashlib import md5
from io import BytesIO,StringIO
from zipfile import ZipFile
import csv
import pytest

from carnot_battery_lab.physics.ude_r600_run_validation import (
    audit_original_ude_archive,read_original_bitzer_run,
    _inside_segment_in_3d,EXPECTED_RUN_IDS,
)
LOG_ROOT="data/GitLab Code/measurement_data/Bitzer Data Log/"
NAMES=[f"2025-10-10_Experiment {run}_n-Butane_T_st_75C-70Hz.csv"
       for run in EXPECTED_RUN_IDS]

def _sample(*,power="2,5",pd="9,5",refrig="R600",rows=12)->bytes:
    f=StringIO()
    w=csv.writer(f,delimiter=";")
    w.writerow(["Time","Compressor speed","Low pressure [bar(a)]",
                "High pressure [bar(a)]","Motor power",
                "Compressor frequency","Refrigerant"])
    for i in range(rows):
        w.writerow([f"00:00:{i:02d}","70","3,2",pd,power,"70",refrig])
    return f.getvalue().encode("utf-8")

def _processed_six_source_fixtures():
    # Synthetic test-only measured 66-column worksheet, NOT research evidence.
    from carnot_battery_lab.physics.ude_r600_processed_means import COL
    f=StringIO()
    w=csv.writer(f,delimiter=";")
    header=[[""]*66 for _ in range(11)]
    header[6][0]="Measured Data"
    header[6][39]="Calculated Data"
    header[10][0]="Name in Code"
    for col,field in COL.values():
        header[10][col]=field
    for row in header:w.writerow(row)
    for i in range(6):
        row=[""]*66
        row[0]=str(24+i)
        row[1]="Butane"
        row[3]="70"
        row[6]="0.01"
        row[7]="35"
        row[11]=str(200000+i*5000)
        row[12]=str(700000+i*10000)
        row[17]="2000"
        row[30]="330"
        row[31]="410"
        row[32]="405"
        row[45]="0.55"
        row[46]="0.6"
        row[49]="0.7"
        w.writerow(row)
    return f.getvalue().encode()


def _archive(*,change_run=None,append_bad_path=None):
    f=BytesIO()
    with ZipFile(f,"w") as z:
        for name in NAMES:
            v=_sample() if change_run is None or change_run[0] not in name else change_run[1]
            z.writestr(LOG_ROOT+name,v)
        if append_bad_path:z.writestr(append_bad_path,b"")
        z.writestr("data/CSV_mirror/experimental_data.CSV",
                   _processed_six_source_fixtures())
        # Source code must never be opened, even if present in ZIP archive.
        z.writestr("data/compressor-model (Welp)/class_piston_compressor.py",
                   "raise RuntimeError('PROPRIETARY_SOURCE_MUST_NOT_BE_EXECUTED')")
    return f.getvalue()

def test_three_runs_and_time_samples_are_not_independent():
    raw=_archive()
    out=audit_original_ude_archive(raw,expected_md5=md5(raw).hexdigest())
    assert out["source_filename_labeled_nbutane_run_count"]==3
    assert out["logger_setting_compatible_nbutane_run_count"]==3
    assert out["logged_refrigerant_identity_conflict_detected"] is False
    assert out["raw_correlated_time_sample_count_not_independent"]==36
    assert out["experimental_run_ids"]==["026","027","028"]
    assert all(x["positive_motor_channel_rows"]==12
               for x in out["run_sensor_aggregate_only"])
    assert all(q["3D_holdout_centroid_in_training_two_run_line_segment"]
               for q in out["leave_one_ENTIRE_run_out_support_checks"])
    processed=out["processed_six_r600_original_measured_experiment_summaries"]
    assert processed["candidate_original_pure_nbutane_record_count"]==6
    assert processed["pure_nbutane_measured_EOS_eligible_points"]==6
    assert processed["reference_M1_7_0_68894_electrical_eta_absolute_error_mean"] is not None
    assert processed["raw_individual_points_exposed"] is False
    assert processed["original_1MW_H_REF_hardware_map_qualified"] is False
    assert out["claim_of_real_3D_in_envelope_predictive_accuracy"] is False
    assert out["minimum_independent_run_count_gate_passed"] is False
    assert out["source_model_code_used_or_republished"] is False
    assert out["individual_measurement_timeseries_redistributed"] is False

def test_original_archive_hash_mismatch_hard_failure():
    with pytest.raises(ValueError,match="MD5 mismatch"):
        audit_original_ude_archive(_archive(),expected_md5="f"*32)

@pytest.mark.parametrize("path",["../../bad.csv","/etc/shadow"])
def test_archive_traversal_fail_closed(path):
    raw=_archive(append_bad_path=path)
    with pytest.raises(ValueError,match="unsafe ZIP"):
        audit_original_ude_archive(raw,expected_md5=md5(raw).hexdigest())

def test_pressure_and_motor_invalid_samples_are_excluded_not_fitted():
    s=_sample(power="-1",pd="2,5")
    a=read_original_bitzer_run(s,filename=NAMES[0],run_id="026")
    assert a.csv_record_count==12
    assert a.physically_running_pressure_valid_rows==0
    assert a.positive_motor_channel_rows==0
    assert a.measured_pressure_ratio["N"]==0
    assert a.compressor_speed_logger_units_UNCONFIRMED["N"]==0

def test_locale_decimal_and_field_names_preserved():
    a=read_original_bitzer_run(_sample(),filename=NAMES[0],run_id="026")
    assert a.measured_pressure_suction_bar_a["median"]==3.2
    assert a.measured_pressure_discharge_bar_a["median"]==9.5
    assert a.motor_power_logger_units_UNCONFIRMED["median"]==2.5
    assert a.compressor_speed_logger_units_UNCONFIRMED["median"]==70.
    assert a.motor_power_logger_units_UNCONFIRMED["N"]==12
    assert not a.shaft_power_measured_in_confirmed_SI_units
    assert not a.actual_suction_temperature_C_measured_in_this_log

def test_no_cross_fluid_or_missing_run_is_accepted():
    with pytest.raises(ValueError,match="different refrigerant"):
        read_original_bitzer_run(_sample(),filename="Experiment 007_Propane.csv",
                                run_id="026")
    f=BytesIO()
    with ZipFile(f,"w") as z:
        for name in NAMES[:2]:
            z.writestr(LOG_ROOT+name,_sample())
    raw=f.getvalue()
    with pytest.raises(ValueError,match="missing original"):
        audit_original_ude_archive(raw,expected_md5=md5(raw).hexdigest())

def test_exact_run_centroid_line_segment_geometry():
    assert _inside_segment_in_3d((2.,4.,70.),(1.,3.,70.),(3.,5.,70.))
    assert not _inside_segment_in_3d((2.,6.,70.),(1.,3.,70.),(3.,5.,70.))
    assert not _inside_segment_in_3d((4.,6.,70.),(1.,3.,70.),(3.,5.,70.))
    assert not _inside_segment_in_3d((2.,4.,75.),(1.,3.,70.),(3.,5.,70.))

def test_partial_missing_motor_channel_does_not_overstate_valid_samples():
    # Invalid power is parseable? blank is not.
    raw=_sample(power="",rows=12)
    a=read_original_bitzer_run(raw,filename=NAMES[0],run_id="026")
    assert a.csv_record_count==12
    assert a.motor_power_channel_parseable_rows==0
    assert a.samples_with_all_required_channels==0
    assert a.positive_motor_channel_rows==0

def test_inconsistent_csv_row_width_fails_source_contract():
    raw=_sample()+b"extra;unexpected;column\n"
    with pytest.raises(ValueError,match="column count"):
        read_original_bitzer_run(raw,filename=NAMES[0],run_id="026")

def test_predeclared_six_experiment_holdout_uses_electrical_meter_not_source_fit():
    from carnot_battery_lab.physics.ude_r600_processed_means import (
        audit_processed_experiment_summaries,
    )
    report=audit_processed_experiment_summaries(
        _processed_six_source_fixtures())
    cv=report["experimental_source_means_leave_ONE_EXPERIMENT_OUT_validation"]
    assert cv["eligible"] is True
    assert cv["N"]==6
    assert cv["whole_experiment_LOO_metrics"][
        "fixed_original_M1_7_constant"]["N"]==6
    assert cv["whole_experiment_LOO_metrics"][
        "train_only_two_parameter_log_pressure_ridge"]["N"]==6
    assert cv["same_frequency_in_training_hull_N"]+cv[
        "outside_same_frequency_training_hull_N"]==6
    assert cv["multi_speed_interpolation_used"] is False
    assert cv["in_domain_predictive_accuracy_established"] is False
    assert report["source_derived_global_eta_not_independently_measured"]["N"]==6


def test_m1_7_original_holdout_hashes_are_hard_frozen():
    from pathlib import Path
    from scripts.run_m1_8_ude_r600_validation import (
        FROZEN_OST_M1_7_RESERVED_CONDITION_IDS,
    )
    assert FROZEN_OST_M1_7_RESERVED_CONDITION_IDS==(
        "4f0a2b700ee73221",
        "5dc9eee2bf90a3e0",
        "7aac3574d2cbc688",
        "7c72ebc272835679",
        "86060d047e5b07fa",
    )


def test_meter_units_and_measured_column_contract_fail_closed():
    from carnot_battery_lab.physics.ude_r600_processed_means import (
        audit_processed_experiment_summaries,
    )
    raw=_processed_six_source_fixtures()
    altered=raw.replace(b"P_comp_el",b"P_unknown")
    with pytest.raises(ValueError,match="field header changed"):
        audit_processed_experiment_summaries(altered)


