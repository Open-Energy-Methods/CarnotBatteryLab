"""Sequential model consistency: R718 charge state -> reverse packed-bed gas heat."""
import pytest
pytest.importorskip("scipy")
pytest.importorskip("CoolProp")
from carnot_battery_lab.physics.gas_rock_regenerator import (
    GasRockBed,BedState)
from carnot_battery_lab.physics.coupled_charge import ChargeControl,simulate_charge
from carnot_battery_lab.physics.r718 import R718Inputs
from carnot_battery_lab.physics.sequential_hp_tes_service import (
    CandidateProcessGasService,handoff_coupled_charge_to_reverse_discharge)


@pytest.fixture(scope="module")
def short_hp_charge():
    bed=GasRockBed(cells=8)
    s=BedState.uniform(bed,95.)
    run=simulate_charge(bed,s,R718Inputs(),
                        ChargeControl(dt_s=120.,number_of_steps=2))
    assert run.completed,run.termination_reason
    return bed,run


def test_discharge_can_reuse_true_coupled_charge_final_state_and_close_energy(short_hp_charge):
    bed,run=short_hp_charge
    result=handoff_coupled_charge_to_reverse_discharge(
        bed,run,CandidateProcessGasService(requested_steps=3,dt_s=60.))
    assert result["charging_HP_was_TES_state_responsive"] is True
    assert result["charge_completed_steps"]==2
    assert len(result["discharge_steps"])==3
    assert abs(result["discharge_energy_residual_J"])<.002*max(
        1.,abs(result["signed_discharge_heat_into_process_gas_J"]))
    assert result["charge_grid_electricity_J_including_partial_aux"]>0
    assert result["discharge_model_blower_electricity_J"]>0
    assert result["charge_compressor_hardware_qualified"] is False
    assert result["matched_service_architecture_comparison_qualified"] is False
    assert result["round_trip_efficiency"] is None
    if result["status"]=="PROCESS_GRADE_UNMET_AT_REQUESTED_TEMPERATURE":
        assert result["qualified_process_heat_J"]==0


def test_real_110_to_150_process_grade_is_not_fabricated(short_hp_charge):
    bed,run=short_hp_charge
    result=handoff_coupled_charge_to_reverse_discharge(
        bed,run,CandidateProcessGasService(
            process_return_K=383.15,required_supply_K=423.15,
            requested_steps=2,dt_s=60.))
    assert result["status"]=="PROCESS_GRADE_UNMET_AT_REQUESTED_TEMPERATURE"
    assert result["qualified_process_heat_J"]==0
    assert all(not row["sampled_temperature_grade_qualified"]
               for row in result["discharge_steps"])
    assert result["total_qualified_thermodynamic_process_service"] is False


def test_charge_infeasibility_blocks_discharge_not_invents_performance():
    bed=GasRockBed(cells=8)
    hot=simulate_charge(
        bed,BedState.uniform(bed,155.),R718Inputs(),
        ChargeControl(number_of_steps=2,dt_s=120))
    assert hot.completed is False
    result=handoff_coupled_charge_to_reverse_discharge(bed,hot)
    assert result["status"]=="BLOCKED_INCOMPLETE_COUPLED_CHARGE"
    assert result["discharge_steps"]==[]
    assert result["qualified_process_heat_J"]==0
    assert result["round_trip_efficiency"] is None


def test_invalid_process_temperature_order_rejected():
    with pytest.raises(ValueError):
        CandidateProcessGasService(
            process_return_K=423.,required_supply_K=403.)
