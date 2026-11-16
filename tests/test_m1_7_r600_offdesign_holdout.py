"""M1.7 adversarial testing: external measured source != model calibration truth.

Synthetic test points validate split independence and metric reproducibility;
only the official publisher-MD5 dataset can support reported experimental
results from the GitHub real-data CI workflow.
"""
from dataclasses import replace
from hashlib import md5
import csv
import io
import math
import random
import pytest

from carnot_battery_lab.physics.r600_offdesign_holdout import (
    MeasuredOffdesignPoint,EXPERIMENTAL_CAMPAIGN,
    REFERENCE_OVERALL_ELECTRIC_EFFICIENCY,parse_ost_pure_butane,
    reserve_operating_condition_groups,fit_one_predictor,
    validate_reserved_offdesign,eos_ideal_electrical_work_diagnostics,
)


def _example_observations()->tuple[MeasuredOffdesignPoint,...]:
    pts=[]
    for i in range(20):
        # One compressor, 20 distinct conditions with controlled variation.
        p=200000.+i*12000.
        ratio=1.8+i*.23
        t=42.+(i%7)*2.+i*.3
        eta_el=.66-.029*math.log(ratio)+.008*(i%3-1)
        eta_vol=.82-.043*math.log(ratio)+.005*(i%4-1)
        pts.append(MeasuredOffdesignPoint(
            compressor="SYNTHETIC_TEST_NO_REAL_HARDWARE",
            campaign=EXPERIMENTAL_CAMPAIGN,
            suction_pressure_Pa=p,discharge_pressure_Pa=p*ratio,
            suction_temperature_C=t,electrical_frequency_Hz=48.33,
            overall_electric_isentropic_efficiency=eta_el,
            volumetric_efficiency=eta_vol))
    return tuple(pts)


def test_original_m14_electric_efficiency_meter_boundary():
    assert REFERENCE_OVERALL_ELECTRIC_EFFICIENCY==pytest.approx(
        .74*.95*.98)
    assert REFERENCE_OVERALL_ELECTRIC_EFFICIENCY!=pytest.approx(.74)


def test_stratified_reservation_reproducible_independent_of_labels():
    points=_example_observations()
    train,held,meta=reserve_operating_condition_groups(points)
    shuffled=list(points)
    random.Random(9).shuffle(shuffled)
    a,b,other=reserve_operating_condition_groups(shuffled)
    assert meta["reserved_opaque_condition_hashes"]==other[
        "reserved_opaque_condition_hashes"]
    assert set(x.condition_key for x in train).isdisjoint(
        x.condition_key for x in held)
    assert len(held)==5
    assert len(train)==15
    assert meta["train_observations"]+meta["holdout_observations"]==20
    # Split uses inputs only, not efficiencies or heldout outcomes.
    malicious=tuple(replace(x,overall_electric_isentropic_efficiency=
                            .1+.02*(i%5)) for i,x in enumerate(points))
    _,_,relabel=reserve_operating_condition_groups(malicious)
    assert meta["reserved_opaque_condition_hashes"]==relabel[
        "reserved_opaque_condition_hashes"]


def test_exact_duplicate_operating_condition_stays_in_one_partition():
    points=list(_example_observations())
    points.append(replace(points[8],
                          overall_electric_isentropic_efficiency=.64))
    train,held,meta=reserve_operating_condition_groups(points)
    assert meta["unique_operating_condition_count"]==20
    assert not ({x.condition_key for x in train}&
                {x.condition_key for x in held})
    key=points[8].condition_key
    assert sum(x.condition_key==key for x in train) in (0,2)
    assert sum(x.condition_key==key for x in held) in (0,2)


def test_small_sample_or_pooled_machines_fails_closed():
    with pytest.raises(ValueError,match="too few"):
        reserve_operating_condition_groups(_example_observations()[:5])
    bad=replace(_example_observations()[0],campaign="Experimental OST (London 2023)")
    with pytest.raises(ValueError,match="campaign"):
        _=bad


def test_train_only_ridge_does_not_consult_reserved_efficiencies():
    points=_example_observations()
    train,hold,_=reserve_operating_condition_groups(points)
    original=fit_one_predictor(
        train,variable="overall_electric_isentropic_efficiency")
    changed_heldout=[replace(x,overall_electric_isentropic_efficiency=.15)
                     for x in hold]
    assert fit_one_predictor(train,variable=
        "overall_electric_isentropic_efficiency")==original
    # If holdout targets are changed, predictions do not change.
    assert [original.predict(p) for p in hold]==[
        original.predict(p) for p in changed_heldout]
    with pytest.raises(ValueError,match="unsupported"):
        fit_one_predictor(train,variable="electric_power_W")


