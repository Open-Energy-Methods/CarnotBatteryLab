"""Periodic convergence gate and bounded-flow prototype tests."""
from copy import deepcopy
import pytest
from carnot_battery_lab.physics.periodic_recovery import periodic_audit,STATE_LIMITS

def row(n):
    c={"heater_electric_J":1000.,"blower_electric_J":10.}
    d={"blower_electric_J":5.,"cooler_heat_to_assumed_sink_J":100.,
       "water_boundary_heat_J":500.,"qualified_water_heat_J":300.,
       "water_target_band_heat_J":200.,"qualified_water_duration_s":20.,
       "water_target_band_duration_s":10.}
    return dict(cycle=n,charge=c,discharge=d,**{k:0. for k in STATE_LIMITS})

def test_gate_requires_two_successive_passes():
    assert not periodic_audit([row(1),row(2)])["approximate_periodic_model_gate_pass"]
    assert periodic_audit([row(1),row(2),row(3)])["approximate_periodic_model_gate_pass"]

@pytest.mark.parametrize("key",list(STATE_LIMITS))
def test_state_not_masked_by_stable_energy(key):
    a,b,c=row(1),row(2),row(3)
    b[key]=2*STATE_LIMITS[key]
    assert not periodic_audit([a,b,c])["approximate_periodic_model_gate_pass"]

def test_unstable_output_and_duration_fail():
    a,b,c=row(1),row(2),row(3)
    c["discharge"]["water_target_band_duration_s"]+=1.
    assert not periodic_audit([a,b,c])["approximate_periodic_model_gate_pass"]
    c=deepcopy(b);c["cycle"]=3;c["discharge"]["qualified_water_heat_J"]+=20.
    assert not periodic_audit([a,b,c])["approximate_periodic_model_gate_pass"]

def test_nonfinite_rejected():
    a=row(1);a["max_rock_cycle_end_change_K"]=float("nan")
    with pytest.raises(ValueError):periodic_audit([a])

def test_controlled_flow_and_conservative_band_split():
    pytest.importorskip("CoolProp")
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    from dataclasses import replace
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    c=ClosedCycle()
    c=replace(c,charge_s=120.,discharge_s=60.,train=replace(c.train,bed_cells=2,hx_cells=2))
    x=run_closed_cycle(c,reverse_discharge=True,valve_loss_K=2.,water_control_gain_kg_s_K=.004)
    ch,d=x["charge"],x["discharge"]
    assert ch["water_throughput_kg"]==0.
    assert .1*c.train.water_flow_kg_s<=d["water_min_flow_at_nodes_kg_s"]<=d["water_max_flow_at_nodes_kg_s"]<=2*c.train.water_flow_kg_s
    assert .1*c.train.water_flow_kg_s*c.discharge_s-1e-6<=d["water_throughput_kg"]<=2*c.train.water_flow_kg_s*c.discharge_s+1e-6
    assert 0<=d["water_target_band_duration_s"]<=c.discharge_s
    assert d["water_target_band_heat_J"]>=-1e-6
    assert abs(x["repeated_sequence_electrical_residual_J"])<.2
