"""M3.2: falsifiable process contract and conservative cyclic closure."""
import pytest

pytest.importorskip("scipy")
from carnot_battery_lab.physics.gas_rock_regenerator import BedState,GasRockBed
from carnot_battery_lab.physics.matched_thermal_service import (
    MatchedThermalProtocol,max_terminal_field_difference_K,
    sampled_interval_service_passes,scan_matched_thermal_schedules,
)


def test_temperature_qualification_and_per_interval_duty_are_joint_guards():
    valid={"sampled_temperature_grade_qualified":True,
           "qualified_process_heat_J":1_100_000.}
    invalid_grade={"sampled_temperature_grade_qualified":False,
                   "qualified_process_heat_J":9_999_999.}
    short_duty={"sampled_temperature_grade_qualified":True,
                "qualified_process_heat_J":10_000.}
    check=lambda rows:sampled_interval_service_passes(
        rows,required_interval_heat_J=1_000_000.,expected_intervals=2)
    assert check([valid,valid])
    assert not check([valid,invalid_grade])
    assert not check([valid,short_duty])
    assert not check([valid])
    assert not check([valid,valid,valid])


def test_cyclic_full_fields_not_masked_by_identical_bulk_energy():
    before=BedState((300.,400.),(310.,390.))
    after=BedState((400.,300.),(390.,310.))
    assert sum(before.fluid_temperature_K)==sum(after.fluid_temperature_K)
    assert sum(before.solid_temperature_K)==sum(after.solid_temperature_K)
    assert max_terminal_field_difference_K(before,after)==100.


@pytest.mark.parametrize("kwargs",[
    {"charge_step_counts":()},
    {"charge_step_counts":(2,2)},
    {"discharge_step_counts":(True,)},
    {"repeat_cycles":2},
    {"repeat_cycles":True},
    {"nominal_process_duty_W":0.},
    {"terminal_max_abs_difference_K":-1.},
])
def test_invalid_search_contract_fails_early(kwargs):
    with pytest.raises(ValueError):
        MatchedThermalProtocol(**kwargs)


def test_exact_repeated_R718_handoff_is_fail_closed_for_original_grade():
    pytest.importorskip("CoolProp")
    from carnot_battery_lab.physics.coupled_charge import ChargeControl
    from carnot_battery_lab.physics.r718 import R718Inputs
    from carnot_battery_lab.physics.sequential_hp_tes_service import (
        CandidateProcessGasService,
    )
    bed=GasRockBed(cells=8)
    initial=BedState.uniform(bed,95.)
    protocol=MatchedThermalProtocol(
        charge_step_counts=(2,),discharge_step_counts=(2,),
        repeat_cycles=3,nominal_process_duty_W=1_000_000.,
        terminal_max_abs_difference_K=.25)
    out=scan_matched_thermal_schedules(
        bed,initial,R718Inputs(),
        ChargeControl(dt_s=120.,number_of_steps=2),
        CandidateProcessGasService(
            process_return_K=383.15,required_supply_K=423.15,
            reverse_mass_flow_kg_s=25.,dt_s=60.,requested_steps=2),
        protocol)
    assert out["candidate_count"]==1
    assert out["hardware_qualified"] is False
    assert out["physical_validation"] is False
    assert out["round_trip_efficiency"] is None
    candidate=out["candidates"]["charge_2_discharge_2"]
    assert candidate["requested_gas_temperature_grade_K"]==[
        383.15,423.15]
    assert candidate["required_interval_gas_heat_J"]==pytest.approx(
        25*1005*40*60)
    assert candidate["system_round_trip_efficiency"] is None
    assert candidate["validated_compressor_and_source_envelope"] is False
    assert candidate["continuous_between_samples_temperature_guarantee"] is False
    cycles=candidate["cycles"]
    assert len(cycles)>=1
    assert cycles[0]["start_bed_state"]["fluid_temperature_K"]==[
        368.15]*bed.cells
    for i in range(len(cycles)-1):
        # Every next cycle MUST begin with the exact earlier discharge state.
        if "final_bed_state" in cycles[i]:
            assert cycles[i+1]["start_bed_state"]==cycles[i]["final_bed_state"]
    for row in cycles:
        if row["status"]=="NUMERICAL_CYCLE_COMPLETED":
            assert abs(row["storage_energy_closure_residual_J"])<2e4
            assert row["charge_electricity_J_partial_aux"]>0.
            assert row["sampled_discharge_intervals"][0][
                "first_process_gas_out_K"]>0.
    # Existing cold/short path does not establish a full matched contract.
    # Even if a later model-only path passes, hardware status must stay False.
    assert candidate["status"]!="VALIDATED_CARNOT_BATTERY"
