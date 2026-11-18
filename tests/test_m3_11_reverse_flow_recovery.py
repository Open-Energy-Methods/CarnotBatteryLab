"""M3.11: routing, grade-ledger crossing and conservation regressions."""
from dataclasses import replace
import numpy as np
import pytest
pytest.importorskip("CoolProp")
from carnot_battery_lab.physics.closed_real_air_cycle import (
    ClosedCycle,run_closed_cycle,gas_route,qualified_water_heat,blower_flow)
from carnot_battery_lab.physics.real_air_bed_prototype import _tp_properties
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry

def test_route_reverses_only_bed():
    assert gas_route(3,2,False).tolist()==[0,1,2,3,4,5]
    assert gas_route(3,2,True).tolist()==[2,1,0,3,4,5]

def test_grade_two_crossings_and_exact_ledger():
    def sol(t):return np.array([4-(t-3)**2,2*t*t])
    t=np.arange(0.,7.)
    seconds,heat=qualified_water_heat(t,sol,0,1,0.)
    assert seconds==pytest.approx(4.)
    assert heat==pytest.approx(48.)

def test_grade_negative_and_all_pass():
    t=[0.,1.,2.]
    assert qualified_water_heat(t,lambda x:[-1.,x],0,1,0.)==(0.,0.)
    assert qualified_water_heat(t,lambda x:[1.,x],0,1,0.)==(2.,2.)

def test_valve_reduces_blower_flow_at_fixed_states():
    c=ClosedCycle()
    g=PackedBedGeometry(length_m=.5,diameter_m=.3,particle_diameter_m=.01,porosity=.4)
    s=_tp_properties(383.15,250000.)
    d=_tp_properties(383.15,250100.)
    assert blower_flow(s,d,g,.25,c,valve_loss_K=20.)[0]<blower_flow(s,d,g,.25,c)[0]

@pytest.fixture(scope="module")
def paired():
    c=ClosedCycle()
    c=replace(c,train=replace(c.train,bed_cells=2,hx_cells=2),charge_s=120.,discharge_s=120.)
    return (run_closed_cycle(c,valve_loss_K=2.),
            run_closed_cycle(c,reverse_discharge=True,valve_loss_K=2.,cycles=2))

def test_same_charge_and_reversed_discharge(paired):
    a,b=paired
    assert a["charge"]["heater_electric_J"]==pytest.approx(b["charge"]["heater_electric_J"],rel=1e-9)
    assert a["charge"]["final_solid_C"]==pytest.approx(b["charge"]["final_solid_C"])
    assert b["charge"]["bed_flow_order"]==[0,1]
    assert b["discharge"]["bed_flow_order"]==[1,0]
    assert a["discharge"]["bed_flow_order"]==[0,1]

def test_repeated_conservation_and_qualified_ledger(paired):
    _,b=paired
    assert len(b["cycle_records"])==2
    assert not b["verified_periodic_cycle"]
    assert abs(b["repeated_sequence_mass_residual_kg"])<1e-8
    assert abs(b["repeated_sequence_electrical_residual_J"])<.2
    for p in b["cycle_records"]:
        ch,di=p["charge"],p["discharge"]
        assert ch["gas_final_mass_kg"]==pytest.approx(di["gas_input_mass_kg"],abs=1e-10)
        assert 0<=di["qualified_water_duration_s"]<=di["duration_s"]
        assert di["qualified_water_heat_J"]>=-1e-6
        assert di["qualified_water_heat_J"]+di["signed_water_heat_outside_grade_J"]==pytest.approx(di["water_boundary_heat_J"],abs=1e-6)
        for z in (ch,di):
            assert max(abs(v) for v in z["component_thermal_residuals_J"].values())<.2
    assert b["cycle_records"][1]["charge"]["gas_input_mass_kg"]==pytest.approx(b["cycle_records"][0]["discharge"]["gas_final_mass_kg"],abs=1e-10)

@pytest.mark.parametrize("kwargs",[{"cycles":0},{"cycles":True},{"valve_loss_K":-1.},{"reverse_discharge":1}])
def test_reject_bad_controls(kwargs):
    with pytest.raises(ValueError):run_closed_cycle(ClosedCycle(),**kwargs)
