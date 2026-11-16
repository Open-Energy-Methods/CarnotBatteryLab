"""M1.5 tests use synthetic GENERATIVE fixtures, not manufactured equipment.

The synthetic positive control proves only that the fixed-speed convex-hull,
independent holdouts, rated-limit guards and multipoint sweep are executable.
It cannot prove measured hardware performance or an industrial process duty.
"""
from dataclasses import asdict, replace
import json
import pytest

from carnot_battery_lab.physics.compressor_envelope_requirements import (
    CompressorStageDemand,
)
from carnot_battery_lab.physics.measured_compressor_map_gate import (
    MapEvidence, RatedMapLimits, MapObservation, MapThresholds, CompressorMap,
    validate_holdouts, screen_stage_demand, screen_compressor_train,
    screen_r718_charging_trajectory,read_map_package,
)


TRAIN="H_REF_R718_TWO_STAGE_INTERCOOLED"
TOPO="R718_TWO_STAGE_WITH_EXTERNAL_INTERCOOLER"


def demand(stage="stage1", *, p=100000.,ratio=2.,v=1.):
    return CompressorStageDemand(
        refrigerant="R718 water",stage=stage,
        suction_pressure_Pa=p,discharge_pressure_Pa=p*ratio,
        suction_temperature_C=80.,discharge_temperature_C=150.,
        stage_pressure_ratio=ratio,refrigerant_mass_flow_kg_s=1.,
        suction_density_kg_m3=1./v,suction_volumetric_flow_m3_s=v,
        shaft_power_W_idealized=100000.)


def measured_outputs(p,t,ratio,vol):
    # Exact affine synthetic map; no mechanical claim about any real compressor.
    return {
        "refrigerant_mass_flow_kg_s":1.+0.1*(vol-1.)+0.000001*(p-100000.),
        "shaft_power_W":100000.+10000.*(ratio-2.)+400.*(t-80.)+10000.*(vol-1.),
        "discharge_temperature_C":150.+50.*(ratio-2.)+0.5*(t-80.),
    }


def observation(label, role, coords, *,speed=10000.,bad_power=0.):
    p,t,ratio,vol=coords
    outputs=measured_outputs(p,t,ratio,vol)
    outputs["shaft_power_W"]+=bad_power
    return MapObservation(
        point_id=label,role=role,speed_rpm=speed,
        suction_pressure_Pa=p,suction_temperature_C=t,
        stage_pressure_ratio=ratio,
        suction_volumetric_flow_m3_s=vol,
        **outputs,
        isentropic_efficiency=.74,stability_confirmed=True,
        flow_relative_standard_uncertainty=.005,
        shaft_relative_standard_uncertainty=.005,
        discharge_temperature_standard_uncertainty_K=.2)


def synth_map(stage="stage1", *,bad_holdout=False,
              mismatch_id=False) -> CompressorMap:
    base=(100000.,80.,2.,1.)
    fit=[
        (101000.,80.,2.,1.),
        (100000.,82.,2.,1.),
        (100000.,80.,2.1,1.),
        (100000.,80.,2.,1.1),
        (99000.,78.,1.9,.9),
    ]
    # Both withheld points are strictly interior to the five-vertex simplex.
    holdout=[base,(100200.,80.2,2.01,1.01)]
    points=tuple(
        observation("fit"+str(i),"fit",x) for i,x in enumerate(fit)
    )+tuple(
        observation("holdout"+str(i),"holdout",x,
                    bad_power=8000. if bad_holdout and i==1 else 0.)
        for i,x in enumerate(holdout)
    )
    evidence=MapEvidence(
        evidence_class="SYNTHETIC_TEST_FIXTURE",
        manufacturer_or_laboratory="TEST ONLY NO LAB",
        machine_id="SYNTHETIC_NO_HARDWARE",
        train_id="WRONG_TRAIN" if mismatch_id else TRAIN,
        topology_id=TOPO, stage=stage, refrigerant="R718 water",
        source_document_url=None,source_document_sha256=None,
        calibration_traceability_reference=None,
        heldout_test_campaign_id=None,independent_review_reference=None,
    )
    rating=RatedMapLimits(
        minimum_speed_rpm=9000.,maximum_speed_rpm=11000.,
        maximum_absolute_discharge_pressure_Pa=300000.,
        maximum_stage_pressure_ratio=2.5,
        maximum_discharge_temperature_C=180.,
        maximum_shaft_power_W=120000.)
    return CompressorMap(evidence,rating,points)


