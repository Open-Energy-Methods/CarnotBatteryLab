"""Offline M2.1 adverse-data evidence tests: all fixture physics synthetic.

No fixtures count as a measured TES breakthrough or real dP.
"""
from dataclasses import replace
from hashlib import sha256
import pytest

from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.packed_bed_measurement_gate import (
    MeasuredBedRun,fixed_run_holdout_protocol,
    pressure_loss_no_fit_score,score_independent_holdout_thermal_history,
)
from scripts.discover_m2_packed_bed_original_data import (
    PUBLIC_DATASETS,_metadata_structure,
)


def _run(i:int=0,**kwargs):
    g=PackedBedGeometry(
        length_m=1.0,diameter_m=.5,particle_diameter_m=.02,porosity=.4)
    base={
      "dataset_doi":"10.17632/synthetic-test-only",
      "run_id":f"synthetic-{i}","apparatus_id":"FAKE_TEST_RIG",
      "evidence_class":"SYNTHETIC_UNIT_TEST",
      "source_sha256":sha256(str(i).encode()).hexdigest(),
      "source_field_and_unit_map_id":"synthetic-fixture-map-v1",
      "temperature_calibration_ref":"synthetic-temperature-reference-not-real",
      "pressure_calibration_ref":"synthetic-pressure-reference-not-real",
      "flow_calibration_ref":"synthetic-flow-reference-not-real",
      "bed_geometry":g,
      "mass_flow_kg_s":.05+i*.001,
      "gas_density_kg_m3":1.2,
      "gas_dynamic_viscosity_Pa_s":1.8e-5,
      "initial_temperature_K":300.,
      "thermal_inlet_temperature_K":400.,
      "reported_pressure_drop_tap_to_tap_Pa":200.,
      "independently_measured_pipe_fittings_pressure_drop_Pa":15.,
      "differential_pressure_sensor_standard_uncertainty_Pa":3.,
      "time_s":(0.,10.,20.,30.),
      "axial_sensor_positions_m":(.2,.8),
      "observed_fluid_temperature_K_by_sensor":(
         (300.,312.,324.,337.),(300.,302.,305.,310.)),
      "thermal_sensor_standard_uncertainty_K":.5,
      "stable_flow_confirmed":True}
    base.update(kwargs)
    return MeasuredBedRun(**base)


def test_manifests_have_original_source_and_independent_air_pressure_candidate():
    assert len(PUBLIC_DATASETS)==2
    a,b=PUBLIC_DATASETS
    assert a["doi"]=="10.17632/3pp86gdvh4.2"
    assert a["declared_experiment_count_in_publisher_description"]==9
    assert "differential_pressure" in a["expected_physics"]
    assert b["doi"]=="10.17632/fgn79fzg7x.1"
    assert "differential_pressure" not in b["expected_physics"]


def test_manifest_only_never_elevates_metadata_to_observations():
    d=_metadata_structure({"files":[{"name":"test.csv","id":"abc","size":20}],
                           "folders":[]})
    assert d["file_count_if_list"]==1
    assert d["entries_metadata_only"][0]["source_file_contents_downloaded"] is False
    assert d["entries_metadata_only"][0]["name"]=="test.csv"


def test_good_synthetic_protocol_cannot_be_used_as_measured_acceptance():
    runs=[_run(i) for i in range(4)]
    m=fixed_run_holdout_protocol(
        runs,holdout_run_ids=["synthetic-2","synthetic-3"],
        expected_evidence="SYNTHETIC_UNIT_TEST")
    assert m["reserved_run_count"]==2
    assert m["training_run_count"]==2
    assert not m["source_temperature_and_pressure_holdout_predictions_accepted"]
    assert m["simulated_observation_count_used_as_independent_experiment"]==0
    with pytest.raises(ValueError,match="wrong experiment evidence class"):
        fixed_run_holdout_protocol(
            runs,holdout_run_ids=["synthetic-2","synthetic-3"])


def test_replication_and_same_experiment_cannot_create_fake_independence():
    rr=[_run(i) for i in range(4)]
    rr[3]=rr[2]
    with pytest.raises(ValueError,match="duplicated"):
        fixed_run_holdout_protocol(
            rr,holdout_run_ids=["synthetic-2","synthetic-3"],
            expected_evidence="SYNTHETIC_UNIT_TEST")


