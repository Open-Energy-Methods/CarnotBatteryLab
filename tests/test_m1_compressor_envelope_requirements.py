"""Independent numerical invariants and adverse evidence cases for M1.4.

Real-fluid property checks do not turn literature into compressor-map
validation; the literature gate MUST remain unqualified.
"""
from dataclasses import replace
import pytest

from carnot_battery_lab.physics.compressor_literature_gate import (
    PublishedHardwareEvidence, TARGET, evidence_crosswalk,
    assess_reference_against_h_ref, REQUIRED_MAP_FIELDS,
)
from carnot_battery_lab.physics.compressor_envelope_requirements import (
    source_and_process_requirements, CompressorStageDemand,
)


def test_target_source_and_process_heat_capacity_requirements():
    r=source_and_process_requirements(
        q_source_W=1_000_000.,process_duty_W=1_000_000.)
    assert r["source_heat_available_at_assumed_cap_W"]==pytest.approx(1_045_000.)
    assert r["source_flow_required_kg_s"]==pytest.approx(
        1_000_000./(4180.*10.))
    assert r["required_process_water_flow_kg_s"]==pytest.approx(
        1_000_000./(4180.*40.))
    assert r["source_heat_below_assumed_cap"] is True
    assert source_and_process_requirements(
        q_source_W=1_060_000.,process_duty_W=1e6)[
        "source_heat_below_assumed_cap"] is False
    unknown=source_and_process_requirements(
        q_source_W=1e6,process_duty_W=1e6,
        assumed_max_source_flow_kg_s=None)
    assert unknown["source_heat_below_assumed_cap"] is None
    assert unknown["source_heat_available_at_assumed_cap_W"] is None
    assert unknown["assumed_source_flow_cap_kg_s"] is None


@pytest.mark.parametrize("kwargs",[
    {"q_source_W":-1.},
    {"source_in_C":70.},
    {"process_supply_C":100.},
    {"source_cp_J_kgK":0.},
])
def test_invalid_demand_capacity_inputs_fail(kwargs):
    values={"q_source_W":1e6,"process_duty_W":1e6}
    values.update(kwargs)
    with pytest.raises(ValueError):
        source_and_process_requirements(**values)


def test_all_published_points_stay_fail_closed_and_missing_fields_are_visible():
    registry=evidence_crosswalk()
    assert registry["target"]==TARGET
    assert len(registry["records"])==8
    assert all(row["measured_exact_target_compressor_map_qualified"] is False
               for row in registry["records"])
    assert all(len(row["qualification_missing"])==len(REQUIRED_MAP_FIELDS)
               for row in registry["records"])
    by_id={x["id"]:x for x in registry["records"]}
    assert by_id["benkert_2025_2026_r600_steam_test"][
        "explicitly_different_or_insufficient_boundaries"][
        "maximum_reported_sink_C"]["published_C"]==120.
    assert by_id["pfeiffer_2026_r290_r601a_mixture_model"][
        "technical_applicability"]=="SIMULATION_ONLY_NOT_HARDWARE_QUALIFICATION"
    assert by_id["wu_2019_r718_injected_screw"][
        "refrigerant_evaporation_incompatible_with_80C_inlet"] is True
    assert by_id["verdnik_rieberer_2022_r600_experiment"][
        "reported_single_unit_capacity_below_1MW"] is True
    # Commercial steam product is not an 80C inlet machine or 110->150C
    # liquid process unit. Supplier publication explicitly lacks third-party
    # validation; never count a rated 624kW/165C steam point as H-REF pass.
    commercial=by_id["kobelco_sgh165_annex58_supplier_reported_commercial"]
    assert commercial["natural_refrigerant"] is False
    assert commercial["source_inlet_C"]==70.
    assert commercial["source_outlet_C"]==65.
    assert commercial["sink_supply_C"]==165.
    assert commercial["reported_single_unit_capacity_below_1MW"] is True
    assert commercial["measured_exact_target_compressor_map_qualified"] is False
    assert commercial["explicitly_different_or_insufficient_boundaries"][
        "source_inlet_C"]["target_C"]==80.
    demo=by_id["futraheat_2026_brewery_supplier_reported_demonstration"]
    assert demo["source_inlet_C"]==100.
    assert demo["sink_supply_C"]==130.
    assert demo["technical_applicability"]=="DIFFERENT_OR_UNREPORTED_TARGET_BOUNDARIES"


def test_an_exact_single_point_still_does_not_prove_multidimensional_map():
    item=PublishedHardwareEvidence(
        id="synthetic_test_not_real_hardware",
        url="https://example.com/synthetic",
        refrigerant="test fluid",natural_refrigerant=True,
        evidence_class="EXPERIMENTAL_POINT",
        source_inlet_C=80.,source_outlet_C=70.,
        sink_return_C=110.,sink_supply_C=150.,
        heating_output_kW=1000.)
    evaluation=assess_reference_against_h_ref(item)
    assert evaluation["missing_exact_boundary_fields"]==[]
    assert evaluation["explicitly_different_or_insufficient_boundaries"]=={}
    assert evaluation["technical_applicability"]==(
        "SINGLE_EXPERIMENTAL_POINT_NOT_FULL_ENVELOPE")
    assert evaluation["measured_exact_target_compressor_map_qualified"] is False