def test_map_schema_requires_actual_fit_and_holdout_separation():
    base=synth_map()
    with pytest.raises(ValueError,match="holdout"):
        CompressorMap(base.evidence,base.rated_limits,
                      base.points[:5]+(base.points[5],))
    with pytest.raises(ValueError,match="excluded"):
        CompressorMap(base.evidence,base.rated_limits,
            base.points[:5]+(
                replace(base.points[5],suction_pressure_Pa=101000.),
                base.points[6]))
    with pytest.raises(ValueError,match="duplicate"):
        CompressorMap(base.evidence,base.rated_limits,
                      tuple(replace(x,point_id="same") for x in base.points))


def test_declared_rated_limits_and_point_uncertainty_must_be_valid():
    m=synth_map()
    with pytest.raises(ValueError,match="limits"):
        RatedMapLimits(**{**asdict(m.rated_limits),"maximum_speed_rpm":100.})
    with pytest.raises(ValueError,match="measured field"):
        replace(m.points[0],flow_relative_standard_uncertainty=-1.)
    with pytest.raises(ValueError,match="stability"):
        replace(m.points[0],stability_confirmed=False)
    with pytest.raises(ValueError,match="rated"):
        CompressorMap(m.evidence,replace(m.rated_limits,
                maximum_stage_pressure_ratio=2.05),m.points)


def test_unverified_or_forged_measured_evidence_rejected_by_schema():
    x=synth_map().evidence
    with pytest.raises(ValueError,match="source"):
        replace(x,evidence_class="MEASURED_UNREVIEWED")
    with pytest.raises(ValueError,match="review"):
        replace(x,evidence_class="MEASURED_REVIEW_ASSERTED",
            source_document_url="https://example.org/raw-map",
            source_document_sha256="a"*64,
            calibration_traceability_reference="CAL-1",
            heldout_test_campaign_id="HOLDOUT-1")
    declared=replace(x,evidence_class="MEASURED_REVIEW_ASSERTED",
        source_document_url="https://example.org/raw-map",
        source_document_sha256="a"*64,
        calibration_traceability_reference="CAL-1",
        heldout_test_campaign_id="HOLDOUT-1",
        independent_review_reference="https://example.org/review")
    assert declared.independent_review_reference
    # A syntactically valid review claim remains just an assertion in JSON.
    assert declared.evidence_class=="MEASURED_REVIEW_ASSERTED"


def test_missing_map_never_promoted():
    result=screen_stage_demand(demand(),(),train_id=TRAIN,topology_id=TOPO)
    assert result["status"]=="NO_IDENTITY_AND_TOPOLOGY_MATCHED_MAP"
    assert result["local_map_support"] is False
    assert result["hardware_qualified"] is False


def test_positive_interior_synthetic_control_and_heldout_interpolation():
    pytest.importorskip("scipy")
    m=synth_map()
    hold=validate_holdouts(m,MapThresholds())
    assert hold["passed"] is True
    assert hold["heldout_count"]==2
    assert all(row["test_not_used_for_fit"] is True for row in hold["details"])
    result=screen_stage_demand(demand(),(m,),train_id=TRAIN,topology_id=TOPO)
    assert result["local_map_support"] is True
    assert result["supported_speed_rpm"]==10000.
    assert result["status"]=="MODEL_COORDINATES_LOCALLY_SUPPORTED_BY_SYNTHETIC_MAP_ONLY"
    assert result["hardware_qualified"] is False
    assert result["source_authenticity_independently_verified_by_software"] is False
    assert result["speed_line_trials"][0]["holdout_points_excluded_from_fit"] is True


def test_corrupted_independent_holdout_blocks_even_perfect_training_fit():
    pytest.importorskip("scipy")
    m=synth_map(bad_holdout=True)
    h=validate_holdouts(m,MapThresholds())
    assert h["passed"] is False
    assert any(x["status"]=="HOLDOUT_PREDICTION_FAILED" for x in h["details"])
    result=screen_stage_demand(demand(),(m,),train_id=TRAIN,topology_id=TOPO)
    assert result["status"]=="INDEPENDENT_HOLDOUT_VALIDATION_FAILED"
    assert result["local_map_support"] is False


@pytest.mark.parametrize("changed",[
    {"p":120000.},
    {"ratio":2.3},
    {"v":1.3},
])
def test_extrapolation_blocked_in_every_independent_map_coordinate(changed):
    pytest.importorskip("scipy")
    args={"stage":"stage1","p":100000.,"ratio":2.,"v":1.}
    args.update(changed)
    result=screen_stage_demand(demand(**args),(synth_map(),),
                               train_id=TRAIN,topology_id=TOPO)
    assert result["local_map_support"] is False
    assert result["hardware_qualified"] is False