@pytest.mark.parametrize("change",[
    {"time_s":(0.,10.,10.,30.)},
    {"time_s":(0.,20.,10.,30.)},
    {"time_s":(0.,10.,20.)},
    {"axial_sensor_positions_m":(.2,.2)},
    {"axial_sensor_positions_m":(.2,2.)},
    {"mass_flow_kg_s":0.},
    {"gas_density_kg_m3":-1.},
    {"differential_pressure_sensor_standard_uncertainty_Pa":0.},
    {"stable_flow_confirmed":False},
    {"temperature_calibration_ref":""},
    {"source_sha256":"pretend-original-archive"},
    {"observed_fluid_temperature_K_by_sensor":((300.,302.),(300.,302.))},
])
def test_invalid_sensor_and_temporal_contracts_fail_closed(change):
    with pytest.raises(ValueError):
        _run(**change)


def test_pressure_loss_fails_without_independently_measured_pipe_correction():
    r=_run(independently_measured_pipe_fittings_pressure_drop_Pa=None)
    result=pressure_loss_no_fit_score(r)
    assert result["status"]=="BLOCKED_UNMEASURED_EXTERNAL_PIPING_LOSS"
    assert not result["validation_passed"]


def test_pressure_loss_ergun_positive_synthetic_diagnostic_not_certification():
    r=_run()
    result=pressure_loss_no_fit_score(r)
    assert result["status"]=="NO_FIT_PHYSICAL_ERGUN_DIAGNOSTIC"
    assert result["measured_bed_only_dP_Pa"]==185.
    assert result["predicted_ergun_dP_Pa"]>0.
    assert result["evidence_class"]=="SYNTHETIC_UNIT_TEST_NOT_EXPERIMENTAL_VALIDATION"
    assert result["validation_passed"] is False


def test_excessive_pipe_correction_blocks_pressure_validation():
    r=_run(independently_measured_pipe_fittings_pressure_drop_Pa=250.)
    out=pressure_loss_no_fit_score(r)
    assert out["status"]=="BLOCKED_SOURCE_CORRECTION_EXCEEDS_TOTAL_TAP_LOSS"


def test_thermal_history_scores_only_resolved_sensor_positions_and_times():
    r=_run(1)
    p=[list(row) for row in r.observed_fluid_temperature_K_by_sensor]
    res=score_independent_holdout_thermal_history(
        r,p,training_run_ids=["synthetic-0"],holdout_run_ids=["synthetic-1"])
    assert res["status"]=="POINTWISE_THERMAL_HISTORY_DIAGNOSTIC_ONLY"
    assert res["total_correlated_timeseries_values"]==8
    assert all(x["MAE_K"]==0. for x in res["per_position_error"])
    assert not res["experimental_validation_certified"]


def test_train_holdout_leakage_and_unsupported_position_fail_closed():
    r=_run()
    p=[list(row) for row in r.observed_fluid_temperature_K_by_sensor]
    with pytest.raises(ValueError,match="heldout run"):
        score_independent_holdout_thermal_history(
            r,p,training_run_ids=[r.run_id],holdout_run_ids=[r.run_id])
    with pytest.raises(ValueError,match="positions"):
        score_independent_holdout_thermal_history(
            r,p[:1],training_run_ids=[],holdout_run_ids=[r.run_id])
    with pytest.raises(ValueError,match="timestamps"):
        score_independent_holdout_thermal_history(
            r,[(300.,310.),(300.,310.)],
            training_run_ids=[],holdout_run_ids=[r.run_id])


def test_mixed_experimental_rig_never_pooled_even_if_same_fluid():
    rr=[_run(i) for i in range(4)]
    rr[2]=replace(rr[2],apparatus_id="SECOND_SYNTHETIC_RIG")
    with pytest.raises(ValueError,match="different apparatus"):
        fixed_run_holdout_protocol(rr,
            holdout_run_ids=["synthetic-2","synthetic-3"],
            expected_evidence="SYNTHETIC_UNIT_TEST")