def test_unreviewed_manual_map_assertion_is_refused():
    with pytest.raises(ValueError,match="single point"):
        PublishedHardwareEvidence(
            id="invalid",url="https://example.com/not-a-map",
            refrigerant="R600",natural_refrigerant=True,
            evidence_class="EXPERIMENTAL_POINT",
            reported_compressor_map_at_target=True)


def test_compressor_stage_invalid_flow_or_pressure_rejected():
    kwargs=dict(
        refrigerant="R718",stage="first",suction_pressure_Pa=1e5,
        discharge_pressure_Pa=2e5,suction_temperature_C=70.,
        discharge_temperature_C=150.,stage_pressure_ratio=2.,
        refrigerant_mass_flow_kg_s=1.,suction_density_kg_m3=1.,
        suction_volumetric_flow_m3_s=1.,shaft_power_W_idealized=1000.)
    with pytest.raises(ValueError):
        CompressorStageDemand(**{**kwargs,"suction_density_kg_m3":0.})
    with pytest.raises(ValueError):
        CompressorStageDemand(**{**kwargs,"discharge_pressure_Pa":1e5})
    with pytest.raises(ValueError,match="inconsistent"):
        CompressorStageDemand(**{**kwargs,"stage_pressure_ratio":3.})
    with pytest.raises(ValueError,match="inconsistent"):
        CompressorStageDemand(**{**kwargs,"suction_volumetric_flow_m3_s":2.})


def test_r718_1mw_full_compressor_stage_requirements_and_trajectory():
    pytest.importorskip("CoolProp")
    pytest.importorskip("scipy")
    from CoolProp.CoolProp import PropsSI
    from carnot_battery_lab.physics.r718 import solve_r718,R718Inputs
    from carnot_battery_lab.physics.coupled_charge import ChargeControl,simulate_charge
    from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed,BedState
    from carnot_battery_lab.physics.compressor_envelope_requirements import (
        r718_stage_demands,r718_requirements_report,
        r718_charge_trajectory_demands,
    )
    x=solve_r718(R718Inputs())
    req=r718_requirements_report(x)
    assert req["equipment_map_qualified"] is False
    assert len(req["compressor_stage_demands"])==2
    stages=r718_stage_demands(x)
    assert sum(p.shaft_power_W_idealized for p in stages)==pytest.approx(
        x.W_compressor_shaft_W,rel=1e-10)
    for p in stages:
        expected=PropsSI("Dmass","P",p.suction_pressure_Pa,
                         "T",p.suction_temperature_C+273.15,"HEOS::Water")
        assert p.suction_density_kg_m3==pytest.approx(expected)
        assert p.suction_volumetric_flow_m3_s==pytest.approx(
            p.refrigerant_mass_flow_kg_s/expected,rel=1e-11)
    assert all(p.stage_pressure_ratio>1. for p in stages)
    assert req["heat_source_and_sink"]["source_heat_below_assumed_cap"]
    bed=GasRockBed(cells=8)
    ctrl=ChargeControl(dt_s=120.,number_of_steps=2)
    charge=simulate_charge(bed,BedState.uniform(bed,95.),R718Inputs(),ctrl)
    assert charge.completed,charge.termination_reason
    traj=r718_charge_trajectory_demands(charge,R718Inputs(),bed,ctrl)
    assert traj["charge_completed"] is True
    assert len(traj["points"])==2
    assert all(len(x["compressor_stages"])==2 for x in traj["points"])
    assert traj["entire_requested_trajectory_qualified"] is False
    for step,model_step in zip(traj["points"],charge.steps):
        assert step["compressor_electric_W_with_assumed_drive_losses"]==pytest.approx(
            model_step.compressor_electric_W,rel=1e-7)


def test_r600_screen_requirements_remain_unqualified_and_consistent():
    pytest.importorskip("CoolProp")
    pytest.importorskip("scipy")
    from carnot_battery_lab.physics.r600_transcritical_screen import (
        R600ScreenInputs,solve_r600_screen,scan_transcritical_high_side,
    )
    from carnot_battery_lab.physics.compressor_envelope_requirements import (
        r600_stage_demands,r600_requirements_report,
    )
    scan=scan_transcritical_high_side()
    feasible=[p for p in scan["points"]
              if p["status"]=="FINITE_HX_THERMODYNAMIC_SCREEN_PASS"]
    if not feasible:
        assert scan["screening_best_pressure_Pa"] is None
        return
    case=R600ScreenInputs(high_pressure_Pa=feasible[0]["pressure_Pa"])
    r=solve_r600_screen(case)
    stage=r600_stage_demands(r)[0]
    assert stage.stage_pressure_ratio==pytest.approx(r.pressure_ratio)
    assert stage.shaft_power_W_idealized==pytest.approx(r.W_shaft_W)
    assert stage.suction_volumetric_flow_m3_s>0.
    req=r600_requirements_report(r)
    assert req["equipment_map_qualified"] is False
    assert req["measured_compressor_operating_envelope"] is None
    assert req["heat_source_and_sink"]["required_process_water_flow_kg_s"]==pytest.approx(
        1_000_000./(4180*40))