def test_reserved_metrics_separate_electric_and_volumetric_efficiency():
    pytest.importorskip("scipy")
    pts=_example_observations()
    train,held,split=reserve_operating_condition_groups(pts)
    output=validate_reserved_offdesign(train,held,split=split)
    assert output["reserved_holdout_count"]==5
    assert output["training_holdout_overlap"] is False
    assert output["independent_experimental_campaign_holdout"] is False
    assert output["model_reference_overall_electric_eta"]==pytest.approx(
        .74*.95*.98)
    assert output["metrics"]["electric_isentropic_efficiency"][
        "fixed_M1_4_reference"]["N"]==5
    assert output["metrics"]["volumetric_efficiency"][
        "train_only_ridge_log_pressure_ratio"]["N"]==5
    assert output["reserved_holdout_within_training_convex_hull"]+output[
        "reserved_holdout_outside_training_convex_hull"]==5
    assert output["equipment_hardware_qualified"] is False
    assert output["matched_H_REF_80_70_to_110_150_qualified"] is False


def test_test_leakage_is_a_hard_failure_even_if_point_values_change():
    pytest.importorskip("scipy")
    pts=_example_observations()
    train,held,_=reserve_operating_condition_groups(pts)
    with pytest.raises(ValueError,match="leakage"):
        validate_reserved_offdesign(train,held+(train[0],))


def _csv_bytes():
    buf=io.StringIO()
    writer=csv.writer(buf)
    writer.writerow([
        "source","compressor","refrigerant","f_elec_Hz",
        "p_suc_bar","p_dis_bar","T_suc_C","eta_is","eta_vol",
    ])
    for p in _example_observations():
        writer.writerow([
            p.campaign,p.compressor,"butane",
            p.electrical_frequency_Hz,
            p.suction_pressure_Pa/1e5,p.discharge_pressure_Pa/1e5,
            p.suction_temperature_C,
            p.overall_electric_isentropic_efficiency,
            p.volumetric_efficiency,
        ])
    writer.writerow([
        "Bitzer EN12900","SYNTHETIC_COEFFS","butane",
        50,4.,16.,60.,.9,.9,
    ])
    writer.writerow([
        EXPERIMENTAL_CAMPAIGN,"SYNTHETIC_TEST_NO_REAL_HARDWARE",
        "Butane/propane (x1=0.75)",48.33,3.,10.,65.,.6,.7,
    ])
    return buf.getvalue().encode("utf-8")


def test_raw_csv_source_classification_and_checksum_guard():
    raw=_csv_bytes()
    rows=parse_ost_pure_butane(raw,expected_md5=md5(raw).hexdigest())
    assert len(rows)==20  # no polynomial, no mixture contamination
    with pytest.raises(ValueError,match="checksum"):
        parse_ost_pure_butane(raw,expected_md5="0"*32)
    altered=raw.replace(b"butane",b"propane")
    with pytest.raises(ValueError,match="no measured pure n-butane"):
        parse_ost_pure_butane(altered,expected_md5=md5(altered).hexdigest())


def test_different_drive_frequency_not_a_single_speed_line():
    raw=_csv_bytes().replace(b"48.33,2.0",b"49.0,2.0",1)
    with pytest.raises(ValueError,match="frequency variation"):
        parse_ost_pure_butane(raw,expected_md5=md5(raw).hexdigest())


def test_ost_eos_specific_work_derived_not_confused_with_measured_power():
    pytest.importorskip("CoolProp")
    pts=_example_observations()
    report=eos_ideal_electrical_work_diagnostics(pts[:4])
    assert report["points"]==4
    assert report["isentropic_specific_enthalpy_J_kg"]["min"]>0
    assert report["actual_measured_electric_power"] is None
    assert report["actual_measured_shaft_power"] is None
    assert report["actual_measured_refrigerant_mass_flow"] is None
    assert report["measured_eta_implied_not_measured_electric_work_J_kg"][
        "min"]>0


def test_missing_observation_and_two_compressors_fail():
    a=list(_example_observations())
    a[0]=replace(a[0],compressor="DIFFERENT_MACHINE")
    buf=io.StringIO()
    writer=csv.writer(buf)
    writer.writerow([
        "source","compressor","refrigerant","f_elec_Hz",
        "p_suc_bar","p_dis_bar","T_suc_C","eta_is","eta_vol",
    ])
    for p in a:
        writer.writerow([p.campaign,p.compressor,"butane",
                         p.electrical_frequency_Hz,
                         p.suction_pressure_Pa/1e5,
                         p.discharge_pressure_Pa/1e5,
                         p.suction_temperature_C,
                         p.overall_electric_isentropic_efficiency,
                         p.volumetric_efficiency])
    raw=buf.getvalue().encode()
    with pytest.raises(ValueError,match="multiple"):
        parse_ost_pure_butane(raw,expected_md5=md5(raw).hexdigest())
