"""New axial conduction term remains internally conservative and optional."""
import pytest
pytest.importorskip("scipy")
from carnot_battery_lab.physics.gas_rock_regenerator import (
    GasRockBed,BedState,advance_bed,bed_energy_J)


def test_solid_axial_conduction_preserves_energy_under_zero_wall_and_zero_flow():
    from dataclasses import replace
    base=GasRockBed(cells=8,wall_UA_W_K=0.0,
                    solid_axial_conductivity_W_mK=0.0)
    conduction=replace(base,solid_axial_conductivity_W_mK=100.0)
    state=BedState((350.,)*8,(450.,350.,350.,350.,350.,350.,350.,350.))
    a=advance_bed(base,state,inlet_K=350.,mass_flow_kg_s=0,dt_s=600.)
    b=advance_bed(conduction,state,inlet_K=350.,mass_flow_kg_s=0,dt_s=600.)
    assert abs(b.heat_from_hot_gas_J)<1e-4
    assert abs(b.heat_loss_to_ambient_J)<1e-4
    assert abs(b.stored_energy_change_J)<.01
    assert abs(b.energy_residual_J)<.01
    assert b.final_state.solid_temperature_K[1]>a.final_state.solid_temperature_K[1]
    assert b.final_state.solid_temperature_K[0]<a.final_state.solid_temperature_K[0]


def test_zero_axial_conduction_is_default_for_backward_comparison():
    base=GasRockBed()
    assert base.solid_axial_conductivity_W_mK==0


def test_negative_axial_conductivity_is_rejected():
    with pytest.raises(ValueError,match="axial conductivity"):
        GasRockBed(solid_axial_conductivity_W_mK=-1)
