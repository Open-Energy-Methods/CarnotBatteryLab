"""Closed gas cycle: independent conservation and physical negative controls."""
from dataclasses import replace
import pytest
pytest.importorskip("CoolProp")
from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle,blower_flow
from carnot_battery_lab.physics.open_real_air_water_train import OpenAirWaterTrain
from carnot_battery_lab.physics.real_air_bed_prototype import _tp_properties
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry

def small():
    return ClosedCycle(train=OpenAirWaterTrain(bed_cells=2,hx_cells=2,initial_bed_solid_K=383.15),
                      charge_s=120.,discharge_s=60.)

def test_blower_head_closed_positive_branch():
    c=small()
    g=PackedBedGeometry(length_m=.5,diameter_m=.3,particle_diameter_m=.01,porosity=.4)
    s=_tp_properties(383.15,250000.)
    b=_tp_properties(383.15,250100.)
    m,w,el,head=blower_flow(s,b,g,.25,c)
    assert 0<m<c.blower_assumed_zero_head_flow_kg_s
    assert 0<head<c.blower_shutoff_head_Pa
    assert 0<w<el
    assert el*c.motor_efficiency==pytest.approx(w)
    b=_tp_properties(383.15,251000.)
    assert blower_flow(s,b,g,.25,c)==(0.,0.,0.,0.)

def test_closed_cycle_no_inventory_reset_and_separate_electricity():
    r=run_closed_cycle(small())
    a,b=r["charge"],r["discharge"]
    assert r["charge_end_is_discharge_start"]
    assert a["gas_final_mass_kg"]==pytest.approx(b["gas_input_mass_kg"],abs=1e-10)
    assert a["solid_energy_change_J"]>0
    assert a["heater_electric_J"]>a["heater_thermal_to_gas_J"]>0
    assert a["water_boundary_heat_J"]==0
    assert a["cooler_heat_to_assumed_sink_J"]==0
    assert b["heater_electric_J"]==0
    assert b["water_boundary_heat_J"]>0
    assert b["cooler_heat_to_assumed_sink_J"]>0
    for phase in (a,b):
        assert abs(phase["mass_residual_kg"])<1e-8
        assert abs(phase["thermal_first_law_residual_J"])<.1
        assert abs(phase["electrical_boundary_residual_J"])<.1
        assert phase["blower_electric_J"]>phase["blower_work_to_gas_J"]>0
        assert phase["max_accepted_node_Mach"]<.1
    assert r["closed_gas_circulation_modeled"]
    assert not r["verified_periodic_cycle"]
    assert not r["industrial_1MW_service_qualified"]
    assert r["Carnot_battery_RTE"] is None

def test_preheated_inventory_not_permitted():
    with pytest.raises(ValueError,match="cold state"):
        ClosedCycle(train=OpenAirWaterTrain())
@pytest.mark.parametrize("kwargs",[{"heater_efficiency":1.1},{"return_gas_volume_m3":0},
                                 {"blower_shutoff_head_Pa":10000},{"charge_s":0}])
def test_bad_inputs(kwargs):
    with pytest.raises(ValueError):ClosedCycle(**kwargs)