def test_compressor_temperature_guard_blocks_despite_hull_coverage():
    pytest.importorskip("scipy")
    m=synth_map()
    d=replace(demand(),discharge_temperature_C=190.)
    result=screen_stage_demand(d,(m,),train_id=TRAIN,topology_id=TOPO)
    assert result["local_map_support"] is False
    assert result["speed_line_trials"][0]["status"]==(
        "MODEL_DISCHARGE_TEMPERATURE_ABOVE_MACHINE_RATING")


def test_stage_machine_and_topology_crosswiring_fails():
    pytest.importorskip("scipy")
    m=synth_map(stage="stage1")
    assert not screen_stage_demand(
        demand(stage="stage2"),(m,),train_id=TRAIN,
        topology_id=TOPO)["local_map_support"]
    assert not screen_stage_demand(
        demand(),(m,),train_id=TRAIN,
        topology_id="DIFFERENT_IHX_TOPOLOGY")["local_map_support"]
    assert not screen_stage_demand(
        demand(),(synth_map(mismatch_id=True),),train_id=TRAIN,
        topology_id=TOPO)["local_map_support"]


def test_two_stage_synthetic_train_not_a_physical_train():
    pytest.importorskip("scipy")
    first=synth_map("stage1")
    second=synth_map("stage2")
    out=screen_compressor_train(
        (demand("stage1"),demand("stage2")),(first,second),
        train_id=TRAIN,topology_id=TOPO)
    assert out["model_stage_coordinates_supported"] is True
    assert out["machine_hardware_qualified"] is False
    assert out["all_stage_speeds_coordinated_and_controllable"] is False
    out2=screen_compressor_train(
        (demand("stage1"),demand("stage2")),(first,),
        train_id=TRAIN,topology_id=TOPO)
    assert out2["model_stage_coordinates_supported"] is False


def test_incomplete_charge_trajectory_never_passes_with_supported_points():
    pytest.importorskip("scipy")
    point={
        "step":1,"elapsed_s":120.,"bed_return_C":100.,"hot_gas_supply_C":140.,
        "compressor_stages":[asdict(demand("stage1")),
                            asdict(demand("stage2"))],
    }
    maps=(synth_map("stage1"),synth_map("stage2"))
    done=screen_r718_charging_trajectory(
        {"charge_completed":True,"charge_termination_reason":None,
         "points":[point]},maps)
    assert done["entire_requested_trajectory_locally_supported"] is True
    assert done["compressor_machine_hardware_qualified"] is False
    aborted=screen_r718_charging_trajectory(
        {"charge_completed":False,
         "charge_termination_reason":"InfeasibleCycle: discharge temperature",
         "points":[point]},maps)
    assert aborted["all_completed_steps_locally_supported"] is True
    assert aborted["entire_requested_trajectory_locally_supported"] is False
    assert aborted["status"]=="R718_CHARGE_ENVELOPE_NOT_ESTABLISHED"


def test_loader_rejects_schema_and_duplicate_stage(tmp_path):
    m=synth_map()
    file=tmp_path/"map.json"
    file.write_text(json.dumps({"schema":"bad","maps":[asdict(m)]}))
    with pytest.raises(ValueError,match="schema"):
        read_map_package(file)
    file.write_text(json.dumps({"schema":"m1.5-measured-map-v1",
                                "maps":[asdict(m),asdict(m)]}))
    with pytest.raises(ValueError,match="multiple"):
        read_map_package(file)
    file.write_text(json.dumps({"schema":"m1.5-measured-map-v1",
                                "maps":[asdict(m)]}))
    assert len(read_map_package(file))==1


def test_cannot_blend_between_two_rpm_lines_to_create_fictitious_speed_support():
    pytest.importorskip("scipy")
    m=synth_map()
    moved_low=tuple(replace(p,speed_rpm=9000.,
        suction_pressure_Pa=p.suction_pressure_Pa-8000.)
        for p in m.points)
    moved_high=tuple(replace(p,speed_rpm=11000.,
        point_id="hi-"+p.point_id,
        suction_pressure_Pa=p.suction_pressure_Pa+8000.)
        for p in m.points)
    merged=CompressorMap(
        m.evidence,m.rated_limits,
        moved_low+moved_high)
    result=screen_stage_demand(demand(),(merged,),
                               train_id=TRAIN,topology_id=TOPO)
    assert result["local_map_support"] is False
    assert all(row["status"]=="OUTSIDE_FIXED_SPEED_MEASURED_CONVEX_HULL"
               for row in result["speed_line_trials"])


