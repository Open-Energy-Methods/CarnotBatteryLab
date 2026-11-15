"""Fixed-point exhaust flow: measured outlet temperature is never an input."""
import pytest
pytest.importorskip("scipy")
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed,BedState
from carnot_battery_lab.validation.exhaust_flow_coupling import (
    ExhaustCouplingSettings,step_from_velocity,ideal_gas_mass_flow)


def bed():
    return GasRockBed(
        geometry=PackedBedGeometry(.4,.158,.02,.39),cells=8,
        gas_density_kg_m3=1.0,rock_density_kg_m3=3700,
        rock_cp_J_kgK=1100,wall_UA_W_K=.5)


def test_exhaust_density_gives_lower_mdot_for_higher_predicted_temperature():
    s=ExhaustCouplingSettings()
    a=ideal_gas_mass_flow(temperature_K=300,measured_velocity_m_s=5,settings=s)
    b=ideal_gas_mass_flow(temperature_K=600,measured_velocity_m_s=5,settings=s)
    assert a==pytest.approx(2*b)


def test_coupled_flow_converges_and_preserves_model_energy_without_observed_tout():
    b=bed()
    state=BedState.uniform(b,30)
    x=step_from_velocity(b,state,inlet_temperature_K=423.15,
                         measured_exhaust_velocity_m_s=5,dt_s=30)
    assert x.iterations>=1
    assert x.mass_flow_kg_s>0
    assert x.relative_flow_residual<=ExhaustCouplingSettings().relative_flow_tolerance
    assert x.measured_outlet_temperature_used_as_input is False
    step=x.bed_step
    assert abs(step.energy_residual_J)<1e-5*max(1,abs(step.heat_from_hot_gas_J))


def test_outlet_target_values_cannot_change_forward_result():
    b=bed()
    state=BedState.uniform(b,30)
    # No measured outlet is passed into the solver. Changing independent
    # temperature observations affects only evaluation, not physics.
    measured_targets=(100.,300.)
    runs=[step_from_velocity(
        b,state,inlet_temperature_K=423.15,
        measured_exhaust_velocity_m_s=5,dt_s=30) for _ in measured_targets]
    assert runs[0].mass_flow_kg_s==pytest.approx(runs[1].mass_flow_kg_s)
    assert runs[0].bed_step.final_outlet_temperature_K==pytest.approx(
        runs[1].bed_step.final_outlet_temperature_K)


def test_bad_bore_or_pressure_is_rejected_before_prediction():
    with pytest.raises(ValueError):
        ExhaustCouplingSettings(pipe_inner_diameter_m=0)
    with pytest.raises(ValueError):
        ExhaustCouplingSettings(exhaust_pressure_Pa=0)


def test_zero_velocity_not_spurious_flow_or_pressure_loss():
    b=bed()
    s=BedState.uniform(b,30)
    out=step_from_velocity(b,s,inlet_temperature_K=423.15,
                           measured_exhaust_velocity_m_s=0,dt_s=30)
    assert out.mass_flow_kg_s==0
    assert out.bed_step.pressure_drop_Pa==0