def test_measured_map_eos_sanity_rejects_thermophysically_fake_map():
    pytest.importorskip("scipy")
    pytest.importorskip("CoolProp")
    # Even seemingly complete declarations cannot make a made-up 1kg/m3,
    # 1kg/s R718 suction state a verified compressor performance map.
    fake=synth_map()
    evidence=replace(
        fake.evidence,evidence_class="MEASURED_REVIEW_ASSERTED",
        source_document_url="https://example.org/nonexistent-synthetic-map",
        source_document_sha256="a"*64,
        calibration_traceability_reference="SYNTHETIC-CAL",
        heldout_test_campaign_id="SYNTHETIC-RESERVED",
        independent_review_reference="https://example.org/nonexistent-review",
    )
    disguised=CompressorMap(evidence,fake.rated_limits,fake.points)
    result=screen_stage_demand(
        demand(),(disguised,),train_id=TRAIN,topology_id=TOPO)
    assert result["status"]=="MEASURED_MAP_PROPERTY_AND_ENERGY_AUDIT_FAILED"
    assert result["measured_point_thermodynamic_audit"]["passed"] is False
    assert result["local_map_support"] is False
    assert result["hardware_qualified"] is False


def test_each_accepted_speed_line_needs_its_own_two_holdouts():
    pytest.importorskip("scipy")
    example=synth_map()
    shifted_fit=tuple(replace(p,point_id="low-"+p.point_id,
        suction_pressure_Pa=p.suction_pressure_Pa-8000.)
        for p in example.points if p.role=="fit")
    shifted_holdout=tuple(replace(p,point_id="low-"+p.point_id,
        suction_pressure_Pa=p.suction_pressure_Pa-8000.)
        for p in example.points if p.role=="holdout")
    # 10000 rpm line has valid holdouts but no target coverage.
    # 10500 rpm line has target coverage but no holdouts at that speed.
    untested_fit=tuple(replace(p,point_id="untested-"+p.point_id,
        speed_rpm=10500.) for p in example.points if p.role=="fit")
    map_without_speed_holdouts=CompressorMap(
        example.evidence,example.rated_limits,
        shifted_fit+shifted_holdout+untested_fit)
    result=screen_stage_demand(
        demand(),(map_without_speed_holdouts,),
        train_id=TRAIN,topology_id=TOPO)
    assert result["local_map_support"] is False
    states={row["speed_rpm"]:row["status"] for row in result["speed_line_trials"]}
    assert states[10000.]=="OUTSIDE_FIXED_SPEED_MEASURED_CONVEX_HULL"
    assert states[10500.]=="INSUFFICIENT_HOLDOUTS_ON_THIS_SPEED_LINE"


def test_interpolated_measured_outputs_must_agree_with_cycle_work():
    pytest.importorskip("scipy")
    altered=replace(demand(),shaft_power_W_idealized=109000.)
    result=screen_stage_demand(
        altered,(synth_map(),),train_id=TRAIN,topology_id=TOPO)
    assert result["local_map_support"] is False
    assert result["speed_line_trials"][0]["status"]==(
        "MAP_PREDICTION_DIFFERS_FROM_CYCLE_HYPOTHESIS")


def test_inflated_uncertainty_is_not_a_way_to_pass_bad_measured_map():
    pytest.importorskip("scipy")
    good=synth_map()
    broad=CompressorMap(good.evidence,good.rated_limits,tuple(
        replace(x,flow_relative_standard_uncertainty=.20)
        for x in good.points))
    h=validate_holdouts(broad,MapThresholds())
    assert h["passed"] is False
    assert h["status"]=="DECLARED_MEASUREMENT_UNCERTAINTY_TOO_LARGE"
    assert not screen_stage_demand(
        demand(),(broad,),train_id=TRAIN,topology_id=TOPO)["local_map_support"]


def test_small_holdout_bias_fails_if_more_than_three_standard_uncertainties():
    pytest.importorskip("scipy")
    m=synth_map()
    changed=tuple(
        replace(x,shaft_power_W=x.shaft_power_W+3000.)
        if x.point_id=="holdout1" else x
        for x in m.points)
    biased=CompressorMap(m.evidence,m.rated_limits,changed)
    # 3% is less than the 5% absolute model screen, but greater than
    # 3x the reported 0.5% measurement standard uncertainty.
    h=validate_holdouts(biased,MapThresholds())
    assert h["passed"] is False
    assert any(x["status"]=="HOLDOUT_PREDICTION_FAILED" for x in h["details"])
